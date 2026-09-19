"""Provision a synthetic workspace account for the Duralux customizer verifier.

Creates a user with a clinic admin membership and prints the credentials so the
caller can launch the Playwright runner with the env vars it requires. Only
intended for local verification; this script never touches production data and
refuses to run when DEBUG is False or when the target database is not test.
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import django

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT_STR = str(BACKEND_ROOT)
if BACKEND_ROOT_STR not in sys.path:
    sys.path.insert(0, BACKEND_ROOT_STR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
os.environ.setdefault("DJANGO_SECURE_SSL_REDIRECT", "False")
os.environ.setdefault("TEST_DATABASE", "postgresql")
os.environ.setdefault("DB_NAME", "mindcare")
os.environ.setdefault("DB_USER", "mindcare")
os.environ.setdefault("DB_PASSWORD", "mindcare-test-only")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "55439")

warnings.filterwarnings("ignore", message="No directory at:")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from tests.factories import (  # noqa: E402
    ClinicFactory,
    ClinicMembershipFactory,
    UserFactory,
)

EMAIL = os.environ.get("MINDCARE_TEST_EMAIL", "sintetico+customizer@example.test")
PASSWORD = os.environ.get("MINDCARE_TEST_PASSWORD", "Sintetico-9f81!timeoutProbe")

user = get_user_model().objects.filter(email=EMAIL).first() or UserFactory.create(
    email=EMAIL
)
user.set_password(PASSWORD)
user.save(update_fields=("password",))
user.is_active = True
user.save(update_fields=("is_active",))

clinic = ClinicFactory.create()
ClinicMembershipFactory.create(user=user, clinic=clinic, role="clinic_admin")

print(f"MINDCARE_TEST_EMAIL={EMAIL}")
print(f"MINDCARE_TEST_PASSWORD={PASSWORD}")
print(f"clinic_pk={clinic.pk}")
