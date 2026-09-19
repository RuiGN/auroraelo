"""Identity boundary evidence for the Sprint 03 migration gates."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import User
from clinics.models import Clinic
from clinics.policies import ClinicAuthorizationPolicy

pytestmark = pytest.mark.django_db


def test_technical_superuser_without_membership_has_no_clinical_scope(
    client: Client,
) -> None:
    """Framework administration never substitutes for a clinical membership."""
    clinic = Clinic.infrastructure_objects.create(
        name="Clínica Limite de Identidade",
        slug="clinica-limite-identidade",
    )
    superuser = User.objects.create_superuser(
        email="superusuario-tecnico@example.test",
        password="senha-sintetica-segura",
    )
    client.force_login(superuser)

    response = client.get(
        reverse("workspace_vertical"),
        headers={"X-Clinic-ID": str(clinic.pk)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Acesso à clínica não autorizado."}
    assert (
        ClinicAuthorizationPolicy().is_allowed(superuser, clinic, "clinic.read")
        is False
    )
