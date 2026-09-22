"""Unified tenant-scoped feature flag system.

Replaces per-domain rollout flag models (e.g. AiAssistantRolloutFlag,
IntegrationRolloutFlag) with a single, centrally managed flag registry.
Supports tenant-scoped and platform-wide flags with optional deterministic
percentage-based user rollout.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.persistence import UUIDTimestampedModel


class FeatureFlag(UUIDTimestampedModel):
    """A tenant-scoped feature toggle with optional percentage rollout."""

    class Meta:
        db_table = "core_feature_flag"
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "flag_key"],
                name="unique_flag_per_clinic",
            ),
        ]
        indexes = [
            models.Index(fields=["flag_key", "is_enabled"]),
        ]

    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="feature_flags",
    )
    flag_key = models.CharField(
        max_length=120,
        db_index=True,
        help_text="Dot-separated key, e.g. 'ai_assistant.enabled'.",
    )
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        help_text="Percentage of users within tenant that see this feature (0-100).",
    )
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = models.Manager()  # type: ignore[assignment]

    def __str__(self) -> str:
        status = "ON" if self.is_enabled else "OFF"
        pct = f" ({self.rollout_percentage}%)" if self.rollout_percentage < 100 else ""
        return f"{self.flag_key} [{status}{pct}] @ {self.clinic_id}"


class GlobalFeatureFlag(UUIDTimestampedModel):
    """Platform-wide feature flag independent of any clinic tenant."""

    class Meta:
        db_table = "core_global_feature_flag"

    flag_key = models.CharField(max_length=120, unique=True)
    is_enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    objects = models.Manager()  # type: ignore[assignment]

    def __str__(self) -> str:
        status = "ON" if self.is_enabled else "OFF"
        return f"{self.flag_key} [{status}] (global)"


# ── Selectors ─────────────────────────────────────────────────────────────────

import hashlib
from uuid import UUID


def is_feature_enabled(
    *,
    clinic_id: UUID,
    flag_key: str,
    user_id: UUID | None = None,
) -> bool:
    """Check if a tenant-scoped feature flag is active.

    When ``rollout_percentage`` is below 100, a deterministic hash of
    ``user_id`` decides membership so the same user always gets the same
    result for a given flag.
    """
    flag = (
        FeatureFlag.objects.filter(clinic_id=clinic_id, flag_key=flag_key)
        .values("is_enabled", "rollout_percentage")
        .first()
    )
    if flag is None or not flag["is_enabled"]:
        return False
    if flag["rollout_percentage"] >= 100:
        return True
    if user_id is None:
        return False
    # Deterministic hash-based rollout (consistent per user per flag).
    bucket = (
        int(hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest()[:8], 16) % 100
    )
    return bucket < flag["rollout_percentage"]


def is_global_feature_enabled(*, flag_key: str) -> bool:
    """Check if a platform-wide global feature flag is active."""
    flag = (
        GlobalFeatureFlag.objects.filter(flag_key=flag_key)
        .values("is_enabled")
        .first()
    )
    return flag is not None and flag["is_enabled"]
