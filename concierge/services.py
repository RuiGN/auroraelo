"""Serviços transacionais do concierge e do acompanhamento pós-alta.

Toda gravação: (1) reautoriza ator + clínica pela matriz de ações, (2) valida a
entrada no servidor, (3) mantém o isolamento por clínica e (4) deixa trilha de
auditoria. O registro do concierge é somente de acréscimo: correções geram um novo
registro que aponta para o anterior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from audit.services import record_audit_event
from clinics.services import authorized_active_clinic, lock_clinic_for_update
from core.services import Service as Service
from people.selectors import patient_profile_in_clinic

from .contracts import (
    ACTION_MANAGE,
    ACTION_MANAGE_RULES,
    CALL_OUTCOMES,
    DEFAULT_RULE_NAME,
    DEFAULT_RULE_STEPS,
    MAX_BACKDATE_DAYS,
    MAX_DAY_AFTER_DISCHARGE,
    MAX_NOTES_LENGTH,
    MAX_RULE_STEPS,
    MAX_SUMMARY_LENGTH,
    MIN_SUMMARY_LENGTH,
    OPEN_REQUEST_STATUSES,
    SUCCESS_OUTCOMES,
    VISIT_OUTCOMES,
    ContactKind,
    ContactOutcome,
    ContactStatus,
    DischargeStatus,
    LogChannel,
    LogDirection,
    RequestKind,
    RequestStatus,
    ResponsibleRole,
)
from .events import (
    aftercare_contact_completed,
    aftercare_contact_missed,
    aftercare_contact_rescheduled,
    concierge_log_recorded,
    discharge_canceled,
    discharge_registered,
    family_consent_changed,
    family_contact_saved,
    family_request_changed,
    family_request_registered,
    rule_saved,
)
from .models import (
    AftercareContact,
    CommunicationRule,
    CommunicationRuleStep,
    ConciergeLog,
    Discharge,
    FamilyContact,
    FamilyRequest,
)

__all__ = [
    "Service",
    "add_family_contact",
    "cancel_discharge",
    "cancel_family_request",
    "complete_contact",
    "correct_log",
    "deactivate_family_contact",
    "ensure_default_rule",
    "forward_family_request",
    "mark_contact_missed",
    "record_log",
    "register_discharge",
    "register_family_request",
    "reschedule_contact",
    "resolve_family_request",
    "save_communication_rule",
    "set_family_consent",
    "update_family_contact",
]

MAX_RESCHEDULES = 5
MAX_ACTIVE_FAMILY_CONTACTS = 10
MAX_LOG_BACKDATE_DAYS = 90
_CLOCK_SKEW = timedelta(minutes=5)


# ── Auxiliares ──────────────────────────────────────────────────────────────


def _user(actor: AbstractBaseUser | None) -> Any:
    """Tipagem: o ator autenticado é sempre o modelo de usuário configurado."""
    return actor


def _authorize(*, clinic_id: UUID, actor: AbstractBaseUser, action: str) -> None:
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action=action)


def _audit(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    action: str,
    resource_type: str,
    resource_id: UUID | str,
    request_id: UUID,
    justification: str | None = None,
) -> None:
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        outcome="success",
        request_id=request_id,
        network_origin=None,
        justification=justification,
    )


def _publish(
    signal: Any, *, clinic_id: UUID, actor: AbstractBaseUser, **extra: Any
) -> None:
    """Publica o evento só depois que a transação confirmar."""
    transaction.on_commit(
        lambda: signal.send(
            sender=None, clinic_id=clinic_id, actor_id=actor.pk, **extra
        )
    )


def _clean_text(value: str, *, minimum: int, maximum: int, message: Any) -> str:
    text = (value or "").strip()
    if len(text) < minimum or len(text) > maximum:
        raise ValidationError(message)
    return text


def _require_patient(*, clinic_id: UUID, patient_profile_id: UUID) -> Any:
    profile = patient_profile_in_clinic(
        clinic_id=clinic_id, patient_profile_id=patient_profile_id
    )
    if profile is None:
        # Mesmo erro para "não existe" e "é de outra clínica": não revela existência.
        raise PermissionDenied
    return profile


def _lock[M: models.Model](model: type[M], *, clinic_id: UUID, pk: UUID) -> M:
    manager: Any = getattr(model, "infrastructure_objects")  # noqa: B009
    obj = manager.select_for_update().filter(pk=pk, clinic_id=clinic_id).first()
    if obj is None:
        raise PermissionDenied
    return cast(M, obj)


def _contactable_family(
    *, clinic_id: UUID, patient_profile_id: UUID, family_contact_id: UUID
) -> FamilyContact:
    contact = FamilyContact.infrastructure_objects.filter(
        pk=family_contact_id, clinic_id=clinic_id, patient_profile_id=patient_profile_id
    ).first()
    if contact is None:
        raise PermissionDenied
    if not contact.is_active:
        raise ValidationError(_("Este contato da família está inativo."))
    if not contact.consent_to_contact:
        raise ValidationError(
            _(
                "O paciente ainda não autorizou o contato com este familiar. "
                "Registre a autorização antes de continuar."
            )
        )
    return contact


# ── Régua de comunicação ────────────────────────────────────────────────────


def _clean_steps(steps: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for index, raw in enumerate(steps):
        kind = str(raw.get("kind", ""))
        if kind not in ContactKind.values:
            raise ValidationError(_("Tipo de contato inválido na régua."))
        try:
            day = int(raw.get("day") or 0)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                _("Informe os dias após a alta como número.")
            ) from exc
        if not 1 <= day <= MAX_DAY_AFTER_DISCHARGE:
            raise ValidationError(_("Os dias após a alta devem estar entre 1 e 365."))
        role = str(raw.get("responsible_role") or ResponsibleRole.ADMINISTRATIVE_STAFF)
        if role not in ResponsibleRole.values:
            raise ValidationError(_("Responsável inválido na régua."))
        if (kind, day) in seen:
            raise ValidationError(
                _("A régua não pode repetir o mesmo tipo de contato no mesmo dia.")
            )
        seen.add((kind, day))
        cleaned.append(
            {"kind": kind, "day": day, "responsible_role": role, "order": index}
        )
    if not cleaned:
        raise ValidationError(_("A régua precisa ter ao menos uma etapa."))
    if len(cleaned) > MAX_RULE_STEPS:
        raise ValidationError(_("A régua pode ter no máximo 8 etapas."))
    return sorted(cleaned, key=lambda item: (item["day"], item["kind"]))


def _create_rule(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser | None,
    name: str,
    steps: list[dict[str, Any]],
) -> CommunicationRule:
    current = (
        CommunicationRule.infrastructure_objects.select_for_update()
        .filter(clinic_id=clinic_id)
        .order_by("-version")
        .first()
    )
    if current is not None and current.is_active:
        current.is_active = False
        current.save(update_fields=("is_active", "updated_at"))
    rule = CommunicationRule.infrastructure_objects.create(
        clinic_id=clinic_id,
        name=name,
        version=(current.version + 1) if current else 1,
        is_active=True,
        created_by=_user(actor),
    )
    CommunicationRuleStep.infrastructure_objects.bulk_create(
        [
            CommunicationRuleStep(
                clinic_id=clinic_id,
                rule=rule,
                kind=step["kind"],
                day_after_discharge=step["day"],
                order=step["order"],
                responsible_role=step["responsible_role"],
            )
            for step in steps
        ]
    )
    return rule


@transaction.atomic
def ensure_default_rule(
    *, clinic_id: UUID, actor: AbstractBaseUser, request_id: UUID
) -> CommunicationRule:
    """Garante a régua padrão do PRD (ligações aos 7 e 15 dias, visita aos 15)."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    lock_clinic_for_update(clinic_id=clinic_id)
    existing = CommunicationRule.infrastructure_objects.filter(
        clinic_id=clinic_id, is_active=True
    ).first()
    if existing is not None:
        return existing
    rule = _create_rule(
        clinic_id=clinic_id,
        actor=actor,
        name=str(DEFAULT_RULE_NAME),
        steps=_clean_steps(
            {"kind": kind, "day": day} for kind, day in DEFAULT_RULE_STEPS
        ),
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="create",
        resource_type="communication_rule",
        resource_id=rule.pk,
        request_id=request_id,
    )
    _publish(rule_saved, clinic_id=clinic_id, actor=actor, rule_id=rule.pk)
    return rule


