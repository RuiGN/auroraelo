"""Login único, cadastro de usuários pela administração e troca da senha provisória.

O administrador cadastra a pessoa e escolhe a função; o sistema gera uma senha
aleatória, mostrada uma única vez; a pessoa só usa o sistema depois de trocá-la no
primeiro acesso. O menu e a área de trabalho seguem a função.
"""

from __future__ import annotations

import re
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from accounts.models import User
from accounts.services import (
    TEAM_MEMBER_ROLES,
    create_team_member,
    generate_temporary_password,
)
from clinics.models import ClinicMembership
from tests.factories import (
    ClinicFactory,
    ClinicMembershipFactory,
    UserFactory,
    synthetic_cpf,
)

pytestmark = pytest.mark.django_db

PASSWORD = "senha-segura-sintetica-123"  # nosec - credencial sintética de teste
CARLA_CPF = "52998224725"
CARLA_CPF_MASKED = "***.982.247-**"
PASSWORD_SHAPE = re.compile(r"^[A-Za-z2-9]{4}(-[A-Za-z2-9]{4}){3}$")


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _member(clinic, role: str, email: str) -> User:
    user = UserFactory.create(email=email)
    user.set_password(PASSWORD)
    user.save()
    ClinicMembershipFactory.create(clinic=clinic, user=user, role=role)
    return user


def _client_for(user: User, clinic) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def _stage():
    clinic = ClinicFactory.create()
    admin = _member(clinic, "clinic_admin", "admin-cadastro@example.test")
    return clinic, admin, _client_for(admin, clinic)


def _register(client: Client, **over: str):
    data = {
        "first_name": "Carla",
        "last_name": "Dias",
        "cpf": "529.982.247-25",
        "email": "carla.dias@example.test",
        "role": "therapist",
        **over,
    }
    return client.post(reverse("team_member_create"), data)


def _shown_password(response) -> str:
    match = re.search(
        r'data-testid="temporary-password">([^<]+)<', response.content.decode()
    )
    assert match is not None, "a senha provisória não apareceu na página"
    return match.group(1)


# ── Login único, sem abas ───────────────────────────────────────────────────


def test_login_is_a_single_form_without_role_tabs() -> None:
    html = Client().get(reverse("account_login")).content.decode()
    assert "aurora-role-tab" not in html and "data-role-tab" not in html
    assert "Médico / Psi" not in html and "Recepção" not in html
    assert 'name="cpf"' in html and 'name="password"' in html
    assert 'name="email"' not in html
    assert html.count("<form") >= 1
    assert "Pacientes usam o aplicativo" in html


# ── Senha aleatória ─────────────────────────────────────────────────────────


def test_generated_passwords_are_random_readable_and_strong() -> None:
    samples = {generate_temporary_password() for _ in range(300)}
    assert len(samples) == 300
    for password in samples:
        assert PASSWORD_SHAPE.match(password)
        letters = password.replace("-", "")
        assert any(c.islower() for c in letters)
        assert any(c.isupper() for c in letters)
        assert any(c.isdigit() for c in letters)
        assert not set(letters) & set("0O1lIo")


# ── Cadastro pela administração ─────────────────────────────────────────────


def test_admin_registers_a_person_and_the_password_is_shown_only_once() -> None:
    clinic, admin, client = _stage()
    response = _register(client)
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    password = _shown_password(response)
    assert PASSWORD_SHAPE.match(password)
    user = User.objects.get(email="carla.dias@example.test")
    assert user.check_password(password) and user.must_change_password is True
    assert user.get_full_name() == "Carla Dias"
    membership = ClinicMembership.objects.for_clinic(clinic.pk).get(user=user)
    assert membership.role == "therapist" and membership.is_active
    # a senha não fica em nenhum lugar legível: nem na sessão do administrador
    assert password not in str(dict(client.session))
    again = client.get(reverse("team_list")).content.decode()
    assert password not in again


@pytest.mark.parametrize("role", TEAM_MEMBER_ROLES)
def test_every_team_function_can_be_registered(role: str) -> None:
    clinic, _admin, client = _stage()
    response = _register(
        client, role=role, email=f"{role}@example.test", cpf=synthetic_cpf(900)
    )
    assert response.status_code == 200
    membership = ClinicMembership.objects.for_clinic(clinic.pk).get(
        user__email=f"{role}@example.test"
    )
    assert membership.role == role


def test_only_the_clinic_administrator_registers_people() -> None:
    clinic, _admin, _client = _stage()
    for role in ("therapist", "administrative_staff"):
        member = _member(clinic, role, f"{role}-tenta@example.test")
        client = _client_for(member, clinic)
        assert client.get(reverse("team_member_create")).status_code == 403
        assert _register(client, email="intruso@example.test").status_code == 403
    assert not User.objects.filter(email="intruso@example.test").exists()


