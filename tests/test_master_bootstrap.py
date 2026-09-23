"""Regression tests for production Master bootstrap configuration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core import management
from django.core.management.base import CommandError
from django.test import override_settings

from accounts.models import User

PROJECT_ROOT = Path(__file__).parents[1]


MASTER_EMAIL = "master.synthetic@example.test"
MASTER_PASSWORD = "synthetic-master-password-only"


def _production_environment(*, include_master: bool) -> dict[str, str]:
    """Return a minimal production environment containing only synthetic values."""
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_ROOT),
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": "synthetic-django-secret-key-for-tests",
        "AUDIT_INTEGRITY_KEY": "synthetic-audit-integrity-key-32-chars",
        "MFA_ENCRYPTION_KEY": "synthetic-mfa-key",
        "CACHE_REDIS_URL": "redis://127.0.0.1:6379/1",
        "DJANGO_ALLOWED_HOSTS": "testserver",
        "DB_NAME": "synthetic_db",
        "DB_USER": "synthetic_user",
        "DB_PASSWORD": "synthetic_password",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_SSLMODE": "disable",
    }
    if include_master:
        environment["MASTER_USER_EMAIL"] = MASTER_EMAIL
        environment["MASTER_USER_PASSWORD"] = MASTER_PASSWORD
    return environment


def test_production_requires_master_email_and_password() -> None:
    """Production settings fail before startup when Master credentials are absent."""
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.production"],
        cwd=PROJECT_ROOT,
        env=_production_environment(include_master=False),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "MASTER_USER_EMAIL" in result.stderr
    assert MASTER_PASSWORD not in result.stdout + result.stderr


def test_production_imports_with_synthetic_master_credentials() -> None:
    """Production settings import when all mandatory values are supplied."""
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.production"],
        cwd=PROJECT_ROOT,
        env=_production_environment(include_master=True),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert MASTER_PASSWORD not in result.stdout + result.stderr


@pytest.mark.django_db
def test_ensure_master_user_creates_without_echoing_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The bootstrap command creates a valid global operator without logging secrets."""
    with override_settings(
        MASTER_USER_EMAIL=MASTER_EMAIL,
        MASTER_USER_PASSWORD=MASTER_PASSWORD,
    ):
        management.call_command("ensure_master_user")

    user = User.objects.get(email=MASTER_EMAIL)
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password(MASTER_PASSWORD)
    output = capsys.readouterr().out
    assert MASTER_EMAIL not in output
    assert MASTER_PASSWORD not in output


@pytest.mark.django_db
def test_ensure_master_user_is_idempotent_without_resetting_existing_password(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An existing valid Master is preserved and never receives a silent password
    reset.
    """
    old_password = "old-synthetic-password"
    User.objects.create_superuser(
        email=MASTER_EMAIL,
        password=old_password,
        username="",
    )

    with override_settings(
        MASTER_USER_EMAIL=MASTER_EMAIL,
        MASTER_USER_PASSWORD=MASTER_PASSWORD,
    ):
        management.call_command("ensure_master_user")

    assert User.objects.filter(email=MASTER_EMAIL).count() == 1
    user = User.objects.get(email=MASTER_EMAIL)
    assert user.check_password(old_password)
    assert not user.check_password(MASTER_PASSWORD)
    output = capsys.readouterr().out
    assert MASTER_EMAIL not in output
    assert MASTER_PASSWORD not in output


@pytest.mark.django_db
def test_ensure_master_user_rejects_existing_non_global_account() -> None:
    """Bootstrap fails closed instead of silently promoting an invalid account."""
    User.objects.create_user(email=MASTER_EMAIL, password="old-synthetic-password")

    with (
        override_settings(
            MASTER_USER_EMAIL=MASTER_EMAIL,
            MASTER_USER_PASSWORD=MASTER_PASSWORD,
        ),
        pytest.raises(CommandError, match="global operator"),
    ):
        management.call_command("ensure_master_user")
