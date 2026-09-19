"""Forms for the ordered clinic setup flow."""

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from .services import CLINIC_MODULE_PREREQUISITES

WEEKDAYS = (
    ("monday", _("Segunda-feira")),
    ("tuesday", _("Terça-feira")),
    ("wednesday", _("Quarta-feira")),
    ("thursday", _("Quinta-feira")),
    ("friday", _("Sexta-feira")),
    ("saturday", _("Sábado")),
    ("sunday", _("Domingo")),
)

MODULE_LABELS = {
    "patient_management": _("Pacientes"),
    "agenda": _("Agenda"),
    "clinical_records": _("Registros clínicos"),
    "finance": _("Financeiro"),
    "billing": _("Cobrança"),
    "documents": _("Documentos"),
    "metrics": _("Indicadores"),
    "notifications": _("Notificações"),
}


class ClinicIdentityForm(forms.Form):
    """Minimized institutional identity and structured address."""

    legal_name = forms.CharField(label=_("Razão social"), max_length=255)
    display_name = forms.CharField(label=_("Nome de exibição"), max_length=120)
    registration_identifier = forms.CharField(
        label=_("Documento aplicável"), max_length=64, required=False
    )
    administrative_email = forms.EmailField(label=_("E-mail administrativo"))
    administrative_phone = forms.CharField(
        label=_("Telefone administrativo"), max_length=32, required=False
    )
    address_line_1 = forms.CharField(label=_("Endereço"), max_length=255)
    address_line_2 = forms.CharField(
        label=_("Complemento"), max_length=255, required=False
    )
    city = forms.CharField(label=_("Cidade"), max_length=120)
    region = forms.CharField(label=_("Estado ou região"), max_length=120)
    postal_code = forms.CharField(label=_("Código postal"), max_length=32)
    country_code = forms.CharField(label=_("País (ISO)"), min_length=2, max_length=2)


class ClinicOperationsForm(forms.Form):
    """Operational locale, channels, hours and off-hours guidance."""

    timezone_name = forms.CharField(label=_("Fuso horário"), max_length=64)
    language_code = forms.ChoiceField(
        label=_("Idioma"),
        choices=(("pt-BR", _("Português do Brasil")), ("en-US", _("English (US)"))),
    )
    service_channels = forms.MultipleChoiceField(
        label=_("Canais institucionais"),
        choices=(
            ("in_person", _("Presencial")),
            ("video", _("Videochamada")),
            ("phone", _("Telefone")),
        ),
        widget=forms.CheckboxSelectMultiple,
    )
    out_of_hours_instructions = forms.CharField(
        label=_("Orientação fora do expediente"),
        max_length=1000,
        required=False,
        widget=forms.Textarea,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for key, label in WEEKDAYS:
            self.fields[f"{key}_start"] = forms.TimeField(
                label=_("%(weekday)s: início") % {"weekday": label},
                required=False,
                widget=forms.TimeInput(),
            )
            self.fields[f"{key}_end"] = forms.TimeField(
                label=_("%(weekday)s: fim") % {"weekday": label},
                required=False,
                widget=forms.TimeInput(),
            )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        weekly_hours: dict[str, list[dict[str, str]]] = {}
        for key, _label in WEEKDAYS:
            start = cleaned.get(f"{key}_start")
            end = cleaned.get(f"{key}_end")
            if bool(start) != bool(end):
                self.add_error(
                    f"{key}_{'end' if start else 'start'}",
                    _("Informe início e fim, ou deixe os dois campos vazios."),
                )
            weekly_hours[key] = (
                [{"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")}]
                if start and end
                else []
            )
        cleaned["weekly_hours"] = weekly_hours
        return cleaned


class ClinicBrandingForm(forms.Form):
    """Safe logo and accessible brand accent inputs."""

    logo = forms.FileField(
        label=_("Logotipo (PNG ou JPEG, até 2 MB)"),
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/png,image/jpeg", "data-brand-logo-input": ""}
        ),
    )
    primary_color = forms.CharField(
        label=_("Cor primária"),
        max_length=7,
        widget=forms.TextInput(attrs={"type": "color", "data-brand-primary-input": ""}),
    )
    secondary_color = forms.CharField(
        label=_("Cor secundária"),
        max_length=7,
        widget=forms.TextInput(
            attrs={"type": "color", "data-brand-secondary-input": ""}
        ),
    )


class ClinicModulesForm(forms.Form):
    """Closed module selection with visible prerequisite validation."""

    enabled_modules = forms.MultipleChoiceField(
        label=_("Módulos ativos"),
        choices=tuple(MODULE_LABELS.items()),
        widget=forms.CheckboxSelectMultiple,
    )

    def clean_enabled_modules(self) -> list[str]:
        selected = list(self.cleaned_data["enabled_modules"])
        missing = {
            prerequisite
            for module in selected
            for prerequisite in CLINIC_MODULE_PREREQUISITES[module]
            if prerequisite not in selected
        }
        if missing:
            missing_labels = ", ".join(
                str(MODULE_LABELS[code]) for code in sorted(missing)
            )
            raise forms.ValidationError(
                _("Ative os pré-requisitos antes dos módulos dependentes: %(modules)s"),
                params={"modules": missing_labels},
            )
        return selected
