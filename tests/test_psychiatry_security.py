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


@pytest.mark.parametrize(
    "view", [api.b2c_mood, api.b2c_cbt_diary, api.b2c_subscription_status]
)
def test_b2c_rejects_external_identity(identities, view):
    actor = identities[2]["patient"]
    response = request_for(view, actor=actor, method="post", data={"user_id": "victim"})
    assert response.status_code == 400


@pytest.mark.parametrize("view", [api.b2c_mood, api.b2c_cbt_diary])
def test_b2c_history_has_no_demo_or_legacy_identity_fallback(identities, view):
    from psychiatry.models import B2CCBTDiary, B2CMindLog

    actor = identities[2]["patient"]
    B2CMindLog.objects.create(user_identifier=str(actor.pk))
    B2CCBTDiary.objects.create(user_identifier=str(actor.pk))
    response = request_for(view, actor=actor)
    data = json.loads(response.content)
    assert data.get("history", data.get("entries")) == []


def test_b2c_writes_owner_and_reads_only_owner(identities):
    from psychiatry.models import B2CMindLog

    actor = identities[2]["patient"]
    response = request_for(
        api.b2c_mood,
        actor=actor,
        method="post",
        data={
            "mood": "CALM",
            "anxiety_score": 0,
            "energy_score": 1,
            "sleep_hours": 0,
        },
    )
    assert response.status_code == 200
    log = B2CMindLog.objects.get()
    assert log.user_id == actor.pk
    assert log.anxiety_score == 0
    assert (
        len(json.loads(request_for(api.b2c_mood, actor=actor).content)["history"]) == 1
    )
    assert (
        json.loads(request_for(api.b2c_mood, actor=identities[2]["therapist"]).content)[
            "history"
        ]
        == []
    )


@pytest.mark.parametrize(
    "body",
    ["null", "[]", "1", '"text"', "{", '{"mood":NaN}', '{"mood":"CALM","mood":"LOW"}'],
)
def test_json_root_and_syntax_are_validated(identities, body):
    request = RequestFactory().post("/", data=body, content_type="application/json")
    request.user = identities[2]["patient"]
    request._dont_enforce_csrf_checks = True
    assert api.b2c_mood(request).status_code == 400


@pytest.mark.parametrize(
    "data",
    [
        {"anxiety_score": True},
        {"anxiety_score": "3"},
        {"anxiety_score": 11},
        {"energy_score": 0},
        {"sleep_hours": 25},
        {"mood": "UNKNOWN"},
        {"tags": "x"},
        {"gratitude": "x" * 4001},
    ],
)
def test_mood_field_validation(identities, data):
    assert (
        request_for(
            api.b2c_mood, actor=identities[2]["patient"], method="post", data=data
        ).status_code
        == 400
    )


def test_session_writes_enforce_csrf_locally(identities):
    request = RequestFactory().post("/", data="{}", content_type="application/json")
    request.user = identities[2]["patient"]
    assert api.b2c_mood(request).status_code == 403


@pytest.mark.parametrize(
    "params", [{"limit": "0"}, {"limit": "101"}, {"offset": "-1"}, {"offset": "1.2"}]
)
def test_pagination_invalid_values_rejected(identities, params):
    assert (
        request_for(
            api.b2c_mood, actor=identities[2]["patient"], data=params
        ).status_code
        == 400
    )


def test_payload_size_is_bounded(identities):
    assert (
        request_for(
            api.b2c_mood,
            actor=identities[2]["patient"],
            method="post",
            data={"gratitude": "a" * 65537},
        ).status_code
        == 413
    )


def test_subscription_cannot_be_self_activated(identities):
    assert (
        request_for(
            api.b2c_subscription_status,
            actor=identities[2]["patient"],
            method="post",
            data={"plan": "PLUS_ANNUAL"},
        ).status_code
        == 503
    )


@pytest.fixture
def own_profile(identities):
    clinic, _, actors = identities
    return profile(clinic=clinic, user=actors["patient"])


def test_connected_summary_uses_only_own_profile(identities, own_profile):
    response = request_for(
        api.patient_mobile_summary, actor=identities[2]["patient"], clinic=identities[0]
    )
    data = json.loads(response.content)["data"]
    assert data["patient"]["record_number"] == own_profile.record_number
    assert data["medications"] == []
    assert data["monitoring_active"] is False


def test_connected_missing_owner_fails_closed(identities):
    profile(tcle_signed=True)
    assert (
        request_for(
            api.patient_mobile_summary,
            actor=identities[2]["patient"],
            clinic=identities[0],
        ).status_code
        == 404
    )


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


def test_adherence_is_persisted_and_other_prescription_denied(identities, prescribed):
    from psychiatry.models import (
        MedicationAdherenceLog,
        PrescriptionItem,
        PsychopharmacologyPrescription,
    )

    payload = {
        "medication_id": prescribed.pk,
        "is_taken": False,
        "scheduled_time": "2026-01-01T10:00:00Z",
    }
    response = request_for(
        api.log_medication_adherence,
        actor=identities[2]["patient"],
        clinic=identities[0],
        method="post",
        data=payload,
    )
    assert response.status_code == 200
    log = MedicationAdherenceLog.objects.get()
    assert log.patient_id == prescribed.prescription.patient_id
    assert log.is_taken is False and log.taken_at is None
    foreign = profile()
    rx = PsychopharmacologyPrescription.objects.create(
        patient=foreign, expires_date=date(2099, 1, 1)
    )
    item = PrescriptionItem.objects.create(prescription=rx)
    payload["medication_id"] = item.pk
    assert (
        request_for(
            api.log_medication_adherence,
            actor=identities[2]["patient"],
            clinic=identities[0],
            method="post",
            data=payload,
        ).status_code
        == 404
    )
    assert MedicationAdherenceLog.objects.count() == 1


