"""Limites JSON via HTTP real, com sessão e dados exclusivamente sintéticos."""

from __future__ import annotations

from typing import Never
from unittest.mock import patch

import pytest
from django.db import connection
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client
from django.test.utils import CaptureQueriesContext
from pytest_django.fixtures import SettingsWrapper

from accounts.services import register_current_session
from clinical_operations.forms import COMMANDS
from clinical_operations.models import Product
from tests import test_clinical_operations as operation_fixtures
from tests.test_clinical_operations import ClinicalContext

context = operation_fixtures.context
pytestmark = pytest.mark.django_db


@pytest.fixture
def strict_client(
    context: ClinicalContext, settings: SettingsWrapper
) -> tuple[Client, dict[str, str]]:
    clinic, _, professional, _ = context
    settings.CLINICAL_OPERATIONS_ENABLED = True
    settings.ACCOUNT_SESSION_ALLOW_UNKNOWN = False
    client = Client(enforce_csrf_checks=True)
    client.force_login(professional)
    request = HttpRequest()
    request.session = client.session
    register_current_session(request=request, user=professional)
    token = get_token(request)
    client.cookies[settings.CSRF_COOKIE_NAME] = token
    return client, {"X-CSRFToken": token, "X-Clinic-ID": str(clinic.pk)}


@pytest.mark.parametrize("resource", tuple(COMMANDS))
@pytest.mark.parametrize("shape", ["array", "object"])
@pytest.mark.parametrize("depth_case", ["reported", "near_byte_limit"])
def test_deep_json_is_generic_400_without_domain_writes(
    strict_client: tuple[Client, dict[str, str]],
    resource: str,
    shape: str,
    depth_case: str,
) -> None:
    client, headers = strict_client
    opening, closing = ("[", "]") if shape == "array" else ('{"v":', "}")
    envelope = '{"name":0,"sku":"SYNTH-DEPTH"}'
    depth = (
        2000
        if depth_case == "reported"
        else (16383 - len(envelope)) // (len(opening) + len(closing))
    )
    nested = opening * depth + "0" + closing * depth
    body = ('{"name":' + nested + ',"sku":"SYNTH-DEPTH"}').encode()
    assert len(body) < 16384, "Corpo deve ficar abaixo do limite de bytes."
    client.raise_request_exception = False
    with CaptureQueriesContext(connection) as queries:
        response = client.post(
            f"/api/v1/clinical-operations/{resource}/",
            body,
            content_type="application/json",
            headers=headers,
        )
    domain_writes = [
        query["sql"]
        for query in queries
        if query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and ("clinical_operations_" in query["sql"] or "audit_" in query["sql"])
    ]
    assert not domain_writes
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_payload"}
    assert "no-store" in response.headers["Cache-Control"]
    assert "SYNTH-DEPTH" not in response.content.decode()


def test_parser_recursion_error_returns_generic_400(
    strict_client: tuple[Client, dict[str, str]],
) -> None:
    """Falha injetada só no parser; não alega 500 por payload real neste Python."""
    client, headers = strict_client
    client.raise_request_exception = False
    with (
        patch("clinical_operations.views.json") as parser,
        CaptureQueriesContext(connection) as queries,
    ):
        parser.loads.side_effect = RecursionError("Parser sintético")
        response = client.post(
            "/api/v1/clinical-operations/products/",
            {"name": "Produto sintético", "sku": "SYNTH-PARSER"},
            content_type="application/json",
            headers=headers,
        )
    parser.loads.assert_called_once()
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and ("clinical_operations_" in query["sql"] or "audit_" in query["sql"])
        for query in queries
    )
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_payload"}
    assert "no-store" in response.headers["Cache-Control"]


def test_valid_json_control_still_persists(
    strict_client: tuple[Client, dict[str, str]], context: ClinicalContext
) -> None:
    client, headers = strict_client
    response = client.post(
        "/api/v1/clinical-operations/products/",
        {"name": "Produto sintético", "sku": "SYNTH-CONTROL"},
        content_type="application/json",
        headers=headers,
    )
    assert response.status_code == 201
    product = Product.infrastructure_objects.get(
        clinic_id=context[0].pk, pk=response.json()["id"]
    )
    assert product.name == "Produto sintético"
    assert product.sku == "SYNTH-CONTROL"


def test_service_recursion_error_is_not_mislabeled_as_invalid_json(
    strict_client: tuple[Client, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, headers = strict_client

    def broken_service(**kwargs: object) -> Never:
        raise RecursionError("Falha interna sintética")

    monkeypatch.setitem(COMMANDS, "products", (broken_service, COMMANDS["products"][1]))
    with pytest.raises(RecursionError, match="Falha interna sintética"):
        client.post(
            "/api/v1/clinical-operations/products/",
            {"name": "Produto sintético", "sku": "SYNTH-SERVICE"},
            content_type="application/json",
            headers=headers,
        )
