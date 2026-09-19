"""Catch shared-template syntax failures before database-heavy HTTP tests."""

from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import get_template, render_to_string
from django.utils.translation import override

TEMPLATE_NAMES = sorted(
    path.relative_to(Path(settings.BASE_DIR) / "templates").as_posix()
    for path in (Path(settings.BASE_DIR) / "templates").rglob("*.html")
)


@pytest.mark.parametrize("template_name", TEMPLATE_NAMES)
def test_application_template_compiles(template_name: str) -> None:
    """Every application template must be accepted by Django's actual parser."""
    get_template(template_name)


def test_summary_card_renders_the_danger_branch() -> None:
    """Broken multiline elif tags must not silently select a neutral icon."""
    html = render_to_string(
        "components/summary_card.html",
        {"card": {"id": "urgent", "tone": "danger", "title": "Atenção", "value": 2}},
    )
    assert "feather-alert-octagon" in html
    assert "{%" not in html


@pytest.mark.parametrize(
    ("language", "count", "expected"),
    (
        ("pt-br", 1, "1 revogação operacional pendente"),
        ("pt-br", 2, "2 revogações operacionais pendentes"),
        ("en", 1, "1 pending operational revocation"),
        ("en", 2, "2 pending operational revocations"),
        ("es", 1, "1 revocación operativa pendiente"),
        ("es", 2, "2 revocaciones operativas pendientes"),
    ),
)
def test_navigation_renders_pending_revocation_count(
    language: str, count: int, expected: str
) -> None:
    """The navigation must render the localized singular or plural count."""
    with override(language):
        html = render_to_string(
            "layouts/partials/navigation.html",
            {"pending_consent_revocation_count": count},
        )

    assert expected in html
    assert "{{" not in html
