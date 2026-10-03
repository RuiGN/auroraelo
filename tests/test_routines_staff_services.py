"""Serviços, políticas e seletores usados pelas telas de equipe de ``routines``."""

from __future__ import annotations

from datetime import time, timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent
from clinics.models import ClinicMembership
from people.models import CareRelationship
from routines import care_plan_services, medication_services, selectors
from routines import services as habit_services
from routines.forms import parse_schedule_times
from routines.models import CarePlanStatus, HabitStatus, PatientResponseChoice
from routines.policies import can_author_care_plan, can_staff_manage_patient_care
from tests.aftercare_support import make_patient_login
from tests.factories import ClinicMembershipFactory, UserFactory
from tests.routines_staff_support import (
    World,
    build_world,
    link,
    make_habit,
    make_medication,
    make_plan,
    today,
)

pytestmark = pytest.mark.django_db


def _events(world: World, action: str) -> list[AuditEvent]:
    return list(
        AuditEvent.infrastructure_objects.filter(
            clinic_id=world.clinic.pk, action=action
        )
    )


def _plan_ids(world: World, plan: Any, **extra: Any) -> dict[str, Any]:
    return {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": plan.patient_profile_id,
        "care_plan_id": plan.pk,
        **extra,
    }


# ── Horários da prescrição ──────────────────────────────────────────────────


def test_schedule_times_are_normalized_sorted_and_deduplicated() -> None:
    assert parse_schedule_times("20:00, 8:00;08:00 12:30") == [
        "08:00",
        "12:30",
        "20:00",
    ]


@pytest.mark.parametrize("raw", ["", " ", "24:00", "08:60", "8h", "08:00:00", "abc"])
def test_invalid_schedule_times_are_rejected(raw: str) -> None:
    with pytest.raises(ValidationError):
        parse_schedule_times(raw)


# ── Políticas ───────────────────────────────────────────────────────────────