@transaction.atomic
def save_communication_rule(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    name: str,
    steps: Iterable[Mapping[str, Any]],
    request_id: UUID,
) -> CommunicationRule:
    """Cria uma nova versão da régua da clínica; altas já registradas não mudam."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE_RULES)
    lock_clinic_for_update(clinic_id=clinic_id)
    clean_name = _clean_text(
        name,
        minimum=3,
        maximum=120,
        message=_("Informe o nome da régua (3 a 120 caracteres)."),
    )
    rule = _create_rule(
        clinic_id=clinic_id, actor=actor, name=clean_name, steps=_clean_steps(steps)
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="communication_rule",
        resource_id=rule.pk,
        request_id=request_id,
    )
    _publish(rule_saved, clinic_id=clinic_id, actor=actor, rule_id=rule.pk)
    return rule


def _rule_snapshot(rule: CommunicationRule) -> dict[str, Any]:
    steps = list(
        CommunicationRuleStep.infrastructure_objects.filter(rule=rule).order_by(
            "day_after_discharge", "order", "kind"
        )
    )
    return {
        "rule_id": str(rule.pk),
        "name": rule.name,
        "version": rule.version,
        "steps": [
            {
                "kind": step.kind,
                "day": step.day_after_discharge,
                "responsible_role": step.responsible_role,
                "order": step.order,
            }
            for step in steps
        ],
    }


# ── Alta e contatos pós-alta ────────────────────────────────────────────────


@transaction.atomic
def register_discharge(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    patient_profile_id: UUID,
    discharge_date: date,
    request_id: UUID,
    notes: str = "",
) -> Discharge:
    """Registra a alta e gera a agenda de contatos pela régua vigente da clínica."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    lock_clinic_for_update(clinic_id=clinic_id)
    _require_patient(clinic_id=clinic_id, patient_profile_id=patient_profile_id)

    today = timezone.localdate()
    if discharge_date > today:
        raise ValidationError(_("A data da alta não pode ser futura."))
    if discharge_date < today - timedelta(days=MAX_BACKDATE_DAYS):
        raise ValidationError(_("A data da alta não pode ser anterior a 365 dias."))
    clean_notes = (notes or "").strip()
    if len(clean_notes) > 500:
        raise ValidationError(_("As observações da alta aceitam até 500 caracteres."))
    if Discharge.infrastructure_objects.filter(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        status=DischargeStatus.ACTIVE,
    ).exists():
        raise ValidationError(_("Este paciente já tem uma alta em acompanhamento."))

    rule = ensure_default_rule(clinic_id=clinic_id, actor=actor, request_id=request_id)
    snapshot = _rule_snapshot(rule)
    discharge = Discharge.infrastructure_objects.create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        discharge_date=discharge_date,
        rule=rule,
        rule_snapshot=snapshot,
        notes=clean_notes,
        registered_by=_user(actor),
    )
    AftercareContact.infrastructure_objects.bulk_create(
        [
            AftercareContact(
                clinic_id=clinic_id,
                discharge=discharge,
                kind=step["kind"],
                day_after_discharge=step["day"],
                due_date=discharge_date + timedelta(days=step["day"]),
                original_due_date=discharge_date + timedelta(days=step["day"]),
                responsible_role=step["responsible_role"],
            )
            for step in snapshot["steps"]
        ]
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="create",
        resource_type="discharge",
        resource_id=discharge.pk,
        request_id=request_id,
    )
    _publish(
        discharge_registered,
        clinic_id=clinic_id,
        actor=actor,
        discharge_id=discharge.pk,
    )
    return discharge


