"""Forms for the configurable daily check-in."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _


def build_checkin_form_fields(
    questions: list[dict[str, object]],
) -> dict[str, forms.Field]:
    """Dynamically build form fields from the active questionnaire."""
    fields: dict[str, forms.Field] = {}
    for question in questions:
        key = str(question.get("key", ""))
        q_type = str(question.get("type", ""))
        label = str(question.get("label", key))
        required = bool(question.get("required", False))

        if q_type == "scale_1_5":
            scale_choices = (
                ("", _("Prefiro não responder")),
                ("1", _("1 — Muito baixo")),
                ("2", _("2 — Baixo")),
                ("3", _("3 — Médio")),
                ("4", _("4 — Alto")),
                ("5", _("5 — Muito alto")),
            )
            fields[key] = forms.TypedChoiceField(
                label=label,
                choices=scale_choices,
                coerce=lambda v: int(v) if v else None,
                empty_value=None,
                required=required,
                widget=forms.RadioSelect,
            )
        elif q_type == "yes_no":
            fields[key] = forms.ChoiceField(
                label=label,
                choices=(
                    ("", _("Prefiro não responder")),
                    ("yes", _("Sim")),
                    ("no", _("Não")),
                    ("prefer_not_to_answer", _("Prefiro não responder")),
                ),
                required=required,
                widget=forms.RadioSelect,
            )
        else:
            fields[key] = forms.CharField(
                label=label,
                required=required,
                max_length=2000,
                widget=forms.Textarea(attrs={"rows": 2}),
                help_text=_("Opcional. Máximo de 2000 caracteres.")
                if not required
                else "",
            )
    return fields


class DailyCheckInForm(forms.Form):
    """Dynamic form rendered from the clinic's active questionnaire."""

    def __init__(
        self, questions: list[dict[str, object]], *args: object, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        for key, field in build_checkin_form_fields(questions).items():
            self.fields[key] = field
