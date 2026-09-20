"""Comandos transacionais; locks seguem clínica → recurso → auditoria."""

from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from audit.services import record_audit_event
from clinics.policies import has_active_clinic_role
from clinics.services import authorized_active_clinic, lock_clinic_for_update
from core.services import Service as Service

from .models import (
    ClinicalRecord,
    Encounter,
    Enrollment,
    OperationGrant,
    Product,
    StockLot,
    StockMovement,
    TherapySession,
)
from .policies import (
    CAPABILITIES,
    require_capability,
    require_encounter_access,
    require_patient_access,
)


def _audit(*, clinic_id, actor, resource, action):
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action=action,
        resource_type=resource._meta.model_name,
        resource_id=str(resource.pk),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
    )


@transaction.atomic
def set_grant(*, clinic_id, actor, user_id, capability, enabled):
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action="clinic.manage")
    lock_clinic_for_update(clinic_id=clinic_id)
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action="clinic.manage")
    if capability not in CAPABILITIES or type(enabled) is not bool:
        raise ValidationError("Grant inválido.")
    if not enabled:
        # Revogar não depende de o alvo conservar os requisitos da concessão.
        grant = (
            OperationGrant.objects.for_clinic(clinic_id)
            .filter(user_id=user_id, capability=capability)
            .first()
        )
        if grant is None:
            raise ValidationError("Grant indisponível nesta clínica.")
        grant.enabled = False
        grant.authorized_by_id = actor.pk
        grant.save(update_fields=("enabled", "authorized_by", "updated_at"))
        _audit(
            clinic_id=clinic_id, actor=actor, resource=grant, action="operations.grant"
        )
        return grant
    roles = (
        ("therapist",)
        if capability.startswith(("record.", "encounter.", "session."))
        else ("clinic_admin", "administrative_staff", "therapist")
    )
    if not any(
        has_active_clinic_role(
            clinic_id=clinic_id,
            user_id=user_id,
            role=role,
            on_date=timezone.localdate(),
        )
        for role in roles
    ):
        raise ValidationError("Responsável sem papel ativo compatível na clínica.")
    grant, _ = OperationGrant.objects.for_clinic(clinic_id).update_or_create(
        user_id=user_id,
        capability=capability,
        defaults={
            "clinic_id": clinic_id,
            "enabled": enabled,
            "authorized_by_id": actor.pk,
        },
    )
    _audit(clinic_id=clinic_id, actor=actor, resource=grant, action="operations.grant")
    return grant


@transaction.atomic
def create_product(*, clinic_id, actor, name, sku):
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    product = Product(clinic_id=clinic_id, name=name, sku=sku)
    product.full_clean(
        validate_unique=False, validate_constraints=False, exclude=("clinic",)
    )
    product.save(force_insert=True)
    _audit(
        clinic_id=clinic_id, actor=actor, resource=product, action="operations.product"
    )
    return product


class ConflictError(ValueError):
    """Conflito de estado, sem conteúdo sensível na mensagem."""


Conflict = ConflictError  # Alias público estável do contrato HTTP/serviços.


def _object(model, clinic_id, object_id):
    result = model.objects.for_clinic(clinic_id).filter(pk=object_id).first()
    if result is None:
        raise ValidationError("Referência indisponível nesta clínica.")
    return result


def _patient(clinic_id, patient_id):
    if not has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=patient_id,
        role="patient",
        on_date=timezone.localdate(),
    ):
        raise ValidationError("Paciente indisponível nesta clínica.")


