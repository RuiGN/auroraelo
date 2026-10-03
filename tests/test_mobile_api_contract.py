"""Guarda de contrato da API do app do paciente (`/api/v1/mobile/`).

Estes testes leem o OpenAPI gerado e impedem, para qualquer rota futura, os erros que
mais custam caro neste tipo de API: rota aberta, rota que aceita cookie, rota em que o
cliente escolhe a clínica ou o paciente, rota fora da documentação, rota que traz de
volta funções que pertencem ao aplicativo da clínica, rota escondida por outra do mesmo
caminho e código de erro que o app não conhece.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest
from django.test import Client

from api import api

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "mobile-patient-api.md"
PUBLIC_OPERATIONS = {
    ("post", "/api/v1/mobile/auth/login/"),
    ("post", "/api/v1/mobile/auth/refresh/"),
    ("post", "/api/v1/mobile/auth/activate/"),
    ("post", "/api/v1/mobile/auth/password-recovery/"),
    ("post", "/api/v1/mobile/auth/password-reset/"),
}
# O cliente nunca informa de quem é o dado nem em que clínica ele está.
IDENTITY_FIELDS = {
    "clinic_id",
    "tenant_id",
    "patient_id",
    "patient_profile_id",
    "user_id",
    "actor_id",
    "subject_id",
}
# Funções do aplicativo da clínica (equipe): não têm rota no app do paciente.
CLINIC_APP_TERMS = (
    "aftercare",
    "concierge",
    "discharge",
    "family",
    "communication-rule",
    "conversation",
    "messages",
)


def _schema() -> dict[str, Any]:
    return api.get_openapi_schema()


def _operations() -> list[tuple[str, str, dict[str, Any]]]:
    found = []
    for path, operations in _schema()["paths"].items():
        if path.startswith("/api/v1/mobile/"):
            for method, operation in operations.items():
                found.append((method, path, operation))
    return found


def _body_properties(operation: dict[str, Any]) -> set[str]:
    schema = _schema()
    body = (
        operation.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    ref = body.get("$ref", "")
    if not ref:
        return set(body.get("properties", {}))
    name = ref.rsplit("/", 1)[-1]
    return set(schema["components"]["schemas"][name].get("properties", {}))


def test_the_patient_app_has_routes() -> None:
    assert len(_operations()) >= 40


@pytest.mark.parametrize(("method", "path", "operation"), _operations())
def test_every_route_requires_only_the_app_token(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    if (method, path) in PUBLIC_OPERATIONS:
        assert not operation.get("security")
        return
    assert operation.get("security") == [{"PatientBearerAuth": []}], (method, path)


@pytest.mark.parametrize(("method", "path", "operation"), _operations())
def test_no_route_lets_the_client_choose_clinic_or_patient(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    parameters = {p["name"] for p in operation.get("parameters", [])}
    assert not parameters & IDENTITY_FIELDS, (method, path, parameters)
    allowed_in_body = (
        {"clinic_id"}
        if (method, path)
        == (
            "post",
            "/api/v1/mobile/auth/login/",
        )
        else set()
    )
    assert not (_body_properties(operation) & IDENTITY_FIELDS) - allowed_in_body, (
        method,
        path,
    )


def test_no_route_brings_back_clinic_app_features() -> None:
    for method, path, _operation in _operations():
        assert not any(term in path for term in CLINIC_APP_TERMS), (method, path)


def test_every_route_is_documented() -> None:
    text = re.sub(r"\{[^}]*\}", "{}", DOC.read_text(encoding="utf-8"))
    for method, path, _operation in _operations():
        short = re.sub(r"\{[^}]*\}", "{}", path.removeprefix("/api/v1"))
        assert short in text, f"{method.upper()} {path} não está em {DOC.name}"


def _documented_error_codes() -> str:
    text = DOC.read_text(encoding="utf-8")
    return text[text.index("## Erros") : text.index("## Rotas")]


def _error_codes_in_source() -> set[str]:
    """Todo `code` que as rotas do app devolvem (`problem(...)` ou `{"code": ...}`)."""
    found: set[str] = set()
    for path in sorted((ROOT / "api").glob("mobile_*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "problem":
                arg = node.args[2] if len(node.args) >= 3 else None
                for keyword in node.keywords:
                    if keyword.arg == "code":
                        arg = keyword.value
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.add(arg.value)
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values, strict=True):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "code"
                        and isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and value.value
                    ):
                        found.add(value.value)
    return found


def test_every_error_code_the_api_returns_is_in_the_documented_list() -> None:
    documented = _documented_error_codes()
    found = _error_codes_in_source()
    assert {"not_found", "limit_reached", "invalid_phone"} <= found  # a varredura acha
    missing = sorted(code for code in found if f"`{code}`" not in documented)
    assert not missing, f"códigos fora da lista de erros de {DOC.name}: {missing}"


@pytest.mark.django_db
@pytest.mark.parametrize(("method", "path", "operation"), _operations())
def test_every_route_answers_its_own_method(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    """Dois roteadores no mesmo caminho: o Django usa o primeiro e o outro dá 405."""
    if (method, path) in PUBLIC_OPERATIONS:
        return
    url = re.sub(r"\{[^}]*\}", "00000000-0000-4000-8000-000000000000", path)
    response = getattr(Client(), method)(url, content_type="application/json")
    assert response.status_code == 401, (method, path, response.status_code)
