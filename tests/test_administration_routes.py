"""Fronteira HTTP da administração global, separada dos tenants."""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.test import Client, RequestFactory, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.models import AccountSession
from clinics.models import ClinicMembership
from tests.factories import ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


def test_administration_has_its_own_route(client: Client) -> None:
    user = UserFactory.create(is_staff=True)
    client.force_login(user)
    response = client.get("/administracao/")
    assert response.status_code == 200
    assert reverse("administration:user_list") == "/administracao/"
    assert "Usuários e equipe" in response.content.decode()


@pytest.mark.parametrize("identity", ["anonymous", "member", "inactive"])
@pytest.mark.parametrize(
    "suffix", ["", "convites/", "vinculos/{id}/", "convites/{id}/revogar/"]
)
def test_administration_denies_non_operators(
    client: Client, identity: str, suffix: str
) -> None:
    if identity != "anonymous":
        client.force_login(
            UserFactory.create(
                is_staff=identity == "inactive", is_active=identity != "inactive"
            )
        )
    path = "/administracao/" + suffix.format(id=uuid4())
    response = client.post(path) if "revogar" in suffix else client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/master/login/?next=")


def test_legacy_user_route_redirects_but_cannot_mutate(client: Client) -> None:
    client.force_login(UserFactory.create(is_staff=True))
    response = client.get("/master/users/")
    assert response.status_code == 302
    assert response.headers["Location"] == "/administracao/"
    assert client.post("/master/users/invite/").status_code == 405


def test_administration_mutations_require_csrf() -> None:
    client = Client(enforce_csrf_checks=True)
    client.force_login(UserFactory.create(is_staff=True))
    assert client.post("/administracao/convites/").status_code == 403
    assert client.post(f"/administracao/convites/{uuid4()}/revogar/").status_code == 403


@pytest.mark.parametrize(
    ("destination", "expected"),
    [
        ("/administracao/", "/administracao/"),
        ("https://outside.invalid/", "/master/"),
        ("//outside.invalid/", "/master/"),
    ],
)
def test_master_login_returns_to_safe_destination(
    client: Client, destination: str, expected: str
) -> None:
    user = UserFactory.create(is_staff=True)
    user.set_password("synthetic-login-test-only")
    user.save()
    response = client.post(
        reverse("master_login") + "?next=" + destination,
        {"email": user.email, "password": "synthetic-login-test-only"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == expected


@pytest.mark.parametrize(
    "suffix", ["", "convites/", "vinculos/{id}/", "convites/{id}/revogar/"]
)
def test_clinic_admin_cannot_call_global_views_directly(suffix: str) -> None:
    actor = UserFactory.create(is_staff=False, is_superuser=False)
    ClinicMembershipFactory.create(user=actor, role=ClinicMembership.Role.CLINIC_ADMIN)
    path = "/administracao/" + suffix.format(id=uuid4())
    request = RequestFactory().post(path)
    request.user = actor
    match = resolve(path)
    response = match.func(request, **match.kwargs)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/master/login/?next=")


@override_settings(ACCOUNT_SESSION_ALLOW_UNKNOWN=False)
@pytest.mark.parametrize("state", ["unknown", "revoked", "expired"])
@pytest.mark.parametrize(
    "suffix", ["", "convites/", "vinculos/{id}/", "convites/{id}/revogar/"]
)
def test_administration_requires_valid_managed_session(
    client: Client, state: str, suffix: str
) -> None:
    user = UserFactory.create(is_staff=True)
    if state == "unknown":
        client.force_login(user)
    else:
        user.set_password("synthetic-managed-session-only")
        user.save()
        response = client.post(
            reverse("master_login"),
            {"email": user.email, "password": "synthetic-managed-session-only"},
        )
        assert response.status_code == 302
        assert client.get("/administracao/").status_code == 200
        tracked = AccountSession.objects.get(user=user)
        if state == "revoked":
            tracked.revoked_at = timezone.now()
            tracked.save(update_fields=("revoked_at",))
        else:
            tracked.absolute_expires_at = timezone.now() - timedelta(seconds=1)
            tracked.save(update_fields=("absolute_expires_at",))
    path = "/administracao/" + suffix.format(id=uuid4())
    response = client.post(path) if suffix else client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("account_login")
