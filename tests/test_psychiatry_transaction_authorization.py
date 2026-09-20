"""Regressões de autorização transacional com dados exclusivamente sintéticos."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, transaction
from django.db.models import QuerySet
from django.http import Http404

from clinics.models import ClinicMembership
from clinics.services import lock_clinic_for_update
from consents.services import revoke_consent
from people.models import CareRelationship
from psychiatry import api, services
from psychiatry.models import TwelveStepsAnamnesis
from tests import test_psychiatry_security as security_fixtures
from tests.test_psychiatry_security import (
    grant_follow_up,
    request_for,
)

identities = security_fixtures.identities
linked_profile = security_fixtures.linked_profile
own_profile = security_fixtures.own_profile
prescribed = security_fixtures.prescribed

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("operation", ["consolidate", "update_step"])
@pytest.mark.parametrize(
    "revocation", ["consent", "actor", "patient", "membership", "care", "clinic"]
)
def test_draft_rechecks_authorization_after_resource_lock(
    identities, linked_profile, monkeypatch, operation, revocation
):
    clinic, _, actors = identities
    document = grant_follow_up(identities)
    draft = TwelveStepsAnamnesis.objects.create(
        patient=linked_profile,
        author=actors["therapist"],
        status="DRAFT",
        draft_steps={"step_1": {"answer": "Resposta sintética"}},
    )
    original = QuerySet.first
    changed = False

    def first_after_wait(query):
        nonlocal changed
        entry = original(query)
        if query.model is TwelveStepsAnamnesis and query.query.select_for_update:
            assert not changed
            changed = True
            # Costura determinística: simula mudança durante a espera da query.
            # O teste PostgreSQL separado comprova commits de conexões concorrentes.
            if revocation == "consent":
                revoke_consent(
                    clinic_id=clinic.pk,
                    actor=actors["patient"],
                    subject_id=actors["patient"].pk,
                    document_id=document.pk,
                    request_id=uuid4(),
                    reason="Revogação sintética durante espera",
                )
            elif revocation in {"actor", "patient"}:
                user = actors["therapist" if revocation == "actor" else "patient"]
                type(user).objects.filter(pk=user.pk).update(is_active=False)
            elif revocation == "membership":
                ClinicMembership.infrastructure_objects.filter(
                    clinic=clinic, user=actors["therapist"]
                ).update(is_active=False)
            elif revocation == "care":
                CareRelationship.infrastructure_objects.filter(clinic=clinic).update(
                    is_active=False
                )
            else:
                type(clinic).infrastructure_objects.filter(pk=clinic.pk).update(
                    is_active=False
                )
        return entry

    monkeypatch.setattr(QuerySet, "first", first_after_wait)
    with pytest.raises((PermissionDenied, Http404)):
        if operation == "consolidate":
            services.consolidate_steps(
                actor=actors["therapist"], clinic=clinic, session_id=draft.uuid
            )
        else:
            services.save_step(
                actor=actors["therapist"],
                clinic=clinic,
                data={
                    "patient_id": str(linked_profile.uuid),
                    "session_id": str(draft.uuid),
                    "step_number": 2,
                    "step_data": {"answer": "Não deve persistir"},
                },
            )
    assert changed
    draft.refresh_from_db()
    assert draft.status == "DRAFT"
    assert draft.step1_powerlessness == ""
    assert "step_2" not in draft.draft_steps


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Exige locks PostgreSQL.")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "operation",
    [
        "new_step",
        "update_step",
        "consolidate",
        "anamnesis",
        "sos",
        "craving",
        "adherence",
    ],
)
def test_write_waits_for_clinic_and_rechecks_committed_revocation(
    identities, linked_profile, prescribed, operation
):
    clinic, _, actors = identities
    document = grant_follow_up(identities)
    patient_mode = operation in {"sos", "craving", "adherence"}
    actor = actors["patient" if patient_mode else "therapist"]
    draft = TwelveStepsAnamnesis.objects.create(
        patient=linked_profile,
        author=actors["therapist"],
        status="DRAFT",
        draft_steps={"step_1": {"answer": "Resposta sintética"}},
    )
    view, data = {
        "new_step": (
            api.api_save_12steps_step,
            {
                "patient_id": str(linked_profile.uuid),
                "step_number": 1,
                "step_data": {"answer": "Resposta sintética"},
            },
        ),
        "update_step": (
            api.api_save_12steps_step,
            {
                "patient_id": str(linked_profile.uuid),
                "step_number": 2,
                "session_id": str(draft.uuid),
                "step_data": {"answer": "Não deve persistir"},
            },
        ),
        "consolidate": (api.api_consolidate_12steps, {"session_id": str(draft.uuid)}),
        "adherence": (
            api.log_medication_adherence,
            {
                "medication_id": prescribed.pk,
                "is_taken": False,
                "scheduled_time": "2026-01-01T10:00:00Z",
            },
        ),
        "anamnesis": (
            api.save_anamnesis,
            {
                "patient_id": str(linked_profile.uuid),
                "chief_complaint": "Sintético",
                "hda": "Sintético",
                "anxiety_scale": 1,
                "risk_level": "LOW",
                "diagnostic_impression": "Relato sintético",
                "therapeutic_plan": "Revisão humana",
            },
        ),
        "sos": (api.trigger_patient_sos, {}),
        "craving": (
            api.api_record_craving,
            {
                "intensity": 1,
                "target_urge": "Relato sintético",
                "urge_surfed_successfully": False,
            },
        ),
    }[operation]
    pids = Queue()
    done = Event()

    def write():
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '15000ms'")
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            return request_for(
                view, actor=actor, clinic=clinic, method="post", data=data
            )
        finally:
            done.set()
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with transaction.atomic():
            lock_clinic_for_update(clinic_id=clinic.pk)
            future = pool.submit(write)
            pid = pids.get(timeout=10)
            blocked = False
            deadline = monotonic() + 10
            while monotonic() < deadline and not done.is_set():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))", [pid]
                    )
                    blocked = cursor.fetchone()[0]
                if blocked:
                    break
                sleep(0.01)
            if patient_mode:
                type(actor).objects.filter(pk=actor.pk).update(is_active=False)
            else:
                revoke_consent(
                    clinic_id=clinic.pk,
                    actor=actors["patient"],
                    subject_id=actors["patient"].pk,
                    document_id=document.pk,
                    reason="Revogação confirmada antes da escrita",
                    request_id=uuid4(),
                )
        response = future.result(timeout=15)
    assert blocked, "A mutação não se serializou com a revogação da clínica."
    assert response.status_code in {403, 404}
    draft.refresh_from_db()
    assert draft.status == "DRAFT"
    assert "step_2" not in draft.draft_steps
    from psychiatry.models import (
        CravingTrackingLog,
        MedicationAdherenceLog,
        PsychiatricCrisisAlert,
        PsychiatricEvaluation,
    )

    for model in (
        CravingTrackingLog,
        MedicationAdherenceLog,
        PsychiatricCrisisAlert,
        PsychiatricEvaluation,
    ):
        assert not model.objects.exists()
    assert TwelveStepsAnamnesis.objects.count() == 1