def _text(value, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValidationError("Texto inválido ou acima do limite.")
    return value.strip()


@transaction.atomic
def create_lot(*, clinic_id, actor, product_id, code, expires_on):
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    _object(Product, clinic_id, product_id)
    lot = StockLot(
        clinic_id=clinic_id,
        product_id=product_id,
        code=_text(code, 64),
        expires_on=expires_on,
        balance=0,
    )
    lot.full_clean(
        validate_unique=False, validate_constraints=False, exclude=("clinic", "product")
    )
    lot.save(force_insert=True)
    _audit(clinic_id=clinic_id, actor=actor, resource=lot, action="operations.lot")
    return lot


@transaction.atomic
def move_stock(*, clinic_id, actor, lot_id, quantity, direction, key, patient_id=None):
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="pharmacy.write")
    if (
        type(quantity) is not int
        or not 1 <= quantity <= 1000000
        or direction not in {"in", "out"}
    ):
        raise ValidationError("Quantidade ou direção inválida.")
    _text(key, 80)  # Validar sem normalizar a chave idempotente.
    if direction == "out":
        _patient(clinic_id, patient_id)
    elif patient_id is not None:
        raise ValidationError("Entrada não recebe paciente.")
    lot = _object(StockLot, clinic_id, lot_id)
    previous = StockMovement.objects.for_clinic(clinic_id).filter(key=key).first()
    if previous:
        if (
            str(previous.lot_id),
            previous.quantity,
            previous.direction,
            str(previous.patient_id),
            previous.actor_id,
        ) != (str(lot.pk), quantity, direction, str(patient_id), actor.pk):
            raise Conflict("idempotency_conflict")
        return previous
    if direction == "out":
        if lot.expires_on < timezone.localdate():
            raise Conflict("expired_lot")
        if lot.balance < quantity:
            raise Conflict("insufficient_stock")
        lot.balance -= quantity
    else:
        if lot.balance + quantity > 2147483647:
            raise ValidationError("Saldo acima do limite.")
        lot.balance += quantity
    lot.save(update_fields=("balance", "updated_at"))
    movement = StockMovement.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        lot=lot,
        actor_id=actor.pk,
        patient_id=patient_id,
        quantity=quantity,
        direction=direction,
        key=key,
    )
    _audit(
        clinic_id=clinic_id, actor=actor, resource=movement, action="operations.stock"
    )
    return movement


def _future(value):
    from datetime import datetime

    if (
        not isinstance(value, datetime)
        or timezone.is_naive(value)
        or value <= timezone.now()
    ):
        raise ValidationError("Agendamento requer data futura com fuso horário.")
    return value


@transaction.atomic
def schedule_encounter(*, clinic_id, actor, patient_id, starts_at):
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=patient_id,
        capability="encounter.manage",
    )
    lock_clinic_for_update(clinic_id=clinic_id)
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=patient_id,
        capability="encounter.manage",
    )
    encounter = Encounter.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_id=patient_id,
        professional_id=actor.pk,
        starts_at=_future(starts_at),
        status="agendado",
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        resource=encounter,
        action="operations.encounter",
    )
    return encounter


TRANSITIONS = {
    "agendado": {"em_atendimento", "cancelado"},
    "em_atendimento": {"concluido", "cancelado"},
    "concluido": set(),
    "cancelado": set(),
}


@transaction.atomic
def transition_encounter(*, clinic_id, actor, encounter_id, status):
    require_capability(clinic_id=clinic_id, actor=actor, capability="encounter.manage")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="encounter.manage")
    encounter = _object(Encounter, clinic_id, encounter_id)
    require_encounter_access(
        clinic_id=clinic_id,
        actor=actor,
        encounter=encounter,
        capability="encounter.manage",
    )
    if status not in TRANSITIONS[encounter.status]:
        raise Conflict("invalid_transition")
    encounter.status = status
    encounter.save(update_fields=("status", "updated_at"))
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        resource=encounter,
        action="operations.transition",
    )
    return encounter


@transaction.atomic
def append_record(*, clinic_id, actor, encounter_id, content):
    require_capability(clinic_id=clinic_id, actor=actor, capability="record.write")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="record.write")
    encounter = _object(Encounter, clinic_id, encounter_id)
    require_encounter_access(
        clinic_id=clinic_id,
        actor=actor,
        encounter=encounter,
        capability="record.write",
        consent=True,
    )
    if encounter.status != "em_atendimento":
        raise Conflict("invalid_record_state")
    record = ClinicalRecord.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        encounter=encounter,
        author_id=actor.pk,
        content=_text(content, 8000),
    )
    _audit(
        clinic_id=clinic_id, actor=actor, resource=record, action="operations.record"
    )
    return record


