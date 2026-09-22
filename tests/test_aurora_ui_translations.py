"""Traduções técnicas da UI; não representam aceite clínico/publicação."""

import gettext as python_gettext
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import TypedDict

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils.translation import gettext, ngettext, override
from pytest_django.fixtures import SettingsWrapper

from accounts.models import User
from scripts.check_ui_catalogs import run_check

LANGUAGES = ("pt-br", "en", "es")
COPY = (
    (
        "Acesse sua conta para continuar.",
        "Sign in to your account to continue.",
        "Inicia sesión en tu cuenta para continuar.",
    ),
    (
        "Assistente de IA indisponível",
        "AI assistant unavailable",
        "Asistente de IA no disponible",
    ),
    (
        "Avatar de inteligência artificial",
        "Artificial intelligence avatar",
        "Avatar de inteligencia artificial",
    ),
    (
        "A IA generativa está desativada até a integração com API própria e "
        "revisão clínica. Este avatar não representa um profissional de saúde.",
        "Generative AI is disabled pending integration with our own API and "
        "clinical review. This avatar does not represent a healthcare "
        "professional.",
        "La IA generativa está desactivada hasta la integración con una API "
        "propia y la revisión clínica. Este avatar no representa a un "
        "profesional de la salud.",
    ),
    (
        "Este portal não é um serviço de emergência e não oferece monitoramento"
        " contínuo.",
        "This portal is not an emergency service and does not provide "
        "continuous monitoring.",
        "Este portal no es un servicio de emergencias y no ofrece seguimiento "
        "continuo.",
    ),
    (
        "No Brasil, em emergência, ligue 192 (SAMU). Para apoio emocional, 188 "
        "(CVV). Em outros países, procure o serviço local de emergência.",
        "In Brazil, in an emergency, call 192 (SAMU). For emotional support, "
        "call 188 (CVV). In other countries, contact your local emergency "
        "service.",
        "En Brasil, en una emergencia, llama al 192 (SAMU). Para apoyo "
        "emocional, al 188 (CVV). En otros países, contacta con el servicio "
        "local de emergencias.",
    ),
    (
        "Álcool, outras substâncias e jogos: cada trajetória merece cuidado e "
        "respeito.",
        "Alcohol, other substances and gambling or gaming: every journey "
        "deserves care and respect.",
        "Alcohol, otras sustancias y juegos de azar o videojuegos: cada "
        "trayectoria merece cuidado y respeto.",
    ),
)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("messages", COPY)
def test_new_safety_copy_uses_real_gettext(
    language: str, messages: tuple[str, str, str]
) -> None:
    with override(language):
        translated = gettext(messages[0])
    assert translated == messages[LANGUAGES.index(language)]
    if language != "pt-br":
        assert translated != messages[0]


def inventory_files(path: Path) -> list[str]:
    inventory: object = json.loads(path.read_text())
    assert isinstance(inventory, dict)
    files: object = inventory["files"]
    # O inventário mapeia arquivo para msgids; o escopo contém uma lista de arquivos.
    assert isinstance(files, (dict, list))
    names: list[str] = []
    for file in files:
        assert isinstance(file, str)
        names.append(file)
    return names


def test_cumulative_scope_includes_every_new_surface_and_gettext_key(
    tmp_path: Path,
) -> None:
    root = Path(settings.BASE_DIR)
    scope = root / "docs/migration/translated-ui-scope.json"
    inventory = inventory_files(root / "design_system/ui-strings.json")
    assert set(inventory) <= set(inventory_files(scope))
    # Extração Django real inclui blocktranslate, contexto e todas as formas plurais.
    assert run_check(scope, tmp_path / "check.json", tmp_path / "ui.pot")


