"""Domain events (signals) published by the concierge domain after commit."""

from __future__ import annotations

from dataclasses import dataclass

from django.dispatch import Signal

from core.events import DomainEvent as CoreDomainEvent


@dataclass(frozen=True, slots=True)
class DomainEvent(CoreDomainEvent):
    """Base domain event for concierge operations."""


rule_saved = Signal()
discharge_registered = Signal()
discharge_canceled = Signal()
aftercare_contact_completed = Signal()
aftercare_contact_rescheduled = Signal()
aftercare_contact_missed = Signal()
family_contact_saved = Signal()
family_consent_changed = Signal()
concierge_log_recorded = Signal()
family_request_registered = Signal()
family_request_changed = Signal()
