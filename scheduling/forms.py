"""Forms for scheduling flows, with localized labels."""

from __future__ import annotations

from typing import Any, cast

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ConversationKind, ReminderChannel, ReminderType

DATETIME_INPUT_FORMATS = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]

REMINDER_TYPE_CHOICES = (
    (ReminderType.APPOINTMENT, _("Consulta")),
    (ReminderType.CHECKIN, _("Check-in")),
    (ReminderType.EXERCISE, _("Exercício")),
)
REMINDER_CHANNEL_CHOICES = (
    (ReminderChannel.PUSH, _("Push")),
    (ReminderChannel.EMAIL, _("E-mail")),
)


class AppointmentRequestForm(forms.Form):
    """Collect a patient's consultation request against an open slot."""

    service = forms.ChoiceField(label=_("Tipo de consulta"))
    professional = forms.ChoiceField(label=_("Profissional"))
    unit = forms.ChoiceField(label=_("Unidade"))
    start_at = forms.DateTimeField(
        label=_("Data e horário"),
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1800}),
    )

    def __init__(
        self,
        *args: Any,
        service_choices: list[tuple[str, str]],
        professional_choices: list[tuple[str, str]],
        unit_choices: list[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(forms.ChoiceField, self.fields["service"]).choices = service_choices
        cast(
            forms.ChoiceField, self.fields["professional"]
        ).choices = professional_choices
        cast(forms.ChoiceField, self.fields["unit"]).choices = unit_choices


class AppointmentRescheduleForm(forms.Form):
    """Collect a proposed new start time for one appointment."""

    start_at = forms.DateTimeField(
        label=_("Novo data e horário"),
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": 1800}),
    )


class ReminderPreferenceForm(forms.Form):
    """Collect one patient reminder preference."""

    reminder_type = forms.ChoiceField(
        label=_("Tipo de lembrete"), choices=REMINDER_TYPE_CHOICES
    )
    channel = forms.ChoiceField(label=_("Canal"), choices=REMINDER_CHANNEL_CHOICES)
    enabled = forms.BooleanField(label=_("Ativado"), required=False)
    advance_minutes = forms.IntegerField(label=_("Antecedência (minutos)"), min_value=0)
    silence_start = forms.TimeField(
        label=_("Início do horário de silêncio (opcional)"),
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    silence_end = forms.TimeField(
        label=_("Fim do horário de silêncio (opcional)"),
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    timezone_name = forms.CharField(label=_("Fuso horário"), required=False)
    max_daily = forms.IntegerField(
        label=_("Frequência máxima diária"), min_value=1, max_value=24
    )


class ConversationForm(forms.Form):
    """Collect one conversation's channel, subject and bound participants."""

    kind = forms.ChoiceField(
        label=_("Tipo de conversa"), choices=ConversationKind.choices
    )
    subject = forms.CharField(
        label=_("Assunto (opcional)"), max_length=255, required=False
    )
    participant_ids = forms.MultipleChoiceField(label=_("Participantes"))

    def __init__(
        self, *args: Any, participant_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(
            forms.ChoiceField, self.fields["participant_ids"]
        ).choices = participant_choices


class MessageForm(forms.Form):
    """Collect one immutable message body."""

    body = forms.CharField(
        label=_("Mensagem"),
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Este canal não atende emergências."),
    )


class AppointmentActionForm(forms.Form):
    """Carry an optional reason for cancellation."""

    reason = forms.CharField(
        label=_("Motivo (opcional)"), required=False, max_length=255
    )


class WaitlistEntryForm(forms.Form):
    """Collect one waitlist request with period and unit preference."""

    patient_profile = forms.ChoiceField(label=_("Paciente"))
    unit = forms.ChoiceField(label=_("Unidade"))
    service = forms.ChoiceField(label=_("Serviço"))
    preferred_period = forms.CharField(
        label=_("Período preferido (opcional)"), required=False, max_length=32
    )
    contact_note = forms.CharField(
        label=_("Contato (opcional)"), required=False, max_length=255
    )

    def __init__(
        self,
        *args: Any,
        patient_choices: list[tuple[str, str]],
        unit_choices: list[tuple[str, str]],
        service_choices: list[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(
            forms.ChoiceField, self.fields["patient_profile"]
        ).choices = patient_choices
        cast(forms.ChoiceField, self.fields["unit"]).choices = unit_choices
        cast(forms.ChoiceField, self.fields["service"]).choices = service_choices


class UnitForm(forms.Form):
    """Collect one unit's operational identity."""

    name = forms.CharField(label=_("Nome"), max_length=255)
    timezone_name = forms.CharField(
        label=_("Fuso horário"), initial="America/Sao_Paulo", max_length=64
    )


class RoomForm(forms.Form):
    """Collect one room's name inside a unit."""

    unit = forms.ChoiceField(label=_("Unidade"))
    name = forms.CharField(label=_("Nome"), max_length=255)

    def __init__(
        self, *args: Any, unit_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(forms.ChoiceField, self.fields["unit"]).choices = unit_choices
