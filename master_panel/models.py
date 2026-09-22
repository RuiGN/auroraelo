"""Tenant subscription and usage models for the master control panel."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from clinics.models import Clinic


class TenantSubscription(models.Model):
    """Stripe billing state for one clinic tenant."""

    class Plan(models.TextChoices):
        FREE = "free", "Gratuito"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Profissional"
        ENTERPRISE = "enterprise", "Enterprise"

    class Status(models.TextChoices):
        TRIALING = "trialing", "Em período de teste"
        ACTIVE = "active", "Ativo"
        PAST_DUE = "past_due", "Inadimplente"
        CANCELED = "canceled", "Cancelado"
        BLOCKED = "blocked", "Bloqueado"

    clinic = models.OneToOneField(
        Clinic,
        on_delete=models.CASCADE,
        related_name="subscription",
        to_field="id",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")
    plan = models.CharField(
        max_length=32, choices=Plan.choices, default=Plan.FREE
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.TRIALING
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    block_reason = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assinatura de tenant"
        verbose_name_plural = "Assinaturas de tenants"

    def __str__(self) -> str:
        return f"{self.clinic.name} [{self.plan} / {self.status}]"

    @property
    def is_blocked(self) -> bool:
        return self.status == self.Status.BLOCKED

    @property
    def is_past_due(self) -> bool:
        return self.status == self.Status.PAST_DUE

    @property
    def is_active(self) -> bool:
        return self.status in (self.Status.ACTIVE, self.Status.TRIALING)

    def block(self, reason: str = "Inadimplência") -> None:
        self.status = self.Status.BLOCKED
        self.blocked_at = timezone.now()
        self.block_reason = reason
        self.save(update_fields=["status", "blocked_at", "block_reason", "updated_at"])

    def unblock(self) -> None:
        self.status = self.Status.ACTIVE
        self.blocked_at = None
        self.block_reason = ""
        self.save(update_fields=["status", "blocked_at", "block_reason", "updated_at"])


class TenantUsageSnapshot(models.Model):
    """Periodic usage snapshot for one clinic tenant."""

    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="usage_snapshots",
    )
    snapshot_at = models.DateTimeField(auto_now_add=True)
    active_users = models.PositiveIntegerField(default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    storage_mb = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    api_calls = models.PositiveIntegerField(default=0)
    appointments = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Snapshot de uso"
        verbose_name_plural = "Snapshots de uso"
        ordering = ["-snapshot_at"]
        indexes = [
            models.Index(fields=["clinic", "snapshot_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.clinic.name} @ {self.snapshot_at:%Y-%m-%d %H:%M}"
