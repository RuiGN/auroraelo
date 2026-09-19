"""Exercise MFA schema removal only in an explicitly isolated test database.

Use config.settings.test, TEST_DATABASE=postgresql, and a freshly created
DB_NAME=mindcare_mfa_verification on compose.test.yml's PostgreSQL service.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


def main() -> None:
    django.setup()
    database = settings.DATABASES["default"]
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.test"
    assert database["NAME"] == "mindcare_mfa_verification"
    assert database["HOST"] == "127.0.0.1" and str(database["PORT"]) == "55439"
    assert connection.vendor == "postgresql"
    assert not connection.introspection.table_names(), "Use a fresh empty test database"

    before = [("accounts", "0007_user_preferred_language")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    apps = executor.loader.project_state(before).apps
    user = apps.get_model("accounts", "User").objects.create(
        email="migration@example.invalid"
    )
    apps.get_model("accounts", "UserMFA").objects.create(
        user=user, encrypted_secret="retired-fixture"
    )
    apps.get_model("accounts", "MFARecoveryCode").objects.create(
        user=user, code_digest="retired-fixture"
    )
    from accounts.models import AccountSession, User

    session = AccountSession.objects.create_for_session(
        user=User.objects.get(pk=user.pk),
        session_key="isolated-migration-fixture",
        client_label="Migration test",
        network_hint="",
        absolute_expires_at=timezone.now(),
    )
    assert {"accounts_usermfa", "accounts_mfarecoverycode"}.issubset(
        connection.introspection.table_names()
    )
    MigrationExecutor(connection).migrate([("accounts", "0008_remove_mfa")])
    tables = set(connection.introspection.table_names())
    assert not {"accounts_usermfa", "accounts_mfarecoverycode"} & tables
    assert "accounts_accountsession" in tables
    session.refresh_from_db()
    assert session.decrypt_session_key() == "isolated-migration-fixture"
    assert User.objects.filter(pk=user.pk).exists()
    print(
        "PASS PostgreSQL 0007 -> 0008: MFA tables removed; "
        "user and encrypted session preserved"
    )


if __name__ == "__main__":
    main()
