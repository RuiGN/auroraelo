"""Fronteiras reais de middleware do portal clínico, com dados sintéticos."""

from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse

from clinics.middleware import is_tenant_exempt_path
from psychiatry.urls import urlpatterns
from tests.factories import UserFactory

PUBLIC_PATHS = ("/psiquiatria/login/",)
EXEMPT_PATHS = PUBLIC_PATHS
TENANT_PATHS = tuple(
    path
    for pattern in urlpatterns
    if (path := f"/psiquiatria/{pattern.pattern}") not in EXEMPT_PATHS
)


def test_only_expected_psychiatry_paths_are_tenant_independent() -> None:
    paths = {f"/psiquiatria/{pattern.pattern}" for pattern in urlpatterns}
    assert len(paths) == 19
    assert {path for path in paths if is_tenant_exempt_path(path)} == set(EXEMPT_PATHS)


@pytest.mark.parametrize("path", EXEMPT_PATHS)
def test_tenant_exceptions_never_match_a_prefix_or_similar_path(path: str) -> None:
    assert is_tenant_exempt_path(path)
    assert not is_tenant_exempt_path(path + "extra/")
    assert not is_tenant_exempt_path(path.rstrip("/"))
    assert not is_tenant_exempt_path("/x" + path)


@pytest.mark.django_db
@pytest.mark.parametrize("path", EXEMPT_PATHS)
def test_tenant_independent_route_ignores_stale_clinic_selection(
    client: Client, path: str
) -> None:
    client.force_login(UserFactory.create())
    session = client.session
    session["active_clinic_id"] = "selecao-invalida-sintetica"
    session.save()
    response = client.get(path, headers={"X-Clinic-ID": str(uuid4())})
    if path == "/psiquiatria/login/":
        assert response.status_code == 302
        assert response.headers["Location"] == reverse("account_login")
    else:
        assert response.status_code == 200
    assert client.session["active_clinic_id"] == "selecao-invalida-sintetica"


@pytest.mark.django_db
@pytest.mark.parametrize("path", TENANT_PATHS)
def test_clinical_portal_still_requires_tenant(
    client: Client, path: str
) -> None:
    client.force_login(UserFactory.create())
    response = client.get(path)
    assert response.status_code == 400
    assert response.json() == {"detail": "Selecione uma clínica para continuar."}
