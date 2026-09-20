"""Guard application-wide input presentation, including hand-written fields."""

import re
from pathlib import Path

from django.conf import settings

ROOT = Path(settings.BASE_DIR) / "templates"
CONTROL = re.compile(
    r'<(input|select|textarea)\b(?:"[^"]*"|\'[^\']*\'|[^\'">])*>', re.S
)


def test_manual_text_controls_have_icon_wrappers_and_hints() -> None:
    failures = []
    for path in ROOT.rglob("*.html"):
        source = path.read_text()
        for match in CONTROL.finditer(source):
            tag = match.group()
            if re.search(
                r'type=["\'](?:hidden|checkbox|radio|file|color|range|submit|button)["\']',
                tag,
            ):
                continue
            before = source[max(0, match.start() - 250) : match.start()]
            if "field-control-icon" not in before:
                failures.append(f"{path.relative_to(ROOT)}: missing icon: {tag[:100]}")
            needs_hint = match.group(1) != "select" and not re.search(
                r'type=["\'](?:date|time|datetime-local)["\']', tag
            )
            if needs_hint and "placeholder=" not in tag:
                failures.append(f"{path.relative_to(ROOT)}: missing hint: {tag[:100]}")
    assert not failures, "\n".join(failures)


def test_widgets_use_shared_control_or_auth_renderer() -> None:
    allowed = {
        "components/duralux_control.html",
        "components/duralux_field.html",
        "accounts/auth_form.html",
    }
    remaining = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.html")
        if "|accessible_widget" in path.read_text()
        and str(path.relative_to(ROOT)) not in allowed
    ]
    assert not remaining, remaining


def test_shared_form_has_direct_responsive_fields() -> None:
    source = (ROOT / "components/form.html").read_text()
    assert "product-form-grid" in source
    assert '<div class="mb-3">' not in source
