"""Accessible forms for explicit consent decisions."""

from uuid import uuid4

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ConsentManifestation


class ConsentDecisionForm(forms.Form):
    """Require one unambiguous decision without a preselected option."""

    request_id = forms.UUIDField(
        label=_("Identificador da solicitação"),
        widget=forms.HiddenInput,
        initial=uuid4,
        required=True,
    )
    decision = forms.ChoiceField(
        label=_("Sua decisão"),
        choices=(
            (
                ConsentManifestation.Decision.ACCEPTED,
                _("Aceitou"),
            ),
            (
                ConsentManifestation.Decision.REFUSED,
                _("Recusou"),
            ),
        ),
        widget=forms.RadioSelect,
        required=True,
    )


class ConsentRevocationForm(forms.Form):
    """Require an explicit scope confirmation and a reviewable reason."""

    request_id = forms.UUIDField(
        label=_("Identificador da solicitação"),
        widget=forms.HiddenInput,
        initial=uuid4,
        required=True,
    )
    reason = forms.CharField(
        label=_("Reason for revocation"),
        max_length=500,
        min_length=3,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    confirm_scope = forms.BooleanField(
        label=_(
            "I understand that revocation stops future use for this purpose "
            "and does not erase the historical evidence."
        ),
        required=True,
    )
