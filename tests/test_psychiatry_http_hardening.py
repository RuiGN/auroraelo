"""Cache HTTP privado e números hostis, somente com registros sintéticos."""

import json
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client, RequestFactory
from django.urls import resolve

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from psychiatry.models import PsychiatricCrisisAlert, PsychiatricPatientProfile
from psychiatry.urls import urlpatterns
from psychiatry.validation import number

pytestmark = pytest.mark.django_db


def assert_private_cache(response):
    directives = set(response.headers.get("Cache-Control", "").split(", "))
    assert {
        "private",
        "no-store",
        "no-cache",
        "must-revalidate",
        "max-age=0",
    } <= directives
    assert "public" not in directives
    assert "Expires" in response.headers


@pytest.fixture
def patient_context():
    clinic = Clinic.infrastructure_objects.create(name="Clínica Sintética", slug="http")
    actor = User.objects.create_user(email="patient-http@example.test")
    ClinicMembership.infrastructure_objects.create(
        clinic=clinic, user=actor, role="patient", valid_from=date.today()
    )
    patient = PsychiatricPatientProfile.objects.create(
        clinic=clinic,
        user=actor,
        full_name="Paciente Sintético HTTP",
        cpf="synthetic-http",
        date_of_birth=date(1990, 1, 1),
        phone="",
        record_number="http-synthetic",
    )
    return clinic, actor, patient


def send(
    transport, path, *, actor=None, clinic=None, method="get", data=None, csrf=True
):
    from django.contrib.auth.models import AnonymousUser

    headers = {}
    if clinic is not None:
        headers["X-Clinic-ID"] = str(clinic.pk)
    token_request = HttpRequest()
    token = get_token(token_request)
    if csrf:
        headers["X-CSRFToken"] = token
    if transport == "client":
        client = Client(enforce_csrf_checks=True)
        if actor is not None:
            client.force_login(actor)
        if csrf:
            client.cookies["csrftoken"] = token_request.META["CSRF_COOKIE"]
        return getattr(client, method)(
            path, data=data, content_type="application/json", headers=headers
        )
    request = getattr(RequestFactory(), method)(
        path,
        data=json.dumps(data) if method != "get" else data,
        content_type="application/json",
        headers=headers,
    )
    request.user = actor if actor is not None else AnonymousUser()
    request.clinic = clinic
    request.session = {}
    if csrf:
        request.COOKIES["csrftoken"] = token_request.META["CSRF_COOKIE"]
    return resolve(path).func(request)


# Inventário derivado das rotas reais: inclui HTML, APIs e todos os aliases.
# O web é só da equipe: não há rotas de paciente.
PRIVATE_ROUTES = [
    (f"/psiquiatria/{route.pattern}", route.callback.__name__)
    for route in urlpatterns
    if route.callback.__name__ != "login_view"
]
POST_ONLY = {
    "save_anamnesis",
    "api_save_12steps_step",
    "api_consolidate_12steps",
}


@pytest.fixture
def clinical_context(patient_context):
    from uuid import uuid4

    from consents.services import record_consent_manifestation
    from people.models import CareRelationship
    from psychiatry.models import TwelveStepsAnamnesis
    from tests.test_versioned_consents import publish_document

    clinic, patient_actor, patient = patient_context
    actors = {}
    for role in ("therapist", "clinic_admin", "administrative_staff"):
        actor = User.objects.create_user(email=f"{role}-http@example.test")
        ClinicMembership.infrastructure_objects.create(
            clinic=clinic, user=actor, role=role, valid_from=date.today()
        )
        actors[role] = actor
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=actors["therapist"],
        patient=patient_actor,
        valid_from=date.today(),
    )
    document = publish_document(clinic=clinic, actor=actors["clinic_admin"])
    record_consent_manifestation(
        clinic_id=clinic.pk,
        actor=patient_actor,
        subject_id=patient_actor.pk,
        document_id=document.pk,
        decision="accepted",
        request_id=uuid4(),
    )
    draft = TwelveStepsAnamnesis.objects.create(
        patient=patient,
        author=actors["therapist"],
        draft_steps={"step_1": {"answer": "Rascunho sintético HTTP"}},
    )
    return clinic, patient_actor, actors, draft


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize("path,view_name", PRIVATE_ROUTES)
def test_all_private_get_responses_are_never_cached(
    clinical_context, transport, path, view_name
):
    clinic, patient_actor, actors, draft = clinical_context
    actor = actors["therapist"]
    data = (
        {"session_id": str(draft.uuid)}
        if view_name == "api_get_12steps_draft"
        else None
    )
    response = send(transport, path, actor=actor, clinic=clinic, data=data)
    assert response.status_code == (405 if view_name in POST_ONLY else 200)
    assert_private_cache(response)
    if view_name == "api_get_12steps_draft":
        assert json.loads(response.content)["draft"]["steps"] == draft.draft_steps


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize("path,view_name", PRIVATE_ROUTES)
def test_all_private_anonymous_errors_are_never_cached(transport, path, view_name):
    response = send(transport, path)
    assert response.status_code == 401
    assert_private_cache(response)


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize("path,view_name", PRIVATE_ROUTES)
def test_all_private_inactive_actor_errors_are_never_cached(
    patient_context, transport, path, view_name
):
    clinic, actor, _ = patient_context
    User.objects.filter(pk=actor.pk).update(is_active=False)
    response = send(transport, path, actor=actor, clinic=clinic)
    # O backend do Client anonimiza; RequestFactory conserva a instância obsoleta.
    assert response.status_code == (401 if transport == "client" else 403)
    assert_private_cache(response)


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize(
    "path",
    [
        p
        for p, name in PRIVATE_ROUTES
        if name in POST_ONLY
    ],
)
def test_local_csrf_rejections_are_never_cached_but_global_csrf_preempts(
    clinical_context, transport, path, record_property
):
    clinic, _, actors, _ = clinical_context
    actor = actors["therapist"]
    response = send(
        transport, path, actor=actor, clinic=clinic, method="post", data={}, csrf=False
    )
    assert response.status_code == 403
    assert not getattr(resolve(path).func, "csrf_exempt", False)
    if transport == "factory":
        assert_private_cache(response)
    else:
        # CsrfViewMiddleware global responde antes de domain_access/never_cache.
        record_property("outer_csrf_cache_control", response.get("Cache-Control", ""))


