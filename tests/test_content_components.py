"""Rendering contracts for reusable cards, states, tables, and pagination."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from clinics.models import ClinicMembership
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


def _render(template: str, **context: Any) -> str:
    return render_to_string(template, context)


class _MainContentParser(HTMLParser):
    """Collect text rendered inside the operational main landmark only."""

    def __init__(self) -> None:
        super().__init__()
        self._main_depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "main":
            self._main_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._main_depth:
            self.text.append(data)


def _main_text(content: str) -> str:
    parser = _MainContentParser()
    parser.feed(content)
    return " ".join(parser.text)


def test_shared_components_use_duralux_bootstrap_contracts() -> None:
    summary = _render(
        "components/summary_card.html",
        card={
            "id": "migration-summary",
            "title": "Resumo",
            "description": "Descrição",
            "value": "1",
            "raw_value": 1,
            "trend_label": None,
            "tone": "info",
            "action": None,
        },
    )
    state = _render(
        "components/content_state.html",
        state={
            "kind": "empty",
            "title": "Sem itens",
            "message": "Cadastre o primeiro item.",
            "announce": False,
            "action": None,
        },
    )
    table = _render("components/responsive_table.html", **_table_context())
    pagination = _render(
        "components/pagination.html",
        pagination={
            "current_label": "Página 1 de 1",
            "first": None,
            "previous": None,
            "pages": [{"number": 1, "url": "?page=1", "current": True}],
            "next": None,
            "last": None,
        },
    )
    messages_source = (
        Path(settings.BASE_DIR) / "templates" / "layouts" / "partials" / "messages.html"
    ).read_text(encoding="utf-8")

    assert 'class="card h-100' in summary
    assert 'data-tone="info"' in summary
    assert 'class="alert ' in state
    assert 'data-state-kind="empty"' in state
    assert 'class="table-responsive' in table
    assert 'class="table table-hover align-middle"' in table
    assert re.search(r'class="pagination(?: [^"]*)?"', pagination)
    assert "workspace-message" not in messages_source
    assert "alert alert-" in messages_source


def test_summary_card_renders_semantics_trend_and_action() -> None:
    content = _render(
        "components/summary_card.html",
        card={
            "id": "summary-active",
            "title": "Cadastros ativos",
            "description": "Registros operacionais disponíveis.",
            "value": "12",
            "raw_value": 12,
            "trend_label": "2 novos no período",
            "tone": "info",
            "action": {"label": "Ver cadastros", "url": "/workspace/?view=active"},
        },
    )

    assert '<article class="card h-100' in content
    assert 'data-tone="info"' in content
    assert 'aria-labelledby="summary-active-title"' in content
    assert re.search(
        r'<h2\b[^>]*id="summary-active-title"[^>]*>Cadastros ativos</h2>', content
    )
    assert '<data value="12">12</data>' in content
    assert 'aria-label="Tendência: 2 novos no período"' in content
    assert 'href="/workspace/?view=active"' in content
    assert ">Ver cadastros<" in content


def test_summary_card_escapes_values_and_allowlists_tone() -> None:
    content = _render(
        "components/summary_card.html",
        card={
            "id": "unsafe-card",
            "title": "<script>alert(1)</script>",
            "description": "<strong>não confiável</strong>",
            "value": "<img src=x onerror=alert(1)>",
            "raw_value": "<12>",
            "trend_label": "<script>trend</script>",
            "tone": "javascript:alert(1)",
            "action": None,
        },
    )

    assert "<script>" not in content
    assert "<img" not in content
    assert "&lt;script&gt;" in content
    assert "&lt;strong&gt;" in content
    assert '<article class="card h-100' in content
    assert 'data-tone="neutral"' in content
    assert "javascript:alert(1)" not in content


@pytest.mark.parametrize(
    ("kind", "title"),
    (
        ("loading", "Carregando conteúdo"),
        ("empty", "Nenhum item cadastrado"),
        ("no_results", "Nenhum resultado encontrado"),
        ("unavailable", "Conteúdo temporariamente indisponível"),
        ("error", "Não foi possível carregar o conteúdo"),
        ("restricted", "Acesso não autorizado"),
    ),
)
def test_content_state_supports_every_allowlisted_kind(kind: str, title: str) -> None:
    content = _render(
        "components/content_state.html",
        state={
            "kind": kind,
            "title": title,
            "message": "Revise as opções disponíveis e tente novamente.",
            "announce": False,
            "action": None,
        },
    )

    assert 'class="alert ' in content
    assert f'data-state-kind="{kind}"' in content
    assert re.search(r"<h2\b[^>]*>" + re.escape(title) + r"</h2>", content)
    assert 'aria-hidden="true"' in content
    assert 'aria-live="polite"' not in content
    assert 'role="status"' not in content


def test_content_state_announces_change_and_escapes_action() -> None:
    content = _render(
        "components/content_state.html",
        state={
            "kind": "error",
            "title": "Falha temporária",
            "message": "Tente novamente sem reenviar dados.",
            "announce": True,
            "action": {"label": "Tentar novamente", "url": "/workspace/?retry=1"},
        },
    )

    assert 'role="status"' in content
    assert 'aria-live="polite"' in content
    assert 'href="/workspace/?retry=1"' in content
    assert ">Tentar novamente<" in content


def test_restricted_state_does_not_confirm_protected_resource() -> None:
    content = _render(
        "components/content_state.html",
        state={
            "kind": "restricted",
            "title": "Acesso não autorizado",
            "message": "Você não tem permissão para acessar este conteúdo.",
            "announce": False,
            "action": {"label": "Voltar à área de trabalho", "url": "/workspace/"},
        },
    )

    assert "Você não tem permissão para acessar este conteúdo." in content
    assert "paciente" not in content.casefold()
    assert "registro existe" not in content.casefold()


def test_build_query_url_allowlists_replaces_and_sorts_parameters() -> None:
    from core.presentation import build_query_url

    result = build_query_url(
        {"q": "Horizonte", "order": "name", "token": "secret", "page": "1"},
        overrides={"page": "2"},
        allowed_keys={"q", "order", "page"},
    )

    assert result == "?order=name&page=2&q=Horizonte"
    assert "token" not in result


@pytest.mark.parametrize(
    ("query", "overrides", "expected"),
    (
        ({"q": ""}, {}, ""),
        ({"q": "Clínica Sul"}, {}, "?q=Cl%C3%ADnica+Sul"),
        ({"page": "2"}, {"page": ""}, ""),
        ({"ignored": "value"}, {"ignored": "other"}, ""),
    ),
)
def test_build_query_url_handles_blank_unicode_and_unknown_keys(
    query: dict[str, str], overrides: dict[str, str], expected: str
) -> None:
    from core.presentation import build_query_url

    assert (
        build_query_url(
            query,
            overrides=overrides,
            allowed_keys={"q", "order", "page"},
        )
        == expected
    )


def _table_context() -> dict[str, Any]:
    return {
        "table": {
            "id": "activity-table",
            "caption": "Atividades operacionais recentes",
            "columns": [
                {
                    "key": "name",
                    "label": "Atividade",
                    "order_url": "?order=-name",
                    "aria_sort": "ascending",
                },
                {
                    "key": "status",
                    "label": "Situação",
                    "order_url": "?order=status",
                    "aria_sort": None,
                },
            ],
            "rows": [
                {
                    "id": "activity-1",
                    "cells": ["Configuração inicial", "Concluída"],
                    "actions": [
                        {
                            "label": "Abrir Configuração inicial",
                            "url": "/workspace/?item=1",
                        }
                    ],
                }
            ],
        }
    }


def test_responsive_table_preserves_native_and_mobile_semantics() -> None:
    content = _render("components/responsive_table.html", **_table_context())

    assert '<div class="table-responsive' in content
    assert '<table class="table table-hover align-middle">' in content
    assert "<caption>Atividades operacionais recentes</caption>" in content
    assert content.count('scope="col"') == 3
    assert 'aria-sort="ascending"' in content
    assert '<th scope="row">Configuração inicial</th>' in content
    assert "product-mobile-row-list" in content
    assert '<article class="card border-0 shadow-sm"' in content
    assert (
        '<span class="visually-hidden">Atividade: </span>Configuração inicial</h3>'
        in content
    )
    assert "<dd>Configuração inicial</dd>" not in content
    assert 'aria-current="true"' in content
    assert "ordem atual crescente" in content
    assert "aria-hidden" not in content
    assert ">Abrir Configuração inicial<" in content


def test_responsive_table_escapes_cells_and_actions() -> None:
    context = _table_context()
    context["table"]["rows"][0]["cells"][0] = "<script>alert(1)</script>"
    context["table"]["rows"][0]["actions"][0]["label"] = "<b>Abrir</b>"

    content = _render("components/responsive_table.html", **context)

    assert "<script>" not in content
    assert "<b>" not in content
    assert "&lt;script&gt;" in content
    assert "&lt;b&gt;Abrir&lt;/b&gt;" in content


def test_pagination_renders_middle_page_and_boundaries() -> None:
    content = _render(
        "components/pagination.html",
        pagination={
            "current": 2,
            "current_label": "Página 2 de 3",
            "page_count": 3,
            "first": "?page=1",
            "previous": "?page=1",
            "pages": [
                {"number": 1, "url": "?page=1", "current": False},
                {"number": 2, "url": "?page=2", "current": True},
                {"number": 3, "url": "?page=3", "current": False},
            ],
            "next": "?page=3",
            "last": "?page=3",
        },
    )

    assert '<nav aria-label="Paginação">' in content
    assert re.search(r'<ul class="pagination(?: [^"]*)?">', content)
    assert "Página 2 de 3" in content
    assert 'aria-current="page">2</span>' in content
    assert 'href="?page=1"' in content
    assert 'href="?page=3"' in content
    assert ">Primeira<" in content
    assert ">Última<" in content


def test_pagination_suppresses_unavailable_links_and_single_page() -> None:
    content = _render(
        "components/pagination.html",
        pagination={
            "current": 1,
            "current_label": "Página 1 de 1",
            "page_count": 1,
            "first": None,
            "previous": None,
            "pages": [{"number": 1, "url": "?page=1", "current": True}],
            "next": None,
            "last": None,
        },
    )

    assert "Página 1 de 1" in content
    assert "Primeira" not in content
    assert "Anterior" not in content
    assert "Próxima" not in content
    assert "Última" not in content
    assert 'href="?page=1"' not in content


def _login_component_user(client: Client, *, is_staff: bool = False) -> None:
    user = UserFactory.create(is_staff=is_staff)
    clinic = ClinicFactory.create(name="Clínica Componentes")
    ClinicMembershipFactory.create(
        user=user,
        clinic=clinic,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()


@pytest.mark.django_db
@pytest.mark.parametrize("route_name", ("workspace_vertical", "workspace_detached"))
def test_workspace_integrates_components_without_clinical_demo_data(
    client: Client, route_name: str
) -> None:
    _login_component_user(client)

    response = client.get(reverse(route_name))
    content = response.content.decode("utf-8")
    operational_content = _main_text(content).casefold()

    assert response.status_code == 200
    assert "Por onde começar" in content
    assert "Configurar clínica" in content
    assert "Módulos disponíveis" not in content
    assert "Registros sintéticos" not in content
    assert "diagnóstico" not in operational_content
    assert "john doe" not in operational_content

    filtered = client.get(
        reverse(route_name), {"q": "<script>alert(1)</script>"}
    ).content.decode("utf-8")
    assert "<script>alert(1)</script>" not in filtered
    assert "activity-search" not in filtered


def test_component_css_has_accessible_responsive_contracts() -> None:
    css = (
        Path(settings.BASE_DIR)
        / "static"
        / "duralux"
        / "css"
        / "product-integration.css"
    ).read_text(encoding="utf-8")

    for selector in (
        ".product-metric-grid",
        ".product-summary-card",
        ".product-content-state",
        ".product-table-desktop",
        ".product-mobile-row-list",
        ".pagination",
    ):
        assert selector in css
    assert "min-height: 44px" in css
    assert "var(--bs-border-radius-lg)" in css
    assert "var(--bs-body-bg)" in css
    assert "var(--bs-border-color)" in css
    assert "var(--bs-secondary-color)" in css
    assert "@media (max-width: 767.98px)" in css
    assert "overflow-x: auto" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
