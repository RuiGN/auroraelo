"""Ativação, recuperação e redefinição de senha do paciente, só pelo aplicativo."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.services import issue_invitation
from clinics.models import ClinicMembership
from mobile_api.models import MobileSession
from people import services as people_services
from people.models import PatientProfile
from tests.aftercare_support import Stage, build_stage, make_patient
from tests.factories import ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

BASE = "/api/v1/mobile/auth"
PASSWORD = "Senha-Segura-Longa-123"  # nosec - credencial sintética de teste


@pytest.fixture(autouse=True)
def _fresh_state() -> None:
    cache.clear()
    mail.outbox.clear()


def _post(url: str, body: dict[str, Any]) -> Any:
    return Client().post(url, body, content_type="application/json")


def _invite(stage: Stage, name: str = "Ana Souza") -> tuple[PatientProfile, str]:
    profile = make_patient(stage.clinic, stage.admin, name=name)
    issued = people_services.issue_patient_invitation(
        clinic_id=stage.clinic.pk,
        actor=stage.admin,
        patient_profile_id=profile.pk,
        expires_at=people_services.invitation_expiration_after(days=7),
        request_id=uuid4(),
    )
    return profile, issued.raw_token


def _activate(code: str, **extra: Any) -> Any:
    body = {
        "code": code,
        "password": PASSWORD,
        "first_name": "Ana",
        "last_name": "Souza",
        "device_label": "iPhone",
        "platform": "ios",
        **extra,
    }
    return _post(f"{BASE}/activate/", body)


# ── Ativação ────────────────────────────────────────────────────────────────


def test_a_new_patient_activates_the_account_and_gets_a_session() -> None:
    stage = build_stage()
    profile, code = _invite(stage)
    response = _activate(code)
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["clinic"]["id"] == str(stage.clinic.pk)
    assert body["patient"]["id"] == str(profile.pk)
    profile.refresh_from_db()
    assert profile.user is not None and profile.user.email == profile.email
    assert ClinicMembership.infrastructure_objects.filter(
        user=profile.user, clinic=stage.clinic, role="patient"
    ).exists()
    me = Client().get(
        "/api/v1/mobile/me/",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert MobileSession.infrastructure_objects.count() == 1


def test_the_code_works_once_and_a_bad_one_is_refused_the_same_way() -> None:
    stage = build_stage()
    _profile, code = _invite(stage)
    assert _activate(code).status_code == 200
    reused = _activate(code)
    unknown = _activate("codigo-que-nao-existe-" + "x" * 30)
    for response in (reused, unknown):
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_code"
    assert response.json()["errors"] == []


def test_a_weak_password_is_rejected_and_keeps_the_invitation_usable() -> None:
    stage = build_stage()
    _profile, code = _invite(stage)
    weak = _activate(code, password="12345678")
    assert weak.status_code == 422 and weak.json()["code"] == "weak_password"
    assert weak.json()["errors"]
    assert User.objects.filter(email__startswith="paciente").count() == 0
    assert _activate(code).status_code == 200


def test_expired_and_staff_invitations_cannot_activate_a_patient_account() -> None:
    stage = build_stage()
    _profile, code = _invite(stage)
    from accounts.models import ClinicInvitation

    ClinicInvitation.infrastructure_objects.update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    assert _activate(code).json()["code"] == "invalid_code"
    staff = issue_invitation(
        clinic_id=stage.clinic.pk,
        issuer=stage.admin,
        recipient_email="nova.terapeuta@example.test",
        initial_role="therapist",
        expires_at=timezone.now() + timedelta(days=3),
    )
    refused = _activate(staff.raw_token)
    assert refused.status_code == 422 and refused.json()["code"] == "invalid_code"
    assert not User.objects.filter(email="nova.terapeuta@example.test").exists()


def test_an_existing_account_proves_itself_with_its_current_password() -> None:
    stage = build_stage()
    profile, code = _invite(stage, name="Bia Lima")
    existing = UserFactory.create(email=profile.email)
    existing.set_password(PASSWORD)
    existing.save()
    ClinicMembershipFactory.create(
        clinic=stage.other_clinic,
        user=existing,
        role=ClinicMembership.Role.PATIENT,
    )
    wrong = _activate(code, password="senha-errada-qualquer")
    assert wrong.status_code == 401 and wrong.json()["code"] == "invalid_credentials"
    ok = _activate(code)
    assert ok.status_code == 200, ok.content
    assert ok.json()["clinic"]["id"] == str(stage.clinic.pk)
    profile.refresh_from_db()
    assert profile.user_id == existing.pk


# ── Web: o paciente é levado ao aplicativo ──────────────────────────────────


def test_the_web_invitation_page_sends_patients_to_the_app_and_keeps_staff_flow() -> (
    None
):
    stage = build_stage()
    _profile, code = _invite(stage)
    page = Client().get(reverse("invitation_accept", kwargs={"raw_token": code}))
    html = page.content.decode()
    assert page.status_code == 200
    assert "aplicativo" in html and 'name="password"' not in html
    staff = issue_invitation(
        clinic_id=stage.clinic.pk,
        issuer=stage.admin,
        recipient_email="outra.pessoa@example.test",
        initial_role="therapist",
        expires_at=timezone.now() + timedelta(days=3),
    )
    staff_page = Client().get(
        reverse("invitation_accept", kwargs={"raw_token": staff.raw_token})
    )
    assert 'name="password"' in staff_page.content.decode()


def test_staff_invites_a_patient_and_the_code_reaches_the_patient_by_email() -> None:
    stage = build_stage()
    profile = make_patient(stage.clinic, stage.admin, name="Carla Dias")
    client = Client()
    client.force_login(stage.admin)
    session = client.session
    session["active_clinic_id"] = str(stage.clinic.pk)
    session.save()
    response = client.post(reverse("patient_invite", args=[profile.pk]))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    code = re.search(r'id="invitation-code"[^>]*>([^<]+)<', response.content.decode())
    assert code is not None
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [profile.email]
    assert code.group(1) in message.body
    assert "auroraelo-posalta://activate?code=" in message.body
    assert _activate(code.group(1)).status_code == 200
    # só quem pode convidar vê o código
    therapist = Client()
    therapist.force_login(stage.therapist)
    session = therapist.session
    session["active_clinic_id"] = str(stage.clinic.pk)
    session.save()
    assert (
        therapist.post(reverse("patient_invite", args=[profile.pk])).status_code == 403
    )


# ── Recuperação e redefinição ───────────────────────────────────────────────


def _active_patient(stage: Stage, name: str = "Ana Souza") -> tuple[str, str]:
    profile, code = _invite(stage, name=name)
    assert _activate(code).status_code == 200
    return profile.email, PASSWORD


def _recovery_code() -> str:
    body = mail.outbox[-1].body
    match = re.search(r"copie o código abaixo no aplicativo: (\S+)", body)
    assert match is not None, body
    return match.group(1)


def test_recovery_by_the_app_emails_the_code_and_link_without_enumerating() -> None:
    stage = build_stage()
    email, _ = _active_patient(stage)
    mail.outbox.clear()
    known = _post(f"{BASE}/password-recovery/", {"email": email})
    unknown = _post(f"{BASE}/password-recovery/", {"email": "ninguem@example.test"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1
    assert "auroraelo-posalta://reset?code=" in mail.outbox[0].body
    assert "/accounts/password-reset/" not in mail.outbox[0].body


def test_recovery_by_the_app_never_emails_team_accounts() -> None:
    stage = build_stage()
    stage.therapist.email = "terapeuta-app@example.test"
    stage.therapist.save()
    response = _post(f"{BASE}/password-recovery/", {"email": stage.therapist.email})
    assert response.status_code == 202
    assert mail.outbox == []


@override_settings(PASSWORD_RECOVERY_RATE_LIMIT_ATTEMPTS=2)
def test_recovery_is_rate_limited() -> None:
    stage = build_stage()
    email, _ = _active_patient(stage)
    codes = [
        _post(f"{BASE}/password-recovery/", {"email": email}).status_code
        for _ in range(4)
    ]
    assert codes[:2] == [202, 202] and 429 in codes


def test_reset_with_the_emailed_code_changes_the_password_and_ends_sessions() -> None:
    stage = build_stage()
    email, old_password = _active_patient(stage)
    login = {"email": email, "password": old_password}
    session_tokens = _post(f"{BASE}/login/", login).json()
    mail.outbox.clear()
    _post(f"{BASE}/password-recovery/", {"email": email})
    code = _recovery_code()
    new_password = "Outra-Senha-Forte-456"  # nosec - sintética
    done = _post(
        f"{BASE}/password-reset/", {"code": code, "new_password": new_password}
    )
    assert done.status_code == 204
    # as sessões abertas caem e a senha nova entra
    me = Client().get(
        "/api/v1/mobile/me/",
        headers={"Authorization": f"Bearer {session_tokens['access_token']}"},
    )
    assert me.status_code == 401
    assert _post(f"{BASE}/login/", login).status_code == 401
    assert (
        _post(f"{BASE}/login/", {"email": email, "password": new_password}).status_code
        == 200
    )
    # o código vale uma vez
    again = _post(
        f"{BASE}/password-reset/", {"code": code, "new_password": "Mais-Uma-789-xyz"}
    )
    assert again.status_code == 400 and again.json()["code"] == "invalid_code"


def test_reset_refuses_weak_passwords_and_garbage_codes() -> None:
    stage = build_stage()
    email, _ = _active_patient(stage)
    mail.outbox.clear()
    _post(f"{BASE}/password-recovery/", {"email": email})
    code = _recovery_code()
    weak = _post(f"{BASE}/password-reset/", {"code": code, "new_password": "123"})
    assert weak.status_code == 422 and weak.json()["code"] == "weak_password"
    for bad in ("", "sem-ponto", "a.b", "x" * 200):
        response = _post(
            f"{BASE}/password-reset/",
            {"code": bad, "new_password": "Qualquer-Senha-1234"},
        )
        assert response.status_code == 400 and response.json()["code"] == "invalid_code"
    # o código segue válido depois das tentativas ruins
    ok = _post(
        f"{BASE}/password-reset/", {"code": code, "new_password": "Senha-Nova-Forte-9"}
    )
    assert ok.status_code == 204


def test_web_recovery_gives_a_patient_the_app_code_and_the_team_the_web_link() -> None:
    stage = build_stage()
    email, _ = _active_patient(stage)
    mail.outbox.clear()
    Client().post(reverse("password_recovery"), {"email": email})
    assert len(mail.outbox) == 1
    assert "auroraelo-posalta://reset" in mail.outbox[0].body
    mail.outbox.clear()
    stage.therapist.email = "terapeuta-web@example.test"
    stage.therapist.save()
    Client().post(reverse("password_recovery"), {"email": stage.therapist.email})
    assert len(mail.outbox) == 1
    assert "/accounts/password-reset/" in mail.outbox[0].body


def test_the_web_reset_page_does_not_serve_patient_only_accounts() -> None:
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    stage = build_stage()
    email, _ = _active_patient(stage)
    user = User.objects.get(email=email)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    page = Client().get(reverse("password_reset", kwargs={"uid": uid, "token": token}))
    html = page.content.decode()
    assert page.status_code == 200
    assert "aplicativo" in html and "new_password" not in html
    posted = Client().post(
        reverse("password_reset", kwargs={"uid": uid, "token": token}),
        {
            "new_password": "Senha-Pelo-Web-123",
            "new_password_confirm": "Senha-Pelo-Web-123",
        },
    )
    assert posted.status_code == 200
    user.refresh_from_db()
    assert not user.check_password("Senha-Pelo-Web-123")
