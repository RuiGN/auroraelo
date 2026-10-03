"""Persistência do concierge e do acompanhamento pós-alta (tudo isolado por clínica)."""

from __future__ import annotations

from typing import Any, NoReturn, TypeVar, cast
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q

from core.persistence import UUIDTimestampedModel

from .contracts import (
    ContactKind,
    ContactOutcome,
    ContactStatus,
    DischargeStatus,
    LogChannel,
    LogDirection,
    RequestKind,
    RequestStatus,
    ResponsibleRole,
)
from .fields import EncryptedTextField

_ModelT = TypeVar("_ModelT", bound=models.Model)


class ConciergeQuerySet(models.QuerySet[_ModelT]):
    """Consultas sempre restritas a uma clínica explícita."""

    def for_clinic(self, clinic_id: UUID) -> ConciergeQuerySet[_ModelT]:
        return self.filter(clinic_id=clinic_id)


class ConciergeTenantManager(models.Manager[_ModelT]):
    """Manager padrão: recusa consultas sem `.for_clinic(clinic_id)`."""

    def get_queryset(self) -> ConciergeQuerySet[_ModelT]:
        if hasattr(self, "core_filters") or hasattr(self, "instance"):
            return ConciergeQuerySet(self.model, using=self._db)
        raise RuntimeError("Concierge queries require .for_clinic(clinic_id).")

    def for_clinic(self, clinic_id: UUID) -> ConciergeQuerySet[_ModelT]:
        return ConciergeQuerySet(self.model, using=self._db).for_clinic(clinic_id)


class InfrastructureConciergeManager(models.Manager[_ModelT]):
    """Acesso sem escopo reservado a serviços internos e testes."""

    def get_queryset(self) -> ConciergeQuerySet[_ModelT]:
        return ConciergeQuerySet(self.model, using=self._db)


# Colunas de autoria. O Django as anula (ON DELETE SET NULL) quando o usuário é
# excluído, por exemplo no direito de apagamento. Isso não altera o conteúdo do
# registro, então é a única atualização em massa permitida.
_AUTHOR_COLUMNS = frozenset({"recorded_by", "recorded_by_id"})


