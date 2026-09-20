"""HTML privado com a mesma política das APIs; login continua público."""

from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .models import (
    AddictionProfile,
    CravingTrackingLog,
    DiagnosticCategory,
    TwelveStepsAnamnesis,
)
from .policies import domain_access
from .selectors import own_patient, visible_patients


@domain_access("clinical")
@require_GET
def dashboard_view(request):
    patients = visible_patients(actor=request.user, clinic=request.clinic)
    return render(
        request,
        "psychiatry/dashboard.html",
        {
            "page_title": "Painel clínico",
            "active_nav": "dashboard",
            "active_patients_count": patients.filter(status="ACTIVE").count(),
            "today_appointments_count": None,
            "telehealth_active_count": None,
            "bed_occupancy_percent": None,
            "occupied_beds": None,
            "total_beds": None,
            "adherence_rate": None,
        },
    )


@domain_access("clinical")
@require_GET
def anamnesis_view(request):
    return render(
        request,
        "psychiatry/anamnesis.html",
        {
            "active_nav": "anamnesis",
            "diagnostics": DiagnosticCategory.objects.order_by("cid11_code")[:100],
            "patients": visible_patients(
                actor=request.user, clinic=request.clinic
            ).order_by("pk")[:50],
        },
    )


@domain_access("clinical")
@require_GET
def patients_view(request):
    return render(
        request,
        "psychiatry/patients.html",
        {
            "active_nav": "patients",
            "patients": visible_patients(
                actor=request.user, clinic=request.clinic
            ).order_by("pk")[:50],
        },
    )


@domain_access("clinical")
@require_GET
def telepsychiatry_room_view(request):
    return render(
        request,
        "psychiatry/telepsychiatry_room.html",
        {
            "active_nav": "telepsychiatry",
            "room_id": None,
            "service_available": False,
        },
    )


@domain_access("clinical")
@require_GET
def crisis_protocol_view(request):
    return render(
        request,
        "psychiatry/crisis_protocol.html",
        {
            "active_nav": "crisis",
            "monitoring_active": False,
            "notification_delivered": False,
        },
    )


@domain_access("clinical")
@require_GET
def inpatient_beds_view(request):
    return render(request, "psychiatry/beds.html", {"active_nav": "beds", "beds": []})


@domain_access("patient")
@require_GET
def mobile_connected_view(request):
    patient = own_patient(actor=request.user, clinic=request.clinic)
    return render(
        request,
        "psychiatry/mobile_connected.html",
        {"patient": patient, "monitoring_active": False},
    )


@domain_access("b2c")
@require_GET
def mobile_b2c_view(request):
    return render(request, "psychiatry/mobile_b2c.html", {"monitoring_active": False})


@require_GET
def login_view(request):
    return redirect("account_login")


@domain_access("clinical")
@require_GET
def addiction_dashboard_view(request):
    patients = visible_patients(actor=request.user, clinic=request.clinic)
    profiles = AddictionProfile.objects.filter(patient__in=patients)
    return render(
        request,
        "psychiatry/addiction_dashboard.html",
        {
            "active_nav": "addiction",
            "profiles": profiles.select_related("patient").order_by("pk")[:15],
            "recent_cravings": CravingTrackingLog.objects.filter(
                patient__in=patients
            ).select_related("patient")[:6],
            "consolidated_anamneses": TwelveStepsAnamnesis.objects.filter(
                patient__in=patients, status="CONSOLIDATED"
            ).select_related("patient")[:8],
            "total_patients": profiles.count(),
            "avg_clean_days": None,
        },
    )


@domain_access("clinical")
@require_GET
def twelve_steps_anamnesis_view(request):
    return render(
        request,
        "psychiatry/twelve_steps_anamnesis.html",
        {
            "active_nav": "addiction",
            "patients": visible_patients(
                actor=request.user, clinic=request.clinic
            ).order_by("pk")[:50],
            "session_id": None,
        },
    )
