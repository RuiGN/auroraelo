"""Cenário sintético compartilhado pelos testes das telas de equipe de ``routines``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Any
from uuid import uuid4

from django.test import Client
from django.utils import timezone

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from people import services as people_services
from people.models import PatientProfile
from routines import care_plan_services
from routines import services as habit_services
from routines.medication_services import register_prescribed_medication
from routines.models import (
    CarePlan,
    Habit,
    HabitFrequency,
    PrescribedMedication,
    TimeOfDayWindow,
)
from tests.aftercare_support import Stage, build_stage, make_patient
from tests.factories import ClinicMembershipFactory, UserFactory


@dataclass
class World:
    """Clínica sintética: admin, terapeutas e dois pacientes (um sem vínculo)."""

    stage: Stage
    patient: PatientProfile
    other_patient: PatientProfile
    linked: User  # terapeuta vinculado só a ``patient``
    second_linked: User  # outro terapeuta, também vinculado a ``patient``
    unlinked: User  # terapeuta sem nenhum vínculo

    @property
    def clinic(self) -> Clinic:
        return self.stage.clinic

    @property
    def admin(self) -> User:
        return self.stage.admin


def _therapist(clinic: Clinic) -> User:
    user = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=user, role=ClinicMembership.Role.THERAPIST
    )
    return user


def link(
    world_clinic: Clinic, admin: User, therapist: User, patient: PatientProfile
) -> None:
    people_services.create_patient_care_relationship(
        clinic_id=world_clinic.pk,
        actor=admin,
        therapist_id=therapist.pk,
        patient_profile_id=patient.pk,
        function="Terapeuta responsável",
        valid_from=timezone.localdate() - timedelta(days=1),
        valid_until=None,
        request_id=uuid4(),
    )


def build_world() -> World:
    stage = build_stage()
    patient = make_patient(stage.clinic, stage.admin, name="Ana Souza")
    other_patient = make_patient(stage.clinic, stage.admin, name="Bia Lima")
    linked = stage.therapist
    second = _therapist(stage.clinic)
    unlinked = _therapist(stage.clinic)
    link(stage.clinic, stage.admin, linked, patient)
    link(stage.clinic, stage.admin, second, patient)
    return World(stage, patient, other_patient, linked, second, unlinked)


def login(clinic: Clinic, user: User) -> Client:
    client = Client()
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return client


def today() -> date:
    return timezone.localdate()


# ── Dados de formulário ─────────────────────────────────────────────────────


def medication_form(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "medication_name": "Sertralina",
        "presentation": "comprimido",
        "prescribed_dose": "50 mg",
        "route": "oral",
        "schedule_times": "8:00, 20:00",
        "start_date": today().isoformat(),
        "is_continuous": "on",
        "end_date": "",
        "prescriber_name": "Dra. Helena Prado",
        "prescriber_registration": "CRM-PE 12345",
        "prescription_date": today().isoformat(),
        "instructions": "Tomar após as refeições.",
    }
    data.update(over)
    return data


def plan_form(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "title": "Plano de retorno gradual",
        "objective": "Retomar a rotina com apoio da equipe.",
        "clinical_rationale": "Raciocínio clínico interno do caso.",
        "contraindications": "Evitar esforço intenso.",
        "valid_from": today().isoformat(),
        "valid_until": "",
        "form-TOTAL_FORMS": "4",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "12",
        "form-0-description": "Caminhada leve",
        "form-0-target_frequency": "Diária",
        "form-0-guidance": "Vinte minutos ao ar livre.",
        "form-0-is_mandatory": "on",
        "form-1-description": "Anotar como foi o dia",
        "form-1-target_frequency": "3 vezes por semana",
        "form-1-guidance": "",
    }
    data.update(over)
    return data


def habit_form(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "title": "Beber água",
        "description": "Um copo ao acordar.",
        "frequency": HabitFrequency.DAILY.value,
        "time_window": TimeOfDayWindow.MORNING.value,
        "target_time": "",
        "target_duration_minutes": "",
    }
    data.update(over)
    return data


# ── Objetos prontos (pelos serviços de domínio) ─────────────────────────────


def make_medication(
    world: World, patient: PatientProfile | None = None, **over: Any
) -> PrescribedMedication:
    values: dict[str, Any] = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": (patient or world.patient).pk,
        "medication_name": "Sertralina",
        "presentation": "comprimido",
        "prescribed_dose": "50 mg",
        "schedule_times": ["08:00", "20:00"],
        "start_date": today() - timedelta(days=5),
        "is_continuous": True,
        "prescriber_name": "Dra. Helena Prado",
        "prescriber_registration": "CRM-PE 12345",
        "prescription_date": today() - timedelta(days=5),
        "instructions": "Tomar após as refeições.",
    }
    values.update(over)
    return register_prescribed_medication(**values)


def make_plan(
    world: World,
    author: User | None = None,
    patient: PatientProfile | None = None,
    *,
    status: str = "draft",
) -> CarePlan:
    """Proposes a plan and moves it to ``status`` through the domain services."""
    author = author or world.admin
    plan = care_plan_services.propose_care_plan(
        clinic_id=world.clinic.pk,
        patient_profile_id=(patient or world.patient).pk,
        professional_user=author,
        title="Plano de retorno gradual",
        objective="Retomar a rotina com apoio da equipe.",
        clinical_rationale="Raciocínio clínico interno do caso.",
        contraindications="Evitar esforço intenso.",
        actions_data=[
            {
                "description": "Caminhada leve",
                "frequency": "Diária",
                "is_mandatory": True,
            }
        ],
    )
    pid = plan.patient_profile_id
    common: dict[str, Any] = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": pid,
        "care_plan_id": plan.pk,
        "professional_user": author,
    }
    if status in {"pending_signature", "active", "paused"}:
        care_plan_services.submit_care_plan_for_signature(**common)
    if status in {"active", "paused"}:
        care_plan_services.sign_care_plan(
            clinic_id=world.clinic.pk,
            care_plan_id=plan.pk,
            signing_professional=author,
        )
    if status == "paused":
        care_plan_services.pause_care_plan(**common)
    plan.refresh_from_db()
    return plan


def make_habit(
    world: World, patient: PatientProfile | None = None, **over: Any
) -> Habit:
    values: dict[str, Any] = {
        "clinic_id": world.clinic.pk,
        "patient_profile_id": (patient or world.patient).pk,
        "title": "Beber água",
        "description": "Um copo ao acordar.",
        "time_window": TimeOfDayWindow.MORNING,
    }
    values.update(over)
    return habit_services.create_habit(**values)


# ── HTML ────────────────────────────────────────────────────────────────────


class _Hidden(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        values = dict(attrs)
        name = values.get("name")
        if values.get("type") == "hidden" and name and name != "csrfmiddlewaretoken":
            self.fields[name] = values.get("value") or ""


def hidden_fields(html: str) -> dict[str, str]:
    """The hidden inputs of a page (what a browser would send back on submit)."""
    parser = _Hidden()
    parser.feed(html)
    return parser.fields
