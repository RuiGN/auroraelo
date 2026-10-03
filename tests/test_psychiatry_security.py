"""Segurança local do domínio com identidades e registros sintéticos."""

import json
from datetime import date

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from psychiatry import api, urls
from psychiatry.models import PsychiatricPatientProfile

pytestmark = pytest.mark.django_db


def profile(**overrides):
    from uuid import uuid4

    marker = uuid4().hex[:10]
    values = dict(
        full_name="Paciente Sintético",
        cpf=marker,
        date_of_birth=date(1990, 1, 1),
        phone="",
        record_number=marker,
    )
    values.update(overrides)
    return PsychiatricPatientProfile.objects.create(**values)


def test_legacy_profile_is_not_returned_or_counted(identities):
    clinic, _, actors = identities
    profile(tcle_signed=True)
    response = request_for(api.list_patients, actor=actors["therapist"], clinic=clinic)
    assert json.loads(response.content)["patients"] == []
    response = request_for(
        api.clinic_dashboard_kpis, actor=actors["therapist"], clinic=clinic
    )
    assert json.loads(response.content)["data"]["active_patients"] == 0


def test_new_ownership_fields_are_nullable_and_consent_is_opt_in():
    p = profile()
    assert hasattr(p, "clinic_id") and hasattr(p, "user_id")
    assert p.clinic_id is None and p.user_id is None
    assert p.tcle_signed is False


def test_profile_scopes_require_care_relationship(identities):
    from people.models import CareRelationship

    grant_follow_up(identities)

    clinic, other, actors = identities
    own = profile(clinic=clinic, user=actors["patient"])
    profile(clinic=other, user=actors["patient"])
    profile(clinic=clinic)
    response = request_for(api.list_patients, actor=actors["therapist"], clinic=clinic)
    assert json.loads(response.content)["patients"] == []
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=actors["therapist"],
        patient=actors["patient"],
        valid_from=date.today(),
    )
    response = request_for(api.list_patients, actor=actors["therapist"], clinic=clinic)
    assert [p["uuid"] for p in json.loads(response.content)["patients"]] == [
        str(own.uuid)
    ]


@pytest.fixture
def own_profile(identities):
    clinic, _, actors = identities
    return profile(clinic=clinic, user=actors["patient"])


@pytest.fixture
def prescribed(own_profile):
    from datetime import timedelta

    from psychiatry.models import PrescriptionItem, PsychopharmacologyPrescription

    rx = PsychopharmacologyPrescription.objects.create(
        patient=own_profile, expires_date=date.today() + timedelta(days=7)
    )
    return PrescriptionItem.objects.create(
        prescription=rx, drug_name="Sintético", dosage="1", posology="Teste"
    )


def test_anamnesis_never_resolves_by_cpf(identities):
    response = request_for(
        api.save_anamnesis,
        actor=identities[2]["therapist"],
        clinic=identities[0],
        method="post",
        data={"cpf": "legacy", "full_name": "Inventado"},
    )
    assert response.status_code == 400
    assert PsychiatricPatientProfile.objects.count() == 0


@pytest.fixture
def linked_profile(identities, own_profile):
    from people.models import CareRelationship

    CareRelationship.infrastructure_objects.create(
        clinic=identities[0],
        therapist=identities[2]["therapist"],
        patient=identities[2]["patient"],
        valid_from=date.today(),
    )
    return own_profile


def test_drafts_persist_with_server_identity_and_isolated_scope(
    identities, linked_profile, monkeypatch
):
    from psychiatry import redis_service

    grant_follow_up(identities)
    monkeypatch.setattr(redis_service, "get_redis_client", lambda: None)
    actor = identities[2]["therapist"]
    clinic = identities[0]
    payload = {
        "patient_id": str(linked_profile.uuid),
        "step_number": 1,
        "step_data": {"answer": "Relato sintético"},
    }
    response = request_for(
        api.api_save_12steps_step,
        actor=actor,
        clinic=clinic,
        method="post",
        data=payload,
    )
    assert response.status_code == 200
    saved = json.loads(response.content)
    assert saved["persisted"] is True
    session_id = saved["session_id"]
    response = request_for(
        api.api_get_12steps_draft,
        actor=actor,
        clinic=clinic,
        data={"session_id": session_id},
    )
    assert (
        json.loads(response.content)["draft"]["steps"]["step_1"]["answer"]
        == "Relato sintético"
    )
    assert (
        request_for(
            api.api_get_12steps_draft,
            actor=actor,
            clinic=identities[1],
            data={"session_id": session_id},
        ).status_code
        == 403
    )
    payload = {"session_id": session_id}
    response = request_for(
        api.api_consolidate_12steps,
        actor=actor,
        clinic=clinic,
        method="post",
        data=payload,
    )
    assert response.status_code == 200
    assert json.loads(response.content)["ai_processed"] is False
    from psychiatry.models import TwelveStepsAnamnesis

    entry = TwelveStepsAnamnesis.objects.get()
    assert entry.patient == linked_profile
    assert entry.step1_powerlessness == "Relato sintético"
    assert entry.step2_restoration_hope == ""
    assert entry.ai_prevention_plan == ""
    assert entry.author_id == actor.pk


