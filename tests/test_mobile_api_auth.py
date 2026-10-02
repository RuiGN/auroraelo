"""Sessão do app do paciente: login, tokens rotativos, revogação e isolamento."""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from typing import Any
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent
from clinics.models import ClinicMembership
from concierge import services as concierge_services
from mobile_api.contracts import RevokeReason
from mobile_api.models import MobileSession
from mobile_api.services import purge_finished_sessions
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient,
    make_patient_login,
)
from tests.factories import ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/mobile/auth/login/"
REFRESH = "/api/v1/mobile/auth/refresh/"
LOGOUT = "/api/v1/mobile/auth/logout/"
SESSIONS = "/api/v1/mobile/auth/sessions/"
ME = "/api/v1/mobile/me/"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _post(client: Client, url: str, body: dict[str, Any], **extra: Any) -> Any:
    return client.post(url, body, content_type="application/json", **extra)


def _login(
    client: Client, who: PatientLogin, *, label: str = "iPhone de teste", **extra: Any
) -> dict[str, Any]:
    response = _post(
        client,
        LOGIN,
        {
            "email": who.user.email,
            "password": who.password,
            "device_label": label,
            "platform": "ios",
            "app_version": "1.0.0",
            **extra,
        },
    )
    assert response.status_code == 200, response.content
    tokens: dict[str, Any] = response.json()
    return tokens


