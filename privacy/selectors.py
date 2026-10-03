"""Public privacy-domain selector contracts."""

from __future__ import annotations

from uuid import UUID

from core.selectors import Selector as Selector

from .models import DataSubjectRequest

__all__ = ["Selector", "data_subject_requests_for_subject"]


def data_subject_requests_for_subject(
    *, clinic_id: UUID, subject_id: UUID
) -> list[DataSubjectRequest]:
    """Return the requests a data subject filed (or had filed) for themselves."""
    return list(
        DataSubjectRequest.infrastructure_objects.filter(
            clinic_id=clinic_id, subject_id=subject_id
        ).order_by("-requested_at")
    )