def test_staff_policy_matrix() -> None:
    world = build_world()
    patient_login = make_patient_login(world.clinic, world.admin, name="Com Login")
    ids = {"clinic_id": world.clinic.pk, "patient_profile_id": world.patient.pk}

    def allowed(user: Any, **over: Any) -> bool:
        return can_staff_manage_patient_care(user=user, **(ids | over))

    assert allowed(world.admin)
    assert allowed(world.linked) and allowed(world.second_linked)
    assert not allowed(world.unlinked)  # terapeuta sem vínculo
    assert not allowed(world.stage.staff)  # administrativo
    assert not allowed(world.stage.other_admin)  # outra clínica
    assert not allowed(patient_login.user)  # paciente
    # ninguém cuida da própria conta, nem o administrador
    assert not allowed(world.admin, patient_user_id=world.admin.pk)
    assert not allowed(
        patient_login.user,
        patient_profile_id=patient_login.profile.pk,
        patient_user_id=patient_login.user.pk,
    )
    # vínculo com outro paciente não vale
    assert not can_staff_manage_patient_care(
        user=world.linked,
        clinic_id=world.clinic.pk,
        patient_profile_id=world.other_patient.pk,
    )
    inactive = UserFactory.create(is_active=False)
    ClinicMembershipFactory.create(
        clinic=world.clinic, user=inactive, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    assert not allowed(inactive)


def test_staff_policy_ignores_closed_links() -> None:
    world = build_world()
    expired = world.unlinked
    link(world.clinic, world.admin, expired, world.patient)
    assert can_staff_manage_patient_care(
        user=expired, clinic_id=world.clinic.pk, patient_profile_id=world.patient.pk
    )
    CareRelationship.infrastructure_objects.filter(therapist=expired).update(
        is_active=False
    )
    assert not can_staff_manage_patient_care(
        user=expired, clinic_id=world.clinic.pk, patient_profile_id=world.patient.pk
    )


def test_only_the_proposing_professional_authors_a_plan() -> None:
    world = build_world()
    plan = make_plan(world, author=world.linked)
    ids = {
        "clinic_id": world.clinic.pk,
        "prescribing_professional_id": plan.prescribing_professional_id,
    }
    assert can_author_care_plan(user=world.linked, **ids)
    assert not can_author_care_plan(user=world.admin, **ids)
    assert not can_author_care_plan(user=world.second_linked, **ids)
    assert not can_author_care_plan(user=world.stage.staff, **ids)


# ── Seletores da equipe ─────────────────────────────────────────────────────


def test_staff_selectors_see_every_state_but_stay_inside_patient_and_clinic() -> None:
    world = build_world()
    medication = make_medication(world)
    plan = make_plan(world)
    habit = make_habit(world)
    habit_services.archive_habit(clinic_id=world.clinic.pk, habit_id=habit.pk)
    medication_services.suspend_prescribed_medication(
        clinic_id=world.clinic.pk,
        patient_profile_id=world.patient.pk,
        medication_id=medication.pk,
        actor_id=world.admin.pk,
    )
    clinic, patient = world.clinic.pk, world.patient.pk
    # o que o app não mostra (suspenso, rascunho, arquivado) a equipe enxerga
    assert selectors.medication_for_staff(
        clinic_id=clinic, patient_profile_id=patient, medication_id=medication.pk
    )
    assert selectors.care_plan_for_staff(
        clinic_id=clinic, patient_profile_id=patient, care_plan_id=plan.pk
    )
    assert selectors.habit_for_staff(
        clinic_id=clinic, patient_profile_id=patient, habit_id=habit.pk
    )
    assert [
        h.pk
        for h in selectors.habits_for_staff(
            clinic_id=clinic, patient_profile_id=patient
        )
    ] == [habit.pk]
    assert (
        selectors.habits_for_patient(clinic_id=clinic, patient_profile_id=patient) == []
    )
    # outro paciente ou outra clínica nunca resolve o objeto
    for other in (world.other_patient.pk, uuid4()):
        assert not selectors.medication_for_staff(
            clinic_id=clinic, patient_profile_id=other, medication_id=medication.pk
        )
        assert not selectors.care_plan_for_staff(
            clinic_id=clinic, patient_profile_id=other, care_plan_id=plan.pk
        )
        assert not selectors.habit_for_staff(
            clinic_id=clinic, patient_profile_id=other, habit_id=habit.pk
        )
    outside = world.stage.other_clinic.pk
    assert not selectors.medication_for_staff(
        clinic_id=outside, patient_profile_id=patient, medication_id=medication.pk
    )
    assert not selectors.habits_for_staff(clinic_id=outside, patient_profile_id=patient)


# ── Medicação ───────────────────────────────────────────────────────────────


def _update_kwargs(world: World, medication: Any, **over: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": medication.patient_profile_id,
        "medication_id": medication.pk,
        "medication_name": medication.medication_name,
        "presentation": medication.presentation,
        "prescribed_dose": medication.prescribed_dose,
        "route": medication.route,
        "schedule_times": ["08:00"],
        "start_date": medication.start_date,
        "end_date": None,
        "is_continuous": True,
        "prescriber_name": medication.prescriber_name,
        "prescriber_registration": medication.prescriber_registration,
        "prescription_date": medication.prescription_date,
        "instructions": "",
        "actor_id": world.admin.pk,
    }
    values.update(over)
    return values


def test_registering_a_medication_is_audited_only_for_team_actions() -> None:
    world = build_world()
    make_medication(world)  # fluxo antigo, sem ator: não audita aqui
    assert _events(world, "routines.medication_registered") == []
    med = make_medication(
        world, actor_id=world.admin.pk, request_id=uuid4(), medication_name="Lítio"
    )
    events = _events(world, "routines.medication_registered")
    assert len(events) == 1
    assert events[0].resource_id == str(med.pk) and events[0].actor_id == world.admin.pk


def test_updating_a_medication_keeps_past_doses_and_blocks_unsafe_text() -> None:
    world = build_world()
    medication = make_medication(world)
    medication_services.record_medication_dose(
        clinic_id=world.clinic.pk,
        medication_id=medication.pk,
        scheduled_time=timezone.now() - timedelta(days=1),
    )
    updated = medication_services.update_prescribed_medication(
        **_update_kwargs(
            world, medication, prescribed_dose="75 mg", schedule_times=["09:00"]
        )
    )
    assert updated.prescribed_dose == "75 mg" and updated.schedule_times == ["09:00"]
    assert updated.logs.count() == 1
    assert len(_events(world, "routines.medication_updated")) == 1
    with pytest.raises(ValidationError):
        medication_services.update_prescribed_medication(
            **_update_kwargs(
                world, medication, instructions="Aumente a dose se piorar."
            )
        )
    with pytest.raises(ValidationError):
        medication_services.update_prescribed_medication(
            **_update_kwargs(world, medication, prescriber_registration=" ")
        )
    medication.refresh_from_db()
    assert medication.prescribed_dose == "75 mg"


def test_a_limited_course_drops_its_end_date_when_it_becomes_continuous() -> None:
    world = build_world()
    medication = make_medication(
        world, is_continuous=False, end_date=today() + timedelta(days=10)
    )
    updated = medication_services.update_prescribed_medication(
        **_update_kwargs(
            world, medication, is_continuous=True, end_date=today() + timedelta(days=3)
        )
    )
    assert updated.is_continuous and updated.end_date is None


def test_medication_services_only_reach_the_given_patients_medication() -> None:
    world = build_world()
    foreign = make_medication(world, world.other_patient)
    common = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": world.patient.pk,
        "medication_id": foreign.pk,
        "actor_id": world.admin.pk,
    }
    for service in (
        medication_services.suspend_prescribed_medication,
        medication_services.resume_prescribed_medication,
        medication_services.end_prescribed_medication,
    ):
        with pytest.raises(ValidationError, match="não encontrado"):
            service(**common)
    with pytest.raises(ValidationError, match="não encontrado"):
        medication_services.update_prescribed_medication(
            **_update_kwargs(world, foreign, patient_profile_id=world.patient.pk)
        )
    with pytest.raises(ValidationError, match="não encontrado"):
        medication_services.suspend_prescribed_medication(
            **(
                common
                | {
                    "clinic_id": world.stage.other_clinic.pk,
                    "patient_profile_id": world.other_patient.pk,
                }
            )
        )
    foreign.refresh_from_db()
    assert foreign.is_active