def _auth(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _setup() -> tuple[Stage, PatientLogin]:
    stage = build_stage()
    return stage, make_patient_login(
        stage.clinic, stage.admin, name="Ana Souza", social_name="Aninha"
    )


# ── Login ───────────────────────────────────────────────────────────────────


def test_login_issues_prefixed_tokens_and_never_stores_them() -> None:
    stage, patient = _setup()
    tokens = _login(Client(), patient)
    assert tokens["access_token"].startswith("aem_")
    assert tokens["refresh_token"].startswith("aer_")
    assert tokens["clinic"] == {"id": str(stage.clinic.pk), "name": stage.clinic.name}
    assert tokens["patient"] == {
        "id": str(patient.profile.pk),
        "display_name": "Aninha",
    }
    session = MobileSession.infrastructure_objects.get()
    assert session.clinic_id == stage.clinic.pk and session.user_id == patient.user.pk
    assert session.patient_profile_id == patient.profile.pk
    assert (session.device_label, session.platform, session.app_version) == (
        "iPhone de teste",
        "ios",
        "1.0.0",
    )
    stored = " ".join(
        str(getattr(session, field.name))
        for field in MobileSession._meta.get_fields()
        if hasattr(field, "attname")
    )
    assert tokens["access_token"] not in stored
    assert tokens["refresh_token"] not in stored
    assert len(session.access_digest) == 64 and len(session.refresh_digest) == 64


def test_login_is_audited_without_credentials() -> None:
    stage, patient = _setup()
    _login(Client(), patient)
    event = AuditEvent.objects.for_clinic(stage.clinic.pk).get(action="login")
    assert event.resource_type == "mobile_session" and event.outcome == "success"
    assert event.actor_id == patient.user.pk


def test_login_failures_are_indistinguishable() -> None:
    stage, patient = _setup()
    therapist_password = "Outra-Senha-456"  # nosec - sintética
    therapist = stage.therapist
    therapist.set_password(therapist_password)
    therapist.save()
    inactive = make_patient_login(stage.clinic, stage.admin, name="Inativa")
    inactive.user.is_active = False
    inactive.user.save()
    client = Client()
    bodies = []
    for email, password in (
        (patient.user.email, "senha-errada"),
        ("ninguem@example.test", "qualquer"),
        (therapist.email, therapist_password),  # credencial certa, mas não é paciente
        (inactive.user.email, inactive.password),
    ):
        response = _post(client, LOGIN, {"email": email, "password": password})
        assert response.status_code == 401
        bodies.append(response.json())
    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["code"] == "invalid_credentials"
    assert MobileSession.infrastructure_objects.count() == 0


def test_login_shares_the_failure_budget_and_returns_429() -> None:
    _stage, patient = _setup()
    client = Client()
    for _ in range(5):
        assert (
            _post(
                client, LOGIN, {"email": patient.user.email, "password": "x"}
            ).status_code
            == 401
        )
    blocked = _post(
        client, LOGIN, {"email": patient.user.email, "password": patient.password}
    )
    assert blocked.status_code == 429 and blocked.json()["code"] == "rate_limited"


def test_login_requires_clinic_choice_only_when_ambiguous() -> None:
    stage, patient = _setup()
    second = stage.other_clinic
    ClinicMembershipFactory.create(
        clinic=second, user=patient.user, role=ClinicMembership.Role.PATIENT
    )
    other_profile = make_patient(second, stage.other_admin)
    other_profile.user = patient.user
    other_profile.save()
    client = Client()
    ambiguous = _post(
        client, LOGIN, {"email": patient.user.email, "password": patient.password}
    )
    assert ambiguous.status_code == 409
    body = ambiguous.json()
    assert body["code"] == "clinic_choice_required"
    assert {c["id"] for c in body["clinics"]} == {str(stage.clinic.pk), str(second.pk)}
    chosen = _post(
        client,
        LOGIN,
        {
            "email": patient.user.email,
            "password": patient.password,
            "clinic_id": str(second.pk),
        },
    )
    assert chosen.status_code == 200
    assert chosen.json()["clinic"]["id"] == str(second.pk)
    # clínica onde a pessoa não é paciente nunca é aceita
    foreign = _post(
        client,
        LOGIN,
        {
            "email": patient.user.email,
            "password": patient.password,
            "clinic_id": str(uuid4()),
        },
    )
    assert foreign.status_code == 401


def test_login_and_calls_work_without_csrf_token_or_cookie() -> None:
    _stage, patient = _setup()
    client = Client(enforce_csrf_checks=True)
    tokens = _login(client, patient)
    assert client.get(ME, headers=_auth(tokens)).status_code == 200
    assert client.post(LOGOUT, headers=_auth(tokens)).status_code == 204


# ── Autenticação por requisição ─────────────────────────────────────────────


def test_mobile_routes_refuse_missing_malformed_and_session_cookie_credentials() -> (
    None
):
    stage, patient = _setup()
    client = Client()
    assert client.get(ME).status_code == 401
    assert client.get(ME, HTTP_AUTHORIZATION="Bearer lixo").status_code == 401
    assert (
        client.get(ME, HTTP_AUTHORIZATION="Bearer aem_" + "a" * 500).status_code == 401
    )
    assert client.get(ME, HTTP_AUTHORIZATION="Bearer ").status_code == 401
    # sessão web válida não vale para as rotas do app
    web = Client()
    web.force_login(patient.user)
    session = web.session
    session["active_clinic_id"] = str(stage.clinic.pk)
    session.save()
    # o paciente nem abre sessão web (403); sessão web de equipe também não vale (401)
    assert web.get(ME).status_code in {401, 403}
    team = Client()
    team.force_login(stage.therapist)
    session = team.session
    session["active_clinic_id"] = str(stage.clinic.pk)
    session.save()
    assert team.get(ME).status_code == 401


def test_me_returns_only_what_the_patient_app_needs() -> None:
    stage, patient = _setup()
    concierge_services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.profile.pk,
        discharge_date=timezone.localdate() - timedelta(days=4),
        request_id=uuid4(),
        notes="nota administrativa interna",
    )
    tokens = _login(Client(), patient)
    response = Client().get(ME, headers=_auth(tokens))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "id",
        "display_name",
        "language",
        "timezone",
        "clinic",
        "discharge_date",
        "care_team",
    }
    assert body["display_name"] == "Aninha"
    assert (
        body["discharge_date"] == (timezone.localdate() - timedelta(days=4)).isoformat()
    )
    # régua, contatos e notas da clínica nunca saem
    raw = response.content.decode()
    assert "nota administrativa" not in raw and "contact" not in raw
    assert response["Cache-Control"] == "private, no-store"


