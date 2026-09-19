"""Localized copy for system-generated content notifications."""

from __future__ import annotations

from collections.abc import Mapping

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import override

_NOTIFICATION_MESSAGES: Mapping[str, str] = {
    "active": "Uma recomendação de conteúdo foi atribuída a você.",
    "retired": "Uma recomendação foi retirada.",
    "content_removed": "Um conteúdo recomendado a você não está mais disponível.",
    "credential_revoked": (
        "Uma recomendação foi retirada (credencial profissional revogada)."
    ),
}


def _catalog_markers() -> tuple[str, ...]:
    """Expose dynamic message IDs to gettext extraction without evaluating them."""
    return (
        _("Uma recomendação de conteúdo foi atribuída a você."),
        _("Uma recomendação foi retirada."),
        _("Um conteúdo recomendado a você não está mais disponível."),
        _("Uma recomendação foi retirada (credencial profissional revogada)."),
    )


def localized_notification_body(*, kind: str, language: str | None) -> str:
    """Return system copy in one valid recipient language.

    The override is scoped to this call so interleaved recipients cannot inherit
    another person's locale. Unknown or empty preferences use the project default.
    """
    available = {code for code, _label in settings.LANGUAGES}
    selected = language if language in available else settings.LANGUAGE_CODE
    with override(selected):
        return _(_NOTIFICATION_MESSAGES[kind])
