"""Reusable non-domain forms for internal presentation examples."""

from __future__ import annotations

import re
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class CanonicalDigitsField(forms.CharField):
    """Accept a visual mask while returning digits as the canonical value."""

    default_error_messages = {
        "max_digits": _("Informe no máximo %(limit_value)d dígitos."),
    }

    def __init__(self, *args: Any, max_digits: int, **kwargs: Any) -> None:
        self.max_digits = max_digits
        super().__init__(*args, **kwargs)

    def clean(self, value: object) -> str:
        cleaned = super().clean(value)
        canonical_value = re.sub(r"\D", "", cleaned)
        if len(canonical_value) > self.max_digits:
            raise ValidationError(
                self.error_messages["max_digits"],
                code="max_digits",
                params={"limit_value": self.max_digits},
            )
        return canonical_value


class DesignSystemExampleForm(forms.Form):
    """Show every supported field family with synthetic operational labels."""

    display_name = forms.CharField(
        label=_("Nome de exibição"),
        help_text=_("Use um nome reconhecível para a equipe autorizada."),
    )
    category = forms.ChoiceField(
        label=_("Categoria"),
        choices=(("individual", _("Individual")), ("group", _("Grupo"))),
    )
    start_date = forms.DateField(
        label=_("Data de início"), widget=forms.DateInput(attrs={"type": "date"})
    )
    phone = CanonicalDigitsField(label=_("Telefone"), max_digits=11, required=False)
    document = CanonicalDigitsField(label=_("Documento"), max_digits=14, required=False)
    notes = forms.CharField(
        label=_("Observações administrativas"),
        widget=forms.Textarea,
        required=False,
    )
    confirmed = forms.BooleanField(label=_("Confirmo os dados"), required=False)
    contact_method = forms.ChoiceField(
        label=_("Contato preferencial"),
        choices=(("email", _("E-mail")), ("phone", _("Telefone"))),
        widget=forms.RadioSelect,
    )
    enabled = forms.BooleanField(label=_("Recurso ativo"), required=False)
    attachment = forms.FileField(label=_("Anexo"), required=False)