def test_patients_are_not_registered_as_team_and_input_is_validated() -> None:
    _clinic, _admin, client = _stage()
    assert _register(client, role="patient").status_code == 200
    assert not User.objects.filter(email="carla.dias@example.test").exists()
    users_before = User.objects.count()
    bad = _register(client, email="nao-e-email")
    assert bad.status_code == 200
    assert User.objects.count() == users_before


def test_existing_member_is_refused_and_other_clinics_keep_their_password() -> None:
    clinic, _admin, client = _stage()
    _register(client)
    again = _register(client)
    assert again.status_code == 200 and "vínculo ativo" in again.content.decode()
    other_clinic = ClinicFactory.create()
    elsewhere = _member(other_clinic, "therapist", "ja-existe@example.test")
    response = _register(client, email="ja-existe@example.test", cpf=elsewhere.cpf)
    html = response.content.decode()
    assert 'data-testid="temporary-password"' not in html
    assert "continua com a própria senha" in html
    elsewhere.refresh_from_db()
    assert elsewhere.check_password(PASSWORD) and not elsewhere.must_change_password
    assert (
        ClinicMembership.objects.for_clinic(clinic.pk).filter(user=elsewhere).exists()
    )


def test_registration_is_audited_without_the_password() -> None:
    from audit.models import AuditEvent

    clinic, admin, client = _stage()
    response = _register(client)
    password = _shown_password(response)
    events = AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk, resource_type="team_member"
    )
    assert events.count() == 1 and events.get().actor_id == admin.pk
    assert password not in repr(list(events.values()))


def test_registered_person_signs_in_with_the_cpf_and_it_is_shown_masked() -> None:
    clinic, _admin, client = _stage()
    response = _register(client)
    html = response.content.decode()
    user = User.objects.get(email="carla.dias@example.test")
    assert user.cpf == CARLA_CPF
    assert CARLA_CPF_MASKED in html and "529.982.247-25" not in html
    assert "CPF da pessoa" in html
    listing = client.get(reverse("team_list")).content.decode()
    assert CARLA_CPF_MASKED in listing
    assert "529.982.247-25" not in listing and CARLA_CPF not in listing


def test_registration_requires_a_valid_cpf() -> None:
    _clinic, _admin, client = _stage()
    before = User.objects.count()
    for bad in ("", "123.456.789-00", "111.111.111-11", "5299822472", "abc"):
        response = _register(client, cpf=bad)
        assert response.status_code == 200, bad
        assert 'data-testid="temporary-password"' not in response.content.decode()
    assert User.objects.count() == before


def test_cpf_is_unique_across_the_platform() -> None:
    _clinic, _admin, client = _stage()
    _register(client)
    other_clinic = ClinicFactory.create()
    other_admin = _member(other_clinic, "clinic_admin", "outra-admin@example.test")
    other = _client_for(other_admin, other_clinic)
    # o mesmo CPF com outro e-mail é a mesma pessoa: ganha o vínculo, mantém a senha
    response = _register(other, email="outro-email@example.test")
    assert 'data-testid="temporary-password"' not in response.content.decode()
    assert User.objects.filter(cpf=CARLA_CPF).count() == 1
    assert not User.objects.filter(email="outro-email@example.test").exists()


def test_cpf_and_email_of_different_people_are_refused() -> None:
    clinic, _admin, client = _stage()
    _register(client)
    stranger = _member(clinic, "therapist", "estranho@example.test")
    before = ClinicMembership.infrastructure_objects.count()
    response = _register(client, email=stranger.email, cpf=CARLA_CPF)
    assert "contas diferentes" in response.content.decode()
    assert ClinicMembership.infrastructure_objects.count() == before


def test_account_without_cpf_receives_the_informed_one_and_keeps_its_password() -> None:
    clinic, _admin, client = _stage()
    legacy = User.objects.create_user(email="antigo@example.test", password=PASSWORD)
    assert legacy.cpf is None
    response = _register(client, email="antigo@example.test")
    assert 'data-testid="temporary-password"' not in response.content.decode()
    legacy.refresh_from_db()
    assert legacy.cpf == CARLA_CPF and legacy.check_password(PASSWORD)
    assert ClinicMembership.objects.for_clinic(clinic.pk).filter(user=legacy).exists()
    # e uma conta que já tem outro CPF não é reaproveitada com um CPF diferente
    other = _member(clinic, "therapist", "com-cpf@example.test")
    refused = _register(client, email=other.email, cpf=synthetic_cpf(901))
    assert "outro CPF" in refused.content.decode()


def test_cpf_is_stored_as_digits_and_blank_is_not_a_value() -> None:
    first = User.objects.create_user(
        email="a@example.test", password=PASSWORD, cpf="529.982.247-25"
    )
    assert first.cpf == CARLA_CPF and first.masked_cpf == CARLA_CPF_MASKED
    for index in range(2):
        user = User.objects.create_user(email=f"sem-cpf-{index}@example.test", cpf="")
        assert user.cpf is None and user.masked_cpf == ""


