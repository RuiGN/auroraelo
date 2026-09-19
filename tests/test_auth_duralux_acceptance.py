"""Rendered acceptance checks for the Duralux account presentation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountSession, User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _authenticated_user(client: Client) -> User:
    user = UserFactory.create()
    client.force_login(user)
    return user


def test_public_auth_forms_use_the_minimal_shell_and_preserve_django_inputs(
    client: Client,
) -> None:
    login = client.get(reverse("account_login"))
    recovery = client.get(reverse("password_recovery"))

    assert login.status_code == recovery.status_code == 200
    login_html = login.content.decode()
    recovery_html = recovery.content.decode()

    assert 'lang="pt-br"' in login_html.lower()
    assert 'href="/static/duralux/css/auth.css"' in login_html
    assert 'class="minimal-card-wrapper product-auth-inner"' in login_html
    assert 'name="csrfmiddlewaretoken"' in login_html
    assert 'name="email"' in login_html
    assert 'autocomplete="email"' in login_html
    assert 'name="password"' in login_html
    assert 'autocomplete="current-password"' in login_html
    assert reverse("password_recovery") in login_html
    assert "data-theme-toggle" not in login_html
    assert 'name="csrfmiddlewaretoken"' in recovery_html
    assert 'name="email"' in recovery_html
    assert reverse("account_login") in recovery_html


def test_invalid_login_keeps_field_errors_associated_with_the_original_input(
    client: Client,
) -> None:
    response = client.post(
        reverse("account_login"),
        {"email": "endereco-invalido", "password": ""},
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert "data-focus-error-summary" not in html  # no non-field summary in this state
    assert 'id="id_email"' in html
    assert 'id="id_email_error_0"' in html
    assert 'aria-invalid="true"' in html
    assert 'value="endereco-invalido"' in html
    assert 'id="id_password"' in html
    assert 'id="id_password_error_0"' in html


def test_recovery_confirmation_keeps_the_generic_status_message(client: Client) -> None:
    response = client.post(
        reverse("password_recovery"),
        {"email": "nao-cadastrada@example.test"},
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert 'role="status"' in html
    assert "Se existir uma conta ativa para este e-mail" in html
    assert "nao-cadastrada@example.test" not in html
    assert reverse("account_login") in html


def test_session_management_renders_device_status_and_revocation_payload(
    client: Client,
) -> None:
    user = _authenticated_user(client)
    django_session = Session.objects.create(
        session_key="auth-duralux-other-session",
        session_data="e30:synthetic",
        expire_date=timezone.now() + timedelta(hours=1),
    )
    tracked = AccountSession.objects.create_for_session(
        user=user,
        session_key=django_session.session_key,
        client_label="Firefox em computador",
        network_hint="",
        absolute_expires_at=timezone.now() + timedelta(hours=1),
    )

    response = client.get(reverse("account_sessions"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Firefox em computador" in html
    assert "Última atividade:" in html
    assert "<time datetime=" in html
    assert 'name="action" value="revoke"' in html
    assert f'name="session_id" value="{tracked.pk}"' in html
    assert 'aria-label="Encerrar Firefox em computador"' in html
    assert 'name="action" value="revoke_others"' in html
    assert 'name="password"' in html
    assert 'autocomplete="current-password"' in html


def test_session_reauthentication_error_is_linked_and_focusable(client: Client) -> None:
    _authenticated_user(client)

    response = client.post(
        reverse("account_sessions"),
        {"action": "revoke_others", "password": "senha-incorreta"},
    )

    assert response.status_code == 400
    html = response.content.decode()
    assert 'id="id_password"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="id_password_error_0"' in html
    assert 'id="id_password_error_0"' in html
    assert "Não foi possível confirmar sua senha atual." in html
