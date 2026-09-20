"""Revogação e visibilidade atuais, com identidades exclusivamente sintéticas."""

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from pytest_django.fixtures import SettingsWrapper

from accounts.models import User
from clinical_operations.models import (
    Encounter,
    Enrollment,
    OperationGrant,
    TherapySession,
)
from clinical_operations.policies import require_capability
from clinical_operations.selectors import list_resources
from clinical_operations.services import set_grant
from clinics.models import Clinic, ClinicMembership
from people.models import CareRelationship
from tests import test_clinical_operations as operation_fixtures
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

context = operation_fixtures.context
pytestmark = pytest.mark.django_db

type OperationContext = tuple[Clinic, User, User, User]


@pytest.mark.parametrize(
    "state", ["inactive", "suspended", "expired", "role_changed", "removed"]
)
def test_admin_can_revoke_existing_grant_after_target_loses_role(
    context: OperationContext, state: str
) -> None:
    clinic, admin, professional, _ = context
    memberships = ClinicMembership.infrastructure_objects.filter(
        clinic=clinic, user=professional
    )
    original = OperationGrant.objects.for_clinic(clinic.pk).get(
        user=professional, capability="record.read"
    )
    count = OperationGrant.objects.for_clinic(clinic.pk).count()
    if state == "inactive":
        User.objects.filter(pk=professional.pk).update(is_active=False)
    elif state == "suspended":
        memberships.update(is_active=False)
    elif state == "expired":
        memberships.update(
            valid_from=timezone.localdate() - timedelta(days=10),
            valid_until=timezone.localdate() - timedelta(days=1),
        )
    elif state == "role_changed":
        memberships.update(role="administrative_staff")
    else:
        memberships.delete()

    result = set_grant(
        clinic_id=clinic.pk,
        actor=admin,
        user_id=professional.pk,
        capability="record.read",
        enabled=False,
    )
    original.refresh_from_db()
    assert result.pk == original.pk
    assert original.enabled is False
    assert original.authorized_by_id == admin.pk
    assert OperationGrant.objects.for_clinic(clinic.pk).count() == count

    User.objects.filter(pk=professional.pk).update(is_active=True)
    if state == "removed":
        ClinicMembershipFactory.create(
            clinic=clinic, user=professional, role="therapist"
        )
    else:
        memberships.update(
            is_active=True,
            role="therapist",
            valid_from=timezone.localdate(),
            valid_until=None,
        )
    with pytest.raises(PermissionDenied):
        require_capability(
            clinic_id=clinic.pk, actor=professional, capability="record.read"
        )


def test_revoking_missing_grant_does_not_create_a_permission_row(
    context: OperationContext,
) -> None:
    clinic, admin, _, _ = context
    target = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=target, role="therapist")
    before = OperationGrant.objects.for_clinic(clinic.pk).count()
    with pytest.raises(ValidationError):
        set_grant(
            clinic_id=clinic.pk,
            actor=admin,
            user_id=target.pk,
            capability="record.read",
            enabled=False,
        )
    assert OperationGrant.objects.for_clinic(clinic.pk).count() == before