def test_the_cpf_never_reaches_the_audit_trail() -> None:
    from audit.models import AuditEvent

    clinic, _admin, client = _stage()
    _register(client)
    events = AuditEvent.infrastructure_objects.filter(clinic_id=clinic.pk)
    assert CARLA_CPF not in repr(list(events.values()))


def test_service_refuses_non_administrators_and_unknown_roles() -> None:
    clinic, _admin, _client = _stage()
    therapist = _member(clinic, "therapist", "terapeuta-servico@example.test")
    kwargs = dict(
        clinic_id=clinic.pk,
        cpf=CARLA_CPF,
        email="x@example.test",
        first_name="X",
        last_name="Y",
        role="therapist",
        request_id=uuid4(),
    )
    with pytest.raises(PermissionDenied):
        create_team_member(actor=therapist, **kwargs)
    admin = User.objects.get(email="admin-cadastro@example.test")
    with pytest.raises(ValidationError):
        create_team_member(actor=admin, **{**kwargs, "role": "patient"})


# ── Troca obrigatória no primeiro acesso ────────────────────────────────────


def _first_access(client: Client):
    """Registra uma pessoa e entra pelo login real com a senha provisória."""
    shown = _shown_password(_register(client))
    person = Client()
    response = person.post(
        reverse("account_login"),
        {"cpf": CARLA_CPF, "password": shown},
    )
    assert response.status_code == 302
    return person, shown


def test_first_access_holds_the_person_on_the_password_change_page() -> None:
    _clinic, _admin, client = _stage()
    person, _shown = _first_access(client)
    for route in ("workspace_vertical", "patient_list", "appointment_list"):
        response = person.get(reverse(route))
        assert response.status_code == 302
        assert response["Location"] == reverse("password_change_required")
    api = person.get("/api/v1/journal/entries/")
    assert api.status_code == 403
    assert api.json()["code"] == "password_change_required"
    page = person.get(reverse("password_change_required"))
    assert page.status_code == 200 and page["Cache-Control"] == "private, no-store"
    # sair continua possível
    assert person.post(reverse("account_logout")).status_code in {200, 302}


def test_changing_the_password_releases_the_account_and_keeps_the_session() -> None:
    _clinic, _admin, client = _stage()
    person, shown = _first_access(client)
    new = "Outra-Senha-Segura-2026-xyz"  # nosec - credencial sintética de teste
    response = person.post(
        reverse("password_change_required"),
        {"current_password": shown, "new_password": new, "confirm_password": new},
    )
    assert response.status_code == 302
    user = User.objects.get(email="carla.dias@example.test")
    assert user.must_change_password is False and user.check_password(new)
    # a sessão continua válida e o sistema abre
    assert person.get(reverse("workspace_vertical")).status_code == 200
    # a provisória deixou de valer
    fresh = Client().post(
        reverse("account_login"),
        {"cpf": CARLA_CPF, "password": shown},
    )
    assert fresh.status_code == 200
    # e a página de troca não serve mais a quem já trocou
    assert person.get(reverse("password_change_required")).status_code == 302


@pytest.mark.parametrize(
    "case",
    ["wrong_current", "mismatch", "same_as_temporary", "too_short", "numeric_only"],
)
def test_the_password_change_rejects_bad_input(case: str) -> None:
    _clinic, _admin, client = _stage()
    person, shown = _first_access(client)
    data = {
        "wrong_current": ("errada-e-longa-123", "Senha-Nova-Valida-777x", None),
        "mismatch": (shown, "Senha-Nova-Valida-777x", "Outra-Coisa-Diferente-1"),
        "same_as_temporary": (shown, shown, shown),
        "too_short": (shown, "Ab1-x", "Ab1-x"),
        "numeric_only": (shown, "4815162342481516", "4815162342481516"),
    }[case]
    current, new, confirm = data
    response = person.post(
        reverse("password_change_required"),
        {
            "current_password": current,
            "new_password": new,
            "confirm_password": confirm or new,
        },
    )
    assert response.status_code == 200
    user = User.objects.get(email="carla.dias@example.test")
    assert user.must_change_password is True and user.check_password(shown)


# ── Redefinição pela administração ──────────────────────────────────────────