@pytest.mark.parametrize(
    "kwargs",
    [{"session_id": "guess"}, {"session_id": "00000000-0000-0000-0000-000000000001"}],
)
def test_draft_unknown_or_malformed_ids_denied(identities, kwargs, monkeypatch):
    from psychiatry import redis_service

    monkeypatch.setattr(redis_service, "get_redis_client", lambda: None)
    response = request_for(
        api.api_get_12steps_draft,
        actor=identities[2]["therapist"],
        clinic=identities[0],
        data=kwargs,
    )
    assert response.status_code in (400, 404)


def test_unscoped_legacy_helpers_are_disabled_before_queries(django_assert_num_queries):
    from psychiatry.tasks import (
        consolidate_twelve_steps_task,
        generate_ai_relapse_prevention_plan_task,
        notify_urgent_craving_alert_task,
    )

    with django_assert_num_queries(0):
        assert generate_ai_relapse_prevention_plan_task(123)["status"] == "disabled"
        assert (
            consolidate_twelve_steps_task("old-session", "old-cpf")["status"]
            == "disabled"
        )
        assert (
            notify_urgent_craving_alert_task("old-cpf", 9, "alcohol")[
                "notification_delivered"
            ]
            is False
        )


def test_unscoped_redis_helpers_cannot_read_or_write(monkeypatch):
    from django.core.exceptions import PermissionDenied

    from psychiatry import redis_service

    monkeypatch.setattr(redis_service, "get_redis_client", lambda: None)
    with pytest.raises(PermissionDenied):
        redis_service.TwelveStepsRedisService.save_step_draft(
            "guess", 1, {"answer": "x"}
        )
    with pytest.raises(PermissionDenied):
        redis_service.TwelveStepsRedisService.get_session_draft("guess")


def test_addiction_kpis_no_demo_and_tenant_scope(identities):
    from psychiatry.models import AddictionProfile

    AddictionProfile.objects.create(patient=profile())
    response = request_for(
        api.api_addiction_dashboard_kpis,
        actor=identities[2]["therapist"],
        clinic=identities[0],
    )
    assert json.loads(response.content)["data"]["total_recovery_patients"] == 0


def test_html_context_never_includes_legacy_profiles(identities, monkeypatch):
    from django.http import HttpResponse

    from psychiatry import views
    from psychiatry.models import AddictionProfile

    AddictionProfile.objects.create(patient=profile())
    contexts = []

    def capture(request, template, context):
        contexts.append(context)
        return HttpResponse("ok")

    monkeypatch.setattr(views, "render", capture)
    for view in (
        views.dashboard_view,
        views.addiction_dashboard_view,
        views.twelve_steps_anamnesis_view,
    ):
        assert (
            request_for(
                view, actor=identities[2]["therapist"], clinic=identities[0]
            ).status_code
            == 200
        )
    assert contexts[0]["active_patients_count"] == 0
    assert list(contexts[1]["profiles"]) == []
    assert contexts[1]["total_patients"] == 0
    assert list(contexts[2]["patients"]) == []


def grant_follow_up(identities):
    from uuid import uuid4

    from consents.services import record_consent_manifestation
    from tests.test_versioned_consents import publish_document

    clinic, _, actors = identities
    document = publish_document(clinic=clinic, actor=actors["clinic_admin"])
    record_consent_manifestation(
        clinic_id=clinic.pk,
        actor=actors["patient"],
        subject_id=actors["patient"].pk,
        document_id=document.pk,
        decision="accepted",
        request_id=uuid4(),
    )
    return document


