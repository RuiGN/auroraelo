"""Operações com identidades e dados exclusivamente sintéticos."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from importlib.util import find_spec
from typing import TYPE_CHECKING, Never, NotRequired, TypedDict, Unpack

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.utils import timezone

from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from django.test import Client
    from pytest_django.fixtures import SettingsWrapper

    from accounts.models import User
    from clinical_operations.models import ClinicalRecord, StockMovement
    from clinics.models import Clinic
    from consents.models import ConsentDocument

type ClinicalContext = tuple[Clinic, User, User, User]


class ServiceArguments(TypedDict):
    clinic_id: UUID
    actor: User


class StockArguments(ServiceArguments):
    lot_id: UUID


class MembershipChanges(TypedDict, total=False):
    is_active: bool
    valid_until: date
    valid_from: date
    role: str


class AuditEventArguments(TypedDict):
    clinic_id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    request_id: UUID
    network_origin: str | None
    justification: NotRequired[str | None]


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def enable_clinical_operations(settings: SettingsWrapper) -> None:
    settings.CLINICAL_OPERATIONS_ENABLED = True


def test_explicit_grant_required_for_pharmacy() -> None:
    assert find_spec("clinical_operations") is not None, "Falta o domínio operacional"
    from clinical_operations.services import create_product, set_grant

    clinic = ClinicFactory.create()
    admin = UserFactory.create()
    worker = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=admin, role="clinic_admin")
    ClinicMembershipFactory.create(
        clinic=clinic, user=worker, role="administrative_staff"
    )
    with pytest.raises(PermissionDenied):
        create_product(
            clinic_id=clinic.pk, actor=admin, name="Produto sintético", sku="S1"
        )
    set_grant(
        clinic_id=clinic.pk,
        actor=admin,
        user_id=worker.pk,
        capability="pharmacy.write",
        enabled=True,
    )
    product = create_product(
        clinic_id=clinic.pk, actor=worker, name="Produto sintético", sku="S1"
    )
    assert product.clinic_id == clinic.pk
    assert product.sku == "S1"


@pytest.fixture
def context() -> ClinicalContext:
    from clinical_operations.services import set_grant

    clinic = ClinicFactory.create()
    admin, professional, patient = (UserFactory.create() for _ in range(3))
    for user, role in (
        (admin, "clinic_admin"),
        (professional, "therapist"),
        (patient, "patient"),
    ):
        ClinicMembershipFactory.create(clinic=clinic, user=user, role=role)
    for capability in (
        "pharmacy.read",
        "pharmacy.write",
        "encounter.manage",
        "record.read",
        "record.write",
        "session.manage",
    ):
        set_grant(
            clinic_id=clinic.pk,
            actor=admin,
            user_id=professional.pk,
            capability=capability,
            enabled=True,
        )
    return clinic, admin, professional, patient


def test_inventory_atomic_idempotent_append_only(context: ClinicalContext) -> None:
    from django.core.exceptions import ValidationError

    from clinical_operations import services

    assert hasattr(services, "move_stock"), "Falta movimento atômico"
    from clinical_operations.models import StockMovement

    clinic, _, actor, patient = context
    product = services.create_product(
        clinic_id=clinic.pk, actor=actor, name="Sintético", sku="A"
    )
    lot = services.create_lot(
        clinic_id=clinic.pk,
        actor=actor,
        product_id=product.pk,
        code="L1",
        expires_on=timezone.localdate() + timedelta(days=1),
    )
    common: StockArguments = dict(clinic_id=clinic.pk, actor=actor, lot_id=lot.pk)
    services.move_stock(**common, quantity=5, direction="in", key="receipt")
    out = services.move_stock(
        **common, quantity=3, direction="out", key="dispense", patient_id=patient.pk
    )
    again = services.move_stock(
        **common, quantity=3, direction="out", key="dispense", patient_id=patient.pk
    )
    assert again.pk == out.pk
    lot.refresh_from_db()
    assert lot.balance == 2
    with pytest.raises(services.Conflict, match="idempotency_conflict"):
        services.move_stock(
            **common, quantity=2, direction="out", key="dispense", patient_id=patient.pk
        )
    with pytest.raises(services.Conflict, match="insufficient_stock"):
        services.move_stock(
            **common, quantity=3, direction="out", key="too-many", patient_id=patient.pk
        )
    assert StockMovement.objects.for_clinic(clinic.pk).count() == 2
    with pytest.raises(ValidationError):
        out.quantity = 1
        out.save()
    with pytest.raises(ValidationError):
        StockMovement.objects.for_clinic(clinic.pk).update(quantity=1)
    with pytest.raises(ValidationError):
        StockMovement.objects.for_clinic(clinic.pk).delete()
    with pytest.raises(ValidationError):
        out.delete()


def test_expired_lot_and_cross_clinic_fks(context: ClinicalContext) -> None:
    from clinical_operations import services

    assert hasattr(services, "create_lot"), "Falta lote"
    from django.core.exceptions import ValidationError

    clinic, _, actor, patient = context
    other = ClinicFactory.create()
    ClinicMembershipFactory.create(clinic=other, user=actor, role="clinic_admin")
    services.set_grant(
        clinic_id=other.pk,
        actor=actor,
        user_id=actor.pk,
        capability="pharmacy.write",
        enabled=True,
    )
    product = services.create_product(
        clinic_id=clinic.pk, actor=actor, name="Sintético", sku="B"
    )
    with pytest.raises(ValidationError):
        services.create_lot(
            clinic_id=other.pk,
            actor=actor,
            product_id=product.pk,
            code="cross",
            expires_on=timezone.localdate(),
        )
    lot = services.create_lot(
        clinic_id=clinic.pk,
        actor=actor,
        product_id=product.pk,
        code="expired",
        expires_on=timezone.localdate() - timedelta(days=1),
    )
    services.move_stock(
        clinic_id=clinic.pk,
        actor=actor,
        lot_id=lot.pk,
        quantity=2,
        direction="in",
        key="receipt",
    )
    with pytest.raises(services.Conflict, match="expired_lot"):
        services.move_stock(
            clinic_id=clinic.pk,
            actor=actor,
            lot_id=lot.pk,
            quantity=1,
            direction="out",
            key="expired",
            patient_id=patient.pk,
        )


def link_and_consent(context: ClinicalContext) -> ConsentDocument:
    from uuid import uuid4

    from consents.services import publish_consent_document, record_consent_manifestation
    from people.models import CareRelationship

    clinic, admin, professional, patient = context
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=professional,
        patient=patient,
        authorized_by=admin,
        valid_from=timezone.localdate(),
    )
    document = publish_consent_document(
        clinic_id=clinic.pk,
        actor=admin,
        document_type="consent",
        title="Sintético",
        version="1",
        content="Termo sintético",
        purpose="clinical_follow_up",
        effective_from=timezone.now() - timedelta(days=1),
        audience="patient",
        is_mandatory=False,
        refusal_consequence="Sem acompanhamento",
        alternative_instructions="Contato presencial",
        clinic_contact_instructions="Recepção",
    )
    record_consent_manifestation(
        clinic_id=clinic.pk,
        actor=patient,
        subject_id=patient.pk,
        document_id=document.pk,
        decision="accepted",
        request_id=uuid4(),
    )
    return document


def test_encounter_transitions_and_record_access_segregation(
    context: ClinicalContext,
) -> None:
    from clinical_operations import services

    assert hasattr(services, "schedule_encounter"), "Falta atendimento"
    from clinical_operations.selectors import read_records

    clinic, admin, actor, patient = context
    args: ServiceArguments = dict(clinic_id=clinic.pk, actor=actor)
    with pytest.raises(PermissionDenied):
        services.schedule_encounter(
            **args, patient_id=patient.pk, starts_at=timezone.now() + timedelta(days=1)
        )
    link_and_consent(context)
    encounter = services.schedule_encounter(
        **args, patient_id=patient.pk, starts_at=timezone.now() + timedelta(days=1)
    )
    assert encounter.status == "agendado"
    with pytest.raises(services.Conflict):
        services.transition_encounter(
            **args, encounter_id=encounter.pk, status="concluido"
        )
    services.transition_encounter(
        **args, encounter_id=encounter.pk, status="em_atendimento"
    )
    record = services.append_record(
        **args, encounter_id=encounter.pk, content="Registro sintético confidencial"
    )
    assert read_records(**args, encounter_id=encounter.pk)[0].pk == record.pk
    with pytest.raises(PermissionDenied):
        read_records(clinic_id=clinic.pk, actor=admin, encounter_id=encounter.pk)
    services.set_grant(
        clinic_id=clinic.pk,
        actor=admin,
        user_id=actor.pk,
        capability="record.read",
        enabled=False,
    )
    with pytest.raises(PermissionDenied):
        read_records(**args, encounter_id=encounter.pk)
    services.append_record(
        **args, encounter_id=encounter.pk, content="Segunda anotação sintética"
    )
    services.transition_encounter(**args, encounter_id=encounter.pk, status="concluido")
    with pytest.raises(services.Conflict):
        services.transition_encounter(
            **args, encounter_id=encounter.pk, status="em_atendimento"
        )
    with pytest.raises(services.Conflict):
        services.append_record(**args, encounter_id=encounter.pk, content="Tarde")


def test_consent_revocation_blocks_record_read_write(context: ClinicalContext) -> None:
    from clinical_operations import services

    assert hasattr(services, "append_record"), "Falta registro clínico segregado"
    from uuid import uuid4

    from clinical_operations.selectors import read_records
    from consents.services import revoke_consent

    clinic, _, actor, patient = context
    document = link_and_consent(context)
    args: ServiceArguments = dict(clinic_id=clinic.pk, actor=actor)
    encounter = services.schedule_encounter(
        **args, patient_id=patient.pk, starts_at=timezone.now() + timedelta(days=1)
    )
    services.transition_encounter(
        **args, encounter_id=encounter.pk, status="em_atendimento"
    )
    services.append_record(
        **args, encounter_id=encounter.pk, content="Confidencial sintético"
    )
    revoke_consent(
        clinic_id=clinic.pk,
        actor=patient,
        subject_id=patient.pk,
        document_id=document.pk,
        reason="Revogação sintética",
        request_id=uuid4(),
    )
    with pytest.raises(PermissionDenied):
        read_records(**args, encounter_id=encounter.pk)
    with pytest.raises(PermissionDenied):
        services.append_record(
            **args, encounter_id=encounter.pk, content="Não autorizado"
        )


@pytest.mark.parametrize(
    "modality", ["psicoterapia", "exercicio", "yoga", "arteterapia"]
)
def test_sessions_capacity_and_attendance(
    context: ClinicalContext, modality: str
) -> None:
    from clinical_operations import services

    assert hasattr(services, "schedule_session"), "Falta sessão"
    from django.core.exceptions import ValidationError

    from people.models import CareRelationship

    clinic, admin, actor, patient = context
    link_and_consent(context)
    args: ServiceArguments = dict(clinic_id=clinic.pk, actor=actor)
    second = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=second, role="patient")
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=actor,
        patient=second,
        authorized_by=admin,
        valid_from=timezone.localdate(),
    )
    start = timezone.now() + timedelta(days=1)
    with pytest.raises(ValidationError):
        services.schedule_session(
            **args,
            kind="individual",
            modality=modality,
            capacity=2,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
        )
    session = services.schedule_session(
        **args,
        kind="grupo",
        modality=modality,
        capacity=1,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
    )
    enrollment = services.enroll_patient(
        **args, session_id=session.pk, patient_id=patient.pk
    )
    assert (
        services.enroll_patient(**args, session_id=session.pk, patient_id=patient.pk).pk
        == enrollment.pk
    )
    with pytest.raises(services.Conflict, match="capacity_reached"):
        services.enroll_patient(**args, session_id=session.pk, patient_id=second.pk)
    services.set_attendance(**args, enrollment_id=enrollment.pk, status="presente")
    enrollment.refresh_from_db()
    assert enrollment.status == "presente"
    with pytest.raises(ValidationError):
        services.set_attendance(
            **args, enrollment_id=enrollment.pk, status="prescrever"
        )
    with pytest.raises(services.Conflict, match="schedule_overlap"):
        services.schedule_session(
            **args,
            kind="individual",
            modality=modality,
            capacity=1,
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
        )


API = "/api/v1/clinical-operations/"


def login(client: Client, clinic: Clinic, actor: User) -> None:
    client.force_login(actor)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()


def test_http_json_csrf_and_read_only_get(
    context: ClinicalContext, client: Client
) -> None:
    from django.middleware.csrf import _get_new_csrf_string
    from django.test import Client

    from audit.models import AuditEvent

    clinic, _, actor, _ = context
    assert client.get(API + "products/").status_code == 401
    login(client, clinic, actor)
    before = AuditEvent.objects.for_clinic(clinic.pk).count()
    assert client.get(API + "products/").status_code == 200
    assert AuditEvent.objects.for_clinic(clinic.pk).count() == before
    payload = {"name": "Sintético", "sku": "HTTP"}
    strict = Client(enforce_csrf_checks=True)
    login(strict, clinic, actor)
    assert (
        strict.post(
            API + "products/", payload, content_type="application/json"
        ).status_code
        == 403
    )
    token = _get_new_csrf_string()
    strict.cookies["csrftoken"] = token
    result = strict.post(
        API + "products/",
        payload,
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert result.status_code == 201, result.content
    assert result.json()["id"]
    assert len(client.get(API + "products/").json()["results"]) == 1
    for bad in [
        {"name": "x", "sku": "x", "clinic_id": str(clinic.pk)},
        [],
        {"name": "x"},
        {"name": "x" * 161, "sku": "x"},
    ]:
        assert (
            client.post(
                API + "products/", bad, content_type="application/json"
            ).status_code
            == 400
        )
    assert (
        client.post(API + "products/", "{", content_type="application/json").status_code
        == 400
    )
    assert (
        client.post(
            API + "products/", "x" * 17000, content_type="application/json"
        ).status_code
        == 413
    )
    assert client.post(API + "products/", payload).status_code == 415
    assert client.get(API + "attendance/").status_code == 405


@pytest.mark.parametrize(
    "role", ["patient", "administrative_staff", "clinic_admin", "therapist"]
)
def test_http_roles_denied_without_grant(role: str, client: Client) -> None:
    clinic = ClinicFactory.create()
    actor = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=actor, role=role)
    login(client, clinic, actor)
    assert client.get(API + "products/").status_code == 403
    assert (
        client.post(
            API + "encounters/",
            {"patient_id": str(actor.pk), "starts_at": timezone.now().isoformat()},
            content_type="application/json",
        ).status_code
        == 403
    )


def test_http_inactive_clinic_and_tenant_crossing(
    context: ClinicalContext, client: Client
) -> None:
    clinic, _, actor, _ = context
    login(client, clinic, actor)
    other = ClinicFactory.create()
    assert (
        client.get(API + "products/", HTTP_X_CLINIC_ID=str(other.pk)).status_code == 403
    )
    clinic.is_active = False
    clinic.save(update_fields=("is_active",))
    assert client.get(API + "products/").status_code == 403


def test_own_domain_obeys_public_architecture() -> None:
    from pathlib import Path

    from tests.architecture_helpers import architecture_violations, domain_dependencies
    from tests.test_domain_architecture import ALLOWED_DEPENDENCIES, DOMAIN_MODULES

    modules = (*DOMAIN_MODULES, "clinical_operations")
    allowed = {
        **ALLOWED_DEPENDENCIES,
        "clinical_operations": {"core", "clinics", "people", "consents", "audit"},
    }
    assert (
        architecture_violations(
            domain_dependencies(Path(__file__).parents[1], modules), allowed
        )
        == []
    )


@pytest.mark.parametrize("kind", ["movement", "record"])
def test_immutable_rows_resist_raw_sql(context: ClinicalContext, kind: str) -> None:
    from django.db import DatabaseError, connection, transaction
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(connection, ignore_no_migrations=True)
    if ("clinical_operations", "0002_append_only") not in loader.graph.nodes:
        pytest.skip(
            "Triggers append-only são instalados por migration real; "
            "ausentes sob pytest --nomigrations."
        )

    from clinical_operations import services

    clinic, _, actor, patient = context
    row: StockMovement | ClinicalRecord
    if kind == "movement":
        product = services.create_product(
            clinic_id=clinic.pk, actor=actor, name="Sintético", sku="SQL"
        )
        lot = services.create_lot(
            clinic_id=clinic.pk,
            actor=actor,
            product_id=product.pk,
            code="SQL",
            expires_on=timezone.localdate(),
        )
        row = services.move_stock(
            clinic_id=clinic.pk,
            actor=actor,
            lot_id=lot.pk,
            quantity=2,
            direction="in",
            key="SQL",
        )
    else:
        link_and_consent(context)
        encounter = services.schedule_encounter(
            clinic_id=clinic.pk,
            actor=actor,
            patient_id=patient.pk,
            starts_at=timezone.now() + timedelta(days=1),
        )
        services.transition_encounter(
            clinic_id=clinic.pk,
            actor=actor,
            encounter_id=encounter.pk,
            status="em_atendimento",
        )
        row = services.append_record(
            clinic_id=clinic.pk,
            actor=actor,
            encounter_id=encounter.pk,
            content="Sintético privado",
        )
    table = connection.ops.quote_name(row._meta.db_table)
    for sql in (f"UPDATE {table} SET clinic_id = clinic_id", f"DELETE FROM {table}"):
        with (
            pytest.raises(DatabaseError),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(sql)


def test_cross_tenant_model_foreign_key_rejected(context: ClinicalContext) -> None:
    from django.core.exceptions import ValidationError

    from clinical_operations import services
    from clinical_operations.models import StockLot

    clinic, _, actor, _ = context
    product = services.create_product(
        clinic_id=clinic.pk, actor=actor, name="Sintético", sku="FK"
    )
    other = ClinicFactory.create()
    with pytest.raises(ValidationError):
        StockLot(
            clinic_id=other.pk,
            product_id=product.pk,
            code="cross",
            expires_on=timezone.localdate(),
        ).save()


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Exige PostgreSQL real; SQLite não comprova concorrência.",
)
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_key", [False, True])
def test_postgresql_concurrent_stock_requests(
    context: ClinicalContext, same_key: bool
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    from clinical_operations import services
    from clinical_operations.models import StockMovement

    if connection.vendor != "postgresql":
        pytest.skip("Exige PostgreSQL real; SQLite não comprova locks concorrentes.")
    clinic, _, actor, patient = context
    product = services.create_product(
        clinic_id=clinic.pk, actor=actor, name="Sintético", sku="RACE"
    )
    lot = services.create_lot(
        clinic_id=clinic.pk,
        actor=actor,
        product_id=product.pk,
        code="RACE",
        expires_on=timezone.localdate() + timedelta(days=1),
    )
    services.move_stock(
        clinic_id=clinic.pk,
        actor=actor,
        lot_id=lot.pk,
        quantity=1,
        direction="in",
        key="receipt",
    )
    barrier = Barrier(2)

    def dispense(index: int) -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            row = services.move_stock(
                clinic_id=clinic.pk,
                actor=actor,
                lot_id=lot.pk,
                quantity=1,
                direction="out",
                key="same" if same_key else f"out-{index}",
                patient_id=patient.pk,
            )
            return str(row.pk)
        except services.Conflict as exc:
            return str(exc)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(dispense, range(2)))
    lot.refresh_from_db()
    assert lot.balance == 0
    assert StockMovement.objects.for_clinic(clinic.pk).count() == 2
    if same_key:
        assert results[0] == results[1]
    else:
        assert results.count("insufficient_stock") == 1


def test_write_rechecks_grant_after_acquiring_clinic_lock(
    context: ClinicalContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clinical_operations import services
    from clinical_operations.models import OperationGrant
    from clinics.services import lock_clinic_for_update

    clinic, _, actor, _ = context
    original = lock_clinic_for_update

    def revoke_before_lock(*, clinic_id: UUID) -> None:
        OperationGrant.objects.for_clinic(clinic_id).filter(
            user_id=actor.pk, capability="pharmacy.write"
        ).update(enabled=False)
        original(clinic_id=clinic_id)

    monkeypatch.setattr(services, "lock_clinic_for_update", revoke_before_lock)
    with pytest.raises(PermissionDenied):
        services.create_product(
            clinic_id=clinic.pk, actor=actor, name="Sintético", sku="REVOKED"
        )


@pytest.mark.parametrize(
    "resource",
    [
        "grants",
        "products",
        "lots",
        "movements",
        "encounters",
        "transitions",
        "records",
        "sessions",
        "enrollments",
        "attendance",
    ],
)
def test_anonymous_post_never_mutates(client: Client, resource: str) -> None:
    assert (
        client.post(
            API + resource + "/", {}, content_type="application/json"
        ).status_code
        == 401
    )


def test_http_complete_operational_flow(
    context: ClinicalContext, client: Client
) -> None:
    from audit.models import AuditEvent

    clinic, admin, actor, patient = context
    link_and_consent(context)
    login(client, clinic, actor)

    def post(
        resource: str,
        payload: Mapping[str, str | int | float | bool],
        expected: int = 201,
    ) -> dict[str, str]:
        response = client.post(
            API + resource + "/", payload, content_type="application/json"
        )
        assert response.status_code == expected, response.content
        body: dict[str, str] = response.json()
        return body

    product = post("products", {"name": "Produto sintético", "sku": "FLOW"})["id"]
    lot = post(
        "lots",
        {
            "product_id": product,
            "code": "FLOW",
            "expires_on": timezone.localdate().isoformat(),
        },
    )["id"]
    post(
        "movements", {"lot_id": lot, "quantity": 2, "direction": "in", "key": "FLOW-IN"}
    )
    out: dict[str, str | int | float | bool] = {
        "lot_id": lot,
        "quantity": 1,
        "direction": "out",
        "key": "FLOW-OUT",
        "patient_id": str(patient.pk),
    }
    assert post("movements", out) == post("movements", out)
    post("movements", {**out, "quantity": 2}, expected=409)
    post("movements", {**out, "quantity": True}, expected=400)
    post("movements", {**out, "key": "NEG", "quantity": -1}, expected=400)
    post("movements", {**out, "key": "FRACTION", "quantity": 1.5}, expected=400)
    start = timezone.now() + timedelta(days=1)
    encounter = post(
        "encounters", {"patient_id": str(patient.pk), "starts_at": start.isoformat()}
    )["id"]
    post(
        "transitions", {"encounter_id": encounter, "status": "concluido"}, expected=409
    )
    post("transitions", {"encounter_id": encounter, "status": "em_atendimento"})
    content = "Conteúdo clínico sintético reservado FLOW"
    post("records", {"encounter_id": encounter, "content": content})
    before = AuditEvent.objects.for_clinic(clinic.pk).count()
    read = client.get(API + "records/", {"encounter_id": encounter})
    assert read.status_code == 200
    assert read.json()["results"][0]["content"] == content
    assert AuditEvent.objects.for_clinic(clinic.pk).count() == before
    assert content not in str(list(AuditEvent.objects.for_clinic(clinic.pk).values()))
    session = post(
        "sessions",
        {
            "kind": "individual",
            "modality": "yoga",
            "capacity": 1,
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=1)).isoformat(),
        },
    )["id"]
    enrollment = post(
        "enrollments", {"session_id": session, "patient_id": str(patient.pk)}
    )["id"]
    post("attendance", {"enrollment_id": enrollment, "status": "ausente"})
    for resource in (
        "products",
        "lots",
        "movements",
        "encounters",
        "sessions",
        "enrollments",
    ):
        response = client.get(API + resource + "/")
        assert response.status_code == 200
        assert response.json()["results"]
        assert content not in response.content.decode()
    login(client, clinic, admin)
    assert client.get(API + "records/", {"encounter_id": encounter}).status_code == 403
    post(
        "grants",
        {"user_id": str(actor.pk), "capability": "record.write", "enabled": False},
    )
    login(client, clinic, actor)
    post("records", {"encounter_id": encounter, "content": "Bloqueado"}, expected=403)


def test_cross_patient_fk_and_no_consent(context: ClinicalContext) -> None:
    from django.core.exceptions import ValidationError

    from clinical_operations import services
    from clinical_operations.selectors import read_records
    from people.models import CareRelationship

    clinic, admin, actor, patient = context
    other_patient = UserFactory.create()
    ClinicMembershipFactory.create(user=other_patient, role="patient")
    args: ServiceArguments = dict(clinic_id=clinic.pk, actor=actor)
    product = services.create_product(**args, name="Sintético", sku="CROSS")
    lot = services.create_lot(
        **args, product_id=product.pk, code="CROSS", expires_on=timezone.localdate()
    )
    services.move_stock(**args, lot_id=lot.pk, direction="in", quantity=1, key="IN")
    with pytest.raises(ValidationError):
        services.move_stock(
            **args,
            lot_id=lot.pk,
            direction="out",
            quantity=1,
            key="CROSS",
            patient_id=other_patient.pk,
        )
    CareRelationship.infrastructure_objects.create(
        clinic=clinic,
        therapist=actor,
        patient=patient,
        authorized_by=admin,
        valid_from=timezone.localdate(),
    )
    encounter = services.schedule_encounter(
        **args, patient_id=patient.pk, starts_at=timezone.now() + timedelta(days=1)
    )
    services.transition_encounter(
        **args, encounter_id=encounter.pk, status="em_atendimento"
    )
    with pytest.raises(PermissionDenied):
        services.append_record(
            **args, encounter_id=encounter.pk, content="Sem consentimento"
        )
    with pytest.raises(PermissionDenied):
        read_records(**args, encounter_id=encounter.pk)


@pytest.mark.parametrize(
    "state",
    [
        "user_inactive",
        "membership_inactive",
        "membership_expired",
        "clinic_inactive",
        "wrong_role",
    ],
)
def test_persisted_authorization_is_rechecked(
    context: ClinicalContext, state: str
) -> None:
    from clinical_operations import services
    from clinics.models import ClinicMembership

    clinic, _, actor, _ = context
    if state == "user_inactive":
        type(actor).objects.filter(pk=actor.pk).update(is_active=False)
    elif state == "clinic_inactive":
        type(clinic).infrastructure_objects.filter(pk=clinic.pk).update(is_active=False)
    else:
        changes: MembershipChanges = (
            {"is_active": False}
            if state == "membership_inactive"
            else {
                "valid_until": timezone.localdate() - timedelta(days=1),
                "valid_from": timezone.localdate() - timedelta(days=2),
            }
            if state == "membership_expired"
            else {"role": "patient"}
        )
        ClinicMembership.objects.for_clinic(clinic.pk).filter(user=actor).update(
            **changes
        )
    with pytest.raises(PermissionDenied):
        services.create_product(
            clinic_id=clinic.pk, actor=actor, name="Sintético", sku="STALE"
        )


def test_audit_failure_rolls_back_stock(
    context: ClinicalContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clinical_operations import services
    from clinical_operations.models import StockMovement

    clinic, _, actor, _ = context
    args: ServiceArguments = dict(clinic_id=clinic.pk, actor=actor)
    product = services.create_product(**args, name="Sintético", sku="ROLLBACK")
    lot = services.create_lot(
        **args, product_id=product.pk, code="RB", expires_on=timezone.localdate()
    )

    def unavailable(**kwargs: Unpack[AuditEventArguments]) -> Never:
        raise RuntimeError("Falha sintética de auditoria")

    monkeypatch.setattr(services, "record_audit_event", unavailable)
    with pytest.raises(RuntimeError):
        services.move_stock(**args, lot_id=lot.pk, quantity=1, direction="in", key="RB")
    lot.refresh_from_db()
    assert lot.balance == 0
    assert not StockMovement.objects.for_clinic(clinic.pk).exists()


@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="Capacidade concorrente exige PostgreSQL real.",
)
@pytest.mark.django_db(transaction=True)
def test_postgresql_concurrent_session_capacity(context: ClinicalContext) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    from clinical_operations import services
    from clinical_operations.models import Enrollment
    from people.models import CareRelationship

    clinic, admin, actor, first = context
    second = UserFactory.create()
    ClinicMembershipFactory.create(clinic=clinic, user=second, role="patient")
    for patient in (first, second):
        CareRelationship.infrastructure_objects.create(
            clinic=clinic,
            therapist=actor,
            patient=patient,
            authorized_by=admin,
            valid_from=timezone.localdate(),
        )
    start = timezone.now() + timedelta(days=1)
    session = services.schedule_session(
        clinic_id=clinic.pk,
        actor=actor,
        kind="grupo",
        modality="psicoterapia",
        capacity=1,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
    )
    barrier = Barrier(2)

    def enroll(patient: User) -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            services.enroll_patient(
                clinic_id=clinic.pk,
                actor=actor,
                session_id=session.pk,
                patient_id=patient.pk,
            )
            return "enrolled"
        except services.Conflict as exc:
            return str(exc)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(enroll, (first, second)))
    assert sorted(results) == ["capacity_reached", "enrolled"]
    assert Enrollment.objects.for_clinic(clinic.pk).count() == 1


def test_idempotency_key_is_preserved_literally(
    context: ClinicalContext, client: Client
) -> None:
    from clinical_operations import services

    clinic, _, actor, _ = context
    product = services.create_product(
        clinic_id=clinic.pk, actor=actor, name="Sintético", sku="KEY"
    )
    lot = services.create_lot(
        clinic_id=clinic.pk,
        actor=actor,
        product_id=product.pk,
        code="KEY",
        expires_on=timezone.localdate(),
    )
    login(client, clinic, actor)
    rows = []
    for key in ("K", " K "):
        response = client.post(
            API + "movements/",
            {"lot_id": str(lot.pk), "quantity": 1, "direction": "in", "key": key},
            content_type="application/json",
        )
        assert response.status_code == 201
        rows.append(response.json()["id"])
    assert rows[0] != rows[1]
    lot.refresh_from_db()
    assert lot.balance == 2
