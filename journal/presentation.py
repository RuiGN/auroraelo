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

# Short question names for the team's check-in series (the patient sees the long form).
CHECKIN_QUESTION_LABELS = {
    "general_state": _("Estado geral"),
    "anxiety": _("Ansiedade"),
    "sadness": _("Tristeza ou desânimo"),
    "irritability": _("Irritabilidade"),
    "energy": _("Disposição e energia"),
    "sleep_quality": _("Qualidade do sono"),
    "motivation": _("Motivação"),
}

# Request states as the team reads them. Only the patient answers a request.
ACCESS_STATE_LABELS = {
    "pending": _("Aguardando resposta do paciente"),
    "granted": _("Aprovado pelo paciente"),
    "rejected": _("Recusado pelo paciente"),
    "revoked": _("Revogado"),
    "expired": _("Expirado"),
    "none": _("Sem pedido"),
}

# Badge tone per request state (design system badge modifiers).
ACCESS_STATE_TONES = {
    "pending": "warning",
    "granted": "success",
    "rejected": "danger",
    "revoked": "muted",
    "expired": "muted",
    "none": "info",
}


def mood_label(value: int) -> str:
    """Return the translated mood name for one 1-5 mood value."""
    return str(MOOD_LABELS.get(value, _("Registrado")))


def emotion_labels(codes: list[str]) -> list[str]:
    """Return translated emotion names, skipping codes the catalog does not know."""
    return [str(EMOTION_LABELS[code]) for code in codes if code in EMOTION_LABELS]
