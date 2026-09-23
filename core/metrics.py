"""Application metrics middleware and SLO tracking.

Collects per-route latency (P50/P95/P99), error rates, and exposes a
``/metrics/`` endpoint for scraping. Designed to integrate with Prometheus,
Grafana, or any OpenTelemetry-compatible metrics collector.

Metrics are stored in-memory with a configurable rolling window.
For production clusters, export via OpenTelemetry metrics exporter instead.
"""

from __future__ import annotations

import bisect
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger("application.metrics")

_LOCK = threading.Lock()

# Configurable maximum observations per route before pruning oldest entries.
_MAX_OBSERVATIONS = 10_000


@dataclass
class RouteMetrics:
    """Thread-safe per-route metric accumulator."""

    request_count: int = 0
    error_count: int = 0
    latencies: list[float] = field(default_factory=list)

    def record(self, latency_ms: float, *, is_error: bool) -> None:
        self.request_count += 1
        if is_error:
            self.error_count += 1
        if len(self.latencies) >= _MAX_OBSERVATIONS:
            self.latencies = self.latencies[-(_MAX_OBSERVATIONS // 2) :]
        bisect.insort(self.latencies, latency_ms)

    def percentile(self, p: float) -> float | None:
        if not self.latencies:
            return None
        k = int(len(self.latencies) * p / 100)
        return self.latencies[min(k, len(self.latencies) - 1)]

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": (
                round(self.error_count / self.request_count, 4)
                if self.request_count > 0
                else 0.0
            ),
            "p50_ms": round(self.percentile(50) or 0, 2),
            "p95_ms": round(self.percentile(95) or 0, 2),
            "p99_ms": round(self.percentile(99) or 0, 2),
        }


_metrics: dict[str, RouteMetrics] = defaultdict(RouteMetrics)

# Routes to exclude from metrics collection (health checks, static files).
_EXCLUDE_PREFIXES = ("/health/", "/static/", "/media/", "/jsi18n/", "/favicon")


class MetricsMiddleware:
    """Collect per-route latency and error rate metrics.

    Insert after ``RequestCorrelationMiddleware`` in MIDDLEWARE to capture
    the full request lifecycle excluding correlation overhead.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path_info
        if any(path.startswith(prefix) for prefix in _EXCLUDE_PREFIXES):
            return self.get_response(request)

        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Use the URL route pattern (not the resolved path) to avoid
        # cardinality explosion from UUID segments.
        resolver = getattr(request, "resolver_match", None)
        route_key = resolver.route if resolver else path

        with _LOCK:
            _metrics[route_key].record(
                elapsed_ms, is_error=response.status_code >= 500
            )

        return response


def get_all_metrics() -> dict[str, Any]:
    """Return a snapshot of all collected route metrics."""
    with _LOCK:
        return {route: metrics.as_dict() for route, metrics in _metrics.items()}


def reset_metrics() -> None:
    """Clear all collected metrics (useful in tests)."""
    with _LOCK:
        _metrics.clear()


# ── SLO Definitions ──────────────────────────────────────────────────────────

SLO_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "scheduling.appointment_create",
        "description": "Appointment creation latency",
        "route_pattern": "agenda/",
        "target_p99_ms": 500,
    },
    {
        "name": "journal.checkin_submit",
        "description": "Daily check-in submission latency",
        "route_pattern": "journal/",
        "target_p99_ms": 300,
    },
    {
        "name": "api.response_time",
        "description": "API endpoint response time",
        "route_pattern": "api/",
        "target_p99_ms": 400,
    },
]


def evaluate_slos() -> list[dict[str, Any]]:
    """Evaluate all defined SLOs against current metrics."""
    results = []
    snapshot = get_all_metrics()
    for slo in SLO_DEFINITIONS:
        matching_routes = {
            route: data
            for route, data in snapshot.items()
            if slo["route_pattern"] in route
        }
        if not matching_routes:
            results.append(
                {
                    "name": slo["name"],
                    "status": "no_data",
                    "target_p99_ms": slo["target_p99_ms"],
                    "actual_p99_ms": None,
                }
            )
            continue

        # Aggregate: use the worst P99 across matching routes.
        worst_p99 = max(data["p99_ms"] for data in matching_routes.values())
        met = worst_p99 <= slo["target_p99_ms"]
        results.append(
            {
                "name": slo["name"],
                "status": "met" if met else "breached",
                "target_p99_ms": slo["target_p99_ms"],
                "actual_p99_ms": worst_p99,
                "total_requests": sum(
                    data["request_count"] for data in matching_routes.values()
                ),
            }
        )
    return results


# ── Views ─────────────────────────────────────────────────────────────────────


def metrics_view(request: HttpRequest) -> JsonResponse:
    """Expose application metrics for scraping (staff-only)."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    return JsonResponse(
        {
            "routes": get_all_metrics(),
            "slos": evaluate_slos(),
        },
        json_dumps_params={"indent": 2},
    )
