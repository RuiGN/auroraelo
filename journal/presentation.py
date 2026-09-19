"""Translated display labels kept separate from persisted journal codes."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

MOOD_LABELS = {
    1: _("Muito mal"),
    2: _("Mal"),
    3: _("Neutro"),
    4: _("Bem"),
    5: _("Muito bem"),
}

EMOTION_LABELS = {
    "anxiety": _("Ansiedade"),
    "sadness": _("Tristeza"),
    "anger": _("Raiva"),
    "joy": _("Alegria"),
    "fear": _("Medo"),
    "calm": _("Calma"),
    "frustration": _("Frustração"),
    "hope": _("Esperança"),
}

VISIBILITY_LABELS = {
    "shareable": _("Verde — Compartilhável"),
    "confirmation_required": _("Amarelo — Confirmação necessária"),
    "private": _("Vermelho — Privado"),
}