ERROR_CASES = [
    ("clinic/patients/", "get", {"limit": "101"}, 400),
    ("patients/", "get", {"limit": "101"}, 400),
    ("adictologia/dashboard/", "get", {"limit": "101"}, 400),
    ("adictologia/12-passos/draft/", "get", {"session_id": "invalid"}, 400),
    (
        "adictologia/12-passos/draft/",
        "get",
        {"session_id": "00000000-0000-0000-0000-000000000001"},
        404,
    ),
]


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize("endpoint,method,data,status", ERROR_CASES)
def test_private_validation_not_found_size_and_unavailable_errors_are_never_cached(
    clinical_context, transport, endpoint, method, data, status
):
    clinic, _, actors, _ = clinical_context
    path = "/psiquiatria/api/v1/" + endpoint
    actor = actors["therapist"]
    response = send(
        transport, path, actor=actor, clinic=clinic, method=method, data=data
    )
    assert response.status_code == status
    assert_private_cache(response)


@pytest.mark.parametrize("state", ["csrf", "revoked_session", "missing_tenant"])
def test_outer_middleware_stops_before_private_decorator(
    clinical_context, state, monkeypatch, record_property
):
    from django.utils import timezone

    from accounts.models import AccountSession
    from psychiatry import policies

    clinic, _, actors, _ = clinical_context
    actor = actors["therapist"]
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    path = "/psiquiatria/api/v1/clinic/patients/"
    assert client.get(path).status_code == 200
    if state == "revoked_session":
        AccountSession.objects.filter(user=actor).update(revoked_at=timezone.now())
    elif state == "missing_tenant":
        ClinicMembership.infrastructure_objects.filter(user=actor).delete()

    def unexpected_entry(**kwargs):
        pytest.fail("O middleware deveria interromper antes do decorator privado.")

    monkeypatch.setattr(policies, "require_domain_access", unexpected_entry)
    response = (
        client.post(path, {}, content_type="application/json")
        if state == "csrf"
        else client.get(path)
    )
    assert (
        response.status_code
        == {"csrf": 403, "revoked_session": 302, "missing_tenant": 403}[state]
    )
    assert not PsychiatricCrisisAlert.objects.exists()
    record_property("outer_middleware_cache_control", response.get("Cache-Control", ""))
    # A próxima leitura anônima chega ao decorator e já possui no-store.
    if state == "revoked_session":
        monkeypatch.undo()
        response = client.get(path)
        assert response.status_code == 401
        assert_private_cache(response)


@pytest.mark.parametrize("transport", ["client", "factory"])
@pytest.mark.parametrize(
    "path",
    [p for p, name in PRIVATE_ROUTES],
)
def test_active_wrong_role_errors_are_never_cached(clinical_context, transport, path):
    clinic, _, actors, _ = clinical_context
    response = send(
        transport, path, actor=actors["administrative_staff"], clinic=clinic
    )
    assert response.status_code == 403
    assert_private_cache(response)


@pytest.mark.parametrize(
    "value",
    [True, False, None, "8", [], {}, float("nan"), float("inf"), -float("inf"), -1, 25],
)
def test_number_keeps_strict_type_finiteness_and_bounds(value):
    with pytest.raises(ValidationError):
        number({"value": value}, "value", 0, 24)


@pytest.mark.parametrize("value", [0, 0.0, 8, 8.5, 24, 24.0])
def test_number_keeps_valid_integer_and_fractional_boundaries(value):
    assert number({"value": value}, "value", 0, 24) == value
