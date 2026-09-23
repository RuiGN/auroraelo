"""Global user and membership administration services."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from accounts.events import account_audit_required
from accounts.models import ClinicInvitation, User
from clinics.models import Clinic, ClinicMembership
from clinics.services import create_clinic_membership, ensure_membership_activatable
from core.policies import current_actor_is_active
from people.models import ProfessionalProfile

_ALLOWED_CATEGORIES = frozenset(ProfessionalProfile.Category.values)


def require_global_operator(actor: AbstractBaseUser) -> User:
    """Require active platform staff without granting that role to clinic users."""
    if not isinstance(actor, User) or not current_actor_is_active(actor):
        raise PermissionDenied
    if not (actor.is_staff or actor.is_superuser):
        raise PermissionDenied
    return actor


def _audit_membership(*, actor: User, membership: ClinicMembership) -> None:
    """Emit only technical identifiers for a global membership change."""
    account_audit_required.send(
        sender=ClinicMembership,
        clinic_id=membership.clinic_id,
        actor_id=actor.pk,
        action="permission_change",
        resource_type="clinic_membership",
        resource_id=str(membership.pk),
        request_id=uuid4(),
        network_origin=None,
        justification=None,
    )


def _sync_professional_profile(
    *, membership: ClinicMembership, category: str
) -> ProfessionalProfile | None:
    """Create or update only the professional presentation, never credentials."""
    if membership.role != ClinicMembership.Role.THERAPIST:
        if category:
            raise ValidationError("A categoria exige o papel therapist.")
        return None
    if category not in _ALLOWED_CATEGORIES:
        raise ValidationError("Categoria profissional inválida.")
    if not category:
        return None
    user = membership.user
    profile, _created = ProfessionalProfile.infrastructure_objects.get_or_create(
        clinic_id=membership.clinic_id,
        user_id=membership.user_id,
        defaults={
            "full_name": user.get_full_name().strip() or "Perfil profissional",
            "professional_email": user.email,
            "category": category,
        },
    )
    if profile.category != category:
        profile.category = category
        profile.save(update_fields=("category", "updated_at"))
    return profile


@transaction.atomic
def link_or_update_membership(
    *,
    actor: AbstractBaseUser,
    user: User,
    clinic_id: UUID,
    role: str,
    category: str = "",
    unit_name: str = "",
    valid_from: date | None = None,
    valid_until: date | None = None,
    is_active: bool = True,
) -> ClinicMembership:
    """Link an existing identity or update its one authorized clinic relationship."""
    operator = require_global_operator(actor)
    if role not in ClinicMembership.Role.values:
        raise ValidationError(gettext("Papel de clínica inválido."))
    if not Clinic.infrastructure_objects.filter(pk=clinic_id, is_active=True).exists():
        raise PermissionDenied
    effective_valid_from = valid_from or timezone.localdate()
    if valid_until is not None and valid_until < effective_valid_from:
        raise ValidationError(gettext("A validade final é inválida."))
    membership = (
        ClinicMembership.infrastructure_objects.select_for_update()
        .filter(user_id=user.pk, clinic_id=clinic_id)
        .first()
    )
    if membership is None:
        membership = create_clinic_membership(
            clinic_id=clinic_id,
            user_id=user.pk,
            role=role,
            unit_name=unit_name,
            valid_from=effective_valid_from,
            valid_until=valid_until,
            authorized_by_id=operator.pk,
        )
    else:
        if is_active:
            ensure_membership_activatable(
                valid_from=effective_valid_from,
                valid_until=valid_until,
            )
        membership.role = role
        membership.unit_name = unit_name.strip()
        membership.valid_from = effective_valid_from
        membership.valid_until = valid_until
        membership.is_active = is_active
        membership.authorized_by_id = operator.pk
        membership.full_clean(validate_unique=False, validate_constraints=False)
        membership.save(
            update_fields=(
                "role",
                "unit_name",
                "valid_from",
                "valid_until",
                "is_active",
                "authorized_by",
                "updated_at",
            )
        )
    _sync_professional_profile(membership=membership, category=category)
    _audit_membership(actor=operator, membership=membership)
    return membership


@transaction.atomic
def update_membership_as_operator(
    *,
    actor: AbstractBaseUser,
    membership_id: UUID,
    role: str,
    category: str = "",
    unit_name: str = "",
    valid_from: date,
    valid_until: date | None,
    is_active: bool,
) -> ClinicMembership:
    """Update one target through global infrastructure scope."""
    operator = require_global_operator(actor)
    membership = (
        ClinicMembership.infrastructure_objects.select_for_update()
        .select_related("user", "clinic")
        .filter(pk=membership_id, clinic__is_active=True)
        .first()
    )
    if membership is None:
        raise PermissionDenied
    if role not in ClinicMembership.Role.values:
        raise ValidationError(gettext("Papel de clínica inválido."))
    if valid_until is not None and valid_until < valid_from:
        raise ValidationError(gettext("A validade final é inválida."))
    if is_active:
        ensure_membership_activatable(
            valid_from=valid_from,
            valid_until=valid_until,
        )
    membership.role = role
    membership.unit_name = unit_name.strip()
    membership.valid_from = valid_from
    membership.valid_until = valid_until
    membership.is_active = is_active
    membership.authorized_by_id = operator.pk
    membership.full_clean(validate_unique=False, validate_constraints=False)
    membership.save(
        update_fields=(
            "role",
            "unit_name",
            "valid_from",
            "valid_until",
            "is_active",
            "authorized_by",
            "updated_at",
        )
    )
    _sync_professional_profile(membership=membership, category=category)
    _audit_membership(actor=operator, membership=membership)
    return membership


@transaction.atomic
def revoke_invitation_as_operator(
    *, actor: AbstractBaseUser, invitation_id: UUID
) -> ClinicInvitation:
    """Revoke one pending invitation without exposing its bearer token."""
    operator = require_global_operator(actor)
    invitation = (
        ClinicInvitation.infrastructure_objects.select_for_update()
        .filter(pk=invitation_id, used_at__isnull=True, revoked_at__isnull=True)
        .first()
    )
    if invitation is None:
        raise PermissionDenied
    invitation.revoked_at = timezone.now()
    invitation.revoked_by = operator
    invitation.save(update_fields=("revoked_at", "revoked_by", "updated_at"))
    account_audit_required.send(
        sender=ClinicInvitation,
        clinic_id=invitation.clinic_id,
        actor_id=operator.pk,
        action="update",
        resource_type="clinic_invitation",
        resource_id=str(invitation.pk),
        request_id=uuid4(),
        network_origin=None,
        justification=None,
    )
    return invitation


__all__ = [
    "link_or_update_membership",
    "revoke_invitation_as_operator",
    "update_membership_as_operator",
]
