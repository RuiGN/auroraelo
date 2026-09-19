"""Session and device acceptance tests for PRD 8.4.2."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountSession, User
from accounts.services import (
    SensitiveActionRateLimitedError,
    reauthenticate_sensitive_action,
    register_current_session,
    revoke_account_session,
    revoke_other_sessions,
    validate_current_session,
)
from audit.models import AuditEvent
from clinics.models import Clinic, ClinicMembership
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


def authenticated_admin(client: Client) -> tuple[User, Clinic]:
    clinic = ClinicFactory.create()
    user = UserFactory.create()
    user.set_password("senha-sintetica-segura")
    user.save(update_fields=("password", "credentials_changed_at"))
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=user,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return user, clinic


@override_settings(ACCOUNT_SESSION_ALLOW_UNKNOWN=False)
def test_login_registers_session_before_fail_closed_validation(client: Client) -> None:
    clinic = ClinicFactory.create()
    user = User.objects.create_user(
        email="login-rastreado@example.test",
        password="senha-sintetica-segura",
    )
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=user,
        role=ClinicMembership.Role.THERAPIST,
    )

    response = client.post(
        reverse("account_login"),
        {
            "email": "login-rastreado@example.test",
            "password": "senha-sintetica-segura",
        },
    )

    assert response.status_code == 302
    assert AccountSession.objects.filter(user=user, revoked_at__isnull=True).exists()
    assert client.get(reverse("workspace_vertical")).status_code == 200


@override_settings(
    ACCOUNT_SESSION_IDLE_SECONDS=900,
    ACCOUNT_SESSION_ABSOLUTE_SECONDS=7200,
)
def test_registered_session_has_minimized_device_data_and_enforced_expiry(
    client: Client,
) -> None:
    user, _clinic = authenticated_admin(client)
    request = client.get("/workspace/").wsgi_request
    request.META["HTTP_USER_AGENT"] = "Synthetic Browser/1.0"
    request.META["REMOTE_ADDR"] = "198.51.100.20"

    device = register_current_session(request=request, user=user)

    assert device.session_key_digest
    assert "198.51.100.20" not in device.network_hint
    assert device.client_label == "Synthetic Browser"
    assert device.absolute_expires_at > device.created_at
    device.last_seen_at = timezone.now() - timedelta(seconds=901)
    device.save(update_fields=("last_seen_at",))
    assert validate_current_session(request=request, user=user) is False


@override_settings(ACCOUNT_SESSION_ALLOW_UNKNOWN=True)
def test_unknown_session_is_rejected_when_fail_closed_is_enabled(
    client: Client,
) -> None:
    user, _clinic = authenticated_admin(client)
    request = client.get("/workspace/").wsgi_request
    AccountSession.objects.filter(user=user).delete()

    with override_settings(ACCOUNT_SESSION_ALLOW_UNKNOWN=False):
        assert validate_current_session(request=request, user=user) is False
    assert not AccountSession.objects.filter(user=user).exists()


def test_user_can_revoke_one_or_all_other_sessions(client: Client) -> None:
    user, clinic = authenticated_admin(client)
    current_request = client.get("/workspace/").wsgi_request
    current = register_current_session(request=current_request, user=user)
    other_session = Session.objects.create(
        session_key="other-session-key",
        session_data="e30:synthetic",
        expire_date=timezone.now() + timedelta(hours=1),
    )
    other = AccountSession.objects.create_for_session(
        user=user,
        session_key=other_session.session_key,
        client_label="Outro navegador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )

    revoke_account_session(actor=user, account_session_id=other.pk)
    other.refresh_from_db()
    assert other.revoked_at is not None
    assert not Session.objects.filter(session_key=other_session.session_key).exists()
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk,
        actor_id=user.pk,
        resource_type="session",
        resource_id=str(other.pk),
    ).exists()

    third_session = Session.objects.create(
        session_key="third-session-key",
        session_data="e30:synthetic",
        expire_date=timezone.now() + timedelta(hours=1),
    )
    AccountSession.objects.create_for_session(
        user=user,
        session_key=third_session.session_key,
        client_label="Terceiro navegador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )
    revoked = revoke_other_sessions(actor=user, current_session_id=current.pk)
    assert revoked == 1
    assert AccountSession.objects.get(pk=current.pk).revoked_at is None
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=clinic.pk,
        actor_id=user.pk,
        resource_type="session_set",
    ).exists()


def test_session_revocation_audit_uses_active_clinic(client: Client) -> None:
    user, first_clinic = authenticated_admin(client)
    active_clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(
        clinic=active_clinic,
        user=user,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    session = client.session
    session["active_clinic_id"] = str(active_clinic.pk)
    session.save()
    tracked = AccountSession.objects.create_for_session(
        user=user,
        session_key="tenant-audit-session",
        client_label="Outro navegador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )

    response = client.post(
        reverse("account_sessions"),
        {"action": "revoke", "session_id": str(tracked.pk)},
    )

    assert response.status_code == 302
    assert AuditEvent.infrastructure_objects.filter(
        clinic_id=active_clinic.pk,
        actor_id=user.pk,
        resource_type="session",
        resource_id=str(tracked.pk),
    ).exists()
    assert not AuditEvent.infrastructure_objects.filter(
        clinic_id=first_clinic.pk,
        resource_type="session",
        resource_id=str(tracked.pk),
    ).exists()


def test_user_cannot_revoke_another_identity_session(client: Client) -> None:
    user = UserFactory.create()
    other = UserFactory.create()
    session = AccountSession.objects.create_for_session(
        user=other,
        session_key="foreign-session-key",
        client_label="Outro navegador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )

    with pytest.raises(PermissionDenied):
        revoke_account_session(actor=user, account_session_id=session.pk)


def test_revoking_all_other_sessions_requires_current_password(client: Client) -> None:
    user, _clinic = authenticated_admin(client)
    other_django_session = Session.objects.create(
        session_key="reauth-other-session",
        session_data="e30:synthetic",
        expire_date=timezone.now() + timedelta(hours=1),
    )
    other = AccountSession.objects.create_for_session(
        user=user,
        session_key=other_django_session.session_key,
        client_label="Outro navegador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )

    denied = client.post(
        reverse("account_sessions"),
        {"action": "revoke_others", "password": "senha-incorreta"},
    )

    assert denied.status_code == 400
    other.refresh_from_db()
    assert other.revoked_at is None

    accepted = client.post(
        reverse("account_sessions"),
        {"action": "revoke_others", "password": "senha-sintetica-segura"},
    )

    assert accepted.status_code == 302
    other.refresh_from_db()
    assert other.revoked_at is not None


def test_django_admin_login_uses_account_entrypoint(client: Client) -> None:
    response = client.get("/admin/login/")

    assert response.status_code == 302
    assert response.headers["Location"] == (
        f"{reverse('account_login')}?next=%2Fadmin%2F"
    )


def test_global_staff_can_authenticate_through_account_entrypoint(
    client: Client,
) -> None:
    staff = User.objects.create_user(
        email="staff-global@example.test",
        password="senha-sintetica-segura",
        is_staff=True,
    )

    response = client.post(
        f"{reverse('account_login')}?next=/admin/",
        {
            "email": staff.email,
            "password": "senha-sintetica-segura",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/"
    assert AccountSession.objects.filter(user=staff, revoked_at__isnull=True).exists()
    assert client.get("/admin/").status_code == 200


@override_settings(
    SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS=2,
    SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS=300,
)
def test_sensitive_reauthentication_is_rate_limited_per_identity() -> None:
    actor = UserFactory.create()
    actor.set_password("senha-correta")
    actor.save(update_fields=("password", "credentials_changed_at"))

    assert reauthenticate_sensitive_action(actor=actor, password="errada") is False
    assert reauthenticate_sensitive_action(actor=actor, password="errada") is False
    with pytest.raises(SensitiveActionRateLimitedError):
        reauthenticate_sensitive_action(actor=actor, password="senha-correta")


@override_settings(
    SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS=1,
    SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS=300,
)
def test_session_reauthentication_rate_limit_returns_429(client: Client) -> None:
    authenticated_admin(client)
    assert client.get(reverse("account_sessions")).status_code == 200
    payload = {"action": "revoke_others", "password": "senha-incorreta"}

    assert client.post(reverse("account_sessions"), payload).status_code == 400
    rate_limited = client.post(reverse("account_sessions"), payload)

    assert rate_limited.status_code == 429
    assert rate_limited.headers["Retry-After"] == "300"
