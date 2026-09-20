"""Imutabilidade no banco, inclusive UPDATE/DELETE fora do ORM."""
from django.db import migrations

TABLES = ("clinical_operations_stockmovement", "clinical_operations_clinicalrecord")


def install(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == "postgresql":
        schema_editor.execute("""
            CREATE FUNCTION clinical_operations_reject_mutation() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                RAISE EXCEPTION 'clinical_operations_append_only';
            END; $$
        """)
        for table in TABLES:
            schema_editor.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION clinical_operations_reject_mutation()"
            )
    elif vendor == "sqlite":
        for table in TABLES:
            for operation in ("UPDATE", "DELETE"):
                schema_editor.execute(
                    f"CREATE TRIGGER {table}_{operation.lower()} BEFORE {operation} "
                    f"ON {table} BEGIN "
                    "SELECT RAISE(ABORT, 'clinical_operations_append_only'); END"
                )
    else:
        raise RuntimeError("Operações clínicas exigem PostgreSQL ou SQLite de teste.")


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        for table in TABLES:
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
        schema_editor.execute("DROP FUNCTION IF EXISTS clinical_operations_reject_mutation()")
    elif schema_editor.connection.vendor == "sqlite":
        for table in TABLES:
            for operation in ("update", "delete"):
                schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_{operation}")


class Migration(migrations.Migration):
    dependencies = [("clinical_operations", "0001_initial")]
    operations = [migrations.RunPython(install, uninstall)]
