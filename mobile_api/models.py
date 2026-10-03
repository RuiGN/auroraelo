"""Sessões do app do paciente. Guarda só resumos (hash) dos tokens, nunca o token."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.persistence import UUIDTimestampedModel

from .contracts import (
    MAX_APP_VERSION_LENGTH,
    MAX_DEVICE_LABEL_LENGTH,
    Platform,
    RevokeReason,
)

_ModelT = TypeVar("_ModelT", bound=models.Model)


class MobileSessionQuerySet(models.QuerySet[_ModelT]):
    """Consultas sempre restritas a uma clínica explícita."""

    def for_clinic(self, clinic_id: UUID) -> MobileSessionQuerySet[_ModelT]:
        return self.filter(clinic_id=clinic_id)

    def active(self) -> MobileSessionQuerySet[_ModelT]:
        now = timezone.now()
        return self.filter(revoked_at__isnull=True, absolute_expires_at__gt=now)


class MobileSessionManager(models.Manager[_ModelT]):
    """Manager padrão: recusa consultas sem `.for_clinic(clinic_id)`."""

    def get_queryset(self) -> MobileSessionQuerySet[_ModelT]:
        if hasattr(self, "core_filters") or hasattr(self, "instance"):
            return MobileSessionQuerySet(self.model, using=self._db)
        raise RuntimeError("Mobile session queries require .for_clinic(clinic_id).")

    def for_clinic(self, clinic_id: UUID) -> MobileSessionQuerySet[_ModelT]:
        return MobileSessionQuerySet(self.model, using=self._db).for_clinic(clinic_id)


class InfrastructureMobileSessionManager(models.Manager[_ModelT]):
    """Acesso sem escopo: a autenticação por token acontece antes de saber a clínica."""

    def get_queryset(self) -> MobileSessionQuerySet[_ModelT]:
        return MobileSessionQuerySet(self.model, using=self._db)


class MobileSession(UUIDTimestampedModel):
    """Um aparelho do paciente, preso a uma pessoa e a uma clínica.

    O servidor decide a clínica e o perfil de paciente quando a sessão é criada. O
    app não consegue trocar nenhum dos dois por cabeçalho ou parâmetro.
    """

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="mobile_sessions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_sessions",
    )
    patient_profile = models.ForeignKey(
        "people.PatientProfile",
        on_delete=models.CASCADE,
        related_name="mobile_sessions",
    )
    device_label = models.CharField(max_length=MAX_DEVICE_LABEL_LENGTH)
    platform = models.CharField(
        max_length=16, choices=Platform.choices, default=Platform.OTHER
    )
    app_version = models.CharField(max_length=MAX_APP_VERSION_LENGTH, blank=True)
    network_hint = models.CharField(max_length=16, blank=True)

    access_digest = models.CharField(max_length=64, unique=True)
    access_expires_at = models.DateTimeField()
    refresh_digest = models.CharField(max_length=64, unique=True)
    # Último refresh substituído. Se alguém o apresentar de novo, houve vazamento.
    previous_refresh_digest = models.CharField(max_length=64, blank=True, db_index=True)
    refresh_expires_at = models.DateTimeField()
    absolute_expires_at = models.DateTimeField()

    last_used_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(
        max_length=24, choices=RevokeReason.choices, blank=True
    )

    objects = MobileSessionManager["MobileSession"]()
    infrastructure_objects = InfrastructureMobileSessionManager["MobileSession"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-last_used_at"]
        indexes = [
            models.Index(fields=["clinic", "user", "revoked_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_label} ({self.pk})"
