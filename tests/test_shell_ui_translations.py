"""Focused HTTP contracts for S14.05 shell UI translation."""

from __future__ import annotations

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from clinics.models import ClinicMembership
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


def _login_in_clinic(client: Client, *, language: str) -> str:
    user = UserFactory.create(preferred_language=language)
    clinic = ClinicFactory.create(name="Clínica Horizonte")
    ClinicMembershipFactory.create(
        user=user,
        clinic=clinic,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return clinic.name


@pytest.mark.django_db
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
@pytest.mark.parametrize(
    ("language", "workspace", "navigation", "sign_out"),
    (
        ("en", "Workspace", "Main navigation", "Sign out"),
        ("es", "Espacio de trabajo", "Navegación principal", "Cerrar sesión"),
    ),
)
def test_workspace_shell_uses_effective_language_without_translating_contract_values(
    client: Client,
    language: str,
    workspace: str,
    navigation: str,
    sign_out: str,
) -> None:
    clinic_name = _login_in_clinic(client, language=language)

    response = client.get(reverse("workspace_vertical"))
    html = response.content.decode("utf-8")

    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    assert f'lang="{language}"' in html
    assert workspace in html
    assert f'aria-label="{navigation}"' in html
    assert sign_out in html
    # The product theme is pinned to light: no switch chrome may leak back in.
    assert "data-theme-dark" not in html
    assert "data-theme-toggle" not in html
    assert clinic_name in html
    assert 'value="vertical"' in html
    assert 'value="detached"' in html
    assert f'href="{reverse("workspace_vertical")}"' in html
    assert "/en/" not in html
    assert "/es/" not in html


@pytest.mark.django_db
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
@pytest.mark.parametrize(
    ("language", "expected"),
    (
        ("en", "Invalid layout preference."),
        ("es", "Preferencia de diseño no válida."),
    ),
)
def test_layout_error_is_translated_without_changing_the_layout_allowlist(
    client: Client, language: str, expected: str
) -> None:
    _login_in_clinic(client, language=language)

    response = client.post(
        reverse("workspace_layout_preference"),
        {"layout": "traduzido-invalido"},
    )

    assert response.status_code == 400
    assert response.content.decode("utf-8") == expected


@pytest.mark.django_db
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
@pytest.mark.parametrize(
    ("language", "expected"),
    (
        ("en", "Therapeutic platform available."),
        ("es", "Plataforma terapéutica disponible."),
    ),
)
def test_foundation_response_uses_the_request_language(
    client: Client, language: str, expected: str
) -> None:
    client.cookies["django_language"] = language

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    assert expected in response.content.decode("utf-8")
