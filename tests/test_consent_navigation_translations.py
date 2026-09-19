"""Consent notifications use the active locale in both navigation surfaces."""

import pytest
from django.template.loader import render_to_string
from django.utils.translation import override


@pytest.mark.parametrize(
    ("language", "singular", "plural"),
    (
        (
            "pt-br",
            "1 revogação operacional pendente",
            "2 revogações operacionais pendentes",
        ),
        (
            "en",
            "1 pending operational revocation",
            "2 pending operational revocations",
        ),
        (
            "es",
            "1 revocación operativa pendiente",
            "2 revocaciones operativas pendientes",
        ),
    ),
)
@pytest.mark.parametrize("count", (1, 2))
def test_sidebar_revocation_notification_uses_localized_plural(
    language: str, singular: str, plural: str, count: int
) -> None:
    with override(language):
        content = render_to_string(
            "layouts/partials/navigation.html",
            {"pending_consent_revocation_count": count},
        )
    assert f"<span>{singular if count == 1 else plural}</span>" in content


def test_sidebar_without_revocations_has_no_notification() -> None:
    content = render_to_string(
        "layouts/partials/navigation.html", {"pending_consent_revocation_count": 0}
    )
    assert 'role="status"' not in content