def test_suspend_resume_and_end_follow_the_medication_lifecycle() -> None:
    world = build_world()
    medication = make_medication(world)
    common = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": world.patient.pk,
        "medication_id": medication.pk,
        "actor_id": world.admin.pk,
        "request_id": uuid4(),
    }
    suspend = medication_services.suspend_prescribed_medication
    resume = medication_services.resume_prescribed_medication
    end = medication_services.end_prescribed_medication
    with pytest.raises(ValidationError):
        resume(**common)  # já ativo
    assert not suspend(**common).is_active
    with pytest.raises(ValidationError):
        suspend(**common)  # já suspenso
    assert resume(**common).is_active
    suspend(**common)
    ended = end(**common)  # suspenso também pode ser encerrado
    assert not ended.is_active and not ended.is_continuous
    assert ended.end_date == today()
    assert medication_services.course_has_ended(ended, today=today())
    with pytest.raises(ValidationError, match="já terminou"):
        resume(**common)
    with pytest.raises(ValidationError, match="já foi encerrado"):
        end(**common)
    for action in ("suspended", "resumed", "ended"):
        assert _events(world, f"routines.medication_{action}")
    assert all(
        e.actor_id == world.admin.pk
        for e in _events(world, "routines.medication_ended")
    )


def test_ending_a_course_that_starts_in_the_future_keeps_dates_consistent() -> None:
    world = build_world()
    start = today() + timedelta(days=4)
    medication = make_medication(
        world, start_date=start, is_continuous=False, end_date=start + timedelta(days=9)
    )
    ended = medication_services.end_prescribed_medication(
        clinic_id=world.clinic.pk,
        patient_profile_id=world.patient.pk,
        medication_id=medication.pk,
        actor_id=world.admin.pk,
    )
    assert ended.end_date is not None and ended.end_date >= ended.start_date


