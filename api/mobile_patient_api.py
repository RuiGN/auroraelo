"""Perfil e resumo do paciente para o app (`/api/v1/mobile/`)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Schema

from concierge.selectors import discharge_date_for_patient
from people.selectors import linked_therapists_for_patient

from .mobile_common import PatientBearerAuth, mobile_context

router = Router(tags=["Mobile · Paciente"], auth=PatientBearerAuth())

# Categorias do cadastro profissional que o app sabe nomear; o resto vira "other".
_TEAM_ROLES = {"psychiatrist": "psychiatrist", "psychologist": "psychologist"}


class TeamMemberOut(Schema):
    id: UUID
    name: str
    role: str


class ClinicRefOut(Schema):
    id: UUID
    name: str


class PatientSummaryOut(Schema):
    id: UUID
    display_name: str
    language: str
    timezone: str
    clinic: ClinicRefOut
    discharge_date: date | None
    care_team: list[TeamMemberOut]


@router.get("/me/", response=PatientSummaryOut)
def me(request: HttpRequest):
    """Quem é o paciente, em que clínica, a data da alta e a equipe que o acompanha.

    Da alta sai **somente a data** (para contar os dias). Régua, ligações, visita e
    contatos com a família pertencem ao aplicativo da clínica.
    """
    context = mobile_context(request)
    profile = context.patient_profile
    team = linked_therapists_for_patient(
        clinic_id=context.clinic_id,
        patient_user_id=context.user.pk,
        on_date=timezone.localdate(),
    )
    return PatientSummaryOut(
        id=profile.pk,
        display_name=profile.social_name or profile.full_name,
        language=context.user.preferred_language or profile.language_code,
        timezone=profile.timezone_name,
        clinic=ClinicRefOut(id=context.clinic.pk, name=context.clinic.name),
        discharge_date=discharge_date_for_patient(
            clinic_id=context.clinic_id, patient_profile_id=profile.pk
        ),
        care_team=[
            TeamMemberOut(
                id=row.therapist_id,
                name=row.social_name or row.full_name,
                role=_TEAM_ROLES.get(row.category, "other"),
            )
            for row in team
        ],
    )
