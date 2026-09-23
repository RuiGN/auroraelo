"""Public selector interface for the accounts domain."""

from uuid import UUID

from core.selectors import Selector as Selector

from .models import ClinicInvitation, User


def identity_export_records(
    *, clinic_id: UUID, subject_id: UUID
) -> list[dict[str, object]]:
    """Return subject-owned fields only when related to the explicit clinic."""
    identity = (
        User.objects.filter(
            pk=subject_id,
            clinic_memberships__clinic_id=clinic_id,
        )
        .values(
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "last_login",
        )
        .first()
    )
    if identity is None:
        return []
    return [
        {
            "type": "account",
            "id": str(identity["id"]),
            "email": identity["email"],
            "first_name": identity["first_name"],
            "last_name": identity["last_name"],
            "is_active": identity["is_active"],
            "date_joined": identity["date_joined"].isoformat(),
            "last_login": (
                identity["last_login"].isoformat()
                if identity["last_login"] is not None
                else None
            ),
        }
    ]


def accepted_professional_invitation(
    *, clinic_id: UUID, invitation_id: UUID
) -> tuple[str, UUID] | None:
    """Expose only role, category and user identity for an accepted invitation."""
    invitation = (
        ClinicInvitation.infrastructure_objects.filter(
            pk=invitation_id,
            clinic_id=clinic_id,
            used_at__isnull=False,
            initial_role="therapist",
        )
        .values("initial_category", "recipient_email")
        .first()
    )
    if invitation is None or not invitation["initial_category"]:
        return None
    user_id = (
        User.objects.filter(email=invitation["recipient_email"], is_active=True)
        .values_list("pk", flat=True)
        .first()
    )
    if user_id is None:
        return None
    return invitation["initial_category"], user_id


def active_user_display(*, user_id: UUID) -> tuple[str, str] | None:
    """Return name and e-mail of an active identity for a tenant projection."""
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return None
    return user.get_full_name().strip() or "Perfil profissional", user.email


__all__ = [
    "Selector",
    "accepted_professional_invitation",
    "active_user_display",
    "identity_export_records",
]
