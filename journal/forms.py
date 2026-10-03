"""Formulários da equipe para o diário compartilhado pelo paciente."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

PURPOSE_MIN_LENGTH = 10
PURPOSE_MAX_LENGTH = 255
DEFAULT_VALIDITY_DAYS = "30"
# Validade pedida ao paciente: sempre limitada, nunca "sem prazo".
VALIDITY_DAY_CHOICES = (
    ("7", _("7 dias")),
    ("15", _("15 dias")),
    ("30", _("30 dias")),
    ("60", _("60 dias")),
    ("90", _("90 dias")),
)
PERIOD_CHOICES = (
    ("7d", _("Últimos 7 dias")),
    ("30d", _("Últimos 30 dias")),
    ("90d", _("Últimos 90 dias")),
    ("todos", _("Todo o período")),
)
CHECKIN_WINDOW_CHOICES = (
    ("14", _("Últimos 14 dias")),
    ("30", _("Últimos 30 dias")),
)


class AccessRequestForm(forms.Form):
    """Pedido da equipe para ver um registro "perguntar antes"."""

    purpose = forms.CharField(
        label=_("Finalidade do pedido"),
        min_length=PURPOSE_MIN_LENGTH,
        max_length=PURPOSE_MAX_LENGTH,
        help_text=_(
            "O paciente lê este texto no aplicativo antes de decidir. Explique "
            "para que você precisa do registro e não inclua conteúdo clínico."
        ),
    )
    validity_days = forms.ChoiceField(
        label=_("Validade do acesso, se o paciente aprovar"),
        choices=VALIDITY_DAY_CHOICES,
        initial=DEFAULT_VALIDITY_DAYS,
        help_text=_(
            "Conta a partir de hoje. O paciente pode escolher outro prazo ao responder."
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["purpose"].widget.attrs["class"] = "ae-input"
        self.fields["purpose"].widget.attrs["maxlength"] = PURPOSE_MAX_LENGTH
        self.fields["validity_days"].widget.attrs["class"] = "ae-select"


class DiaryFilterForm(forms.Form):
    """Período do diário (o padrão é curto: a equipe lê o mínimo necessário)."""

    periodo = forms.ChoiceField(
        label=_("Período"), choices=PERIOD_CHOICES, required=False
    )


class CheckInWindowForm(forms.Form):
    """Janela da série de check-ins."""

    dias = forms.ChoiceField(
        label=_("Janela"), choices=CHECKIN_WINDOW_CHOICES, required=False
    )
