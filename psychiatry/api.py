"""REST API Controller for Aurora Elo Health Systems.

Serves Web Clinic Dashboard, Connected Mobile App (App 1),
and Retail B2C Mobile App (App 2: Aurora Mind).
"""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import validation as v
from .models import (
    B2CCBTDiary,
    B2CMindLog,
    B2CSubscription,
    PrescriptionItem,
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
# 2. CONNECTED MOBILE APP APIS (App 1: Aurora Elo Clínica)
# ==============================================================================


@domain_access("patient")
@require_http_methods(["GET"])
def patient_mobile_summary(request):
    from .selectors import own_patient

    patient = own_patient(actor=request.user, clinic=request.clinic)
    limit, offset = v.pagination(request)
    medications = list(
        PrescriptionItem.objects.filter(
            prescription__patient=patient,
            prescription__is_active=True,
            prescription__issued_date__lte=timezone.localdate(),
            prescription__expires_date__gte=timezone.localdate(),
        )
        .order_by("pk")
        .values("id", "drug_name", "dosage", "posology")[offset : offset + limit]
    )
    return JsonResponse(
        {
            "success": True,
            "data": {
                "patient": {
                    "name": patient.full_name,
                    "record_number": patient.record_number,
                    "uuid": str(patient.uuid),
                },
                "medications": medications,
                "today_medications": medications,
                "next_teleconsultation": None,
                "monitoring_active": False,
            },
        }
    )


@domain_access("patient")
@require_http_methods(["POST"])
def log_medication_adherence(request):
    from .services import record_adherence

    data = v.payload(request, {"medication_id", "is_taken", "scheduled_time", "notes"})
    entry = record_adherence(actor=request.user, clinic=request.clinic, data=data)
    return JsonResponse(
        {
            "success": True,
            "persisted": True,
            "log_id": entry.pk,
            "medication_id": entry.item_id,
            "is_taken": entry.is_taken,
            "notification_delivered": False,
        }
    )


@domain_access("patient")
@require_http_methods(["POST"])
def trigger_patient_sos(request):
    from .services import NO_DELIVERY, record_sos

    data = v.payload(request, {"latitude", "longitude"})
    alert = record_sos(actor=request.user, clinic=request.clinic, data=data)
    return JsonResponse(
        {"success": True, "persisted": True, "alert_id": alert.pk, **NO_DELIVERY}
    )


# ==============================================================================
# 3. RETAIL B2C APP STORE APIS (App 2: Aurora Mind & Wellness)
# ==============================================================================


@domain_access("b2c")
@require_http_methods(["POST", "GET"])
def b2c_mood(request):
    if request.method == "POST":
        data = v.payload(
            request,
            {
                "mood",
                "anxiety_score",
                "energy_score",
                "sleep_hours",
                "tags",
                "gratitude",
            },
        )
        entry = B2CMindLog.objects.create(
            user=request.user,
            user_identifier=str(request.user.pk),
            mood=v.choice(data, "mood", B2CMindLog.MoodState.values),
            anxiety_score=v.integer(data, "anxiety_score", 0, 10),
            energy_score=v.integer(data, "energy_score", 1, 5),
            sleep_hours=v.number(data, "sleep_hours", 0, 24),
            emotions_tags=v.strings(data, "tags"),
            gratitude_note=v.text(data, "gratitude"),
        )
        return JsonResponse({"success": True, "persisted": True, "id": entry.pk})
    limit, offset = v.pagination(request)
    history = list(
        B2CMindLog.objects.filter(user=request.user)
        .order_by("-logged_at", "-pk")
        .values(
            "id",
            "logged_at",
            "mood",
            "anxiety_score",
            "energy_score",
            "sleep_hours",
            "emotions_tags",
            "gratitude_note",
        )[offset : offset + limit]
    )
    return JsonResponse(
        {
            "success": True,
            "history": history,
            "count": len(history),
            "limit": limit,
            "offset": offset,
        }
    )


@domain_access("b2c")
@require_http_methods(["POST", "GET"])
def b2c_cbt_diary(request):
    if request.method == "POST":
        data = v.payload(
            request, {"trigger", "thought", "distortion", "rational", "before", "after"}
        )
        entry = B2CCBTDiary.objects.create(
            user=request.user,
            user_identifier=str(request.user.pk),
            trigger_situation=v.text(data, "trigger", required=True),
            automatic_thought=v.text(data, "thought", required=True),
            cognitive_distortion=v.text(data, "distortion", maximum=150),
            rational_response=v.text(data, "rational"),
            emotion_before_percent=v.integer(data, "before", 0, 100),
            emotion_after_percent=v.integer(data, "after", 0, 100),
        )
        return JsonResponse({"success": True, "persisted": True, "id": entry.pk})
    limit, offset = v.pagination(request)
    entries = list(
        B2CCBTDiary.objects.filter(user=request.user)
        .order_by("-created_at", "-pk")
        .values(
            "id",
            "created_at",
            "trigger_situation",
            "automatic_thought",
            "cognitive_distortion",
            "rational_response",
            "emotion_before_percent",
            "emotion_after_percent",
        )[offset : offset + limit]
    )
    return JsonResponse(
        {
            "success": True,
            "entries": entries,
            "count": len(entries),
            "limit": limit,
            "offset": offset,
        }
    )


@require_http_methods(["GET"])
def b2c_breathing_exercises(request):
    """Clinical breathing protocols for panic/anxiety relief."""
    protocols = [
        {
            "id": "box-breathing",
            "title": "Respiração Guiada 4-4-4-4 (Box Breathing)",
            "category": "Alívio Rápido de Ansiedade & Taquicardia",
            "description": (
                "Utilizada por forças de elite e recomendada na TCC "
                "para equilibrar o sistema nervoso autônomo parassimpático."
            ),
            "cycles": [
                {"phase": "Inspirar", "seconds": 4},
                {"phase": "Segurar com ar", "seconds": 4},
                {"phase": "Expirar", "seconds": 4},
                {"phase": "Segurar sem ar", "seconds": 4},
            ],
            "recommended_minutes": 5,
        },
        {
            "id": "4-7-8-sleep",
            "title": "Técnica 4-7-8 para Sono & Relaxamento Profundo",
            "category": "Indução Natural do Sono",
            "description": (
                "Desacelera a frequência cardíaca e reduz a ruminação noturna."
            ),
            "cycles": [
                {"phase": "Inspirar pelo nariz", "seconds": 4},
                {"phase": "Reter o ar", "seconds": 7},
                {"phase": "Expirar lentamente pela boca", "seconds": 8},
            ],
            "recommended_minutes": 7,
        },
    ]
    return JsonResponse(
        {
            "success": True,
            "data": {
                "protocols": protocols,
                "exercises": protocols,
            },
            "exercises": protocols,
        }
    )


@domain_access("b2c")
@require_http_methods(["GET", "POST"])
def b2c_subscription_status(request):
    if request.method == "POST":
        data = v.payload(request, {"plan", "platform"})
        v.choice(data, "plan", B2CSubscription.PlanTier.values)
        if "platform" in data:
            v.choice(data, "platform", B2CSubscription.StorePlatform.values)
        return JsonResponse(
            {
                "success": False,
                "error": "Verificação de compra indisponível.",
                "is_active": False,
            },
            status=503,
        )
    v.pagination(request)
    sub = B2CSubscription.objects.filter(user=request.user).order_by("-pk").first()
    active = bool(sub and sub.is_active and sub.valid_until > timezone.now())
    return JsonResponse(
        {"success": True, "plan": sub.plan if active else "FREE", "is_active": active}
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


@domain_access("patient")
@require_http_methods(["POST"])
def api_record_craving(request):
    from .services import NO_DELIVERY, record_craving

    data = v.payload(
        request,
        {
            "intensity",
            "target_urge",
            "trigger",
            "halt_factors",
            "coping",
            "urge_surfed_successfully",
        },
    )
    entry = record_craving(actor=request.user, clinic=request.clinic, data=data)
    return JsonResponse(
        {"success": True, "persisted": True, "log_id": entry.pk, **NO_DELIVERY}
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
