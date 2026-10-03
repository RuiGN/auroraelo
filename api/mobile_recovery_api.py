"""Recuperação e ajuda urgente no app do paciente (`/api/v1/mobile/`).

- A leitura da ajuda urgente **não tem efeito colateral**: abrir a tela não registra
  acesso nem avisa ninguém, como o app promete ao paciente.
- A ajuda urgente continua disponível mesmo se a clínica estiver com cobrança
  bloqueada (`allow_blocked_tenant`).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Router, Schema, Status

from support_network.selectors import urgent_support_plan_for_patient
from support_network.urgent_plan_models import UrgentSupportContact, UrgentSupportPlan
from wellness.models import CravingCheckIn, RelapsePreventionPlan, SobrietyGoal
from wellness.selectors import (
    active_sobriety_goal_for_patient,
    cravings_for_patient,
    crisis_resources_and_grounding,
    relapse_plan_for_patient,
)
from wellness.sobriety_services import (
    adjust_or_restart_sobriety_goal,
    record_craving_checkin,
    set_sobriety_counter_hidden,
)

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    patient_zone,
    problem,
)

router = Router(tags=["Mobile · Recuperação"], auth=PatientBearerAuth())
help_router = Router(
    tags=["Mobile · Ajuda urgente"], auth=PatientBearerAuth(allow_blocked_tenant=True)
)

MAX_DETAIL = 2000


# ── Meta de recuperação e contador ──────────────────────────────────────────


class SobrietyOut(Schema):
    id: UUID
    goal_type: str
    focus: str
    reference_date: date
    restart_count: int
    motivations: str
    hide_counter: bool


class CravingOut(Schema):
    id: UUID
    recorded_at: datetime
    intensity: int | None
    triggers_context: str
    coping_strategy_used: str


class RecoveryOut(Schema):
    sobriety: SobrietyOut | None
    cravings: list[CravingOut]


class CravingIn(Schema):
    intensity: int = Field(ge=1, le=10)
    triggers_context: str = Field(default="", max_length=MAX_DETAIL)
    coping_strategy_used: str = Field(default="", max_length=MAX_DETAIL)


class CounterVisibilityIn(Schema):
    hidden: bool


def sobriety_out(goal: SobrietyGoal) -> SobrietyOut:
    return SobrietyOut(
        id=goal.pk,
        goal_type=goal.goal_type,
        focus=goal.substance_or_behavior,
        reference_date=goal.reference_date,
        restart_count=goal.restart_count,
        motivations=goal.motivations,
        hide_counter=goal.hide_counter,
    )


def _craving_out(item: CravingCheckIn) -> CravingOut:
    return CravingOut(
        id=item.pk,
        recorded_at=item.recorded_at,
        intensity=item.intensity,
        triggers_context=item.triggers_context,
        coping_strategy_used=item.coping_strategy_used,
    )


@router.get("/recovery/", response=RecoveryOut)
def get_recovery(request: HttpRequest):
    """Meta de recuperação, contador e os últimos registros de vontade de usar."""
    context = mobile_context(request)
    goal = active_sobriety_goal_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    cravings = cravings_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    return RecoveryOut(
        sobriety=sobriety_out(goal) if goal is not None else None,
        cravings=[_craving_out(item) for item in cravings],
    )


@router.put(
    "/recovery/counter/",
    response={200: SobrietyOut, 404: MobileErrorOut},
)
def set_counter_visibility(request: HttpRequest, payload: CounterVisibilityIn):
    """Mostra ou oculta o contador. Não mexe em datas nem no histórico."""
    context = mobile_context(request)
    goal = active_sobriety_goal_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    if goal is None:
        return problem(404, "Nenhuma meta de recuperação ativa.", "not_found")
    updated = set_sobriety_counter_hidden(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        goal_id=goal.pk,
        hidden=payload.hidden,
        actor_id=context.user.pk,
    )
    return Status(200, sobriety_out(updated))


@router.post("/recovery/restart/", response={200: SobrietyOut, 404: MobileErrorOut})
def restart_counter(request: HttpRequest):
    """Recomeça o contador a partir de hoje, sem apagar nada e sem culpa."""
    context = mobile_context(request)
    goal = active_sobriety_goal_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    if goal is None:
        return problem(404, "Nenhuma meta de recuperação ativa.", "not_found")
    zone = patient_zone(context.patient_profile.timezone_name)
    updated = adjust_or_restart_sobriety_goal(
        clinic_id=context.clinic_id,
        goal_id=goal.pk,
        new_reference_date=timezone.now().astimezone(zone).date(),
        actor_id=context.user.pk,
        patient_profile_id=context.patient_profile_id,
    )
    return Status(200, sobriety_out(updated))


@router.post("/recovery/cravings/", response={201: CravingOut, 422: MobileErrorOut})
def add_craving(request: HttpRequest, payload: CravingIn):
    """Registra uma vontade de usar (registro privado, protegido na tela travada)."""
    context = mobile_context(request)
    goal = active_sobriety_goal_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    try:
        item = record_craving_checkin(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
            sobriety_goal_id=goal.pk if goal is not None else None,
            intensity=payload.intensity,
            triggers_context=payload.triggers_context,
            coping_strategy_used=payload.coping_strategy_used,
            actor_id=context.user.pk,
        )
    except ValidationError:
        return problem(422, "Intensidade inválida.", "invalid_intensity")
    return Status(201, _craving_out(item))


# ── Plano de prevenção de recaída ───────────────────────────────────────────


class RelapseSectionOut(Schema):
    id: UUID
    type: str
    title: str
    content: str


class RelapsePlanOut(Schema):
    id: UUID
    title: str
    version: int
    last_reviewed_at: datetime | None
    sections: list[RelapseSectionOut]


class RelapsePlanEnvelope(Schema):
    relapse_plan: RelapsePlanOut | None


def relapse_plan_envelope(plan: RelapsePreventionPlan | None) -> RelapsePlanEnvelope:
    """O plano no formato do app (seções na ordem do plano); ``None`` = sem plano."""
    if plan is None:
        return RelapsePlanEnvelope(relapse_plan=None)
    return RelapsePlanEnvelope(
        relapse_plan=RelapsePlanOut(
            id=plan.pk,
            title=plan.title,
            version=plan.version,
            last_reviewed_at=plan.last_reviewed_at,
            sections=[
                RelapseSectionOut(
                    id=section.pk,
                    type=section.section_type,
                    title=section.title,
                    content=section.content,
                )
                for section in sorted(
                    plan.sections.all(), key=lambda item: (item.order, item.created_at)
                )
            ],
        )
    )


@router.get("/relapse-plan/", response=RelapsePlanEnvelope)
def get_relapse_plan(request: HttpRequest):
    """Plano de prevenção de recaída do próprio paciente (edição: `PUT`)."""
    context = mobile_context(request)
    return relapse_plan_envelope(
        relapse_plan_for_patient(
            clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
        )
    )


# ── Ajuda urgente ───────────────────────────────────────────────────────────


class UrgentContactOut(Schema):
    id: UUID
    name: str
    relationship: str
    phone: str
    message_template: str


class UrgentPlanOut(Schema):
    personal_instructions: str
    calming_strategies: list[str]
    contacts: list[UrgentContactOut]
    last_reviewed_at: datetime


def urgent_contact_out(contact: UrgentSupportContact) -> UrgentContactOut:
    return UrgentContactOut(
        id=contact.pk,
        name=contact.name,
        relationship=contact.relationship,
        phone=contact.phone_number,
        message_template=contact.message_template,
    )


def urgent_plan_out(
    plan: UrgentSupportPlan, contacts: list[UrgentSupportContact]
) -> UrgentPlanOut:
    """Plano pessoal e contatos ativos, na ordem de prioridade (só ao dono)."""
    return UrgentPlanOut(
        personal_instructions=plan.personal_instructions,
        calming_strategies=[str(item) for item in plan.calming_strategies],
        contacts=[urgent_contact_out(contact) for contact in contacts],
        last_reviewed_at=plan.last_reviewed_at,
    )


class LocalResourceOut(Schema):
    name: str
    service_type: str
    phone: str
    hours: str


class GroundingOut(Schema):
    id: str
    title: str
    technique_type: str
    instructions: str
    steps: list[str]
    duration_seconds: int
    can_exit_anytime: bool


class CustomHelplineOut(Schema):
    name: str
    number: str


class HelpOut(Schema):
    disclaimer: str
    emergency_medical: str
    emergency_fire: str
    emotional_support: str
    custom_helpline: CustomHelplineOut | None
    urgent_plan: UrgentPlanOut | None
    local_resources: list[LocalResourceOut]
    grounding_exercises: list[GroundingOut]


@help_router.get("/help/", response=HelpOut)
def get_help(request: HttpRequest):
    """Números de emergência, plano pessoal e exercícios de aterramento.

    Somente leitura e sem registro de acesso: abrir a ajuda não avisa ninguém. Os
    números abrem o discador apenas quando o paciente toca, dentro do app.
    """
    context = mobile_context(request)
    resources = crisis_resources_and_grounding(clinic_id=context.clinic_id)
    urgent = urgent_support_plan_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    plan = urgent["plan"]
    return HelpOut(
        disclaimer=resources["mandatory_disclaimer"],
        emergency_medical=resources["emergency_medical"],
        emergency_fire=resources["emergency_fire"],
        emotional_support=resources["emotional_support"],
        custom_helpline=resources["custom_helpline"],
        urgent_plan=(
            urgent_plan_out(plan, urgent["contacts"]) if plan is not None else None
        ),
        local_resources=[
            LocalResourceOut(
                name=item.resource_name,
                service_type=item.service_type,
                phone=item.contact_number,
                hours=item.hours_of_operation,
            )
            for item in urgent["local_resources"]
        ],
        grounding_exercises=[
            GroundingOut(
                id=item["id"],
                title=item["title"],
                technique_type=item["technique_type"],
                instructions=item["instructions"],
                steps=[str(step) for step in item["steps"]],
                duration_seconds=item["duration_seconds"],
                can_exit_anytime=item["can_exit_anytime"],
            )
            for item in resources["grounding_exercises"]
        ],
    )
