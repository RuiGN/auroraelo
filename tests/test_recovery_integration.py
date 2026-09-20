"""Integração HTTP real de recuperação; sem consentimento ou LLM de produção."""

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client
from django.urls import resolve, reverse
from django.utils import timezone
from pytest_django.fixtures import SettingsWrapper

from accounts.models import AccountSession
from accounts.services import register_current_session
from ai_assistant.recovery_access import RecoveryConsent
from clinics.middleware import is_tenant_exempt_path
from tests.factories import UserFactory

PATHS = ("/api/v1/recovery/library/", "/api/v1/recovery/assistant/")


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("language", ["en", "es"])
def test_explicit_recovery_language_survives_real_middleware(
    path: str, language: str, settings: SettingsWrapper
) -> None:
    settings.ACCOUNT_SESSION_ALLOW_UNKNOWN = False
    settings.RECOVERY_CONSENT_RESOLVER = None
    settings.LANGUAGES = (
        ("pt-br", "Português (Brasil)"),
        ("en", "English"),
        ("es", "Español"),
    )
    actor = UserFactory.create(preferred_language=language)
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    request = HttpRequest()
    request.session = client.session
    register_current_session(request=request, user=actor)
    token = get_token(request)
    client.cookies[settings.CSRF_COOKIE_NAME] = token
    field = "message" if path.endswith("assistant/") else "query"

    with (
        patch("ai_assistant.recovery_views.redis_client") as redis,
        patch("ai_assistant.recovery_views.generate") as provider,
    ):
        response = client.post(
            path,
            {field: "Atividade física", "language": "pt-br"},
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
    assert language == response.wsgi_request.LANGUAGE_CODE
    assert response.status_code == 403
    assert response.json()["code"] == "consent_required"
    assert response.json()["detail"] == "Acesso requer consentimento expresso vigente."
    assert response.headers["Content-Language"] == "pt-br"
    assert "no-store" in response.headers["Cache-Control"]
    assert AccountSession.objects.filter(user=actor, revoked_at__isnull=True).exists()
    actor.refresh_from_db()
    assert actor.preferred_language == language
    redis.assert_not_called()
    provider.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_missing_b2c_consent_denies_without_tenant_or_external_calls(path: str) -> None:
    client = Client(enforce_csrf_checks=True)
    client.force_login(UserFactory.create())
    token = get_token(HttpRequest())
    client.cookies["csrftoken"] = token
    field = "message" if path.endswith("assistant/") else "query"
    with (
        patch("ai_assistant.recovery_views.redis_client") as redis,
        patch("ai_assistant.recovery_views.generate") as provider,
    ):
        response = client.post(
            path,
            {field: "Atividade física", "language": "pt-br"},
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "consent_required"
    assert "no-store" in response.headers["Cache-Control"]
    redis.assert_not_called()
    provider.assert_not_called()


@pytest.mark.parametrize("path", PATHS)
def test_recovery_routes_are_mounted_and_tenant_exceptions_are_exact(path: str) -> None:
    name = "recovery-assistant" if path.endswith("assistant/") else "recovery-library"
    assert resolve(path).url_name == name
    assert reverse(name) == path
    assert is_tenant_exempt_path(path)
    for wrong in (path + "extra/", path.rstrip("/"), "/x" + path, "/api/v1/recovery/"):
        assert not is_tenant_exempt_path(wrong)


def test_ai_is_disabled_and_consent_resolver_absent_by_default(
    settings: SettingsWrapper,
) -> None:
    assert settings.RECOVERY_AI_ENABLED is False
    assert settings.RECOVERY_AI_CLINICAL_APPROVED is False
    assert settings.RECOVERY_CONSENT_RESOLVER is None


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_recovery_still_requires_authentication_and_real_csrf(path: str) -> None:
    strict = Client(enforce_csrf_checks=True)
    token = get_token(HttpRequest())
    strict.cookies["csrftoken"] = token
    field = "message" if path.endswith("assistant/") else "query"
    payload = {field: "Atividade física"}
    assert (
        strict.post(
            path,
            payload,
            content_type="application/json",
            headers={"X-CSRFToken": token},
        ).status_code
        == 401
    )
    strict.force_login(UserFactory.create())
    assert (
        strict.post(path, payload, content_type="application/json").status_code == 403
    )
    assert strict.get(path).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_recovery_rejects_inactive_accounts_and_revoked_sessions(
    client: Client, path: str
) -> None:
    field = "message" if path.endswith("assistant/") else "query"
    payload = {field: "Atividade física"}
    client.force_login(UserFactory.create(is_active=False))
    assert (
        client.post(path, payload, content_type="application/json").status_code == 401
    )
    actor = UserFactory.create()
    client.force_login(actor)
    assert (
        client.post(path, payload, content_type="application/json").status_code == 403
    )
    tracked = AccountSession.objects.get(user=actor)
    tracked.revoked_at = timezone.now()
    tracked.save(update_fields=("revoked_at",))
    result = client.post(path, payload, content_type="application/json")
    assert result.status_code == 302
    assert result.headers["Location"] == reverse("account_login")


@pytest.mark.django_db
@pytest.mark.parametrize("path", PATHS)
def test_stale_clinic_session_does_not_authorize_or_choose_tenant(
    client: Client, path: str
) -> None:
    client.force_login(UserFactory.create())
    session = client.session
    session["active_clinic_id"] = "selecao-sintetica-invalida"
    session.save()
    field = "message" if path.endswith("assistant/") else "query"
    payload = {field: "Atividade física"}
    assert (
        client.post(path, payload, content_type="application/json").json()["code"]
        == "consent_required"
    )
    assert client.session["active_clinic_id"] == "selecao-sintetica-invalida"
    for url, headers, body in (
        (path + "?clinic_id=" + str(uuid4()), {}, payload),
        (path, {"X-Clinic-ID": str(uuid4())}, payload),
        (path, {}, {**payload, "user_id": str(uuid4())}),
        (path, {}, {**payload, "consent": True}),
    ):
        result = client.post(
            url, body, content_type="application/json", headers=headers
        )
        assert result.status_code == 400
        assert result.json()["code"] == "invalid_input"


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["pt-br", "en", "es"])
def test_synthetic_consent_does_not_enable_disabled_ai(
    language: str, settings: SettingsWrapper
) -> None:
    settings.ACCOUNT_SESSION_ALLOW_UNKNOWN = False
    settings.LANGUAGES = (
        ("pt-br", "Português (Brasil)"),
        ("en", "English"),
        ("es", "Español"),
    )
    actor = UserFactory.create(preferred_language=language)
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    request = HttpRequest()
    request.session = client.session
    register_current_session(request=request, user=actor)
    token = get_token(request)
    client.cookies[settings.CSRF_COOKIE_NAME] = token
    now = timezone.now()
    # Adaptador exclusivamente sintético; não demonstra consentimento persistido.
    resolver = Mock(
        return_value=RecoveryConsent(
            subject_id=actor.pk,
            purpose="recovery_ai",
            document_version="synthetic-v1",
            explicit=True,
            accepted_at=now - timedelta(minutes=1),
            expires_at=now + timedelta(minutes=5),
            revoked_at=None,
        )
    )
    settings.RECOVERY_CONSENT_RESOLVER = resolver
    with (
        patch("ai_assistant.recovery_views.redis_client") as redis,
        patch("ai_assistant.recovery_views.generate") as provider,
    ):
        result = client.post(
            PATHS[1],
            {"message": "Atividade física"},
            content_type="application/json",
            headers={"X-CSRFToken": token},
        )
    assert result.status_code == 503
    assert result.json()["code"] == "assistant_unavailable"
    assert result.json()["identity"] == "Aurora Elo — apoio digital de IA"
    assert result.json()["detail"] == "Assistente de IA indisponível."
    assert result.headers["Content-Language"] == "pt-br"
    assert result.wsgi_request.user.pk == actor.pk
    resolver.assert_called_once_with(
        actor=result.wsgi_request.user, purpose="recovery_ai"
    )
    assert settings.RECOVERY_AI_ENABLED is False
    assert settings.RECOVERY_AI_CLINICAL_APPROVED is False
    redis.assert_not_called()
    provider.assert_not_called()
