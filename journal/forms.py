"""Forms for the emotional journal and check-in domain."""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    CONTEXT_MAX_LENGTH,
    DETAIL_MAX_LENGTH,
    JournalEntry,
)


class JournalEntryForm(forms.Form):
    """Collect one patient diary record in PT-BR with accessibility metadata."""

    mood = forms.TypedChoiceField(
        label=_("Como você está se sentindo?"),
        choices=JournalEntry.Mood.choices,
        coerce=int,
        widget=forms.RadioSelect,
        help_text=_(
            "Selecione como você avalia seu humor geral neste momento "
            "(1 = Muito mal a 5 = Muito bem)."
        ),
        required=True,
    )
    emotions = forms.MultipleChoiceField(
        label=_("Quais emoções você identifica?"),
        choices=JournalEntry.Emotion.choices,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Você pode selecionar mais de uma emoção."),
        required=False,
    )
    intensity = forms.IntegerField(
        label=_("Intensidade emocional (1 a 5)"),
        min_value=1,
        max_value=5,
        initial=3,
        help_text=_("1 = muito leve, 5 = muito intensa"),
        required=True,
    )
    context = forms.CharField(
        label=_("Relato do diário"),
        max_length=CONTEXT_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": _(
                    "Descreva o que aconteceu ou como você está se sentindo..."
                ),
            }
        ),
        help_text=_("Máximo de %(max)d caracteres.") % {"max": CONTEXT_MAX_LENGTH},
        required=True,
    )
    triggers = forms.CharField(
        label=_("Gatilhos"),
        max_length=DETAIL_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": _(
                    "Situações, pensamentos ou eventos que desencadearam este momento"
                    " (opcional)"
                ),
            }
        ),
        help_text=_("Opcional. Máximo de %(max)d caracteres.")
        % {"max": DETAIL_MAX_LENGTH},
        required=False,
    )
    reactions = forms.CharField(
        label=_("Reações físicas"),
        max_length=DETAIL_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": _(
                    "Ex.: tensão muscular, respiração curta, aperto no peito (opcional)"
                ),
            }
        ),
        help_text=_("Opcional. Máximo de %(max)d caracteres.")
        % {"max": DETAIL_MAX_LENGTH},
        required=False,
    )
    strategies = forms.CharField(
        label=_("O que me ajudou"),
        max_length=DETAIL_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": _(
                    "Ações, pensamentos ou técnicas que ajudaram a lidar com a situação"
                    " (opcional)"
                ),
            }
        ),
        help_text=_("Opcional. Máximo de %(max)d caracteres.")
        % {"max": DETAIL_MAX_LENGTH},
        required=False,
    )
    visibility = forms.ChoiceField(
        label=_("Compartilhamento"),
        choices=JournalEntry.Visibility.choices,
        widget=forms.RadioSelect,
        initial=JournalEntry.Visibility.PRIVATE,
        help_text=_(
            "Verde = Compartilhável com terapeuta; Amarelo = Perguntar antes de"
            " compartilhar; Vermelho = Somente eu (privado)."
        ),
        required=True,
    )

    def clean_context(self) -> str:
        value = (self.cleaned_data.get("context") or "").strip()
        if not value:
            raise forms.ValidationError(_("Descreva o relato do diário."))
        if len(value) > CONTEXT_MAX_LENGTH:
            raise forms.ValidationError(
                _("O relato do diário deve ter no máximo %(max)d caracteres.")
                % {"max": CONTEXT_MAX_LENGTH}
            )
        return value

    def clean_triggers(self) -> str:
        value = (self.cleaned_data.get("triggers") or "").strip()
        if len(value) > DETAIL_MAX_LENGTH:
            raise forms.ValidationError(
                _("O campo gatilhos deve ter no máximo %(max)d caracteres.")
                % {"max": DETAIL_MAX_LENGTH}
            )
        return value

    def clean_reactions(self) -> str:
        value = (self.cleaned_data.get("reactions") or "").strip()
        if len(value) > DETAIL_MAX_LENGTH:
            raise forms.ValidationError(
                _("O campo reações deve ter no máximo %(max)d caracteres.")
                % {"max": DETAIL_MAX_LENGTH}
            )
        return value

    def clean_strategies(self) -> str:
        value = (self.cleaned_data.get("strategies") or "").strip()
        if len(value) > DETAIL_MAX_LENGTH:
            raise forms.ValidationError(
                _("O campo estratégias deve ter no máximo %(max)d caracteres.")
                % {"max": DETAIL_MAX_LENGTH}
            )
        return value


class JournalFilterForm(forms.Form):
    """Filter parameters for patient journal history in PT-BR."""

    PERIOD_CHOICES = (
        ("7d", _("Últimos 7 dias")),
        ("30d", _("Últimos 30 dias")),
        ("90d", _("Últimos 90 dias")),
        ("all", _("Todo o histórico")),
    )

    period = forms.ChoiceField(
        label=_("Período"),
        choices=PERIOD_CHOICES,
        required=False,
        initial="30d",
    )
    emotion = forms.ChoiceField(
        label=_("Emoção"),
        choices=[("", _("Todas as emoções")), *JournalEntry.Emotion.choices],
        required=False,
    )
    mood = forms.ChoiceField(
        label=_("Humor"),
        choices=[
            ("", _("Todos os humores")),
            *[(str(val), label) for val, label in JournalEntry.Mood.choices],
        ],
        required=False,
    )
