"""Tenant lifecycle services shared by the Master Panel and maintenance jobs."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.translation import gettext

from accounts.events import account_audit_required
from clinics.models import Clinic

from .models import TenantSubscription, TenantUsageSnapshot
from .user_services import require_global_operator

if TYPE_CHECKING:
    from django.db.models import QuerySet


@dataclass(frozen=True, slots=True)
class TenantPanelRow:
    """A clinic row whose commercial state may still be unconfigured."""

    clinic: Clinic
    subscription: TenantSubscription | None

    UNCONFIGURED_STATUS = "unconfigured"

    @property
    def status(self) -> str:
        """Return the persisted state or the explicit missing-state marker."""
        if self.subscription is None:
            return self.UNCONFIGURED_STATUS
        return self.subscription.status

    @property
    def plan(self) -> str:
        """Return the persisted plan or the default display plan."""
        if self.subscription is None:
            return TenantSubscription.Plan.FREE
        return self.subscription.plan

    @property
    def created_at(self) -> datetime:
        """Use the clinic creation time until a commercial record exists."""
        if self.subscription is not None:
            return self.subscription.created_at
        return self.clinic.created_at

    @property
    def is_blocked(self) -> bool:
        """Return whether the persisted commercial state blocks the tenant."""
        return self.subscription is not None and self.subscription.is_blocked

    @property
    def is_past_due(self) -> bool:
        """Return whether the persisted commercial state is past due."""
        return self.subscription is not None and self.subscription.is_past_due

    def get_plan_display(self) -> str:
        """Expose a safe localized-ish label for the existing templates."""
        if self.subscription is None:
            return "Gratuito (padrão)"
        return self.subscription.get_plan_display()

    def get_status_display(self) -> str:
        """Expose a clear state when billing has not been initialized yet."""
        if self.subscription is None:
            return "Sem assinatura configurada"
        return self.subscription.get_status_display()

    @property
    def stripe_customer_id(self) -> str:
        """Expose billing identifiers only when a commercial row exists."""
        return self.subscription.stripe_customer_id if self.subscription else ""


def ensure_tenant_subscription(*, clinic_id: UUID) -> TenantSubscription:
    """Create the neutral trial record for one clinic exactly once.

    The clinic is locked before the one-to-one lookup so concurrent bootstrap,
    detail and backfill requests cannot create competing commercial rows.
    Existing Stripe state is never overwritten.
    """
    with transaction.atomic():
        clinic = Clinic.infrastructure_objects.select_for_update().get(pk=clinic_id)
        subscription, _created = (
            TenantSubscription.objects.select_for_update().get_or_create(
                clinic=clinic,
                defaults={
                    "plan": TenantSubscription.Plan.FREE,
                    "status": TenantSubscription.Status.TRIALING,
                },
            )
        )
    return subscription


def backfill_tenant_subscriptions(*, clinic_ids: Iterable[UUID] | None = None) -> int:
    """Ensure missing neutral commercial rows without altering valid data."""
    ids = clinic_ids
    if ids is None:
        ids = Clinic.infrastructure_objects.values_list("pk", flat=True)
    created = 0
    for clinic_id in ids:
        before = TenantSubscription.objects.filter(clinic_id=clinic_id).exists()
        ensure_tenant_subscription(clinic_id=clinic_id)
        if not before:
            created += 1
    return created


def tenant_panel_rows(*, q: str = "", status: str = "") -> list[TenantPanelRow]:
    """Return every infrastructure clinic, including rows without billing state."""
    clinics: QuerySet[Clinic] = Clinic.infrastructure_objects.all().order_by(
        "-created_at", "-pk"
    )
    if q:
        clinics = clinics.filter(name__icontains=q) | clinics.filter(slug__icontains=q)
    clinic_rows = list(clinics)
    subscriptions = {
        subscription.clinic_id: subscription
        for subscription in TenantSubscription.objects.filter(
            clinic_id__in=[clinic.pk for clinic in clinic_rows]
        )
    }
    rows = [
        TenantPanelRow(clinic=clinic, subscription=subscriptions.get(clinic.pk))
        for clinic in clinic_rows
    ]
    if status:
        rows = [row for row in rows if row.status == status]
    return rows


def latest_usage_snapshots() -> list[TenantUsageSnapshot]:
    """Return the newest snapshot per clinic without PostgreSQL DISTINCT ON."""
    newest: dict[UUID, TenantUsageSnapshot] = {}
    snapshots = TenantUsageSnapshot.objects.select_related("clinic").order_by(
        "clinic_id", "-snapshot_at", "-pk"
    )
    for snapshot in snapshots.iterator():
        if snapshot.clinic_id not in newest:
            newest[snapshot.clinic_id] = snapshot
    return list(newest.values())


@transaction.atomic
def set_tenant_blocked(
    *,
    actor: AbstractBaseUser,
    clinic_id: UUID,
    blocked: bool,
    reason: str = "",
    request_id: UUID | None = None,
) -> TenantSubscription:
    """Block or unblock a clinic through one audited operator path."""
    operator = require_global_operator(actor)
    clinic = Clinic.infrastructure_objects.filter(pk=clinic_id).first()
    if clinic is None:
        raise PermissionDenied
    subscription = ensure_tenant_subscription(clinic_id=clinic.pk)
    if blocked:
        subscription.block(reason=reason.strip() or gettext("Bloqueio administrativo."))
    else:
        subscription.unblock()
    audit_subscription_transition(
        subscription=subscription,
        justification=reason.strip() or gettext("Bloqueio administrativo."),
        actor_id=operator.pk,
        request_id=request_id,
    )
    return subscription


def audit_subscription_transition(
    *,
    subscription: TenantSubscription,
    justification: str,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> None:
    """Record one audited tenant subscription transition.

    Operator actions pass the operator id; system-originated transitions (payment
    provider webhooks) pass ``None`` and explain the trigger in the justification,
    so every status change leaves the same audit trail.
    """
    account_audit_required.send(
        sender=TenantSubscription,
        clinic_id=subscription.clinic_id,
        actor_id=actor_id,
        action="update",
        resource_type="tenant_subscription",
        resource_id=str(subscription.pk),
        request_id=request_id or uuid4(),
        network_origin=None,
        justification=justification or None,
    )


__all__ = [
    "TenantPanelRow",
    "audit_subscription_transition",
    "backfill_tenant_subscriptions",
    "ensure_tenant_subscription",
    "latest_usage_snapshots",
    "set_tenant_blocked",
    "tenant_panel_rows",
]
