"""Translation contracts for shared UI, preserving data and accessible names."""

from __future__ import annotations

import pytest
from django.template.loader import render_to_string
from django.utils import translation

from core.forms import DesignSystemExampleForm


@pytest.mark.parametrize(
    ("language", "actions", "sort", "empty", "field_label"),
    [
        (
            "pt-br",
            "Ações",
            "Ordenar por",
            "Nenhum registro disponível.",
            "Nome de exibição",
        ),
        ("en", "Actions", "Sort by", "No records available.", "Display name"),
        (
            "es",
            "Acciones",
            "Ordenar por",
            "No hay registros disponibles.",
            "Nombre para mostrar",
        ),
    ],
)
def test_shared_table_translates_labels_without_translating_or_unescaping_data(
    language: str, actions: str, sort: str, empty: str, field_label: str
) -> None:
    table = {
        "id": "records",
        "caption": "Registro original",
        "columns": [
            {"label": '<img src=x onerror="alert(1)">', "order_url": "?order=title"}
        ],
        "rows": [{"id": "record-1", "cells": ["Nome clínico original"], "actions": []}],
    }
    with translation.override(language):
        html = render_to_string("components/responsive_table.html", {"table": table})
        assert str(DesignSystemExampleForm()["display_name"].label) == field_label
        table["rows"] = []
        empty_html = render_to_string(
            "components/responsive_table.html", {"table": table}
        )
    assert actions in html
    assert sort in html
    assert "Nome clínico original" in html
    assert "<img src=x" not in html
    assert "&lt;img" in html
    assert "?order=title" in html
    assert empty in empty_html


@pytest.mark.parametrize(
    ("language", "label"), [("en", "Go to page 2"), ("es", "Ir a la página 2")]
)
def test_pagination_accessible_name_uses_translated_placeholder(
    language: str, label: str
) -> None:
    with translation.override(language):
        html = render_to_string(
            "components/pagination.html",
            {"pagination": {"pages": [{"number": 2, "url": "?page=2&q=original"}]}},
        )
    assert f'aria-label="{label}"' in html
    assert "?page=2&amp;q=original" in html


@pytest.mark.parametrize(
    ("language", "back"), [("en", "Back to home"), ("es", "Volver al inicio")]
)
def test_error_page_keeps_request_reference_escaped(language: str, back: str) -> None:
    with translation.override(language):
        html = render_to_string(
            "errors/403.html",
            {
                "title": "Fixed title",
                "message": "Fixed message",
                "request_id": "<private-reference>",
            },
        )
    assert back in html
    assert "&lt;private-reference&gt;" in html
    assert "<private-reference>" not in html
