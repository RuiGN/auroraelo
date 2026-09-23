"""Regression coverage for the Master Panel clinic source of truth."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clinics.models import Clinic
from master_panel.models import TenantSubscription, TenantUsageSnapshot
from master_panel.tenant_services import latest_usage_snapshots
from tests.factories import ClinicFactory, UserFactory

pytestmark = pytest.mark.django_db


def _master(client: Client) -> User:
    user = UserFactory.create(is_staff=True, is_superuser=True)
    client.force_login(user)
    return user


def test_tenant_list_includes_clinic_without_subscription(client: Client) -> None:
    """A clinic created by infrastructure admin is visible before billing setup."""
    _master(client)
    clinic = ClinicFactory.create(name="Clínica sem comercial")

    response = client.get(reverse("master_panel:tenant_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert clinic.name in content
    assert "Sem assinatura configurada" in content


def test_dashboard_counts_clinics_without_postgres_distinct_on(client: Client) -> None:
    """Dashboard counts Clinic roots and works on SQLite as well as PostgreSQL."""
    _master(client)
    clinic = ClinicFactory.create(name="Clínica do dashboard")

    response = client.get(reverse("master_panel:dashboard"))

    assert response.status_code == 200
    assert response.context["total_tenants"] == 1
    assert clinic.name in response.content.decode()


def test_tenant_detail_initializes_only_the_missing_subscription(
    client: Client,
) -> None:
    """Detail access creates the neutral state without touching commercial data."""
    _master(client)
    clinic = ClinicFactory.create(name="Clínica detalhada")

    response = client.get(
        reverse("master_panel:tenant_detail", kwargs={"clinic_id": clinic.pk})
    )

    assert response.status_code == 200
    subscription = TenantSubscription.objects.get(clinic=clinic)
    assert subscription.plan == TenantSubscription.Plan.FREE
    assert subscription.status == TenantSubscription.Status.TRIALING


def test_backfill_command_is_idempotent() -> None:
    """Maintenance backfill creates missing rows and preserves existing state."""
    clinic = ClinicFactory.create(name="Clínica para backfill")

    call_command("backfill_tenant_subscriptions")
    subscription = TenantSubscription.objects.get(clinic=clinic)
    subscription.status = TenantSubscription.Status.ACTIVE
    subscription.save(update_fields=("status", "updated_at"))

    call_command("backfill_tenant_subscriptions")

    subscription.refresh_from_db()
    assert subscription.status == TenantSubscription.Status.ACTIVE
    assert TenantSubscription.objects.filter(clinic=clinic).count() == 1


def test_dashboard_monthly_series_is_chronological(client: Client) -> None:
    """Monthly buckets are sent oldest-first so the chart reads left to right."""
    _master(client)
    older = ClinicFactory.create(name="Clínica mais antiga")
    newer = ClinicFactory.create(name="Clínica mais recente")
    now = timezone.now()
    Clinic.infrastructure_objects.filter(pk=older.pk).update(
        created_at=now - timedelta(days=70)
    )
    Clinic.infrastructure_objects.filter(pk=newer.pk).update(
        created_at=now - timedelta(days=5)
    )

    response = client.get(reverse("master_panel:dashboard"))

    labels = json.loads(response.context["chart_monthly_labels"])
    data = json.loads(response.context["chart_monthly_data"])
    expected_labels = [
        (now - timedelta(days=70)).strftime("%b/%Y"),
        (now - timedelta(days=5)).strftime("%b/%Y"),
    ]
    assert labels == expected_labels
    assert data == [1, 1]


def test_latest_usage_snapshots_keeps_only_the_newest_row_per_clinic() -> None:
    """One deterministic snapshot per clinic is returned without DISTINCT ON."""
    first = ClinicFactory.create(name="Clínica com histórico")
    second = ClinicFactory.create(name="Clínica com um snapshot")
    previous = TenantUsageSnapshot.objects.create(clinic=first, active_users=2)
    TenantUsageSnapshot.objects.filter(pk=previous.pk).update(
        snapshot_at=timezone.now() - timedelta(days=3)
    )
    newest = TenantUsageSnapshot.objects.create(clinic=first, active_users=11)
    TenantUsageSnapshot.objects.create(clinic=second, active_users=4)

    snapshots = latest_usage_snapshots()

    assert {snapshot.clinic_id for snapshot in snapshots} == {first.pk, second.pk}
    by_clinic = {snapshot.clinic_id: snapshot for snapshot in snapshots}
    assert by_clinic[first.pk].pk == newest.pk
    assert by_clinic[first.pk].active_users == 11
