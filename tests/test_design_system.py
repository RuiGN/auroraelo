"""Contracts for the application-owned Duralux asset layer."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.test import Client
from django.urls import reverse

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

STATIC_ROOT = Path(settings.BASE_DIR) / "static"
PRODUCT_CSS_PATH = STATIC_ROOT / "duralux" / "css" / "product-integration.css"


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _staff_with_clinic() -> tuple[User, Clinic]:
    user = UserFactory.create(is_staff=True)
    clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(
        user=user,
        clinic=clinic,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    return user, clinic


def test_duralux_semantic_tokens_and_focus_meet_accessibility_contract() -> None:
    css = PRODUCT_CSS_PATH.read_text(encoding="utf-8").lower()

    assert "--product-primary" in css
    assert "--product-secondary" in css
    assert "--bs-primary: var(--product-primary)" in css
    assert "--bs-secondary: var(--product-secondary)" in css
    assert '[data-bs-theme="light"]' in css
    assert '[data-bs-theme="dark"]' in css
    assert ":focus-visible" in css
    assert "outline: 3px solid var(--product-focus-ring)" in css
    assert _contrast_ratio("#1d4ed8", "#ffffff") >= 4.5
    assert _contrast_ratio("#93c5fd", "#1f1f1f") >= 4.5


def test_duralux_uses_system_fonts_without_external_font_downloads() -> None:
    css = PRODUCT_CSS_PATH.read_text(encoding="utf-8").lower()

    assert "--product-font-sans: system-ui" in css
    assert "@font-face" not in css
    assert "fonts.googleapis.com" not in css


def test_only_allowlisted_application_assets_are_in_static_storage() -> None:
    expected = {
        "duralux/css/bootstrap.min.css",
        "duralux/css/theme.min.css",
        "duralux/css/product-integration.css",
        "duralux/images/favicon.svg",
        "duralux/js/bootstrap.bundle.min.js",
        "duralux/js/product-shell.js",
    }
    promoted = {
        str(path.relative_to(STATIC_ROOT))
        for path in STATIC_ROOT.rglob("*")
        if path.is_file()
    }

    assert expected <= promoted
    # Toda a árvore estática vive em um dos quatro diretórios de aplicação;
    # nada solto na raiz de static/.
    allowed_roots = {"css", "design_system", "duralux", "images"}
    assert all(path.split("/")[0] in allowed_roots for path in promoted)
    assert not any(path.endswith(("user.png",)) for path in promoted)
    assert not any("logo-full" in path or "bg-main" in path for path in promoted)
    assert not any("design_system_duralux" in path for path in promoted)
    for asset in expected:
        assert find(asset) is not None, f"Static finder cannot resolve {asset}"


def test_design_assets_are_application_owned() -> None:
    base_dir = Path(settings.BASE_DIR)
    source = base_dir / "design_system"

    assert source.is_dir()
    assert (source / "css" / "tokens.css").is_file()
    assert PRODUCT_CSS_PATH.is_file()
    assert find("duralux/css/product-integration.css") is not None
    assert not (STATIC_ROOT / "vendor").exists()

    tool_config = (base_dir / "pyproject.toml").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in tool_config


def test_design_system_has_no_legacy_icon_font_dependency() -> None:
    css = PRODUCT_CSS_PATH.read_text(encoding="utf-8").lower()

    assert "@font-face" not in css
    assert not (STATIC_ROOT / "fonts").exists()
    assert "https://" not in css


def test_design_reference_requires_authentication(client: Client) -> None:
    # A referência visual é pública: redireciona para o showcase estático
    # publicado no design_system/ (decisão de produto; a página staff-only
    # com gráficos operacionais foi descontinuada).
    response = client.get(reverse("design_system_reference"))

    assert response.status_code == 302
    assert response.headers["Location"] == "/static/design_system/index.html"


def test_design_reference_rejects_authenticated_non_staff(client: Client) -> None:
    # Qualquer sessão recebe o showcase estático; nenhuma superfície staff
    # ou dados clínicos é exposta na referência visual.
    user = UserFactory.create(is_staff=False)
    clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(user=user, clinic=clinic)
    client.force_login(user)

    response = client.get(
        reverse("design_system_reference"),
        headers={"X-Clinic-ID": str(clinic.pk)},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/static/design_system/index.html"


def test_design_reference_uses_normal_tenant_resolution(client: Client) -> None:
    # O showcase não contorna o middleware de tenant: sessões autenticadas
    # sem clínica ativa continuam sujeitas à resolução normal (400), igual
    # a qualquer outra rota da plataforma.
    user = UserFactory.create(is_staff=True)
    client.force_login(user)

    response = client.get(reverse("design_system_reference"))

    assert response.status_code == 400
    assert response.json()["detail"] == "Selecione uma clínica para continuar."


def test_design_reference_is_pt_br_accessible_and_demo_free(client: Client) -> None:
    # O showcase estático deve refletir exatamente o pacote design_system/:
    # pt-BR, identidade Aurora Elo e nenhuma referência ao pacote legado
    # design_system_duralux nem ao chrome duralux (nxl-*/product-auth).
    showcase = STATIC_ROOT / "design_system" / "index.html"
    content = showcase.read_text(encoding="utf-8")
    lowered = content.lower()

    assert find("design_system/index.html") is not None
    assert '<html lang="pt-br"' in lowered
    assert "Aurora Elo" in content
    assert "john doe" not in lowered
    assert "logo-dark.svg" not in lowered
    assert "design_system_duralux" not in lowered
    assert "nxl-" not in lowered
    assert "product-auth" not in lowered
    assert "fundação duralux" not in lowered


def test_static_showcase_matches_the_design_system_package() -> None:
    # Anti-deriva: as páginas publicadas são cópias byte-a-byte do pacote de
    # referência. Exceções documentadas: css/tokens.css e css/custom.css são
    # variantes de runtime consumidas pelo build compilado (aurora.css).
    package = Path(settings.BASE_DIR) / "design_system"
    showcase = STATIC_ROOT / "design_system"

    synced = [
        "index.html",
        "login.html",
        "mobile-b2c.html",
        "mobile-connected.html",
        "package.json",
        "tailwind.config.js",
        "README.md",
        "js/app.js",
        "js/i18n.js",
        "js/masks.js",
    ]
    for name in synced:
        assert (showcase / name).read_bytes() == (package / name).read_bytes(), name
    for component in sorted((package / "components").glob("*.html")):
        assert (
            (showcase / "components" / component.name).read_bytes()
            == component.read_bytes()
        )
    for image in sorted((package / "assets" / "images").glob("*")):
        assert (
            (showcase / "assets" / "images" / image.name).read_bytes()
            == image.read_bytes()
        )

    compiled = showcase / "css" / "aurora.css"
    assert compiled.is_file() and compiled.stat().st_size > 1024
    compiled_text = compiled.read_text(encoding="utf-8").lower()
    assert "fonts.googleapis.com" not in compiled_text
    assert "@theme" not in compiled_text


def test_app_shells_have_no_duralux_chrome() -> None:
    # A camada de compatibilidade legada permanece apenas para conteúdo
    # (Bootstrap/formulários/tabelas); o chrome do shell — login, sidebar e
    # header — usa exclusivamente o design system Aurora Elo.
    chrome = [
        "templates/accounts/auth_base.html",
        "templates/accounts/auth_form.html",
        "templates/accounts/auth_message.html",
        "templates/components/language_selector.html",
        "templates/layouts/base.html",
        "templates/layouts/vertical.html",
        "templates/layouts/detached.html",
        "templates/layouts/partials/header.html",
        "templates/layouts/partials/navigation.html",
    ]
    banned = (
        "nxl-",
        "product-auth",
        "product-shell.js",
        "language-selector.js",
        "minimal-card",
    )
    base_dir = Path(settings.BASE_DIR)
    for template in chrome:
        text = (base_dir / template).read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{template} ainda referencia {token}"
    # O login não pode carregar CSS do tema legado.
    auth = (base_dir / "templates" / "accounts" / "auth_base.html").read_text(
        encoding="utf-8"
    )
    assert "duralux/css/auth.css" not in auth
    assert "duralux/css/theme.min.css" not in auth
    assert "duralux/css/product-integration.css" not in auth