@transaction.atomic
def cancel_discharge(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    discharge_id: UUID,
    reason: str,
    request_id: UUID,
) -> Discharge:
    """Cancela uma alta registrada por engano e os contatos ainda agendados."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    discharge = _lock(Discharge, clinic_id=clinic_id, pk=discharge_id)
    if discharge.status != DischargeStatus.ACTIVE:
        raise ValidationError(
            _("Somente uma alta em acompanhamento pode ser cancelada.")
        )
    clean_reason = _clean_text(
        reason,
        minimum=3,
        maximum=255,
        message=_("Informe o motivo do cancelamento (3 a 255 caracteres)."),
    )
    discharge.status = DischargeStatus.CANCELED
    discharge.canceled_at = timezone.now()
    discharge.canceled_by = _user(actor)
    discharge.cancel_reason = clean_reason
    discharge.save(
        update_fields=(
            "status",
            "canceled_at",
            "canceled_by",
            "cancel_reason",
            "updated_at",
        )
    )
    AftercareContact.infrastructure_objects.filter(
        clinic_id=clinic_id, discharge=discharge, status=ContactStatus.SCHEDULED
    ).update(status=ContactStatus.CANCELED, updated_at=timezone.now())
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="discharge",
        resource_id=discharge.pk,
        request_id=request_id,
        justification=clean_reason,
    )
    _publish(
        discharge_canceled, clinic_id=clinic_id, actor=actor, discharge_id=discharge.pk
    )
    return discharge


def _close_discharge_if_finished(discharge: Discharge) -> None:
    pending = AftercareContact.infrastructure_objects.filter(
        discharge=discharge, status=ContactStatus.SCHEDULED
    ).exists()
    if not pending and discharge.status == DischargeStatus.ACTIVE:
        discharge.status = DischargeStatus.COMPLETED
        discharge.save(update_fields=("status", "updated_at"))


def _scheduled_contact(*, clinic_id: UUID, contact_id: UUID) -> AftercareContact:
    contact = _lock(AftercareContact, clinic_id=clinic_id, pk=contact_id)
    if contact.status != ContactStatus.SCHEDULED:
        raise ValidationError(_("Este contato já foi concluído ou cancelado."))
    discharge = Discharge.infrastructure_objects.get(pk=contact.discharge_id)
    if discharge.status != DischargeStatus.ACTIVE:
        raise ValidationError(
            _("A alta deste contato não está mais em acompanhamento.")
        )
    return contact


@transaction.atomic
def complete_contact(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    contact_id: UUID,
    outcome: str,
    request_id: UUID,
    notes: str = "",
    family_contact_id: UUID | None = None,
) -> AftercareContact:
    """Conclui uma ligação ou visita da régua e, se envolveu a família, a registra."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _scheduled_contact(clinic_id=clinic_id, contact_id=contact_id)
    allowed = CALL_OUTCOMES if contact.kind == ContactKind.CALL else VISIT_OUTCOMES
    if outcome not in allowed:
        raise ValidationError(_("Resultado inválido para este tipo de contato."))
    clean_notes = (notes or "").strip()
    if len(clean_notes) > MAX_NOTES_LENGTH:
        raise ValidationError(_("As observações aceitam até 1000 caracteres."))

    discharge = Discharge.infrastructure_objects.select_related("patient_profile").get(
        pk=contact.discharge_id
    )
    family = None
    if family_contact_id is not None:
        family = _contactable_family(
            clinic_id=clinic_id,
            patient_profile_id=discharge.patient_profile_id,
            family_contact_id=family_contact_id,
        )

    now = timezone.now()
    contact.outcome = outcome
    contact.status = (
        ContactStatus.DONE if outcome in SUCCESS_OUTCOMES else ContactStatus.MISSED
    )
    contact.completed_at = now
    contact.completed_by = _user(actor)
    contact.notes = clean_notes
    contact.save(
        update_fields=(
            "outcome",
            "status",
            "completed_at",
            "completed_by",
            "notes",
            "updated_at",
        )
    )
    if family is not None:
        label = ContactOutcome(outcome).label
        ConciergeLog.infrastructure_objects.create(
            clinic_id=clinic_id,
            patient_profile_id=discharge.patient_profile_id,
            family_contact=family,
            aftercare_contact=contact,
            channel=LogChannel.CALL
            if contact.kind == ContactKind.CALL
            else LogChannel.VISIT,
            direction=LogDirection.OUTBOUND,
            occurred_at=now,
            summary=f"{label}. {clean_notes}".strip(),
            recorded_by=_user(actor),
        )
    _close_discharge_if_finished(discharge)
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="aftercare_contact",
        resource_id=contact.pk,
        request_id=request_id,
    )
    _publish(
        aftercare_contact_completed,
        clinic_id=clinic_id,
        actor=actor,
        contact_id=contact.pk,
    )
    return contact