def test_admin_resets_a_members_password_and_ends_their_sessions() -> None:
    clinic, _admin, client = _stage()
    person, shown = _first_access(client)
    new = "Troca-Valida-do-Primeiro-Acesso-9"  # nosec - credencial sintética de teste
    person.post(
        reverse("password_change_required"),
        {"current_password": shown, "new_password": new, "confirm_password": new},
    )
    assert person.get(reverse("workspace_vertical")).status_code == 200
    membership = ClinicMembership.objects.for_clinic(clinic.pk).get(
        user__email="carla.dias@example.test"
    )
    response = client.post(reverse("team_member_reset_password", args=[membership.pk]))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    password = _shown_password(response)
    user = User.objects.get(email="carla.dias@example.test")
    assert user.check_password(password) and user.must_change_password is True
    assert not user.check_password(new)
    # a sessão que a pessoa tinha deixou de valer
    assert person.get(reverse("workspace_vertical")).status_code == 302
    location = person.get(reverse("workspace_vertical"))["Location"]
    assert "/accounts/login" in location or "/admin/login" in location


def test_reset_is_refused_for_yourself_other_clinics_and_foreign_memberships() -> None:
    clinic, admin, client = _stage()
    own = ClinicMembership.objects.for_clinic(clinic.pk).get(user=admin)
    refused = client.post(reverse("team_member_reset_password", args=[own.pk]))
    assert refused.status_code == 302  # volta à lista com a mensagem de recusa
    other_clinic = ClinicFactory.create()
    shared = _member(clinic, "therapist", "atua-nas-duas@example.test")
    ClinicMembershipFactory.create(clinic=other_clinic, user=shared, role="therapist")
    shared_membership = ClinicMembership.objects.for_clinic(clinic.pk).get(user=shared)
    client.post(reverse("team_member_reset_password", args=[shared_membership.pk]))
    shared.refresh_from_db()
    assert shared.check_password(PASSWORD)  # a senha dela não foi trocada
    outsider = _member(other_clinic, "therapist", "outra-clinica@example.test")
    foreign = ClinicMembership.objects.for_clinic(other_clinic.pk).get(user=outsider)
    assert (
        client.post(
            reverse("team_member_reset_password", args=[foreign.pk])
        ).status_code
        == 403
    )
    outsider.refresh_from_db()
    assert outsider.check_password(PASSWORD)


def test_only_the_administrator_can_reset() -> None:
    clinic, _admin, _client = _stage()
    therapist = _member(clinic, "therapist", "terapeuta-reset@example.test")
    target = _member(clinic, "administrative_staff", "alvo-reset@example.test")
    membership = ClinicMembership.objects.for_clinic(clinic.pk).get(user=target)
    response = _client_for(therapist, clinic).post(
        reverse("team_member_reset_password", args=[membership.pk])
    )
    assert response.status_code == 403
    target.refresh_from_db()
    assert target.check_password(PASSWORD)


# ── O sistema se apresenta pela função ──────────────────────────────────────

SIDEBAR = {
    "admin": "Gestão da clínica",
    "team": "Usuários e equipe",
    "setup": "Configurar clínica",
    "patients": "Pacientes",
    "aftercare": "Pós-alta e concierge",
    "agenda": "Agenda de consultas",
    "therapist_panel": "Painel profissional",
    "clinical": "Psiquiatria e recuperação",
    "design": "Sistema de design",
    "account": "Segurança da conta",
}


def _sidebar(role: str) -> str:
    clinic = ClinicFactory.create()
    user = _member(clinic, role, f"{role}-menu@example.test")
    page = _client_for(user, clinic).get(reverse("workspace_vertical"))
    assert page.status_code == 200
    return page.content.decode()


@pytest.mark.parametrize(
    ("role", "shown", "hidden"),
    [
        (
            "clinic_admin",
            {"admin", "team", "setup", "patients", "aftercare", "agenda", "account"},
            {"therapist_panel", "clinical", "design"},
        ),
        (
            "therapist",
            {"patients", "agenda", "therapist_panel", "clinical", "account"},
            {"admin", "team", "setup", "aftercare", "design"},
        ),
        (
            "administrative_staff",
            {"patients", "aftercare", "agenda", "account"},
            {"admin", "team", "setup", "therapist_panel", "clinical", "design"},
        ),
    ],
)
def test_the_menu_follows_the_function(
    role: str, shown: set[str], hidden: set[str]
) -> None:
    html = _sidebar(role)
    for key in shown:
        assert SIDEBAR[key] in html, (role, key)
    for key in hidden:
        assert SIDEBAR[key] not in html, (role, key)


def test_the_home_shows_the_function_and_only_its_shortcuts() -> None:
    admin_home = _sidebar("clinic_admin")
    assert "Sua função: Administrador da clínica." in admin_home
    assert "Portal de psiquiatria" not in admin_home
    therapist_home = _sidebar("therapist")
    assert "Sua função: Terapeuta." in therapist_home
    assert "Portal de psiquiatria" in therapist_home
    staff_home = _sidebar("administrative_staff")
    assert "Sua função: Equipe administrativa." in staff_home
    assert "Cadastre pessoas, defina a função" not in staff_home
