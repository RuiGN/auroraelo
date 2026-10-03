"""Domain event contract for the patient mobile API domain."""

from __future__ import annotations

from dataclasses import dataclass

from core.events import DomainEvent as CoreDomainEvent


@dataclass(frozen=True, slots=True)
class DomainEvent(CoreDomainEvent):
    """Base domain event for patient mobile API operations."""
