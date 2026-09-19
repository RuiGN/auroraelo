"""Deployment isolation contracts for the migrated Mindcare application."""

import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize("trusted_origins", (None, "https://mindcare.example.test"))
def test_production_trusts_only_explicit_csrf_origins(
    trusted_origins: str | None,
) -> None:
    """A new deployment must not inherit cross-origin trust from the source."""
    environment = {
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "test-only-production-secret",
        "AUDIT_INTEGRITY_KEY": "test-only-audit-integrity-key-32-characters",
        "MFA_ENCRYPTION_KEY": "test-only-mfa-key-32-characters-long",
        "DJANGO_ALLOWED_HOSTS": "mindcare.example.test",
        "CACHE_URL": "redis://127.0.0.1:6379/15",
        "DB_NAME": "mindcare_test",
        "DB_USER": "test",
        "DB_PASSWORD": "test",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_SSLROOTCERT": "/test-only/postgresql-ca.pem",
    }
    if trusted_origins is not None:
        environment["DJANGO_CSRF_TRUSTED_ORIGINS"] = trusted_origins
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from django.conf import settings; "
            "print(json.dumps(settings.CSRF_TRUSTED_ORIGINS))",
        ],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == (
        [trusted_origins] if trusted_origins is not None else []
    )
