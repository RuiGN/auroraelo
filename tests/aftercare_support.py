"""Helpers sintéticos compartilhados pelos testes do concierge e da API do paciente."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import count
from typing import Any
from uuid import uuid4

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from people import services as people_services
from people.models import PatientProfile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

_emails = count(1)


@dataclass
class Stage:
    """Uma clínica sintética com equipe, e uma segunda clínica para isolamento."""

    clinic: Clinic
    admin: User
    staff: User
    therapist: User
    other_clinic: Clinic
    other_admin: User


def build_stage() -> Stage:
    clinic = ClinicFactory.create()
    other = ClinicFactory.create()
    admin = UserFactory.create()
    staff = UserFactory.create()
    therapist = UserFactory.create()
    other_admin = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=admin, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    ClinicMembershipFactory.create(
        clinic=clinic, user=staff, role=ClinicMembership.Role.ADMINISTRATIVE_STAFF
    )
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    ClinicMembershipFactory.create(
        clinic=other, user=other_admin, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    return Stage(clinic, admin, staff, therapist, other, other_admin)


def patient_payload(email: str, name: str = "Paciente Exemplo") -> dict[str, Any]:
    return {
        "full_name": name,
        "social_name": "",
        "birth_date": date(1990, 1, 1),
        "gender": "undisclosed",
        "email": email,
        "phone": "",
        "language_code": "pt-BR",
        "timezone_name": "America/Sao_Paulo",
        "accessibility_preferences": "",
        "address": {},
        "address_purpose": "",
        "emergency_contact": {},
        "emergency_contact_purpose": "",
    }


def make_patient(
    clinic: Clinic, actor: User, *, name: str = "Paciente Exemplo"
) -> PatientProfile:
    return people_services.register_patient_profile(
        clinic_id=clinic.pk,
        actor=actor,
        request_id=uuid4(),
        **patient_payload(f"paciente{next(_emails)}@example.test", name),
    )


@dataclass
class PatientLogin:
    """Paciente sintético com identidade, senha, vínculo de paciente e perfil."""

    user: User
    profile: PatientProfile
    clinic: Clinic
    password: str


def make_patient_login(
    clinic: Clinic,
    admin: User,
    *,
    name: str = "Paciente Exemplo",
    password: str = "Senha-Segura-123",  # nosec - credencial sintética de teste
    social_name: str = "",
) -> PatientLogin:
    """Cria o paciente que o app usaria: usuário com senha + vínculo + perfil."""
    profile = make_patient(clinic, admin, name=name)
    user = UserFactory.create(email=profile.email)
    user.set_password(password)
    user.save()
    ClinicMembershipFactory.create(
        clinic=clinic, user=user, role=ClinicMembership.Role.PATIENT
    )
    profile.user = user
    if social_name:
        profile.social_name = social_name
    profile.save()
    return PatientLogin(user=user, profile=profile, clinic=clinic, password=password)
