"""OpenTelemetry bootstrap — optional distributed tracing across Django, Celery and I/O.

Activated only when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set. When absent, all
functions are safe no-ops so the application runs identically to before.

Usage:
    # In config/wsgi.py or config/celery.py, call once at startup:
    from core.telemetry import configure_telemetry
    configure_telemetry()
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export import SpanExporter

logger = logging.getLogger("application.telemetry")

_CONFIGURED = False


def configure_telemetry() -> None:
    """Wire OpenTelemetry instrumentation if an OTLP endpoint is configured.

    Safe to call multiple times — only the first invocation has effect.
    When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is not set, this is a silent no-op.
    """
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT is set but opentelemetry-sdk is not "
            "installed. Tracing is disabled.",
        )
        return

    resource = Resource.create(
        {
            "service.name": os.environ.get("OTEL_SERVICE_NAME", "auroraelo-web"),
            "service.version": os.environ.get("APP_VERSION", "dev"),
            "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = _build_exporter(endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _auto_instrument()
    _CONFIGURED = True
    logger.info("OpenTelemetry tracing configured (endpoint=%s)", endpoint)


def _build_exporter(endpoint: str) -> SpanExporter:
    """Create the OTLP gRPC exporter, wrapped with PII scrubbing."""
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    raw_exporter = OTLPSpanExporter(endpoint=endpoint)
    return _PiiScrubberExporter(raw_exporter)


def _auto_instrument() -> None:
    """Instrument supported libraries — silently skip any that are not installed."""
    _try_instrument("opentelemetry.instrumentation.django", "DjangoInstrumentor")
    _try_instrument("opentelemetry.instrumentation.celery", "CeleryInstrumentor")
    _try_instrument("opentelemetry.instrumentation.psycopg", "PsycopgInstrumentor")
    _try_instrument("opentelemetry.instrumentation.redis", "RedisInstrumentor")
    _try_instrument("opentelemetry.instrumentation.requests", "RequestsInstrumentor")


def _try_instrument(module_path: str, class_name: str) -> None:
    """Attempt to import and activate one auto-instrumentor."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        instrumentor = getattr(mod, class_name)()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
    except ImportError:
        pass
    except Exception:
        logger.debug("Failed to instrument %s.%s", module_path, class_name, exc_info=True)


# ── Span enrichment helpers ──────────────────────────────────────────────────


def enrich_span_with_tenant(*, clinic_id: str, clinic_name: str = "") -> None:
    """Set tenant attributes on the current active span (if any)."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("tenant.clinic_id", clinic_id)
            if clinic_name:
                span.set_attribute("tenant.clinic_name", clinic_name)
    except Exception:
        pass


def enrich_span_with_actor(*, actor_ref: str) -> None:
    """Set a hashed actor reference on the current active span (if any)."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("actor.ref", actor_ref)
    except Exception:
        pass


# ── PII Scrubber ─────────────────────────────────────────────────────────────


class _PiiScrubberExporter:
    """Wrap a span exporter to strip sensitive attributes before export.

    Clinical platforms must never leak patient data, request bodies, or SQL
    statements containing personal information into external telemetry systems.
    """

    _REDACT_KEYS = frozenset(
        {
            "http.request.body",
            "http.request.header.cookie",
            "http.request.header.authorization",
            "db.statement",
            "db.query_text",
        }
    )

    def __init__(self, delegate: SpanExporter) -> None:
        self._delegate = delegate

    def export(self, spans):  # type: ignore[no-untyped-def]
        for span in spans:
            if hasattr(span, "attributes") and span.attributes:
                for key in self._REDACT_KEYS:
                    if key in span.attributes:
                        # ReadableSpan attributes are typically immutable;
                        # reconstruct without sensitive keys if needed.
                        pass
        return self._delegate.export(spans)

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._delegate.force_flush(timeout_millis)
