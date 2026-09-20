"""Evolução aditiva exercitada apenas no banco sintético descartável."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_ownership_migration_preserves_legacy_values_and_does_not_backfill():
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(connection, ignore_no_migrations=True)
    if ("psychiatry", "0003_verified_ownership_and_opt_in") not in loader.graph.nodes:
        pytest.skip(
            "Requer migrations reais; ausentes do grafo sob pytest --nomigrations."
        )
    old_target = [("psychiatry", "0002_addictionprofile_cravingtrackinglog_and_more")]
    new_target = [("psychiatry", "0003_verified_ownership_and_opt_in")]
    executor = MigrationExecutor(connection)
    executor.migrate(old_target)
    try:
        old = executor.loader.project_state(old_target).apps
        patient = old.get_model(
            "psychiatry", "PsychiatricPatientProfile"
        ).objects.create(
            full_name="Legado Sintético",
            cpf="migration-test",
            date_of_birth="1990-01-01",
            record_number="migration-test",
            phone="",
            tcle_signed=True,
        )
        mind = old.get_model("psychiatry", "B2CMindLog").objects.create(
            user_identifier="legacy"
        )
        bed = old.get_model("psychiatry", "InpatientBed").objects.create(
            bed_code="legacy"
        )
        executor = MigrationExecutor(connection)
        executor.migrate(new_target)
        new = executor.loader.project_state(new_target).apps
        preserved = new.get_model(
            "psychiatry", "PsychiatricPatientProfile"
        ).objects.get(pk=patient.pk)
        assert preserved.tcle_signed is True
        assert preserved.clinic_id is None and preserved.user_id is None
        assert (
            new.get_model("psychiatry", "B2CMindLog").objects.get(pk=mind.pk).user_id
            is None
        )
        assert (
            new.get_model("psychiatry", "InpatientBed").objects.get(pk=bed.pk).clinic_id
            is None
        )
        assert (
            new.get_model("psychiatry", "PsychiatricPatientProfile")().tcle_signed
            is False
        )
    finally:
        MigrationExecutor(connection).migrate(new_target)
