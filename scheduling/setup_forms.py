"""Forms of the clinic setup screens: services and weekly availability."""

from __future__ import annotations

from typing import Any, cast

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .catalog_services import (
    MAX_BUFFER_MINUTES,
    MAX_DURATION_MINUTES,
    MAX_NAME_LENGTH,
    MIN_DURATION_MINUTES,
)
from .operating_hours import WEEKDAY_LABELS

WEEKDAY_CHOICES = [(str(index), label) for index, label in enumerate(WEEKDAY_LABELS)]


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
            classes = str(widget.attrs.get("class", "")).split()
            if css not in classes:
                widget.attrs["class"] = " ".join([*classes, css])


class AeForm(AeFormMixin, forms.Form):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.apply_design_system()


def _set_choices(
    form: forms.Form, name: str, choices: list[tuple[str, str]], *, blank: str = ""
) -> None:
    field = cast(forms.ChoiceField, form.fields[name])
    field.choices = [("", blank), *choices] if blank else choices


class ServiceForm(AeForm):
    """Name and timing of one bookable service."""

    name = forms.CharField(label=_("Nome do serviço"), max_length=MAX_NAME_LENGTH)
    duration_minutes = forms.IntegerField(
        label=_("Duração da consulta (minutos)"),
        min_value=MIN_DURATION_MINUTES,
        max_value=MAX_DURATION_MINUTES,
        initial=50,
    )
    buffer_minutes = forms.IntegerField(
        label=_("Intervalo entre consultas (minutos)"),
        min_value=0,
        max_value=MAX_BUFFER_MINUTES,
        initial=10,
        help_text=_(
            "Somado à duração para calcular os horários que o paciente vê no "
            "aplicativo. Consultas já marcadas não mudam."
        ),
    )


class ConfirmForm(AeForm):
    """Form without fields: the page only asks for an explicit confirmation."""


class AvailabilityBaseForm(AeForm):
    """Fields shared by creating and editing a weekly availability window."""

    unit = forms.ChoiceField(label=_("Unidade"))
    room = forms.ChoiceField(
        label=_("Sala (opcional)"),
        required=False,
        help_text=_("Deixe em branco quando qualquer sala da unidade puder ser usada."),
    )
    start_time = forms.TimeField(label=_("Início"), widget=_time_widget())
    end_time = forms.TimeField(label=_("Fim"), widget=_time_widget())
    valid_from = forms.DateField(
        label=_("Vale a partir de"), widget=_date_widget(), initial=timezone.localdate
    )
    valid_until = forms.DateField(
        label=_("Vale até (opcional)"),
        required=False,
        widget=_date_widget(),
        help_text=_("Deixe em branco para valer por tempo indeterminado."),
    )

    def __init__(
        self,
        *args: Any,
        unit_choices: list[tuple[str, str]],
        room_choices: list[tuple[str, str]],
        room_units: dict[str, str],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.room_units = room_units
        _set_choices(self, "unit", unit_choices, blank=str(_("Selecione a unidade")))
        _set_choices(self, "room", room_choices, blank=str(_("Qualquer sala")))
        self.apply_design_system()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start is not None and end is not None and start >= end:
            self.add_error("end_time", _("O fim deve ser depois do início."))
        valid_from, valid_until = cleaned.get("valid_from"), cleaned.get("valid_until")
        if valid_from and valid_until and valid_until < valid_from:
            self.add_error(
                "valid_until", _("A data final não pode ser anterior à inicial.")
            )
        room, unit = cleaned.get("room"), cleaned.get("unit")
        if room and unit and self.room_units.get(room) != unit:
            self.add_error("room", _("Esta sala não pertence à unidade escolhida."))
        return cleaned


class AvailabilityCreateForm(AvailabilityBaseForm):
    """Create the same window on one or more weekdays for one professional."""

    professional = forms.ChoiceField(label=_("Profissional"))
    weekdays = forms.MultipleChoiceField(
        label=_("Dias da semana"),
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Marque todos os dias em que este horário se repete."),
    )
    field_order = [
        "professional",
        "unit",
        "room",
        "weekdays",
        "start_time",
        "end_time",
        "valid_from",
        "valid_until",
    ]

    def __init__(
        self, *args: Any, professional_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        _set_choices(
            self,
            "professional",
            professional_choices,
            blank=str(_("Selecione o profissional")),
        )


class AvailabilityUpdateForm(AvailabilityBaseForm):
    """Edit one window; the professional stays the same (remove and recreate)."""

    weekday = forms.ChoiceField(label=_("Dia da semana"), choices=WEEKDAY_CHOICES)
    field_order = [
        "unit",
        "room",
        "weekday",
        "start_time",
        "end_time",
        "valid_from",
        "valid_until",
    ]


class PreviewFilterForm(AeForm):
    """Which service and professional to preview free slots for."""

    service = forms.ChoiceField(label=_("Serviço"))
    professional = forms.ChoiceField(label=_("Profissional"), required=False)

    def __init__(
        self,
        *args: Any,
        service_choices: list[tuple[str, str]],
        professional_choices: list[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        _set_choices(self, "service", service_choices)
        _set_choices(
            self,
            "professional",
            professional_choices,
            blank=str(_("Todos os profissionais")),
        )
        self.apply_design_system()