@transaction.atomic
def reschedule_contact(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    contact_id: UUID,
    new_due_date: date,
    reason: str,
    request_id: UUID,
) -> AftercareContact:
    """Muda a data prevista de um contato agendado (até 5 vezes), com motivo."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _scheduled_contact(clinic_id=clinic_id, contact_id=contact_id)
    clean_reason = _clean_text(
        reason,
        minimum=3,
        maximum=255,
        message=_("Informe o motivo do reagendamento (3 a 255 caracteres)."),
    )
    today = timezone.localdate()
    if new_due_date < today:
        raise ValidationError(_("A nova data não pode estar no passado."))
    discharge = Discharge.infrastructure_objects.get(pk=contact.discharge_id)
    if new_due_date > discharge.discharge_date + timedelta(
        days=MAX_DAY_AFTER_DISCHARGE
    ):
        raise ValidationError(_("A nova data excede 365 dias após a alta."))
    if contact.reschedule_count >= MAX_RESCHEDULES:
        raise ValidationError(_("Este contato já foi reagendado o máximo de vezes."))
    previous = contact.due_date
    contact.due_date = new_due_date
    contact.reschedule_count += 1
    contact.save(update_fields=("due_date", "reschedule_count", "updated_at"))
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="aftercare_contact",
        resource_id=contact.pk,
        request_id=request_id,
        justification=(
            f"{previous.isoformat()} -> {new_due_date.isoformat()}: {clean_reason}"
        ),
    )
    _publish(
        aftercare_contact_rescheduled,
        clinic_id=clinic_id,
        actor=actor,
        contact_id=contact.pk,
    )
    return contact


@transaction.atomic
def mark_contact_missed(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    contact_id: UUID,
    notes: str,
    request_id: UUID,
) -> AftercareContact:
    """Encerra como não realizado um contato cuja data já passou."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _scheduled_contact(clinic_id=clinic_id, contact_id=contact_id)
    if contact.due_date > timezone.localdate():
        raise ValidationError(
            _("Só é possível encerrar como não realizado após a data prevista.")
        )
    clean_notes = _clean_text(
        notes,
        minimum=3,
        maximum=MAX_NOTES_LENGTH,
        message=_("Informe o motivo (3 a 1000 caracteres)."),
    )
    contact.status = ContactStatus.MISSED
    contact.notes = clean_notes
    contact.completed_at = timezone.now()
    contact.completed_by = _user(actor)
    contact.save(
        update_fields=("status", "notes", "completed_at", "completed_by", "updated_at")
    )
    discharge = Discharge.infrastructure_objects.get(pk=contact.discharge_id)
    _close_discharge_if_finished(discharge)
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="aftercare_contact",
        resource_id=contact.pk,
        request_id=request_id,
    )
    _publish(
        aftercare_contact_missed,
        clinic_id=clinic_id,
        actor=actor,
        contact_id=contact.pk,
    )
    return contact


