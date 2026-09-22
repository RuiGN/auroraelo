"""Tests for the event store and DB router modules."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from core.db_router import ReadReplicaRouter
from core.event_store import (
    StoredEvent,
    append_event,
    reconstruct_state,
    aggregate_history,
    register_event_applier,
)


# ── StoredEvent immutability ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestStoredEventImmutability:
    """Events must be append-only: no updates, no deletes."""

    def _make_event(self, **overrides) -> StoredEvent:
        defaults = dict(
            aggregate_type="test",
            aggregate_id=uuid4(),
            sequence=1,
            event_type="test_event",
            event_data={"key": "value"},
            occurred_at=timezone.now(),
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        defaults.update(overrides)
        return StoredEvent.objects.create(**defaults)

    def test_create_event_succeeds(self) -> None:
        event = self._make_event()
        assert event.pk is not None
        assert event.event_type == "test_event"

    def test_update_existing_event_raises(self) -> None:
        event = self._make_event()
        event.event_data = {"changed": True}
        with pytest.raises(PermissionError, match="immutable"):
            event.save()

    def test_delete_event_raises(self) -> None:
        event = self._make_event()
        with pytest.raises(PermissionError, match="cannot be deleted"):
            event.delete()


# ── append_event ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAppendEvent:
    """Verify auto-sequencing and event creation."""

    def test_first_event_has_sequence_1(self) -> None:
        agg_id = uuid4()
        event = append_event(
            aggregate_type="consent",
            aggregate_id=agg_id,
            event_type="consent_created",
            event_data={"version": "v1.0"},
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert event.sequence == 1

    def test_subsequent_events_increment_sequence(self) -> None:
        agg_id = uuid4()
        tenant_id = uuid4()
        actor_id = uuid4()
        for i in range(3):
            event = append_event(
                aggregate_type="consent",
                aggregate_id=agg_id,
                event_type=f"event_{i}",
                event_data={"step": i},
                actor_id=actor_id,
                tenant_id=tenant_id,
            )
        assert event.sequence == 3


# ── reconstruct_state ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestReconstructState:
    """Verify temporal state reconstruction from events."""

    def test_reconstruct_empty_aggregate(self) -> None:
        state = reconstruct_state(
            aggregate_type="consent",
            aggregate_id=uuid4(),
        )
        assert state == {}

    def test_reconstruct_replays_events_in_order(self) -> None:
        agg_id = uuid4()
        tid = uuid4()
        aid = uuid4()
        append_event(
            aggregate_type="consent",
            aggregate_id=agg_id,
            event_type="created",
            event_data={"status": "pending"},
            actor_id=aid,
            tenant_id=tid,
        )
        append_event(
            aggregate_type="consent",
            aggregate_id=agg_id,
            event_type="granted",
            event_data={"status": "granted", "scope": "journal"},
            actor_id=aid,
            tenant_id=tid,
        )
        state = reconstruct_state(
            aggregate_type="consent",
            aggregate_id=agg_id,
        )
        assert state["status"] == "granted"
        assert state["scope"] == "journal"

    def test_reconstruct_as_of_returns_past_state(self) -> None:
        agg_id = uuid4()
        tid = uuid4()
        aid = uuid4()
        past = timezone.now() - timedelta(hours=2)
        future = timezone.now() + timedelta(hours=1)

        append_event(
            aggregate_type="consent",
            aggregate_id=agg_id,
            event_type="created",
            event_data={"status": "pending"},
            actor_id=aid,
            tenant_id=tid,
            occurred_at=past,
        )
        append_event(
            aggregate_type="consent",
            aggregate_id=agg_id,
            event_type="granted",
            event_data={"status": "granted"},
            actor_id=aid,
            tenant_id=tid,
            occurred_at=future,
        )
        # Reconstruct as of 1 hour ago — should not include the "granted" event
        state = reconstruct_state(
            aggregate_type="consent",
            aggregate_id=agg_id,
            as_of=timezone.now(),
        )
        assert state["status"] == "pending"


# ── aggregate_history ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAggregateHistory:
    """Verify event history retrieval."""

    def test_returns_ordered_events(self) -> None:
        agg_id = uuid4()
        tid = uuid4()
        aid = uuid4()
        for i in range(5):
            append_event(
                aggregate_type="appointment",
                aggregate_id=agg_id,
                event_type=f"transition_{i}",
                event_data={"step": i},
                actor_id=aid,
                tenant_id=tid,
            )
        history = aggregate_history(
            aggregate_type="appointment",
            aggregate_id=agg_id,
        )
        assert len(history) == 5
        assert [e.sequence for e in history] == [1, 2, 3, 4, 5]


# ── Custom applier ───────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCustomApplier:
    """Verify pluggable event appliers."""

    def test_custom_applier_is_called(self) -> None:
        def consent_applier(state: dict, event_type: str, data: dict) -> None:
            if event_type == "created":
                state.update(data)
                state["history"] = [event_type]
            else:
                state.update(data)
                state.setdefault("history", []).append(event_type)

        register_event_applier("test_consent", consent_applier)

        agg_id = uuid4()
        tid = uuid4()
        aid = uuid4()
        append_event(
            aggregate_type="test_consent",
            aggregate_id=agg_id,
            event_type="created",
            event_data={"version": "v1.0", "status": "pending"},
            actor_id=aid,
            tenant_id=tid,
        )
        append_event(
            aggregate_type="test_consent",
            aggregate_id=agg_id,
            event_type="granted",
            event_data={"status": "granted"},
            actor_id=aid,
            tenant_id=tid,
        )
        state = reconstruct_state(
            aggregate_type="test_consent",
            aggregate_id=agg_id,
        )
        assert state["status"] == "granted"
        assert state["history"] == ["created", "granted"]
        assert state["version"] == "v1.0"


# ── ReadReplicaRouter ────────────────────────────────────────────────────────


class TestReadReplicaRouter:
    """Verify the DB router routes reads/writes correctly."""

    def test_writes_always_go_to_default(self) -> None:
        router = ReadReplicaRouter()
        assert router.db_for_write(StoredEvent) == "default"

    def test_reads_from_non_replica_app_go_to_default(self) -> None:
        router = ReadReplicaRouter()
        assert router.db_for_read(StoredEvent) == "default"

    def test_allow_relation_returns_true(self) -> None:
        router = ReadReplicaRouter()
        assert router.allow_relation(None, None) is True

    def test_allow_migrate_only_on_default(self) -> None:
        router = ReadReplicaRouter()
        assert router.allow_migrate("default", "core") is True
        assert router.allow_migrate("replica", "core") is False
