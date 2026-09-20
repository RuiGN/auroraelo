"""Idioma explícito da resposta tem precedência sobre preferência de interface."""

import pytest
from django.http import HttpResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.test import RequestFactory
from django.utils import translation
from pytest_django.fixtures import SettingsWrapper

from accounts.middleware import UserLanguageMiddleware
from accounts.models import User


@pytest.mark.parametrize("explicit_language", [None, "pt-br"])
@pytest.mark.parametrize("kind", ["html", "json", "stream"])
def test_response_language_keeps_view_header_or_uses_profile_default(
    explicit_language: str | None, kind: str, settings: SettingsWrapper
) -> None:
    settings.LANGUAGES = (("pt-br", "Português (Brasil)"), ("en", "English"))
    request = RequestFactory().get("/synthetic-language/")
    request.user = User(preferred_language="en")
    request.LANGUAGE_CODE = "pt-br"
    response: HttpResponseBase
    if kind == "stream":
        response = StreamingHttpResponse([b"synthetic"], content_type="text/html")
    else:
        response = HttpResponse(
            b"{}", content_type="text/html" if kind == "html" else "application/json"
        )
    if explicit_language is not None:
        response.headers["Content-Language"] = explicit_language

    with translation.override("es"):
        result = UserLanguageMiddleware(lambda _request: response)(request)
        assert translation.get_language() == "es"

    assert result.headers["Content-Language"] == (explicit_language or "en")
    assert request.LANGUAGE_CODE == "en"
    assert request.user.preferred_language == "en"
    if kind in {"html", "stream"}:
        assert set(result.headers["Vary"].split(", ")) == {"Cookie", "Accept-Language"}
    else:
        assert "Vary" not in result.headers
