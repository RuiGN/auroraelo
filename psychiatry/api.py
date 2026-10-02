"""REST API controller for the clinic web portal (team only).

Patients use only the post-discharge mobile app, served by ``/api/v1/mobile/``.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from . import validation as v
from .models import (
    PsychiatricCrisisAlert,
    PsychiatricPatientProfile,
    TelepsychiatryRoom,
)
from .policies import domain_access

# ==============================================================================
# 1. CLINIC WEB PORTAL APIS
# ==============================================================================


@domain_access("clinical")
@require_http_methods(["GET"])
def clinic_dashboard_kpis(request):
    from .selectors import visible_patients

    patients = visible_patients(actor=request.user, clinic=request.clinic)
    return JsonResponse(
        {
            "success": True,
            "data": {
                "active_patients": patients.filter(status="ACTIVE").count(),
                "today_appointments": None,
                "telehealth_active": TelepsychiatryRoom.objects.filter(
                    patient__in=patients, status="IN_PROGRESS"
                ).count(),
                "total_beds": None,
                "occupied_beds": None,
                "bed_occupancy_percent": None,
                "medication_adherence_percent": None,
                "active_crisis_alerts": PsychiatricCrisisAlert.objects.filter(
                    patient__in=patients, status="OPEN"
                ).count(),
            },
        }
    )


@domain_access("clinical")
@require_http_methods(["GET"])
def list_patients(request):
    from django.db.models import Q

    from .selectors import visible_patients

    limit, offset = v.pagination(request, extra={"q", "status", "risk"})
    patients = visible_patients(actor=request.user, clinic=request.clinic)
    query = v.text(request.GET, "q", maximum=100)
    if query:
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(record_number__icontains=query)
        )
    for key, field, choices in (
        ("status", "status", PsychiatricPatientProfile.TreatmentStatus.values),
        ("risk", "risk_level", PsychiatricPatientProfile.RiskLevel.values),
    ):
        if key in request.GET and request.GET[key] != "all":
            patients = patients.filter(**{field: v.choice(request.GET, key, choices)})
    results = [
        {
            "uuid": str(p.uuid),
            "name": p.full_name,
            "record_number": p.record_number,
            "status": p.status,
            "risk_level": p.risk_level,
        }
        for p in patients.order_by("pk")[offset : offset + limit]
    ]
    return JsonResponse(
        {
            "success": True,
            "count": len(results),
            "patients": results,
            "limit": limit,
            "offset": offset,
        }
    )


@domain_access("clinical")
@require_http_methods(["POST"])
def save_anamnesis(request):
    from .services import record_evaluation

    data = v.payload(
        request,
        {
            "patient_id",
            "chief_complaint",
            "hda",
            "anxiety_scale",
            "risk_level",
            "diagnostic_impression",
            "therapeutic_plan",
        },
    )
    evaluation = record_evaluation(actor=request.user, clinic=request.clinic, data=data)
    return JsonResponse(
        {"success": True, "persisted": True, "evaluation_id": evaluation.pk}
    )


# ==============================================================================
# 4. ADDICTOLOGY, GAMBLING & 12 STEPS REST APIS (REDIS & CELERY INTEGRATED)
# ==============================================================================


@domain_access("clinical")
@require_http_methods(["POST"])
def api_save_12steps_step(request):
    from .services import save_step

    data = v.payload(request, {"session_id", "patient_id", "step_number", "step_data"})
    entry = save_step(actor=request.user, clinic=request.clinic, data=data)
    return JsonResponse(
        {
            "success": True,
            "persisted": True,
            "session_id": str(entry.uuid),
            "saved_step": data["step_number"],
        }
    )


@domain_access("clinical")
@require_http_methods(["GET"])
def api_get_12steps_draft(request):
    from .services import authorized_draft

    v.pagination(request, extra={"session_id"})
    entry = authorized_draft(
        actor=request.user,
        clinic=request.clinic,
        session_id=v.identifier(request.GET, "session_id"),
    )
    return JsonResponse(
        {
            "success": True,
            "has_draft": entry.status == "DRAFT",
            "draft": {"session_id": str(entry.uuid), "steps": entry.draft_steps},
        }
    )


@domain_access("clinical")
@require_http_methods(["POST"])
def api_consolidate_12steps(request):
    from .services import consolidate_steps

    data = v.payload(request, {"session_id"})
    entry = consolidate_steps(
        actor=request.user,
        clinic=request.clinic,
        session_id=v.identifier(data, "session_id"),
    )
    return JsonResponse(
        {
            "success": True,
            "persisted": True,
            "ai_processed": False,
            "status": entry.status,
            "evaluation_id": entry.pk,
        }
    )


@domain_access("clinical")
@require_http_methods(["GET"])
def api_addiction_dashboard_kpis(request):
    from .models import AddictionProfile, CravingTrackingLog
    from .selectors import visible_patients

    v.pagination(request)
    patients = visible_patients(actor=request.user, clinic=request.clinic)
    profiles = AddictionProfile.objects.filter(patient__in=patients)
    return JsonResponse(
        {
            "success": True,
            "data": {
                "total_recovery_patients": profiles.count(),
                "gambling_disorder_patients": profiles.filter(
                    category="GAMBLING"
                ).count(),
                "alcohol_dependency_patients": profiles.filter(
                    category="ALCOHOL"
                ).count(),
                "chemical_dependency_patients": profiles.filter(
                    category="CHEMICAL"
                ).count(),
                "average_clean_days": None,
                "total_gambling_debt_managed": None,
                "active_craving_alerts": CravingTrackingLog.objects.filter(
                    patient__in=patients, craving_intensity__gte=7
                ).count(),
                "monitoring_active": False,
            },
        }
    )
