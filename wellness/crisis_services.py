"""Service layer for crisis mode access and emergency one-touch actions (8.15.5)."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from audit.services import record_audit_event
from clinics.services import authorized_active_clinic, lock_clinic_for_update
from core.services import Service as CoreService

from .events import crisis_emergency_action_triggered, crisis_mode_accessed
from .models import (
    MANDATORY_CRISIS_DISCLAIMER,
    CrisisAccessLog,
    CrisisResourceConfig,
)

SERVICE_NUMBER_MAX_LENGTH = 16
HELPLINE_NUMBER_MAX_LENGTH = 32
HELPLINE_NAME_MAX_LENGTH = 128
MAX_DISCLAIMER_LENGTH = 1000
MIN_PHONE_DIGITS = 3
MAX_PHONE_DIGITS = 15

# Dialed from the patient app: only digits, spaces and one leading plus.
_PHONE_PATTERN = re.compile(r"\+?[0-9][0-9 ]*")


class CrisisService(CoreService[Any, Any]):
    """Crisis domain service base."""


@transaction.atomic
def log_crisis_mode_access(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    action_invoked: str = "viewed_disclaimer",
    offline_mode_active: bool = False,
    actor_id: UUID | None = None,
) -> CrisisAccessLog:
    """Log crisis mode entry ensuring mandatory disclaimer is visible."""
    now = timezone.now()
    log = CrisisAccessLog.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        accessed_at=now,
        action_invoked=action_invoked,
        confirmation_requested=False,
        confirmation_granted=True,
        offline_mode_active=offline_mode_active,
    )

    crisis_mode_accessed.send(sender=CrisisAccessLog, log=log)
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="wellness.crisis_mode_accessed",
        resource_type="crisis_access_log",
        resource_id=str(log.id),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
    )
    return log


@transaction.atomic
def trigger_emergency_touch_action(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    action_invoked: str,  # e.g., "call_samu_192", "call_cvv_188"
    confirmation_confirmed: bool,
    actor_id: UUID | None = None,
) -> CrisisAccessLog:
    """Execute one-touch action requiring user confirmation before dialing."""
    if not confirmation_confirmed:
        raise ValidationError(
            "Confirmação explícita do usuário é obrigatória antes de acionar chamada."
        )

    now = timezone.now()
    log = CrisisAccessLog.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        accessed_at=now,
        action_invoked=action_invoked,
        confirmation_requested=True,
        confirmation_granted=True,
        offline_mode_active=False,
    )

    crisis_emergency_action_triggered.send(sender=CrisisAccessLog, log=log)
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="wellness.emergency_action_confirmed",
        resource_type="crisis_access_log",
        resource_id=str(log.id),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
    )
    return log


def clean_phone_number(value: str, *, max_length: int) -> str:
    """Normalize a number to digits, single spaces and an optional leading plus."""
    normalized = " ".join(value.split())
    if not _PHONE_PATTERN.fullmatch(normalized):
        raise ValidationError(_("Use apenas dígitos, espaços e um + no início."))
    digits = sum(character.isdigit() for character in normalized)
    if not MIN_PHONE_DIGITS <= digits <= MAX_PHONE_DIGITS:
        raise ValidationError(_("O número deve ter entre 3 e 15 dígitos."))
    if len(normalized) > max_length:
        raise ValidationError(_("O número é longo demais."))
    return normalized


def clean_disclaimer_text(value: str) -> str:
    """Return the notice text, which must keep the mandatory statement.

    The clinic may add guidance around it but never remove or empty it.
    """
    lines = value.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
    cleaned = "\n".join(line.rstrip() for line in lines)
    if not cleaned:
        raise ValidationError(_("O aviso não pode ficar vazio."))
    if " ".join(MANDATORY_CRISIS_DISCLAIMER.split()) not in " ".join(cleaned.split()):
        raise ValidationError(
            _(
                "O aviso deve manter o texto obrigatório. Você pode acrescentar "
                "orientações antes ou depois dele."
            )
        )
    if len(cleaned) > MAX_DISCLAIMER_LENGTH:
        raise ValidationError(_("O aviso é longo demais (máximo de 1000 caracteres)."))
    return cleaned


@transaction.atomic
def update_crisis_resources(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    emergency_medical_number: str,
    emergency_fire_number: str,
    emotional_support_number: str,
    custom_helpline_name: str,
    custom_helpline_number: str,
    mandatory_disclaimer_text: str,
    request_id: UUID,
) -> CrisisResourceConfig:
    """Save the numbers and notice the patient app shows in a crisis.

    Only the clinic administrator may change them. The mandatory notice cannot be
    removed or emptied, numbers are validated for the dialer, and the change is
    audited without copying the content.
    """
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action="clinic.manage")
    lock_clinic_for_update(clinic_id=clinic_id)
    helpline_name = " ".join(custom_helpline_name.split())
    helpline_number = custom_helpline_number.strip()
    if len(helpline_name) > HELPLINE_NAME_MAX_LENGTH:
        raise ValidationError(_("O nome da linha de apoio é longo demais."))
    if bool(helpline_name) != bool(helpline_number):
        raise ValidationError(
            _("Informe o nome e o telefone da linha de apoio ou deixe os dois vazios.")
        )
    values = {
        "emergency_medical_number": clean_phone_number(
            emergency_medical_number, max_length=SERVICE_NUMBER_MAX_LENGTH
        ),
        "emergency_fire_number": clean_phone_number(
            emergency_fire_number, max_length=SERVICE_NUMBER_MAX_LENGTH
        ),
        "emotional_support_number": clean_phone_number(
            emotional_support_number, max_length=SERVICE_NUMBER_MAX_LENGTH
        ),
        "custom_helpline_name": helpline_name,
        "custom_helpline_number": (
            clean_phone_number(helpline_number, max_length=HELPLINE_NUMBER_MAX_LENGTH)
            if helpline_number
            else ""
        ),
        "mandatory_disclaimer_text": clean_disclaimer_text(mandatory_disclaimer_text),
    }
    config = (
        CrisisResourceConfig.infrastructure_objects.select_for_update()
        .filter(clinic_id=clinic_id)
        .first()
    )
    if config is None:
        config = CrisisResourceConfig.infrastructure_objects.create(
            clinic_id=clinic_id, **values
        )
        action = "create"
    else:
        changed = [
            name for name, value in values.items() if getattr(config, name) != value
        ]
        if not changed:
            return config
        for name in changed:
            setattr(config, name, values[name])
        config.save(update_fields=(*changed, "updated_at"))
        action = "update"
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action=action,
        resource_type="crisis_resource_config",
        resource_id=str(config.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return config


__all__ = [
    "HELPLINE_NAME_MAX_LENGTH",
    "HELPLINE_NUMBER_MAX_LENGTH",
    "MAX_DISCLAIMER_LENGTH",
    "SERVICE_NUMBER_MAX_LENGTH",
    "CrisisService",
    "clean_disclaimer_text",
    "clean_phone_number",
    "log_crisis_mode_access",
    "trigger_emergency_touch_action",
    "update_crisis_resources",
]
