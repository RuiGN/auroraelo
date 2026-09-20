"""Mutações autorizadas, sem delivery de notificações ou chamadas de IA."""

from decimal import Decimal

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from clinics.services import lock_clinic_for_update

from . import validation as v
from .models import (
    CravingTrackingLog,
    MedicationAdherenceLog,
    PrescriptionItem,
    PsychiatricCrisisAlert,
    PsychiatricEvaluation,
    PsychiatricPatientProfile,
    TwelveStepsAnamnesis,
)
from .policies import require_domain_access
from .selectors import clinical_patient, own_patient, visible_patients

STEP_FIELDS = (
    "step1_powerlessness",
    "step2_restoration_hope",
    "step3_surrender_care",
    "step4_moral_inventory",
    "step5_confession_admission",
    "step6_readiness",
    "step7_humility",
    "step8_amends_list",
    "step9_reparations_plan",
    "step10_daily_inventory",
    "step11_mindfulness_prayer",
    "step12_service_purpose",
)


def _lock_domain(*, actor, clinic, mode="clinical"):
    require_domain_access(actor=actor, clinic=clinic, mode=mode)
    lock_clinic_for_update(clinic_id=clinic.pk)
    require_domain_access(actor=actor, clinic=clinic, mode=mode)


def authorized_draft(*, actor, clinic, session_id, lock=False):
    if lock:
        _lock_domain(actor=actor, clinic=clinic)
    patients = visible_patients(actor=actor, clinic=clinic)
    query = TwelveStepsAnamnesis.objects.filter(
        patient__in=patients,
        author=actor,
        uuid=session_id,
    )
    if lock:
        query = query.select_for_update()
    entry = query.first()
    if entry is None:
        raise Http404
    if lock:
        # Revalidar também depois da espera pelo recurso, não só pela clínica.
        clinical_patient(actor=actor, clinic=clinic, patient_uuid=entry.patient.uuid)
    return entry


@transaction.atomic
def save_step(*, actor, clinic, data):
    _lock_domain(actor=actor, clinic=clinic)
    patient = clinical_patient(
        actor=actor, clinic=clinic, patient_uuid=v.identifier(data, "patient_id")
    )
    step = v.integer(data, "step_number", 1, 12)
    answer_data = data.get("step_data")
    if not isinstance(answer_data, dict) or set(answer_data) != {"answer"}:
        v.invalid()
    answer = v.text(answer_data, "answer", required=True)
    if "session_id" in data:
        entry = authorized_draft(
            actor=actor,
            clinic=clinic,
            session_id=v.identifier(data, "session_id"),
            lock=True,
        )
        if entry.patient_id != patient.pk:
            raise Http404
        if entry.status != TwelveStepsAnamnesis.Status.DRAFT:
            v.invalid()
    else:
        entry = TwelveStepsAnamnesis(
            patient=patient, author=actor, status="DRAFT", relapse_risk_index=None
        )
    entry.draft_steps[f"step_{step}"] = {"answer": answer}
    entry.completed_steps_count = len(entry.draft_steps)
    entry.save()
    return entry


@transaction.atomic
def consolidate_steps(*, actor, clinic, session_id):
    entry = authorized_draft(
        actor=actor, clinic=clinic, session_id=session_id, lock=True
    )
    if entry.status != TwelveStepsAnamnesis.Status.DRAFT or not entry.draft_steps:
        v.invalid()
    for index, field in enumerate(STEP_FIELDS, start=1):
        setattr(
            entry, field, entry.draft_steps.get(f"step_{index}", {}).get("answer", "")
        )
    entry.status = TwelveStepsAnamnesis.Status.IN_PROGRESS
    entry.save()
    return entry


NO_DELIVERY = {
    "notification_delivered": False,
    "monitoring_active": False,
    "protocol_active": False,
    "urgent_intervention_dispatched": False,
    "instructions": (
        "Registro salvo. Ninguém foi notificado. Este "
        "aplicativo não oferece monitoramento nem atendimento de emergência."
    ),
}


