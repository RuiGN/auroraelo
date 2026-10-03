"""Consultas, horários livres e metas do paciente (`/api/v1/mobile/`).

Profissional, unidade e serviço vêm do cliente, então cada um é conferido no servidor:
o profissional precisa ser da equipe **vinculada a este paciente**, e unidade e
serviço, ativos na clínica da sessão. Cancelar ou remarcar só vale para consulta
do próprio paciente.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Router, Schema, Status

from goals.selectors import patient_goals_with_steps
from goals.services import complete_step, set_goal_status
from people.selectors import (
    PROFESSIONAL_FALLBACK_NAME,
    linked_therapists_for_patient,
    professional_display_names,
)
from scheduling.selectors import (
    active_services_for_clinic,
    active_units_for_clinic,
    appointments_visible_to,
)
from scheduling.services import (
    cancel_appointment,
    free_slots,
    request_appointment,
    request_reschedule,
)

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    patient_zone,
    problem,
    request_id,
)

router = Router(tags=["Mobile · Agenda e metas"], auth=PatientBearerAuth())

SLOT_WINDOW_DAYS = 14
MAX_OPTIONS = 12
MAX_REASON = 255


# ── Consultas ───────────────────────────────────────────────────────────────


class AppointmentOut(Schema):
    id: UUID
    service_name: str
    professional_name: str
    unit_name: str
    start_at: datetime
    end_at: datetime
    status: str
    cancel_reason: str


class BookingOptionOut(Schema):
    service_id: UUID
    service_name: str
    duration_minutes: int
    professional_id: UUID
    professional_name: str
    unit_id: UUID
    unit_name: str
    free_slots: list[datetime]


class AppointmentRequestIn(Schema):
    service_id: UUID
    professional_id: UUID
    unit_id: UUID
    start_at: datetime
    idempotency_key: str = Field(min_length=8, max_length=64)


class RescheduleIn(Schema):
    start_at: datetime
    service_duration_minutes: int | None = Field(default=None, ge=5, le=480)


class CancelIn(Schema):
    reason: str = Field(default="", max_length=MAX_REASON)


def _appointment_out(item, names: dict[UUID, str]) -> AppointmentOut:
    return AppointmentOut(
        id=item.pk,
        service_name=item.service.name,
        professional_name=names.get(item.professional_id) or PROFESSIONAL_FALLBACK_NAME,
        unit_name=item.unit.name,
        start_at=item.start_at,
        end_at=item.end_at,
        status=item.status,
        cancel_reason=item.cancel_reason,
    )


def _own_appointments(context):
    return appointments_visible_to(clinic_id=context.clinic_id, actor=context.user)


@router.get("/appointments/", response=list[AppointmentOut])
def list_appointments(request: HttpRequest):
    """Consultas do próprio paciente, com nomes (nada de id solto)."""
    context = mobile_context(request)
    items = _own_appointments(context)
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={i.professional_id for i in items}
    )
    return [_appointment_out(item, names) for item in items]


@router.get("/booking/options/", response=list[BookingOptionOut])
def booking_options(request: HttpRequest):
    """Combinações serviço × profissional vinculado × unidade e os horários livres.

    Os horários cobrem os próximos 14 dias e já excluem o que está ocupado.
    """
    context = mobile_context(request)
    zone = patient_zone(context.patient_profile.timezone_name)
    today = timezone.now().astimezone(zone).date()
    team = linked_therapists_for_patient(
        clinic_id=context.clinic_id,
        patient_user_id=context.user.pk,
        on_date=today,
    )
    options: list[BookingOptionOut] = []
    for service in active_services_for_clinic(clinic_id=context.clinic_id):
        for member in team:
            for unit in active_units_for_clinic(clinic_id=context.clinic_id):
                if len(options) >= MAX_OPTIONS:
                    break
                slots = [
                    slot
                    for slot in free_slots(
                        clinic_id=context.clinic_id,
                        professional_id=member.therapist_id,
                        unit_id=unit.pk,
                        service_id=service.pk,
                        from_date=today,
                        to_date=today + timedelta(days=SLOT_WINDOW_DAYS),
                    )
                    if slot > timezone.now()
                ]
                options.append(
                    BookingOptionOut(
                        service_id=service.pk,
                        service_name=service.name,
                        duration_minutes=service.duration_minutes,
                        professional_id=member.therapist_id,
                        professional_name=member.social_name or member.full_name,
                        unit_id=unit.pk,
                        unit_name=unit.name,
                        free_slots=slots,
                    )
                )
    return options


@router.post(
    "/appointments/",
    response={
        201: AppointmentOut,
        404: MobileErrorOut,
        409: MobileErrorOut,
        422: MobileErrorOut,
    },
)
def create_appointment(request: HttpRequest, payload: AppointmentRequestIn):
    """Solicita uma consulta. A clínica confirma; até lá fica como "solicitada"."""
    context = mobile_context(request)
    if payload.start_at.tzinfo is None:
        return problem(422, "Informe o horário com fuso.", "timezone_required")
    # A chave é única por clínica: prefixar com o paciente impede colisão.
    key = f"{context.patient_profile_id}:{payload.idempotency_key}"
    replay = next(
        (i for i in _own_appointments(context) if i.idempotency_key == key), None
    )
    if replay is not None:
        # Reenvio da mesma solicitação (toque duplo, rede instável): mesma resposta,
        # antes de conferir o horário — que o próprio pedido já ocupa.
        names = professional_display_names(
            clinic_id=context.clinic_id, user_ids={replay.professional_id}
        )
        return Status(201, _appointment_out(replay, names))
    zone = patient_zone(context.patient_profile.timezone_name)
    today = timezone.now().astimezone(zone).date()
    team = {
        row.therapist_id
        for row in linked_therapists_for_patient(
            clinic_id=context.clinic_id,
            patient_user_id=context.user.pk,
            on_date=today,
        )
    }
    if payload.professional_id not in team:
        return problem(404, "Profissional não encontrado.", "not_found")
    service = next(
        (
            s
            for s in active_services_for_clinic(clinic_id=context.clinic_id)
            if s.pk == payload.service_id
        ),
        None,
    )
    if service is None:
        return problem(404, "Serviço não encontrado.", "not_found")
    units = {unit.pk for unit in active_units_for_clinic(clinic_id=context.clinic_id)}
    if payload.unit_id not in units:
        return problem(404, "Unidade não encontrada.", "not_found")
    day = payload.start_at.astimezone(zone).date()
    slots = free_slots(
        clinic_id=context.clinic_id,
        professional_id=payload.professional_id,
        unit_id=payload.unit_id,
        service_id=service.pk,
        from_date=day,
        to_date=day,
    )
    if payload.start_at not in slots:
        return problem(422, "Este horário não está mais livre.", "slot_unavailable")
    try:
        appointment = request_appointment(
            clinic_id=context.clinic_id,
            actor=context.user,
            service_id=service.pk,
            professional_id=payload.professional_id,
            unit_id=payload.unit_id,
            start_at=payload.start_at,
            end_at=payload.start_at + timedelta(minutes=service.duration_minutes),
            idempotency_key=key,
            request_id=request_id(request),
        )
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "appointment_rejected")
    if appointment.patient_profile_id != context.patient_profile_id:
        return problem(409, "Chave de solicitação já usada.", "key_conflict")
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={appointment.professional_id}
    )
    own = {i.pk: i for i in _own_appointments(context)}
    return Status(201, _appointment_out(own.get(appointment.pk, appointment), names))


def _owned(context, appointment_id: UUID):
    return next((i for i in _own_appointments(context) if i.pk == appointment_id), None)


@router.post(
    "/appointments/{uuid:appointment_id}/cancel/",
    response={200: AppointmentOut, 404: MobileErrorOut, 409: MobileErrorOut},
)
def cancel(request: HttpRequest, appointment_id: UUID, payload: CancelIn):
    """Cancela uma consulta do próprio paciente (solicitada ou confirmada)."""
    context = mobile_context(request)
    if _owned(context, appointment_id) is None:
        return problem(404, "Consulta não encontrada.", "not_found")
    try:
        cancel_appointment(
            clinic_id=context.clinic_id,
            actor=context.user,
            appointment_id=appointment_id,
            reason=payload.reason,
            request_id=request_id(request),
        )
    except PermissionDenied, ValidationError:
        return problem(409, "Esta consulta não pode ser cancelada.", "not_cancelable")
    names = professional_display_names(
        clinic_id=context.clinic_id,
        user_ids={i.professional_id for i in _own_appointments(context)},
    )
    return Status(200, _appointment_out(_owned(context, appointment_id), names))


@router.post(
    "/appointments/{uuid:appointment_id}/reschedule/",
    response={
        200: AppointmentOut,
        404: MobileErrorOut,
        409: MobileErrorOut,
        422: MobileErrorOut,
    },
)
def reschedule(request: HttpRequest, appointment_id: UUID, payload: RescheduleIn):
    """Pede remarcação para um horário livre. A clínica confirma o novo horário."""
    context = mobile_context(request)
    current = _owned(context, appointment_id)
    if current is None:
        return problem(404, "Consulta não encontrada.", "not_found")
    if payload.start_at.tzinfo is None:
        return problem(422, "Informe o horário com fuso.", "timezone_required")
    zone = patient_zone(context.patient_profile.timezone_name)
    day = payload.start_at.astimezone(zone).date()
    slots = free_slots(
        clinic_id=context.clinic_id,
        professional_id=current.professional_id,
        unit_id=current.unit_id,
        service_id=current.service_id,
        from_date=day,
        to_date=day,
    )
    if payload.start_at not in slots:
        return problem(422, "Este horário não está mais livre.", "slot_unavailable")
    try:
        request_reschedule(
            clinic_id=context.clinic_id,
            actor=context.user,
            appointment_id=appointment_id,
            start_at=payload.start_at,
            end_at=payload.start_at
            + timedelta(minutes=current.service.duration_minutes),
            request_id=request_id(request),
        )
    except PermissionDenied, ValidationError:
        return problem(
            409, "Esta consulta não pode ser remarcada.", "not_reschedulable"
        )
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={current.professional_id}
    )
    return Status(200, _appointment_out(_owned(context, appointment_id), names))


# ── Metas ───────────────────────────────────────────────────────────────────


class GoalStepOut(Schema):
    id: UUID
    description: str
    order: int
    is_done: bool


class GoalOut(Schema):
    id: UUID
    title: str
    description: str
    horizon: str
    due_date: date | None
    status: str
    steps: list[GoalStepOut]


class StepIn(Schema):
    is_done: bool


class GoalStatusIn(Schema):
    status: Literal["active", "paused", "completed"]


def _goal_out(goal, steps) -> GoalOut:
    return GoalOut(
        id=goal.pk,
        title=goal.title,
        description=goal.description,
        horizon=goal.horizon,
        due_date=goal.due_date,
        status=goal.status,
        steps=[
            GoalStepOut(
                id=step.pk,
                description=step.description,
                order=step.order,
                is_done=step.is_done,
            )
            for step in steps
        ],
    )


@router.get("/goals/", response=list[GoalOut])
def list_goals(request: HttpRequest):
    """Metas do próprio paciente com seus passos."""
    context = mobile_context(request)
    return [
        _goal_out(goal, steps)
        for goal, steps in patient_goals_with_steps(
            clinic_id=context.clinic_id, actor=context.user
        )
    ]


@router.put(
    "/goals/steps/{uuid:step_id}/",
    response={200: GoalOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def set_step(request: HttpRequest, step_id: UUID, payload: StepIn):
    """Marca ou desmarca um passo da meta."""
    context = mobile_context(request)
    try:
        step = complete_step(
            clinic_id=context.clinic_id,
            actor=context.user,
            step_id=step_id,
            is_done=payload.is_done,
            request_id=request_id(request),
        )
    except PermissionDenied:
        return problem(404, "Passo não encontrado.", "not_found")
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "step_rejected")
    for goal, steps in patient_goals_with_steps(
        clinic_id=context.clinic_id, actor=context.user
    ):
        if goal.pk == step.goal_id:
            return Status(200, _goal_out(goal, steps))
    return problem(404, "Meta não encontrada.", "not_found")


@router.put(
    "/goals/{uuid:goal_id}/status/",
    response={200: GoalOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def set_status(request: HttpRequest, goal_id: UUID, payload: GoalStatusIn):
    """Pausa, retoma ou conclui uma meta."""
    context = mobile_context(request)
    try:
        goal = set_goal_status(
            clinic_id=context.clinic_id,
            actor=context.user,
            goal_id=goal_id,
            status=payload.status,
            reason="",
            request_id=request_id(request),
        )
    except PermissionDenied:
        return problem(404, "Meta não encontrada.", "not_found")
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "status_rejected")
    for item, steps in patient_goals_with_steps(
        clinic_id=context.clinic_id, actor=context.user
    ):
        if item.pk == goal.pk:
            return Status(200, _goal_out(item, steps))
    return problem(404, "Meta não encontrada.", "not_found")