def test_client_headers_and_params_cannot_switch_clinic_or_patient() -> None:
    stage, patient = _setup()
    other = make_patient_login(
        stage.other_clinic, stage.other_admin, name="Outra Pessoa"
    )
    tokens = _login(Client(), patient)
    response = Client().get(
        f"{ME}?patient_id={other.profile.pk}&clinic_id={stage.other_clinic.pk}",
        HTTP_X_CLINIC_ID=str(stage.other_clinic.pk),
        headers=_auth(tokens),
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(patient.profile.pk)
    assert response.json()["clinic"]["id"] == str(stage.clinic.pk)


def test_expired_access_token_is_refused_but_refresh_still_works() -> None:
    _stage, patient = _setup()
    tokens = _login(Client(), patient)
    MobileSession.infrastructure_objects.update(
        access_expires_at=timezone.now() - timedelta(seconds=1)
    )
    client = Client()
    assert client.get(ME, headers=_auth(tokens)).status_code == 401
    renewed = _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]})
    assert renewed.status_code == 200
    assert client.get(ME, headers=_auth(renewed.json())).status_code == 200


# ── Renovação rotativa ──────────────────────────────────────────────────────


def test_refresh_rotates_both_tokens() -> None:
    _stage, patient = _setup()
    client = Client()
    first = _login(client, patient)
    response = _post(client, REFRESH, {"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["access_token"] != first["access_token"]
    assert second["session_id"] == first["session_id"]
    assert (
        client.get(ME, headers=_auth(first)).status_code == 401
    )  # acesso antigo morre
    assert client.get(ME, headers=_auth(second)).status_code == 200


def test_replaying_a_rotated_refresh_token_revokes_the_whole_session() -> None:
    stage, patient = _setup()
    client = Client()
    first = _login(client, patient)
    second = _post(client, REFRESH, {"refresh_token": first["refresh_token"]}).json()
    replay = _post(client, REFRESH, {"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401 and replay.json()["code"] == "invalid_token"
    session = MobileSession.infrastructure_objects.get()
    assert session.revoked_reason == RevokeReason.REUSE_DETECTED
    # o par legítimo mais novo também caiu: não dá para saber quem é o dono
    assert client.get(ME, headers=_auth(second)).status_code == 401
    assert (
        _post(client, REFRESH, {"refresh_token": second["refresh_token"]}).status_code
        == 401
    )
    denied = AuditEvent.objects.for_clinic(stage.clinic.pk).filter(outcome="denied")
    assert denied.count() == 1


def test_refresh_rejects_unknown_expired_and_oversized_tokens() -> None:
    _stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    for bad in (
        "",
        "aer_curto",
        "aem_" + "x" * 40,
        "aer_" + "y" * 400,
        tokens["access_token"],
    ):
        assert _post(client, REFRESH, {"refresh_token": bad}).status_code in {401, 422}
    MobileSession.infrastructure_objects.update(
        refresh_expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert (
        _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )


def test_session_has_an_absolute_lifetime() -> None:
    _stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    MobileSession.infrastructure_objects.update(
        absolute_expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert client.get(ME, headers=_auth(tokens)).status_code == 401
    assert (
        _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )


def test_refresh_never_extends_beyond_the_absolute_lifetime() -> None:
    _stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    soon = timezone.now() + timedelta(days=2)
    MobileSession.infrastructure_objects.update(absolute_expires_at=soon)
    renewed = _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]}).json()
    session = MobileSession.infrastructure_objects.get()
    assert session.refresh_expires_at <= soon and session.access_expires_at <= soon
    assert renewed["refresh_expires_at"] is not None


# ── Perda de autorização ────────────────────────────────────────────────────


def _assert_dead(client: Client, tokens: dict[str, Any], reason: RevokeReason) -> None:
    assert client.get(ME, headers=_auth(tokens)).status_code == 401
    assert (
        _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )
    assert MobileSession.infrastructure_objects.get().revoked_reason == reason


def test_password_change_ends_every_mobile_session() -> None:
    _stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    user = User.objects.get(pk=patient.user.pk)
    user.set_password("Nova-Senha-789")  # nosec - sintética
    user.save()
    _assert_dead(client, tokens, RevokeReason.CREDENTIALS_CHANGED)


def test_deactivated_user_loses_access_immediately() -> None:
    _stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    User.objects.filter(pk=patient.user.pk).update(is_active=False)
    _assert_dead(client, tokens, RevokeReason.ACCESS_ENDED)


def test_ended_membership_or_inactive_clinic_ends_the_session() -> None:
    stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    ClinicMembership.infrastructure_objects.filter(
        user=patient.user, clinic=stage.clinic
    ).update(
        valid_from=timezone.localdate() - timedelta(days=10),
        valid_until=timezone.localdate() - timedelta(days=1),
    )
    _assert_dead(client, tokens, RevokeReason.ACCESS_ENDED)

    stage2, patient2 = _setup()
    MobileSession.infrastructure_objects.all().delete()
    tokens2 = _login(client, patient2)
    type(stage2.clinic).infrastructure_objects.filter(pk=stage2.clinic.pk).update(
        is_active=False
    )
    _assert_dead(client, tokens2, RevokeReason.ACCESS_ENDED)


def test_a_therapist_token_cannot_exist_and_a_role_change_ends_the_session() -> None:
    stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    ClinicMembership.infrastructure_objects.filter(
        user=patient.user, clinic=stage.clinic
    ).update(role=ClinicMembership.Role.THERAPIST)
    _assert_dead(client, tokens, RevokeReason.ACCESS_ENDED)


def test_blocked_clinic_gets_402_but_can_still_log_out() -> None:
    from master_panel.models import TenantSubscription

    stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    TenantSubscription.objects.create(
        clinic=stage.clinic, status=TenantSubscription.Status.BLOCKED
    )
    assert client.get(ME, headers=_auth(tokens)).status_code == 402
    assert client.post(LOGOUT, headers=_auth(tokens)).status_code == 204


# ── Logout e aparelhos ──────────────────────────────────────────────────────


def test_logout_revokes_the_session_and_is_audited() -> None:
    stage, patient = _setup()
    client = Client()
    tokens = _login(client, patient)
    assert client.post(LOGOUT, headers=_auth(tokens)).status_code == 204
    assert client.get(ME, headers=_auth(tokens)).status_code == 401
    assert (
        _post(client, REFRESH, {"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )
    session = MobileSession.infrastructure_objects.get()
    assert session.revoked_reason == RevokeReason.LOGOUT
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(action="update", resource_type="mobile_session")
        .count()
        == 1
    )


def test_device_list_and_revocation_are_limited_to_the_own_person() -> None:
    stage, patient = _setup()
    other = make_patient_login(stage.clinic, stage.admin, name="Outra Pessoa")
    client = Client()
    phone = _login(client, patient, label="Celular")
    tablet = _login(client, patient, label="Tablet")
    stranger = _login(client, other, label="Aparelho alheio")

    listing = client.get(SESSIONS, headers=_auth(phone)).json()
    assert {item["device_label"] for item in listing} == {"Celular", "Tablet"}
    assert [
        item["is_current"] for item in listing if item["device_label"] == "Celular"
    ] == [True]
    assert all("token" not in str(item) for item in listing)

    # id de outra pessoa responde como inexistente e não derruba nada
    foreign = client.delete(
        f"{SESSIONS}{stranger['session_id']}/", headers=_auth(phone)
    )
    assert foreign.status_code == 404
    assert client.get(ME, headers=_auth(stranger)).status_code == 200
    missing = client.delete(f"{SESSIONS}{uuid4()}/", headers=_auth(phone))
    assert missing.status_code == 404 and missing.json() == foreign.json()

    assert (
        client.delete(
            f"{SESSIONS}{tablet['session_id']}/", headers=_auth(phone)
        ).status_code
        == 204
    )
    assert client.get(ME, headers=_auth(tablet)).status_code == 401
    assert client.get(ME, headers=_auth(phone)).status_code == 200


def test_revoke_others_keeps_only_the_current_device() -> None:
    _stage, patient = _setup()
    client = Client()
    phone = _login(client, patient, label="Celular")
    tablet = _login(client, patient, label="Tablet")
    watch = _login(client, patient, label="Outro")
    response = client.post(f"{SESSIONS}revoke-others/", headers=_auth(phone))
    assert response.status_code == 200 and response.json() == {"revoked": 2}
    assert client.get(ME, headers=_auth(phone)).status_code == 200
    assert client.get(ME, headers=_auth(tablet)).status_code == 401
    assert client.get(ME, headers=_auth(watch)).status_code == 401


def test_oldest_device_is_evicted_when_the_limit_is_reached(settings: Any) -> None:
    settings.MOBILE_MAX_SESSIONS_PER_USER = 2
    _stage, patient = _setup()
    client = Client()
    first = _login(client, patient, label="Um")
    second = _login(client, patient, label="Dois")
    third = _login(client, patient, label="Três")
    assert client.get(ME, headers=_auth(first)).status_code == 401
    assert client.get(ME, headers=_auth(second)).status_code == 200
    assert client.get(ME, headers=_auth(third)).status_code == 200
    assert (
        MobileSession.infrastructure_objects.get(pk=first["session_id"]).revoked_reason
        == RevokeReason.EVICTED
    )


def test_device_label_is_sanitized_and_platform_is_allowlisted() -> None:
    _stage, patient = _setup()
    _login(
        Client(),
        patient,
        label="  Celular   da\nAna  " + "x" * 200,
        platform="symbian",
    )
    session = MobileSession.infrastructure_objects.get()
    assert session.platform == "other"
    assert "\n" not in session.device_label and len(session.device_label) <= 80


# ── Outras rotas da API aceitam o token do app ──────────────────────────────


def test_app_tokens_are_refused_outside_the_mobile_routes() -> None:
    """O token do app só vale em /api/v1/mobile/; as demais rotas são por sessão."""
    _stage, patient = _setup()
    client = Client()
    mine = _login(client, patient)
    for method, url in (
        ("get", "/api/v1/journal/entries/"),
        ("get", "/api/v1/journal/checkins/"),
        ("get", "/api/v1/goals/"),
        ("get", "/api/v1/scheduling/appointments/"),
        ("post", "/api/v1/scheduling/appointments/"),
    ):
        response = getattr(client, method)(
            url, content_type="application/json", headers=_auth(mine)
        )
        assert response.status_code in {401, 403}, (method, url)


# ── Retenção ────────────────────────────────────────────────────────────────


def test_finished_sessions_are_purged_after_the_retention_window() -> None:
    _stage, patient = _setup()
    client = Client()
    live = _login(client, patient, label="Ativo")
    gone = _login(client, patient, label="Antigo")
    old = timezone.now() - timedelta(days=45)
    MobileSession.infrastructure_objects.filter(pk=gone["session_id"]).update(
        revoked_at=old, revoked_reason=RevokeReason.LOGOUT
    )
    recent = _login(client, patient, label="Recente")
    client.post(LOGOUT, headers=_auth(recent))
    assert purge_finished_sessions(retention_days=30) == 1
    remaining = set(MobileSession.infrastructure_objects.values_list("pk", flat=True))
    assert {live["session_id"], recent["session_id"]} == {str(pk) for pk in remaining}


def test_unscoped_manager_queries_are_refused() -> None:
    with pytest.raises(RuntimeError):
        MobileSession.objects.all()
    stage, _patient = _setup()
    assert MobileSession.objects.for_clinic(stage.clinic.pk).count() == 0
    assert UserFactory.create() is not None


def test_routine_token_renewal_is_not_audited_but_a_replay_is() -> None:
    stage, patient = _setup()
    client = Client()
    first = _login(client, patient)
    events = AuditEvent.objects.for_clinic(stage.clinic.pk).filter(
        resource_type="mobile_session"
    )
    assert events.count() == 1  # só o login
    _post(client, REFRESH, {"refresh_token": first["refresh_token"]})
    assert events.count() == 1  # renovação de rotina fica fora da trilha
    _post(client, REFRESH, {"refresh_token": first["refresh_token"]})
    assert events.filter(outcome="denied").count() == 1  # o reuso, sim


def test_api_responses_are_never_cached() -> None:
    response = Client().get("/api/v1/ping/")
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert Client().get("/api/v1/mobile/me/")["Cache-Control"] == "private, no-store"


def test_purge_command_removes_only_old_finished_sessions() -> None:
    _stage, patient = _setup()
    client = Client()
    keep = _login(client, patient, label="Atual")
    old = _login(client, patient, label="Antigo")
    MobileSession.infrastructure_objects.filter(pk=old["session_id"]).update(
        revoked_at=timezone.now() - timedelta(days=60),
        revoked_reason=RevokeReason.LOGOUT,
    )
    out = StringIO()
    call_command("purge_mobile_sessions", "--days", "30", stdout=out)
    assert "1 sessão" in out.getvalue()
    remaining = MobileSession.infrastructure_objects.values_list("pk", flat=True)
    assert {str(pk) for pk in remaining} == {keep["session_id"]}
