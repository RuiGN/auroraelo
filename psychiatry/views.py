"""Web views for Aurora Elo Psychiatric Clinic & Mobile Ecosystem."""

from django.shortcuts import render
from django.utils import timezone
from .models import (
    DiagnosticCategory,
    PsychiatricPatientProfile,
    PsychiatricEvaluation,
    InpatientBed,
    PsychopharmacologyPrescription,
    PsychiatricCrisisAlert,
)


def dashboard_view(request):
    """Main Psychiatric Clinic Management Portal."""
    context = {
        "page_title": "Painel Clínico - Aurora Elo Psiquiatria",
        "active_nav": "dashboard",
        "active_patients_count": 1284,
        "today_appointments_count": 38,
        "telehealth_active_count": 16,
        "bed_occupancy_percent": 75,
        "occupied_beds": 12,
        "total_beds": 16,
        "adherence_rate": 92.6,
        "doctor_name": "Dr. Marcelo Arantes",
        "doctor_crm": "CRM/SP 148.920",
    }
    return render(request, "psychiatry/dashboard.html", context)


def anamnesis_view(request):
    """Psychiatric Intake, DSM-5 / CID-11 Anamnesis & MSE."""
    diagnostics = DiagnosticCategory.objects.all()
    context = {
        "page_title": "Admissão & Anamnese Psiquiátrica - Aurora Elo",
        "active_nav": "anamnesis",
        "diagnostics": diagnostics,
        "now": timezone.now(),
    }
    return render(request, "psychiatry/anamnesis.html", context)


def patients_view(request):
    """Patient registry with psychiatric risk stratification and filters."""
    context = {
        "page_title": "Pacientes em Acompanhamento - Aurora Elo",
        "active_nav": "patients",
    }
    return render(request, "psychiatry/patients.html", context)


def telepsychiatry_room_view(request):
    """Encrypted Telepsychiatry Room."""
    context = {
        "page_title": "Sala Virtual de Telepsiquiatria HD - Aurora Elo",
        "active_nav": "telepsychiatry",
        "room_id": "elo-room-0842-hd",
        "patient_name": "Mariana Silveira Fagundes",
        "doctor_name": "Dr. Marcelo Arantes",
        "doctor_crm": "CRM/SP 148.920",
    }
    return render(request, "psychiatry/telepsychiatry_room.html", context)


def crisis_protocol_view(request):
    """Psychiatric Emergency & Crisis Response Protocol (SOS Elo)."""
    context = {
        "page_title": "Protocolo de Crise Psiquiátrica 24h - Aurora Elo",
        "active_nav": "crisis",
    }
    return render(request, "psychiatry/crisis_protocol.html", context)


def inpatient_beds_view(request):
    """Inpatient Ward and Psychiatric Bed Management."""
    context = {
        "page_title": "Gestão de Leitos & Internação - Aurora Elo",
        "active_nav": "beds",
    }
    return render(request, "psychiatry/beds.html", context)


def mobile_connected_view(request):
    """Interactive preview for Connected Clinic Mobile App (App 1)."""
    return render(request, "psychiatry/mobile_connected.html")


def mobile_b2c_view(request):
    """Interactive preview for Retail B2C Mobile App (App 2: Aurora Mind)."""
    return render(request, "psychiatry/mobile_b2c.html")


def login_view(request):
    """Clinical authentication portal with multi-role selector."""
    return render(request, "psychiatry/login.html")


def addiction_dashboard_view(request):
    """Adictologia: Jogos de Azar, Álcool e Dependência Química Hub."""
    from .models import AddictionProfile, TwelveStepsAnamnesis, CravingTrackingLog

    profiles = AddictionProfile.objects.select_related("patient").all()[:15]
    recent_cravings = CravingTrackingLog.objects.select_related("patient").all()[:6]
    consolidated_anamneses = TwelveStepsAnamnesis.objects.select_related("patient").all()[:8]

    context = {
        "page_title": "Adictologia & 12 Passos - Aurora Elo",
        "active_nav": "addiction",
        "profiles": profiles,
        "recent_cravings": recent_cravings,
        "consolidated_anamneses": consolidated_anamneses,
        "total_patients": profiles.count() or 48,
        "avg_clean_days": 78,
    }
    return render(request, "psychiatry/addiction_dashboard.html", context)


def twelve_steps_anamnesis_view(request):
    """Interactive 12-Step Anamnesis with Redis live draft saving and Celery AI analysis."""
    from .models import PsychiatricPatientProfile
    import uuid

    patients = PsychiatricPatientProfile.objects.all()[:20]
    session_id = f"sess-{uuid.uuid4().hex[:8]}"

    context = {
        "page_title": "Anamnese Psiquiátrica dos 12 Passos - Aurora Elo",
        "active_nav": "addiction",
        "patients": patients,
        "session_id": session_id,
    }
    return render(request, "psychiatry/twelve_steps_anamnesis.html", context)

