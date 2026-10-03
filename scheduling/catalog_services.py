"""Transactional services for the clinic's bookable service catalog.

A *service* is one appointment type the patient can ask for in the app (name,
duration and the buffer kept between two consultations). Only the clinic
administrator writes; every write is audited without copying the content.
"""

from __future__ import annotations

from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from audit.services import record_audit_event
from clinics.services import authorized_active_clinic, lock_clinic_for_update
from core.services import Service as Service

from .models import Service as ServiceModel

__all__ = [
    "MAX_BUFFER_MINUTES",
    "MAX_DURATION_MINUTES",
    "MAX_NAME_LENGTH",
    "MIN_DURATION_MINUTES",
    "Service",
    "create_service",
    "set_service_active",
    "update_service",
]

MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 480
MAX_BUFFER_MINUTES = 120
MAX_NAME_LENGTH = 255


def _require_admin(*, clinic_id: UUID, actor: AbstractBaseUser) -> None:
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action="clinic.manage")


def _clean_name(name: str) -> str:
    normalized = " ".join(name.split())
    if not normalized:
        raise ValidationError(_("Informe o nome do serviço."))
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValidationError(
            _("O nome do serviço é longo demais (máximo de 255 caracteres).")
        )
    return normalized


def _validate_timing(*, duration_minutes: int, buffer_minutes: int) -> None:
    if not MIN_DURATION_MINUTES <= duration_minutes <= MAX_DURATION_MINUTES:
        raise ValidationError(_("A duração deve ficar entre 5 e 480 minutos."))
    if not 0 <= buffer_minutes <= MAX_BUFFER_MINUTES:
        raise ValidationError(
            _("O intervalo entre consultas deve ficar entre 0 e 120 minutos.")
        )


def _assert_name_available(
    *, clinic_id: UUID, name: str, exclude_id: UUID | None = None
) -> None:
    clashes = ServiceModel.infrastructure_objects.filter(
        clinic_id=clinic_id, name__iexact=name
    )
    if exclude_id is not None:
        clashes = clashes.exclude(pk=exclude_id)
    if clashes.exists():
        raise ValidationError(_("Já existe um serviço com este nome."))


@transaction.atomic
def create_service(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    name: str,
    duration_minutes: int,
    buffer_minutes: int,
    request_id: UUID,
) -> ServiceModel:
    """Create one active bookable service for the clinic."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    normalized = _clean_name(name)
    _validate_timing(duration_minutes=duration_minutes, buffer_minutes=buffer_minutes)
    _assert_name_available(clinic_id=clinic_id, name=normalized)
    service = ServiceModel.infrastructure_objects.create(
        clinic_id=clinic_id,
        name=normalized,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="create",
        resource_type="service",
        resource_id=str(service.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return service


@transaction.atomic
def update_service(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    service_id: UUID,
    name: str,
    duration_minutes: int,
    buffer_minutes: int,
    request_id: UUID,
) -> ServiceModel:
    """Change a service's name and timing.

    Consultations already booked keep their own start and end; only the slots
    offered from now on follow the new duration and buffer.
    """
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    service = (
        ServiceModel.infrastructure_objects.select_for_update()
        .filter(pk=service_id, clinic_id=clinic_id)
        .first()
    )
    if service is None:
        raise PermissionDenied
    normalized = _clean_name(name)
    _validate_timing(duration_minutes=duration_minutes, buffer_minutes=buffer_minutes)
    _assert_name_available(clinic_id=clinic_id, name=normalized, exclude_id=service.pk)
    service.name = normalized
    service.duration_minutes = duration_minutes
    service.buffer_minutes = buffer_minutes
    service.save(
        update_fields=("name", "duration_minutes", "buffer_minutes", "updated_at")
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="update",
        resource_type="service",
        resource_id=str(service.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return service


@transaction.atomic
def set_service_active(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    service_id: UUID,
    is_active: bool,
    request_id: UUID,
) -> ServiceModel:
    """Activate or deactivate a service; booked consultations are untouched."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    service = (
        ServiceModel.infrastructure_objects.select_for_update()
        .filter(pk=service_id, clinic_id=clinic_id)
        .first()
    )
    if service is None:
        raise PermissionDenied
    if service.is_active != is_active:
        service.is_active = is_active
        service.save(update_fields=("is_active", "updated_at"))
        record_audit_event(
            clinic_id=clinic_id,
            actor_id=actor.pk,
            action="update",
            resource_type="service",
            resource_id=str(service.pk),
            outcome="success",
            request_id=request_id,
            network_origin=None,
        )
    return service
