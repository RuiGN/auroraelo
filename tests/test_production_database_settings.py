"""Regression tests for production PostgreSQL and replica configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import postgres_database_from_url

PROJECT_ROOT = Path(__file__).parents[1]


def _production_environment() -> dict[str, str]:
    """Return production settings with only redacted synthetic values."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_ROOT),
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "synthetic-django-secret-key-for-tests",
        "AUDIT_INTEGRITY_KEY": "synthetic-audit-integrity-key-32-chars",
        "MFA_ENCRYPTION_KEY": "synthetic-mfa-key",
        "MASTER_USER_EMAIL": "master.synthetic@example.test",
        "MASTER_USER_PASSWORD": "synthetic-master-password-only",
        "CACHE_REDIS_URL": "redis://127.0.0.1:6379/1",
        "DJANGO_ALLOWED_HOSTS": "testserver",
        "DB_NAME": "synthetic_db",
        "DB_USER": "synthetic_user",
        "DB_PASSWORD": "synthetic_password",
        "DB_HOST": "primary.synthetic",
        "DB_PORT": "5432",
        "DB_SSLMODE": "verify-ca",
        "DB_SSLROOTCERT": "/synthetic/ca.pem",
    }


def test_postgres_database_from_url_decodes_encoded_connection_values() -> None:
    """Replica URL parsing preserves a complete synthetic PostgreSQL config."""
    config = postgres_database_from_url(
        "postgresql://replica%20user:pass%40word@replica.synthetic:5440/replica%20db"
    )

    assert config == {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "replica db",
        "USER": "replica user",
        "PASSWORD": "pass@word",
        "HOST": "replica.synthetic",
        "PORT": "5440",
    }


def test_postgres_database_from_url_rejects_malformed_value_without_echoing_it() -> (
    None
):
    """Malformed replica configuration raises a redacted configuration error."""
    malformed = "not-a-database-url-with-a-synthetic-secret"

    with pytest.raises(ImproperlyConfigured) as error:
        postgres_database_from_url(malformed)

    assert "REPLICA_DATABASE_URL" in str(error.value)
    assert malformed not in str(error.value)


def test_production_settings_without_replica_only_configure_primary() -> None:
    """Production imports without an optional replica alias."""
    environment = _production_environment()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from django.conf import settings; "
                "assert sorted(settings.DATABASES) == ['default']"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_production_settings_adds_replica_with_primary_tls_options() -> None:
    """A valid replica URL gets only the configured database and TLS options."""
    environment = _production_environment()
    environment["REPLICA_DATABASE_URL"] = (
        "postgresql://replica_user:synthetic_password@replica.synthetic:5440/replica_db"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from django.conf import settings; "
                "replica = settings.DATABASES['replica']; "
                "assert replica['HOST'] == 'replica.synthetic'; "
                "assert replica['PORT'] == '5440'; "
                "assert replica['OPTIONS'] == {'sslmode': 'verify-ca', "
                "'sslrootcert': '/synthetic/ca.pem'}; "
                "assert 'TEST' not in replica"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "synthetic_password" not in result.stdout + result.stderr


def test_production_settings_rejects_malformed_replica_without_echoing_value() -> None:
    """A malformed optional replica fails import without logging its contents."""
    environment = _production_environment()
    malformed = "postgresql://broken:synthetic_password@"
    environment["REPLICA_DATABASE_URL"] = malformed
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.production"],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "REPLICA_DATABASE_URL" in result.stderr
    assert malformed not in result.stdout + result.stderr
    assert "synthetic_password" not in result.stdout + result.stderr