class AppendOnlyQuerySet(ConciergeQuerySet[_ModelT]):
    """Leitura escopada; bloqueia qualquer alteração ou exclusão em massa."""

    def update(self, **kwargs: Any) -> int:
        if (
            kwargs
            and set(kwargs) <= _AUTHOR_COLUMNS
            and all(value is None for value in kwargs.values())
        ):
            return super().update(**kwargs)
        raise PermissionDenied("O registro do concierge é somente de acréscimo.")

    def delete(self) -> NoReturn:
        raise PermissionDenied("O registro do concierge não pode ser excluído.")

    def bulk_update(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise PermissionDenied("O registro do concierge é somente de acréscimo.")

    def update_or_create(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise PermissionDenied("O registro do concierge exige o serviço próprio.")


class AppendOnlyTenantManager(models.Manager[_ModelT]):
    def get_queryset(self) -> AppendOnlyQuerySet[_ModelT]:
        if hasattr(self, "core_filters") or hasattr(self, "instance"):
            return AppendOnlyQuerySet(self.model, using=self._db)
        raise RuntimeError("Concierge queries require .for_clinic(clinic_id).")

    def for_clinic(self, clinic_id: UUID) -> AppendOnlyQuerySet[_ModelT]:
        queryset: AppendOnlyQuerySet[_ModelT] = AppendOnlyQuerySet(
            self.model, using=self._db
        )
        return cast(AppendOnlyQuerySet[_ModelT], queryset.for_clinic(clinic_id))


class InfrastructureAppendOnlyManager(models.Manager[_ModelT]):
    def get_queryset(self) -> AppendOnlyQuerySet[_ModelT]:
        return AppendOnlyQuerySet(self.model, using=self._db)


# ── Régua de comunicação (por clínica) ──────────────────────────────────────


class CommunicationRule(UUIDTimestampedModel):
    """Régua de ligações e visitas após a alta. Cada alteração gera uma nova versão."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="communication_rules"
    )
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="communication_rules_created",
    )

    objects = ConciergeTenantManager["CommunicationRule"]()
    infrastructure_objects = InfrastructureConciergeManager["CommunicationRule"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-version", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("clinic",),
                condition=Q(is_active=True),
                name="unique_active_communication_rule_per_clinic",
            ),
            models.UniqueConstraint(
                fields=("clinic", "version"), name="unique_rule_version_per_clinic"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class CommunicationRuleStep(UUIDTimestampedModel):
    """Uma etapa da régua: tipo de contato e dias após a alta."""

    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="communication_rule_steps",
    )
    rule = models.ForeignKey(
        CommunicationRule, on_delete=models.CASCADE, related_name="steps"
    )
    kind = models.CharField(max_length=16, choices=ContactKind.choices)
    day_after_discharge = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(default=0)
    responsible_role = models.CharField(
        max_length=32,
        choices=ResponsibleRole.choices,
        default=ResponsibleRole.ADMINISTRATIVE_STAFF,
    )

    objects = ConciergeTenantManager["CommunicationRuleStep"]()
    infrastructure_objects = InfrastructureConciergeManager["CommunicationRuleStep"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["day_after_discharge", "order", "kind"]
        constraints = [
            models.UniqueConstraint(
                fields=("rule", "kind", "day_after_discharge"),
                name="unique_step_per_rule_kind_day",
            ),
            models.CheckConstraint(
                condition=Q(day_after_discharge__gte=1, day_after_discharge__lte=365),
                name="rule_step_day_between_1_and_365",
            ),
        ]


# ── Alta e contatos pós-alta ────────────────────────────────────────────────


class Discharge(UUIDTimestampedModel):
    """Alta do paciente; origem da agenda de contatos pós-alta."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="discharges"
    )
    patient_profile = models.ForeignKey(
        "people.PatientProfile",
        on_delete=models.CASCADE,
        related_name="discharges",
    )
    discharge_date = models.DateField()
    status = models.CharField(
        max_length=16, choices=DischargeStatus.choices, default=DischargeStatus.ACTIVE
    )
    rule = models.ForeignKey(
        CommunicationRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discharges",
    )
    # Cópia imutável das etapas usadas, para a agenda não mudar se a régua mudar.
    rule_snapshot = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discharges_registered",
    )
    canceled_at = models.DateTimeField(null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="discharges_canceled",
    )
    cancel_reason = models.CharField(max_length=255, blank=True)

    objects = ConciergeTenantManager["Discharge"]()
    infrastructure_objects = InfrastructureConciergeManager["Discharge"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-discharge_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "patient_profile"),
                condition=Q(status="active"),
                name="unique_active_discharge_per_patient",
            )
        ]
        indexes = [models.Index(fields=("clinic", "status", "discharge_date"))]


