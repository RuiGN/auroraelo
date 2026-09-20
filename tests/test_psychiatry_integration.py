"""Fronteiras reais de middleware para B2C, com dados apenas sintéticos."""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pytest_django.fixtures import SettingsWrapper

from accounts.models import AccountSession
from clinics.middleware import is_tenant_exempt_path
from psychiatry.models import B2CCBTDiary, B2CMindLog, B2CSubscription
from psychiatry.urls import urlpatterns
from tests.factories import UserFactory

PRIVATE_PATHS = tuple(
    f"/psiquiatria/api/v1/{prefix}/{resource}/"
    for prefix in ("mind", "mobile/b2c")
    for resource in ("mood", "cbt-diary", "subscription")
)
PUBLIC_PATHS = (
    "/psiquiatria/login/",
    "/psiquiatria/api/v1/mind/breathing/",
    "/psiquiatria/api/v1/mobile/b2c/breathing/",
)
EXEMPT_PATHS = (*PUBLIC_PATHS, *PRIVATE_PATHS)
TENANT_PATHS = tuple(
    path
    for pattern in urlpatterns
    if (path := f"/psiquiatria/{pattern.pattern}") not in EXEMPT_PATHS
)


@pytest.mark.django_db
def test_b2c_mood_works_without_a_clinic(client: Client) -> None:
    actor = UserFactory.create()
    client.force_login(actor)
    response = client.get("/psiquiatria/api/v1/mind/mood/")
    assert response.status_code == 200
    assert response.json()["history"] == []


def test_only_expected_psychiatry_paths_are_tenant_independent() -> None:
    paths = {f"/psiquiatria/{pattern.pattern}" for pattern in urlpatterns}
    assert len(paths) == 36
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
def test_clinical_connected_and_legacy_html_still_require_tenant(
    client: Client, path: str
) -> None:
    client.force_login(UserFactory.create())
    response = client.get(path)
    assert response.status_code == 400
    assert response.json() == {"detail": "Selecione uma clínica para continuar."}


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRIVATE_PATHS)
def test_private_b2c_aliases_deny_anonymous_and_inactive_users(
    client: Client, path: str
) -> None:
    assert client.get(path).status_code == 401
    client.force_login(UserFactory.create(is_active=False))
    assert client.get(path).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRIVATE_PATHS)
def test_private_b2c_aliases_do_not_bypass_session_validation(
    client: Client, settings: SettingsWrapper, path: str
) -> None:
    settings.ACCOUNT_SESSION_ALLOW_UNKNOWN = False
    client.force_login(UserFactory.create())
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("account_login")


@pytest.mark.django_db
def test_tracked_b2c_session_revocation_is_enforced(client: Client) -> None:
    actor = UserFactory.create()
    client.force_login(actor)
    url = "/psiquiatria/api/v1/mind/mood/"
    assert client.get(url).status_code == 200
    tracked = AccountSession.objects.get(user=actor)
    tracked.revoked_at = timezone.now()
    tracked.save(update_fields=("revoked_at",))
    response = client.get(url)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("account_login")


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRIVATE_PATHS)
def test_private_b2c_writes_still_require_real_csrf(path: str) -> None:
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(UserFactory.create())
    assert strict.post(path, {}, content_type="application/json").status_code == 403
    assert not B2CMindLog.objects.exists()
    assert not B2CCBTDiary.objects.exists()
    assert not B2CSubscription.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("prefix", ("mind", "mobile/b2c"))
def test_real_b2c_writes_and_reads_are_owned_without_tenant(prefix: str) -> None:
    actor, other = UserFactory.create(), UserFactory.create()
    B2CMindLog.objects.create(user=other, user_identifier=str(other.pk))
    B2CMindLog.objects.create(user_identifier=str(actor.pk))
    B2CCBTDiary.objects.create(user=other, user_identifier=str(other.pk))
    B2CCBTDiary.objects.create(user_identifier=str(actor.pk))
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(actor)
    token = get_token(HttpRequest())
    strict.cookies["csrftoken"] = token
    base = f"/psiquiatria/api/v1/{prefix}/"
    mood_payload = {
        "mood": "CALM",
        "anxiety_score": 0,
        "energy_score": 1,
        "sleep_hours": 0,
    }
    mood = strict.post(
        base + "mood/",
        mood_payload,
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert mood.status_code == 200
    assert mood.json()["persisted"] is True
    assert B2CMindLog.objects.get(pk=mood.json()["id"]).user_id == actor.pk
    assert [row["id"] for row in strict.get(base + "mood/").json()["history"]] == [
        mood.json()["id"]
    ]
    diary = strict.post(
        base + "cbt-diary/",
        {"trigger": "Sintético", "thought": "Sintético", "before": 0, "after": 0},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert diary.status_code == 200
    assert diary.json()["persisted"] is True
    assert B2CCBTDiary.objects.get(pk=diary.json()["id"]).user_id == actor.pk
    assert [row["id"] for row in strict.get(base + "cbt-diary/").json()["entries"]] == [
        diary.json()["id"]
    ]
    forged = strict.post(
        base + "mood/",
        {**mood_payload, "user_id": str(other.pk)},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert forged.status_code == 400
    assert B2CMindLog.objects.filter(user=actor).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("prefix", ("mind", "mobile/b2c"))
def test_subscription_does_not_adopt_legacy_or_other_owner(prefix: str) -> None:
    actor, other = UserFactory.create(), UserFactory.create()
    for owner, identifier in ((None, str(actor.pk)), (other, str(other.pk))):
        B2CSubscription.objects.create(
            user=owner,
            user_identifier=identifier,
            plan="PLUS_ANNUAL",
            platform="DIRECT",
            is_active=True,
            valid_until=timezone.now() + timedelta(days=1),
        )
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(actor)
    url = f"/psiquiatria/api/v1/{prefix}/subscription/"
    assert strict.get(url).json() == {
        "success": True,
        "plan": "FREE",
        "is_active": False,
    }
    token = get_token(HttpRequest())
    strict.cookies["csrftoken"] = token
    response = strict.post(
        url,
        {"plan": "PLUS_ANNUAL", "platform": "DIRECT"},
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 503
    assert not B2CSubscription.objects.filter(user=actor).exists()