# ── Família ─────────────────────────────────────────────────────────────────


def _clean_family_fields(
    *, full_name: str, relationship: str, phone: str, email: str
) -> tuple[str, str, str, str]:
    name = _clean_text(
        full_name,
        minimum=2,
        maximum=255,
        message=_("Informe o nome do familiar (2 a 255 caracteres)."),
    )
    relation = _clean_text(
        relationship,
        minimum=2,
        maximum=100,
        message=_("Informe o parentesco (2 a 100 caracteres)."),
    )
    clean_phone = "".join(
        ch for ch in (phone or "") if ch.isdigit() or ch in "+() -"
    ).strip()
    clean_email = (email or "").strip().lower()
    if not clean_phone and not clean_email:
        raise ValidationError(_("Informe ao menos um telefone ou e-mail."))
    if clean_phone and sum(ch.isdigit() for ch in clean_phone) < 8:
        raise ValidationError(_("Telefone inválido: informe ao menos 8 dígitos."))
    if clean_email:
        try:
            validate_email(clean_email)
        except ValidationError as exc:
            raise ValidationError(_("E-mail inválido.")) from exc
    return name, relation, clean_phone, clean_email


@transaction.atomic
def add_family_contact(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    patient_profile_id: UUID,
    full_name: str,
    relationship: str,
    request_id: UUID,
    phone: str = "",
    email: str = "",
    is_primary: bool = False,
    consent_to_contact: bool = False,
    consent_note: str = "",
) -> FamilyContact:
    """Cadastra um familiar. O contato só é liberado com a autorização do paciente."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    lock_clinic_for_update(clinic_id=clinic_id)
    _require_patient(clinic_id=clinic_id, patient_profile_id=patient_profile_id)
    name, relation, clean_phone, clean_email = _clean_family_fields(
        full_name=full_name, relationship=relationship, phone=phone, email=email
    )
    if (
        FamilyContact.infrastructure_objects.filter(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id, is_active=True
        ).count()
        >= MAX_ACTIVE_FAMILY_CONTACTS
    ):
        raise ValidationError(
            _("Limite de 10 contatos da família ativos por paciente.")
        )
    note = (consent_note or "").strip()
    if consent_to_contact and len(note) < 3:
        raise ValidationError(
            _(
                "Registre como a autorização do paciente foi obtida "
                "(ex.: termo assinado)."
            )
        )
    if is_primary:
        FamilyContact.infrastructure_objects.filter(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id, is_primary=True
        ).update(is_primary=False, updated_at=timezone.now())
    contact = FamilyContact.infrastructure_objects.create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        full_name=name,
        relationship=relation,
        phone=clean_phone,
        email=clean_email,
        is_primary=is_primary,
        consent_to_contact=consent_to_contact,
        consent_recorded_at=timezone.now() if consent_to_contact else None,
        consent_recorded_by=_user(actor) if consent_to_contact else None,
        consent_note=note[:255] if consent_to_contact else "",
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="create",
        resource_type="family_contact",
        resource_id=contact.pk,
        request_id=request_id,
    )
    _publish(
        family_contact_saved,
        clinic_id=clinic_id,
        actor=actor,
        family_contact_id=contact.pk,
    )
    return contact


@transaction.atomic
def update_family_contact(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_contact_id: UUID,
    full_name: str,
    relationship: str,
    request_id: UUID,
    phone: str = "",
    email: str = "",
    is_primary: bool = False,
) -> FamilyContact:
    """Atualiza dados de contato. A autorização do paciente tem serviço próprio."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _lock(FamilyContact, clinic_id=clinic_id, pk=family_contact_id)
    if not contact.is_active:
        raise ValidationError(_("Este contato da família está inativo."))
    name, relation, clean_phone, clean_email = _clean_family_fields(
        full_name=full_name, relationship=relationship, phone=phone, email=email
    )
    if is_primary and not contact.is_primary:
        FamilyContact.infrastructure_objects.filter(
            clinic_id=clinic_id,
            patient_profile_id=contact.patient_profile_id,
            is_primary=True,
        ).update(is_primary=False, updated_at=timezone.now())
    contact.full_name = name
    contact.relationship = relation
    contact.phone = clean_phone
    contact.email = clean_email
    contact.is_primary = is_primary
    contact.save(
        update_fields=(
            "full_name",
            "relationship",
            "phone",
            "email",
            "is_primary",
            "updated_at",
        )
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="family_contact",
        resource_id=contact.pk,
        request_id=request_id,
    )
    _publish(
        family_contact_saved,
        clinic_id=clinic_id,
        actor=actor,
        family_contact_id=contact.pk,
    )
    return contact


