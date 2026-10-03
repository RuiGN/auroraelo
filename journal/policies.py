"""Public authorization interface for the journal domain."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.utils import timezone

from clinics.policies import has_active_clinic_role
from core.policies import AuthorizationPolicy as AuthorizationPolicy
from people.selectors import linked_patients_for_therapist

__all__ = [
    "AuthorizationPolicy",
    "DiaryTarget",
    "StaffDiaryPolicy",
    "therapist_may_read_patient_diary",
]


@dataclass(frozen=True, slots=True)
class DiaryTarget:
    """One patient's diary inside one clinic."""

    clinic_id: UUID
    patient_profile_id: UUID


def therapist_may_read_patient_diary(
    *, clinic_id: UUID, therapist_id: UUID, patient_profile_id: UUID
) -> bool:
    """True only for a therapist with an active, dated care link to the patient."""
    today = timezone.localdate()
    if not has_active_clinic_role(
        clinic_id=clinic_id, user_id=therapist_id, role="therapist", on_date=today
    ):
        return False
    linked = linked_patients_for_therapist(
        clinic_id=clinic_id, therapist_id=therapist_id, on_date=today
    )
    return patient_profile_id in {row.patient_profile_id for row in linked}


class StaffDiaryPolicy:
    """Decide whether the team may read what one patient shares in the app.

    The diary and the check-ins are declared clinical data: the same rule as the
    domain selectors applies (only a therapist with an active, dated care link to
    that patient). A clinic administrator has no clinical read (matrix action
    ``patient.clinical.read``), so the diary stays closed to that role as well.
    """

    def is_allowed(self, actor: AbstractBaseUser, target: DiaryTarget, /) -> bool:
        return therapist_may_read_patient_diary(
            clinic_id=target.clinic_id,
            therapist_id=actor.pk,
            patient_profile_id=target.patient_profile_id,
        )
