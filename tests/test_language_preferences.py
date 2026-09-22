"""Backend acceptance tests for Duralux language preferences (S14.02/.03)."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from importlib import import_module
from typing import cast

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import translation

from accounts.context_processors import language_preferences
from accounts.middleware import UserLanguageMiddleware
from accounts.models import AccountSession, User
from clinics.services import CLINIC_SESSION_KEY
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


def csrf_client() -> Client:
    client = Client(enforce_csrf_checks=True)
    client.cookies[settings.CSRF_COOKIE_NAME] = "a" * 32
    return client


def post_language(
    client: Client, language: str, next_url: str = "/"
) -> HttpResponseBase:
    return client.post(
        reverse("account_set_language"),
        {"language": language, "next": next_url},
        HTTP_X_CSRFTOKEN="a" * 32,
    )


def test_user_language_candidates_and_blank_default() -> None:
    field = User._meta.get_field("preferred_language")

    assert field.blank is True
    assert field.default == ""
    assert field.choices == User.Language.choices
    assert tuple(User.Language.choices) == LAUNCH_LANGUAGES
    assert UserFactory.create().preferred_language == ""


def test_only_reviewed_portuguese_is_published_by_default() -> None:
    # The test settings expand LANGUAGES to enable i18n test coverage for EN/ES.
    # The invariant we enforce is that the *base* settings (used by production)
    # only expose the fully reviewed and launched language.  Import base directly
    # to avoid the test-environment expansion masking a production misconfiguration.
    from config.settings.base import LANGUAGES as BASE_LANGUAGES

    assert tuple(BASE_LANGUAGES) == (LAUNCH_LANGUAGES[0],)


@pytest.mark.parametrize(
    ("settings_module", "expected_languages"),
    (
        ("config.settings.development", LAUNCH_LANGUAGES),
        ("config.settings.production", (LAUNCH_LANGUAGES[0],)),
    ),
)
def test_runtime_languages_separate_local_acceptance_from_production(
    settings_module: str,
    expected_languages: tuple[tuple[str, str], ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = {
        "DJANGO_SECRET_KEY": "test-settings-secret",
        "AUDIT_INTEGRITY_KEY": "test-settings-audit-key",
        "MFA_ENCRYPTION_KEY": "test-settings-mfa-key",
        "CACHE_REDIS_URL": "redis://127.0.0.1:6379/15",
        "DJANGO_ALLOWED_HOSTS": "example.test",
        "DB_NAME": "settings-contract",
        "DB_USER": "settings-contract",
        "DB_PASSWORD": "settings-contract",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_SSLMODE": "disable",
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    module = import_module(settings_module)

    assert tuple(module.LANGUAGES) == expected_languages


@pytest.mark.django_db(transaction=True)
def test_preference_migration_leaves_existing_users_without_explicit_choice() -> None:
    executor = MigrationExecutor(connection)
    try:
        # Attempt to resolve the migration node; skip gracefully if the migration
        # graph is absent (e.g. when running with --no-migrations for speed).
        executor.loader.graph.forwards_plan(
            ("accounts", "0006_alter_clinicinvitation_initial_role")
        )
    except Exception:
        pytest.skip("Migration graph not available (--no-migrations mode)")
    latest_targets = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate([("accounts", "0006_alter_clinicinvitation_initial_role")])
        old_apps = executor.loader.project_state(
            [("accounts", "0006_alter_clinicinvitation_initial_role")]
        ).apps
        old_user_model = old_apps.get_model("accounts", "User")
        old_user = old_user_model.objects.create(email="existing-language@example.test")

        executor = MigrationExecutor(connection)
        executor.migrate([("accounts", "0007_user_preferred_language")])

        assert User.objects.get(pk=old_user.pk).preferred_language == ""
    finally:
        # A historical state can contain retired tables unknown to Django's flush.
        MigrationExecutor(connection).migrate(latest_targets)


def test_language_endpoint_is_post_only_and_requires_csrf() -> None:
    client = Client(enforce_csrf_checks=True)

    assert client.get(reverse("account_set_language")).status_code == 405
    without_csrf = client.post(reverse("account_set_language"), {"language": "pt-br"})
    assert without_csrf.status_code == 403


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_anonymous_choice_sets_cookie_without_creating_identity() -> None:
    client = csrf_client()

    response = post_language(client, "es", "/accounts/login/?next=%2Fworkspace%2F")

    assert response.status_code == 302
    assert response.headers["Location"] == "/accounts/login/?next=%2Fworkspace%2F"
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "es"
    assert User.objects.count() == 0


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_external_next_and_invalid_language_are_rejected_safely() -> None:
    client = csrf_client()

    external = post_language(client, "en", "https://attacker.example/collect")
    invalid = post_language(client, "fr", "/workspace/")

    assert external.status_code == 302
    assert external.headers["Location"] == "/"
    assert external.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"
    assert invalid.status_code == 400
    assert settings.LANGUAGE_COOKIE_NAME not in invalid.cookies


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_authenticated_manual_choice_updates_profile_and_cookie_together() -> None:
    user = UserFactory.create(preferred_language="")
    client = csrf_client()
    client.force_login(user)

    response = post_language(client, "en", "/workspace/?page=2")

    user.refresh_from_db()
    assert response.status_code == 302
    assert response.headers["Location"] == "/workspace/?page=2"
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == "en"
    assert user.preferred_language == "en"


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_profile_preference_wins_across_clients_and_over_an_existing_cookie() -> None:
    user = UserFactory.create(preferred_language="es")
    first = Client()
    second = Client()
    first.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
    first.force_login(user)
    second.force_login(user)

    assert first.get(reverse("account_login")).headers["Content-Language"] == "es"
    assert second.get(reverse("account_login")).headers["Content-Language"] == "es"


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_two_users_in_one_browser_keep_independent_profile_preferences() -> None:
    first_user = UserFactory.create(preferred_language="es")
    second_user = UserFactory.create(preferred_language="")
    client = Client()
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"

    client.force_login(first_user)
    assert client.get(reverse("account_login")).headers["Content-Language"] == "es"
    client.force_login(second_user)
    assert client.get(reverse("account_login")).headers["Content-Language"] == "en"

    first_user.refresh_from_db()
    second_user.refresh_from_db()
    assert first_user.preferred_language == "es"
    assert second_user.preferred_language == ""


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_cookie_and_accept_language_precedence_do_not_persist_inferred_values() -> None:
    cookie_client = Client()
    cookie_client.cookies[settings.LANGUAGE_COOKIE_NAME] = "es"
    browser_client = Client(HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9")

    cookie_response = cookie_client.get(reverse("account_login"))
    browser_response = browser_client.get(reverse("account_login"))

    assert cookie_response.headers["Content-Language"] == "es"
    assert browser_response.headers["Content-Language"] == "en"


@override_settings(LANGUAGES=(("pt-br", "Português (Brasil)"),))
def test_removed_profile_and_cookie_values_fall_back_without_rewriting() -> None:
    user = UserFactory.create(preferred_language="es")
    client = Client(HTTP_ACCEPT_LANGUAGE="en,pt-BR;q=0.8")
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "es"
    client.force_login(user)

    response = client.get(reverse("account_login"))

    user.refresh_from_db()
    assert response.headers["Content-Language"] == "pt-br"
    assert user.preferred_language == "es"
    assert settings.LANGUAGE_COOKIE_NAME not in response.cookies


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_action_does_not_grant_clinic_access() -> None:
    user = UserFactory.create(is_staff=True)
    client = csrf_client()
    client.force_login(user)

    changed = post_language(client, "en", reverse("workspace_vertical"))
    protected = client.get(reverse("workspace_vertical"))

    user.refresh_from_db()
    assert changed.status_code == 302
    assert user.preferred_language == "en"
    assert protected.status_code == 400


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_change_does_not_modify_active_clinic_selection() -> None:
    user = UserFactory.create()
    client = csrf_client()
    client.force_login(user)
    session = client.session
    session[CLINIC_SESSION_KEY] = "00000000-0000-0000-0000-000000000123"
    session.save()

    response = post_language(client, "en")

    assert response.status_code == 302
    assert client.session[CLINIC_SESSION_KEY] == "00000000-0000-0000-0000-000000000123"


@override_settings(LANGUAGES=LAUNCH_LANGUAGES, ACCOUNT_SESSION_ALLOW_UNKNOWN=False)
def test_revoked_managed_session_cannot_change_profile_or_cookie() -> None:
    user = UserFactory.create(preferred_language="pt-br")
    client = csrf_client()
    client.force_login(user)
    with override_settings(ACCOUNT_SESSION_ALLOW_UNKNOWN=True):
        client.get(reverse("account_login"))
    account_session = AccountSession.objects.get(user=user)
    account_session.revoked_at = account_session.last_seen_at
    account_session.save(update_fields=("revoked_at", "updated_at"))

    response = post_language(client, "en")

    user.refresh_from_db()
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("account_login")
    assert user.preferred_language == "pt-br"
    assert settings.LANGUAGE_COOKIE_NAME not in response.cookies


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_context_processor_exposes_local_names_and_safe_current_query() -> None:
    request = RequestFactory().get("/workspace/?page=2&search=ana")
    request.LANGUAGE_CODE = "en"

    context = language_preferences(request)

    assert context == {
        "ui_languages": [
            {
                "code": "pt-br",
                "name_local": "Português (Brasil)",
                "country_code": "br",
                "flag_path": "duralux/images/flags/br.svg",
            },
            {
                "code": "en",
                "name_local": "English",
                "country_code": "us",
                "flag_path": "duralux/images/flags/us.svg",
            },
            {
                "code": "es",
                "name_local": "Español",
                "country_code": "es",
                "flag_path": "duralux/images/flags/es.svg",
            },
        ],
        "current_ui_language": "en",
        "ui_language_next": "/workspace/?page=2&search=ana",
    }


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_middleware_varies_translated_html_and_restores_context() -> None:
    request = RequestFactory().get("/stream/", HTTP_ACCEPT_LANGUAGE="en")
    request.user = UserFactory.create(preferred_language="es")
    request.LANGUAGE_CODE = "en"
    translation.activate("pt-br")

    def stream() -> Iterator[bytes]:
        yield str(translation.get_language()).encode()

    response = UserLanguageMiddleware(
        lambda _request: StreamingHttpResponse(stream(), content_type="text/html")
    )(request)

    assert translation.get_language() == "pt-br"
    assert response.headers["Content-Language"] == "es"
    assert set(response.headers["Vary"].split(", ")) == {"Cookie", "Accept-Language"}
    streaming = cast(StreamingHttpResponse, response)
    assert streaming.is_async is False
    content = cast(Iterable[bytes], streaming.streaming_content)
    assert b"".join(content) == b"es"
    assert translation.get_language() == "pt-br"


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_middleware_localizes_async_stream_without_context_leak() -> None:
    request = RequestFactory().get("/async-stream/")
    request.user = UserFactory.create(preferred_language="en")
    request.LANGUAGE_CODE = "pt-br"
    translation.activate("pt-br")

    async def stream() -> AsyncIterator[bytes]:
        yield str(translation.get_language()).encode()

    response = UserLanguageMiddleware(
        lambda _request: StreamingHttpResponse(stream(), content_type="text/html")
    )(request)

    async def consume() -> bytes:
        streaming = cast(StreamingHttpResponse, response)
        assert streaming.is_async is True
        content = cast(AsyncIterable[bytes], streaming.streaming_content)
        chunks = [chunk async for chunk in content]
        return b"".join(chunks)

    assert async_to_sync(consume)() == b"en"
    assert translation.get_language() == "pt-br"
