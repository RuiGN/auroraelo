"""Public authorization interface for the patient mobile API domain.

Access of the *patient app* is not granted through ``ACTION_ROLES``: a token session
exists only for an identity that holds the ``patient`` role in an active clinic, and
that decision is re-checked on every request (see ``mobile_api.services``).

The *staff panel* about a patient's app access (``mobile_api.views``) is decided here:

- the clinic administrator may open the panel and revoke devices of any patient of the
  clinic, and is the only role that issues or re-sends the activation invitation
  (same rule as the clinic matrix action ``invitation.issue``);
- a therapist may open the panel and revoke devices only of a patient to whom the
  therapist has an active, dated care link;
- administrative staff, patients and anyone else are denied.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from clinics.policies import has_active_clinic_role
from core.policies import AuthorizationPolicy as AuthorizationPolicy
from people.selectors import therapist_linked_to_patient_profile

from .contracts import INVITATION_ROLE

__all__ = [
    "AuthorizationPolicy",
    "can_issue_patient_invitation",
    "can_manage_patient_app",
]


def can_manage_patient_app(
    *, clinic_id: UUID, actor_id: UUID, patient_profile_id: UUID, on_date: date
) -> bool:
    """Whether the actor may see the app access of, and revoke devices of, a patient."""
    if has_active_clinic_role(
        clinic_id=clinic_id, user_id=actor_id, role="clinic_admin", on_date=on_date
    ):
        return True
    return has_active_clinic_role(
        clinic_id=clinic_id, user_id=actor_id, role="therapist", on_date=on_date
    ) and therapist_linked_to_patient_profile(
        clinic_id=clinic_id,
        therapist_id=actor_id,
        patient_profile_id=patient_profile_id,
        on_date=on_date,
    )


def can_issue_patient_invitation(
    *, clinic_id: UUID, actor_id: UUID, on_date: date
) -> bool:
    """Whether the actor may issue or re-send an activation invitation."""
    return has_active_clinic_role(
        clinic_id=clinic_id, user_id=actor_id, role=INVITATION_ROLE, on_date=on_date
    )
