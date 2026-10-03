"""O sistema web é só da equipe: o paciente usa apenas o aplicativo pós-alta.

Cobre a fronteira (login, seleção de clínica, middleware), a ausência das telas web de
paciente e o que continua disponível para a equipe.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from django.contrib.auth import SESSION_KEY
from django.core.cache import cache
from django.test import Client
from django.urls import NoReverseMatch, reverse

from accounts.models import User
from accounts.services import GENERIC_LOGIN_ERROR
from clinics.models import ClinicMembership
from people import services as people_services
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "senha-segura-sintetica-123"  # nosec - credencial sintética de teste


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _user(email: str) -> User:
    user = UserFactory.create(email=email)
    user.set_password(PASSWORD)
    user.save()
    return user


def _team_client(role: str = "therapist") -> Client:
    clinic = ClinicFactory.create()
    user = _user(f"{role}-boundary@example.test")
    ClinicMembershipFactory.create(clinic=clinic, user=user, role=role)
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


# ── Login e seleção de clínica ──────────────────────────────────────────────


def test_patient_cannot_sign_in_to_the_web_even_with_the_right_password() -> None:
    clinic = ClinicFactory.create()
    patient = _user("paciente-web@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic, user=patient, role=ClinicMembership.Role.PATIENT
    )
    client = Client()
    response = client.post(
        reverse("account_login"), {"email": patient.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert GENERIC_LOGIN_ERROR in response.content.decode()
    assert SESSION_KEY not in client.session


def test_a_person_who_is_also_staff_gets_only_the_staff_clinic_on_the_web() -> None:
    patient_clinic, staff_clinic = ClinicFactory.create(), ClinicFactory.create()
    person = _user("duplo-papel@example.test")
    ClinicMembershipFactory.create(
        clinic=patient_clinic, user=person, role=ClinicMembership.Role.PATIENT
    )
    ClinicMembershipFactory.create(
        clinic=staff_clinic, user=person, role=ClinicMembership.Role.THERAPIST
    )
    client = Client()
    response = client.post(
        reverse("account_login"), {"email": person.email, "password": PASSWORD}
    )
    assert response.status_code == 302
    assert client.session["active_clinic_id"] == str(staff_clinic.pk)
    # forçar a clínica em que a pessoa é paciente não abre nada
    session = client.session
    session["active_clinic_id"] = str(patient_clinic.pk)
    session.save()
    assert client.get(reverse("workspace_vertical")).status_code == 403


@pytest.mark.parametrize("route", ["workspace_vertical", "workspace_detached"])
def test_a_patient_session_opens_no_web_page(route: str) -> None:
    clinic = ClinicFactory.create()
    patient = _user("paciente-sessao@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic, user=patient, role=ClinicMembership.Role.PATIENT
    )
    client = Client()
    client.force_login(patient)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    assert client.get(reverse(route)).status_code == 403
    assert client.get("/api/v1/journal/entries/").status_code in {401, 403}


def test_clinic_switch_never_offers_a_patient_clinic() -> None:
    patient_clinic, staff_clinic = ClinicFactory.create(), ClinicFactory.create()
    person = _user("troca-clinica@example.test")
    ClinicMembershipFactory.create(
        clinic=patient_clinic, user=person, role=ClinicMembership.Role.PATIENT
    )
    ClinicMembershipFactory.create(
        clinic=staff_clinic, user=person, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    client = Client()
    client.force_login(person)
    session = client.session
    session["active_clinic_id"] = str(staff_clinic.pk)
    session.save()
    ok = client.get(
        reverse("clinic_switch_review"), {"clinic_id": str(staff_clinic.pk)}
    )
    denied = client.get(
        reverse("clinic_switch_review"), {"clinic_id": str(patient_clinic.pk)}
    )
    assert ok.status_code == 200
    assert denied.status_code == 403
    page = client.get(reverse("workspace_vertical")).content.decode()
    assert str(patient_clinic.pk) not in page


# ── Telas de paciente não existem mais ──────────────────────────────────────

REMOVED_URL_NAMES = [
    "journal_list",
    "journal_create",
    "checkin_today",
    "checkin_list",
    "goal_list",
    "goal_create",
    "low_energy_home",
    "patient_exercise_list",
    "patient_exercise_execute",
    "appointment_request",
    "reminder_preferences",
    "conversation_list",
    "conversation_create",
    "attachment_download",
    "patient_dashboard",
    "patient_onboarding",
    "content_recommendations",
    "content_notifications",
    "psychiatry:mobile_connected",
    "psychiatry:mobile_b2c",
    "psychiatry:api_patient_summary",
    "psychiatry:api_medication_log",
    "psychiatry:api_patient_sos",
    "psychiatry:api_b2c_mood",
    "psychiatry:api_b2c_cbt_diary",
    "psychiatry:api_b2c_breathing",
    "psychiatry:api_b2c_subscription",
    "psychiatry:api_record_craving",
]


@pytest.mark.parametrize("name", REMOVED_URL_NAMES)
def test_patient_web_routes_no_longer_exist(name: str) -> None:
    with pytest.raises(NoReverseMatch):
        reverse(name, kwargs=_kwargs_for(name))


def _kwargs_for(name: str) -> dict[str, str] | None:
    """Parâmetros fictícios: o que importa é o nome não resolver mais."""
    needs = {
        "attachment_download": {
            "attachment_id": "00000000-0000-0000-0000-000000000001"
        },
        "patient_exercise_execute": {
            "assignment_id": "00000000-0000-0000-0000-000000000001"
        },
    }
    return needs.get(name)


REMOVED_PATHS = [
    "/journal/",
    "/journal/novo/",
    "/journal/checkin/",
    "/goals/",
    "/goals/nova/",
    "/goals/baixa-energia/",
    "/goals/exercicios/meus/",
    "/agenda/consultas/nova/",
    "/agenda/lembretes/",
    "/agenda/mensagens/",
    "/analytics/",
    "/onboarding/patient/",
    "/conteudos/minhas-recomendacoes/",
    "/conteudos/notificacoes/",
    "/psiquiatria/mobile/conectado/",
    "/psiquiatria/mobile/b2c/",
    "/psiquiatria/api/v1/patient/summary/",
    "/psiquiatria/api/v1/mobile/connected/sos/",
    "/psiquiatria/api/v1/mind/mood/",
    "/psiquiatria/api/v1/mobile/b2c/breathing/",
]


@pytest.mark.parametrize("path", REMOVED_PATHS)
def test_removed_patient_paths_answer_404_even_to_the_team(path: str) -> None:
    client = _team_client("clinic_admin")
    assert client.get(path).status_code == 404


# ── O que a equipe continua usando ──────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        "appointment_list",
        "appointment_calendar",
        "waitlist_list",
        "exercise_catalog",
        "patient_list",
        "content_library",
        "consent_center",
        "concierge:dashboard",
    ],
)
def test_team_pages_still_work_for_the_clinic_administrator(name: str) -> None:
    client = _team_client("clinic_admin")
    assert client.get(reverse(name)).status_code == 200


def test_team_navigation_has_no_patient_entries() -> None:
    client = _team_client("therapist")
    for url_name in ("workspace_vertical", "workspace_detached"):
        html = client.get(reverse(url_name)).content.decode()
        for patient_only in (
            "Diário emocional",
            "Minhas metas",
            "Minha evolução",
            "Modo de baixa energia",
            "Prévia do aplicativo",
        ):
            assert patient_only not in html


def test_patient_record_links_every_app_panel_and_each_link_resolves() -> None:
    clinic = ClinicFactory.create()
    admin = _user("admin-links@example.test")
    ClinicMembershipFactory.create(
        clinic=clinic, user=admin, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    patient = people_services.register_patient_profile(
        clinic_id=clinic.pk,
        actor=admin,
        request_id=uuid4(),
        full_name="Marina Exemplo",
        social_name="",
        birth_date=date(1994, 5, 18),
        gender="woman",
        email="marina-links@example.test",
        phone="",
        language_code="pt-BR",
        timezone_name="America/Sao_Paulo",
        accessibility_preferences="",
        address={},
        address_purpose="",
        emergency_contact={},
        emergency_contact_purpose="",
    )
    client = Client()
    client.force_login(admin)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    page = client.get(reverse("patient_detail", args=[patient.pk]))
    assert page.status_code == 200
    html = page.content.decode()
    for name in (
        "mobile_api:patient_app",
        "routines:medication_list",
        "routines:care_plan_list",
        "routines:habit_list",
        "journal:patient_diary",
        "journal:patient_checkins",
    ):
        url = reverse(name, args=[patient.pk])
        assert f'href="{url}"' in html
        # a tela existe; quem não tem papel clínico recebe 403, nunca 404/500
        assert client.get(url).status_code in {200, 403}


def test_clinic_setup_links_are_in_the_sidebar_for_the_administrator() -> None:
    client = _team_client("clinic_admin")
    html = client.get(reverse("workspace_vertical")).content.decode()
    for name in (
        "scheduling:service_list",
        "scheduling:availability_list",
        "wellness:crisis_resources",
    ):
        assert f'href="{reverse(name)}"' in html
