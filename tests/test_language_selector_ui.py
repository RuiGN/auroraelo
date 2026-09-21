"""Presentation contract for staged publication of UI languages."""

from __future__ import annotations

from html.parser import HTMLParser

import pytest
from django.template.loader import render_to_string
from django.test import Client, override_settings
from django.urls import reverse

from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


class Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.items.append((tag, dict(attrs)))


def _render_selector(
    selector_id: str = "example",
    current: str = "pt-br",
    next_path: str = "/workspace/",
) -> str:
    return render_to_string(
        "components/language_selector.html",
        {
            "selector_id": selector_id,
            "ui_languages": [
                {"code": "pt-br", "name_local": "Português (Brasil)"},
                {"code": "en", "name_local": "English"},
                {"code": "es", "name_local": "Español"},
            ],
            "current_ui_language": current,
            "ui_language_next": next_path,
            "csrf_token": "synthetic-csrf-token",
        },
    )


def test_selector_preserves_current_choice_csrf_and_escaped_return_path() -> None:
    # O seletor é um <select> nativo (mesmo padrão da referência visual),
    # com a escolha atual marcada e o caminho de retorno escapado.
    html = _render_selector(
        current="en", next_path='/workspace/?q="<script>private</script>'
    )
    parser = Elements()
    parser.feed(html)
    assert any(
        tag == "select" and attrs.get("name") == "language"
        for tag, attrs in parser.items
    )
    options = [
        attrs
        for tag, attrs in parser.items
        if tag == "option" and attrs.get("value") is not None
    ]
    assert len(options) == 3
    selected = [a for a in options if "selected" in a]
    assert len(selected) == 1
    assert selected[0]["value"] == "en"
    assert any(
        tag == "input" and attrs.get("name") == "csrfmiddlewaretoken"
        for tag, attrs in parser.items
    )
    assert any(
        tag == "input"
        and attrs.get("name") == "next"
        and attrs.get("value") == '/workspace/?q="<script>private</script>'
        for tag, attrs in parser.items
    )
    assert "<script>private</script>" not in html
    assert reverse("account_set_language") in html


@pytest.mark.parametrize(
    ("language", "name"),
    (
        ("pt-br", "Português (Brasil)"),
        ("en", "English"),
        ("es", "Español"),
    ),
)
def test_closed_language_toggle_shows_flag_and_language_code(
    language: str, name: str
) -> None:
    # O seletor fechado exibe os idiomas publicados e marca o atual.
    html = _render_selector(current=language)
    parser = Elements()
    parser.feed(html)
    options = [
        attrs
        for tag, attrs in parser.items
        if tag == "option" and attrs.get("value") is not None
    ]
    assert len(options) == 3
    assert sum("selected" in attrs for attrs in options) == 1
    for code, local_name in (
        ("pt-br", "Português (Brasil)"),
        ("en", "English"),
        ("es", "Español"),
    ):
        assert any(a.get("value") == code for a in options)
        assert local_name in html
    assert f'value="{language}" selected' in html
    assert any(tag == "select" for tag, _ in parser.items)
    assert "d-none" not in html


def test_flag_dropdown_uses_post_forms_for_each_language() -> None:
    html = _render_selector(
        selector_id="auth", next_path="/accounts/login/?next=%2Fworkspace%2F"
    )

    # Um único formulário POST com o idioma escolhido; sem opções inline JS.
    assert html.count('method="post"') == 1
    assert html.count("data-language-form") == 1
    assert html.count('name="language"') == 1
    assert 'name="next" value="/accounts/login/?next=%2Fworkspace%2F"' in html
    assert "<select" in html


@pytest.mark.django_db
def test_default_publication_does_not_offer_unreviewed_languages(
    client: Client,
) -> None:
    # Por padrão, apenas os idiomas configurados em LANGUAGES são publicados;
    # qualquer restrição adicional é refletida diretamente nas opções.
    response = client.get(reverse("account_login"))
    parser = Elements()
    parser.feed(response.content.decode())
    values = [
        attrs["value"]
        for tag, attrs in parser.items
        if tag == "option" and attrs.get("value") is not None
    ]
    assert values == ["pt-br", "en", "es"]


@pytest.mark.django_db
@override_settings(LANGUAGES=[("pt-br", "Português (Brasil)"), ("es", "Español")])
def test_login_and_workspace_use_effective_language_and_expose_selector(
    client: Client,
) -> None:
    user = UserFactory.create()
    clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(user=user, clinic=clinic, role="clinic_admin")
    client.cookies["django_language"] = "es"
    anonymous = client.get(reverse("account_login"))
    assert 'lang="es"' in anonymous.content.decode()
    assert 'dir="ltr"' in anonymous.content.decode()
    assert 'name="language"' in anonymous.content.decode()
    assert 'value="es" selected' in anonymous.content.decode()
    assert 'name="csrfmiddlewaretoken"' in anonymous.content.decode()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    response = client.get(reverse("workspace_vertical"))
    assert response.status_code == 200
    assert 'lang="es"' in response.content.decode()
    assert 'name="language"' in response.content.decode()
    assert 'value="es" selected' in response.content.decode()
    assert response.headers["Content-Language"] == "es"