def test_legacy_tcle_true_is_not_reconfirmed_consent(identities, linked_profile):
    from uuid import uuid4

    linked_profile.tcle_signed = True
    linked_profile.save()

    def listing():
        return json.loads(
            request_for(
                api.list_patients,
                actor=identities[2]["therapist"],
                clinic=identities[0],
            ).content
        )["patients"]

    assert listing() == []
    document = grant_follow_up(identities)
    assert len(listing()) == 1
    from consents.services import revoke_consent

    revoke_consent(
        clinic_id=identities[0].pk,
        actor=identities[2]["patient"],
        subject_id=identities[2]["patient"].pk,
        document_id=document.pk,
        reason="Teste sintético",
        request_id=uuid4(),
    )
    assert listing() == []


def test_empty_list_and_filters_do_not_return_demo(identities, linked_profile):
    grant_follow_up(identities)
    response = request_for(
        api.list_patients,
        actor=identities[2]["therapist"],
        clinic=identities[0],
        data={"q": "does-not-match"},
    )
    assert json.loads(response.content)["patients"] == []
    for params in ({"limit": "101"}, {"risk": "BOGUS"}, {"status": "BOGUS"}):
        assert (
            request_for(
                api.list_patients,
                actor=identities[2]["therapist"],
                clinic=identities[0],
                data=params,
            ).status_code
            == 400
        )


def test_anamnesis_author_is_authenticated_and_no_fabricated_mse(
    identities, linked_profile
):
    from psychiatry.models import PsychiatricEvaluation

    grant_follow_up(identities)
    data = {
        "patient_id": str(linked_profile.uuid),
        "chief_complaint": "Sintético",
        "hda": "Sintético",
        "anxiety_scale": 0,
        "risk_level": "LOW",
        "diagnostic_impression": "Sintético",
        "therapeutic_plan": "Sintético",
    }
    response = request_for(
        api.save_anamnesis,
        actor=identities[2]["therapist"],
        clinic=identities[0],
        method="post",
        data=data,
    )
    assert response.status_code == 200
    entry = PsychiatricEvaluation.objects.get()
    assert entry.author_id == identities[2]["therapist"].pk
    assert entry.mse_mood_affect == ""
    data["patient_id"] = str(profile().uuid)
    assert (
        request_for(
            api.save_anamnesis,
            actor=identities[2]["therapist"],
            clinic=identities[0],
            method="post",
            data=data,
        ).status_code
        == 404
    )
    assert PsychiatricEvaluation.objects.count() == 1


def test_bed_ownership_nullable_and_unassessed_risk_not_zero():
    from psychiatry.models import InpatientBed, TwelveStepsAnamnesis

    assert hasattr(InpatientBed(), "clinic_id")
    assert InpatientBed().clinic_id is None
    assert TwelveStepsAnamnesis().relapse_risk_index is None


PUBLIC = {"login_view"}
ROUTES = [(str(route.pattern), route.callback) for route in urls.urlpatterns]
PRIVATE_ROUTES = [(p, view) for p, view in ROUTES if view.__name__ not in PUBLIC]
CLINICAL_ROUTES = PRIVATE_ROUTES
WRITE_VIEWS = [
    api.save_anamnesis,
    api.api_save_12steps_step,
    api.api_consolidate_12steps,
]


@pytest.mark.parametrize("path,view", PRIVATE_ROUTES)
def test_all_private_entries_reject_stale_inactive_actor(identities, path, view):
    clinic, _, actors = identities
    actor = actors["therapist"]
    User.objects.filter(pk=actor.pk).update(is_active=False)
    assert request_for(view, actor=actor, clinic=clinic).status_code == 403


@pytest.mark.parametrize("path,view", CLINICAL_ROUTES)
@pytest.mark.parametrize(
    "state", ["missing", "foreign", "inactive", "staff", "expired"]
)
def test_all_clinical_entries_recheck_clinic_and_membership(
    identities, path, view, state
):
    from datetime import timedelta

    clinic, other, actors = identities
    actor = actors["therapist"]
    if state == "missing":
        clinic = None
    elif state == "foreign":
        clinic = other
    elif state == "inactive":
        Clinic.infrastructure_objects.filter(pk=clinic.pk).update(is_active=False)
    elif state == "staff":
        actor = actors["administrative_staff"]
    else:
        ClinicMembership.infrastructure_objects.filter(user=actor).update(
            valid_from=date.today() - timedelta(days=2),
            valid_until=date.today() - timedelta(days=1),
        )
    assert request_for(view, actor=actor, clinic=clinic).status_code == 403