def test_a_suspended_course_with_days_left_can_resume_but_an_expired_one_cannot() -> (
    None
):
    world = build_world()
    future = make_medication(
        world, is_continuous=False, end_date=today() + timedelta(days=5)
    )
    expired = make_medication(
        world,
        medication_name="Antigo",
        is_continuous=False,
        start_date=today() - timedelta(days=20),
        end_date=today() - timedelta(days=1),
    )
    common = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": world.patient.pk,
        "actor_id": world.admin.pk,
    }
    for medication in (future, expired):
        medication_services.suspend_prescribed_medication(
            **common, medication_id=medication.pk
        )
    assert medication_services.resume_prescribed_medication(
        **common, medication_id=future.pk
    ).is_active
    with pytest.raises(ValidationError):
        medication_services.resume_prescribed_medication(
            **common, medication_id=expired.pk
        )


# ── Plano de cuidado ────────────────────────────────────────────────────────


def test_proposing_a_plan_is_audited_and_never_visible_to_the_patient() -> None:
    world = build_world()
    request_id = uuid4()
    plan = care_plan_services.propose_care_plan(
        clinic_id=world.clinic.pk,
        patient_profile_id=world.patient.pk,
        professional_user=world.admin,
        title="Plano",
        objective="Objetivo",
        clinical_rationale="Raciocínio",
        actions_data=[{"description": "Respirar fundo", "frequency": "Diária"}],
        request_id=request_id,
    )
    assert plan.status == CarePlanStatus.DRAFT
    event = _events(world, "routines.care_plan_proposed")[0]
    assert event.request_id == request_id and event.resource_id == str(plan.pk)
    assert (
        selectors.current_care_plan_for_patient(
            clinic_id=world.clinic.pk, patient_profile_id=world.patient.pk
        )
        is None
    )
    with pytest.raises(ValidationError):
        care_plan_services.propose_care_plan(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            professional_user=world.stage.staff,  # administrativo não propõe
            title="Plano",
            objective="Objetivo",
            clinical_rationale="Raciocínio",
        )


def test_draft_edit_submit_reopen_and_sign_enforce_author_and_state() -> None:
    world = build_world()
    plan = make_plan(world, author=world.linked)
    ids = _plan_ids(world, plan)
    author, other = world.linked, world.admin

    def edit(user: Any, **over: Any) -> Any:
        values: dict[str, Any] = {
            "professional_user": user,
            "title": "Título novo",
            "objective": "Objetivo novo",
            "clinical_rationale": "Raciocínio novo",
            "actions_data": [{"description": "Nova ação", "frequency": "Diária"}],
        }
        return care_plan_services.update_care_plan_draft(**ids, **(values | over))

    with pytest.raises(ValidationError, match="Somente o profissional"):
        edit(other)
    with pytest.raises(ValidationError):
        edit(author, title=" ")
    assert edit(author).title == "Título novo"
    assert [a.action_description for a in plan.actions.all()] == ["Nova ação"]
    # sem ações não há o que assinar
    edit(author, actions_data=[])
    with pytest.raises(ValidationError, match="ao menos uma ação"):
        care_plan_services.submit_care_plan_for_signature(
            **ids, professional_user=author
        )
    edit(author)
    with pytest.raises(ValidationError):
        care_plan_services.submit_care_plan_for_signature(
            **ids, professional_user=other
        )
    submitted = care_plan_services.submit_care_plan_for_signature(
        **ids, professional_user=author
    )
    assert submitted.status == CarePlanStatus.PENDING_SIGNATURE
    with pytest.raises(ValidationError):  # não edita nem reenvia depois de enviado
        edit(author)
    with pytest.raises(ValidationError):
        care_plan_services.submit_care_plan_for_signature(
            **ids, professional_user=author
        )
    with pytest.raises(ValidationError, match="Somente o profissional"):
        care_plan_services.reopen_care_plan_draft(**ids, professional_user=other)
    reopened = care_plan_services.reopen_care_plan_draft(
        **ids, professional_user=author
    )
    assert reopened.status == CarePlanStatus.DRAFT
    with pytest.raises(ValidationError):
        care_plan_services.reopen_care_plan_draft(**ids, professional_user=author)
    for action in ("updated", "submitted", "reopened"):
        assert _events(world, f"routines.care_plan_{action}")


