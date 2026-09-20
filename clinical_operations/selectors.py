"""Leituras puras e limitadas, sem auditoria mutável em GET."""

from core.selectors import Selector as Selector
from people.selectors import patient_visible_to

from .models import (
    ClinicalRecord,
    Encounter,
    Enrollment,
    Product,
    StockLot,
    StockMovement,
    TherapySession,
)
from .policies import require_capability, require_encounter_access
from .services import _object


def list_resources(*, clinic_id, actor, resource, offset=0):
    definitions = {
        "products": (Product, "pharmacy.read", ("id", "name", "sku")),
        "lots": (
            StockLot,
            "pharmacy.read",
            ("id", "product_id", "code", "expires_on", "balance"),
        ),
        "movements": (
            StockMovement,
            "pharmacy.read",
            ("id", "lot_id", "quantity", "direction", "created_at"),
        ),
        "encounters": (
            Encounter,
            "encounter.manage",
            ("id", "patient_id", "starts_at", "status"),
        ),
        "sessions": (
            TherapySession,
            "session.manage",
            ("id", "kind", "modality", "capacity", "starts_at", "ends_at"),
        ),
        "enrollments": (
            Enrollment,
            "session.manage",
            ("id", "session_id", "patient_id", "status"),
        ),
    }
    model, capability, fields = definitions[resource]
    clinic = require_capability(clinic_id=clinic_id, actor=actor, capability=capability)
    query = model.objects.for_clinic(clinic_id)
    if resource in {"encounters", "sessions"}:
        query = query.filter(professional_id=actor.pk)
    elif resource == "enrollments":
        query = query.filter(
            session__professional_id=actor.pk, session__clinic_id=clinic_id
        )
    if resource in {"encounters", "enrollments"}:
        # O histórico não concede acesso após o término do vínculo. Filtrar
        # identidades autorizadas antes de paginar, usando a política pública.
        patient_ids = query.order_by().values_list("patient_id", flat=True).distinct()
        visible_ids = [
            patient_id
            for patient_id in patient_ids
            if patient_visible_to(
                actor=actor,
                clinic=clinic,
                patient_id=patient_id,
                action="patient.clinical.read",
            )
            is not None
        ]
        query = query.filter(patient_id__in=visible_ids)
    return list(
        query.order_by("created_at", "pk").values(*fields)[offset : offset + 100]
    )


def read_records(*, clinic_id, actor, encounter_id, offset=0):
    require_capability(clinic_id=clinic_id, actor=actor, capability="record.read")
    encounter = _object(Encounter, clinic_id, encounter_id)
    require_encounter_access(
        clinic_id=clinic_id,
        actor=actor,
        encounter=encounter,
        capability="record.read",
        consent=True,
    )
    return list(
        ClinicalRecord.objects.for_clinic(clinic_id)
        .filter(encounter=encounter)
        .order_by("created_at", "pk")[offset : offset + 100]
    )
