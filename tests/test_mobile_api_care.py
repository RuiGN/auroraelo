"""API do app do paciente: medicação, plano de cuidado, rotina, exercícios e energia.

O ponto central é a posse: serviços de rotina autorizam só por clínica, então cada
rota resolve o objeto pelo perfil do paciente da sessão. Cada gravação tem um teste de
"id de outra pessoa da mesma clínica" e "id de outra clínica".
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from audit.models import AuditEvent
from clinics.models import Clinic
from goals.exercise_models import ExerciseAssignment, ExerciseStatus
from goals.exercise_services import assign_exercise, create_exercise
from goals.low_energy_models import LowEnergyMode
from goals.low_energy_services import configure_low_energy_actions
from routines.care_plan_models import (
    CarePlan,
    CarePlanAction,
    CarePlanPatientResponse,
    CarePlanStatus,
)
from routines.medication_models import MedicationLog, PrescribedMedication
from routines.medication_services import register_prescribed_medication
from routines.routine_models import (
    Habit,
    HabitCheckIn,
    HabitOccurrence,
    HabitStatus,
)
from routines.services import create_habit
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient_login,
)

pytestmark = pytest.mark.django_db

SP = ZoneInfo("America/Sao_Paulo")
LOGIN = "/api/v1/mobile/auth/login/"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _login(who: PatientLogin) -> dict[str, str]:
    response = Client().post(
        LOGIN,
        {"email": who.user.email, "password": who.password, "device_label": "Teste"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


def _json(
    client: Client, method: str, url: str, headers: dict[str, str], body: Any = None
) -> Any:
    kwargs: dict[str, Any] = dict(headers)
    if body is not None:
        kwargs["data"] = body
        kwargs["content_type"] = "application/json"
    return getattr(client, method)(url, **kwargs)


def _world() -> tuple[
    Stage, PatientLogin, PatientLogin, dict[str, str], dict[str, str]
]:
    stage = build_stage()
    ana = make_patient_login(stage.clinic, stage.admin, name="Ana Souza")
    bia = make_patient_login(stage.clinic, stage.admin, name="Bia Lima")
    return stage, ana, bia, _login(ana), _login(bia)


def _today() -> date:
    return timezone.now().astimezone(SP).date()


def _med(clinic: Clinic, who: PatientLogin, **over: Any) -> PrescribedMedication:
    values: dict[str, Any] = {
        "clinic_id": clinic.pk,
        "patient_profile_id": who.profile.pk,
        "medication_name": "Sertralina",
        "presentation": "Comprimido 50 mg",
        "prescribed_dose": "1 comprimido",
        "schedule_times": ["08:00", "20:00"],
        "start_date": _today() - timedelta(days=30),
        "is_continuous": True,
        "prescriber_name": "Dra. Exemplo",
        "prescriber_registration": "CRM-XX 000000",
        "prescription_date": _today() - timedelta(days=30),
        "instructions": "Após o café da manhã.",
    }
    values.update(over)
    return register_prescribed_medication(**values)


def _dose_time(day: date, hhmm: str) -> str:
    hour, minute = (int(part) for part in hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SP).isoformat()


# ── Medicação ───────────────────────────────────────────────────────────────


def test_medications_list_only_the_patients_own_active_courses() -> None:
    stage, ana, bia, ana_h, _bia_h = _world()
    mine = _med(stage.clinic, ana)
    _med(stage.clinic, bia, medication_name="Medicamento da Bia")
    _med(
        stage.clinic,
        ana,
        medication_name="Curso encerrado",
        is_continuous=False,
        start_date=_today() - timedelta(days=40),
        end_date=_today() - timedelta(days=10),
    )
    PrescribedMedication.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_profile_id=ana.profile.pk,
        medication_name="Suspensa",
        presentation="x",
        prescribed_dose="x",
        schedule_times=["09:00"],
        start_date=_today() - timedelta(days=5),
        is_continuous=True,
        is_active=False,
        prescriber_name="Dr. X",
        prescriber_registration="CRM 1",
        prescription_date=_today() - timedelta(days=5),
    )
    body = _json(Client(), "get", "/api/v1/mobile/medications/", ana_h).json()
    assert [m["name"] for m in body["medications"]] == ["Sertralina"]
    med = body["medications"][0]
    assert med["id"] == str(mine.pk) and med["schedule_times"] == ["08:00", "20:00"]
    assert set(med) == {
        "id",
        "name",
        "presentation",
        "dose",
        "route",
        "schedule_times",
        "start_date",
        "end_date",
        "is_continuous",
        "prescriber_name",
        "instructions",
    }
    assert "000000" not in str(body)  # registro do prescritor não sai
    assert body["dose_logs"] == []


def test_dose_log_is_idempotent_and_can_be_corrected_or_undone() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    med = _med(stage.clinic, ana)
    yesterday = _today() - timedelta(days=1)
    url = f"/api/v1/mobile/medications/{med.pk}/doses/"
    when = _dose_time(yesterday, "08:00")
    client = Client()
    taken = _json(client, "put", url, ana_h, {"scheduled_for": when, "status": "taken"})
    assert taken.status_code == 200, taken.content
    assert taken.json()["status"] == "taken"
    log = MedicationLog.objects.for_clinic(stage.clinic.pk).get()
    assert log.actual_time is not None
    omitted = _json(
        client, "put", url, ana_h, {"scheduled_for": when, "status": "omitted"}
    )
    assert omitted.json()["status"] == "omitted"
    undone = _json(
        client, "put", url, ana_h, {"scheduled_for": when, "status": "not_reported"}
    )
    assert undone.json()["status"] == "not_reported"
    assert MedicationLog.objects.for_clinic(stage.clinic.pk).count() == 1
    listing = _json(client, "get", "/api/v1/mobile/medications/", ana_h).json()
    assert [d["status"] for d in listing["dose_logs"]] == ["not_reported"]


def test_late_dose_records_the_actual_time() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    med = _med(stage.clinic, ana)
    when = _dose_time(_today() - timedelta(days=1), "20:00")
    response = _json(
        Client(),
        "put",
        f"/api/v1/mobile/medications/{med.pk}/doses/",
        ana_h,
        {"scheduled_for": when, "status": "late"},
    )
    assert response.status_code == 200
    assert (
        MedicationLog.objects.for_clinic(stage.clinic.pk).get().actual_time is not None
    )


@pytest.mark.parametrize(
    "case",
    ["off_schedule", "future", "too_old", "before_start", "naive"],
)
def test_dose_log_rejects_times_that_are_not_real_scheduled_doses(case: str) -> None:
    stage, ana, _bia, ana_h, _ = _world()
    med = _med(
        stage.clinic, ana, start_date=_today() - timedelta(days=3), is_continuous=True
    )
    yesterday = _today() - timedelta(days=1)
    when = {
        "off_schedule": _dose_time(yesterday, "09:30"),
        "future": _dose_time(_today() + timedelta(days=1), "08:00"),
        "too_old": _dose_time(_today() - timedelta(days=9), "08:00"),
        "before_start": _dose_time(_today() - timedelta(days=5), "08:00"),
        "naive": f"{yesterday.isoformat()}T08:00:00",
    }[case]
    response = _json(
        Client(),
        "put",
        f"/api/v1/mobile/medications/{med.pk}/doses/",
        ana_h,
        {"scheduled_for": when, "status": "taken"},
    )
    assert response.status_code == 422
    assert MedicationLog.objects.for_clinic(stage.clinic.pk).count() == 0


def test_dose_log_refuses_unknown_status_values() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    med = _med(stage.clinic, ana)
    response = _json(
        Client(),
        "put",
        f"/api/v1/mobile/medications/{med.pk}/doses/",
        ana_h,
        {
            "scheduled_for": _dose_time(_today() - timedelta(days=1), "08:00"),
            "status": "double",
        },
    )
    assert response.status_code == 422


def test_medication_of_another_patient_or_clinic_is_a_plain_404() -> None:
    stage, ana, bia, ana_h, _bia_h = _world()
    theirs = _med(stage.clinic, bia)
    outsider = make_patient_login(stage.other_clinic, stage.other_admin, name="Fora")
    foreign = _med(stage.other_clinic, outsider)  # outra clínica
    when = _dose_time(_today() - timedelta(days=1), "08:00")
    client = Client()
    for target in (theirs, foreign):
        response = _json(
            client,
            "put",
            f"/api/v1/mobile/medications/{target.pk}/doses/",
            ana_h,
            {"scheduled_for": when, "status": "taken"},
        )
        assert response.status_code == 404
    missing = _json(
        client,
        "put",
        f"/api/v1/mobile/medications/{uuid4()}/doses/",
        ana_h,
        {"scheduled_for": when, "status": "taken"},
    )
    assert missing.status_code == 404
    assert (
        MedicationLog.objects.for_clinic(stage.clinic.pk).count()
        + MedicationLog.objects.for_clinic(stage.other_clinic.pk).count()
        == 0
    )


# ── Plano de cuidado ────────────────────────────────────────────────────────


def _plan(stage: Stage, who: PatientLogin, status: str, **over: Any) -> CarePlan:
    plan = CarePlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_profile_id=who.profile.pk,
        prescribing_professional_id=stage.therapist.pk,
        title=over.pop("title", "Plano de cuidado pós-alta"),
        objective="Manter a rotina de cuidado",
        clinical_rationale="Justificativa interna que o paciente não vê",
        contraindications="Evitar sobrecarga",
        status=status,
        version=over.pop("version", 1),
        valid_from=_today() - timedelta(days=2),
        **over,
    )
    for index, text in enumerate(("Caminhar 20 minutos", "Dormir no mesmo horário")):
        CarePlanAction.objects.for_clinic(stage.clinic.pk).create(
            clinic_id=stage.clinic.pk,
            care_plan=plan,
            action_description=text,
            target_frequency="daily",
            guidance="Com calma",
            is_mandatory=index == 0,
            order=index,
        )
    return plan


def test_care_plan_shows_only_the_visible_plan_without_internal_rationale() -> None:
    stage, ana, bia, ana_h, _bia_h = _world()
    client = Client()
    empty = _json(client, "get", "/api/v1/mobile/care-plan/", ana_h).json()
    assert empty == {"care_plan": None}
    _plan(stage, ana, CarePlanStatus.DRAFT, title="Rascunho")
    _plan(stage, ana, CarePlanStatus.PENDING_SIGNATURE, title="Aguardando assinatura")
    _plan(stage, bia, CarePlanStatus.ACTIVE, title="Plano da Bia")
    assert _json(client, "get", "/api/v1/mobile/care-plan/", ana_h).json() == {
        "care_plan": None
    }
    active = _plan(stage, ana, CarePlanStatus.ACTIVE)
    body = _json(client, "get", "/api/v1/mobile/care-plan/", ana_h).json()["care_plan"]
    assert body["id"] == str(active.pk) and body["status"] == "active"
    assert [a["description"] for a in body["actions"]] == [
        "Caminhar 20 minutos",
        "Dormir no mesmo horário",
    ]
    assert body["response"] is None
    assert "Justificativa interna" not in str(body)


def test_patient_response_is_recorded_audited_and_visible() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    plan = _plan(stage, ana, CarePlanStatus.ACTIVE)
    url = f"/api/v1/mobile/care-plan/{plan.pk}/response/"
    client = Client()
    response = _json(
        client, "post", url, ana_h, {"decision": "accepted", "notes": "Combinado."}
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert (
        body["response"]["decision"] == "accepted"
        and body["response"]["notes"] == "Combinado."
    )
    assert CarePlanPatientResponse.objects.for_clinic(stage.clinic.pk).count() == 1
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(action="routines.care_plan_patient_response", actor_id=ana.user.pk)
        .exists()
    )


def test_refusing_closes_the_plan_and_pausing_pauses_it() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    plan = _plan(stage, ana, CarePlanStatus.ACTIVE)
    url = f"/api/v1/mobile/care-plan/{plan.pk}/response/"
    client = Client()
    assert (
        _json(client, "post", url, ana_h, {"decision": "paused"}).json()["status"]
        == "paused"
    )
    assert (
        _json(client, "post", url, ana_h, {"decision": "refused"}).json()["status"]
        == "revoked"
    )
    # plano encerrado não aceita nova resposta
    assert (
        _json(client, "post", url, ana_h, {"decision": "accepted"}).status_code == 409
    )


def test_care_plan_response_is_refused_for_foreign_draft_or_invalid_input() -> None:
    stage, ana, bia, ana_h, _ = _world()
    theirs = _plan(stage, bia, CarePlanStatus.ACTIVE)
    draft = _plan(stage, ana, CarePlanStatus.DRAFT)
    mine = _plan(stage, ana, CarePlanStatus.ACTIVE, version=2)
    client = Client()
    for target in (theirs, draft):
        response = _json(
            client,
            "post",
            f"/api/v1/mobile/care-plan/{target.pk}/response/",
            ana_h,
            {"decision": "accepted"},
        )
        assert response.status_code == 404
    url = f"/api/v1/mobile/care-plan/{mine.pk}/response/"
    assert _json(client, "post", url, ana_h, {"decision": "obey"}).status_code == 422
    assert (
        _json(
            client, "post", url, ana_h, {"decision": "accepted", "notes": "x" * 2001}
        ).status_code
        == 422
    )
    assert (
        CarePlan.objects.for_clinic(stage.clinic.pk).get(pk=theirs.pk).status
        == "active"
    )
    assert CarePlanPatientResponse.objects.for_clinic(stage.clinic.pk).count() == 0


# ── Rotina e hábitos ────────────────────────────────────────────────────────


def _habit(stage: Stage, who: PatientLogin, **over: Any) -> Habit:
    return create_habit(
        clinic_id=stage.clinic.pk,
        patient_profile_id=who.profile.pk,
        title=over.pop("title", "Beber água"),
        description="Um copo ao acordar",
        **over,
    )


def test_routine_lists_own_habits_and_checks_in_the_window() -> None:
    stage, ana, bia, ana_h, _ = _world()
    habit = _habit(stage, ana)
    _habit(stage, bia, title="Hábito da Bia")
    archived = _habit(stage, ana, title="Arquivado")
    Habit.objects.for_clinic(stage.clinic.pk).filter(pk=archived.pk).update(
        status=HabitStatus.ARCHIVED
    )
    client = Client()
    today = _today()
    ok = _json(
        client,
        "put",
        f"/api/v1/mobile/habits/{habit.pk}/checks/{today}/",
        ana_h,
        {"status": "completed"},
    )
    assert ok.status_code == 200, ok.content
    body = _json(client, "get", "/api/v1/mobile/routine/?days=3", ana_h).json()
    assert [h["title"] for h in body["habits"]] == ["Beber água"]
    assert body["checks"] == [
        {"habit_id": str(habit.pk), "date": today.isoformat(), "status": "completed"}
    ]
    assert (
        _json(client, "get", "/api/v1/mobile/routine/?days=500", ana_h).status_code
        == 200
    )


def test_habit_check_updates_in_place_and_keeps_history() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    habit = _habit(stage, ana)
    url = f"/api/v1/mobile/habits/{habit.pk}/checks/{_today()}/"
    client = Client()
    _json(client, "put", url, ana_h, {"status": "partial"})
    _json(client, "put", url, ana_h, {"status": "completed"})
    assert HabitOccurrence.objects.for_clinic(stage.clinic.pk).count() == 1
    checkin = HabitCheckIn.objects.for_clinic(stage.clinic.pk).get()
    assert checkin.status == "completed" and len(checkin.history) == 2


def test_habit_check_enforces_the_date_window_and_the_schedule() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    today = _today()
    habit = _habit(stage, ana)
    client = Client()
    for day in (today + timedelta(days=1), today - timedelta(days=8)):
        r = _json(
            client,
            "put",
            f"/api/v1/mobile/habits/{habit.pk}/checks/{day}/",
            ana_h,
            {"status": "completed"},
        )
        assert r.status_code == 422 and r.json()["code"] == "invalid_date"
    weekdays_only = _habit(
        stage, ana, title="Só em dias úteis", active_days=[0, 1, 2, 3, 4]
    )
    saturday = next(
        today - timedelta(days=i)
        for i in range(1, 8)
        if (today - timedelta(days=i)).weekday() == 5
    )
    r = _json(
        client,
        "put",
        f"/api/v1/mobile/habits/{weekdays_only.pk}/checks/{saturday}/",
        ana_h,
        {"status": "completed"},
    )
    assert r.status_code == 422 and r.json()["code"] == "not_scheduled"
    assert (
        _json(
            client,
            "put",
            f"/api/v1/mobile/habits/{habit.pk}/checks/{today}/",
            ana_h,
            {"status": "perfect"},
        ).status_code
        == 422
    )
    assert HabitCheckIn.objects.for_clinic(stage.clinic.pk).count() == 0


def test_habit_check_cannot_touch_another_patients_or_archived_habits() -> None:
    stage, ana, bia, ana_h, _ = _world()
    theirs = _habit(stage, bia)
    archived = _habit(stage, ana, title="Arquivado")
    Habit.objects.for_clinic(stage.clinic.pk).filter(pk=archived.pk).update(
        status=HabitStatus.ARCHIVED
    )
    client = Client()
    for target in (theirs, archived):
        url = f"/api/v1/mobile/habits/{target.pk}/checks/{_today()}/"
        assert (
            _json(client, "put", url, ana_h, {"status": "completed"}).status_code == 404
        )
        assert _json(client, "delete", url, ana_h).status_code == 404
    assert HabitOccurrence.objects.for_clinic(stage.clinic.pk).count() == 0


def test_clearing_a_habit_check_is_audited_and_idempotent() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    habit = _habit(stage, ana)
    url = f"/api/v1/mobile/habits/{habit.pk}/checks/{_today()}/"
    client = Client()
    _json(client, "put", url, ana_h, {"status": "completed"})
    assert _json(client, "delete", url, ana_h).status_code == 204
    assert HabitCheckIn.objects.for_clinic(stage.clinic.pk).count() == 0
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(action="delete", resource_type="habit_checkin", actor_id=ana.user.pk)
        .count()
        == 1
    )
    assert _json(client, "delete", url, ana_h).status_code == 204  # idempotente
    # a outra pessoa não consegue desfazer o registro alheio
    _json(client, "put", url, ana_h, {"status": "completed"})
    assert _json(client, "delete", url, bia_h).status_code == 404
    assert HabitCheckIn.objects.for_clinic(stage.clinic.pk).count() == 1


# ── Exercícios da equipe ────────────────────────────────────────────────────


def _exercise(stage: Stage, who: PatientLogin, **over: Any) -> ExerciseAssignment:
    exercise = create_exercise(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        title=over.pop("title", "Registro de pensamentos"),
        instructions="Anote o que sentiu.",
        status=ExerciseStatus.PUBLISHED,
        request_id=uuid4(),
        **over,
    )
    return assign_exercise(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        exercise_id=exercise.pk,
        patient_profile_id=who.profile.pk,
        request_id=uuid4(),
    )


def test_exercises_list_only_the_patients_own_assignments() -> None:
    stage, ana, bia, ana_h, _ = _world()
    mine = _exercise(stage, ana)
    _exercise(stage, bia, title="Do outro paciente")
    cancelled = _exercise(stage, ana, title="Cancelado")
    ExerciseAssignment.objects.for_clinic(stage.clinic.pk).filter(
        pk=cancelled.pk
    ).update(status="cancelled")
    body = _json(Client(), "get", "/api/v1/mobile/exercises/", ana_h).json()
    assert [e["id"] for e in body] == [str(mine.pk)]
    assert body[0]["status"] == "assigned" and body[0]["response"] == ""


def test_completing_an_exercise_stores_the_answer_once() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    assignment = _exercise(stage, ana)
    url = f"/api/v1/mobile/exercises/{assignment.pk}/complete/"
    client = Client()
    done = _json(
        client,
        "post",
        url,
        ana_h,
        {"response": "Percebi que respirar ajuda.", "visibility": "shareable"},
    )
    assert done.status_code == 200, done.content
    body = done.json()
    assert (
        body["status"] == "completed"
        and body["response"] == "Percebi que respirar ajuda."
    )
    assert body["visibility"] == "shareable" and body["completed_at"] is not None
    assert _json(client, "post", url, ana_h, {"response": "de novo"}).status_code == 409


def test_exercise_completion_is_validated_and_isolated() -> None:
    stage, ana, bia, ana_h, _ = _world()
    mine = _exercise(stage, ana)
    theirs = _exercise(stage, bia)
    scale = _exercise(stage, ana, title="Escala", response_format="scale_1_5")
    client = Client()
    base = "/api/v1/mobile/exercises/"
    assert (
        _json(
            client, "post", f"{base}{theirs.pk}/complete/", ana_h, {"response": "x"}
        ).status_code
        == 404
    )
    assert (
        _json(
            client, "post", f"{base}{uuid4()}/complete/", ana_h, {"response": "x"}
        ).status_code
        == 404
    )
    assert (
        _json(
            client, "post", f"{base}{mine.pk}/complete/", ana_h, {"response": ""}
        ).status_code
        == 422
    )
    assert (
        _json(
            client,
            "post",
            f"{base}{mine.pk}/complete/",
            ana_h,
            {"response": "x" * 4001},
        ).status_code
        == 422
    )
    assert (
        _json(
            client,
            "post",
            f"{base}{mine.pk}/complete/",
            ana_h,
            {"response": "ok", "visibility": "public"},
        ).status_code
        == 422
    )
    assert (
        _json(
            client, "post", f"{base}{scale.pk}/complete/", ana_h, {"response": "9"}
        ).status_code
        == 422
    )
    assert (
        _json(
            client, "post", f"{base}{scale.pk}/complete/", ana_h, {"response": "4"}
        ).status_code
        == 200
    )
    assert (
        ExerciseAssignment.objects.for_clinic(stage.clinic.pk).get(pk=theirs.pk).status
        == "assigned"
    )
    assert (
        ExerciseAssignment.objects.for_clinic(stage.clinic.pk).get(pk=mine.pk).status
        == "assigned"
    )


# ── Modo de pouca energia ───────────────────────────────────────────────────


def test_low_energy_needs_configured_actions_before_it_can_be_turned_on() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    client = Client()
    state = _json(client, "get", "/api/v1/mobile/low-energy/", ana_h).json()
    assert state == {
        "actions": [],
        "active": False,
        "started_at": None,
        "ends_at": None,
        "can_activate": False,
    }
    refused = _json(
        client, "put", "/api/v1/mobile/low-energy/", ana_h, {"active": True}
    )
    assert (
        refused.status_code == 422 and refused.json()["code"] == "no_actions_configured"
    )
    configure_low_energy_actions(
        clinic_id=stage.clinic.pk,
        actor=ana.user,
        action_1="Tomar água",
        action_2="Respirar fundo",
        request_id=uuid4(),
    )
    on = _json(
        client, "put", "/api/v1/mobile/low-energy/", ana_h, {"active": True}
    ).json()
    assert on["active"] is True and on["actions"] == ["Tomar água", "Respirar fundo"]
    assert on["started_at"] is not None and on["ends_at"] is not None
    # o estado de uma pessoa não vaza para outra
    other = _json(client, "get", "/api/v1/mobile/low-energy/", bia_h).json()
    assert other["active"] is False and other["actions"] == []
    off = _json(
        client, "put", "/api/v1/mobile/low-energy/", ana_h, {"active": False}
    ).json()
    assert off["active"] is False
    assert (
        LowEnergyMode.objects.for_clinic(stage.clinic.pk)
        .filter(patient_profile_id=bia.profile.pk)
        .count()
        == 0
    )


# ── Transversais ────────────────────────────────────────────────────────────


def test_every_care_route_requires_the_app_token() -> None:
    stage, ana, _bia, _ana_h, _ = _world()
    med = _med(stage.clinic, ana)
    client = Client()
    routes = [
        ("get", "/api/v1/mobile/medications/"),
        ("put", f"/api/v1/mobile/medications/{med.pk}/doses/"),
        ("get", "/api/v1/mobile/care-plan/"),
        ("post", f"/api/v1/mobile/care-plan/{uuid4()}/response/"),
        ("get", "/api/v1/mobile/routine/"),
        ("put", f"/api/v1/mobile/habits/{uuid4()}/checks/{_today()}/"),
        ("delete", f"/api/v1/mobile/habits/{uuid4()}/checks/{_today()}/"),
        ("get", "/api/v1/mobile/exercises/"),
        ("post", f"/api/v1/mobile/exercises/{uuid4()}/complete/"),
        ("get", "/api/v1/mobile/low-energy/"),
        ("put", "/api/v1/mobile/low-energy/"),
    ]
    for method, url in routes:
        response = getattr(client, method)(url, content_type="application/json")
        assert response.status_code == 401, (method, url)


def test_a_blocked_clinic_stops_care_data_with_402() -> None:
    from master_panel.models import TenantSubscription

    stage, ana, _bia, ana_h, _ = _world()
    TenantSubscription.objects.create(
        clinic=stage.clinic, status=TenantSubscription.Status.BLOCKED
    )
    assert (
        _json(Client(), "get", "/api/v1/mobile/medications/", ana_h).status_code == 402
    )
