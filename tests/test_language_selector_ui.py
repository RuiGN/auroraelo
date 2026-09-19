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


def test_selector_preserves_current_choice_csrf_and_escaped_return_path() -> None:
    html = render_to_string(
        "components/language_selector.html",
        {
            "selector_id": "example",
            "ui_languages": [
                {
                    "code": "pt-br",
                    "name_local": "Português (Brasil)",
                    "country_code": "br",
                    "flag_path": "duralux/images/flags/br.svg",
                },
                {
                    "code": "en",
                    "name_local": "English",
                    "country_code": "us",
                    "flag_path": "duralux/images/flags/us.svg",
                },
            ],
            "current_ui_language": "en",
            "ui_language_next": '/workspace/?q="<script>private</script>',
            "csrf_token": "synthetic-csrf-token",
        },
    )
    parser = Elements()
    parser.feed(html)
    assert any(
        tag == "input"
        and attrs.get("name") == "language"
        and attrs.get("value") == "en"
        for tag, attrs in parser.items
    )
    assert any(
        tag == "button" and "product-language-option" in (attrs.get("class") or "")
        for tag, attrs in parser.items
    )
    assert "<script>private</script>" not in html
    assert reverse("account_set_language") in html


@pytest.mark.parametrize(
    ("language", "country", "name"),
    (
        ("pt-br", "br", "Português (Brasil)"),
        ("en", "us", "English"),
        ("es", "es", "Español"),
    ),
)
def test_closed_language_toggle_shows_flag_and_language_code(
    language: str, country: str, name: str
) -> None:
    html = render_to_string(
        "components/language_selector.html",
        {
            "selector_id": "header",
            "current_ui_language": language,
            "ui_language_next": "/workspace/",
            "ui_languages": [
                {
                    "code": code,
                    "name_local": local_name,
                    "country_code": code_country,
                    "flag_path": f"duralux/images/flags/{code_country}.svg",
                }
                for code, local_name, code_country in (
                    ("pt-br", "Português (Brasil)", "br"),
                    ("en", "English", "us"),
                    ("es", "Español", "es"),
                )
            ],
        },
    )
    toggle = html.split("</button>", 1)[0]
    parser = Elements()
    parser.feed(toggle)
    assert not any(tag == "i" for tag, _attrs in parser.items)
    flag = next(attrs for tag, attrs in parser.items if tag == "img")
    assert flag["class"] == "product-language-flag"
    assert flag["alt"] == name
    assert flag["aria-hidden"] == "true"
    flag_src = flag["src"]
    assert flag_src is not None and flag_src.endswith(
        f"/duralux/images/flags/{country}.svg"
    )
    button = next(attrs for tag, attrs in parser.items if tag == "button")
    assert name in str(button["aria-label"])
    assert f'<span class="product-language-code">{language.upper()}</span>' in toggle
    assert "d-none" not in toggle
    assert "<select" not in html
    full_parser = Elements()
    full_parser.feed(html)
    option_buttons = [
        attrs
        for tag, attrs in full_parser.items
        if tag == "button" and "product-language-option" in (attrs.get("class") or "")
    ]
    assert len(option_buttons) == 3
    assert sum(attrs.get("aria-current") == "true" for attrs in option_buttons) == 1
    for code, local_name, country in (
        ("pt-br", "Português (Brasil)", "br"),
        ("en", "English", "us"),
        ("es", "Español", "es"),
    ):
        assert f'name="language" value="{code}"' in html
        assert f'alt="{local_name}"' in html
        assert f"/duralux/images/flags/{country}.svg" in html


def test_flag_dropdown_uses_post_forms_for_each_language() -> None:
    html = render_to_string(
        "components/language_selector.html",
        {
            "selector_id": "auth",
            "current_ui_language": "pt-br",
            "ui_language_next": "/accounts/login/?next=%2Fworkspace%2F",
            "ui_languages": [
                {
                    "code": code,
                    "name_local": local_name,
                    "country_code": country,
                    "flag_path": f"duralux/images/flags/{country}.svg",
                }
                for code, local_name, country in (
                    ("pt-br", "Português (Brasil)", "br"),
                    ("en", "English", "us"),
                    ("es", "Español", "es"),
                )
            ],
        },
    )
    assert html.count('method="post"') == 3
    assert html.count('data-language-form') == 3
    assert html.count('name="language"') == 3
    assert 'name="next" value="/accounts/login/?next=%2Fworkspace%2F"' in html
    assert 'class="product-language-option active ' in html


@pytest.mark.django_db
def test_default_publication_does_not_offer_unreviewed_languages(
    client: Client,
) -> None:
    response = client.get(reverse("account_login"))
    parser = Elements()
    parser.feed(response.content.decode())
    values = [
        attrs["value"]
        for tag, attrs in parser.items
        if tag == "input" and attrs.get("name") == "language"
    ]
    assert values == ["pt-br"]


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
    assert 'name="language" value="es"' in anonymous.content.decode()
    assert 'name="csrfmiddlewaretoken"' in anonymous.content.decode()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    response = client.get(reverse("workspace_vertical"))
    assert response.status_code == 200
    assert 'lang="es"' in response.content.decode()
    assert 'name="language" value="es"' in response.content.decode()
    assert response.headers["Content-Language"] == "es"
