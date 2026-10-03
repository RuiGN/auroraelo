"""Team forms for medication, care plans and habits (design system classes, i18n)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .medication_services import validate_non_prescriptive_content
from .models import CarePlanStatus, HabitFrequency, TimeOfDayWindow
from .presentation import (
    FREQUENCY_CHOICES,
    ROUTE_CHOICES,
    WEEKDAY_CHOICES,
    WINDOW_CHOICES,
)

MAX_DOSES_PER_DAY = 12
MAX_PLAN_ACTIONS = 12
MAX_HABIT_MINUTES = 480

_TIME_TOKEN = re.compile(r"^(\d{1,2}):(\d{2})$")


def _date_widget() -> forms.DateInput:
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def _time_widget() -> forms.TimeInput:
    return forms.TimeInput(attrs={"type": "time"}, format="%H:%M")


class AeFormMixin:
    """Apply the design system classes (`ae-input`, `ae-select`, `ae-textarea`)."""

    fields: dict[str, forms.Field]

    def apply_design_system(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput | forms.CheckboxSelectMultiple):
                continue
            if isinstance(widget, forms.Select):
                css = "ae-select"
            elif isinstance(widget, forms.Textarea):
                css = "ae-textarea"
            else:
                css = "ae-input"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()


class AeForm(AeFormMixin, forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_design_system()


# ── Confirmações ────────────────────────────────────────────────────────────


class ConfirmForm(AeForm):
    """A single explicit confirmation, worded for the action being confirmed."""

    confirm = forms.BooleanField(
        required=True,
        error_messages={"required": _("Marque a confirmação para continuar.")},
    )

    def __init__(self, *args: Any, label: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["confirm"].label = label


MEDICATION_STOP_CHOICES = [
    ("suspend", _("Suspender: sai do app e poderá ser retomada")),
    ("end", _("Encerrar o tratamento: sai do app e não poderá ser retomada")),
]


class MedicationStopForm(ConfirmForm):
    kind = forms.ChoiceField(
        label=_("O que fazer com este medicamento"), choices=MEDICATION_STOP_CHOICES
    )

    field_order = ["kind", "confirm"]

    def __init__(self, *args: Any, allow_suspend: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not allow_suspend:
            # A medication that is already suspended can only be ended.
            self.fields["kind"].choices = [  # type: ignore[attr-defined]
                choice for choice in MEDICATION_STOP_CHOICES if choice[0] == "end"
            ]


PLAN_CLOSE_CHOICES = [
    (
        CarePlanStatus.COMPLETED.value,
        _("Concluído: os objetivos foram cumpridos ou o ciclo terminou"),
    ),
    (CarePlanStatus.REVOKED.value, _("Revogado: a equipe retirou o plano")),
]


class CarePlanCloseForm(ConfirmForm):
    outcome = forms.ChoiceField(
        label=_("Como o plano termina"), choices=PLAN_CLOSE_CHOICES
    )

    field_order = ["outcome", "confirm"]


class HabitPauseForm(AeForm):
    paused_until = forms.DateField(
        label=_("Pausado até (opcional)"),
        required=False,
        widget=_date_widget(),
        help_text=_(
            "É só um lembrete para a equipe: o hábito continua pausado até que "
            "alguém o retome."
        ),
    )

    def clean_paused_until(self) -> date | None:
        value: date | None = self.cleaned_data["paused_until"]
        if value is not None and value < timezone.localdate():
            raise ValidationError(_("A data não pode estar no passado."))
        return value


# ── Medicação ───────────────────────────────────────────────────────────────


def parse_schedule_times(raw: str) -> list[str]:
    """Turn ``"8:00, 20:30"`` into the sorted, zero-padded ``["08:00", "20:30"]``."""
    tokens = [token for token in re.split(r"[,;\s]+", raw.strip()) if token]
    times: set[str] = set()
    for token in tokens:
        match = _TIME_TOKEN.match(token)
        hour, minute = (int(part) for part in match.groups()) if match else (99, 99)
        if hour > 23 or minute > 59:
            raise ValidationError(
                _("Horário inválido: %(value)s. Use HH:MM, por exemplo 08:00."),
                params={"value": token},
            )
        times.add(f"{hour:02d}:{minute:02d}")
    if not times:
        raise ValidationError(_("Informe ao menos um horário."))
    if len(times) > MAX_DOSES_PER_DAY:
        raise ValidationError(
            _("Informe no máximo %(max)d horários."), params={"max": MAX_DOSES_PER_DAY}
        )
    return sorted(times)


class MedicationForm(AeForm):
    """Register or correct an external prescription for adherence tracking."""

    medication_name = forms.CharField(label=_("Medicamento"), max_length=255)
    presentation = forms.CharField(
        label=_("Apresentação"),
        max_length=128,
        help_text=_("Por exemplo: comprimido, gotas, solução oral."),
    )
    prescribed_dose = forms.CharField(
        label=_("Dose prescrita"),
        max_length=128,
        help_text=_("Exatamente como consta na receita. Por exemplo: 50 mg."),
    )
    route = forms.ChoiceField(label=_("Via de administração"), choices=ROUTE_CHOICES)
    schedule_times = forms.CharField(label=_("Horários das doses"), max_length=200)
    start_date = forms.DateField(label=_("Início do tratamento"), widget=_date_widget())
    is_continuous = forms.BooleanField(
        label=_("Uso contínuo (sem data final)"), required=False
    )
    end_date = forms.DateField(
        label=_("Fim do tratamento"), required=False, widget=_date_widget()
    )
    prescriber_name = forms.CharField(
        label=_("Prescritor"),
        max_length=255,
        help_text=_("Profissional externo que assinou a receita."),
    )
    prescriber_registration = forms.CharField(
        label=_("Registro do prescritor (CRM/CRO)"), max_length=64
    )
    prescription_date = forms.DateField(
        label=_("Data da receita"), widget=_date_widget()
    )
    instructions = forms.CharField(
        label=_("Orientações da receita (o paciente vê)"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_(
            "Copie só o que está na receita. Mudar, compensar ou interromper a "
            "dose é decisão do prescritor e não pode ser publicado aqui."
        ),
    )

    def __init__(self, *args: Any, timezone_name: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["schedule_times"].help_text = gettext(
            "Horários no formato HH:MM, separados por vírgula, no fuso do "
            "paciente (%(zone)s). Por exemplo: 08:00, 20:00."
        ) % {"zone": timezone_name}

    def clean_schedule_times(self) -> list[str]:
        return parse_schedule_times(self.cleaned_data["schedule_times"])

    def clean_instructions(self) -> str:
        text: str = self.cleaned_data["instructions"]
        try:
            validate_non_prescriptive_content(text)
        except ValidationError:
            raise ValidationError(
                _(
                    "Esta orientação sugere mudar, compensar ou interromper a "
                    "medicação. Isso é decisão do prescritor e não pode ser "
                    "publicado no app."
                )
            ) from None
        return text

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        start: date | None = data.get("start_date")
        end: date | None = data.get("end_date")
        if data.get("is_continuous"):
            if end is not None:
                self.add_error(
                    "end_date",
                    _(
                        "Uso contínuo não tem data final: apague a data ou "
                        "desmarque o uso contínuo."
                    ),
                )
        elif end is None and "end_date" not in self.errors:
            self.add_error(
                "end_date", _("Informe a data final ou marque o uso contínuo.")
            )
        if start is not None and end is not None and end < start:
            self.add_error(
                "end_date", _("A data final não pode ser anterior ao início.")
            )
        prescribed_on: date | None = data.get("prescription_date")
        if prescribed_on is not None and prescribed_on > timezone.localdate():
            self.add_error(
                "prescription_date", _("A data da receita não pode ser futura.")
            )
        return data


# ── Plano de cuidado ────────────────────────────────────────────────────────


class CarePlanForm(AeForm):
    title = forms.CharField(label=_("Título do plano"), max_length=255)
    objective = forms.CharField(
        label=_("Objetivo (o paciente vê)"),
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    clinical_rationale = forms.CharField(
        label=_("Justificativa clínica (uso interno)"),
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Fica só no sistema da clínica: não aparece no app do paciente."),
    )
    contraindications = forms.CharField(
        label=_("Cuidados e contraindicações (o paciente vê)"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    valid_from = forms.DateField(label=_("Vale a partir de"), widget=_date_widget())
    valid_until = forms.DateField(
        label=_("Vale até (opcional)"), required=False, widget=_date_widget()
    )

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        start: date | None = data.get("valid_from")
        end: date | None = data.get("valid_until")
        if start is not None and end is not None and end < start:
            self.add_error(
                "valid_until", _("A data final não pode ser anterior ao início.")
            )
        return data


class CarePlanActionForm(AeForm):
    description = forms.CharField(label=_("Ação"), max_length=255)
    target_frequency = forms.CharField(
        label=_("Frequência (o paciente vê)"),
        max_length=64,
        help_text=_("Texto livre. Por exemplo: Diária, 3 vezes por semana."),
    )
    guidance = forms.CharField(
        label=_("Orientação (o paciente vê)"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    is_mandatory = forms.BooleanField(label=_("Ação obrigatória"), required=False)


class BaseCarePlanActionFormSet(forms.BaseFormSet):  # type: ignore[type-arg]
    def add_fields(self, form: Any, index: int | None) -> None:
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].label = _("Remover esta ação")

    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return
        if not self.actions_data():
            raise ValidationError(_("Inclua ao menos uma ação no plano."))

    def actions_data(self) -> list[dict[str, Any]]:
        """The kept rows, in screen order, as the service expects them."""
        rows: list[dict[str, Any]] = []
        for form in self.forms:
            data = getattr(form, "cleaned_data", {})
            if not data.get("description") or data.get("DELETE"):
                continue
            rows.append(
                {
                    "description": data["description"],
                    "frequency": data["target_frequency"],
                    "guidance": data.get("guidance", ""),
                    "is_mandatory": data.get("is_mandatory", False),
                }
            )
        return rows


def care_plan_action_formset(*, extra: int) -> type[BaseCarePlanActionFormSet]:
    """Formset class with ``extra`` blank rows (no script: add more by editing)."""
    return forms.formset_factory(  # type: ignore[return-value]
        CarePlanActionForm,
        formset=BaseCarePlanActionFormSet,
        extra=extra,
        max_num=MAX_PLAN_ACTIONS,
        validate_max=True,
        can_delete=True,
        can_delete_extra=False,
    )


# ── Hábitos ─────────────────────────────────────────────────────────────────


class HabitForm(AeForm):
    title = forms.CharField(label=_("Hábito"), max_length=255)
    description = forms.CharField(
        label=_("Descrição (o paciente vê)"),
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    frequency = forms.ChoiceField(label=_("Frequência"), choices=FREQUENCY_CHOICES)
    active_days = forms.MultipleChoiceField(
        label=_("Dias da semana"),
        required=False,
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Vale apenas para a frequência “Dias específicos”."),
    )
    time_window = forms.ChoiceField(
        label=_("Parte do dia"),
        choices=WINDOW_CHOICES,
        help_text=_("Escolha “Horário fixo” para informar a hora exata."),
    )
    target_time = forms.TimeField(
        label=_("Horário (fuso do paciente)"),
        required=False,
        widget=_time_widget(),
        input_formats=["%H:%M", "%H:%M:%S"],
    )
    target_duration_minutes = forms.IntegerField(
        label=_("Duração em minutos (opcional)"),
        required=False,
        min_value=0,
        max_value=MAX_HABIT_MINUTES,
    )

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        frequency = data.get("frequency")
        if frequency == HabitFrequency.SPECIFIC_DAYS and not data.get("active_days"):
            self.add_error("active_days", _("Escolha ao menos um dia da semana."))
        if data.get("time_window") == TimeOfDayWindow.EXACT_TIME and not data.get(
            "target_time"
        ):
            self.add_error("target_time", _("Informe o horário do hábito."))
        return data


__all__ = [
    "AeForm",
    "BaseCarePlanActionFormSet",
    "CarePlanActionForm",
    "CarePlanCloseForm",
    "CarePlanForm",
    "ConfirmForm",
    "HabitForm",
    "HabitPauseForm",
    "MedicationForm",
    "MedicationStopForm",
    "care_plan_action_formset",
    "parse_schedule_times",
]
