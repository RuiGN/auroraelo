"""Regression tests for telemetry redaction at the exporter boundary."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from core.telemetry import _PiiScrubberExporter


class _SyntheticSpan:
    """Small immutable span-shaped object for exporter contract tests."""

    def __init__(self, attributes: dict[str, Any]) -> None:
        self.name = "synthetic-operation"
        self.attributes = MappingProxyType(attributes)


class _FakeExporter:
    """Exporter that records the exact objects it receives."""

    def __init__(self) -> None:
        self.exports: list[tuple[Any, ...]] = []
        self.shutdown_calls = 0
        self.flush_timeouts: list[int] = []

    def export(self, spans: Any) -> str:
        self.exports.append(tuple(spans))
        return "success"

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def force_flush(self, timeout_millis: int) -> bool:
        self.flush_timeouts.append(timeout_millis)
        return True


def test_scrubber_removes_sensitive_attributes_without_mutating_readable_span() -> None:
    """Sensitive request and SQL fields are absent from the delegate payload."""
    original_attributes = {
        "http.request.body": "synthetic body",
        "http.request.header.cookie": "synthetic cookie",
        "http.request.header.authorization": "Bearer synthetic-token",
        "db.statement": "SELECT synthetic_patient",
        "db.query_text": "synthetic query",
        "http.request.method": "GET",
    }
    original = _SyntheticSpan(original_attributes)
    delegate = _FakeExporter()

    result = _PiiScrubberExporter(delegate).export([original])

    assert result == "success"
    assert original.attributes == original_attributes
    exported = delegate.exports[0][0]
    assert exported is not original
    assert exported.attributes == {"http.request.method": "GET"}
    assert exported.name == original.name


def test_scrubber_passes_clean_spans_and_delegates_lifecycle() -> None:
    """Clean spans remain exportable and lifecycle methods reach the delegate."""
    original = _SyntheticSpan({"tenant.clinic_id": "clinic-synthetic"})
    delegate = _FakeExporter()
    scrubber = _PiiScrubberExporter(delegate)

    assert scrubber.export([original]) == "success"
    assert delegate.exports == [(original,)]
    assert scrubber.force_flush(1234) is True
    scrubber.shutdown()
    assert delegate.flush_timeouts == [1234]
    assert delegate.shutdown_calls == 1
