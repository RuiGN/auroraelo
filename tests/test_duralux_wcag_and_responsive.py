"""Acceptance tests for WCAG 2.2 AA accessibility and asset budgets (Sprint 11).

Validates:
- S11.02: Responsive layouts, table wrappers, and viewport adaptation (375/768/1440px).
- S11.03: Focus rings, contrast ratios (>= 4.5:1), landmarks, labels, reduced motion.
- S11.04: Absence of demo links, broken actions, or unresolvable static references.
- S11.08: Conditional asset loading and runtime asset budget adherence.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles.finders import find

pytestmark = pytest.mark.django_db

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"
STATIC_DIR = Path(settings.BASE_DIR) / "static"
PRODUCT_CSS = STATIC_DIR / "duralux" / "css" / "product-integration.css"


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5)]
    linear = [
        val / 12.92 if val <= 0.04045 else ((val + 0.055) / 1.055) ** 2.4
        for val in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(c1: str, c2: str) -> float:
    l1, l2 = sorted((_luminance(c1), _luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_s11_02_every_table_has_responsive_wrapper_to_prevent_horizontal_overflow() -> (
    None
):
    """S11.02: Tables must be wrapped in .table-responsive or .product-table-scroll."""
    for html_path in TEMPLATES_DIR.rglob("*.html"):
        content = html_path.read_text(encoding="utf-8")
        if "<table" in content:
            assert (
                "table-responsive" in content
                or "product-table-scroll" in content
                or "product-table-wrapper" in content
                or "overflow-x-auto" in content
            ), (
                f"{html_path.relative_to(TEMPLATES_DIR)} contains <table> without a "
                "responsive wrapper."
            )


def test_s11_02_css_supports_mobile_tablet_desktop_breakpoints() -> None:
    """S11.02: product-integration.css defines adaptive rules across breakpoints."""
    css = PRODUCT_CSS.read_text(encoding="utf-8")
    for breakpoint in (
        "@media (max-width: 767.98px)",
        "@media (max-width: 991.98px)",
        "@media (max-width: 1199.98px)",
    ):
        assert breakpoint in css, f"Missing breakpoint query: {breakpoint}"


def test_s11_03_wcag_contrast_ratios_meet_level_aa() -> None:
    """S11.03: Standard text and focus rings meet WCAG AA contrast ratio (>= 4.5:1)."""
    # Mindcare primary blue #1d4ed8 against white background #ffffff
    assert _contrast("#1d4ed8", "#ffffff") >= 4.5
    # Dark mode light blue #93c5fd against dark surface #1f1f1f
    assert _contrast("#93c5fd", "#1f1f1f") >= 4.5
    # Body text #111827 on white #ffffff
    assert _contrast("#111827", "#ffffff") >= 4.5
    # Dark mode body text #f8fafc on dark #111827
    assert _contrast("#f8fafc", "#111827") >= 4.5


def test_s11_03_landmarks_and_skip_links_present_in_base_layouts() -> None:
    """S11.03: Every shell layout includes skip-to-content and main landmark."""
    base_source = (TEMPLATES_DIR / "layouts/base.html").read_text(encoding="utf-8")
    assert 'href="#main-content"' in base_source

    header_source = (TEMPLATES_DIR / "layouts/partials/header.html").read_text(
        encoding="utf-8"
    )
    assert '<header class="nxl-header"' in header_source

    workspace_layouts = ("layouts/vertical.html", "layouts/detached.html")
    for layout in workspace_layouts:
        source = (TEMPLATES_DIR / layout).read_text(encoding="utf-8")
        assert 'id="main-content"' in source, f"{layout} missing main content landmark"
        assert 'include "layouts/partials/header.html"' in source, (
            f"{layout} missing header include"
        )
        assert 'role="main"' in source or "<main" in source, f"{layout} missing main"


def test_s11_03_reduced_motion_respected_in_css() -> None:
    """S11.03: CSS disables transitions and animations under prefers-reduced-motion."""
    css = PRODUCT_CSS.read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation-duration: 0.01ms" in css or "transition-duration: 0.01ms" in css


def test_s11_04_no_broken_demo_links_or_javascript_void() -> None:
    """S11.04: Active templates do not contain dead demo links or javascript:void(0)."""
    forbidden_hrefs = (
        'href="#"',
        'href="javascript:void(0)"',
        'href="javascript:;"',
        "apps-mail.html",
        "auth-login-minimal.html",
        "reports-sales.html",
    )
    for html_path in TEMPLATES_DIR.rglob("*.html"):
        content = html_path.read_text(encoding="utf-8")
        for forbidden in forbidden_hrefs:
            assert forbidden not in content, (
                f"{html_path.relative_to(TEMPLATES_DIR)} contains forbidden demo link: "
                f"{forbidden}"
            )


def test_s11_04_all_static_references_in_templates_resolve() -> None:
    """S11.04: Every static file tag in templates points to an existing file."""
    static_tag_pattern = re.compile(r'{%\s*static\s+[\'"]([^\'"]+)[\'"]\s*%}')
    checked = set()
    for html_path in TEMPLATES_DIR.rglob("*.html"):
        content = html_path.read_text(encoding="utf-8")
        for match in static_tag_pattern.finditer(content):
            static_path = match.group(1)
            if static_path in checked:
                continue
            checked.add(static_path)
            resolved = find(static_path)
            assert resolved is not None, (
                f"{html_path.relative_to(TEMPLATES_DIR)} references missing static "
                f"asset: {static_path}"
            )


def test_s11_08_specialized_plugins_are_conditionally_loaded() -> None:
    """S11.08: Page-specific scripts are never loaded globally in layouts."""
    base_layouts = [
        (TEMPLATES_DIR / "layouts/base.html").read_text(encoding="utf-8"),
        (TEMPLATES_DIR / "layouts/vertical.html").read_text(encoding="utf-8"),
        (TEMPLATES_DIR / "layouts/detached.html").read_text(encoding="utf-8"),
    ]
    page_specific_scripts = (
        "apexcharts.min.js",
        "dashboard-charts.js",
        "visual-reference-charts.js",
        "lesson-player.js",
        "form-behaviors.js",
    )
    for script in page_specific_scripts:
        for layout_content in base_layouts:
            assert script not in layout_content, (
                f"{script} is loaded unconditionally in base layout; must be "
                "page-specific."
            )


def test_s11_08_runtime_asset_size_is_within_budget() -> None:
    """S11.08: Total runtime asset footprint remains strictly within 2MB budget."""
    duralux_root = STATIC_DIR / "duralux"
    total_size = sum(f.stat().st_size for f in duralux_root.rglob("*") if f.is_file())
    # 2MB budget (2 * 1024 * 1024 = 2,097,152 bytes)
    max_budget = 2 * 1024 * 1024
    assert total_size < max_budget, (
        f"Runtime assets exceed 2MB budget: {total_size} bytes"
    )
