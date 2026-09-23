"""Regression coverage for the production static-files manifest failure.

The production storage resolves every ``{% static %}`` reference against the
collected manifest. Jazzmin's admin template references ``vendor/bootswatch`` as
a directory, which is never a manifest entry, so a strict manifest turned every
``/admin/`` page into a 500.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from django.test import Client, override_settings
from whitenoise.storage import CompressedManifestStaticFilesStorage

from config.storage import TolerantCompressedManifestStaticFilesStorage
from tests.factories import UserFactory
from tests.test_production_database_settings import (
    PROJECT_ROOT,
    _production_environment,
)

JAZZMIN_DIRECTORY_REFERENCE = "vendor/bootswatch"
EXPECTED_BACKEND = "config.storage.TolerantCompressedManifestStaticFilesStorage"


def _manifest_root(tmp_path):
    """Create a valid collected manifest that lacks the Jazzmin entry."""
    static_root = tmp_path / "staticfiles"
    static_root.mkdir()
    manifest = {"version": "1.1", "hash": "", "paths": {}}
    (static_root / "staticfiles.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return static_root


@pytest.mark.django_db
def test_strict_manifest_rejects_the_jazzmin_directory_reference(tmp_path) -> None:
    """The strict storage is what turned every admin page into a 500."""
    static_root = _manifest_root(tmp_path)
    strict = CompressedManifestStaticFilesStorage(
        location=str(static_root), base_url="/static/"
    )
    with pytest.raises(ValueError):
        strict.url(JAZZMIN_DIRECTORY_REFERENCE)

    tolerant = TolerantCompressedManifestStaticFilesStorage(
        location=str(static_root), base_url="/static/"
    )
    assert tolerant.url(JAZZMIN_DIRECTORY_REFERENCE) == (
        f"/static/{JAZZMIN_DIRECTORY_REFERENCE}"
    )


def test_production_uses_the_tolerant_manifest_storage() -> None:
    """Production must not keep the strict backend that raises for that path."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from django.conf import settings; "
                "print(settings.STORAGES['staticfiles']['BACKEND'])"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=_production_environment(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == EXPECTED_BACKEND
    assert issubclass(
        TolerantCompressedManifestStaticFilesStorage,
        CompressedManifestStaticFilesStorage,
    )
    assert TolerantCompressedManifestStaticFilesStorage.manifest_strict is False


@pytest.mark.django_db
def test_admin_index_renders_with_a_manifest_missing_the_jazzmin_entry(
    tmp_path,
) -> None:
    """The authenticated admin index renders instead of raising ValueError."""
    static_root = _manifest_root(tmp_path)
    client = Client(raise_request_exception=True)
    client.force_login(UserFactory.create(is_staff=True, is_superuser=True))

    storages = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": EXPECTED_BACKEND},
    }
    with override_settings(STATIC_ROOT=str(static_root), STORAGES=storages):
        response = client.get("/admin/")

    assert response.status_code == 200
    assert len(response.content) > 1000