@transaction.atomic
def record_adherence(*, actor, clinic, data):
    _lock_domain(actor=actor, clinic=clinic, mode="patient")
    patient = own_patient(actor=actor, clinic=clinic)
    item_id = v.integer(data, "medication_id", 1, 2147483647)
    taken = v.boolean(data, "is_taken")
    notes = v.text(data, "notes", maximum=255)
    scheduled = v.text(data, "scheduled_time", maximum=40, required=True)
    try:
        scheduled = parse_datetime(scheduled)
    except ValueError:
        v.invalid()
    if scheduled is None or timezone.is_naive(scheduled):
        v.invalid()
    item = PrescriptionItem.objects.filter(
        pk=item_id,
        prescription__patient=patient,
        prescription__is_active=True,
        prescription__issued_date__lte=timezone.localdate(),
        prescription__expires_date__gte=timezone.localdate(),
    ).first()
    if item is None:
        raise Http404
    return MedicationAdherenceLog.objects.create(
        patient=patient,
        item=item,
        scheduled_time=scheduled,
        taken_at=timezone.now() if taken else None,
        is_taken=taken,
        patient_notes=notes,
    )


@transaction.atomic
def record_sos(*, actor, clinic, data):
    _lock_domain(actor=actor, clinic=clinic, mode="patient")
    patient = own_patient(actor=actor, clinic=clinic)
    if ("latitude" in data) != ("longitude" in data):
        v.invalid()
    coords = {}
    for key, bound in (("latitude", 90), ("longitude", 180)):
        if key in data:
            coords[key] = Decimal(str(v.number(data, key, -bound, bound))).quantize(
                Decimal("0.000001")
            )
    return PsychiatricCrisisAlert.objects.create(
        patient=patient, status="OPEN", **coords
    )


@transaction.atomic
def record_craving(*, actor, clinic, data):
    _lock_domain(actor=actor, clinic=clinic, mode="patient")
    patient = own_patient(actor=actor, clinic=clinic)
    return CravingTrackingLog.objects.create(
        patient=patient,
        craving_intensity=v.integer(data, "intensity", 0, 10),
        target_urge=v.text(data, "target_urge", maximum=80, required=True),
        trigger_detail=v.text(data, "trigger"),
        halt_factors=v.strings(
            data, "halt_factors", {"HUNGRY", "ANGRY", "LONELY", "TIRED"}
        ),
        coping_technique=v.text(data, "coping", maximum=150),
        urge_surfed_successfully=v.boolean(data, "urge_surfed_successfully"),
    )


@transaction.atomic
def record_evaluation(*, actor, clinic, data):
    _lock_domain(actor=actor, clinic=clinic)
    patient = clinical_patient(
        actor=actor, clinic=clinic, patient_uuid=v.identifier(data, "patient_id")
    )
    return PsychiatricEvaluation.objects.create(
        patient=patient,
        author=actor,
        doctor_name=actor.get_full_name(),
        doctor_crm="",
        chief_complaint=v.text(data, "chief_complaint", required=True),
        hda=v.text(data, "hda", required=True),
        anxiety_analog_scale=v.integer(data, "anxiety_scale", 0, 10),
        suicide_risk_stratification=v.choice(
            data, "risk_level", PsychiatricPatientProfile.RiskLevel.values
        ),
        diagnostic_impression=v.text(data, "diagnostic_impression", required=True),
        therapeutic_plan=v.text(data, "therapeutic_plan", required=True),
        **{
            field: ""
            for field in (
                "mse_appearance_attitude",
                "mse_psychomotor",
                "mse_mood_affect",
                "mse_speech",
                "mse_thought_process",
                "mse_thought_content",
                "mse_perception",
                "mse_cognition",
                "mse_insight",
                "protective_factors",
            )
        },
    )
