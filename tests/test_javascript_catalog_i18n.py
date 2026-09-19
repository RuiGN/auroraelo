"""Tests for JavaScriptCatalog, djangojs translations, and client-side i18n (S14.06)."""

from __future__ import annotations

import concurrent.futures

import pytest
from django.test import Client, override_settings
from django.urls import reverse

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


@pytest.mark.parametrize(
    ("language", "expected_loading", "escaped_error_fragment"),
    (
        ("pt-br", "Carregando...", "solicita\\u00e7\\u00e3o"),
        ("en", "Loading...", "An error occurred while processing your request."),
        ("es", "Cargando...", "Ocurri\\u00f3 un error"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_javascript_catalog_returns_translated_messages(
    client: Client, language: str, expected_loading: str, escaped_error_fragment: str
) -> None:
    url = reverse("javascript-catalog")
    response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)

    assert response.status_code == 200
    assert "text/javascript" in response.headers["Content-Type"]
    assert response.headers.get("Content-Language") == language
    content = response.content.decode("utf-8")
    assert expected_loading in content
    assert escaped_error_fragment in content


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_javascript_catalog_plural_forms(client: Client) -> None:
    url = reverse("javascript-catalog")

    # English: 1 item selected / 2 items selected
    response_en = client.get(url, HTTP_ACCEPT_LANGUAGE="en")
    content_en = response_en.content.decode("utf-8")
    assert "item selected" in content_en
    assert "items selected" in content_en

    # Spanish: 1 elemento seleccionado / 2 elementos seleccionados
    response_es = client.get(url, HTTP_ACCEPT_LANGUAGE="es")
    content_es = response_es.content.decode("utf-8")
    assert "elemento seleccionado" in content_es
    assert "elementos seleccionados" in content_es


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_javascript_catalog_parallel_requests_isolate_languages() -> None:
    """Ensure concurrent requests in different languages don't cross-contaminate."""
    url = reverse("javascript-catalog")

    def fetch_lang(lang: str) -> tuple[str, str]:
        c = Client()
        r = c.get(url, HTTP_ACCEPT_LANGUAGE=lang)
        return lang, r.content.decode("utf-8")

    languages = ["pt-br", "en", "es"] * 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch_lang, languages))

    for lang, content in results:
        if lang == "en":
            assert "Loading..." in content
            assert "Cargando..." not in content
        elif lang == "es":
            assert "Cargando..." in content
            assert "Loading..." not in content
        elif lang == "pt-br":
            assert "Carregando..." in content
            assert "Loading..." not in content