def test_signing_is_limited_to_the_author_and_to_unpublished_plans() -> None:
    world = build_world()
    plan = make_plan(world, author=world.linked, status="pending_signature")
    with pytest.raises(ValidationError, match="Somente o profissional"):
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=plan.pk,
            signing_professional=world.admin,
        )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.PENDING_SIGNATURE and plan.signed_at is None
    signed = care_plan_services.sign_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=plan.pk,
        signing_professional=world.linked,
    )
    assert signed.status == CarePlanStatus.ACTIVE
    # assinar de novo não renova a assinatura de um plano já em vigor
    with pytest.raises(ValidationError, match="não está aguardando"):
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=plan.pk,
            signing_professional=world.linked,
        )


def test_a_refused_plan_cannot_be_reactivated_by_signing_it_again() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    care_plan_services.respond_to_care_plan(
        clinic_id=world.clinic.pk,
        care_plan_id=plan.pk,
        decision=PatientResponseChoice.REFUSED,
    )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.REVOKED
    with pytest.raises(ValidationError):
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=plan.pk,
            signing_professional=world.admin,
        )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.REVOKED


def test_signing_requires_no_other_plan_in_force_for_the_same_patient() -> None:
    world = build_world()
    make_plan(world, status="active")
    waiting = make_plan(world, status="pending_signature")
    with pytest.raises(ValidationError, match="plano de cuidado em vigor"):
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=waiting.pk,
            signing_professional=world.admin,
        )
    # outro paciente da mesma clínica não é afetado
    other = make_plan(world, patient=world.other_patient, status="pending_signature")
    assert (
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=other.pk,
            signing_professional=world.admin,
        ).status
        == CarePlanStatus.ACTIVE
    )


def test_pause_resume_and_close_follow_the_published_plan_lifecycle() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    ids = _plan_ids(world, plan, professional_user=world.admin, request_id=uuid4())
    with pytest.raises(ValidationError):
        care_plan_services.resume_care_plan(**ids)  # só pausado volta
    assert care_plan_services.pause_care_plan(**ids).status == CarePlanStatus.PAUSED
    with pytest.raises(ValidationError):
        care_plan_services.pause_care_plan(**ids)
    assert care_plan_services.resume_care_plan(**ids).status == CarePlanStatus.ACTIVE
    with pytest.raises(ValidationError, match="inválido"):
        care_plan_services.close_care_plan(**ids, outcome="draft")
    with pytest.raises(ValidationError, match="inválido"):
        care_plan_services.close_care_plan(**ids, outcome="active")
    closed = care_plan_services.close_care_plan(**ids, outcome=CarePlanStatus.REVOKED)
    assert closed.status == CarePlanStatus.REVOKED
    for action in (
        care_plan_services.pause_care_plan,
        care_plan_services.resume_care_plan,
        care_plan_services.close_care_plan,
    ):
        with pytest.raises(ValidationError):
            action(**ids)
    for name in ("paused", "resumed", "closed"):
        events = _events(world, f"routines.care_plan_{name}")
        assert events and events[0].actor_id == world.admin.pk


def test_unpublished_plans_cannot_be_closed_or_revoked() -> None:
    world = build_world()
    for status in ("draft", "pending_signature"):
        plan = make_plan(world, status=status)
        with pytest.raises(ValidationError):
            care_plan_services.close_care_plan(
                **_plan_ids(world, plan, professional_user=world.admin),
                outcome=CarePlanStatus.REVOKED,
            )
        plan.refresh_from_db()
        assert plan.status == status


