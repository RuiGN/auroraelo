"""Persistência tenant-scoped; mutações passam pelos serviços autorizados."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.persistence import UUIDTimestampedModel


class TenantQuerySet(models.QuerySet):
    def for_clinic(self, clinic_id):
        return self.filter(clinic_id=clinic_id)


class TenantManager(models.Manager):
    def get_queryset(self):
        raise RuntimeError("Use .for_clinic(clinic_id).")

    def for_clinic(self, clinic_id):
        return TenantQuerySet(self.model, using=self._db).for_clinic(clinic_id)


class TenantModel(UUIDTimestampedModel):
    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.PROTECT)
    objects = TenantManager()
    infrastructure_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "infrastructure_objects"
        default_manager_name = "objects"

    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if (
                isinstance(field, models.ForeignKey)
                and field.related_model._meta.app_label == "clinical_operations"
                and not field.related_model.objects.for_clinic(self.clinic_id)
                .filter(pk=getattr(self, field.attname))
                .exists()
            ):
                raise ValidationError("Referência de outra clínica.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class OperationGrant(TenantModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operation_grants",
    )
    capability = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authorized_operation_grants",
    )

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "user", "capability"), name="operations_unique_grant"
            )
        ]


class ImmutableQuerySet(TenantQuerySet):
    def update(self, **kwargs):
        raise ValidationError("Registro append-only.")

    def delete(self):
        raise ValidationError("Registro append-only.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Registro append-only.")


class ImmutableManager(TenantManager):
    def for_clinic(self, clinic_id):
        return ImmutableQuerySet(self.model, using=self._db).for_clinic(clinic_id)


class ImmutableInfrastructureManager(models.Manager.from_queryset(ImmutableQuerySet)):
    pass


class ImmutableModel(TenantModel):
    objects = ImmutableManager()
    infrastructure_objects = ImmutableInfrastructureManager()

    class Meta(TenantModel.Meta):
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Registro append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registro append-only.")


class Product(TenantModel):
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=48)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "sku"), name="operations_unique_sku"
            )
        ]


class Encounter(TenantModel):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operation_encounters",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="professional_operation_encounters",
    )
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="agendado")

    class Meta(TenantModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("agendado", "em_atendimento", "concluido", "cancelado")
                ),
                name="operations_encounter_status",
            )
        ]


class ClinicalRecord(ImmutableModel):
    encounter = models.ForeignKey(Encounter, on_delete=models.PROTECT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField(max_length=8000)


class TherapySession(TenantModel):
    professional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12)
    modality = models.CharField(max_length=16)
    capacity = models.PositiveSmallIntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    class Meta(TenantModel.Meta):
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=("individual", "grupo")),
                name="operations_session_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    modality__in=("psicoterapia", "exercicio", "yoga", "arteterapia")
                ),
                name="operations_session_modality",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1, capacity__lte=100),
                name="operations_session_capacity",
            ),
            models.CheckConstraint(
                condition=(models.Q(kind="grupo") | models.Q(capacity=1)),
                name="operations_individual_capacity",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="operations_session_times",
            ),
        ]


class Enrollment(TenantModel):
    session = models.ForeignKey(TherapySession, on_delete=models.PROTECT)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, default="agendado")

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "session", "patient"),
                name="operations_unique_enrollment",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("agendado", "presente", "ausente")),
                name="operations_attendance_status",
            ),
        ]


class StockLot(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    code = models.CharField(max_length=64)
    expires_on = models.DateField()
    balance = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "product", "code"), name="operations_unique_lot"
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name="operations_balance_nonnegative",
            ),
        ]


class StockMovement(ImmutableModel):
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="patient_stock_movements",
    )
    quantity = models.PositiveIntegerField()
    direction = models.CharField(
        max_length=3, choices=(("in", "Entrada"), ("out", "Saída"))
    )
    key = models.CharField(max_length=80)

    class Meta(ImmutableModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("clinic", "key"), name="operations_movement_idempotency"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="operations_quantity_positive"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(direction="in", patient__isnull=True)
                    | models.Q(direction="out", patient__isnull=False)
                ),
                name="operations_movement_direction_patient",
            ),
        ]
