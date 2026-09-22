"""Tests for the metrics middleware, SLO evaluation, and telemetry helpers."""

from __future__ import annotations

import pytest
from django.http import HttpResponse
from django.test import Client, override_settings
from django.urls import path

from core.metrics import (
    RouteMetrics,
    evaluate_slos,
    get_all_metrics,
    reset_metrics,
)
from core.telemetry import enrich_span_with_tenant

pytestmark = pytest.mark.django_db


# ── RouteMetrics unit tests ──────────────────────────────────────────────────


class TestRouteMetrics:
    """Verify per-route metric accumulation and percentile calculations."""

    def test_empty_metrics_return_none_percentiles(self) -> None:
        m = RouteMetrics()
        assert m.percentile(50) is None
        assert m.percentile(99) is None

    def test_single_observation(self) -> None:
        m = RouteMetrics()
        m.record(42.0, is_error=False)
        assert m.request_count == 1
        assert m.error_count == 0
        assert m.percentile(50) == 42.0

    def test_error_counting(self) -> None:
        m = RouteMetrics()
        m.record(10.0, is_error=False)
        m.record(20.0, is_error=True)
        m.record(30.0, is_error=True)
        assert m.request_count == 3
        assert m.error_count == 2

    def test_percentile_calculation_with_100_observations(self) -> None:
        m = RouteMetrics()
        for i in range(100):
            m.record(float(i), is_error=False)
        assert m.percentile(50) == 50.0
        assert m.percentile(95) == 95.0
        assert m.percentile(99) == 99.0

    def test_as_dict_contains_required_keys(self) -> None:
        m = RouteMetrics()
        m.record(100.0, is_error=False)
        m.record(500.0, is_error=True)
        result = m.as_dict()
        assert result["request_count"] == 2
        assert result["error_count"] == 1
        assert result["error_rate"] == 0.5
        assert "p50_ms" in result
        assert "p95_ms" in result
        assert "p99_ms" in result


# ── MetricsMiddleware integration ────────────────────────────────────────────


def metrics_echo(request):
    return HttpResponse("ok")


def metrics_error(request):
    return HttpResponse("error", status=500)


urlpatterns = [
    path("test-ok/", metrics_echo),
    path("test-error/", metrics_error),
]


class TestMetricsMiddleware:
    """Verify the middleware records metrics for real HTTP requests."""

    def setup_method(self) -> None:
        reset_metrics()

    @override_settings(ROOT_URLCONF=__name__)
    def test_successful_request_is_recorded(self, client: Client) -> None:
        client.get("/test-ok/")
        metrics = get_all_metrics()
        values = list(metrics.values())
        assert any(v["request_count"] >= 1 for v in values)
        assert all(v["error_count"] == 0 for v in values)

    @override_settings(ROOT_URLCONF=__name__)
    def test_error_response_increments_error_count(self, client: Client) -> None:
        client.get("/test-error/")
        metrics = get_all_metrics()
        values = list(metrics.values())
        assert any(v["error_count"] >= 1 for v in values)


# ── SLO evaluation ───────────────────────────────────────────────────────────


class TestSloEvaluation:
    """Verify SLO evaluation against collected metrics."""

    def setup_method(self) -> None:
        reset_metrics()

    def test_slos_return_no_data_when_empty(self) -> None:
        results = evaluate_slos()
        assert all(slo["status"] == "no_data" for slo in results)
        assert len(results) > 0


# ── Telemetry safe no-ops ────────────────────────────────────────────────────


class TestTelemetryHelpers:
    """Verify telemetry helpers are safe no-ops without OTel configured."""

    def test_enrich_span_with_tenant_is_safe_without_otel(self) -> None:
        """Must not raise even without an active OTel trace provider."""
        enrich_span_with_tenant(clinic_id="test-id", clinic_name="Test Clinic")

    def test_configure_telemetry_without_endpoint_is_noop(self) -> None:
        """Without OTEL_EXPORTER_OTLP_ENDPOINT, configure_telemetry does nothing."""
        import os

        from core.telemetry import configure_telemetry

        endpoint = os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
        try:
            configure_telemetry()
        finally:
            if endpoint:
                os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = endpoint