def _cancel_open_requests_for(
    *, clinic_id: UUID, family_contact_id: UUID, reason: str
) -> int:
    return FamilyRequest.infrastructure_objects.filter(
        clinic_id=clinic_id,
        family_contact_id=family_contact_id,
        status__in=OPEN_REQUEST_STATUSES,
    ).update(
        status=RequestStatus.CANCELED,
        resolution_note=reason,
        resolved_at=timezone.now(),
        updated_at=timezone.now(),
    )


@transaction.atomic
def set_family_consent(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_contact_id: UUID,
    granted: bool,
    note: str,
    request_id: UUID,
) -> FamilyContact:
    """Registra a concessão ou a revogação da autorização do paciente."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _lock(FamilyContact, clinic_id=clinic_id, pk=family_contact_id)
    clean_note = _clean_text(
        note,
        minimum=3,
        maximum=255,
        message=_(
            "Registre como a decisão do paciente foi obtida (3 a 255 caracteres)."
        ),
    )
    contact.consent_to_contact = granted
    contact.consent_recorded_at = timezone.now()
    contact.consent_recorded_by = _user(actor)
    contact.consent_note = clean_note
    contact.save(
        update_fields=(
            "consent_to_contact",
            "consent_recorded_at",
            "consent_recorded_by",
            "consent_note",
            "updated_at",
        )
    )
    if not granted:
        _cancel_open_requests_for(
            clinic_id=clinic_id,
            family_contact_id=contact.pk,
            reason=str(_("Autorização do paciente revogada.")),
        )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="consent_accept" if granted else "consent_revoke",
        resource_type="family_contact",
        resource_id=contact.pk,
        request_id=request_id,
        justification=clean_note,
    )
    _publish(
        family_consent_changed,
        clinic_id=clinic_id,
        actor=actor,
        family_contact_id=contact.pk,
        granted=granted,
    )
    return contact


@transaction.atomic
def deactivate_family_contact(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_contact_id: UUID,
    request_id: UUID,
) -> FamilyContact:
    """Inativa o familiar (o histórico permanece) e cancela pedidos em aberto."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    contact = _lock(FamilyContact, clinic_id=clinic_id, pk=family_contact_id)
    contact.is_active = False
    contact.is_primary = False
    contact.save(update_fields=("is_active", "is_primary", "updated_at"))
    _cancel_open_requests_for(
        clinic_id=clinic_id,
        family_contact_id=contact.pk,
        reason=str(_("Contato da família inativado.")),
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="family_contact",
        resource_id=contact.pk,
        request_id=request_id,
    )
    _publish(
        family_contact_saved,
        clinic_id=clinic_id,
        actor=actor,
        family_contact_id=contact.pk,
    )
    return contact


# ── Registro do concierge (somente de acréscimo) ────────────────────────────


