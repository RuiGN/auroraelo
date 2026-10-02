"""Design system Aurora Elo no web: ativos, layout e conformidade com a CSP."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory

from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

STATIC = Path(settings.BASE_DIR) / "static"
AE = STATIC / "aurora_elo"
DESIGN_SYSTEM_CSS = (
    Path(settings.BASE_DIR).parent / "auroraelo_design_system/static/css/aurora-elo.css"
)


def test_design_system_assets_are_vendored_inside_the_repository() -> None:
    required = [
        "css/aurora-elo.css",
        "css/aurora-elo-fonts.css",
        "css/aurora-elo-extras.css",
        "js/aurora-elo.js",
        "js/theme-init.js",
        "js/language-select.js",
        "img/aurora-elo-mark.png",
        "img/aurora-elo-mark-160.png",
        "img/aurora-elo-horizontal-light.png",
        "img/aurora-elo-horizontal-dark.png",
        "fonts/Manrope-Medium.ttf",
        "fonts/Manrope-SemiBold.ttf",
        "fonts/Manrope-Bold.ttf",
        "fonts/Manrope-ExtraBold.ttf",
        "fonts/LICENSE-OFL.txt",
    ]
    assert [name for name in required if not (AE / name).is_file()] == []


def test_tokens_come_from_the_design_system_not_hand_edited() -> None:
    css = (AE / "css/aurora-elo.css").read_text()
    for token in ("#0d3665", "#2072ab", "#58abdf", "#0a2342", "#f3f7fb", "#b3261e"):
        assert token in css
    assert 'data-theme="dark"' in css
    if DESIGN_SYSTEM_CSS.is_file():  # a pasta do design system fica fora do checkout
        assert css == DESIGN_SYSTEM_CSS.read_text()


def test_extras_stylesheet_uses_only_design_tokens() -> None:
    extras = (AE / "css/aurora-elo-extras.css").read_text()
    # Cores só por variável (var(--...)): nada de hex solto, para herdar claro/escuro.
    assert re.findall(r"#[0-9a-fA-F]{3,8}\b", extras) == []


def test_fonts_are_self_hosted_for_the_content_security_policy() -> None:
    fonts = (AE / "css/aurora-elo-fonts.css").read_text()
    assert "fonts.googleapis.com" not in fonts and "http" not in fonts
    assert fonts.count("@font-face") == 4
    assert "font-src 'self'" in settings.CONTENT_SECURITY_POLICY


def test_legacy_brand_image_is_the_new_logo() -> None:
    horizontal = STATIC / "images/aurora-elo-horizontal.png"
    header = horizontal.read_bytes()[:24]
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    assert abs(width / height - 1505 / 396) < 0.05  # proporção do logo do design system
    assert (AE / "img/aurora-elo-mark.png").read_bytes() == (
        STATIC / "images/aurora-elo-emblem.png"
    ).read_bytes(), "o emblema do produto deve ser a logo.png fornecida"


@pytest.mark.django_db
def test_layout_renders_without_inline_scripts_or_external_resources() -> None:
    clinic = ClinicFactory.create()
    membership = ClinicMembershipFactory.create(clinic=clinic, role="clinic_admin")
    request = RequestFactory().get("/")
    request.user = membership.user
    request.clinic = clinic  # type: ignore[attr-defined]
    html = render_to_string(
        "layouts/aurora_elo.html", {"page_title": "Teste"}, request=request
    )
    inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html)
    assert inline == [], "a CSP (script-src 'self') bloqueia scripts inline"
    assert not re.search(r"(?:src|href)=[\"']https?://", html)
    assert "fonts.googleapis.com" not in html
    assert 'class="ae-navbar"' in html and "data-ae-navbar" in html
    assert "aurora_elo/img/aurora-elo-mark-160.png" in html
    assert "data-ae-theme-toggle" in html
    assert "Teste · Aurora Elo" in html


@pytest.mark.django_db
def test_layout_marks_the_page_language_and_offers_logout_by_post() -> None:
    user = UserFactory.create()
    request = RequestFactory().get("/")
    request.user = user
    request.clinic = None  # type: ignore[attr-defined]
    html = render_to_string("layouts/aurora_elo.html", {}, request=request)
    assert re.search(r'<html lang="[a-z-]+">', html)
    assert 'action="/accounts/logout/"' in html and 'method="post"' in html
