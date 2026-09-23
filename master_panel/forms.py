"""Forms for global Master Panel user and membership administration."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.forms import translated_membership_role_choices
from clinics.models import Clinic, ClinicMembership
from people.models import ProfessionalProfile

_CATEGORY_UI_LABELS = {
    "psychologist": _("Psicologia"),
    "psychiatrist": _("Psiquiatria"),
    "therapist": _("Terapia"),
    "other": _("Outra categoria"),
}


def _translated_category_choices() -> tuple[tuple[str, object], ...]:
    """Keep stable category codes while translating their presentation labels."""
    return tuple(
        (value, _CATEGORY_UI_LABELS.get(value, label))
        for value, label in ProfessionalProfile.Category.choices
    )


class MasterUserInviteForm(forms.Form):
    """Collect bounded membership data without collecting or creating passwords."""

    recipient_email = forms.EmailField(label=_("E-mail"), max_length=254)
    clinic = forms.ModelChoiceField(
        label=_("Clínica"),
        queryset=Clinic.infrastructure_objects.all().order_by("name", "pk"),
    )
    initial_role = forms.ChoiceField(
        label=_("Papel"),
        choices=translated_membership_role_choices(),
    )
    initial_category = forms.ChoiceField(
        label=_("Categoria profissional"),
        choices=(("", _("Não se aplica")), *_translated_category_choices()),
        required=False,
    )
    unit_name = forms.CharField(label=_("Unidade"), max_length=120, required=False)
    valid_from = forms.DateField(
        label=_("Início da validade"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    valid_until = forms.DateField(
        label=_("Fim da validade"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    expires_in_hours = forms.IntegerField(
        label=_("Validade do convite em horas"),
        min_value=1,
        max_value=168,
        initial=24,
    )

    def clean(self) -> dict[str, Any]:
        """Keep category semantics and validity dates explicit."""
        cleaned = dict(super().clean() or {})
        role = cleaned.get("initial_role")
        category = cleaned.get("initial_category")
        if category and role != ClinicMembership.Role.THERAPIST:
            self.add_error(
                "initial_category",
                _("A categoria profissional exige o papel Terapeuta."),
            )
        valid_from = cleaned.get("valid_from")
        valid_until = cleaned.get("valid_until")
        if valid_from and valid_until and valid_until < valid_from:
            self.add_error(
                "valid_until",
                _("A validade final não pode ser anterior à inicial."),
            )
        return cleaned


class MasterMembershipForm(forms.Form):
    """Edit one existing membership without exposing credential fields."""

    role = forms.ChoiceField(
        label=_("Papel"),
        choices=translated_membership_role_choices(),
    )
    category = forms.ChoiceField(
        label=_("Categoria profissional"),
        choices=(("", _("Não se aplica")), *_translated_category_choices()),
        required=False,
    )
    unit_name = forms.CharField(label=_("Unidade"), max_length=120, required=False)
    valid_from = forms.DateField(
        label=_("Início da validade"), widget=forms.DateInput(attrs={"type": "date"})
    )
    valid_until = forms.DateField(
        label=_("Fim da validade"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    is_active = forms.BooleanField(label=_("Vínculo ativo"), required=False)

    def clean(self) -> dict[str, Any]:
        """Validate category and membership date semantics."""
        cleaned = dict(super().clean() or {})
        if (
            cleaned.get("category")
            and cleaned.get("role") != ClinicMembership.Role.THERAPIST
        ):
            self.add_error("category", _("A categoria exige o papel Terapeuta."))
        valid_from = cleaned.get("valid_from")
        valid_until = cleaned.get("valid_until")
        if valid_from and valid_until and valid_until < valid_from:
            self.add_error("valid_until", _("A validade final é inválida."))
        return cleaned
