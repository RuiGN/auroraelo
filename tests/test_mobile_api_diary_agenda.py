"""API do app do paciente: check-in, diário, consultas e metas.

Foco em posse (id de outra pessoa = 404), em ids vindos do cliente (profissional,
unidade, serviço) e em nunca devolver dado de outro paciente.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from django.test import Client

from goals import services as goal_services
from goals.models import GoalStep
from journal import services as journal_services
from journal.models import DailyCheckIn, JournalAccessRequest, JournalEntry
from people import services as people_services
from scheduling.models import (
    Appointment,
    AvailabilityPattern,
    Service,
    Unit,
)
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient_login,
)

pytestmark = pytest.mark.django_db

SP = ZoneInfo("America/Sao_Paulo")
LOGIN = "/api/v1/mobile/auth/login/"
BASE = "/api/v1/mobile"


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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _call(method: str, url: str, headers: dict[str, str], body: Any = None) -> Any:
    kwargs: dict[str, Any] = {"headers": headers}
    if body is not None:
        kwargs["data"] = body
        kwargs["content_type"] = "application/json"
    return getattr(Client(), method)(url, **kwargs)


def _world() -> tuple[
    Stage, PatientLogin, PatientLogin, dict[str, str], dict[str, str]
]:
    stage = build_stage()
    ana = make_patient_login(stage.clinic, stage.admin, name="Ana Souza")
    bia = make_patient_login(stage.clinic, stage.admin, name="Bia Lima")
    return stage, ana, bia, _login(ana), _login(bia)


ANSWERS = {
    "general_state": 3,
    "anxiety": 4,
    "sadness": 2,
    "irritability": 2,
    "energy": 3,
    "sleep_quality": 3,
    "motivation": 4,
}


# ── Check-in ────────────────────────────────────────────────────────────────


def test_checkin_creates_the_default_questionnaire_and_updates_in_place() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    first = _call(
        "post", f"{BASE}/checkins/", ana_h,
        {"answers": ANSWERS, "notes": "Dia corrido", "visibility": "private"},
    )  # fmt: skip
    assert first.status_code == 200, first.content
    body = first.json()
    assert body["answers"]["anxiety"] == 4 and body["notes"] == "Dia corrido"
    assert body["visibility"] == "private"
    changed = {**ANSWERS, "anxiety": 2}
    second = _call(
        "post", f"{BASE}/checkins/", ana_h,
        {"answers": changed, "notes": "", "visibility": "shareable"},
    )  # fmt: skip
    assert second.status_code == 200
    assert second.json()["id"] == body["id"]
    assert second.json()["answers"]["anxiety"] == 2
    assert second.json()["visibility"] == "shareable" and second.json()["notes"] == ""
    assert DailyCheckIn.objects.for_clinic(stage.clinic.pk).count() == 1


@pytest.mark.parametrize(
    "answers",
    [
        {k: v for k, v in ANSWERS.items() if k != "energy"},
        {**ANSWERS, "energy": 0},
        {**ANSWERS, "energy": 6},
        {**ANSWERS, "surpresa": 3},
    ],
)
def test_checkin_requires_exactly_the_seven_scale_answers(
    answers: dict[str, int],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", f"{BASE}/checkins/", ana_h, {"answers": answers})
    assert response.status_code == 422
    assert DailyCheckIn.objects.for_clinic(stage.clinic.pk).count() == 0


def test_diary_lists_only_the_patients_own_records_newest_first() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _call("post", f"{BASE}/checkins/", ana_h, {"answers": ANSWERS})
    _call("post", f"{BASE}/checkins/", bia_h, {"answers": {**ANSWERS, "anxiety": 1}})
    for who, headers, context in ((ana, ana_h, "Meu dia"), (bia, bia_h, "Dia da Bia")):
        body = {"mood": 4, "emotions": ["calm", "hope"], "intensity": 2}
        payload = {**body, "context": context}
        created = _call("post", f"{BASE}/journal/", headers, payload)
        assert created.status_code == 201, created.content
        assert created.json()["visibility"] == "private"
        assert who.user.pk is not None
    mine = _call("get", f"{BASE}/diary/", ana_h).json()
    assert [e["context"] for e in mine["entries"]] == ["Meu dia"]
    assert [c["answers"]["anxiety"] for c in mine["checkins"]] == [4]
    assert "Bia" not in str(mine)
    assert stage.clinic.pk is not None


# ── Diário ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "payload",
    [
        {"mood": 0, "intensity": 2, "context": "x"},
        {"mood": 3, "intensity": 6, "context": "x"},
        {"mood": 3, "intensity": 2, "context": ""},
        {"mood": 3, "intensity": 2, "context": "x" * 4001},
        {"mood": 3, "intensity": 2, "context": "x", "visibility": "public"},
    ],
)
def test_journal_rejects_invalid_input_without_saving(payload: dict[str, Any]) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    assert _call("post", f"{BASE}/journal/", ana_h, payload).status_code == 422
    assert JournalEntry.objects.for_clinic(stage.clinic.pk).count() == 0


def test_journal_rejects_unknown_emotions() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "post", f"{BASE}/journal/", ana_h,
        {"mood": 3, "intensity": 2, "context": "x", "emotions": ["raiva-do-vizinho"]},
    )  # fmt: skip
    assert response.status_code == 422 and response.json()["code"] == "entry_rejected"


def test_only_the_owner_changes_who_can_see_an_entry() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    entry = journal_services.create_journal_entry(
        clinic_id=stage.clinic.pk, actor=ana.user, patient_profile_id=ana.profile.pk,
        mood=3, emotions=[], intensity=2, context="Privado", triggers="", reactions="",
        strategies="", visibility="private", request_id=uuid4(),
    )  # fmt: skip
    url = f"{BASE}/journal/{entry.pk}/visibility/"
    assert _call("put", url, bia_h, {"visibility": "shareable"}).status_code == 404
    entry.refresh_from_db()
    assert entry.visibility == "private"
    ok = _call("put", url, ana_h, {"visibility": "shareable"})
    assert ok.status_code == 200 and ok.json()["visibility"] == "shareable"
    assert _call("put", url, ana_h, {"visibility": "todos"}).status_code == 422
    assert bia.user.pk is not None


def _therapist_link(stage: Stage, who: PatientLogin) -> None:
    people_services.create_patient_care_relationship(
        clinic_id=stage.clinic.pk, actor=stage.admin, therapist_id=stage.therapist.pk,
        patient_profile_id=who.profile.pk, function="primary_therapist",
        valid_from=date.today(), valid_until=None, request_id=uuid4(),
    )  # fmt: skip


def test_access_requests_are_answered_only_by_the_owner_and_only_once() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _therapist_link(stage, ana)
    entry = journal_services.create_journal_entry(
        clinic_id=stage.clinic.pk, actor=ana.user, patient_profile_id=ana.profile.pk,
        mood=3, emotions=[], intensity=2, context="Amarelo", triggers="", reactions="",
        strategies="", visibility="confirmation_required", request_id=uuid4(),
    )  # fmt: skip
    asked = journal_services.request_journal_entry_access(
        clinic_id=stage.clinic.pk, therapist=stage.therapist, journal_entry_id=entry.pk,
        purpose="Discutir na sessão", expires_at=None, request_id=uuid4(),
    )  # fmt: skip
    listing = _call("get", f"{BASE}/journal/access-requests/", ana_h).json()
    assert [r["id"] for r in listing] == [str(asked.pk)]
    assert listing[0]["purpose"] == "Discutir na sessão"
    assert _call("get", f"{BASE}/journal/access-requests/", bia_h).json() == []
    url = f"{BASE}/journal/access-requests/{asked.pk}/respond/"
    assert _call("post", url, bia_h, {"approve": True}).status_code == 404
    approved = _call("post", url, ana_h, {"approve": True, "expires_in_days": 30})
    assert approved.status_code == 204
    asked.refresh_from_db()
    assert asked.status == JournalAccessRequest.Status.GRANTED and asked.expires_at
    again = _call("post", url, ana_h, {"approve": False})
    assert again.status_code == 409 and again.json()["code"] == "already_answered"
    assert _call("get", f"{BASE}/journal/access-requests/", ana_h).json() == []


def test_access_requests_can_be_refused() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    _therapist_link(stage, ana)
    entry = journal_services.create_journal_entry(
        clinic_id=stage.clinic.pk, actor=ana.user, patient_profile_id=ana.profile.pk,
        mood=3, emotions=[], intensity=2, context="Amarelo", triggers="", reactions="",
        strategies="", visibility="confirmation_required", request_id=uuid4(),
    )  # fmt: skip
    asked = journal_services.request_journal_entry_access(
        clinic_id=stage.clinic.pk, therapist=stage.therapist, journal_entry_id=entry.pk,
        purpose="Discutir na sessão", expires_at=None, request_id=uuid4(),
    )  # fmt: skip
    url = f"{BASE}/journal/access-requests/{asked.pk}/respond/"
    assert _call("post", url, ana_h, {"approve": False}).status_code == 204
    asked.refresh_from_db()
    assert asked.status == JournalAccessRequest.Status.REJECTED


# ── Consultas ───────────────────────────────────────────────────────────────


def _agenda(stage: Stage) -> tuple[Service, Unit]:
    service = Service.infrastructure_objects.create(
        clinic_id=stage.clinic.pk, name="Sessão individual", duration_minutes=50,
        buffer_minutes=10, is_active=True,
    )  # fmt: skip
    unit = Unit.infrastructure_objects.create(
        clinic_id=stage.clinic.pk,
        name="Unidade Centro",
        timezone_name="America/Sao_Paulo",
    )
    for weekday in range(7):
        AvailabilityPattern.infrastructure_objects.create(
            clinic_id=stage.clinic.pk,
            professional_id=stage.therapist.pk,
            unit_id=unit.pk,
            weekday=weekday,
            start_time=time(9, 0),
            end_time=time(12, 0),
            valid_from=date(2020, 1, 1),
        )
    return service, unit


def _first_option(headers: dict[str, str]) -> dict[str, Any]:
    options = _call("get", f"{BASE}/booking/options/", headers).json()
    assert options, "sem opções de agendamento"
    return options[0]


def _request(
    headers: dict[str, str], option: dict[str, Any], slot: str, **extra: Any
) -> Any:
    body = {
        "service_id": option["service_id"],
        "professional_id": option["professional_id"],
        "unit_id": option["unit_id"],
        "start_at": slot,
        "idempotency_key": "chave-" + uuid4().hex[:12],
        **extra,
    }
    return _call("post", f"{BASE}/appointments/", headers, body)


def test_booking_options_only_offer_the_linked_team_with_free_slots() -> None:
    stage, ana, _bia, ana_h, bia_h = _world()
    _agenda(stage)
    assert _call("get", f"{BASE}/booking/options/", ana_h).json() == []  # sem vínculo
    _therapist_link(stage, ana)
    options = _call("get", f"{BASE}/booking/options/", ana_h).json()
    assert len(options) == 1
    option = options[0]
    assert option["professional_id"] == str(stage.therapist.pk)
    assert option["service_name"] == "Sessão individual" and option["free_slots"]
    assert all(
        datetime.fromisoformat(s) > datetime.now(SP) for s in option["free_slots"]
    )
    assert _call("get", f"{BASE}/booking/options/", bia_h).json() == []


def test_requesting_an_appointment_is_idempotent_and_does_not_leak() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _agenda(stage)
    _therapist_link(stage, ana)
    _therapist_link(stage, bia)
    option = _first_option(ana_h)
    slot, other_slot = option["free_slots"][0], option["free_slots"][5]
    key = "mesma-chave-123"
    first = _request(ana_h, option, slot, idempotency_key=key)
    assert first.status_code == 201, first.content
    assert first.json()["status"] == "requested"
    assert (
        first.json()["professional_name"]
        and first.json()["unit_name"] == "Unidade Centro"
    )
    replay = _request(ana_h, option, slot, idempotency_key=key)
    assert replay.status_code == 201 and replay.json()["id"] == first.json()["id"]
    # a mesma chave de outra pessoa é outra solicitação (a chave é única por clínica)
    theirs = _request(bia_h, option, other_slot, idempotency_key=key)
    assert theirs.status_code == 201
    assert theirs.json()["id"] != first.json()["id"]
    assert Appointment.objects.for_clinic(stage.clinic.pk).count() == 2
    assert [a["id"] for a in _call("get", f"{BASE}/appointments/", ana_h).json()] == [
        first.json()["id"]
    ]


def test_appointment_requests_validate_every_id_the_client_sends() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    _agenda(stage)
    _therapist_link(stage, ana)
    option = _first_option(ana_h)
    slot = option["free_slots"][0]
    outsider = Unit.infrastructure_objects.create(
        clinic_id=stage.other_clinic.pk,
        name="Unidade de fora",
        timezone_name="America/Sao_Paulo",
    )
    cases = {
        "profissional fora do vínculo": {"professional_id": str(stage.admin.pk)},
        "unidade de outra clínica": {"unit_id": str(outsider.pk)},
        "serviço inexistente": {"service_id": str(uuid4())},
    }
    for label, override in cases.items():
        response = _request(ana_h, {**option, **override}, slot)
        assert response.status_code == 404, label
    naive = _request(ana_h, option, slot[:19])
    assert naive.status_code == 422 and naive.json()["code"] == "timezone_required"
    taken = _request(ana_h, option, "2030-01-01T03:17:00-03:00")
    assert taken.status_code == 422 and taken.json()["code"] == "slot_unavailable"
    assert Appointment.objects.for_clinic(stage.clinic.pk).count() == 0


def test_cancel_and_reschedule_only_touch_the_patients_own_appointments() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _agenda(stage)
    _therapist_link(stage, ana)
    _therapist_link(stage, bia)
    option = _first_option(ana_h)
    mine = _request(ana_h, option, option["free_slots"][0]).json()
    theirs = _request(bia_h, option, option["free_slots"][3]).json()
    other_url = f"{BASE}/appointments/{theirs['id']}"
    assert (
        _call("post", f"{other_url}/cancel/", ana_h, {"reason": "x"}).status_code == 404
    )
    assert (
        _call(
            "post",
            f"{other_url}/reschedule/",
            ana_h,
            {"start_at": option["free_slots"][6]},
        ).status_code
        == 404
    )
    resched = _call(
        "post", f"{BASE}/appointments/{mine['id']}/reschedule/", ana_h,
        {"start_at": option["free_slots"][8]},
    )  # fmt: skip
    assert resched.status_code == 200, resched.content
    assert resched.json()["status"] == "reschedule_requested"
    bad = _call(
        "post", f"{BASE}/appointments/{mine['id']}/reschedule/", ana_h,
        {"start_at": "2030-01-01T03:17:00-03:00"},
    )  # fmt: skip
    assert bad.status_code == 422
    cancelled = _call(
        "post",
        f"{BASE}/appointments/{mine['id']}/cancel/",
        ana_h,
        {"reason": "Imprevisto"},
    )
    assert cancelled.status_code == 200
    assert (
        cancelled.json()["status"] == "canceled"
        and cancelled.json()["cancel_reason"] == "Imprevisto"
    )
    again = _call(
        "post", f"{BASE}/appointments/{mine['id']}/cancel/", ana_h, {"reason": ""}
    )
    assert again.status_code == 409
    still = Appointment.objects.for_clinic(stage.clinic.pk).get(pk=theirs["id"])
    assert still.status == "requested"


def test_patient_can_cancel_an_appointment_the_team_booked_for_them() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _agenda(stage)
    _therapist_link(stage, ana)
    _therapist_link(stage, bia)
    option = _first_option(ana_h)
    mine = _request(ana_h, option, option["free_slots"][0]).json()
    Appointment.infrastructure_objects.filter(pk=mine["id"]).update(
        requested_by_id=stage.admin.pk
    )
    url = f"{BASE}/appointments/{mine['id']}/cancel/"
    assert _call("post", url, bia_h, {"reason": ""}).status_code == 404
    done = _call("post", url, ana_h, {"reason": "Viagem"})
    assert done.status_code == 200 and done.json()["status"] == "canceled"


# ── Metas ───────────────────────────────────────────────────────────────────


def _goal(stage: Stage, who: PatientLogin, title: str, steps: list[str]) -> Any:
    return goal_services.create_goal(
        clinic_id=stage.clinic.pk, actor=who.user, request_id=uuid4(), title=title,
        description="Descrição", horizon="short", priority=2, due_date=None,
        steps=steps, visibility="private",
    )  # fmt: skip


def test_goals_list_only_the_patients_own_with_steps() -> None:
    stage, ana, bia, ana_h, _ = _world()
    mine = _goal(stage, ana, "Caminhar", ["Sair 10 min", "Sair 20 min"])
    _goal(stage, bia, "Meta da Bia", ["Passo"])
    body = _call("get", f"{BASE}/goals/", ana_h).json()
    assert [g["id"] for g in body] == [str(mine.pk)]
    assert [s["description"] for s in body[0]["steps"]] == [
        "Sair 10 min",
        "Sair 20 min",
    ]
    assert set(body[0]) == {
        "id",
        "title",
        "description",
        "horizon",
        "due_date",
        "status",
        "steps",
    }


def test_steps_and_status_follow_ownership() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    mine = _goal(stage, ana, "Caminhar", ["Sair 10 min"])
    theirs = _goal(stage, bia, "Da Bia", ["Passo da Bia"])
    my_step = GoalStep.objects.for_clinic(stage.clinic.pk).filter(goal=mine).first()
    their_step = (
        GoalStep.objects.for_clinic(stage.clinic.pk).filter(goal=theirs).first()
    )
    assert my_step is not None and their_step is not None
    done = _call("put", f"{BASE}/goals/steps/{my_step.pk}/", ana_h, {"is_done": True})
    assert done.status_code == 200 and done.json()["steps"][0]["is_done"] is True
    assert (
        _call(
            "put", f"{BASE}/goals/steps/{their_step.pk}/", ana_h, {"is_done": True}
        ).status_code
        == 404
    )
    their_step.refresh_from_db()
    assert their_step.is_done is False
    paused = _call(
        "put", f"{BASE}/goals/{mine.pk}/status/", ana_h, {"status": "paused"}
    )
    assert paused.status_code == 200 and paused.json()["status"] == "paused"
    assert (
        _call(
            "put", f"{BASE}/goals/{theirs.pk}/status/", ana_h, {"status": "paused"}
        ).status_code
        == 404
    )
    assert (
        _call(
            "put", f"{BASE}/goals/{mine.pk}/status/", ana_h, {"status": "archived"}
        ).status_code
        == 422
    )


def test_every_new_route_requires_the_app_token() -> None:
    client = Client()
    for method, url in (
        ("get", f"{BASE}/diary/"),
        ("post", f"{BASE}/checkins/"),
        ("post", f"{BASE}/journal/"),
        ("put", f"{BASE}/journal/{uuid4()}/visibility/"),
        ("get", f"{BASE}/journal/access-requests/"),
        ("post", f"{BASE}/journal/access-requests/{uuid4()}/respond/"),
        ("get", f"{BASE}/appointments/"),
        ("get", f"{BASE}/booking/options/"),
        ("post", f"{BASE}/appointments/"),
        ("post", f"{BASE}/appointments/{uuid4()}/cancel/"),
        ("post", f"{BASE}/appointments/{uuid4()}/reschedule/"),
        ("get", f"{BASE}/goals/"),
        ("put", f"{BASE}/goals/steps/{uuid4()}/"),
        ("put", f"{BASE}/goals/{uuid4()}/status/"),
    ):
        response = getattr(client, method)(url, content_type="application/json")
        assert response.status_code == 401, (method, url)
