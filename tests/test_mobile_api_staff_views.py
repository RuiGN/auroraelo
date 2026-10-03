"""Painel web do aplicativo do paciente: papéis, tenant, revogação e segredos."""

from __future__ import annotations

import gettext as gettext_module
import re
from datetime import timedelta
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.template import engines
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from accounts.models import ClinicInvitation, User
from audit.models import AuditEvent
from clinics.models import Clinic
from concierge import services as concierge_services
from mobile_api import policies, selectors, services
from mobile_api.contracts import RevokeReason
from mobile_api.models import MobileSession
from people import services as people_services
from people.models import PatientProfile
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient,
    make_patient_login,
)

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/mobile/auth/login/"
REFRESH = "/api/v1/mobile/auth/refresh/"
ACTIVATE = "/api/v1/mobile/auth/activate/"
ME = "/api/v1/mobile/me/"
PASSWORD = "Senha-Segura-Longa-123"  # nosec - credencial sintética de teste


@pytest.fixture(autouse=True)
def _fresh_state() -> None:
    cache.clear()
    mail.outbox.clear()


# ── Apoio ───────────────────────────────────────────────────────────────────


def _client(clinic: Clinic, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def _post_json(url: str, body: dict[str, Any]) -> Any:
    return Client().post(url, body, content_type="application/json")


def _app_login(who: PatientLogin, label: str = "iPhone da Ana") -> dict[str, Any]:
    response = _post_json(
        LOGIN,
        {
            "email": who.user.email,
            "password": who.password,
            "device_label": label,
            "platform": "ios",
            "app_version": "2.4.1",
        },
    )
    assert response.status_code == 200, response.content
    tokens: dict[str, Any] = response.json()
    return tokens


def _bearer(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _me_status(tokens: dict[str, Any]) -> int:
    return int(Client().get(ME, headers=_bearer(tokens)).status_code)


def _refresh_status(tokens: dict[str, Any]) -> int:
    response = _post_json(REFRESH, {"refresh_token": tokens["refresh_token"]})
    return int(response.status_code)


def _link(stage: Stage, profile: PatientProfile, *, expired: bool = False) -> None:
    today = timezone.localdate()
    people_services.create_patient_care_relationship(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        therapist_id=stage.therapist.pk,
        patient_profile_id=profile.pk,
        function="Terapeuta responsável",
        valid_from=today - timedelta(days=30 if expired else 1),
        valid_until=today - timedelta(days=1) if expired else None,
        request_id=uuid4(),
    )


def _setup(*, linked: bool = True) -> tuple[Stage, PatientLogin]:
    stage = build_stage()
    patient = make_patient_login(stage.clinic, stage.admin, name="Ana Souza")
    if linked:
        _link(stage, patient.profile)
    return stage, patient


def _panel(profile: PatientProfile) -> str:
    return reverse("mobile_api:patient_app", args=[profile.pk])


def _revoke_url(profile: PatientProfile, session_id: Any) -> str:
    return reverse("mobile_api:device_revoke", args=[profile.pk, session_id])


def _revoke_all_url(profile: PatientProfile) -> str:
    return reverse("mobile_api:devices_revoke_all", args=[profile.pk])


def _invite_url(profile: PatientProfile) -> str:
    return reverse("mobile_api:invitation_send", args=[profile.pk])


def _issue_invitation(stage: Stage, profile: PatientProfile) -> str:
    issued = people_services.issue_patient_invitation(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        patient_profile_id=profile.pk,
        expires_at=people_services.invitation_expiration_after(days=7),
        request_id=uuid4(),
    )
    return issued.raw_token


def _text(response: Any) -> str:
    return str(response.content.decode())


def _is_no_store(response: Any) -> bool:
    header = response.get("Cache-Control", "")
    return "no-store" in header and "private" in header


# ── Contrato de nomes e rotas ───────────────────────────────────────────────


def test_url_names_follow_the_integration_contract() -> None:
    profile_id = uuid4()
    assert reverse("mobile_api:patient_app", kwargs={"patient_id": profile_id}) == (
        f"/app-paciente/{profile_id}/"
    )


def test_anonymous_users_are_sent_to_login() -> None:
    _stage, patient = _setup()
    session_id = uuid4()
    client = Client()
    for url in (
        _panel(patient.profile),
        _invite_url(patient.profile),
        _revoke_all_url(patient.profile),
        _revoke_url(patient.profile, session_id),
    ):
        response = client.get(url)
        assert (
            response.status_code == 302 and "/accounts/login/" in response["Location"]
        )
        assert client.post(url).status_code == 302


# ── Autorização ─────────────────────────────────────────────────────────────


def test_clinic_admin_and_linked_therapist_open_the_panel() -> None:
    stage, patient = _setup()
    for user in (stage.admin, stage.therapist):
        response = _client(stage.clinic, user).get(_panel(patient.profile))
        assert response.status_code == 200, user.pk
        assert 'class="ae-navbar"' in _text(response)


def _error_message(response: Any) -> str:
    """Título e mensagem da página 403 (o resto muda a cada requisição)."""
    html = _text(response)
    title = re.search(r'<h1 id="error-title">(.*?)</h1>', html, re.S)
    message = re.search(r'<p class="aurora-auth-subtitle">(.*?)</p>', html, re.S)
    assert title is not None and message is not None
    return f"{title.group(1)}|{message.group(1)}"


def test_panel_is_denied_to_everyone_else_with_the_same_answer() -> None:
    stage, patient = _setup(linked=False)
    # terapeuta sem vínculo, equipe administrativa, o paciente (web) e outra clínica
    denied = {
        "therapist without link": _client(stage.clinic, stage.therapist),
        "administrative staff": _client(stage.clinic, stage.staff),
        "patient": _client(stage.clinic, patient.user),
        "other clinic admin": _client(stage.other_clinic, stage.other_admin),
    }
    for who, client in denied.items():
        response = client.get(_panel(patient.profile))
        assert response.status_code == 403, who
        assert "Ana Souza" not in _text(response), who
    # o mesmo vale para um paciente que nem existe: ninguém descobre quem existe
    unlinked = denied["therapist without link"].get(_panel(patient.profile))
    missing = denied["therapist without link"].get(
        reverse("mobile_api:patient_app", args=[uuid4()])
    )
    assert missing.status_code == 403
    assert _error_message(missing) == _error_message(unlinked)


def test_therapist_whose_link_ended_loses_access() -> None:
    stage, patient = _setup(linked=False)
    _link(stage, patient.profile, expired=True)
    client = _client(stage.clinic, stage.therapist)
    assert client.get(_panel(patient.profile)).status_code == 403
    assert client.post(_revoke_all_url(patient.profile)).status_code == 403


def test_a_therapist_only_sees_the_patient_they_are_linked_to() -> None:
    stage, patient = _setup()
    other = make_patient_login(stage.clinic, stage.admin, name="Outra Pessoa")
    client = _client(stage.clinic, stage.therapist)
    assert client.get(_panel(patient.profile)).status_code == 200
    assert client.get(_panel(other.profile)).status_code == 403


def test_a_patient_of_another_clinic_is_not_reachable_by_url() -> None:
    stage, _patient = _setup()
    foreign = make_patient_login(stage.other_clinic, stage.other_admin, name="Lia")
    response = _client(stage.clinic, stage.admin).get(_panel(foreign.profile))
    assert response.status_code == 403
    assert (
        _client(stage.clinic, stage.admin).get(_invite_url(foreign.profile)).status_code
        == 403
    )


def test_patient_web_sessions_cannot_use_any_staff_screen() -> None:
    stage, patient = _setup()
    tokens = _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    client = _client(stage.clinic, patient.user)
    urls = (
        _panel(patient.profile),
        _invite_url(patient.profile),
        _revoke_all_url(patient.profile),
        _revoke_url(patient.profile, session.pk),
    )
    for url in urls:
        assert client.get(url).status_code == 403
        assert client.post(url, {"confirm": "on"}).status_code == 403
    assert _me_status(tokens) == 200


# ── Conteúdo do painel ──────────────────────────────────────────────────────


def test_panel_for_a_patient_who_was_never_invited() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    response = _client(stage.clinic, stage.admin).get(_panel(profile))
    html = _text(response)
    assert response.status_code == 200
    assert "Ainda não ativada" in html and "Nenhum convite enviado" in html
    assert "Nenhum aparelho conectado no momento." in html
    assert "Sem acesso ao aplicativo registrado." in html
    assert "Nenhuma alta registrada para este paciente." in html
    assert _invite_url(profile) in html and "Enviar convite" in html
    assert _revoke_all_url(profile) not in html


def test_invitation_states_are_shown_without_the_activation_code() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    code = _issue_invitation(stage, profile)
    client = _client(stage.clinic, stage.admin)

    pending = _text(client.get(_panel(profile)))
    assert "Pendente" in pending and "Enviado e ainda não usado" in pending
    assert "Reenviar convite" in pending
    assert code not in pending

    ClinicInvitation.infrastructure_objects.update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    expired = _text(client.get(_panel(profile)))
    assert "Expirado" in expired and "O convite venceu em" in expired
    assert code not in expired

    ClinicInvitation.infrastructure_objects.update(
        expires_at=timezone.now() + timedelta(days=1), revoked_at=timezone.now()
    )
    revoked = _text(client.get(_panel(profile)))
    assert "O último convite foi cancelado" in revoked and code not in revoked


def test_accepted_invitation_shows_an_active_account() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    code = _issue_invitation(stage, profile)
    activated = _post_json(
        ACTIVATE,
        {
            "code": code,
            "password": PASSWORD,
            "first_name": "Caio",
            "last_name": "Lima",
            "device_label": "Pixel",
            "platform": "android",
        },
    )
    assert activated.status_code == 200, activated.content
    html = _text(_client(stage.clinic, stage.admin).get(_panel(profile)))
    assert "Conta ativa" in html and "Aceito" in html
    assert "O paciente usou o convite em" in html
    assert code not in html
    # com a conta ativa não se oferece mais convite
    assert _invite_url(profile) not in html
    assert "Pixel" in html and "Android" in html


def test_devices_show_label_platform_version_and_dates_but_never_credentials() -> None:
    stage, patient = _setup()
    first = _app_login(patient, "iPhone da Ana")
    second = _app_login(patient, "Tablet da casa")
    client = _client(stage.clinic, stage.admin)
    response = client.get(_panel(patient.profile))
    html = _text(response)
    assert "iPhone da Ana" in html and "Tablet da casa" in html
    assert "2.4.1" in html and "iOS" in html
    assert _revoke_all_url(patient.profile) in html
    # nenhum segredo: nem os tokens, nem seus resumos, nem os prefixos
    secrets = [first[k] for k in ("access_token", "refresh_token")]
    secrets += [second[k] for k in ("access_token", "refresh_token")]
    for session in MobileSession.infrastructure_objects.all():
        secrets += [
            session.access_digest,
            session.refresh_digest,
            session.network_hint,
        ]
    for secret in secrets:
        assert secret not in html
    assert "aem_" not in html and "aer_" not in html
    assert _is_no_store(response)


def test_devices_of_other_patients_never_appear() -> None:
    stage, patient = _setup()
    other = make_patient_login(stage.clinic, stage.admin, name="Outra Pessoa")
    _app_login(patient, "iPhone da Ana")
    _app_login(other, "Aparelho da Outra")
    html = _text(_client(stage.clinic, stage.admin).get(_panel(patient.profile)))
    assert "iPhone da Ana" in html and "Aparelho da Outra" not in html


def test_recent_activity_and_discharge_date_are_informative_only() -> None:
    stage, patient = _setup()
    discharge_day = timezone.localdate() - timedelta(days=9)
    concierge_services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.profile.pk,
        discharge_date=discharge_day,
        request_id=uuid4(),
    )
    _app_login(patient)
    html = _text(_client(stage.clinic, stage.admin).get(_panel(patient.profile)))
    today = date_format(timezone.localdate(), "SHORT_DATE_FORMAT")
    assert f"Último acesso ao aplicativo em {today}." in html
    assert date_format(discharge_day, "SHORT_DATE_FORMAT") in html
    assert "Alta registrada em" in html


def test_last_access_survives_revocation_of_the_device() -> None:
    stage, patient = _setup()
    _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    services.revoke_patient_devices(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        patient_profile_id=patient.profile.pk,
        session_id=session.pk,
        request_id=uuid4(),
    )
    html = _text(_client(stage.clinic, stage.admin).get(_panel(patient.profile)))
    assert "Último acesso ao aplicativo em" in html
    assert "Nenhum aparelho conectado no momento." in html


def test_panel_exposes_the_extension_block_for_the_integrator() -> None:
    stage, patient = _setup()
    response = _client(stage.clinic, stage.admin).get(_panel(patient.profile))
    child = engines["django"].from_string(
        '{% extends "mobile_api/patient_app.html" %}'
        "{% block app_panels %}<p>PAINEL-DE-ADESAO</p>{% endblock %}"
    )
    rendered = child.render(response.context_data, response.wsgi_request)
    assert "PAINEL-DE-ADESAO" in rendered
    assert "Aparelhos conectados" in rendered


# ── Cabeçalhos ──────────────────────────────────────────────────────────────


def test_every_page_with_patient_data_is_private_and_not_cached() -> None:
    stage, patient = _setup()
    _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    client = _client(stage.clinic, stage.admin)
    for url in (
        _panel(patient.profile),
        _revoke_url(patient.profile, session.pk),
        _revoke_all_url(patient.profile),
    ):
        response = client.get(url)
        assert response.status_code == 200, url
        assert _is_no_store(response), url
    waiting = make_patient(stage.clinic, stage.admin, name="Sem Conta")
    assert _is_no_store(client.get(_invite_url(waiting)))
    issued = client.post(_invite_url(waiting), {"confirm": "on"})
    assert issued.status_code == 200 and _is_no_store(issued)


# ── Revogar um aparelho ─────────────────────────────────────────────────────


def test_revoking_a_device_needs_the_confirmation() -> None:
    stage, patient = _setup()
    tokens = _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    client = _client(stage.clinic, stage.admin)
    page = client.get(_revoke_url(patient.profile, session.pk))
    assert page.status_code == 200 and "iPhone da Ana" in _text(page)
    unconfirmed = client.post(_revoke_url(patient.profile, session.pk), {})
    assert unconfirmed.status_code == 200
    assert "Marque a confirmação para continuar." in _text(unconfirmed)
    session.refresh_from_db()
    assert session.revoked_at is None and _me_status(tokens) == 200


def test_revoking_a_device_drops_the_token_and_audits_the_staff_actor() -> None:
    stage, patient = _setup()
    lost = _app_login(patient, "Pixel extraviado")
    kept = _app_login(patient, "Tablet seguro")
    lost_session = MobileSession.infrastructure_objects.get(
        device_label="Pixel extraviado"
    )
    assert _me_status(lost) == 200 and _me_status(kept) == 200

    client = _client(stage.clinic, stage.therapist)
    response = client.post(
        _revoke_url(patient.profile, lost_session.pk), {"confirm": "on"}
    )
    assert response.status_code == 302 and response["Location"] == _panel(
        patient.profile
    )

    # o token do aparelho revogado cai na hora, e a renovação também
    assert _me_status(lost) == 401
    assert _refresh_status(lost) == 401
    # o outro aparelho segue valendo
    assert _me_status(kept) == 200
    lost_session.refresh_from_db()
    assert lost_session.revoked_at is not None
    assert lost_session.revoked_reason == RevokeReason.STAFF_REVOKED

    event = AuditEvent.objects.for_clinic(stage.clinic.pk).get(
        resource_type="mobile_session",
        resource_id=str(lost_session.pk),
        action="update",
    )
    assert event.actor_id == stage.therapist.pk and event.outcome == "success"
    serialized = str(event.__dict__)
    assert lost["access_token"] not in serialized
    assert lost["refresh_token"] not in serialized
    # a próxima tela mostra o resultado e o aparelho some da lista
    follow = client.get(_panel(patient.profile))
    assert "Aparelho desconectado" in _text(follow)
    assert "Pixel extraviado" not in _text(follow) and "Tablet seguro" in _text(follow)


def test_a_device_that_is_already_gone_is_a_404_for_the_authorized_staff() -> None:
    stage, patient = _setup()
    _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    client = _client(stage.clinic, stage.admin)
    url = _revoke_url(patient.profile, session.pk)
    assert client.post(url, {"confirm": "on"}).status_code == 302
    assert client.get(url).status_code == 404
    assert client.post(url, {"confirm": "on"}).status_code == 404
    assert client.get(_revoke_url(patient.profile, uuid4())).status_code == 404


def test_a_session_of_another_patient_cannot_be_revoked_through_this_one() -> None:
    stage, patient = _setup()
    other = make_patient_login(stage.clinic, stage.admin, name="Outra Pessoa")
    other_tokens = _app_login(other, "Aparelho da Outra")
    other_session = MobileSession.infrastructure_objects.get()
    client = _client(stage.clinic, stage.admin)
    url = _revoke_url(patient.profile, other_session.pk)
    assert client.get(url).status_code == 404
    assert client.post(url, {"confirm": "on"}).status_code == 404
    assert _me_status(other_tokens) == 200


def test_revocation_is_denied_to_unlinked_staff_other_clinics_and_the_patient() -> None:
    stage, patient = _setup(linked=False)
    tokens = _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    attempts = (
        _client(stage.clinic, stage.therapist),
        _client(stage.clinic, stage.staff),
        _client(stage.clinic, patient.user),
        _client(stage.other_clinic, stage.other_admin),
    )
    for client in attempts:
        single = client.post(
            _revoke_url(patient.profile, session.pk), {"confirm": "on"}
        )
        everything = client.post(_revoke_all_url(patient.profile), {"confirm": "on"})
        assert single.status_code == 403 and everything.status_code == 403
    session.refresh_from_db()
    assert session.revoked_at is None and _me_status(tokens) == 200
    assert (
        not AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(resource_type="mobile_session", action="update")
        .exists()
    )


# ── Revogar todos ───────────────────────────────────────────────────────────


def test_revoking_every_device_ends_all_tokens_of_that_patient_only() -> None:
    stage, patient = _setup()
    other = make_patient_login(stage.clinic, stage.admin, name="Outra Pessoa")
    mine = [_app_login(patient, f"Aparelho {n}") for n in (1, 2, 3)]
    theirs = _app_login(other, "Aparelho da Outra")
    client = _client(stage.clinic, stage.admin)

    page = client.get(_revoke_all_url(patient.profile))
    assert page.status_code == 200
    for n in (1, 2, 3):
        assert f"Aparelho {n}" in _text(page)
    assert "Aparelho da Outra" not in _text(page)

    unconfirmed = client.post(_revoke_all_url(patient.profile), {})
    assert unconfirmed.status_code == 200 and all(_me_status(t) == 200 for t in mine)

    done = client.post(_revoke_all_url(patient.profile), {"confirm": "on"})
    assert done.status_code == 302
    assert all(_me_status(t) == 401 for t in mine)
    assert all(_refresh_status(t) == 401 for t in mine)
    assert _me_status(theirs) == 200
    events = AuditEvent.objects.for_clinic(stage.clinic.pk).filter(
        resource_type="mobile_session", action="update", actor_id=stage.admin.pk
    )
    assert events.count() == 3
    assert (
        MobileSession.infrastructure_objects.filter(
            patient_profile=patient.profile, revoked_reason=RevokeReason.STAFF_REVOKED
        ).count()
        == 3
    )


def test_revoking_all_without_any_device_goes_back_to_the_panel() -> None:
    stage, patient = _setup()
    client = _client(stage.clinic, stage.admin)
    response = client.get(_revoke_all_url(patient.profile))
    assert response.status_code == 302 and response["Location"] == _panel(
        patient.profile
    )
    assert "Nenhum aparelho estava conectado." in _text(
        client.get(response["Location"])
    )


# ── Convite ─────────────────────────────────────────────────────────────────


def test_resending_the_invitation_issues_a_new_code_once_and_voids_the_old_one() -> (
    None
):
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    old_code = _issue_invitation(stage, profile)
    client = _client(stage.clinic, stage.admin)

    confirm_page = client.get(_invite_url(profile))
    assert confirm_page.status_code == 200
    assert "O código anterior deixa de valer." in _text(confirm_page)
    assert old_code not in _text(confirm_page)

    unconfirmed = client.post(_invite_url(profile), {})
    assert unconfirmed.status_code == 200 and not mail.outbox
    assert ClinicInvitation.infrastructure_objects.count() == 1

    sent = client.post(_invite_url(profile), {"confirm": "on"})
    html = _text(sent)
    assert sent.status_code == 200 and _is_no_store(sent)
    assert "Código de ativação" in html
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [profile.email]
    email_body = mail.outbox[0].body
    new_code = html.split('id="invitation-code" class="user-select-all">')[1].split(
        "<"
    )[0]
    assert new_code in email_body and new_code != old_code
    assert old_code not in html

    # depois disso o código some: nem o painel nem uma nova abertura o mostram
    panel = _text(client.get(_panel(profile)))
    assert new_code not in panel and old_code not in panel
    assert new_code not in _text(client.get(_invite_url(profile)))

    # só o código novo ativa a conta
    def activate(code: str) -> Any:
        return _post_json(
            ACTIVATE,
            {
                "code": code,
                "password": PASSWORD,
                "first_name": "Caio",
                "last_name": "Lima",
                "device_label": "Pixel",
                "platform": "android",
            },
        )

    assert activate(old_code).status_code == 422
    assert activate(new_code).status_code == 200
    # o convite foi trocado, não duplicado: o histórico guarda o antigo como cancelado
    invitations = ClinicInvitation.infrastructure_objects.order_by("created_at")
    assert [i.revoked_at is not None for i in invitations] == [True, False]
    assert invitations[1].used_at is not None


def test_resending_is_audited_for_the_admin() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    _issue_invitation(stage, profile)
    before = AuditEvent.objects.for_clinic(stage.clinic.pk).count()
    client = _client(stage.clinic, stage.admin)
    assert client.post(_invite_url(profile), {"confirm": "on"}).status_code == 200
    events = AuditEvent.objects.for_clinic(stage.clinic.pk).filter(
        resource_type="clinic_invitation", actor_id=stage.admin.pk
    )
    assert AuditEvent.objects.for_clinic(stage.clinic.pk).count() >= before + 2
    assert {event.action for event in events} >= {"create", "update"}


def test_first_invitation_can_be_sent_from_the_panel() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    client = _client(stage.clinic, stage.admin)
    page = client.get(_invite_url(profile))
    assert "Enviar convite" in _text(page)
    response = client.post(_invite_url(profile), {"confirm": "on"})
    assert response.status_code == 200 and len(mail.outbox) == 1
    assert ClinicInvitation.infrastructure_objects.count() == 1


def test_the_invitation_belongs_to_the_clinic_admin_only() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Caio Lima")
    _link(stage, profile)
    therapist = _client(stage.clinic, stage.therapist)
    # o terapeuta vinculado vê a situação, mas não envia convite
    panel = _text(therapist.get(_panel(profile)))
    assert "Somente o administrador da clínica envia convites." in panel
    assert _invite_url(profile) not in panel
    assert therapist.get(_invite_url(profile)).status_code == 403
    assert therapist.post(_invite_url(profile), {"confirm": "on"}).status_code == 403
    staff = _client(stage.clinic, stage.staff)
    assert staff.post(_invite_url(profile), {"confirm": "on"}).status_code == 403
    other = _client(stage.other_clinic, stage.other_admin)
    assert other.post(_invite_url(profile), {"confirm": "on"}).status_code == 403
    assert not mail.outbox and not ClinicInvitation.infrastructure_objects.exists()


def test_no_invitation_is_sent_to_a_patient_who_already_has_the_account() -> None:
    stage, patient = _setup()
    client = _client(stage.clinic, stage.admin)
    response = client.post(_invite_url(patient.profile), {"confirm": "on"})
    assert response.status_code == 302
    assert not mail.outbox and not ClinicInvitation.infrastructure_objects.exists()
    assert "já ativou a conta" in _text(client.get(response["Location"]))


# ── Serviços e política ─────────────────────────────────────────────────────


def test_service_refuses_actors_the_policy_denies() -> None:
    stage, patient = _setup(linked=False)
    _app_login(patient)
    for actor in (stage.therapist, stage.staff, stage.other_admin, patient.user):
        with pytest.raises(PermissionDenied):
            services.revoke_patient_devices(
                clinic_id=stage.clinic.pk,
                actor=actor,
                patient_profile_id=patient.profile.pk,
                session_id=None,
                request_id=uuid4(),
            )
    assert (
        MobileSession.infrastructure_objects.filter(revoked_at__isnull=True).count()
        == 1
    )
    with pytest.raises(PermissionDenied):
        services.send_patient_invitation(
            clinic_id=stage.clinic.pk,
            actor=stage.therapist,
            patient_profile_id=patient.profile.pk,
            request_id=uuid4(),
        )


def test_service_refuses_a_profile_from_another_clinic_even_to_an_admin() -> None:
    stage, _patient = _setup()
    foreign = make_patient_login(stage.other_clinic, stage.other_admin, name="Lia")
    _app_login(foreign)
    with pytest.raises(PermissionDenied):
        services.revoke_patient_devices(
            clinic_id=stage.clinic.pk,
            actor=stage.admin,
            patient_profile_id=foreign.profile.pk,
            session_id=None,
            request_id=uuid4(),
        )
    assert (
        MobileSession.infrastructure_objects.filter(revoked_at__isnull=True).count()
        == 1
    )


def test_service_refuses_an_inactive_actor() -> None:
    stage, patient = _setup()
    _app_login(patient)
    stage.admin.is_active = False
    stage.admin.save()
    with pytest.raises(PermissionDenied):
        services.revoke_patient_devices(
            clinic_id=stage.clinic.pk,
            actor=stage.admin,
            patient_profile_id=patient.profile.pk,
            session_id=None,
            request_id=uuid4(),
        )


def test_policy_decisions() -> None:
    stage, patient = _setup()
    today = timezone.localdate()

    def manages(user: User) -> bool:
        return policies.can_manage_patient_app(
            clinic_id=stage.clinic.pk,
            actor_id=user.pk,
            patient_profile_id=patient.profile.pk,
            on_date=today,
        )

    assert manages(stage.admin)
    assert manages(stage.therapist)
    assert not manages(stage.staff)
    assert not manages(patient.user)
    assert not manages(stage.other_admin)
    assert policies.can_issue_patient_invitation(
        clinic_id=stage.clinic.pk, actor_id=stage.admin.pk, on_date=today
    )
    for user in (stage.therapist, stage.staff, patient.user):
        assert not policies.can_issue_patient_invitation(
            clinic_id=stage.clinic.pk, actor_id=user.pk, on_date=today
        )


def test_selectors_expose_no_credentials() -> None:
    stage, patient = _setup()
    _app_login(patient)
    access = selectors.patient_app_access(
        clinic_id=stage.clinic.pk,
        patient_profile_id=patient.profile.pk,
        patient_user_id=patient.user.pk,
    )
    assert access.account_state == selectors.ACCOUNT_ACTIVE
    (row,) = access.devices
    assert set(vars_of(row)) == {
        "session_id",
        "device_label",
        "platform",
        "app_version",
        "connected_at",
        "last_used_at",
    }
    assert (
        selectors.connected_device(
            clinic_id=stage.other_clinic.pk,
            patient_profile_id=patient.profile.pk,
            session_id=row.session_id,
        )
        is None
    )


def vars_of(row: Any) -> list[str]:
    return list(type(row).__dataclass_fields__)


# ── Idiomas (en/es) ─────────────────────────────────────────────────────────


class _TextNodes(HTMLParser):
    """Coleta os nós de texto visíveis (sem script/style), com espaços normalizados."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes: set[str] = set()
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._skip:
            self.nodes.add(text)


def _text_nodes(html: str) -> set[str]:
    parser = _TextNodes()
    parser.feed(html)
    return parser.nodes


def _catalog(language: str) -> dict[str, str]:
    path = settings.BASE_DIR / "locale" / language / "LC_MESSAGES" / "django.mo"
    with path.open("rb") as source:
        catalog = vars(gettext_module.GNUTranslations(source))["_catalog"]
    return {k: v for k, v in catalog.items() if isinstance(k, str) and k}


@pytest.mark.parametrize(
    ("language", "heading"),
    [("en", "Connected devices"), ("es", "Dispositivos conectados")],
)
def test_every_screen_renders_in_english_and_spanish(
    language: str, heading: str
) -> None:
    stage, patient = _setup()
    _app_login(patient)
    session = MobileSession.infrastructure_objects.get()
    waiting = make_patient(stage.clinic, stage.admin, name="Sem Conta")
    _issue_invitation(stage, waiting)
    never = make_patient(stage.clinic, stage.admin, name="Nunca Convidada")
    concierge_services.register_discharge(
        clinic_id=stage.clinic.pk,
        actor=stage.staff,
        patient_profile_id=patient.profile.pk,
        discharge_date=timezone.localdate() - timedelta(days=4),
        request_id=uuid4(),
    )
    client = _client(stage.clinic, stage.admin)
    portuguese = _catalog("pt_BR")
    target = _catalog(language)
    untranslated = {
        msgid for msgid in portuguese if target.get(msgid) not in {None, msgid}
    }
    # nomes e rótulos digitados pelo usuário/aparelho não são frases da interface
    user_data = {"Ana Souza", "iPhone da Ana", "Sem Conta", "Nunca Convidada"}
    urls = [
        _panel(patient.profile),
        _panel(waiting),
        _panel(never),
        _revoke_url(patient.profile, session.pk),
        _revoke_all_url(patient.profile),
        _invite_url(waiting),
        _invite_url(never),
    ]
    for url in urls:
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200, url
        leaked = (_text_nodes(_text(response)) & untranslated) - user_data
        assert not leaked, f"{url}: sem tradução em {language}: {sorted(leaked)}"
    issued = client.post(
        _invite_url(never), {"confirm": "on"}, HTTP_ACCEPT_LANGUAGE=language
    )
    leaked = (_text_nodes(_text(issued)) & untranslated) - user_data
    assert not leaked, f"convite emitido: sem tradução em {language}: {sorted(leaked)}"
    panel = _text(client.get(urls[0], HTTP_ACCEPT_LANGUAGE=language))
    assert heading in panel
    unconfirmed = client.post(urls[3], {}, HTTP_ACCEPT_LANGUAGE=language)
    leaked = (_text_nodes(_text(unconfirmed)) & untranslated) - user_data
    assert not leaked, sorted(leaked)
