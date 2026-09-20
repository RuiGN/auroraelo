"""Contrato renderizado do design system local, sem compilação no navegador."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from pytest_django.fixtures import SettingsWrapper


class AssetsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script":
            src = attributes.get("src", "")
            assert isinstance(src, str)
            self.scripts.append(src)
        if tag == "link" and attributes.get("rel") == "stylesheet":
            href = attributes["href"]
            assert isinstance(href, str)
            self.styles.append(href)


def test_container_build_compiles_the_design_system() -> None:
    dockerfile = Path(settings.BASE_DIR, "Dockerfile").read_text()
    assert "AS ui-build" in dockerfile
    assert "npm ci --ignore-scripts --no-audit --no-fund" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert (
        "COPY --from=ui-build /app/static/design_system/css/aurora.css "
        "/app/static/design_system/css/aurora.css"
    ) in dockerfile


@pytest.mark.parametrize(
    "template",
    [
        "accounts/auth_base.html",
        "layouts/base.html",
        "psychiatry/base_aurora.html",
        "psychiatry/login.html",
    ],
)
def test_shell_uses_compiled_local_css(template: str) -> None:
    html = render_to_string(template)
    assets = AssetsParser()
    assets.feed(html)
    assert "/static/design_system/css/aurora.css" in assets.styles
    assert all(src.startswith("/static/") for src in assets.scripts)
    assert not any("tailwind" in src for src in assets.scripts)
    assert all(href.startswith("/static/") for href in assets.styles)
    css = Path(settings.BASE_DIR, "static/design_system/css/aurora.css").read_text()
    assert ".bg-aurora-900" in css
    assert "@tailwind" not in css
    assert "@theme" not in css
    assert "fonts.googleapis.com" not in css


@pytest.mark.django_db
def test_login_is_real_form_without_demo_credentials(client: Client) -> None:
    from django.urls import reverse

    response = client.get(reverse("account_login"))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'name="csrfmiddlewaretoken"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert 'method="post"' in html
    assert "data-submit-button" in html
    assert "Demo" not in html
    assert "Senha demo" not in html
    assert "selectRolePreset" not in html
    assert "onclick=" not in html
    assert "SOS Crise 24h" not in html
    assert "Saúde Mental & Psiquiatria Integrada" not in html
    assert "aurora-auth-card" in html


def test_legacy_psychiatry_login_links_to_real_authentication() -> None:
    from django.urls import reverse

    html = render_to_string("psychiatry/login.html")
    assert f'href="{reverse("account_login")}"' in html
    assert "onsubmit=" not in html
    assert "0800" not in html
    assert '<input type="password"' not in html


@pytest.mark.parametrize("language", ["pt-br", "en", "es"])
@pytest.mark.parametrize(
    "template", ["accounts/auth_base.html", "psychiatry/base_aurora.html"]
)
def test_shell_language_uses_server_preference(
    template: str, language: str, rf: RequestFactory, settings: SettingsWrapper
) -> None:
    from django.contrib.auth.models import AnonymousUser
    from django.utils.translation import override

    settings.LANGUAGES = [("pt-br", "Português"), ("en", "English"), ("es", "Español")]
    request = rf.get("/portal/")
    request.user = AnonymousUser()
    request.LANGUAGE_CODE = language
    with override(language):
        html = render_to_string(template, request=request)
    assert f'lang="{language}"' in html
    assert 'action="/accounts/language/"' in html
    assert 'name="csrfmiddlewaretoken"' in html
    for code in ("pt-br", "en", "es"):
        assert f'name="language" value="{code}"' in html
    assert "design_system/js/i18n.js" not in html


def test_psychiatry_shell_has_honest_status_and_accessible_navigation() -> None:
    html = render_to_string("psychiatry/base_aurora.html")
    for false_claim in (
        "Dr. Marcelo",
        "148.920",
        "Equipe de Resposta Ativa",
        "SOS 24h",
        "12/16",
        ">128<",
        "WCAG AAA",
        "Conformidade CFM",
        "Aurora Mind",
    ):
        assert false_claim not in html
    assert 'id="main-content"' in html
    assert 'aria-controls="psychiatry-navigation"' in html
    assert "data-aurora-nav-toggle" in html
    assert "design_system/js/shell.js" in html
    assert 'data-ai-status="disabled"' in html
    assert "design_system/images/ai-avatar.svg" in html
    assert "onclick=" not in html
    assert "design_system/js/app.js" not in html


def test_workspace_header_does_not_advertise_monitored_sos() -> None:
    from accounts.models import User

    html = render_to_string(
        "layouts/partials/header.html", {"user": User(email="synthetic@example.test")}
    )
    assert "SOS 24h" not in html


@pytest.mark.parametrize(
    "template", ["psychiatry/dashboard.html", "workspace/home.html"]
)
def test_portal_entrypoints_do_not_present_mock_clinical_operations(
    template: str,
) -> None:
    from accounts.models import User

    html = render_to_string(
        template,
        {
            "user": User(email="synthetic@example.test"),
            "layout_template": "layouts/vertical.html",
        },
    )
    for claim in (
        "0800",
        "1.284",
        "92.6%",
        "Mariana Silveira",
        "Dr. Marcelo",
        "SOS Crise 24h",
        "Monitoramento Contínuo",
        "criptografada",
        "Protocolo Vigente",
        "Plantão 188",
    ):
        assert claim not in html
    assert 'id="main-content"' in html
