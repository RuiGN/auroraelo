"""Snapshots sintéticos para testes de geometria; nunca acessa banco ou produção."""

import json
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"

import django

django.setup()

from django.contrib.auth.models import AnonymousUser  # noqa: E402
from django.template.loader import render_to_string  # noqa: E402
from django.test import RequestFactory  # noqa: E402
from django.urls import resolve  # noqa: E402

from accounts.forms import LoginForm  # noqa: E402
from accounts.models import User  # noqa: E402
from clinics.typing import ClinicRequest  # noqa: E402


def snapshots() -> dict[str, str]:
    """Renderizar dados explícitos sem consultas e sem autenticação real."""
    result: dict[str, str] = {}
    clinic = SimpleNamespace(
        pk=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        name="Clínica sintética de demonstração " + "NomeLongo" * 12,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    row = SimpleNamespace(
        clinic=clinic,
        get_plan_display="Gratuito",
        get_status_display="Em avaliação",
        status="trialing",
        created_at=clinic.created_at,
    )
    pages: list[tuple[str, str, dict[str, object]]] = [
        (
            "/master/login/",
            "master_panel/login.html",
            {"form": LoginForm(), "submit_label": "Acessar painel"},
        ),
        (
            "/master/",
            "master_panel/dashboard.html",
            {
                "page_title": "Painel Master",
                "total_tenants": 1,
                "active_tenants": 1,
                "past_due_tenants": 0,
                "blocked_tenants": 0,
                "recent_subs": [row],
            },
        ),
        (
            "/administracao/",
            "master_panel/users.html",
            {
                "page_title": "Usuários e equipe",
                "clinics": [clinic],
                "membership_rows": [],
                "invitation_rows": [],
            },
        ),
    ]
    for path, template, context in pages:
        request = cast(ClinicRequest, RequestFactory().get(path))
        request.clinic = None
        request.user = (
            AnonymousUser()
            if "login" in path
            else User(email="operador.sintetico@example.test", is_staff=True)
        )
        request.resolver_match = resolve(path)
        result[path] = render_to_string(template, context, request=request)
    return result


if __name__ == "__main__":
    print(json.dumps(snapshots()))