def _check_occurred_at(occurred_at: datetime | None) -> datetime:
    now = timezone.now()
    moment = occurred_at or now
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    if moment > now + _CLOCK_SKEW:
        raise ValidationError(_("A data e hora do contato não podem estar no futuro."))
    if moment < now - timedelta(days=MAX_LOG_BACKDATE_DAYS):
        raise ValidationError(_("O contato não pode ser anterior a 90 dias."))
    return moment


@transaction.atomic
def record_log(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    patient_profile_id: UUID,
    family_contact_id: UUID,
    channel: str,
    summary: str,
    request_id: UUID,
    direction: str = LogDirection.OUTBOUND.value,
    occurred_at: datetime | None = None,
    family_request_id: UUID | None = None,
) -> ConciergeLog:
    """Registra um contato com a família. Não há edição nem exclusão depois."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    _require_patient(clinic_id=clinic_id, patient_profile_id=patient_profile_id)
    family = _contactable_family(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        family_contact_id=family_contact_id,
    )
    if channel not in LogChannel.values:
        raise ValidationError(_("Canal de contato inválido."))
    if direction not in LogDirection.values:
        raise ValidationError(_("Sentido do contato inválido."))
    text = _clean_text(
        summary,
        minimum=MIN_SUMMARY_LENGTH,
        maximum=MAX_SUMMARY_LENGTH,
        message=_(
            "Descreva o contato (3 a 2000 caracteres). Não registre conteúdo clínico."
        ),
    )
    moment = _check_occurred_at(occurred_at)
    log = ConciergeLog.infrastructure_objects.create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        family_contact=family,
        family_request_id=family_request_id,
        channel=channel,
        direction=direction,
        occurred_at=moment,
        summary=text,
        recorded_by=_user(actor),
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="create",
        resource_type="concierge_log",
        resource_id=log.pk,
        request_id=request_id,
    )
    _publish(concierge_log_recorded, clinic_id=clinic_id, actor=actor, log_id=log.pk)
    return log


@transaction.atomic
def correct_log(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    log_id: UUID,
    new_summary: str,
    reason: str,
    request_id: UUID,
) -> ConciergeLog:
    """Corrige um registro criando outro que aponta para o original (que permanece)."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    original = (
        ConciergeLog.infrastructure_objects.select_for_update()
        .filter(pk=log_id, clinic_id=clinic_id)
        .first()
    )
    if original is None:
        raise PermissionDenied
    if ConciergeLog.infrastructure_objects.filter(corrects_id=original.pk).exists():
        raise ValidationError(
            _("Este registro já foi corrigido. Corrija a versão mais recente.")
        )
    clean_reason = _clean_text(
        reason,
        minimum=3,
        maximum=255,
        message=_("Informe o motivo da correção (3 a 255 caracteres)."),
    )
    text = _clean_text(
        new_summary,
        minimum=MIN_SUMMARY_LENGTH,
        maximum=MAX_SUMMARY_LENGTH,
        message=_(
            "Descreva o contato (3 a 2000 caracteres). Não registre conteúdo clínico."
        ),
    )
    corrected = ConciergeLog.infrastructure_objects.create(
        clinic_id=clinic_id,
        patient_profile_id=original.patient_profile_id,
        family_contact_id=original.family_contact_id,
        aftercare_contact_id=original.aftercare_contact_id,
        family_request_id=original.family_request_id,
        corrects=original,
        channel=original.channel,
        direction=original.direction,
        occurred_at=original.occurred_at,
        summary=text,
        recorded_by=_user(actor),
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="concierge_log",
        resource_id=corrected.pk,
        request_id=request_id,
        justification=clean_reason,
    )
    _publish(
        concierge_log_recorded, clinic_id=clinic_id, actor=actor, log_id=corrected.pk
    )
    return corrected


# ── Pedidos do paciente à família ───────────────────────────────────────────


