"""Contratos de renderização do shell responsivo do painel Master."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import include, path, resolve
from django.utils.translation import override

from accounts.models import User
from clinics.typing import ClinicRequest


def _stub_view(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
    return HttpResponse("")


_master_patterns = [
    path("", _stub_view, name="dashboard"),
    path("tenants/", _stub_view, name="tenant_list"),
    path("tenants/create/", _stub_view, name="tenant_create"),
    path("tenants/<uuid:clinic_id>/", _stub_view, name="tenant_detail"),
]
_administration_patterns = [path("users/", _stub_view, name="user_list")]
urlpatterns = [
    path(
        "master/",
        include((_master_patterns, "master_panel"), namespace="master_panel"),
    ),
    path(
        "administration/",
        include(
            (_administration_patterns, "administration"), namespace="administration"
        ),
    ),
    path("logout/", _stub_view, name="account_logout"),
    path("language/", _stub_view, name="account_set_language"),
]


def _request() -> ClinicRequest:
    request = cast(ClinicRequest, RequestFactory().get("/master/"))
    request.clinic = None
    request.user = User(
        email="master@example.test",
        first_name="Pessoa administradora",
    )
    request.resolver_match = resolve("/master/")
    return request


def _render(template_name: str, context: dict[str, object]) -> str:
    return render_to_string(template_name, context, request=_request())


def _source(template_name: str) -> str:
    return Path(template_name).read_text(encoding="utf-8")


@override_settings(ROOT_URLCONF="tests.test_master_responsive_templates")
def test_master_base_renders_mobile_disclosure_and_preserves_child_blocks() -> None:
    content = _render(
        "master_panel/base.html",
        {
            "page_title": "Painel Master",
            "messages": [],
            "ui_languages": [],
        },
    )

    assert 'id="master-sidebar"' in content
    assert 'aria-controls="master-sidebar"' in content
    assert 'aria-expanded="false"' in content
    source = _source("master_panel/templates/master_panel/base.html")
    assert "block panel_navigation" in source
    assert "block panel_label" in source
    assert "block content" in source
    assert "block page_scripts" in source
    assert "chart.umd.min.js" not in content
    assert "<script>" not in content


@override_settings(ROOT_URLCONF="tests.test_master_responsive_templates")
def test_dashboard_is_tenant_only_and_keeps_recent_list_contract() -> None:
    clinic_id = uuid4()

    class Subscription:
        clinic = SimpleNamespace(pk=clinic_id, name="Clínica Aurora")
        status = "active"
        created_at = datetime(2026, 9, 23)

        def get_plan_display(self) -> str:
            return "Essencial"

        def get_status_display(self) -> str:
            return "Ativa"

    content = _render(
        "master_panel/dashboard.html",
        {
            "page_title": "Painel Master",
            "messages": [],
            "ui_languages": [],
            "total_tenants": 1,
            "active_tenants": 1,
            "past_due_tenants": 0,
            "blocked_tenants": 0,
            "recent_subs": [Subscription()],
            # O contrato mensal continua disponível para a integração principal.
            "chart_monthly_labels": '["set/2026"]',
            "chart_monthly_data": "[1]",
        },
    )

    assert "Clínica Aurora" in content
    assert "Total de tenants" in content
    assert "Tenants recentes" in content
    assert "chartMonthly" not in content
    assert "new Chart" not in content
    assert "chart_monthly_labels" not in content

    source = _source("master_panel/templates/master_panel/dashboard.html")
    assert '{% translate "Total de tenants" %}' in source
    assert '{% translate "Tenants recentes" %}' in source
    assert "administration:user_list" in _source(
        "master_panel/templates/master_panel/base.html"
    )


def test_master_css_and_panel_js_define_responsive_accessible_contracts() -> None:
    css = Path("design_system/src/master.css").read_text(encoding="utf-8")
    js = Path("static/master_panel/js/panel.js").read_text(encoding="utf-8")

    assert "minmax(0, 1fr)" in css
    assert "min-width: 0" in css
    assert "overflow-x: auto" in css
    assert "@media (max-width:" in css
    assert ".chart-card" in css
    assert ".status-badge" in css
    assert "aria-expanded" in js
    assert "Escape" in js
    assert "focus()" in js


@pytest.mark.parametrize(
    ("language", "heading", "empty", "administration", "login"),
    [
        (
            "en",
            "Tenant dashboard",
            "No tenants registered yet.",
            "User and team administration",
            "Access restricted to platform administration",
        ),
        (
            "es",
            "Panel de tenants",
            "Aún no hay tenants registrados.",
            "Administración de usuarios y equipo",
            "Acceso restringido a la administración de la plataforma",
        ),
    ],
)
def test_master_pages_render_translated_copy(
    language: str, heading: str, empty: str, administration: str, login: str
) -> None:
    with override(language):
        dashboard = _render("master_panel/dashboard.html", {"recent_subs": []})
        login_html = _render("master_panel/login.html", {})
    assert heading in dashboard
    assert empty in dashboard
    assert administration in dashboard
    assert login in login_html
