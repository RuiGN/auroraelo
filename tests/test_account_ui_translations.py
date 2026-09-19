"""Focused translation contracts for account UI copy."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import pytest
from django import forms
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import translation

from accounts.forms import InvitationAcceptanceForm, InvitationIssueForm, LoginForm

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


@pytest.mark.parametrize(
    ("language", "title", "password_label", "recovery_link"),
    (
        ("en", "Sign in to the platform", "Password", "I forgot my password"),
        ("es", "Iniciar sesión en la plataforma", "Contraseña", "Olvidé mi contraseña"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_login_response_uses_selected_language(
    client: Client,
    language: str,
    title: str,
    password_label: str,
    recovery_link: str,
) -> None:
    response = client.get(reverse("account_login"), HTTP_ACCEPT_LANGUAGE=language)

    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    content = response.content.decode()
    assert title in content
    assert password_label in content
    assert recovery_link in content


@pytest.mark.parametrize(
    ("language", "password_label", "mismatch_error"),
    (
        ("en", "Confirm password", "The passwords do not match."),
        ("es", "Confirme la contraseña", "Las contraseñas no coinciden."),
    ),
)
def test_invitation_form_labels_and_validation_are_translated(
    language: str,
    password_label: str,
    mismatch_error: str,
) -> None:
    with translation.override(language):
        form = InvitationAcceptanceForm(
            data={
                "first_name": "Test",
                "last_name": "User",
                "password": "different-one",
                "confirm_password": "different-two",
            }
        )

        assert not form.is_valid()
        assert str(form.fields["confirm_password"].label) == password_label
        assert mismatch_error in form.errors["confirm_password"]


@pytest.mark.parametrize(
    ("language", "email_error"),
    (
        ("en", "Enter a valid email address."),
        ("es", "Introduzca una dirección de correo electrónico válida."),
    ),
)
def test_framework_validation_follows_account_form_language(
    language: str,
    email_error: str,
) -> None:
    with translation.override(language):
        form = LoginForm(data={"email": "invalid", "password": "secret"})

        assert not form.is_valid()
        assert email_error in form.errors["email"]


@pytest.mark.parametrize(
    ("language", "expected_labels"),
    (
        (
            "en",
            ("Clinic administrator", "Therapist", "Administrative staff", "Patient"),
        ),
        (
            "es",
            (
                "Administrador de la clínica",
                "Terapeuta",
                "Personal administrativo",
                "Paciente",
            ),
        ),
    ),
)
def test_invitation_roles_translate_labels_without_changing_codes(
    language: str,
    expected_labels: tuple[str, ...],
) -> None:
    with translation.override(language):
        field = InvitationIssueForm().fields["initial_role"]
        assert isinstance(field, forms.ChoiceField)
        choices = [
            (value, str(label))
            for value, label in cast(Iterable[tuple[str, object]], field.choices)
        ]

    assert [value for value, _label in choices] == [
        "clinic_admin",
        "therapist",
        "administrative_staff",
        "patient",
    ]
    assert tuple(str(label) for _value, label in choices) == expected_labels
