"""API do app do paciente: o conteúdo pessoal que o próprio paciente escreve.

Meta de recuperação, plano de prevenção de recaída, plano de apoio urgente (com as
pessoas de confiança) e as ações do modo de pouca energia. O ponto central é a posse:
os serviços de domínio autorizam só por clínica, então cada rota resolve o objeto pelo
perfil do paciente da sessão. Há teste de "id de outra pessoa" e de "outra clínica".
O telefone de uma pessoa de confiança é dado de terceiro: nunca em log, nunca na
auditoria, e só volta ao próprio paciente.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from audit.models import AuditEvent
from clinics.models import ClinicMembership
from goals.low_energy_models import LowEnergyActionTemplate, LowEnergyMode
from support_network.events import urgent_action_confirmed, urgent_action_previewed
from support_network.urgent_plan_models import (
    UrgentActionLog,
    UrgentSupportContact,
    UrgentSupportPlan,
)
from support_network.urgent_services import (
    UrgentContactLimitError,
    deactivate_urgent_contact,
    register_urgent_contact,
    update_urgent_contact,
)
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient,
    make_patient_login,
)
from tests.factories import ClinicMembershipFactory
from wellness.crisis_models import CrisisAccessLog
from wellness.relapse_plan_models import (
    RelapsePlanSection,
    RelapsePlanShare,
    RelapsePreventionPlan,
)
from wellness.relapse_services import (
    remove_relapse_plan_section,
    share_relapse_plan_section,
)
from wellness.sobriety_models import SobrietyGoal

pytestmark = pytest.mark.django_db

SP = ZoneInfo("America/Sao_Paulo")
LOGIN = "/api/v1/mobile/auth/login/"
LOGOUT = "/api/v1/mobile/auth/logout/"
GOAL = "/api/v1/mobile/recovery/goal/"
RELAPSE = "/api/v1/mobile/relapse-plan/"
URGENT = "/api/v1/mobile/urgent-plan/"
CONTACTS = "/api/v1/mobile/urgent-plan/contacts/"
HELP = "/api/v1/mobile/help/"
LOW_ENERGY = "/api/v1/mobile/low-energy/"
LOW_ENERGY_ACTIONS = "/api/v1/mobile/low-energy/actions/"
PHONE = "+55 (81) 98765-4321"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _login(who: PatientLogin, clinic_id: UUID | None = None) -> dict[str, str]:
    body: dict[str, str] = {
        "email": who.user.email,
        "password": who.password,
        "device_label": "Teste",
    }
    if clinic_id is not None:
        body["clinic_id"] = str(clinic_id)
    response = Client().post(LOGIN, body, content_type="application/json")
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


def _goal_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "goal_type": "reduction",
        "focus": "Álcool",
        "reference_date": (_today() - timedelta(days=5)).isoformat(),
        "motivations": "Estar mais presente com a minha família",
        "hide_counter": False,
    }
    body.update(changes)
    return body


def _contact_body(**changes: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Marta",
        "relationship": "Irmã",
        "phone_number": PHONE,
    }
    body.update(changes)
    return body


def _add_contact(headers: dict[str, str], **changes: Any) -> dict[str, Any]:
    response = _call("post", CONTACTS, headers, _contact_body(**changes))
    assert response.status_code == 201, response.content
    created: dict[str, Any] = response.json()
    return created


def _relapse_body() -> dict[str, Any]:
    return {
        "title": "Meu plano",
        "sections": [
            {
                "section_type": "triggers",
                "title": "Gatilhos",
                "content": "Fim de semana sozinho",
            },
            {
                "section_type": "coping_strategies",
                "content": "Caminhar e ligar para a Marta",
            },
        ],
    }


def _audit_dump(clinic_id: UUID) -> str:
    rows = AuditEvent.objects.for_clinic(clinic_id).values()
    return " ".join(str(row) for row in rows)


def _events(clinic_id: UUID, *names: str) -> list[AuditEvent]:
    return list(
        AuditEvent.objects.for_clinic(clinic_id)
        .filter(action__in=names)
        .order_by("sequence")
    )


# ── Meta de recuperação ─────────────────────────────────────────────────────


def test_goal_is_created_private_whatever_the_client_sends() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    response = _call(
        "post",
        GOAL,
        ana_h,
        _goal_body(
            hide_counter=True,
            is_private=False,
            clinic_id=str(stage.other_clinic.pk),
            patient_id=str(bia.profile.pk),
        ),
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["goal_type"] == "reduction" and body["focus"] == "Álcool"
    assert body["hide_counter"] is True and body["restart_count"] == 0
    assert body["reference_date"] == (_today() - timedelta(days=5)).isoformat()
    assert set(body) == {
        "id",
        "goal_type",
        "focus",
        "reference_date",
        "restart_count",
        "motivations",
        "hide_counter",
    }
    row = SobrietyGoal.objects.for_clinic(stage.clinic.pk).get()
    assert row.is_private is True and row.is_active is True
    assert row.patient_profile_id == ana.profile.pk
    assert row.initial_start_date == row.reference_date
    assert SobrietyGoal.objects.for_clinic(stage.other_clinic.pk).count() == 0
    mine = _call("get", "/api/v1/mobile/recovery/", ana_h).json()["sobriety"]
    assert mine["id"] == body["id"]
    assert _call("get", "/api/v1/mobile/recovery/", bia_h).json()["sobriety"] is None


def test_a_second_active_goal_is_a_conflict_and_nothing_is_saved() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    first = _call("post", GOAL, ana_h, _goal_body())
    assert first.status_code == 201
    again = _call("post", GOAL, ana_h, _goal_body(focus="Outro foco"))
    assert again.status_code == 409
    assert again.json()["code"] == "already_exists"
    assert SobrietyGoal.objects.for_clinic(stage.clinic.pk).count() == 1
    assert _call("post", "/api/v1/mobile/recovery/restart/", ana_h).status_code == 200
    assert _call("post", GOAL, ana_h, _goal_body()).status_code == 409
    SobrietyGoal.objects.for_clinic(stage.clinic.pk).update(is_active=False)
    third = _call("post", GOAL, ana_h, _goal_body(focus="Novo começo"))
    assert third.status_code == 201 and ana.profile.pk is not None
    assert (
        SobrietyGoal.objects.for_clinic(stage.clinic.pk).filter(is_active=True).count()
        == 1
    )


def test_another_patients_goal_never_blocks_mine() -> None:
    _stage, _ana, _bia, ana_h, bia_h = _world()
    assert _call("post", GOAL, bia_h, _goal_body(focus="Jogos")).status_code == 201
    assert _call("post", GOAL, ana_h, _goal_body()).status_code == 201


@pytest.mark.parametrize("zone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
def test_goal_date_is_checked_in_the_patients_time_zone(zone: str) -> None:
    stage, ana, _bia, _h, _ = _world()
    ana.profile.timezone_name = zone
    ana.profile.save()
    headers = _login(ana)
    today = timezone.now().astimezone(ZoneInfo(zone)).date()
    future = _call(
        "post",
        GOAL,
        headers,
        _goal_body(reference_date=(today + timedelta(days=1)).isoformat()),
    )
    assert future.status_code == 422 and future.json()["code"] == "invalid_date"
    assert SobrietyGoal.objects.for_clinic(stage.clinic.pk).count() == 0
    ok = _call("post", GOAL, headers, _goal_body(reference_date=today.isoformat()))
    assert ok.status_code == 201 and ok.json()["reference_date"] == today.isoformat()


def test_goal_date_far_in_the_past_is_refused() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", GOAL, ana_h, _goal_body(reference_date="1850-01-01"))
    assert response.status_code == 422 and response.json()["code"] == "invalid_date"


@pytest.mark.parametrize(
    "changes",
    [
        {"goal_type": "total"},
        {"goal_type": ""},
        {"focus": ""},
        {"focus": "x" * 129},
        {"motivations": "x" * 2001},
        {"reference_date": "ontem"},
        {"hide_counter": "talvez"},
    ],
)
def test_goal_format_errors_are_422_and_save_nothing(changes: dict[str, Any]) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", GOAL, ana_h, _goal_body(**changes))
    assert response.status_code == 422
    assert SobrietyGoal.objects.for_clinic(stage.clinic.pk).count() == 0


def test_goal_with_a_blank_focus_is_a_stable_422() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", GOAL, ana_h, _goal_body(focus="   "))
    assert response.status_code == 422 and response.json()["code"] == "invalid_focus"
    for field in ("goal_type", "focus", "reference_date"):
        body = _goal_body()
        del body[field]
        assert _call("post", GOAL, ana_h, body).status_code == 422
    assert SobrietyGoal.objects.for_clinic(stage.clinic.pk).count() == 0


def test_goal_accepts_the_maximum_sizes() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "post",
        GOAL,
        ana_h,
        _goal_body(
            focus="f" * 128, motivations="m" * 2000, reference_date=_today().isoformat()
        ),
    )
    assert response.status_code == 201, response.content


# ── Plano de prevenção de recaída ───────────────────────────────────────────


def test_relapse_plan_is_created_updated_and_versioned() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    created = _call("put", RELAPSE, ana_h, _relapse_body())
    assert created.status_code == 200, created.content
    plan = created.json()["relapse_plan"]
    assert plan["title"] == "Meu plano" and plan["version"] == 1
    assert plan["last_reviewed_at"] is not None
    assert [(s["type"], s["title"]) for s in plan["sections"]] == [
        ("triggers", "Gatilhos"),
        ("coping_strategies", "Estratégias pessoais de enfrentamento"),
    ]
    assert _call("get", RELAPSE, ana_h).json() == created.json()  # mesmo formato do GET

    triggers_id = plan["sections"][0]["id"]
    second = _call(
        "put",
        RELAPSE,
        ana_h,
        {
            "sections": [
                {"section_type": "triggers", "content": "Fim de semana ou discussão"},
                {
                    "section_type": "safe_environments",
                    "title": "Lugares",
                    "content": "Casa da minha irmã",
                },
                {"section_type": "protective_factors", "content": "   "},
            ]
        },
    )
    assert second.status_code == 200, second.content
    updated = second.json()["relapse_plan"]
    assert updated["id"] == plan["id"] and updated["version"] == 2
    assert updated["title"] == "Meu plano"  # título em branco mantém o atual
    assert [(s["type"], s["title"]) for s in updated["sections"]] == [
        ("triggers", "Gatilhos"),  # título em branco mantém o gravado
        ("coping_strategies", "Estratégias pessoais de enfrentamento"),
        ("safe_environments", "Lugares"),
    ]
    assert updated["sections"][0]["id"] == triggers_id  # atualizada no lugar
    assert updated["sections"][0]["content"] == "Fim de semana ou discussão"
    assert updated["sections"][1]["content"] == "Caminhar e ligar para a Marta"

    third = _call("put", RELAPSE, ana_h, {"title": "Plano revisado"})
    assert third.json()["relapse_plan"]["version"] == 3
    assert third.json()["relapse_plan"]["title"] == "Plano revisado"
    assert len(third.json()["relapse_plan"]["sections"]) == 3

    plans = RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk)
    assert plans.count() == 1 and plans.get().patient_profile_id == ana.profile.pk
    assert RelapsePlanSection.objects.for_clinic(stage.clinic.pk).count() == 3


def test_relapse_plan_without_a_title_gets_the_default_one() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call("put", RELAPSE, ana_h, {"sections": []})
    assert response.status_code == 200
    plan = response.json()["relapse_plan"]
    assert plan["title"] == "Plano de Prevenção de Recaída"
    assert plan["version"] == 1 and plan["sections"] == []


def test_relapse_section_with_empty_content_is_not_created() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "put",
        RELAPSE,
        ana_h,
        {
            "sections": [
                {"section_type": "triggers", "title": "Gatilhos", "content": "  \n "}
            ]
        },
    )
    assert (
        response.status_code == 200
        and response.json()["relapse_plan"]["sections"] == []
    )
    assert RelapsePlanSection.objects.for_clinic(stage.clinic.pk).count() == 0


@pytest.mark.parametrize(
    ("sections", "code"),
    [
        ([{"section_type": "pessoal", "content": "x"}], "invalid_section_type"),
        ([{"section_type": "", "content": "x"}], "invalid_section_type"),
        (
            [
                {"section_type": "triggers", "content": "a"},
                {"section_type": "triggers", "content": "b"},
            ],
            "duplicate_section",
        ),
        (
            [
                {"section_type": "triggers", "content": "a"},
                {"section_type": "triggers", "content": ""},
            ],
            "duplicate_section",
        ),
    ],
)
def test_relapse_plan_rejects_unknown_and_repeated_types(
    sections: list[dict[str, str]], code: str
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("put", RELAPSE, ana_h, {"title": "Plano", "sections": sections})
    assert response.status_code == 422 and response.json()["code"] == code
    assert RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).count() == 0
    assert RelapsePlanSection.objects.for_clinic(stage.clinic.pk).count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "x" * 201},
        {"sections": [{"section_type": "triggers", "content": "x" * 4001}]},
        {
            "sections": [
                {"section_type": "triggers", "title": "x" * 129, "content": "a"}
            ]
        },
        {"sections": [{"section_type": "t" * 65, "content": "a"}]},
        {"sections": [{"content": "sem tipo"}]},
        {"sections": "triggers"},
        {
            "sections": [
                {"section_type": "triggers", "content": str(n)} for n in range(8)
            ]
        },
    ],
)
def test_relapse_plan_format_errors_are_422_and_save_nothing(
    payload: dict[str, Any],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    assert _call("put", RELAPSE, ana_h, payload).status_code == 422
    assert RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).count() == 0


def test_relapse_plan_accepts_every_domain_type_at_maximum_size() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    kinds = [
        "triggers",
        "early_warning_signs",
        "protective_factors",
        "coping_strategies",
        "safe_environments",
        "support_contacts",
        "professional_resources",
    ]
    response = _call(
        "put",
        RELAPSE,
        ana_h,
        {
            "title": "t" * 200,
            "sections": [
                {"section_type": kind, "title": "s" * 128, "content": "c" * 4000}
                for kind in reversed(kinds)
            ],
        },
    )
    assert response.status_code == 200, response.content
    sections = response.json()["relapse_plan"]["sections"]
    assert [section["type"] for section in sections] == kinds  # ordem fixa do domínio


def test_deleting_a_section_removes_it_and_versions_the_plan() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    _call("put", RELAPSE, ana_h, _relapse_body())
    plan = RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).get()
    whole = share_relapse_plan_section(
        clinic_id=stage.clinic.pk,
        plan_id=plan.pk,
        recipient_label="Dra. Lúcia",
        valid_until=timezone.now() + timedelta(days=30),
        actor_id=ana.user.pk,
    )
    section_share = share_relapse_plan_section(
        clinic_id=stage.clinic.pk,
        plan_id=plan.pk,
        section_type="triggers",
        recipient_label="Dra. Lúcia",
        valid_until=timezone.now() + timedelta(days=30),
        actor_id=ana.user.pk,
    )
    response = _call("delete", f"{RELAPSE}sections/triggers/", ana_h)
    assert response.status_code == 200, response.content
    body = response.json()["relapse_plan"]
    assert [s["type"] for s in body["sections"]] == ["coping_strategies"]
    assert body["version"] == 2
    assert (
        not RelapsePlanSection.objects.for_clinic(stage.clinic.pk)
        .filter(section_type="triggers")
        .exists()
    )
    # o que foi compartilhado dessa seção deixa de valer; o resto do plano segue
    section_share = RelapsePlanShare.objects.for_clinic(stage.clinic.pk).get(
        pk=section_share.pk
    )
    assert section_share.is_revoked is True and section_share.revoked_at is not None
    assert (
        RelapsePlanShare.objects.for_clinic(stage.clinic.pk).get(pk=whole.pk).is_revoked
        is False
    )
    assert _events(stage.clinic.pk, "wellness.relapse_plan_section_removed")
    again = _call("delete", f"{RELAPSE}sections/triggers/", ana_h)
    assert again.status_code == 404 and again.json()["code"] == "not_found"
    assert _call("get", RELAPSE, ana_h).json()["relapse_plan"]["version"] == 2


def test_deleting_a_section_needs_a_known_type_and_an_existing_plan() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    unknown = _call("delete", f"{RELAPSE}sections/pessoal/", ana_h)
    assert (
        unknown.status_code == 422 and unknown.json()["code"] == "invalid_section_type"
    )
    no_plan = _call("delete", f"{RELAPSE}sections/triggers/", ana_h)
    assert no_plan.status_code == 404 and no_plan.json()["code"] == "not_found"


def test_relapse_plan_of_another_patient_is_never_read_or_changed() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _call("put", RELAPSE, ana_h, _relapse_body())
    ana_plan = RelapsePreventionPlan.objects.for_clinic(stage.clinic.pk).get(
        patient_profile_id=ana.profile.pk
    )
    # a Bia ainda não tem plano: não vê o da Ana e não consegue apagar seção dela
    assert _call("get", RELAPSE, bia_h).json() == {"relapse_plan": None}
    assert _call("delete", f"{RELAPSE}sections/triggers/", bia_h).status_code == 404
    # a Bia escreve o dela: o da Ana não muda
    mine = _call(
        "put",
        RELAPSE,
        bia_h,
        {
            "title": "Plano da Bia",
            "sections": [{"section_type": "triggers", "content": "Só da Bia"}],
        },
    )
    assert mine.status_code == 200
    assert mine.json()["relapse_plan"]["id"] != str(ana_plan.pk)
    ana_plan.refresh_from_db()
    assert ana_plan.version == 1 and ana_plan.title == "Meu plano"
    ana_sections = RelapsePlanSection.objects.for_clinic(stage.clinic.pk).filter(
        relapse_plan=ana_plan
    )
    assert ana_sections.count() == 2
    assert "Só da Bia" not in str(_call("get", RELAPSE, ana_h).json())
    # apagar a seção "triggers" como Bia remove só a dela
    assert _call("delete", f"{RELAPSE}sections/triggers/", bia_h).status_code == 200
    assert ana_sections.filter(section_type="triggers").exists()
    assert "Fim de semana sozinho" in str(_call("get", RELAPSE, ana_h).json())
    assert bia.profile.pk is not None


# ── Plano de apoio urgente ──────────────────────────────────────────────────


def test_urgent_plan_is_saved_and_help_reads_it_back() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    response = _call(
        "put",
        URGENT,
        ana_h,
        {
            "personal_instructions": "  Respirar e ligar para a Marta ",
            "calming_strategies": ["Água gelada", "  ", "Música", ""],
        },
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["personal_instructions"] == "Respirar e ligar para a Marta"
    assert body["calming_strategies"] == ["Água gelada", "Música"]
    assert body["contacts"] == [] and body["last_reviewed_at"]
    assert _call("get", HELP, ana_h).json()["urgent_plan"] == body
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).get()
    assert plan.patient_id == ana.profile.pk
    assert (plan.preferred_language, plan.region, plan.review_period_days) == (
        "pt-BR",
        "BR",
        90,
    )


def test_saving_the_urgent_plan_keeps_language_region_review_and_contacts() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_id=ana.profile.pk,
        personal_instructions="Texto antigo",
        calming_strategies=["Antiga"],
        preferred_language="en",
        region="PT",
        review_period_days=30,
    )
    contact = _add_contact(ana_h)
    response = _call(
        "put",
        URGENT,
        ana_h,
        {"personal_instructions": "Texto novo", "calming_strategies": ["Nova"]},
    )
    assert response.status_code == 200
    plan.refresh_from_db()
    assert (plan.preferred_language, plan.region, plan.review_period_days) == (
        "en",
        "PT",
        30,
    )
    assert plan.personal_instructions == "Texto novo"
    assert plan.calming_strategies == ["Nova"]
    assert [c["id"] for c in response.json()["contacts"]] == [contact["id"]]
    assert UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).count() == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"personal_instructions": "x" * 2001},
        {"calming_strategies": [f"estratégia {n}" for n in range(11)]},
        {"calming_strategies": ["x" * 201]},
        {"calming_strategies": "respirar"},
        {"calming_strategies": [3]},
    ],
)
def test_urgent_plan_format_errors_are_422_and_save_nothing(
    payload: dict[str, Any],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    assert _call("put", URGENT, ana_h, payload).status_code == 422
    assert UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).count() == 0


def test_urgent_plan_accepts_the_maximum_sizes() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "put",
        URGENT,
        ana_h,
        {
            "personal_instructions": "i" * 2000,
            "calming_strategies": ["e" * 200 for _ in range(10)],
        },
    )
    assert response.status_code == 200, response.content
    assert len(response.json()["calming_strategies"]) == 10


def test_contacts_follow_the_order_of_creation_and_normalize_the_phone() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    first = _add_contact(ana_h, phone_number=f"  {PHONE.replace(' ', '   ')}  ")
    assert set(first) == {"id", "name", "relationship", "phone", "message_template"}
    assert first["phone"] == PHONE  # espaços normalizados
    assert first["message_template"].startswith("Olá, estou em um momento difícil")
    second = _add_contact(
        ana_h,
        name="  Pedro  ",
        relationship=" Amigo ",
        phone_number="(81) 3333-4444",
        message_template="  Pode me ligar?  ",
    )
    assert second["name"] == "Pedro" and second["relationship"] == "Amigo"
    assert second["message_template"] == "Pode me ligar?"
    third = _add_contact(ana_h, name="Lia", phone_number="12345678")
    rows = UrgentSupportContact.objects.for_clinic(stage.clinic.pk).order_by(
        "priority_order"
    )
    assert [r.priority_order for r in rows] == [1, 2, 3]
    assert [str(r.pk) for r in rows] == [first["id"], second["id"], third["id"]]
    assert {r.plan.patient_id for r in rows} == {ana.profile.pk}
    listed = _call("get", HELP, ana_h).json()["urgent_plan"]
    assert [c["name"] for c in listed["contacts"]] == ["Marta", "Pedro", "Lia"]
    assert listed["contacts"][0]["phone"] == PHONE


def test_first_contact_creates_an_empty_plan_without_touching_the_text() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    assert UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).count() == 0
    _add_contact(ana_h)
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).get()
    assert plan.patient_id == ana.profile.pk and plan.personal_instructions == ""
    _call("put", URGENT, ana_h, {"personal_instructions": "Respirar"})
    _add_contact(ana_h, name="Pedro")
    assert UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).count() == 1
    assert (
        _call("get", HELP, ana_h).json()["urgent_plan"]["personal_instructions"]
        == "Respirar"
    )


@pytest.mark.parametrize(
    "phone",
    [
        "abc",
        "81 99999-0000 ramal 5",
        "1234567",  # 7 dígitos
        "1" * 21,  # 21 dígitos
        "55+81999990000",  # + só no início
        "++5581999990000",
        "5581999990000#",
        "(81) 9999-0000;",
        "٣٣٣٣٣٣٣٣",  # dígitos não ASCII
        "---() ---",
        "+",
    ],
)
def test_invalid_phone_numbers_are_refused_with_a_stable_code(phone: str) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", CONTACTS, ana_h, _contact_body(phone_number=phone))
    assert response.status_code == 422, phone
    assert response.json()["code"] == "invalid_phone"
    assert phone not in response.content.decode()
    assert UrgentSupportContact.objects.for_clinic(stage.clinic.pk).count() == 0


@pytest.mark.parametrize(
    "phone",
    [
        "12345678",
        "+" + "1" * 20,
        "(81) 99999-0000",
        "81 9999 0000",
        "+55 81 99999-0000",
    ],
)
def test_valid_phone_numbers_are_accepted(phone: str) -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    assert _add_contact(ana_h, phone_number=phone)["phone"] == phone


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"name": "n" * 121},
        {"relationship": ""},
        {"relationship": "r" * 81},
        {"phone_number": ""},
        {"phone_number": "1" * 41},
        {"message_template": "m" * 501},
        {"name": 5},
    ],
)
def test_contact_format_errors_are_422_and_save_nothing(
    changes: dict[str, Any],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    response = _call("post", CONTACTS, ana_h, _contact_body(**changes))
    assert response.status_code == 422
    assert UrgentSupportContact.objects.for_clinic(stage.clinic.pk).count() == 0
    for field in ("name", "relationship", "phone_number"):
        body = _contact_body()
        del body[field]
        assert _call("post", CONTACTS, ana_h, body).status_code == 422


def test_contact_with_blank_name_or_relationship_is_a_stable_422() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    for changes in ({"name": "   "}, {"relationship": " \t "}):
        response = _call("post", CONTACTS, ana_h, _contact_body(**changes))
        assert (
            response.status_code == 422 and response.json()["code"] == "invalid_contact"
        )
    assert UrgentSupportContact.objects.for_clinic(stage.clinic.pk).count() == 0


def test_contact_accepts_the_maximum_sizes() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    created = _add_contact(
        ana_h,
        name="n" * 120,
        relationship="r" * 80,
        phone_number="1" * 20,
        message_template="m" * 500,
    )
    assert len(created["name"]) == 120 and len(created["message_template"]) == 500


def test_at_most_five_active_contacts() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    created = [_add_contact(ana_h, name=f"Pessoa {n}") for n in range(5)]
    sixth = _call("post", CONTACTS, ana_h, _contact_body(name="Sexta"))
    assert sixth.status_code == 409 and sixth.json()["code"] == "limit_reached"
    rows = UrgentSupportContact.objects.for_clinic(stage.clinic.pk)
    assert rows.count() == 5 and not rows.filter(name="Sexta").exists()
    # sair libera uma vaga, e a nova pessoa entra no fim da ordem
    assert _call("delete", f"{CONTACTS}{created[1]['id']}/", ana_h).status_code == 204
    sixth = _add_contact(ana_h, name="Sexta")
    active = rows.filter(is_active=True).order_by("priority_order")
    assert [c.name for c in active] == [
        "Pessoa 0",
        "Pessoa 2",
        "Pessoa 3",
        "Pessoa 4",
        "Sexta",
    ]
    orders = [c.priority_order for c in active]
    assert orders == sorted(set(orders))
    newest = active.last()
    assert newest is not None and str(newest.pk) == sixth["id"]
    assert _call("post", CONTACTS, ana_h, _contact_body()).status_code == 409
    assert ana.user.pk is not None


def test_the_contact_limit_is_per_patient() -> None:
    _stage, _ana, _bia, ana_h, bia_h = _world()
    for n in range(5):
        _add_contact(ana_h, name=f"Pessoa {n}")
    assert _call("post", CONTACTS, ana_h, _contact_body()).status_code == 409
    assert (
        _call("post", CONTACTS, bia_h, _contact_body(name="Da Bia")).status_code == 201
    )


def test_editing_a_contact_keeps_its_place_and_resets_a_blank_message() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    first = _add_contact(ana_h, name="Marta", message_template="Mensagem antiga")
    second = _add_contact(ana_h, name="Pedro")
    response = _call(
        "put",
        f"{CONTACTS}{first['id']}/",
        ana_h,
        {
            "name": " Marta Souza ",
            "relationship": "Irmã mais velha",
            "phone_number": "  +55  81  91234-5678 ",
            "message_template": "  ",
        },
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["id"] == first["id"] and body["name"] == "Marta Souza"
    assert body["phone"] == "+55 81 91234-5678"
    assert body["message_template"].startswith("Olá, estou em um momento difícil")
    row = UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get(pk=first["id"])
    assert row.priority_order == 1 and row.is_active is True
    assert (
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk)
        .get(pk=second["id"])
        .name
        == "Pedro"
    )


def test_editing_a_contact_with_a_bad_phone_changes_nothing() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    mine = _add_contact(ana_h)
    response = _call(
        "put",
        f"{CONTACTS}{mine['id']}/",
        ana_h,
        _contact_body(name="Outra", phone_number="12"),
    )
    assert response.status_code == 422 and response.json()["code"] == "invalid_phone"
    row = UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get(pk=mine["id"])
    assert row.name == "Marta" and row.phone_number == PHONE


def test_removing_a_contact_makes_it_inactive_and_it_leaves_every_read() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    mine = _add_contact(ana_h)
    keep = _add_contact(ana_h, name="Pedro")
    response = _call("delete", f"{CONTACTS}{mine['id']}/", ana_h)
    assert response.status_code == 204 and response.content == b""
    row = UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get(pk=mine["id"])
    assert row.is_active is False
    listed = _call("get", HELP, ana_h).json()["urgent_plan"]["contacts"]
    assert [c["id"] for c in listed] == [keep["id"]]
    again = _call("delete", f"{CONTACTS}{mine['id']}/", ana_h)
    assert again.status_code == 404 and again.json()["code"] == "not_found"
    edit = _call("put", f"{CONTACTS}{mine['id']}/", ana_h, _contact_body())
    assert edit.status_code == 404  # inativo não volta por edição
    assert (
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk)
        .get(pk=mine["id"])
        .is_active
        is False
    )


def test_contacts_of_another_patient_are_a_plain_404_and_nothing_is_written() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    theirs = _add_contact(bia_h, name="Da Bia", phone_number="+55 11 98888-7777")
    mine = _add_contact(ana_h)
    before = list(UrgentSupportContact.objects.for_clinic(stage.clinic.pk).values())
    audit_before = AuditEvent.objects.for_clinic(stage.clinic.pk).count()
    edit = _call(
        "put",
        f"{CONTACTS}{theirs['id']}/",
        ana_h,
        _contact_body(name="Sequestrada", phone_number="12345678"),
    )
    assert edit.status_code == 404 and edit.json()["code"] == "not_found"
    delete = _call("delete", f"{CONTACTS}{theirs['id']}/", ana_h)
    assert delete.status_code == 404
    unknown = _call("delete", f"{CONTACTS}{uuid4()}/", ana_h)
    assert unknown.status_code == 404
    for response in (edit, delete, unknown):
        assert "98888-7777" not in response.content.decode()
    assert (
        list(UrgentSupportContact.objects.for_clinic(stage.clinic.pk).values())
        == before
    )
    assert AuditEvent.objects.for_clinic(stage.clinic.pk).count() == audit_before
    # e o contrário: a Bia também não alcança o contato da Ana
    assert _call("delete", f"{CONTACTS}{mine['id']}/", bia_h).status_code == 404
    assert (
        _call("get", HELP, bia_h).json()["urgent_plan"]["contacts"][0]["name"]
        == "Da Bia"
    )
    assert ana.profile.pk != bia.profile.pk


def test_the_phone_of_a_trusted_person_is_only_ever_returned_to_their_patient() -> None:
    _stage, _ana, _bia, ana_h, bia_h = _world()
    _add_contact(ana_h, phone_number="+55 81 98765-4321")
    _call("put", URGENT, ana_h, {"personal_instructions": "Ligar para a Marta"})
    expected = {
        "get": (HELP, None, 200),
        "put": (URGENT, {"personal_instructions": "Da Bia"}, 200),
        "post": (
            CONTACTS,
            _contact_body(name="Da Bia", phone_number="+55 11 90000-0000"),
            201,
        ),
    }
    assert _call("get", RELAPSE, bia_h).status_code == 200
    for method, (url, body, status) in expected.items():
        response = _call(method, url, bia_h, body)
        assert response.status_code == status, (method, url)
        assert "98765-4321" not in response.content.decode()
    mine = _call("get", HELP, ana_h).json()["urgent_plan"]
    assert mine["contacts"][0]["phone"] == "+55 81 98765-4321"
    assert mine["personal_instructions"] == "Ligar para a Marta"
    assert "Da Bia" not in str(mine)


def test_a_trusted_persons_phone_number_never_reaches_the_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    _stage, _ana, _bia, ana_h, bia_h = _world()
    created = _add_contact(ana_h, phone_number="+55 (81) 98765-4321")
    _call(
        "put",
        f"{CONTACTS}{created['id']}/",
        ana_h,
        _contact_body(phone_number="81 91234-5678"),
    )
    bad = _call(
        "post", CONTACTS, ana_h, _contact_body(phone_number="81 97777-6666 abc")
    )
    assert bad.status_code == 422
    too_long = _call("post", CONTACTS, ana_h, _contact_body(phone_number="8" * 60))
    assert too_long.status_code == 422 and "88888888" not in too_long.content.decode()
    _call(
        "put",
        f"{CONTACTS}{created['id']}/",
        bia_h,
        _contact_body(phone_number="81 95555-4444"),
    )
    _call("get", HELP, ana_h)
    _call("delete", f"{CONTACTS}{created['id']}/", ana_h)
    for fragment in (
        "98765-4321",
        "91234-5678",
        "97777-6666",
        "95555-4444",
        "5581987654321",
        "81912345678",
        "81977776666",
        "81955554444",
    ):
        assert fragment not in caplog.text, fragment


def test_saving_the_plan_or_its_contacts_contacts_nobody() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    calls: list[object] = []

    def receiver(sender: object, **kwargs: object) -> None:
        calls.append(kwargs)

    urgent_action_previewed.connect(receiver, weak=False)
    urgent_action_confirmed.connect(receiver, weak=False)
    try:
        _call("put", URGENT, ana_h, {"personal_instructions": "Respirar"})
        created = _add_contact(ana_h)
        _call(
            "put", f"{CONTACTS}{created['id']}/", ana_h, _contact_body(name="Marta S.")
        )
        _call("get", HELP, ana_h)
        _call("delete", f"{CONTACTS}{created['id']}/", ana_h)
    finally:
        urgent_action_previewed.disconnect(receiver)
        urgent_action_confirmed.disconnect(receiver)
    assert calls == [] and mail.outbox == []
    assert UrgentActionLog.objects.for_clinic(stage.clinic.pk).count() == 0
    assert CrisisAccessLog.objects.for_clinic(stage.clinic.pk).count() == 0


# ── Pouca energia ───────────────────────────────────────────────────────────


def test_low_energy_actions_are_saved_and_the_toggle_keeps_working() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    before = _call("get", LOW_ENERGY, ana_h).json()
    assert before["actions"] == [] and before["can_activate"] is False
    response = _call(
        "put",
        LOW_ENERGY_ACTIONS,
        ana_h,
        {"actions": ["", " Beber  água ", "Tomar o remédio"]},
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["actions"] == [
        "Beber água",
        "Tomar o remédio",
    ]  # em branco sai, sem buracos
    assert body["active"] is False and body["can_activate"] is True
    assert _call("get", LOW_ENERGY, ana_h).json() == body
    on = _call("put", LOW_ENERGY, ana_h, {"active": True})
    assert on.status_code == 200 and on.json()["active"] is True
    # as ações novas valem na próxima ativação; a sessão ligada guarda as antigas
    new = _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": ["Deitar um pouco"]})
    assert new.json()["actions"] == ["Deitar um pouco"] and new.json()["active"] is True
    session = LowEnergyMode.objects.for_clinic(stage.clinic.pk).get()
    assert (session.action_1, session.action_2) == ("Beber água", "Tomar o remédio")
    templates = LowEnergyActionTemplate.objects.for_clinic(stage.clinic.pk).filter(
        patient_profile_id=ana.profile.pk
    )
    assert templates.count() == 2
    assert templates.filter(is_active=True).get().version == 2
    off = _call("put", LOW_ENERGY, ana_h, {"active": False})
    assert off.json()["active"] is False


def test_low_energy_accepts_three_actions_of_the_maximum_size() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    response = _call(
        "put", LOW_ENERGY_ACTIONS, ana_h, {"actions": ["a" * 120, "b" * 120, "c" * 120]}
    )
    assert response.status_code == 200 and len(response.json()["actions"]) == 3


@pytest.mark.parametrize("actions", [[], [""], ["  ", "\t"]])
def test_low_energy_without_any_action_is_a_stable_422_and_keeps_the_old_ones(
    actions: list[str],
) -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": ["Beber água"]})
    response = _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": actions})
    assert response.status_code == 422
    assert response.json()["code"] == "no_actions_configured"
    assert _call("get", LOW_ENERGY, ana_h).json()["actions"] == ["Beber água"]


@pytest.mark.parametrize(
    "payload",
    [
        {"actions": ["a", "b", "c", "d"]},
        {"actions": ["x" * 121]},
        {"actions": "Beber água"},
        {"actions": [1]},
        {},
    ],
)
def test_low_energy_format_errors_are_422_and_save_nothing(
    payload: dict[str, Any],
) -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    assert _call("put", LOW_ENERGY_ACTIONS, ana_h, payload).status_code == 422
    assert LowEnergyActionTemplate.objects.for_clinic(stage.clinic.pk).count() == 0


def test_low_energy_actions_of_one_patient_never_reach_another() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": ["Da Ana"]})
    assert _call("get", LOW_ENERGY, bia_h).json()["actions"] == []
    _call("put", LOW_ENERGY_ACTIONS, bia_h, {"actions": ["Da Bia"]})
    assert _call("get", LOW_ENERGY, ana_h).json()["actions"] == ["Da Ana"]
    owners = set(
        LowEnergyActionTemplate.objects.for_clinic(stage.clinic.pk).values_list(
            "patient_profile_id", flat=True
        )
    )
    assert owners == {ana.profile.pk, bia.profile.pk}


# ── Clínica da sessão (mesma pessoa em duas clínicas) ───────────────────────


def _two_clinic_patient(stage: Stage) -> PatientLogin:
    ana = make_patient_login(stage.clinic, stage.admin, name="Ana Souza")
    ClinicMembershipFactory.create(
        clinic=stage.other_clinic, user=ana.user, role=ClinicMembership.Role.PATIENT
    )
    other_profile = make_patient(
        stage.other_clinic, stage.other_admin, name="Ana Souza"
    )
    other_profile.user = ana.user
    other_profile.save()
    return ana


def _write_everything(headers: dict[str, str]) -> dict[str, Any]:
    assert _call("post", GOAL, headers, _goal_body()).status_code == 201
    assert _call("put", RELAPSE, headers, _relapse_body()).status_code == 200
    assert (
        _call("put", URGENT, headers, {"personal_instructions": "Respirar"}).status_code
        == 200
    )
    contact = _add_contact(headers)
    actions = _call("put", LOW_ENERGY_ACTIONS, headers, {"actions": ["Beber água"]})
    assert actions.status_code == 200
    return contact


def _footprint(clinic_id: UUID) -> tuple[int, int, int, int, int, int]:
    return (
        SobrietyGoal.objects.for_clinic(clinic_id).count(),
        RelapsePreventionPlan.objects.for_clinic(clinic_id).count(),
        RelapsePlanSection.objects.for_clinic(clinic_id).count(),
        UrgentSupportPlan.objects.for_clinic(clinic_id).count(),
        UrgentSupportContact.objects.for_clinic(clinic_id).count(),
        LowEnergyActionTemplate.objects.for_clinic(clinic_id).count(),
    )


def test_the_session_only_ever_edits_its_own_clinic() -> None:
    stage = build_stage()
    ana = _two_clinic_patient(stage)
    other_events = AuditEvent.objects.for_clinic(stage.other_clinic.pk).count()
    first_h = _login(ana, clinic_id=stage.clinic.pk)
    contact = _write_everything(first_h)
    assert _footprint(stage.clinic.pk) == (1, 1, 2, 1, 1, 1)
    assert _footprint(stage.other_clinic.pk) == (0, 0, 0, 0, 0, 0)
    assert AuditEvent.objects.for_clinic(stage.other_clinic.pk).count() == other_events
    # a mesma pessoa, agora na outra clínica: começa do zero e não vê a primeira
    second_h = _login(ana, clinic_id=stage.other_clinic.pk)
    assert _call("get", RELAPSE, second_h).json() == {"relapse_plan": None}
    assert _call("get", HELP, second_h).json()["urgent_plan"] is None
    assert _call("get", LOW_ENERGY, second_h).json()["actions"] == []
    assert _call("get", "/api/v1/mobile/recovery/", second_h).json()["sobriety"] is None
    # o contato da primeira clínica não é alcançável pela sessão da segunda
    assert (
        _call(
            "put", f"{CONTACTS}{contact['id']}/", second_h, _contact_body()
        ).status_code
        == 404
    )
    assert _call("delete", f"{CONTACTS}{contact['id']}/", second_h).status_code == 404
    assert _call("delete", f"{RELAPSE}sections/triggers/", second_h).status_code == 404
    assert _footprint(stage.other_clinic.pk) == (0, 0, 0, 0, 0, 0)
    # a meta da primeira clínica não bloqueia a da segunda
    _write_everything(second_h)
    assert _footprint(stage.other_clinic.pk) == (1, 1, 2, 1, 1, 1)
    assert _footprint(stage.clinic.pk) == (1, 1, 2, 1, 1, 1)
    assert (
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get().is_active is True
    )
    assert _events(stage.clinic.pk, "wellness.sobriety_goal_created")
    assert _events(stage.other_clinic.pk, "wellness.sobriety_goal_created")


def test_clinic_and_patient_chosen_by_the_client_are_ignored() -> None:
    stage, ana, bia, ana_h, _ = _world()
    url_ids = f"?clinic_id={stage.other_clinic.pk}&patient_id={bia.profile.pk}"
    extra: dict[str, Any] = {"HTTP_X_CLINIC_ID": str(stage.other_clinic.pk), **ana_h}
    response = Client().put(
        f"{URGENT}{url_ids}",
        {
            "personal_instructions": "Meu",
            "clinic_id": str(stage.other_clinic.pk),
            "patient_id": str(bia.profile.pk),
            "patient_profile_id": str(bia.profile.pk),
        },
        content_type="application/json",
        **extra,
    )
    assert response.status_code == 200
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).get()
    assert plan.patient_id == ana.profile.pk
    assert UrgentSupportPlan.objects.for_clinic(stage.other_clinic.pk).count() == 0


# ── Autenticação, sessão e cobrança ─────────────────────────────────────────


def _writes() -> list[tuple[str, str, Any]]:
    return [
        ("post", GOAL, _goal_body()),
        ("put", RELAPSE, _relapse_body()),
        ("delete", f"{RELAPSE}sections/triggers/", None),
        ("put", URGENT, {"personal_instructions": "Respirar"}),
        ("post", CONTACTS, _contact_body()),
        ("put", f"{CONTACTS}{uuid4()}/", _contact_body()),
        ("delete", f"{CONTACTS}{uuid4()}/", None),
        ("put", LOW_ENERGY_ACTIONS, {"actions": ["Beber água"]}),
    ]


def test_every_authoring_route_needs_a_valid_app_token() -> None:
    stage, _ana, _bia, _ana_h, _ = _world()
    gone = make_patient_login(stage.clinic, stage.admin, name="Sessão encerrada")
    ended = _login(gone)
    assert _call("post", LOGOUT, ended).status_code in {200, 204}
    bad_tokens: list[dict[str, str]] = [
        {},
        {"HTTP_AUTHORIZATION": "Bearer aem_nao_existe"},
        {"HTTP_AUTHORIZATION": "Bearer "},
        {"HTTP_AUTHORIZATION": "Basic YTpi"},
        ended,  # sessão encerrada no servidor
    ]
    for method, url, body in _writes():
        for headers in bad_tokens:
            response = _call(method, url, headers, body)
            assert response.status_code == 401, (method, url, headers)
    assert _footprint(stage.clinic.pk) == (0, 0, 0, 0, 0, 0)


def test_a_web_session_cookie_is_not_an_authentication_for_these_routes() -> None:
    stage, ana, _bia, _h, _ = _world()
    client = Client()
    client.force_login(ana.user)
    staff = Client()
    staff.force_login(stage.admin)
    for method, url, body in _writes():
        for who in (client, staff):
            kwargs: dict[str, Any] = {}
            if body is not None:
                kwargs = {"data": body, "content_type": "application/json"}
            # sem token do app não há autenticação: 401, ou 400 quando o middleware de
            # clínica do web barra antes (a sessão de cookie nunca chega a gravar)
            status = getattr(who, method)(url, **kwargs).status_code
            assert status in {400, 401, 403}, (method, url, status)
    assert _footprint(stage.clinic.pk) == (0, 0, 0, 0, 0, 0)


def test_the_app_token_is_still_refused_outside_the_mobile_routes() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    for method, url in (
        ("get", "/api/v1/journal/entries/"),
        ("get", "/api/v1/goals/"),
        ("post", "/api/v1/scheduling/appointments/"),
    ):
        response = _call(method, url, ana_h, {} if method == "post" else None)
        assert response.status_code in {401, 403}, (method, url)


def test_a_blocked_clinic_stops_every_write_but_not_the_urgent_help() -> None:
    from master_panel.models import TenantSubscription

    stage, _ana, _bia, ana_h, _ = _world()
    mine = _add_contact(ana_h)
    TenantSubscription.objects.create(
        clinic=stage.clinic, status=TenantSubscription.Status.BLOCKED
    )
    footprint = _footprint(stage.clinic.pk)
    audit_before = AuditEvent.objects.for_clinic(stage.clinic.pk).count()
    for method, url, body in _writes():
        response = _call(method, url, ana_h, body)
        assert response.status_code == 402, (method, url, response.status_code)
    assert (
        _call("put", f"{CONTACTS}{mine['id']}/", ana_h, _contact_body()).status_code
        == 402
    )
    assert _call("delete", f"{CONTACTS}{mine['id']}/", ana_h).status_code == 402
    assert _footprint(stage.clinic.pk) == footprint
    assert AuditEvent.objects.for_clinic(stage.clinic.pk).count() == audit_before
    assert (
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get().is_active is True
    )
    help_response = _call("get", HELP, ana_h)
    assert help_response.status_code == 200  # a ajuda continua aberta
    assert help_response.json()["urgent_plan"]["contacts"][0]["id"] == mine["id"]


def test_authoring_responses_are_never_cached() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    for method, url, body in _writes():
        assert _call(method, url, ana_h, body)["Cache-Control"] == "private, no-store"


# ── Auditoria ───────────────────────────────────────────────────────────────


def test_every_write_is_audited_without_clinical_content_or_phone_numbers() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    secrets = (
        "FOCO-SECRETO",
        "MOTIVO-SECRETO",
        "GATILHO-SECRETO",
        "INSTRUCAO-SECRETA",
        "CALMA-SECRETA",
        "NOME-SECRETO",
        "VINCULO-SECRETO",
        "MENSAGEM-SECRETA",
        "ACAO-SECRETA",
        # telefone, como veio e normalizado (sequências longas: não colidem com hex)
        "98765-4321",
        "91234-5678",
        "5581987654321",
        "81912345678",
    )
    assert (
        _call(
            "post",
            GOAL,
            ana_h,
            _goal_body(focus="FOCO-SECRETO", motivations="MOTIVO-SECRETO"),
        ).status_code
        == 201
    )
    _call(
        "put",
        RELAPSE,
        ana_h,
        {"sections": [{"section_type": "triggers", "content": "GATILHO-SECRETO"}]},
    )
    _call("delete", f"{RELAPSE}sections/triggers/", ana_h)
    _call(
        "put",
        URGENT,
        ana_h,
        {
            "personal_instructions": "INSTRUCAO-SECRETA",
            "calming_strategies": ["CALMA-SECRETA"],
        },
    )
    created = _add_contact(
        ana_h,
        name="NOME-SECRETO",
        relationship="VINCULO-SECRETO",
        phone_number="+55 (81) 98765-4321",
        message_template="MENSAGEM-SECRETA",
    )
    _call(
        "put",
        f"{CONTACTS}{created['id']}/",
        ana_h,
        _contact_body(name="NOME-SECRETO", phone_number="81 91234-5678"),
    )
    _call("delete", f"{CONTACTS}{created['id']}/", ana_h)
    _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": ["ACAO-SECRETA"]})

    events = {
        e.action: e
        for e in _events(
            stage.clinic.pk,
            "wellness.sobriety_goal_created",
            "wellness.relapse_plan_updated",
            "wellness.relapse_plan_section_removed",
            "support_network.urgent_plan_updated",
            "support_network.urgent_contact_added",
            "support_network.urgent_contact_updated",
            "support_network.urgent_contact_removed",
            "goals.low_energy_actions_configured",
        )
    }
    assert len(events) == 8
    for event in events.values():
        assert event.actor_id == ana.user.pk and event.outcome == "success"
        assert event.network_origin_digest and event.request_id is not None
        assert event.clinic_id == stage.clinic.pk
    assert events["support_network.urgent_contact_added"].resource_id == created["id"]
    assert events["support_network.urgent_contact_removed"].resource_id == created["id"]
    dump = _audit_dump(stage.clinic.pk)
    for secret in secrets:
        assert secret not in dump, secret
    assert PHONE not in dump and "+55" not in dump


def test_a_write_that_is_refused_leaves_no_audit_event() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    before = AuditEvent.objects.for_clinic(stage.clinic.pk).count()
    _call("post", GOAL, ana_h, _goal_body(reference_date="2999-01-01"))
    _call("put", RELAPSE, ana_h, {"sections": [{"section_type": "x", "content": "a"}]})
    _call("post", CONTACTS, ana_h, _contact_body(phone_number="abc"))
    _call("put", LOW_ENERGY_ACTIONS, ana_h, {"actions": []})
    _call("delete", f"{CONTACTS}{uuid4()}/", ana_h)
    assert AuditEvent.objects.for_clinic(stage.clinic.pk).count() == before


# ── Serviços de domínio chamados direto ─────────────────────────────────────


def test_domain_services_scope_contacts_and_sections_to_the_patient() -> None:
    stage, _ana, bia, ana_h, _ = _world()
    mine = _add_contact(ana_h)
    _call("put", RELAPSE, ana_h, _relapse_body())
    contact_id = UUID(mine["id"])
    with pytest.raises(ValueError, match="não encontrado"):
        update_urgent_contact(
            clinic_id=stage.clinic.pk,
            patient_profile_id=bia.profile.pk,
            contact_id=contact_id,
            name="x",
            relationship="y",
            phone_number="12345678",
        )
    with pytest.raises(ValueError, match="não encontrado"):
        deactivate_urgent_contact(
            clinic_id=stage.clinic.pk,
            patient_profile_id=bia.profile.pk,
            contact_id=contact_id,
        )
    with pytest.raises(ValidationError):
        remove_relapse_plan_section(
            clinic_id=stage.clinic.pk,
            patient_profile_id=bia.profile.pk,
            section_type="triggers",
        )
    assert (
        UrgentSupportContact.objects.for_clinic(stage.clinic.pk).get(pk=contact_id).name
        == "Marta"
    )
    assert RelapsePlanSection.objects.for_clinic(stage.clinic.pk).count() == 2


def test_the_contact_limit_is_enforced_by_the_service_itself() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    _add_contact(ana_h)
    _add_contact(ana_h, name="Pedro")
    plan = UrgentSupportPlan.objects.for_clinic(stage.clinic.pk).get(
        patient_id=ana.profile.pk
    )
    with pytest.raises(UrgentContactLimitError):
        register_urgent_contact(
            clinic_id=stage.clinic.pk,
            plan_id=plan.pk,
            name="Terceira",
            relationship="Amiga",
            phone_number="12345678",
            priority_order=None,
            max_active_contacts=2,
        )
    assert UrgentSupportContact.objects.for_clinic(stage.clinic.pk).count() == 2
    # sem limite informado o serviço segue como antes (uso da equipe e testes antigos)
    extra = register_urgent_contact(
        clinic_id=stage.clinic.pk,
        plan_id=plan.pk,
        name="Terceira",
        relationship="Amiga",
        phone_number="12345678",
    )
    assert extra.priority_order == 1
