"""Regressão PostgreSQL de revogação confirmada durante espera posterior à raiz."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic, sleep
from typing import cast

import pytest
from django.db import close_old_connections, connection, transaction
from django.http import HttpResponse

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from clinics.services import update_membership_role
from psychiatry import api
from psychiatry.models import PsychiatricEvaluation, PsychiatricPatientProfile
from tests import test_psychiatry_security as security_fixtures

identities = security_fixtures.identities
linked_profile = security_fixtures.linked_profile
own_profile = security_fixtures.own_profile

type Identities = tuple[Clinic, Clinic, dict[str, User]]

grant_follow_up = cast(
    Callable[[Identities], object], security_fixtures.grant_follow_up
)
request_for = cast(Callable[..., HttpResponse], security_fixtures.request_for)

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor != "postgresql", reason="Exige locks PostgreSQL reais."
    ),
]


def test_membership_revocation_cannot_commit_before_pending_evaluation(
    identities: Identities, linked_profile: PsychiatricPatientProfile
) -> None:
    """Pausar o INSERT depois da política não pode permitir escrita já revogada."""
    clinic, _, actors = identities
    grant_follow_up(identities)
    membership = ClinicMembership.infrastructure_objects.get(
        clinic=clinic, user=actors["therapist"]
    )
    payload = {
        "patient_id": str(linked_profile.uuid),
        "chief_complaint": "Sintético",
        "hda": "Sintético",
        "anxiety_scale": 1,
        "risk_level": "LOW",
        "diagnostic_impression": "Relato sintético",
        "therapeutic_plan": "Revisão humana",
    }
    pids: Queue[int] = Queue()
    revocation_pids: Queue[int] = Queue()
    completed = Event()

    def write() -> HttpResponse:
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '15000ms'")
                cursor.execute("SELECT pg_backend_pid()")
                pids.put(cursor.fetchone()[0])
            return request_for(
                api.save_anamnesis,
                actor=actors["therapist"],
                clinic=clinic,
                method="post",
                data=payload,
            )
        finally:
            completed.set()
            connection.close()

    def revoke() -> str:
        close_old_connections()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET statement_timeout = '10000ms'")
                cursor.execute("SELECT pg_backend_pid()")
                revocation_pids.put(cursor.fetchone()[0])
            updated = update_membership_role(
                actor=actors["clinic_admin"],
                clinic=clinic,
                membership_id=membership.pk,
                role=ClinicMembership.Role.ADMINISTRATIVE_STAFF,
            )
            assert connection.get_autocommit()
            return updated.role
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        with transaction.atomic():
            # Constante de modelo verificada: sem interpolação de entrada HTTP.
            table = connection.ops.quote_name(PsychiatricEvaluation._meta.db_table)
            with connection.cursor() as cursor:
                cursor.execute(f"LOCK TABLE {table} IN SHARE MODE")
            write_future = pool.submit(write)
            pid = pids.get(timeout=10)
            blocked = False
            deadline = monotonic() + 10
            while monotonic() < deadline and not completed.is_set():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))", [pid]
                    )
                    blocked = cursor.fetchone()[0]
                if blocked:
                    break
                sleep(0.01)
            assert blocked, "A escrita não alcançou a espera SQL posterior à política."
            # Aceitar serialização real OU negar se a revogação confirmar primeiro.
            # Não exigir que uma implementação segura deixe a revogação ultrapassar.
            revocation_future = pool.submit(revoke)
            revocation_pid = revocation_pids.get(timeout=10)
            committed_before_release: bool | None = None
            deadline = monotonic() + 8
            while monotonic() < deadline:
                if revocation_future.done():
                    assert (
                        revocation_future.result()
                        == ClinicMembership.Role.ADMINISTRATIVE_STAFF
                    )
                    membership.refresh_from_db()
                    assert membership.role == ClinicMembership.Role.ADMINISTRATIVE_STAFF
                    committed_before_release = True
                    break
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT %s = ANY(pg_blocking_pids(%s))", [pid, revocation_pid]
                    )
                    serialized = cursor.fetchone()[0]
                if serialized:
                    committed_before_release = False
                    break
                sleep(0.01)
            assert committed_before_release is not None
        response = write_future.result(timeout=20)
        assert (
            revocation_future.result(timeout=12)
            == ClinicMembership.Role.ADMINISTRATIVE_STAFF
        )

    persisted = PsychiatricEvaluation.objects.filter(patient=linked_profile).count()
    outcome = (response.status_code, persisted)
    if committed_before_release:
        assert outcome in {(403, 0), (404, 0), (409, 0)}
    else:
        assert outcome == (200, 1)