@pytest.mark.parametrize("locale", ("pt_BR", "en", "es"))
@pytest.mark.parametrize("domain", ("django", "djangojs"))
def test_catalog_metadata_identifies_aurora_elo(locale: str, domain: str) -> None:
    path = Path(settings.BASE_DIR) / "locale" / locale / "LC_MESSAGES" / f"{domain}.mo"
    with path.open("rb") as source:
        metadata = python_gettext.GNUTranslations(source).info()
    assert "Aurora Elo" in metadata["project-id-version"]
    assert "Aurora Elo" in metadata["last-translator"]
    assert "Aurora Elo" in metadata["language-team"]
    assert metadata["language"] == locale


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize(
    "template",
    (
        "accounts/auth_form.html",
        "psychiatry/login.html",
        "psychiatry/dashboard.html",
        "workspace/home.html",
    ),
)
def test_rendered_surfaces_have_translated_limits_and_selector(
    template: str, language: str, rf: RequestFactory, settings: SettingsWrapper
) -> None:
    settings.LANGUAGES = [(code, code) for code in LANGUAGES]
    request = rf.get("/synthetic/")
    request.user = AnonymousUser()
    request.LANGUAGE_CODE = language
    index = LANGUAGES.index(language)
    # Build the same ui_languages structure that accounts.context_processors
    # language_preferences() would inject — render_to_string does not call
    # context processors automatically.
    _country = {"pt-br": "br", "en": "us", "es": "es"}
    _names = {"pt-br": "Português (Brasil)", "en": "English", "es": "Español"}
    ui_languages = [
        {"code": code, "name_local": _names[code], "country_code": _country[code]}
        for code in LANGUAGES
    ]
    context = {
        "user": User(email="synthetic@example.test", first_name="Pessoa Sintética"),
        "active_clinic": {"name": "Clínica Sintética"},
        "layout_template": "layouts/vertical.html",
        "ui_languages": ui_languages,
        "current_ui_language": language,
        "ui_language_next": "/synthetic/",
    }
    with override(language):
        html = render_to_string(template, context, request=request)
    assert f'lang="{language}"' in html
    assert COPY[4][index] in html
    assert COPY[5][index] in html
    assert "192 (SAMU)" in html and "188 (CVV)" in html
    if template == "psychiatry/login.html":
        prompt = (
            "Use sua conta Aurora Elo para acessar o portal.",
            "Use your Aurora Elo account to access the portal.",
            "Usa tu cuenta Aurora Elo para acceder al portal.",
        )
        assert prompt[index] in html
    if template == "psychiatry/dashboard.html":
        assert COPY[1][index] in html
        assert COPY[2][index] in html
        assert COPY[3][index] in html
        assert 'data-ai-status="disabled"' in html
    if template == "accounts/auth_form.html":
        assert COPY[0][index] in html
        assert COPY[6][index] in html
    if template == "workspace/home.html":
        greetings = (
            "Olá, Pessoa Sintética.",
            "Hello, Pessoa Sintética.",
            "Hola, Pessoa Sintética.",
        )
        assert greetings[index] in html
        assert "Clínica Sintética" in html
    assert f'action="{reverse("account_set_language")}"' in html
    assert 'name="csrfmiddlewaretoken"' in html
    for code in LANGUAGES:
        assert f'<option value="{code}"' in html
    # The template may append class="..." after `selected` (e.g. for auth
    # selector_id), so match the attribute prefix only — not the closing >.
    assert f'<option value="{language}" selected' in html


class ParsedForm(TypedDict):
    attributes: dict[str, str | None]
    inputs: dict[str | None, str | None]


class FormParser(HTMLParser):
    """Inspeciona os formulários renderizados, sem assumir sua ordem."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[ParsedForm] = []
        self.current: ParsedForm | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            self.current = {"attributes": attributes, "inputs": {}}
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            self.current["inputs"][attributes.get("name")] = attributes.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current = None


@pytest.mark.django_db
@pytest.mark.parametrize("language", LANGUAGES)
def test_real_login_and_language_post_preserve_csrf_and_cookie(
    language: str, settings: SettingsWrapper
) -> None:
    settings.LANGUAGES = [(code, code) for code in LANGUAGES]
    client = Client(enforce_csrf_checks=True)
    target = reverse("account_login")
    response = client.get(target)
    assert response.status_code == 200
    parser = FormParser()
    parser.feed(response.content.decode())
    login = next(form for form in parser.forms if "password" in form["inputs"])
    assert login["attributes"]["method"] == "post"
    assert "email" in login["inputs"]
    assert login["inputs"]["csrfmiddlewaretoken"]
    language_form = next(
        form
        for form in parser.forms
        if form["attributes"].get("action") == reverse("account_set_language")
    )
    assert language_form["attributes"]["method"] == "post"
    assert (
        client.post(
            target, {"email": "synthetic@example.test", "password": "synthetic"}
        ).status_code
        == 403
    )
    assert client.get(reverse("account_set_language")).status_code == 405
    assert (
        client.post(reverse("account_set_language"), {"language": language}).status_code
        == 403
    )
    changed = client.post(
        reverse("account_set_language"),
        {
            "language": language,
            "next": target,
            "csrfmiddlewaretoken": language_form["inputs"]["csrfmiddlewaretoken"],
        },
    )
    assert changed.status_code == 302
    assert changed.cookies[settings.LANGUAGE_COOKIE_NAME].value == language
    following = client.get(target)
    assert following.headers["Content-Language"] == language
    assert COPY[0][LANGUAGES.index(language)] in following.content.decode()
    assert User.objects.count() == 0


@pytest.mark.parametrize("language", LANGUAGES)
def test_existing_plural_translation_remains_available(language: str) -> None:
    with override(language):
        singular = ngettext(
            "%(count)s revogação operacional pendente",
            "%(count)s revogações operacionais pendentes",
            1,
        ) % {"count": 1}
        plural = ngettext(
            "%(count)s revogação operacional pendente",
            "%(count)s revogações operacionais pendentes",
            2,
        ) % {"count": 2}
    assert singular != plural
    assert singular.startswith("1 ") and plural.startswith("2 ")
    if language != "pt-br":
        assert "revogação" not in singular and "revogações" not in plural
