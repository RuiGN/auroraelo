"""Tests for recipient-scoped notification localization."""

from __future__ import annotations

from django.test import override_settings
from django.utils.translation import get_language, override

from content.notification_copy import localized_notification_body

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_notification_copy_uses_recipient_language_and_restores_context() -> None:
    with override("pt-br"):
        before = get_language()
        english = localized_notification_body(kind="active", language="en")
        spanish = localized_notification_body(kind="active", language="es")
        assert english == "A content recommendation was assigned to you."
        assert spanish == "Se te ha asignado una recomendación de contenido."
        assert get_language() == before


def test_notification_copy_falls_back_for_invalid_language() -> None:
    with override("en"):
        assert localized_notification_body(kind="retired", language="invalid") == (
            "Uma recomendação foi retirada."
        )