MODALITIES = ("psicoterapia", "exercicio", "yoga", "arteterapia")


@transaction.atomic
def schedule_session(*, clinic_id, actor, kind, modality, capacity, starts_at, ends_at):
    require_capability(clinic_id=clinic_id, actor=actor, capability="session.manage")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="session.manage")
    _future(starts_at)
    _future(ends_at)
    if (
        kind not in {"individual", "grupo"}
        or modality not in MODALITIES
        or type(capacity) is not int
        or not 1 <= capacity <= 100
        or (kind == "individual" and capacity != 1)
        or ends_at <= starts_at
        or (ends_at - starts_at).total_seconds() > 28800
    ):
        raise ValidationError("Sessão inválida (capacidade, modalidade ou horário).")
    if (
        TherapySession.objects.for_clinic(clinic_id)
        .filter(professional_id=actor.pk, starts_at__lt=ends_at, ends_at__gt=starts_at)
        .exists()
    ):
        raise Conflict("schedule_overlap")
    session = TherapySession.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        professional_id=actor.pk,
        kind=kind,
        modality=modality,
        capacity=capacity,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    _audit(
        clinic_id=clinic_id, actor=actor, resource=session, action="operations.session"
    )
    return session


def _session_owner(clinic_id, actor, session):
    require_capability(clinic_id=clinic_id, actor=actor, capability="session.manage")
    if session.clinic_id != clinic_id or session.professional_id != actor.pk:
        raise PermissionDenied("Sessão indisponível.")


@transaction.atomic
def enroll_patient(*, clinic_id, actor, session_id, patient_id):
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=patient_id,
        capability="session.manage",
    )
    lock_clinic_for_update(clinic_id=clinic_id)
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=patient_id,
        capability="session.manage",
    )
    session = _object(TherapySession, clinic_id, session_id)
    _session_owner(clinic_id, actor, session)
    enrollments = Enrollment.objects.for_clinic(clinic_id).filter(session_id=session.pk)
    previous = enrollments.filter(patient_id=patient_id).first()
    if previous:
        return previous
    if session.starts_at <= timezone.now():
        raise Conflict("session_started")
    if enrollments.count() >= session.capacity:
        raise Conflict("capacity_reached")
    if (
        Enrollment.objects.for_clinic(clinic_id)
        .filter(
            patient_id=patient_id,
            session__starts_at__lt=session.ends_at,
            session__ends_at__gt=session.starts_at,
        )
        .exists()
    ):
        raise Conflict("patient_schedule_overlap")
    enrollment = enrollments.create(
        clinic_id=clinic_id, session=session, patient_id=patient_id, status="agendado"
    )
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        resource=enrollment,
        action="operations.enrollment",
    )
    return enrollment


@transaction.atomic
def set_attendance(*, clinic_id, actor, enrollment_id, status):
    require_capability(clinic_id=clinic_id, actor=actor, capability="session.manage")
    lock_clinic_for_update(clinic_id=clinic_id)
    require_capability(clinic_id=clinic_id, actor=actor, capability="session.manage")
    enrollment = _object(Enrollment, clinic_id, enrollment_id)
    session = _object(TherapySession, clinic_id, enrollment.session_id)
    _session_owner(clinic_id, actor, session)
    require_patient_access(
        clinic_id=clinic_id,
        actor=actor,
        patient_id=enrollment.patient_id,
        capability="session.manage",
    )
    if status not in {"presente", "ausente"}:
        raise ValidationError("Presença inválida.")
    enrollment.status = status
    enrollment.save(update_fields=("status", "updated_at"))
    _audit(
        clinic_id=clinic_id,
        actor=actor,
        resource=enrollment,
        action="operations.attendance",
    )
    return enrollment