@pytest.mark.parametrize("resource", ["encounters", "enrollments"])
@pytest.mark.parametrize(
    "state", ["closed", "expired", "patient_inactive", "membership_suspended"]
)
def test_identified_lists_drop_patients_without_current_access(
    context: OperationContext,
    resource: str,
    state: str,
    settings: SettingsWrapper,
) -> None:
    clinic, _, professional, patient = context
    settings.CLINICAL_OPERATIONS_ENABLED = True
    operation_fixtures.link_and_consent(context)
    relationship = CareRelationship.infrastructure_objects.get(
        clinic=clinic, therapist=professional, patient=patient
    )
    start = timezone.now() + timedelta(days=1)
    record: Encounter | Enrollment
    if resource == "encounters":
        record = Encounter.objects.for_clinic(clinic.pk).create(
            clinic=clinic, professional=professional, patient=patient, starts_at=start
        )
    else:
        session = TherapySession.objects.for_clinic(clinic.pk).create(
            clinic=clinic,
            professional=professional,
            kind="grupo",
            modality="psicoterapia",
            capacity=2,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
        )
        record = Enrollment.objects.for_clinic(clinic.pk).create(
            clinic=clinic, session=session, patient=patient
        )
    client = Client(enforce_csrf_checks=True)
    client.force_login(professional)
    url = f"/api/v1/clinical-operations/{resource}/"
    headers = {"X-Clinic-ID": str(clinic.pk)}
    before = client.get(url, headers=headers)
    assert before.status_code == 200
    assert [row["patient_id"] for row in before.json()["results"]] == [str(patient.pk)]

    if state == "closed":
        relationship.is_active = False
        relationship.save(update_fields=("is_active", "updated_at"))
    elif state == "expired":
        relationship.valid_from = timezone.localdate() - timedelta(days=10)
        relationship.valid_until = timezone.localdate() - timedelta(days=1)
        relationship.save(update_fields=("valid_from", "valid_until", "updated_at"))
    elif state == "patient_inactive":
        User.objects.filter(pk=patient.pk).update(is_active=False)
    else:
        ClinicMembership.infrastructure_objects.filter(
            clinic=clinic, user=patient
        ).update(is_active=False)

    with CaptureQueriesContext(connection) as queries:
        rows = list_resources(
            clinic_id=clinic.pk, actor=professional, resource=resource
        )
    assert rows == []
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries
    )
    after = client.get(url, headers=headers)
    assert after.status_code == 200
    assert after.json()["results"] == []
    assert str(patient.pk) not in after.content.decode()
    assert "no-store" in after.headers["Cache-Control"]
    record.refresh_from_db()
    assert record.patient_id == patient.pk


def test_revoking_a_grant_does_not_change_another_clinics_grant(
    context: OperationContext,
) -> None:
    clinic, admin, professional, _ = context
    other = ClinicFactory.create()
    for user, role in ((admin, "clinic_admin"), (professional, "therapist")):
        ClinicMembershipFactory.create(clinic=other, user=user, role=role)
    foreign = set_grant(
        clinic_id=other.pk,
        actor=admin,
        user_id=professional.pk,
        capability="record.read",
        enabled=True,
    )
    result = set_grant(
        clinic_id=clinic.pk,
        actor=admin,
        user_id=professional.pk,
        capability="record.read",
        enabled=False,
    )
    foreign.refresh_from_db()
    assert result.clinic_id == clinic.pk and result.enabled is False
    assert foreign.enabled is True


@pytest.mark.parametrize("state", ["non_admin", "inactive_admin", "inactive_clinic"])
def test_revocation_still_requires_current_clinic_administrator(
    context: OperationContext, state: str
) -> None:
    clinic, admin, professional, _ = context
    actor = professional if state == "non_admin" else admin
    if state == "inactive_admin":
        User.objects.filter(pk=admin.pk).update(is_active=False)
    elif state == "inactive_clinic":
        Clinic.infrastructure_objects.filter(pk=clinic.pk).update(is_active=False)
    with pytest.raises(PermissionDenied):
        set_grant(
            clinic_id=clinic.pk,
            actor=actor,
            user_id=professional.pk,
            capability="record.read",
            enabled=False,
        )
    assert (
        OperationGrant.objects.for_clinic(clinic.pk)
        .get(user=professional, capability="record.read")
        .enabled
        is True
    )


@pytest.mark.parametrize("resource", ["encounters", "enrollments"])
def test_identified_list_paginates_only_currently_visible_records(
    context: OperationContext, resource: str
) -> None:
    clinic, _, professional, patient = context
    operation_fixtures.link_and_consent(context)
    unlinked = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=unlinked, role="patient")
    records: list[Encounter | Enrollment] = []
    start = timezone.now() + timedelta(days=1)
    for target in (unlinked, patient, patient):
        if resource == "encounters":
            record = Encounter.objects.for_clinic(clinic.pk).create(
                clinic=clinic,
                professional=professional,
                patient=target,
                starts_at=start,
            )
        else:
            session = TherapySession.objects.for_clinic(clinic.pk).create(
                clinic=clinic,
                professional=professional,
                kind="grupo",
                modality="psicoterapia",
                capacity=2,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
            )
            record = Enrollment.objects.for_clinic(clinic.pk).create(
                clinic=clinic, session=session, patient=target
            )
        records.append(record)
        start += timedelta(days=1)
    rows = list_resources(
        clinic_id=clinic.pk, actor=professional, resource=resource, offset=1
    )
    assert [row["id"] for row in rows] == [records[-1].pk]
    assert all(row["patient_id"] == patient.pk for row in rows)
