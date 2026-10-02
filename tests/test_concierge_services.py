"""Concierge e acompanhamento pós-alta: serviços, autorização, isolamento e cifragem."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, models
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent
from concierge import selectors, services
from concierge.contracts import (
    ContactKind,
    ContactStatus,
    DischargeStatus,
    RequestStatus,
)
from concierge.fields import decrypt_text, encrypt_text
from concierge.models import (
    AftercareContact,
    CommunicationRule,
    ConciergeLog,
    Discharge,
    FamilyContact,
    FamilyRequest,
)
from people.models import PatientProfile
from tests.aftercare_support import Stage, build_stage, make_patient

pytestmark = pytest.mark.django_db


def _discharge(
    stage: Stage, *, days_ago: int = 0, name: str = "Paciente Exemplo"
) -> tuple[PatientProfile, Discharge]:
    patient = make_patient(stage.clinic, stage.admin, name=name)
    discharge = services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        discharge_date=timezone.localdate() - timedelta(days=days_ago),
        request_id=uuid4(),
    )
    return patient, discharge


def _family(
    stage: Stage, patient: PatientProfile, *, consent: bool = True, **extra: Any
) -> FamilyContact:
    data: dict[str, Any] = {
        "full_name": "Marta Exemplo",
        "relationship": "Mãe",
        "phone": "+55 81 0000-0001",
        "email": "marta@example.test",
        "consent_to_contact": consent,
        "consent_note": "Termo assinado em consulta" if consent else "",
    }
    data.update(extra)
    return services.add_family_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        request_id=uuid4(),
        **data,
    )


def _raw(table: str, column: str, pk: object) -> str:
    """Valor cru da coluna, como está no banco (independe de SQLite/PostgreSQL)."""
    db_pk = models.UUIDField().get_db_prep_value(pk, connection)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE id = %s", [db_pk])
        return str(cursor.fetchone()[0])


def _audit(stage: Stage, resource_type: str) -> int:
    return AuditEvent.infrastructure_objects.filter(
        clinic_id=stage.clinic.pk, resource_type=resource_type
    ).count()


# ── Régua e alta ────────────────────────────────────────────────────────────


def test_first_discharge_creates_the_default_rule_from_the_prd() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage)
    rule = CommunicationRule.objects.for_clinic(stage.clinic.pk).get(is_active=True)
    steps = selectors.rule_steps(clinic_id=stage.clinic.pk, rule_id=rule.pk)
    assert [(s.kind, s.day_after_discharge) for s in steps] == [
        ("call", 7),
        ("call", 15),
        ("visit", 15),
    ]
    assert discharge.rule_id == rule.pk
    assert discharge.rule_snapshot["version"] == 1


def test_discharge_generates_the_contact_schedule_from_the_rule() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=3)
    contacts = list(
        AftercareContact.objects.for_clinic(stage.clinic.pk)
        .filter(discharge=discharge)
        .order_by("due_date", "kind")
    )
    assert [(c.kind, c.day_after_discharge) for c in contacts] == [
        ("call", 7),
        ("call", 15),
        ("visit", 15),
    ]
    for contact in contacts:
        expected = discharge.discharge_date + timedelta(
            days=contact.day_after_discharge
        )
        assert contact.due_date == contact.original_due_date == expected
        assert contact.status == ContactStatus.SCHEDULED
    assert _audit(stage, "discharge") == 1


def test_only_authorized_roles_register_discharges() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "patient_profile_id": patient.pk,
        "discharge_date": timezone.localdate(),
        "request_id": uuid4(),
    }
    with pytest.raises(PermissionDenied):
        services.register_discharge(actor=stage.therapist, **kwargs)
    with pytest.raises(PermissionDenied):
        services.register_discharge(actor=stage.other_admin, **kwargs)
    services.register_discharge(actor=stage.admin, **kwargs)  # administrador pode


def test_discharge_validations() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    base: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "patient_profile_id": patient.pk,
        "request_id": uuid4(),
    }
    today = timezone.localdate()
    with pytest.raises(ValidationError):
        services.register_discharge(discharge_date=today + timedelta(days=1), **base)
    with pytest.raises(ValidationError):
        services.register_discharge(discharge_date=today - timedelta(days=366), **base)
    with pytest.raises(ValidationError):
        services.register_discharge(discharge_date=today, notes="x" * 501, **base)
    services.register_discharge(discharge_date=today, **base)
    with pytest.raises(ValidationError, match="já tem uma alta"):
        services.register_discharge(discharge_date=today, **base)


def test_patient_from_another_clinic_is_not_revealed() -> None:
    stage = build_stage()
    foreign = make_patient(stage.other_clinic, stage.other_admin)
    with pytest.raises(PermissionDenied):
        services.register_discharge(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            patient_profile_id=foreign.pk,
            discharge_date=timezone.localdate(),
            request_id=uuid4(),
        )
    with pytest.raises(PermissionDenied):
        services.register_discharge(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            patient_profile_id=uuid4(),
            discharge_date=timezone.localdate(),
            request_id=uuid4(),
        )


def test_changing_the_rule_creates_a_new_version_without_touching_past_discharges() -> (
    None
):
    stage = build_stage()
    _patient, first = _discharge(stage)
    rule = services.save_communication_rule(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        name="Régua intensiva",
        steps=[
            {"kind": "call", "day": 3},
            {"kind": "call", "day": 10},
            {"kind": "visit", "day": 20, "responsible_role": "therapist"},
        ],
        request_id=uuid4(),
    )
    assert rule.version == 2 and rule.is_active
    rules = selectors.rule_history(clinic_id=stage.clinic.pk)
    assert [(r.version, r.is_active) for r in rules] == [(2, True), (1, False)]
    # A alta anterior mantém a agenda original (7/15/15).
    first_days = sorted(
        AftercareContact.objects.for_clinic(stage.clinic.pk)
        .filter(discharge=first)
        .values_list("day_after_discharge", flat=True)
    )
    assert first_days == [7, 15, 15]
    _other_patient, second = _discharge(stage)
    second_days = sorted(
        AftercareContact.objects.for_clinic(stage.clinic.pk)
        .filter(discharge=second)
        .values_list("day_after_discharge", flat=True)
    )
    assert second_days == [3, 10, 20]
    visit = AftercareContact.objects.for_clinic(stage.clinic.pk).get(
        discharge=second, kind=ContactKind.VISIT
    )
    assert visit.responsible_role == "therapist"


def test_only_clinic_admin_manages_the_rule_and_steps_are_validated() -> None:
    stage = build_stage()
    ok = [{"kind": "call", "day": 7}]
    for actor in (stage.staff, stage.therapist, stage.other_admin):
        with pytest.raises(PermissionDenied):
            services.save_communication_rule(
                clinic_id=stage.clinic.pk,
                actor=actor,
                name="Régua",
                steps=ok,
                request_id=uuid4(),
            )
    invalid: list[list[dict[str, Any]]] = [
        [],
        [{"kind": "sms", "day": 7}],
        [{"kind": "call", "day": 0}],
        [{"kind": "call", "day": 366}],
        [{"kind": "call", "day": "abc"}],
        [{"kind": "call", "day": 7}, {"kind": "call", "day": 7}],
        [{"kind": "call", "day": 7, "responsible_role": "patient"}],
        [{"kind": "call", "day": day} for day in range(1, 10)],
    ]
    for steps in invalid:
        with pytest.raises(ValidationError):
            services.save_communication_rule(
                clinic_id=stage.clinic.pk,
                actor=stage.admin,
                name="Régua",
                steps=steps,
                request_id=uuid4(),
            )
    with pytest.raises(ValidationError):
        services.save_communication_rule(
            clinic_id=stage.clinic.pk,
            actor=stage.admin,
            name="  ",
            steps=ok,
            request_id=uuid4(),
        )
    assert not CommunicationRule.objects.for_clinic(stage.clinic.pk).exists()


def test_cancel_discharge_cancels_scheduled_contacts() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage)
    with pytest.raises(ValidationError):
        services.cancel_discharge(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            discharge_id=discharge.pk,
            reason="x",
            request_id=uuid4(),
        )
    services.cancel_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        discharge_id=discharge.pk,
        reason="Registrada por engano",
        request_id=uuid4(),
    )
    discharge.refresh_from_db()
    assert discharge.status == DischargeStatus.CANCELED
    assert discharge.cancel_reason == "Registrada por engano"
    statuses = set(
        AftercareContact.objects.for_clinic(stage.clinic.pk)
        .filter(discharge=discharge)
        .values_list("status", flat=True)
    )
    assert statuses == {ContactStatus.CANCELED}
    with pytest.raises(ValidationError):
        services.cancel_discharge(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            discharge_id=discharge.pk,
            reason="Outra vez",
            request_id=uuid4(),
        )
    # Cancelada, a paciente pode ter nova alta.
    services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=discharge.patient_profile_id,
        discharge_date=timezone.localdate(),
        request_id=uuid4(),
    )


# ── Contatos pós-alta ───────────────────────────────────────────────────────


def _contacts(
    stage: Stage, discharge: Discharge
) -> dict[tuple[str, int], AftercareContact]:
    return {
        (c.kind, c.day_after_discharge): c
        for c in AftercareContact.objects.for_clinic(stage.clinic.pk).filter(
            discharge=discharge
        )
    }


def test_completing_every_contact_closes_the_discharge() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=20)
    contacts = _contacts(stage, discharge)
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=contacts[("call", 7)].pk,
        outcome="reached",
        notes="Paciente bem, retoma a rotina.",
        request_id=uuid4(),
    )
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=contacts[("call", 15)].pk,
        outcome="no_answer",
        request_id=uuid4(),
    )
    discharge.refresh_from_db()
    assert discharge.status == DischargeStatus.ACTIVE
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=contacts[("visit", 15)].pk,
        outcome="visit_done",
        request_id=uuid4(),
    )
    discharge.refresh_from_db()
    assert discharge.status == DischargeStatus.COMPLETED
    done = _contacts(stage, discharge)
    assert done[("call", 7)].status == ContactStatus.DONE
    assert done[("call", 15)].status == ContactStatus.MISSED  # não atendeu
    assert done[("visit", 15)].status == ContactStatus.DONE
    assert done[("call", 7)].completed_by_id == stage.staff.pk


def test_completion_validates_outcome_state_and_notes() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=8)
    contacts = _contacts(stage, discharge)
    call, visit = contacts[("call", 7)], contacts[("visit", 15)]
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "request_id": uuid4(),
    }
    with pytest.raises(ValidationError):  # desfecho de visita numa ligação
        services.complete_contact(contact_id=call.pk, outcome="visit_done", **kwargs)
    with pytest.raises(ValidationError):  # desfecho de ligação numa visita
        services.complete_contact(contact_id=visit.pk, outcome="reached", **kwargs)
    with pytest.raises(ValidationError):
        services.complete_contact(
            contact_id=call.pk, outcome="reached", notes="x" * 1001, **kwargs
        )
    with pytest.raises(PermissionDenied):
        services.complete_contact(
            clinic_id=stage.clinic.pk,
            actor=stage.therapist,
            contact_id=call.pk,
            outcome="reached",
            request_id=uuid4(),
        )
    services.complete_contact(contact_id=call.pk, outcome="reached", **kwargs)
    with pytest.raises(ValidationError, match="já foi concluído"):
        services.complete_contact(contact_id=call.pk, outcome="reached", **kwargs)


def test_contact_notes_are_encrypted_at_rest() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=8)
    call = _contacts(stage, discharge)[("call", 7)]
    secret = "Paciente comentou que o irmão vai buscá-lo no sábado."
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=call.pk,
        outcome="reached",
        notes=secret,
        request_id=uuid4(),
    )
    raw = _raw("concierge_aftercarecontact", "notes", call.pk)
    assert raw.startswith("enc1:") and secret not in raw
    call.refresh_from_db()
    assert call.notes == secret


def test_completing_with_a_family_member_writes_the_concierge_log() -> None:
    stage = build_stage()
    patient, discharge = _discharge(stage, days_ago=8)
    call = _contacts(stage, discharge)[("call", 7)]
    unauthorized = _family(stage, patient, consent=False, full_name="Pedro Exemplo")
    with pytest.raises(ValidationError, match="não autorizou"):
        services.complete_contact(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            contact_id=call.pk,
            outcome="reached",
            family_contact_id=unauthorized.pk,
            request_id=uuid4(),
        )
    call.refresh_from_db()
    assert call.status == ContactStatus.SCHEDULED  # a falha não deixa efeito parcial
    family = _family(stage, patient)
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=call.pk,
        outcome="reached",
        notes="Combinamos a visita.",
        family_contact_id=family.pk,
        request_id=uuid4(),
    )
    log = ConciergeLog.objects.for_clinic(stage.clinic.pk).get(aftercare_contact=call)
    assert log.family_contact_id == family.pk
    assert log.channel == "call" and "Combinamos a visita." in log.summary


def test_reschedule_rules() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=2)
    call = _contacts(stage, discharge)[("call", 7)]
    today = timezone.localdate()
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "contact_id": call.pk,
    }
    with pytest.raises(ValidationError):
        services.reschedule_contact(
            new_due_date=today - timedelta(days=1),
            reason="Atraso",
            request_id=uuid4(),
            **kwargs,
        )
    with pytest.raises(ValidationError):
        services.reschedule_contact(
            new_due_date=today + timedelta(days=1),
            reason="  ",
            request_id=uuid4(),
            **kwargs,
        )
    with pytest.raises(ValidationError):
        services.reschedule_contact(
            new_due_date=discharge.discharge_date + timedelta(days=366),
            reason="Muito longe",
            request_id=uuid4(),
            **kwargs,
        )
    services.reschedule_contact(
        new_due_date=today + timedelta(days=2),
        reason="Paciente pediu outro dia",
        request_id=uuid4(),
        **kwargs,
    )
    call.refresh_from_db()
    assert call.due_date == today + timedelta(days=2)
    assert call.original_due_date == discharge.discharge_date + timedelta(days=7)
    assert call.reschedule_count == 1
    for attempt in range(4):
        services.reschedule_contact(
            new_due_date=today + timedelta(days=3 + attempt),
            reason="Nova tentativa",
            request_id=uuid4(),
            **kwargs,
        )
    with pytest.raises(ValidationError, match="máximo de vezes"):
        services.reschedule_contact(
            new_due_date=today + timedelta(days=9),
            reason="Sexta vez",
            request_id=uuid4(),
            **kwargs,
        )


def test_mark_missed_only_after_the_due_date() -> None:
    stage = build_stage()
    _patient, discharge = _discharge(stage, days_ago=10)
    contacts = _contacts(stage, discharge)
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "request_id": uuid4(),
    }
    with pytest.raises(ValidationError):  # visita aos 15 dias ainda não venceu
        services.mark_contact_missed(
            contact_id=contacts[("visit", 15)].pk, notes="Sem condições", **kwargs
        )
    services.mark_contact_missed(
        contact_id=contacts[("call", 7)].pk, notes="Número desligado", **kwargs
    )
    assert _contacts(stage, discharge)[("call", 7)].status == ContactStatus.MISSED


# ── Família ─────────────────────────────────────────────────────────────────


def test_family_contact_requires_reachable_data_and_documented_consent() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "patient_profile_id": patient.pk,
        "request_id": uuid4(),
    }
    with pytest.raises(ValidationError):  # sem telefone nem e-mail
        services.add_family_contact(full_name="Ana", relationship="Irmã", **kwargs)
    with pytest.raises(ValidationError):  # telefone curto
        services.add_family_contact(
            full_name="Ana", relationship="Irmã", phone="123", **kwargs
        )
    with pytest.raises(ValidationError):  # e-mail inválido
        services.add_family_contact(
            full_name="Ana", relationship="Irmã", email="sem-arroba", **kwargs
        )
    with pytest.raises(ValidationError):  # consentimento sem forma documentada
        services.add_family_contact(
            full_name="Ana",
            relationship="Irmã",
            phone="81 90000-0000",
            consent_to_contact=True,
            consent_note="",
            **kwargs,
        )
    with pytest.raises(PermissionDenied):
        services.add_family_contact(
            clinic_id=stage.clinic.pk,
            actor=stage.therapist,
            patient_profile_id=patient.pk,
            full_name="Ana",
            relationship="Irmã",
            phone="81 90000-0000",
            request_id=uuid4(),
        )
    pending = _family(stage, patient, consent=False)
    assert not pending.consent_to_contact and pending.consent_recorded_at is None
    assert not pending.can_be_contacted


def test_family_phone_and_email_are_stored_encrypted() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(
        stage, patient, phone="+55 81 0000-0099", email="privado@example.test"
    )
    phone = _raw("concierge_familycontact", "phone", family.pk)
    email = _raw("concierge_familycontact", "email", family.pk)
    assert phone.startswith("enc1:") and "0099" not in phone
    assert email.startswith("enc1:") and "privado" not in email
    family.refresh_from_db()
    assert family.phone == "+55 81 0000-0099" and family.email == "privado@example.test"


def test_only_one_primary_family_contact_per_patient() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    first = _family(stage, patient, is_primary=True)
    second = _family(stage, patient, is_primary=True, full_name="Pedro Exemplo")
    first.refresh_from_db()
    assert not first.is_primary and second.is_primary
    listed = selectors.family_contacts_for_patient(
        clinic_id=stage.clinic.pk, patient_profile_id=patient.pk
    )
    assert listed[0].pk == second.pk


def test_family_contact_limit_per_patient() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    for index in range(10):
        _family(stage, patient, full_name=f"Familiar {index}")
    with pytest.raises(ValidationError, match="Limite de 10"):
        _family(stage, patient, full_name="Familiar 11")


def test_revoking_consent_blocks_contact_and_cancels_open_requests() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    family_request = services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="call_me",
        description="Gostaria que minha mãe me ligasse no domingo.",
        request_id=uuid4(),
    )
    services.set_family_consent(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        family_contact_id=family.pk,
        granted=False,
        note="Paciente retirou a autorização por telefone",
        request_id=uuid4(),
    )
    family.refresh_from_db()
    family_request.refresh_from_db()
    assert not family.consent_to_contact
    assert family_request.status == RequestStatus.CANCELED
    with pytest.raises(ValidationError, match="não autorizou"):
        services.record_log(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            patient_profile_id=patient.pk,
            family_contact_id=family.pk,
            channel="call",
            summary="Ligação para informar a alta.",
            request_id=uuid4(),
        )
    services.set_family_consent(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        family_contact_id=family.pk,
        granted=True,
        note="Nova autorização assinada",
        request_id=uuid4(),
    )
    family.refresh_from_db()
    assert family.can_be_contacted


def test_deactivated_family_contact_keeps_history_but_cannot_be_used() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    log = services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Ligação para combinar a visita.",
        request_id=uuid4(),
    )
    services.deactivate_family_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        family_contact_id=family.pk,
        request_id=uuid4(),
    )
    assert ConciergeLog.objects.for_clinic(stage.clinic.pk).filter(pk=log.pk).exists()
    with pytest.raises(ValidationError, match="inativo"):
        services.record_log(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            patient_profile_id=patient.pk,
            family_contact_id=family.pk,
            channel="call",
            summary="Nova ligação.",
            request_id=uuid4(),
        )


# ── Registro do concierge ───────────────────────────────────────────────────


def test_concierge_log_is_append_only() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    log = services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Informei o horário de visita.",
        request_id=uuid4(),
    )
    log.summary = "Texto reescrito"
    with pytest.raises(PermissionDenied):
        log.save()
    with pytest.raises(PermissionDenied):
        log.delete()
    queryset = ConciergeLog.objects.for_clinic(stage.clinic.pk)
    with pytest.raises(PermissionDenied):
        queryset.update(summary="x")
    with pytest.raises(PermissionDenied):
        queryset.delete()
    with pytest.raises(PermissionDenied):
        queryset.bulk_update([log], ["summary"])
    log.refresh_from_db()
    assert log.summary == "Informei o horário de visita."


def test_deleting_the_author_keeps_the_log_and_only_clears_the_author() -> None:
    """Apagar o usuário (LGPD) não pode quebrar nem reescrever o registro."""
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Informei o horário de visita.",
        request_id=uuid4(),
    )
    User.objects.filter(pk=stage.staff.pk).delete()
    queryset = ConciergeLog.objects.for_clinic(stage.clinic.pk)
    log = queryset.get()
    assert log.recorded_by_id is None
    assert log.summary == "Informei o horário de visita."
    # só a coluna de autoria pode ser anulada em massa; o conteúdo continua blindado
    with pytest.raises(PermissionDenied):
        queryset.update(summary="x")
    with pytest.raises(PermissionDenied):
        queryset.update(recorded_by=None, summary="x")
    with pytest.raises(PermissionDenied):
        queryset.update(recorded_by=stage.admin)


def test_log_correction_keeps_the_original_and_chains_once() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    original = services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Falei com a mãe sobre o sábado.",
        request_id=uuid4(),
    )
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "request_id": uuid4(),
    }
    corrected = services.correct_log(
        log_id=original.pk,
        new_summary="Falei com a mãe sobre o domingo.",
        reason="Dia errado",
        **kwargs,
    )
    assert corrected.corrects_id == original.pk
    original.refresh_from_db()
    assert original.summary == "Falei com a mãe sobre o sábado."
    with pytest.raises(ValidationError, match="já foi corrigido"):
        services.correct_log(
            log_id=original.pk,
            new_summary="Outra versão",
            reason="Outra vez",
            **kwargs,
        )
    again = services.correct_log(
        log_id=corrected.pk,
        new_summary="Versão final do texto",
        reason="Ajuste",
        **kwargs,
    )
    assert again.corrects_id == corrected.pk
    assert _audit(stage, "concierge_log") == 3


def test_log_validations() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "patient_profile_id": patient.pk,
        "family_contact_id": family.pk,
        "request_id": uuid4(),
    }
    now = timezone.now()
    with pytest.raises(ValidationError):
        services.record_log(channel="telepatia", summary="Contato válido", **kwargs)
    with pytest.raises(ValidationError):
        services.record_log(channel="call", summary="ab", **kwargs)
    with pytest.raises(ValidationError):
        services.record_log(channel="call", summary="x" * 2001, **kwargs)
    with pytest.raises(ValidationError):
        services.record_log(
            channel="call",
            summary="Contato no futuro",
            occurred_at=now + timedelta(hours=1),
            **kwargs,
        )
    with pytest.raises(ValidationError):
        services.record_log(
            channel="call",
            summary="Contato antigo demais",
            occurred_at=now - timedelta(days=91),
            **kwargs,
        )
    with pytest.raises(ValidationError):
        services.record_log(
            channel="call", summary="Sentido inválido", direction="lateral", **kwargs
        )
    with pytest.raises(PermissionDenied):
        services.record_log(
            clinic_id=stage.clinic.pk,
            actor=stage.therapist,
            patient_profile_id=patient.pk,
            family_contact_id=family.pk,
            channel="call",
            summary="Terapeuta não registra",
            request_id=uuid4(),
        )


def test_log_summary_is_encrypted_at_rest() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    log = services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="message",
        summary="A família confirmou a visita de domingo às 15h.",
        request_id=uuid4(),
    )
    raw = _raw("concierge_conciergelog", "summary", log.pk)
    assert raw.startswith("enc1:") and "domingo" not in raw


# ── Pedidos do paciente à família ───────────────────────────────────────────


def test_request_lifecycle_requires_forwarding_before_fulfilment() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    family_request = services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="bring_item",
        description="Pediu que tragam o carregador do celular.",
        request_id=uuid4(),
    )
    assert family_request.status == RequestStatus.OPEN
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "request_id": uuid4(),
    }
    # Não se pode afirmar que foi atendido sem registrar que a família foi contatada.
    with pytest.raises(ValidationError, match="primeiro o encaminhamento"):
        services.resolve_family_request(
            family_request_id=family_request.pk,
            fulfilled=True,
            note="Entregue",
            **kwargs,
        )
    forwarded = services.forward_family_request(
        family_request_id=family_request.pk,
        channel="call",
        summary="Liguei para a Marta e passei o pedido.",
        **kwargs,
    )
    assert forwarded.status == RequestStatus.FORWARDED and forwarded.forwarded_at
    log = ConciergeLog.objects.for_clinic(stage.clinic.pk).get(
        family_request=family_request
    )
    assert log.family_contact_id == family.pk
    with pytest.raises(ValidationError, match="já foi registrado"):
        services.forward_family_request(
            family_request_id=family_request.pk,
            channel="call",
            summary="Segunda vez",
            **kwargs,
        )
    done = services.resolve_family_request(
        family_request_id=family_request.pk,
        fulfilled=True,
        note="Entregue no sábado",
        **kwargs,
    )
    assert (
        done.status == RequestStatus.FULFILLED and done.resolved_by_id == stage.staff.pk
    )
    with pytest.raises(ValidationError, match="já foi encerrado"):
        services.cancel_family_request(
            family_request_id=family_request.pk, reason="Tarde demais", **kwargs
        )


def test_request_can_be_declined_or_canceled_and_is_tenant_scoped() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    request = services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="visit_me",
        description="Gostaria de uma visita neste fim de semana.",
        request_id=uuid4(),
    )
    with pytest.raises(PermissionDenied):  # outra clínica não enxerga o pedido
        services.cancel_family_request(
            clinic_id=stage.other_clinic.pk,
            actor=stage.other_admin,
            family_request_id=request.pk,
            reason="Tentativa indevida",
            request_id=uuid4(),
        )
    canceled = services.cancel_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        family_request_id=request.pk,
        reason="Paciente desistiu",
        request_id=uuid4(),
    )
    assert canceled.status == RequestStatus.CANCELED


def test_request_validations() -> None:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin)
    family = _family(stage, patient)
    other_patient = make_patient(stage.clinic, stage.admin, name="Outra Pessoa")
    kwargs: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "actor": stage.staff,
        "patient_profile_id": patient.pk,
        "request_id": uuid4(),
    }
    with pytest.raises(ValidationError):
        services.register_family_request(
            family_contact_id=family.pk,
            kind="pizza",
            description="Pedido inválido",
            **kwargs,
        )
    with pytest.raises(ValidationError):
        services.register_family_request(
            family_contact_id=family.pk, kind="call_me", description="x", **kwargs
        )
    # familiar de outro paciente da mesma clínica não pode ser usado
    with pytest.raises(PermissionDenied):
        services.register_family_request(
            clinic_id=stage.clinic.pk,
            actor=stage.staff,
            patient_profile_id=other_patient.pk,
            family_contact_id=family.pk,
            kind="call_me",
            description="Pedido de outra pessoa",
            request_id=uuid4(),
        )


# ── Isolamento entre clínicas e seletores ───────────────────────────────────


def test_managers_refuse_queries_without_a_clinic_scope() -> None:
    build_stage()
    for model in (
        Discharge,
        AftercareContact,
        FamilyContact,
        FamilyRequest,
        ConciergeLog,
    ):
        with pytest.raises(RuntimeError):
            model.objects.all()


def test_clinics_never_see_each_others_records() -> None:
    stage = build_stage()
    patient, _discharge_row = _discharge(stage)
    family = _family(stage, patient)
    services.record_log(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        channel="call",
        summary="Contato de rotina com a família.",
        request_id=uuid4(),
    )
    other = stage.other_clinic.pk
    assert selectors.discharge_list(clinic_id=other) == []
    assert selectors.contact_queue(clinic_id=other, today=timezone.localdate()) == []
    assert selectors.recent_logs(clinic_id=other) == []
    assert (
        selectors.family_contacts_for_patient(
            clinic_id=other, patient_profile_id=patient.pk
        )
        == []
    )
    assert (
        selectors.patient_timeline(clinic_id=other, patient_profile_id=patient.pk) == []
    )
    summary = selectors.dashboard_summary(clinic_id=other, today=timezone.localdate())
    assert (summary.active_discharges, summary.overdue, summary.open_requests) == (
        0,
        0,
        0,
    )


def test_dashboard_counts_overdue_today_and_upcoming_contacts() -> None:
    stage = build_stage()
    today = timezone.localdate()
    _discharge(stage, days_ago=10, name="Ana Souza")  # ligação 7d venceu; 15d em 5 dias
    _discharge(stage, days_ago=7, name="Bruno Lima")  # ligação 7d vence hoje
    summary = selectors.dashboard_summary(clinic_id=stage.clinic.pk, today=today)
    assert summary.active_discharges == 2
    assert summary.overdue == 1
    assert summary.due_today == 1
    assert summary.due_next_7_days == 2  # 15º dia (ligação e visita) da Ana, em 5 dias
    assert summary.patients_without_family_consent == 2
    assert (
        summary.queue[0].patient_name == "Ana Souza"
        and summary.queue[0].state == "overdue"
    )
    assert {row.state for row in summary.queue} == {"overdue", "today", "upcoming"}
    overdue = selectors.contact_queue(
        clinic_id=stage.clinic.pk, today=today, window="overdue"
    )
    assert [row.patient_name for row in overdue] == ["Ana Souza"]
    visits = selectors.contact_queue(
        clinic_id=stage.clinic.pk, today=today, kind="visit"
    )
    assert {row.contact.kind for row in visits} == {"visit"}


def test_patient_timeline_merges_contacts_logs_and_requests() -> None:
    stage = build_stage()
    patient, discharge = _discharge(stage, days_ago=8)
    family = _family(stage, patient)
    call = _contacts(stage, discharge)[("call", 7)]
    services.complete_contact(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        contact_id=call.pk,
        outcome="reached",
        family_contact_id=family.pk,
        notes="Tudo certo.",
        request_id=uuid4(),
    )
    services.register_family_request(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.pk,
        family_contact_id=family.pk,
        kind="message",
        description="Avisar que chegou bem em casa.",
        request_id=uuid4(),
    )
    timeline = selectors.patient_timeline(
        clinic_id=stage.clinic.pk, patient_profile_id=patient.pk
    )
    kinds = [item.kind for item in timeline]
    assert sorted(kinds) == ["contact", "log", "request"]
    assert timeline == sorted(timeline, key=lambda item: item.when, reverse=True)


# ── Cifragem ────────────────────────────────────────────────────────────────


def test_encryption_round_trip_and_tamper_detection() -> None:
    token = encrypt_text("dado sensível")
    assert token.startswith("enc1:") and "sensível" not in token
    assert decrypt_text(token) == "dado sensível"
    assert decrypt_text("texto antigo sem prefixo") == "texto antigo sem prefixo"
    with pytest.raises(ValueError):
        decrypt_text(token[:-4] + "AAAA")


def test_encrypted_fields_reject_partial_search() -> None:
    stage = build_stage()
    with pytest.raises(ValueError, match="não aceitam busca"):
        lookup: dict[str, Any] = {"phone__icontains": "81"}
        FamilyContact.objects.for_clinic(stage.clinic.pk).filter(**lookup)
