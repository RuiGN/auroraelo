"""Template contracts for the shared user interface language selector."""

from __future__ import annotations

from typing import TypedDict

from django.http import HttpRequest

from .language_preferences import published_language_codes


class UILanguage(TypedDict):
    code: str
    name_local: str
    country_code: str
    flag_path: str


class LanguageContext(TypedDict):
    ui_languages: list[UILanguage]
    current_ui_language: str
    ui_language_next: str


_COUNTRY_BY_CODE = {"pt-br": "br", "en": "us", "es": "es"}


def language_preferences(request: HttpRequest) -> LanguageContext:
    """Expose published locales, country codes, flag paths, and the local path."""
    local_names = {
        "pt-br": "Português (Brasil)",
        "en": "English",
        "es": "Español",
    }
    languages = [
        UILanguage(
            code=code,
            name_local=local_names.get(code, code),
            country_code=_COUNTRY_BY_CODE.get(code, code),
            flag_path=f"duralux/images/flags/{_COUNTRY_BY_CODE.get(code, code)}.svg",
        )
        for code in published_language_codes()
    ]
    return LanguageContext(
        ui_languages=languages,
        current_ui_language=getattr(request, "LANGUAGE_CODE", "pt-br"),
        ui_language_next=request.get_full_path(),
    )
