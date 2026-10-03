"""Forms of the staff screens of the wellness domain."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from .crisis_services import (
    HELPLINE_NAME_MAX_LENGTH,
    HELPLINE_NUMBER_MAX_LENGTH,
    MAX_DISCLAIMER_LENGTH,
    SERVICE_NUMBER_MAX_LENGTH,
    clean_disclaimer_text,
    clean_phone_number,
)


class CrisisResourcesForm(forms.Form):
    """Emergency numbers, the clinic's own helpline and the mandatory notice."""

    emergency_medical_number = forms.CharField(
        label=_("Emergência médica"),
        max_length=SERVICE_NUMBER_MAX_LENGTH,
        help_text=_("No Brasil, 192 (SAMU)."),
    )
    emergency_fire_number = forms.CharField(
        label=_("Bombeiros"),
        max_length=SERVICE_NUMBER_MAX_LENGTH,
        help_text=_("No Brasil, 193."),
    )
    emotional_support_number = forms.CharField(
        label=_("Apoio emocional"),
        max_length=SERVICE_NUMBER_MAX_LENGTH,
        help_text=_("No Brasil, 188 (CVV)."),
    )
    custom_helpline_name = forms.CharField(
        label=_("Linha de apoio da clínica (opcional)"),
        required=False,
        max_length=HELPLINE_NAME_MAX_LENGTH,
        help_text=_("Nome mostrado ao paciente, por exemplo: Plantão da clínica."),
    )
    custom_helpline_number = forms.CharField(
        label=_("Telefone da linha de apoio (opcional)"),
        required=False,
        max_length=HELPLINE_NUMBER_MAX_LENGTH,
        help_text=_("Apenas dígitos, espaços e um + no início."),
    )
    mandatory_disclaimer_text = forms.CharField(
        label=_("Aviso exibido ao paciente"),
        max_length=MAX_DISCLAIMER_LENGTH,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=_(
            "O texto obrigatório abaixo não pode ser removido nem alterado. "
            "Você pode acrescentar orientações antes ou depois dele."
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css = "ae-textarea" if isinstance(widget, forms.Textarea) else "ae-input"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
            if not isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("inputmode", "tel")
        self.fields["custom_helpline_name"].widget.attrs["inputmode"] = "text"

    def clean_emergency_medical_number(self) -> str:
        return clean_phone_number(
            self.cleaned_data["emergency_medical_number"],
            max_length=SERVICE_NUMBER_MAX_LENGTH,
        )

    def clean_emergency_fire_number(self) -> str:
        return clean_phone_number(
            self.cleaned_data["emergency_fire_number"],
            max_length=SERVICE_NUMBER_MAX_LENGTH,
        )

    def clean_emotional_support_number(self) -> str:
        return clean_phone_number(
            self.cleaned_data["emotional_support_number"],
            max_length=SERVICE_NUMBER_MAX_LENGTH,
        )

    def clean_custom_helpline_number(self) -> str:
        value: str = self.cleaned_data["custom_helpline_number"]
        if not value.strip():
            return ""
        return clean_phone_number(value, max_length=HELPLINE_NUMBER_MAX_LENGTH)

    def clean_mandatory_disclaimer_text(self) -> str:
        return clean_disclaimer_text(self.cleaned_data["mandatory_disclaimer_text"])

    def clean(self) -> dict[str, Any]:
        cleaned: dict[str, Any] = super().clean() or {}
        name = " ".join(str(cleaned.get("custom_helpline_name", "")).split())
        number = cleaned.get("custom_helpline_number", "")
        if "custom_helpline_number" not in self.errors:
            if name and not number:
                self.add_error(
                    "custom_helpline_number",
                    _("Informe o telefone da linha de apoio."),
                )
            elif number and not name:
                self.add_error(
                    "custom_helpline_name",
                    _("Informe o nome da linha de apoio."),
                )
        cleaned["custom_helpline_name"] = name
        return cleaned