class AftercareContact(UUIDTimestampedModel):
    """Ligação ou visita prevista pela régua para uma alta."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="aftercare_contacts"
    )
    discharge = models.ForeignKey(
        Discharge, on_delete=models.CASCADE, related_name="contacts"
    )
    kind = models.CharField(max_length=16, choices=ContactKind.choices)
    day_after_discharge = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    original_due_date = models.DateField()
    reschedule_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=ContactStatus.choices, default=ContactStatus.SCHEDULED
    )
    responsible_role = models.CharField(
        max_length=32,
        choices=ResponsibleRole.choices,
        default=ResponsibleRole.ADMINISTRATIVE_STAFF,
    )
    outcome = models.CharField(
        max_length=24, choices=ContactOutcome.choices, blank=True, default=""
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="aftercare_contacts_completed",
    )
    notes = EncryptedTextField(blank=True, default="")

    objects = ConciergeTenantManager["AftercareContact"]()
    infrastructure_objects = InfrastructureConciergeManager["AftercareContact"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["due_date", "kind", "day_after_discharge"]
        constraints = [
            models.UniqueConstraint(
                fields=("discharge", "kind", "day_after_discharge"),
                name="unique_contact_per_discharge_kind_day",
            )
        ]
        indexes = [models.Index(fields=("clinic", "status", "due_date"))]


# ── Família ─────────────────────────────────────────────────────────────────


class FamilyContact(UUIDTimestampedModel):
    """Familiar ou pessoa de referência. Telefone e e-mail ficam cifrados."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="family_contacts"
    )
    patient_profile = models.ForeignKey(
        "people.PatientProfile",
        on_delete=models.CASCADE,
        related_name="family_contacts",
    )
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    phone = EncryptedTextField(blank=True, default="")
    email = EncryptedTextField(blank=True, default="")
    is_primary = models.BooleanField(default=False)
    # O contato com a família só ocorre com autorização do paciente.
    consent_to_contact = models.BooleanField(default=False)
    consent_recorded_at = models.DateTimeField(null=True, blank=True)
    consent_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="family_consents_recorded",
    )
    consent_note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ConciergeTenantManager["FamilyContact"]()
    infrastructure_objects = InfrastructureConciergeManager["FamilyContact"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-is_primary", "full_name"]
        indexes = [models.Index(fields=("clinic", "patient_profile", "is_active"))]

    @property
    def can_be_contacted(self) -> bool:
        return self.is_active and self.consent_to_contact


class ConciergeLog(UUIDTimestampedModel):
    """Registro de contato entre a clínica e a família. Somente de acréscimo."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="concierge_logs"
    )
    patient_profile = models.ForeignKey(
        "people.PatientProfile",
        on_delete=models.CASCADE,
        related_name="concierge_logs",
    )
    family_contact = models.ForeignKey(
        FamilyContact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )
    aftercare_contact = models.ForeignKey(
        AftercareContact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )
    family_request = models.ForeignKey(
        "concierge.FamilyRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
    )
    corrects = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="corrections",
    )
    channel = models.CharField(max_length=16, choices=LogChannel.choices)
    direction = models.CharField(
        max_length=16, choices=LogDirection.choices, default=LogDirection.OUTBOUND
    )
    occurred_at = models.DateTimeField()
    summary = EncryptedTextField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="concierge_logs_recorded",
    )

    objects = AppendOnlyTenantManager["ConciergeLog"]()
    infrastructure_objects = InfrastructureAppendOnlyManager["ConciergeLog"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=("clinic", "patient_profile", "occurred_at")),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise PermissionDenied("O registro do concierge é somente de acréscimo.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise PermissionDenied("O registro do concierge não pode ser excluído.")


class FamilyRequest(UUIDTimestampedModel):
    """Pedido do paciente à família, registrado e acompanhado pelo concierge."""

    clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.CASCADE, related_name="family_requests"
    )
    patient_profile = models.ForeignKey(
        "people.PatientProfile",
        on_delete=models.CASCADE,
        related_name="family_requests",
    )
    family_contact = models.ForeignKey(
        FamilyContact, on_delete=models.PROTECT, related_name="requests"
    )
    kind = models.CharField(max_length=16, choices=RequestKind.choices)
    description = EncryptedTextField()
    status = models.CharField(
        max_length=16, choices=RequestStatus.choices, default=RequestStatus.OPEN
    )
    requested_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="family_requests_recorded",
    )
    forwarded_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="family_requests_resolved",
    )
    resolution_note = models.CharField(max_length=500, blank=True)

    objects = ConciergeTenantManager["FamilyRequest"]()
    infrastructure_objects = InfrastructureConciergeManager["FamilyRequest"]()

    class Meta:
        base_manager_name = "infrastructure_objects"
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=("clinic", "status", "requested_at"))]


__all__ = [
    "AftercareContact",
    "AppendOnlyQuerySet",
    "CommunicationRule",
    "CommunicationRuleStep",
    "ConciergeLog",
    "ConciergeQuerySet",
    "ConciergeTenantManager",
    "Discharge",
    "FamilyContact",
    "FamilyRequest",
    "InfrastructureConciergeManager",
]