def test_plan_transitions_reject_other_patients_clinics_and_non_professionals() -> None:
    world = build_world()
    plan = make_plan(world, status="active")
    patient_login = make_patient_login(world.clinic, world.admin, name="Com Login")
    base = _plan_ids(world, plan, professional_user=world.admin)
    with pytest.raises(ValidationError, match="não encontrado"):
        care_plan_services.pause_care_plan(
            **(base | {"patient_profile_id": world.other_patient.pk})
        )
    with pytest.raises(ValidationError, match="não encontrado"):
        care_plan_services.pause_care_plan(
            **(
                base
                | {
                    "clinic_id": world.stage.other_clinic.pk,
                    "professional_user": world.stage.other_admin,
                }
            )
        )
    with pytest.raises(ValidationError, match="habilitados"):
        care_plan_services.pause_care_plan(
            **(base | {"professional_user": patient_login.user})
        )
    with pytest.raises(ValidationError, match="habilitados"):
        care_plan_services.pause_care_plan(
            **(base | {"professional_user": world.stage.staff})
        )
    plan.refresh_from_db()
    assert plan.status == CarePlanStatus.ACTIVE


# ── Hábitos ─────────────────────────────────────────────────────────────────


def test_habit_changes_are_audited_when_the_team_acts_and_not_for_the_patient() -> None:
    world = build_world()
    request_id = uuid4()
    silent = make_habit(world)  # fluxo antigo: sem ator, sem auditoria
    assert _events(world, "routines.habit_created") == []
    habit = habit_services.create_habit(
        clinic_id=world.clinic.pk,
        patient_profile_id=world.patient.pk,
        title="Caminhar",
        actor_id=world.admin.pk,
        request_id=request_id,
    )
    created = _events(world, "routines.habit_created")
    assert len(created) == 1 and created[0].request_id == request_id
    assert created[0].resource_id == str(habit.pk)
    ids = {"clinic_id": world.clinic.pk, "habit_id": habit.pk}
    acting = {"actor_id": world.admin.pk, "request_id": request_id}
    habit_services.update_habit(**ids, title="Caminhar mais", **acting)
    habit_services.pause_habit(**ids, **acting)
    habit_services.resume_habit(**ids, **acting)
    habit_services.archive_habit(**ids, **acting)
    for action in ("updated", "paused", "resumed", "archived"):
        assert len(_events(world, f"routines.habit_{action}")) == 1
    habit_services.update_habit(
        clinic_id=world.clinic.pk, habit_id=silent.pk, title="X"
    )
    assert len(_events(world, "routines.habit_updated")) == 1


def test_update_habit_time_window_and_time_semantics() -> None:
    world = build_world()
    habit = make_habit(
        world, time_window="exact_time", target_time=time(7, 30), title="Acordar"
    )
    ids = {"clinic_id": world.clinic.pk, "habit_id": habit.pk}
    unchanged = habit_services.update_habit(**ids, title="Acordar cedo")
    assert unchanged.target_time == time(7, 30)  # None não mexe no horário
    moved = habit_services.update_habit(**ids, target_time=time(8, 0))
    assert moved.target_time == time(8, 0)
    window = habit_services.update_habit(**ids, time_window="evening")
    assert window.time_window == "evening"
    cleared = habit_services.update_habit(**ids, clear_target_time=True)
    assert cleared.target_time is None
    assert cleared.version == 5


def test_archived_habits_cannot_be_paused_or_resumed() -> None:
    world = build_world()
    habit = make_habit(world)
    ids = {"clinic_id": world.clinic.pk, "habit_id": habit.pk}
    habit_services.archive_habit(**ids)
    with pytest.raises(ValidationError):
        habit_services.pause_habit(**ids)
    with pytest.raises(ValidationError):
        habit_services.resume_habit(**ids)
    habit.refresh_from_db()
    assert habit.status == HabitStatus.ARCHIVED
    assert (
        selectors.habit_for_patient(
            clinic_id=world.clinic.pk,
            patient_profile_id=world.patient.pk,
            habit_id=habit.pk,
        )
        is None
    )
