"""Idempotent people-domain reactions to account lifecycle changes."""

from uuid import UUID

from django.dispatch import receiver

from accounts.events import invitation_accepted
from accounts.selectors import accepted_professional_invitation, active_user_display

from .models import (
    CareRelationship,
    PatientInvitationLink,
    PatientProfile,
    ProfessionalProfile,
)


@receiver(
    invitation_accepted,
    dispatch_uid="people.create_professional_profile_after_invitation.v1",
)
def create_professional_profile_after_invitation(
    sender: object,
    *,
    clinic_id: UUID,
    invitation_id: UUID,
    actor_id: UUID,
    **kwargs: object,
) -> None:
    """Create the professional projection inside the people domain."""
    del sender, kwargs
    accepted = accepted_professional_invitation(
        clinic_id=clinic_id, invitation_id=invitation_id
    )
    if accepted is None or accepted[1] != actor_id:
        return
    identity = active_user_display(user_id=actor_id)
    if identity is None:
        return
    full_name, email = identity
    ProfessionalProfile.infrastructure_objects.get_or_create(
        clinic_id=clinic_id,
        user_id=actor_id,
        defaults={
            "full_name": full_name,
            "professional_email": email,
            "category": accepted[0],
        },
    )


@receiver(
    invitation_accepted,
    dispatch_uid="people.attach_patient_profile_after_invitation.v1",
)
def attach_patient_profile_after_invitation(
    sender: object,
    *,
    clinic_id: UUID,
    invitation_id: UUID,
    actor_id: UUID,
    **kwargs: object,
) -> None:
    """Attach a consumed patient invitation to its server-owned profile once."""
    del sender, kwargs
    link = (
        PatientInvitationLink.objects.select_related("patient_profile")
        .filter(invitation_id=invitation_id)
        .first()
    )
    if link is None:
        return
    profile = link.patient_profile
    if profile.user_id is not None and profile.user_id != actor_id:
        return
    if profile.user_id is None:
        PatientProfile.infrastructure_objects.filter(
            pk=profile.pk,
            clinic_id=clinic_id,
            user__isnull=True,
        ).update(user_id=actor_id)
    CareRelationship.infrastructure_objects.filter(
        clinic_id=clinic_id,
        patient_profile_id=profile.pk,
        patient__isnull=True,
    ).update(patient_id=actor_id)
