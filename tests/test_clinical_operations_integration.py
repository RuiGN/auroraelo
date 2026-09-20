"""Registro e fronteira HTTP no projeto real, somente dados sintéticos."""

from typing import cast

import pytest
from django.apps import apps
from django.middleware.csrf import get_token
from django.test import Client, RequestFactory
from django.urls import resolve
from pytest_django.fixtures import SettingsWrapper

from accounts.models import User
from clinical_operations.forms import COMMANDS
from clinics.models import Clinic
from clinics.typing import ClinicRequest


def test_main_settings_register_clinical_operations() -> None:
    assert apps.is_installed("clinical_operations")


def test_clinical_operations_are_disabled_by_default(settings: SettingsWrapper) -> None:
    assert settings.CLINICAL_OPERATIONS_ENABLED is False


def test_main_route_is_unavailable_while_disabled(
    client: Client, settings: SettingsWrapper
) -> None:
    settings.CLINICAL_OPERATIONS_ENABLED = False
    response = client.get("/api/v1/clinical-operations/products/")
    assert response.status_code == 503
    assert response.json() == {"error": "clinical_operations_disabled"}
    assert "no-store" in response.headers["Cache-Control"]


@pytest.mark.parametrize("resource", tuple(COMMANDS))
def test_enabled_main_routes_still_require_authentication(
    client: Client, settings: SettingsWrapper, resource: str
) -> None:
    settings.CLINICAL_OPERATIONS_ENABLED = True
    response = client.get(f"/api/v1/clinical-operations/{resource}/")
    assert response.status_code == 401
    assert response.json() == {"error": "authentication_required"}


@pytest.mark.parametrize("resource", tuple(COMMANDS))
def test_disabled_view_denies_authenticated_writes_without_database(
    rf: RequestFactory, settings: SettingsWrapper, resource: str
) -> None:
    settings.CLINICAL_OPERATIONS_ENABLED = False
    url = f"/api/v1/clinical-operations/{resource}/"
    request = cast(ClinicRequest, rf.post(url, {}, content_type="application/json"))
    token = get_token(request)
    request.COOKIES["csrftoken"] = token
    request.META["HTTP_X_CSRFTOKEN"] = token
    request.user = User(username="operador-sintetico")
    request.clinic = Clinic(name="Clínica sintética", slug="clinica-sintetica")
    # Sem django_db: qualquer tentativa de consulta/gravação também reprova.
    match = resolve(url)
    assert match.func(request, **match.kwargs).status_code == 503
