"""Deployment isolation contracts for the Aurora Elo application."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("trusted_origins", (None, "https://auroraelo.example.test"))
def test_production_trusts_only_explicit_csrf_origins(
    trusted_origins: str | None,
) -> None:
    """A new deployment must not inherit cross-origin trust from the source."""
    environment = {
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "test-only-production-secret",
        "AUDIT_INTEGRITY_KEY": "test-only-audit-integrity-key-32-characters",
        "MFA_ENCRYPTION_KEY": "test-only-mfa-key-32-characters-long",
        "DJANGO_ALLOWED_HOSTS": "auroraelo.example.test",
        "CACHE_REDIS_URL": "redis://127.0.0.1:6379/15",
        "DB_NAME": "auroraelo_test",
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


def test_readme_disposable_database_matches_current_compose() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    compose = (root / "compose.test.yml").read_text(encoding="utf-8")

    assert readme.startswith("# Aurora Elo\n")
    for variable, compose_variable in (
        ("DB_NAME", "POSTGRES_DB"),
        ("DB_USER", "POSTGRES_USER"),
        ("DB_PASSWORD", "POSTGRES_PASSWORD"),
    ):
        match = re.search(rf"^\s+{compose_variable}: (\S+)$", compose, re.MULTILINE)
        assert match is not None, compose_variable
        assert f"{variable}={match.group(1)}" in readme
