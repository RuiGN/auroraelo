"""Translated display labels kept separate from persisted goals codes."""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

GOAL_STATUS_LABELS = {
    "active": _("Ativa"),
    "paused": _("Pausada"),
    "completed": _("Concluída"),
    "archived": _("Arquivada"),
}

GOAL_PRIORITY_LABELS = {
    1: _("Baixa"),
    2: _("Média"),
    3: _("Alta"),
}

GOAL_HORIZON_LABELS = {
    "short": _("Curto prazo"),
    "medium": _("Médio prazo"),
    "long": _("Longo prazo"),
}

GOAL_VISIBILITY_LABELS = {
    "shareable": _("Verde — Compartilhável"),
    "confirmation_required": _("Amarelo — Confirmar antes"),
    "private": _("Vermelho — Privado"),
}

EXERCISE_STATUS_LABELS = {
    "draft": _("Rascunho"),
    "published": _("Publicado"),
    "archived": _("Arquivado"),
}

EXERCISE_RESPONSE_FORMAT_LABELS = {
    "text": _("Texto livre"),
    "scale_1_5": _("Escala de 1 a 5"),
    "single_choice": _("Escolha única"),
    "multiple_choice": _("Múltipla escolha"),
}

ASSIGNMENT_STATUS_LABELS = {
    "assigned": _("Atribuído"),
    "completed": _("Concluído"),
    "cancelled": _("Cancelado"),
}

EXERCISE_VISIBILITY_LABELS = {
    "shareable": _("Verde (compartilhado)"),
    "confirmation_required": _("Amarelo (perguntar antes)"),
    "private": _("Vermelho (somente eu)"),
}
