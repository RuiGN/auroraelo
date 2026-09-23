"""Append-only event store with temporal reconstruction capability.

Provides infrastructure for selective event sourcing in domains where
regulatory compliance demands provable state history (consents,
medical records, appointment lifecycle).

Events are immutable once persisted — ``save()`` on an existing record
and ``delete()`` both raise ``PermissionError``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import models
from django.utils import timezone

from core.persistence import UUIDTimestampedModel


class StoredEventQuerySet(models.QuerySet["StoredEvent"]):
    """Query set scoped by tenant/aggregate."""

    def for_aggregate(
        self, aggregate_type: str, aggregate_id: UUID
    ) -> StoredEventQuerySet:
        return self.filter(
            aggregate_type=aggregate_type, aggregate_id=aggregate_id
        )

    def for_tenant(self, tenant_id: UUID) -> StoredEventQuerySet:
        return self.filter(tenant_id=tenant_id)

    def as_of(self, timestamp: datetime) -> StoredEventQuerySet:
        return self.filter(occurred_at__lte=timestamp)


class StoredEvent(UUIDTimestampedModel):
    """Immutable domain event persisted in append-only sequence.

    Each event belongs to one aggregate (identified by ``aggregate_type``
    and ``aggregate_id``) and carries a monotonic ``sequence`` number.
    """

    aggregate_type = models.CharField(max_length=100, db_index=True)
    aggregate_id = models.UUIDField(db_index=True)
    sequence = models.PositiveIntegerField()
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField(default=dict)
    occurred_at = models.DateTimeField()
    actor_id = models.UUIDField()
    tenant_id = models.UUIDField(db_index=True)

    objects = StoredEventQuerySet.as_manager()

    class Meta:
        db_table = "core_stored_event"
        ordering = ["aggregate_id", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["aggregate_type", "aggregate_id", "sequence"],
                name="unique_event_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["aggregate_type", "aggregate_id", "occurred_at"],
                name="event_aggregate_temporal_idx",
            ),
            models.Index(
                fields=["tenant_id", "aggregate_type", "occurred_at"],
                name="event_tenant_temporal_idx",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Append-only: forbid updates to existing events."""
        if self.pk and StoredEvent.objects.filter(pk=self.pk).exists():
            raise PermissionError("Stored events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """Events cannot be deleted — regulatory requirement."""
        raise PermissionError("Stored events cannot be deleted.")

    def __str__(self) -> str:
        return (
            f"{self.aggregate_type}:{self.aggregate_id} "
            f"seq={self.sequence} {self.event_type}"
        )


# ── Event sourcing helpers ───────────────────────────────────────────────────

# Registry of event appliers per aggregate type.
# Each applier receives (state: dict, event_type: str, event_data: dict)
# and mutates state in place.
_EVENT_APPLIERS: dict[str, Callable[[dict, str, dict], None]] = {}


def register_event_applier(
    aggregate_type: str,
    applier: Callable[[dict, str, dict], None],
) -> None:
    """Register an event applier for a specific aggregate type."""
    _EVENT_APPLIERS[aggregate_type] = applier


def _default_applier(state: dict, event_type: str, event_data: dict) -> None:
    """Default applier that merges event data into state."""
    state["_last_event_type"] = event_type
    state.update(event_data)


def append_event(
    *,
    aggregate_type: str,
    aggregate_id: UUID,
    event_type: str,
    event_data: dict,
    actor_id: UUID,
    tenant_id: UUID,
    occurred_at: datetime | None = None,
) -> StoredEvent:
    """Persist one immutable event with auto-incrementing sequence.

    This is the sole entry point for writing events — ensures monotonic
    sequencing and consistent metadata.
    """
    last_seq = (
        StoredEvent.objects.filter(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
        )
        .order_by("-sequence")
        .values_list("sequence", flat=True)
        .first()
    ) or 0

    return StoredEvent.objects.create(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        sequence=last_seq + 1,
        event_type=event_type,
        event_data=event_data,
        occurred_at=occurred_at or timezone.now(),
        actor_id=actor_id,
        tenant_id=tenant_id,
    )


def reconstruct_state(
    *,
    aggregate_type: str,
    aggregate_id: UUID,
    as_of: datetime | None = None,
) -> dict:
    """Replay events to reconstruct aggregate state at a point in time.

    Used to answer compliance queries like:
    "What was the state of consent X on date Y?"
    """
    events = StoredEvent.objects.for_aggregate(aggregate_type, aggregate_id)
    if as_of is not None:
        events = events.as_of(as_of)

    applier = _EVENT_APPLIERS.get(aggregate_type, _default_applier)

    state: dict = {}
    for event in events.order_by("sequence"):
        applier(state, event.event_type, event.event_data)
    return state


def aggregate_history(
    *,
    aggregate_type: str,
    aggregate_id: UUID,
    since: datetime | None = None,
) -> list[StoredEvent]:
    """Return the full event history for one aggregate, optionally filtered."""
    events = StoredEvent.objects.for_aggregate(aggregate_type, aggregate_id)
    if since is not None:
        events = events.filter(occurred_at__gte=since)
    return list(events.order_by("sequence"))
