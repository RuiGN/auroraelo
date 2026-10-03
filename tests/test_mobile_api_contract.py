"""Guarda de contrato da API do app do paciente (`/api/v1/mobile/`).

Estes testes leem o OpenAPI gerado e impedem, para qualquer rota futura, os erros que
mais custam caro neste tipo de API: rota aberta, rota que aceita cookie, rota em que o
cliente escolhe a clínica ou o paciente, rota fora da documentação e rota que traz de
volta funções que pertencem ao aplicativo da clínica.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from api import api

DOC = Path(__file__).resolve().parent.parent / "docs" / "mobile-patient-api.md"
PUBLIC_OPERATIONS = {
    ("post", "/api/v1/mobile/auth/login/"),
    ("post", "/api/v1/mobile/auth/refresh/"),
    ("post", "/api/v1/mobile/auth/activate/"),
    ("post", "/api/v1/mobile/auth/activate-otp/"),
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
    assert len(_operations()) >= 30


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