@transaction.atomic
def register_family_request(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    patient_profile_id: UUID,
    family_contact_id: UUID,
    kind: str,
    description: str,
    request_id: UUID,
    requested_at: datetime | None = None,
) -> FamilyRequest:
    """Registra um pedido feito pelo paciente a um familiar (ainda NÃO encaminhado)."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    _require_patient(clinic_id=clinic_id, patient_profile_id=patient_profile_id)
    family = _contactable_family(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        family_contact_id=family_contact_id,
    )
    if kind not in RequestKind.values:
        raise ValidationError(_("Tipo de pedido inválido."))
    text = _clean_text(
        description,
        minimum=3,
        maximum=1000,
        message=_("Descreva o pedido (3 a 1000 caracteres)."),
    )
    moment = _check_occurred_at(requested_at)
    family_request = FamilyRequest.infrastructure_objects.create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        family_contact=family,
        kind=kind,
        description=text,
        requested_at=moment,
        recorded_by=_user(actor),
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="create",
        resource_type="family_request",
        resource_id=family_request.pk,
        request_id=request_id,
    )
    _publish(
        family_request_registered,
        clinic_id=clinic_id,
        actor=actor,
        family_request_id=family_request.pk,
    )
    return family_request


def _open_request(*, clinic_id: UUID, request_pk: UUID) -> FamilyRequest:
    family_request = _lock(FamilyRequest, clinic_id=clinic_id, pk=request_pk)
    if family_request.status not in OPEN_REQUEST_STATUSES:
        raise ValidationError(_("Este pedido já foi encerrado."))
    return family_request


@transaction.atomic
def forward_family_request(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_request_id: UUID,
    channel: str,
    summary: str,
    request_id: UUID,
    occurred_at: datetime | None = None,
) -> FamilyRequest:
    """Registra que a família foi contatada sobre o pedido (gera registro)."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    family_request = _open_request(clinic_id=clinic_id, request_pk=family_request_id)
    if family_request.status != RequestStatus.OPEN:
        raise ValidationError(_("O encaminhamento deste pedido já foi registrado."))
    log = record_log(
        clinic_id=clinic_id,
        actor=actor,
        patient_profile_id=family_request.patient_profile_id,
        family_contact_id=family_request.family_contact_id,
        channel=channel,
        summary=summary,
        request_id=request_id,
        occurred_at=occurred_at,
        family_request_id=family_request.pk,
    )
    family_request.status = RequestStatus.FORWARDED
    family_request.forwarded_at = log.occurred_at
    family_request.save(update_fields=("status", "forwarded_at", "updated_at"))
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="family_request",
        resource_id=family_request.pk,
        request_id=request_id,
    )
    _publish(
        family_request_changed,
        clinic_id=clinic_id,
        actor=actor,
        family_request_id=family_request.pk,
    )
    return family_request


@transaction.atomic
def resolve_family_request(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_request_id: UUID,
    fulfilled: bool,
    note: str,
    request_id: UUID,
) -> FamilyRequest:
    """Conclui como atendido ou não atendido. Exige o encaminhamento registrado."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    family_request = _open_request(clinic_id=clinic_id, request_pk=family_request_id)
    if family_request.status != RequestStatus.FORWARDED:
        raise ValidationError(
            _(
                "Registre primeiro o encaminhamento à família "
                "antes de concluir o pedido."
            )
        )
    clean_note = _clean_text(
        note,
        minimum=3,
        maximum=500,
        message=_("Informe o desfecho (3 a 500 caracteres)."),
    )
    family_request.status = (
        RequestStatus.FULFILLED if fulfilled else RequestStatus.DECLINED
    )
    family_request.resolved_at = timezone.now()
    family_request.resolved_by = _user(actor)
    family_request.resolution_note = clean_note
    family_request.save(
        update_fields=(
            "status",
            "resolved_at",
            "resolved_by",
            "resolution_note",
            "updated_at",
        )
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="family_request",
        resource_id=family_request.pk,
        request_id=request_id,
    )
    _publish(
        family_request_changed,
        clinic_id=clinic_id,
        actor=actor,
        family_request_id=family_request.pk,
    )
    return family_request


@transaction.atomic
def cancel_family_request(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    family_request_id: UUID,
    reason: str,
    request_id: UUID,
) -> FamilyRequest:
    """Cancela um pedido ainda aberto ou encaminhado."""
    _authorize(clinic_id=clinic_id, actor=actor, action=ACTION_MANAGE)
    family_request = _open_request(clinic_id=clinic_id, request_pk=family_request_id)
    clean_reason = _clean_text(
        reason,
        minimum=3,
        maximum=500,
        message=_("Informe o motivo (3 a 500 caracteres)."),
    )
    family_request.status = RequestStatus.CANCELED
    family_request.resolved_at = timezone.now()
    family_request.resolved_by = _user(actor)
    family_request.resolution_note = clean_reason
    family_request.save(
        update_fields=(
            "status",
            "resolved_at",
            "resolved_by",
            "resolution_note",
            "updated_at",
        )
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        action="update",
        resource_type="family_request",
        resource_id=family_request.pk,
        request_id=request_id,
        justification=clean_reason,
    )
    _publish(
        family_request_changed,
        clinic_id=clinic_id,
        actor=actor,
        family_request_id=family_request.pk,
    )
    return family_request
