"""Formulários do concierge, com rótulos localizados e classes do design system."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from .contracts import (
    CALL_OUTCOMES,
    MAX_RULE_STEPS,
    VISIT_OUTCOMES,
    ContactKind,
    ContactOutcome,
    LogChannel,
    LogDirection,
    RequestKind,
    ResponsibleRole,
)

DATETIME_INPUT_FORMATS = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]


def _date_widget() -> forms.DateInput:
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class AeFormMixin:
    """Aplica as classes do design system (`ae-input`, `ae-select`, `ae-textarea`)."""

    fields: dict[str, forms.Field]

    def apply_design_system(self) -> None:
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
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


# ── Alta ────────────────────────────────────────────────────────────────────


class DischargeForm(AeForm):
    patient = forms.ChoiceField(label=_("Paciente"))
    discharge_date = forms.DateField(label=_("Data da alta"), widget=_date_widget())
    notes = forms.CharField(
        label=_("Observações administrativas"),
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("Não registre conteúdo clínico. Máximo de 500 caracteres."),
    )

    def __init__(
        self, *args: Any, patient_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["patient"].choices = [  # type: ignore[attr-defined]
            ("", _("Selecione um paciente")),
            *patient_choices,
        ]
        self.apply_design_system()


class ReasonForm(AeForm):
    """Motivo curto exigido para cancelar ou corrigir."""

    reason = forms.CharField(
        label=_("Motivo"),
        min_length=3,
        max_length=255,
        widget=forms.TextInput(),
    )


class CompleteContactForm(AeForm):
    outcome = forms.ChoiceField(label=_("Resultado"))
    family_contact = forms.ChoiceField(
        label=_("Familiar contatado (opcional)"),
        required=False,
        help_text=_("Escolha apenas se o contato foi com um familiar autorizado."),
    )
    notes = forms.CharField(
        label=_("Observações"),
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Não registre conteúdo clínico. Máximo de 1000 caracteres."),
    )

    def __init__(
        self,
        *args: Any,
        kind: str,
        family_choices: list[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        allowed = CALL_OUTCOMES if kind == ContactKind.CALL else VISIT_OUTCOMES
        self.fields["outcome"].choices = [  # type: ignore[attr-defined]
            (value, label)
            for value, label in ContactOutcome.choices
            if value in allowed
        ]
        self.fields["family_contact"].choices = [  # type: ignore[attr-defined]
            ("", _("Nenhum (contato com o paciente)")),
            *family_choices,
        ]
        self.apply_design_system()


class RescheduleForm(AeForm):
    new_due_date = forms.DateField(label=_("Nova data"), widget=_date_widget())
    reason = forms.CharField(label=_("Motivo"), min_length=3, max_length=255)


class MissedForm(AeForm):
    notes = forms.CharField(
        label=_("Motivo de não ter sido realizado"),
        min_length=3,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


# ── Família ─────────────────────────────────────────────────────────────────


class FamilyContactForm(AeForm):
    full_name = forms.CharField(label=_("Nome completo"), max_length=255)
    relationship = forms.CharField(label=_("Parentesco"), max_length=100)
    phone = forms.CharField(label=_("Telefone"), required=False, max_length=32)
    email = forms.EmailField(label=_("E-mail"), required=False)
    is_primary = forms.BooleanField(label=_("Contato principal"), required=False)


class NewFamilyContactForm(FamilyContactForm):
    consent_to_contact = forms.BooleanField(
        label=_("O paciente autorizou o contato com este familiar"),
        required=False,
    )
    consent_note = forms.CharField(
        label=_("Como a autorização foi obtida"),
        required=False,
        max_length=255,
        help_text=_("Ex.: termo assinado em 01/10. Obrigatório se autorizado."),
    )


class FamilyConsentForm(AeForm):
    decision = forms.ChoiceField(
        label=_("Decisão do paciente"),
        choices=[
            ("grant", _("Autoriza o contato com este familiar")),
            ("revoke", _("Revoga a autorização de contato")),
        ],
    )
    note = forms.CharField(
        label=_("Como a decisão foi obtida"),
        min_length=3,
        max_length=255,
        help_text=_("Ex.: termo assinado, pedido verbal registrado em consulta."),
    )


# ── Registro e pedidos ──────────────────────────────────────────────────────


class LogForm(AeForm):
    family_contact = forms.ChoiceField(label=_("Familiar"))
    channel = forms.ChoiceField(label=_("Canal"), choices=LogChannel.choices)
    direction = forms.ChoiceField(label=_("Sentido"), choices=LogDirection.choices)
    occurred_at = forms.DateTimeField(
        label=_("Data e hora do contato"),
        required=False,
        input_formats=DATETIME_INPUT_FORMATS,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text=_("Deixe em branco para usar agora."),
    )
    summary = forms.CharField(
        label=_("O que foi tratado"),
        min_length=3,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=_("Não registre conteúdo clínico nem informações de saúde."),
    )

    def __init__(
        self, *args: Any, family_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["family_contact"].choices = family_choices  # type: ignore[attr-defined]
        self.apply_design_system()


class CorrectLogForm(AeForm):
    new_summary = forms.CharField(
        label=_("Texto corrigido"),
        min_length=3,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    reason = forms.CharField(
        label=_("Motivo da correção"), min_length=3, max_length=255
    )


class FamilyRequestForm(AeForm):
    family_contact = forms.ChoiceField(label=_("Familiar"))
    kind = forms.ChoiceField(
        label=_("O que o paciente pediu"), choices=RequestKind.choices
    )
    description = forms.CharField(
        label=_("Detalhes do pedido"),
        min_length=3,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(
        self, *args: Any, family_choices: list[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["family_contact"].choices = family_choices  # type: ignore[attr-defined]
        self.apply_design_system()


class ForwardRequestForm(AeForm):
    channel = forms.ChoiceField(label=_("Canal usado"), choices=LogChannel.choices)
    summary = forms.CharField(
        label=_("O que foi dito à família"),
        min_length=3,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class ResolveRequestForm(AeForm):
    outcome = forms.ChoiceField(
        label=_("Desfecho"),
        choices=[("fulfilled", _("Atendido")), ("declined", _("Não atendido"))],
    )
    note = forms.CharField(label=_("Observação"), min_length=3, max_length=500)


# ── Régua ───────────────────────────────────────────────────────────────────


class RuleForm(AeForm):
    """Nome da régua e até oito etapas (tipo, dias após a alta e responsável)."""

    name = forms.CharField(label=_("Nome da régua"), min_length=3, max_length=120)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for index in range(MAX_RULE_STEPS):
            self.fields[f"step_{index}_kind"] = forms.ChoiceField(
                label=_("Tipo da etapa %(number)d") % {"number": index + 1},
                required=False,
                choices=[("", _("— sem etapa —")), *ContactKind.choices],
            )
            self.fields[f"step_{index}_day"] = forms.IntegerField(
                label=_("Dias após a alta (etapa %(number)d)") % {"number": index + 1},
                required=False,
                min_value=1,
                max_value=365,
            )
            self.fields[f"step_{index}_role"] = forms.ChoiceField(
                label=_("Responsável (etapa %(number)d)") % {"number": index + 1},
                required=False,
                choices=ResponsibleRole.choices,
                initial=ResponsibleRole.ADMINISTRATIVE_STAFF,
            )
        self.apply_design_system()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        steps: list[dict[str, Any]] = []
        for index in range(MAX_RULE_STEPS):
            kind = cleaned.get(f"step_{index}_kind")
            day = cleaned.get(f"step_{index}_day")
            if not kind and day is None:
                continue
            if not kind or day is None:
                raise forms.ValidationError(
                    _("Preencha o tipo e os dias da etapa %(number)d.")
                    % {"number": index + 1}
                )
            steps.append(
                {
                    "kind": kind,
                    "day": day,
                    "responsible_role": cleaned.get(f"step_{index}_role")
                    or ResponsibleRole.ADMINISTRATIVE_STAFF.value,
                }
            )
        if not steps:
            raise forms.ValidationError(_("A régua precisa ter ao menos uma etapa."))
        cleaned["steps"] = steps
        return cleaned
