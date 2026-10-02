"""API do app do paciente: recuperação, vontade de usar, recaída e ajuda."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from audit.models import AuditEvent
from support_network.urgent_plan_models import (
    UrgentLocalResource,
    UrgentSupportContact,
    UrgentSupportPlan,
)
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient_login,
)
from wellness.crisis_models import (
    CrisisAccessLog,
    CrisisResourceConfig,
    GroundingExercise,
)
from wellness.relapse_plan_models import RelapsePlanSection, RelapsePreventionPlan
from wellness.sobriety_models import CravingCheckIn, SobrietyGoal
from wellness.sobriety_services import setup_sobriety_goal

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


def _call(method: str, url: str, headers: dict[str, str], body: Any = None) -> Any:
    kwargs: dict[str, Any] = dict(headers)
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


def _today() -> date:
    return timezone.now().astimezone(SP).date()


def _goal(
    stage: Stage, who: PatientLogin, focus: str = "Álcool", days: int = 10
) -> SobrietyGoal:
    return setup_sobriety_goal(
        clinic_id=stage.clinic.pk,
        patient_profile_id=who.profile.pk,
        substance_or_behavior=focus,
        reference_date=_today() - timedelta(days=days),
        motivations="Minha família",
        actor_id=who.user.pk,
    )


# ── Recuperação ─────────────────────────────────────────────────────────────


def test_recovery_is_empty_until_a_goal_exists_and_never_shows_other_patients() -> None:
    stage, ana, bia, ana_h, _ = _world()
    assert _call("get", "/api/v1/mobile/recovery/", ana_h).json() == {
        "sobriety": None,
        "cravings": [],
    }
    _goal(stage, bia, focus="Jogos de azar")
    mine = _goal(stage, ana)
    body = _call("get", "/api/v1/mobile/recovery/", ana_h).json()
    assert body["sobriety"]["id"] == str(mine.pk)
    assert (
        body["sobriety"]["focus"] == "Álcool" and body["sobriety"]["restart_count"] == 0
    )
    assert set(body["sobriety"]) == {
        "id",
        "goal_type",
        "focus",
        "reference_date",
        "restart_count",
        "motivations",
        "hide_counter",
    }
    assert "Jogos de azar" not in str(body)


def test_hiding_the_counter_only_changes_the_flag_and_is_audited() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    goal = _goal(stage, ana)
    response = _call("put", "/api/v1/mobile/recovery/counter/", ana_h, {"hidden": True})
    assert response.status_code == 200 and response.json()["hide_counter"] is True
    goal.refresh_from_db()
    assert goal.hide_counter is True and goal.restart_count == 0
    assert goal.reference_date == _today() - timedelta(days=10)
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(action="wellness.sobriety_counter_visibility", actor_id=ana.user.pk)
        .exists()
    )
    back = _call("put", "/api/v1/mobile/recovery/counter/", ana_h, {"hidden": False})
    assert back.json()["hide_counter"] is False


def test_restart_resets_the_reference_date_without_losing_history() -> None:
    stage, ana, bia, ana_h, _ = _world()
    goal = _goal(stage, ana)
    others = _goal(stage, bia, focus="Outro foco")
    response = _call("post", "/api/v1/mobile/recovery/restart/", ana_h)
    assert response.status_code == 200
    body = response.json()
    assert body["reference_date"] == _today().isoformat() and body["restart_count"] == 1
    goal.refresh_from_db()
    assert goal.initial_start_date == _today() - timedelta(days=10)  # histórico intacto
    others.refresh_from_db()
    assert others.restart_count == 0 and others.reference_date != _today()


def test_counter_routes_answer_404_when_there_is_no_goal() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    assert (
        _call(
            "put", "/api/v1/mobile/recovery/counter/", ana_h, {"hidden": True}
        ).status_code
        == 404
    )
    assert _call("post", "/api/v1/mobile/recovery/restart/", ana_h).status_code == 404


def test_craving_is_recorded_privately_and_linked_to_the_active_goal() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    goal = _goal(stage, ana)
    created = _call(
        "post",
        "/api/v1/mobile/recovery/cravings/",
        ana_h,
        {
            "intensity": 7,
            "triggers_context": "Depois do trabalho",
            "coping_strategy_used": "Caminhada",
        },
    )
    assert created.status_code == 201, created.content
    row = CravingCheckIn.objects.for_clinic(stage.clinic.pk).get()
    assert row.patient_profile_id == ana.profile.pk and row.sobriety_goal_id == goal.pk
    assert row.protected_from_lockscreen is True and row.intensity == 7
    mine = _call("get", "/api/v1/mobile/recovery/", ana_h).json()["cravings"]
    assert [c["intensity"] for c in mine] == [7]
    assert _call("get", "/api/v1/mobile/recovery/", bia_h).json()["cravings"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"intensity": 0},
        {"intensity": 11},
        {"intensity": 5, "triggers_context": "x" * 2001},
        {"intensity": 5, "coping_strategy_used": "x" * 2001},
        {"intensity": "alta"},
    ],
)
def test_craving_validation_rejects_bad_input_without_saving(
    payload: dict[str, Any],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", "/api/v1/mobile/recovery/cravings/", ana_h, payload)
    assert response.status_code == 422
    assert CravingCheckIn.objects.for_clinic(stage.clinic.pk).count() == 0


def test_craving_can_be_logged_before_a_goal_exists() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "post", "/api/v1/mobile/recovery/cravings/", ana_h, {"intensity": 3}
    )
    assert response.status_code == 201
    assert (
        CravingCheckIn.objects.for_clinic(stage.clinic.pk).get().sobriety_goal_id
        is None
    )


# ── Prevenção de recaída ────────────────────────────────────────────────────


def test_relapse_plan_is_read_only_ordered_and_private_to_the_patient() -> None:
    stage, ana, bia, ana_h, _ = _world()
    assert _call("get", "/api/v1/mobile/relapse-plan/", ana_h).json() == {
        "relapse_plan": None
    }
    plan = RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_profile_id=ana.profile.pk,
        last_reviewed_at=timezone.now(),
    )
    for order, (kind, title) in enumerate(
        (("coping_strategies", "O que faço"), ("triggers", "Gatilhos"))
    ):
        RelapsePlanSection.objects.for_clinic(stage.clinic.pk).create(
            clinic_id=stage.clinic.pk,
            relapse_plan=plan,
            section_type=kind,
            title=title,
            content=f"Conteúdo {title}",
            order=order,
        )
    other = RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_profile_id=bia.profile.pk,
        title="Plano da Bia",
    )
    assert other.pk != plan.pk
    body = _call("get", "/api/v1/mobile/relapse-plan/", ana_h).json()["relapse_plan"]
    assert body["id"] == str(plan.pk)
    assert [s["title"] for s in body["sections"]] == ["O que faço", "Gatilhos"]
    assert "Plano da Bia" not in str(body)
    for method in ("post", "put", "delete"):
        assert _call(method, "/api/v1/mobile/relapse-plan/", ana_h).status_code == 405


# ── Ajuda urgente ───────────────────────────────────────────────────────────


def test_help_has_safe_defaults_when_the_clinic_configured_nothing() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    body = _call("get", "/api/v1/mobile/help/", ana_h).json()
    assert (
        body["emergency_medical"],
        body["emergency_fire"],
        body["emotional_support"],
    ) == (
        "192",
        "193",
        "188",
    )
    assert "não é um serviço de emergência" in body["disclaimer"]
    assert body["urgent_plan"] is None and body["custom_helpline"] is None


def test_help_returns_the_patients_own_plan_and_contacts_only() -> None:
    stage, ana, bia, ana_h, _ = _world()
    CrisisResourceConfig.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        custom_helpline_name="Linha da clínica",
        custom_helpline_number="0800 000 0000",
    )
    GroundingExercise.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        title="5-4-3-2-1",
        instructions_markdown="Olhe ao redor",
        steps=["Veja 5 coisas", "Toque 4 coisas"],
        duration_seconds=120,
    )
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_id=ana.profile.pk,
        personal_instructions="Respirar e ligar para a Marta",
        calming_strategies=["Água gelada", "Música"],
    )
    for order, (name, active) in enumerate(
        (("Marta", True), ("Inativa", False), ("Pedro", True))
    ):
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk).create(
            clinic_id=stage.clinic.pk,
            plan=plan,
            priority_order=order + 1,
            name=name,
            relationship="Família",
            phone_number=f"+55 81 9000-000{order}",
            is_active=active,
        )
    their_plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_id=bia.profile.pk,
        personal_instructions="Do outro",
    )
    UrgentSupportContact.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        plan=their_plan,
        name="Contato da Bia",
        relationship="Amiga",
        phone_number="+55 81 9111-1111",
    )
    UrgentLocalResource.infrastructure_objects.create(
        clinic=stage.clinic,
        region="BR",
        resource_name="CAPS local",
        service_type="caps",
        contact_number="+55 81 3000-0000",
    )
    body = _call("get", "/api/v1/mobile/help/", ana_h).json()
    assert body["custom_helpline"] == {
        "name": "Linha da clínica",
        "number": "0800 000 0000",
    }
    assert [c["name"] for c in body["urgent_plan"]["contacts"]] == ["Marta", "Pedro"]
    assert body["urgent_plan"]["calming_strategies"] == ["Água gelada", "Música"]
    assert [r["name"] for r in body["local_resources"]] == ["CAPS local"]
    assert [g["title"] for g in body["grounding_exercises"]] == ["5-4-3-2-1"]
    assert "Contato da Bia" not in str(body) and "Do outro" not in str(body)
    assert "Inativa" not in str(body)


def test_opening_help_has_no_side_effects() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    events_before = AuditEvent.objects.for_clinic(stage.clinic.pk).count()
    assert _call("get", "/api/v1/mobile/help/", ana_h).status_code == 200
    assert CrisisAccessLog.objects.for_clinic(stage.clinic.pk).count() == 0
    assert AuditEvent.objects.for_clinic(stage.clinic.pk).count() == events_before
    assert ana.user.pk is not None


def test_help_stays_available_when_the_clinic_billing_is_blocked() -> None:
    from master_panel.models import TenantSubscription

    stage, _ana, _bia, ana_h, _ = _world()
    TenantSubscription.objects.create(
        clinic=stage.clinic, status=TenantSubscription.Status.BLOCKED
    )
    assert _call("get", "/api/v1/mobile/help/", ana_h).status_code == 200
    assert _call("get", "/api/v1/mobile/recovery/", ana_h).status_code == 402


def test_every_recovery_route_requires_the_app_token() -> None:
    client = Client()
    for method, url in (
        ("get", "/api/v1/mobile/recovery/"),
        ("put", "/api/v1/mobile/recovery/counter/"),
        ("post", "/api/v1/mobile/recovery/restart/"),
        ("post", "/api/v1/mobile/recovery/cravings/"),
        ("get", "/api/v1/mobile/relapse-plan/"),
        ("get", "/api/v1/mobile/help/"),
    ):
        response = getattr(client, method)(url, content_type="application/json")
        assert response.status_code == 401, (method, url)
    assert uuid4() is not None
