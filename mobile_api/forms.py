"""Formulários do painel da equipe sobre o acesso do paciente ao aplicativo."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _


class ConfirmActionForm(forms.Form):
    """Confirmação explícita e verificada no servidor antes de uma ação irreversível."""

    confirm = forms.BooleanField(
        label=_("Confirmo que quero seguir com esta ação."),
        required=True,
        error_messages={"required": _("Marque a confirmação para continuar.")},
    )