@pytest.mark.parametrize("view", WRITE_VIEWS)
def test_all_session_mutations_require_real_csrf(identities, view):
    actor = identities[2]["therapist"]
    request = RequestFactory().post("/", data="{}", content_type="application/json")
    request.user, request.clinic = actor, identities[0]
    assert not getattr(view, "csrf_exempt", False)
    assert view(request).status_code == 403


def test_another_therapist_cannot_read_authored_draft(identities, linked_profile):
    from people.models import CareRelationship
    from psychiatry.models import TwelveStepsAnamnesis

    grant_follow_up(identities)
    actor = User.objects.create_user(email="second-therapist@example.test")
    ClinicMembership.infrastructure_objects.create(
        clinic=identities[0], user=actor, role="therapist", valid_from=date.today()
    )
    CareRelationship.infrastructure_objects.create(
        clinic=identities[0],
        therapist=actor,
        patient=identities[2]["patient"],
        valid_from=date.today(),
    )
    entry = TwelveStepsAnamnesis.objects.create(
        patient=linked_profile, author=identities[2]["therapist"]
    )
    assert (
        request_for(
            api.api_get_12steps_draft,
            actor=actor,
            clinic=identities[0],
            data={"session_id": str(entry.uuid)},
        ).status_code
        == 404
    )


@pytest.mark.parametrize("number", [0, 13, True, "1"])
def test_step_number_has_strict_type_and_range(identities, linked_profile, number):
    grant_follow_up(identities)
    data = {
        "patient_id": str(linked_profile.uuid),
        "step_number": number,
        "step_data": {"answer": "Sintético"},
    }
    assert (
        request_for(
            api.api_save_12steps_step,
            actor=identities[2]["therapist"],
            clinic=identities[0],
            method="post",
            data=data,
        ).status_code
        == 400
    )


def request_for(view, *, actor=None, clinic=None, method="get", data=None):
    factory = RequestFactory()
    request = getattr(factory, method)(
        "/psiquiatria/",
        data=json.dumps(data or {}) if method == "post" else data,
        content_type="application/json",
    )
    request.user = actor if actor is not None else AnonymousUser()
    request.clinic = clinic
    # Other tests explicitly exercise real CSRF; this isolates authorization.
    request._dont_enforce_csrf_checks = True
    return view(request)


@pytest.fixture
def identities():
    clinic = Clinic.infrastructure_objects.create(name="Sintética A", slug="psy-a")
    other = Clinic.infrastructure_objects.create(name="Sintética B", slug="psy-b")
    actors = {}
    for role in ("therapist", "patient", "clinic_admin", "administrative_staff"):
        user = User.objects.create_user(email=f"psy-{role}@example.test")
        ClinicMembership.infrastructure_objects.create(
            clinic=clinic,
            user=user,
            role=role,
            valid_from=date.today(),
        )
        actors[role] = user
    return clinic, other, actors


@pytest.mark.parametrize("path,view", ROUTES, ids=[p or "dashboard" for p, _ in ROUTES])
def test_every_private_entry_authenticates_without_middleware(path, view):
    if view.__name__ in PUBLIC:
        return
    response = request_for(view)
    assert response.status_code in (401, 403), path


@pytest.mark.parametrize(
    "state", ["inactive", "missing", "foreign", "inactive_clinic", "admin", "staff"]
)
def test_clinical_dashboard_authorizes_local_state(identities, state):
    from psychiatry.api import clinic_dashboard_kpis

    clinic, other, actors = identities
    actor = actors["therapist"]
    if state == "inactive":
        User.objects.filter(pk=actor.pk).update(is_active=False)
    elif state == "missing":
        clinic = None
    elif state == "foreign":
        clinic = other
    elif state == "inactive_clinic":
        Clinic.infrastructure_objects.filter(pk=clinic.pk).update(is_active=False)
    elif state == "admin":
        actor = actors["clinic_admin"]
    else:
        actor = actors["administrative_staff"]
    assert (
        request_for(clinic_dashboard_kpis, actor=actor, clinic=clinic).status_code
        == 403
    )