def test_sos_persists_but_never_claims_delivery(identities, own_profile):
    from psychiatry.models import PsychiatricCrisisAlert

    response = request_for(
        api.trigger_patient_sos,
        actor=identities[2]["patient"],
        clinic=identities[0],
        method="post",
        data={"latitude": -23.1, "longitude": -46.1},
    )
    assert response.status_code == 200
    alert = PsychiatricCrisisAlert.objects.get()
    assert alert.patient == own_profile
    data = json.loads(response.content)
    assert data["persisted"] is True
    assert data["notification_delivered"] is False
    assert data["monitoring_active"] is False
    assert data["protocol_active"] is False
    assert "ninguém foi notificado" in data["instructions"].lower()


@pytest.mark.parametrize(
    "data",
    [
        {"latitude": 91},
        {"longitude": -181},
        {"latitude": True},
        {"patient_cpf": "fake"},
        {"user_id": "fake"},
    ],
)
def test_sos_invalid_or_external_identity_rejected(identities, own_profile, data):
    assert (
        request_for(
            api.trigger_patient_sos,
            actor=identities[2]["patient"],
            clinic=identities[0],
            method="post",
            data=data,
        ).status_code
        == 400
    )


def test_craving_persists_without_inferred_recovery_or_notification(
    identities, own_profile
):
    from psychiatry.models import CravingTrackingLog

    data = {
        "intensity": 9,
        "target_urge": "Álcool",
        "halt_factors": ["HUNGRY"],
        "urge_surfed_successfully": False,
    }
    response = request_for(
        api.api_record_craving,
        actor=identities[2]["patient"],
        clinic=identities[0],
        method="post",
        data=data,
    )
    assert response.status_code == 200
    assert CravingTrackingLog.objects.get().patient == own_profile
    assert CravingTrackingLog.objects.get().urge_surfed_successfully is False
    assert json.loads(response.content)["urgent_intervention_dispatched"] is False


@pytest.mark.parametrize(
    "data", [{"intensity": 11}, {"intensity": "5"}, {"patient_cpf": "fake"}]
)
def test_craving_invalid_fields(identities, own_profile, data):
    assert (
        request_for(
            api.api_record_craving,
            actor=identities[2]["patient"],
            clinic=identities[0],
            method="post",
            data=data,
        ).status_code
        == 400
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


def test_service_actor_none_is_denied_not_system_bypass(identities):
    from django.core.exceptions import PermissionDenied

    from psychiatry.services import record_sos

    with pytest.raises(PermissionDenied):
        record_sos(actor=None, clinic=identities[0], data={})


PUBLIC = {"login_view", "b2c_breathing_exercises"}
ROUTES = [(str(route.pattern), route.callback) for route in urls.urlpatterns]
PRIVATE_ROUTES = [(p, view) for p, view in ROUTES if view.__name__ not in PUBLIC]
CLINICAL_ROUTES = [
    (p, view)
    for p, view in PRIVATE_ROUTES
    if not view.__name__.startswith("b2c_") and view.__name__ != "mobile_b2c_view"
]
WRITE_VIEWS = [
    api.save_anamnesis,
    api.log_medication_adherence,
    api.trigger_patient_sos,
    api.b2c_mood,
    api.b2c_cbt_diary,
    api.b2c_subscription_status,
    api.api_save_12steps_step,
    api.api_consolidate_12steps,
    api.api_record_craving,
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
    actor = (
        identities[2]["patient"]
        if view
        in [
            api.log_medication_adherence,
            api.trigger_patient_sos,
            api.api_record_craving,
            api.b2c_mood,
            api.b2c_cbt_diary,
            api.b2c_subscription_status,
        ]
        else identities[2]["therapist"]
    )
    request = RequestFactory().post("/", data="{}", content_type="application/json")
    request.user, request.clinic = actor, identities[0]
    assert not getattr(view, "csrf_exempt", False)
    assert view(request).status_code == 403


def test_valid_csrf_token_permits_persisted_b2c_write(identities):
    from django.middleware.csrf import get_token

    from psychiatry.models import B2CMindLog

    data = {"mood": "CALM", "anxiety_score": 0, "energy_score": 1, "sleep_hours": 0}
    request = RequestFactory().post(
        "/", data=json.dumps(data), content_type="application/json"
    )
    request.user = identities[2]["patient"]
    token = get_token(request)
    request.COOKIES["csrftoken"] = request.META["CSRF_COOKIE"]
    request.META["HTTP_X_CSRFTOKEN"] = token
    assert api.b2c_mood(request).status_code == 200
    assert B2CMindLog.objects.filter(user=request.user).count() == 1


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
