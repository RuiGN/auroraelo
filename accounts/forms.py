"""Server-rendered forms for account authentication flows."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from clinics.services import membership_role_choices

_MEMBERSHIP_ROLE_UI_LABELS = {
    "clinic_admin": _("Administrador da clínica"),
    "therapist": _("Terapeuta"),
    "administrative_staff": _("Equipe administrativa"),
    "patient": _("Paciente"),
}


def translated_membership_role_label(role: str) -> str:
    """Return the translated label of a membership role.

    Unknown values fall back to a translated generic label so the model display
    name (untranslated) is never rendered in the UI.
    """
    for value, label in translated_membership_role_choices():
        if value == role:
            return str(label)
    return str(_("Papel não reconhecido"))


def translated_membership_role_choices() -> tuple[tuple[str, object], ...]:
    """Keep stable role codes while translating labels in the account UI."""
    return tuple(
        (value, _MEMBERSHIP_ROLE_UI_LABELS.get(value, label))
        for value, label in membership_role_choices()
    )


class LoginForm(forms.Form):
    """Collect credentials without encoding account-existence distinctions."""

    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": _("seu@email.com"),
            }
        ),
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": _("Digite sua senha"),
            }
        ),
    )


class PasswordRecoveryForm(forms.Form):
    """Collect a recovery identity using a neutral response contract."""

    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": _("Informe o e-mail cadastrado"),
            }
        ),
    )


class PasswordResetForm(forms.Form):
    """Validate a new credential and its explicit confirmation."""

    new_password = forms.CharField(
        label=_("Nova senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Crie uma senha forte"),
            }
        ),
    )
    confirm_password = forms.CharField(
        label=_("Confirme a nova senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Repita a nova senha"),
            }
        ),
    )

    def clean(self) -> dict[str, Any]:
        """Require matching credentials and apply configured Django validators."""
        cleaned: dict[str, Any] = super().clean() or {}
        password = cleaned.get("new_password")
        confirmation = cleaned.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error(
                "confirm_password",
                _("As senhas informadas não coincidem."),
            )
            return cleaned
        if isinstance(password, str):
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("new_password", error)
        return cleaned


class SensitiveActionReauthenticationForm(forms.Form):
    """Collect the current password immediately before a high-impact action."""

    password = forms.CharField(
        label=_("Senha atual"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class InvitationIssueForm(forms.Form):
    """Collect the bounded tenant role and expiry for one invitation."""

    recipient_email = forms.EmailField(label=_("E-mail da pessoa convidada"))
    initial_role = forms.ChoiceField(
        label=_("Papel inicial"),
        choices=translated_membership_role_choices(),
    )
    expires_in_hours = forms.IntegerField(
        label=_("Validade em horas"),
        min_value=1,
        max_value=168,
        initial=24,
    )


class InvitationAcceptanceForm(forms.Form):
    """Collect a new invited identity without weakening password validation."""

    first_name = forms.CharField(label=_("Nome"), max_length=150)
    last_name = forms.CharField(label=_("Sobrenome"), max_length=150)
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirme a senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self) -> dict[str, Any]:
        """Require matching credentials before the service validates strength."""
        cleaned: dict[str, Any] = super().clean() or {}
        password = cleaned.get("password")
        confirmation = cleaned.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error("confirm_password", _("As senhas informadas não coincidem."))
        return cleaned
