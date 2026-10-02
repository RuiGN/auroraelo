"""Cuidado do paciente no app: medicação, plano de cuidado, rotina, exercícios e
modo de pouca energia (`/api/v1/mobile/`).

Todo objeto é resolvido **restrito ao perfil do paciente da sessão** antes de qualquer
gravação. Os serviços de domínio de rotinas autorizam só por clínica, então a posse
é conferida aqui por seletor: id de outra pessoa responde 404 e nada é gravado.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Router, Schema, Status

from goals.exercise_models import ExerciseAssignment, ExerciseExecution
from goals.exercise_services import start_or_resume_execution, submit_execution
from goals.low_energy_services import (
    activate_low_energy_mode,
    deactivate_low_energy_mode,
    get_low_energy_state,
)
from goals.selectors import low_energy_actions_for_patient, patient_exercise_assignments
from people.selectors import professional_display_names
from routines.care_plan_services import respond_to_care_plan
from routines.medication_services import record_medication_dose
from routines.models import CarePlan, MedicationLog
from routines.selectors import (
    care_plan_for_patient,
    current_care_plan_for_patient,
    habit_checks_for_patient,
    habit_for_patient,
    habits_for_patient,
    medication_for_patient,
    medication_logs_for_patient,
    prescribed_medications_for_patient,
)
from routines.services import (
    clear_habit_checkin,
    ensure_habit_occurrence,
    record_habit_checkin,
)

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    patient_zone,
    problem,
    request_id,
)

router = Router(tags=["Mobile · Cuidado"], auth=PatientBearerAuth())

DOSE_LOOKBACK_DAYS = 14
DOSE_EDIT_WINDOW_DAYS = 7
DOSE_FUTURE_TOLERANCE = timedelta(minutes=30)
HABIT_EDIT_WINDOW_DAYS = 7
MAX_TEXT = 4000
MAX_NOTES = 2000


# ── Medicação ───────────────────────────────────────────────────────────────


class MedicationOut(Schema):
    id: UUID
    name: str
    presentation: str
    dose: str
    route: str
    schedule_times: list[str]
    start_date: date
    end_date: date | None
    is_continuous: bool
    prescriber_name: str
    instructions: str


class DoseLogOut(Schema):
    id: UUID
    medication_id: UUID
    scheduled_for: datetime
    status: str
    recorded_at: datetime


class MedicationsOut(Schema):
    medications: list[MedicationOut]
    dose_logs: list[DoseLogOut]


class DoseIn(Schema):
    scheduled_for: datetime
    status: Literal["taken", "late", "omitted", "not_reported"]


def _hhmm(value: object) -> str:
    return str(value)[:5]


def _dose_out(log: MedicationLog) -> DoseLogOut:
    return DoseLogOut(
        id=log.pk,
        medication_id=log.medication_id,
        scheduled_for=log.scheduled_time,
        status=log.status,
        recorded_at=log.recorded_at,
    )


@router.get("/medications/", response=MedicationsOut)
def list_medications(request: HttpRequest):
    """Medicações ativas do paciente e os registros de dose dos últimos 14 dias.

    O app só mostra e registra; a prescrição é da equipe. Nenhuma dose é "compensada".
    """
    context = mobile_context(request)
    zone = patient_zone(context.patient_profile.timezone_name)
    today = timezone.now().astimezone(zone).date()
    medications = [
        item
        for item in prescribed_medications_for_patient(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
        )
        if item.is_continuous or item.end_date is None or item.end_date >= today
    ]
    logs = medication_logs_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        since=timezone.now() - timedelta(days=DOSE_LOOKBACK_DAYS),
    )
    return MedicationsOut(
        medications=[
            MedicationOut(
                id=item.pk,
                name=item.medication_name,
                presentation=item.presentation,
                dose=item.prescribed_dose,
                route=item.route,
                schedule_times=[_hhmm(t) for t in item.schedule_times],
                start_date=item.start_date,
                end_date=item.end_date,
                is_continuous=item.is_continuous,
                prescriber_name=item.prescriber_name,
                instructions=item.instructions,
            )
            for item in medications
        ],
        dose_logs=[_dose_out(log) for log in logs],
    )


@router.put(
    "/medications/{uuid:medication_id}/doses/",
    response={200: DoseLogOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def log_dose(request: HttpRequest, medication_id: UUID, payload: DoseIn):
    """Registra (ou corrige/desfaz com ``not_reported``) uma dose programada."""
    context = mobile_context(request)
    medication = medication_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        medication_id=medication_id,
    )
    if medication is None:
        return problem(404, "Medicação não encontrada.", "not_found")
    if payload.scheduled_for.tzinfo is None:
        return problem(422, "Informe o horário com fuso.", "timezone_required")
    zone = patient_zone(context.patient_profile.timezone_name)
    local = payload.scheduled_for.astimezone(zone).replace(second=0, microsecond=0)
    now = timezone.now()
    scheduled_utc = local.astimezone(UTC)
    in_schedule = _hhmm(local.time()) in {_hhmm(t) for t in medication.schedule_times}
    within_course = local.date() >= medication.start_date and (
        medication.is_continuous
        or medication.end_date is None
        or local.date() <= medication.end_date
    )
    too_old = scheduled_utc < now - timedelta(days=DOSE_EDIT_WINDOW_DAYS)
    too_new = scheduled_utc > now + DOSE_FUTURE_TOLERANCE
    if not (in_schedule and within_course) or too_old or too_new:
        return problem(
            422,
            "Esse horário não é uma dose programada que possa ser registrada.",
            "invalid_dose_time",
        )
    try:
        log = record_medication_dose(
            clinic_id=context.clinic_id,
            medication_id=medication.pk,
            scheduled_time=scheduled_utc,
            status=payload.status,
            actual_time=now if payload.status in {"taken", "late"} else None,
        )
    except ValidationError:
        return problem(422, "Não foi possível registrar a dose.", "dose_rejected")
    return Status(200, _dose_out(log))


# ── Plano de cuidado ────────────────────────────────────────────────────────


class CarePlanActionOut(Schema):
    id: UUID
    description: str
    target_frequency: str
    guidance: str
    is_mandatory: bool


class CarePlanResponseOut(Schema):
    decision: str
    notes: str
    responded_at: datetime


class CarePlanOut(Schema):
    id: UUID
    title: str
    objective: str
    contraindications: str
    status: str
    version: int
    valid_from: date
    valid_until: date | None
    prescriber_name: str
    actions: list[CarePlanActionOut]
    response: CarePlanResponseOut | None


class CarePlanEnvelope(Schema):
    care_plan: CarePlanOut | None


class CarePlanResponseIn(Schema):
    decision: Literal["accepted", "refused", "paused", "review_requested"]
    notes: str = Field(default="", max_length=MAX_NOTES)


def _care_plan_out(plan: CarePlan, *, clinic_id: UUID) -> CarePlanOut:
    names = professional_display_names(
        clinic_id=clinic_id,
        user_ids={plan.prescribing_professional_id},
    )
    reviewed = sorted(
        (
            item
            for item in plan.patient_responses.all()
            if item.plan_version_reviewed == plan.version
        ),
        key=lambda item: item.responded_at,
        reverse=True,
    )
    latest = reviewed[0] if reviewed else None
    return CarePlanOut(
        id=plan.pk,
        title=plan.title,
        objective=plan.objective,
        contraindications=plan.contraindications,
        status=plan.status,
        version=plan.version,
        valid_from=plan.valid_from,
        valid_until=plan.valid_until,
        prescriber_name=names.get(plan.prescribing_professional_id, ""),
        actions=[
            CarePlanActionOut(
                id=action.pk,
                description=action.action_description,
                target_frequency=action.target_frequency,
                guidance=action.guidance,
                is_mandatory=action.is_mandatory,
            )
            for action in sorted(
                plan.actions.all(),
                key=lambda a: (a.order, a.created_at),
            )
        ],
        response=(
            CarePlanResponseOut(
                decision=latest.decision,
                notes=latest.patient_notes,
                responded_at=latest.responded_at,
            )
            if latest is not None
            else None
        ),
    )


@router.get("/care-plan/", response=CarePlanEnvelope)
def get_care_plan(request: HttpRequest):
    """Plano de cuidado vigente (nunca rascunho) e a última resposta do paciente."""
    context = mobile_context(request)
    plan = current_care_plan_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    return CarePlanEnvelope(
        care_plan=(
            _care_plan_out(plan, clinic_id=context.clinic_id)
            if plan is not None
            else None
        )
    )


@router.post(
    "/care-plan/{uuid:care_plan_id}/response/",
    response={200: CarePlanOut, 404: MobileErrorOut, 409: MobileErrorOut},
)
def respond_care_plan(
    request: HttpRequest, care_plan_id: UUID, payload: CarePlanResponseIn
):
    """Registra a decisão do paciente. Recusar encerra o plano; pausar o pausa."""
    context = mobile_context(request)
    plan = care_plan_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        care_plan_id=care_plan_id,
    )
    if plan is None:
        return problem(404, "Plano não encontrado.", "not_found")
    if plan.status not in {"active", "paused"}:
        return problem(409, "Este plano não aceita resposta.", "plan_closed")
    try:
        respond_to_care_plan(
            clinic_id=context.clinic_id,
            care_plan_id=plan.pk,
            decision=payload.decision,
            patient_notes=payload.notes,
            actor_id=context.user.pk,
            request_id=request_id(request),
        )
    except ValidationError:
        return problem(409, "Não foi possível registrar a resposta.", "plan_closed")
    refreshed = care_plan_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        care_plan_id=plan.pk,
    )
    assert refreshed is not None
    return Status(200, _care_plan_out(refreshed, clinic_id=context.clinic_id))


# ── Rotina e hábitos ────────────────────────────────────────────────────────


class HabitOut(Schema):
    id: UUID
    title: str
    description: str
    time_window: str
    target_time: str | None
    paused_until: date | None


class HabitCheckOut(Schema):
    habit_id: UUID
    date: date
    status: str


class RoutineOut(Schema):
    habits: list[HabitOut]
    checks: list[HabitCheckOut]


class HabitCheckIn(Schema):
    status: Literal["completed", "partial", "postponed", "skipped"]


@router.get("/routine/", response=RoutineOut)
def get_routine(request: HttpRequest, days: int = 7):
    """Hábitos do paciente e os registros dos últimos ``days`` dias (padrão 7)."""
    days = max(1, min(days, 31))
    context = mobile_context(request)
    zone = patient_zone(context.patient_profile.timezone_name)
    today = timezone.now().astimezone(zone).date()
    habits = habits_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    checks = habit_checks_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        start_date=today - timedelta(days=days - 1),
        end_date=today,
    )
    return RoutineOut(
        habits=[
            HabitOut(
                id=habit.pk,
                title=habit.title,
                description=habit.description,
                time_window=habit.time_window,
                target_time=_hhmm(habit.target_time) if habit.target_time else None,
                paused_until=habit.paused_until,
            )
            for habit in habits
        ],
        checks=[
            HabitCheckOut(habit_id=habit_id, date=when, status=status)
            for habit_id, when, status in checks
        ],
    )


def _habit_day_error(check_date: date, today: date) -> Status[dict[str, str]] | None:
    if check_date > today or check_date < today - timedelta(
        days=HABIT_EDIT_WINDOW_DAYS
    ):
        return problem(
            422, "Só é possível registrar de hoje até 7 dias atrás.", "invalid_date"
        )
    return None


@router.put(
    "/habits/{uuid:habit_id}/checks/{check_date}/",
    response={200: HabitCheckOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def set_habit_check(
    request: HttpRequest, habit_id: UUID, check_date: date, payload: HabitCheckIn
):
    """Marca como feito, parcial, adiado ou pulado. Repetir o envio atualiza."""
    context = mobile_context(request)
    habit = habit_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        habit_id=habit_id,
    )
    if habit is None:
        return problem(404, "Hábito não encontrado.", "not_found")
    zone = patient_zone(context.patient_profile.timezone_name)
    invalid = _habit_day_error(check_date, timezone.now().astimezone(zone).date())
    if invalid is not None:
        return invalid
    occurrence = ensure_habit_occurrence(
        clinic_id=context.clinic_id, habit_id=habit.pk, scheduled_date=check_date
    )
    if occurrence is None:
        return problem(
            422, "Este hábito não está previsto para o dia.", "not_scheduled"
        )
    checkin = record_habit_checkin(
        clinic_id=context.clinic_id,
        occurrence_id=occurrence.pk,
        status=payload.status,
        actor_id=context.user.pk,
    )
    return Status(
        200, HabitCheckOut(habit_id=habit.pk, date=check_date, status=checkin.status)
    )


@router.delete(
    "/habits/{uuid:habit_id}/checks/{check_date}/",
    response={204: None, 404: MobileErrorOut, 422: MobileErrorOut},
)
def clear_habit_check(request: HttpRequest, habit_id: UUID, check_date: date):
    """Desfaz o registro do dia (a trilha de auditoria da clínica é mantida)."""
    context = mobile_context(request)
    habit = habit_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        habit_id=habit_id,
    )
    if habit is None:
        return problem(404, "Hábito não encontrado.", "not_found")
    zone = patient_zone(context.patient_profile.timezone_name)
    invalid = _habit_day_error(check_date, timezone.now().astimezone(zone).date())
    if invalid is not None:
        return invalid
    occurrence = ensure_habit_occurrence(
        clinic_id=context.clinic_id, habit_id=habit.pk, scheduled_date=check_date
    )
    if occurrence is not None:
        clear_habit_checkin(
            clinic_id=context.clinic_id,
            occurrence_id=occurrence.pk,
            actor_id=context.user.pk,
            request_id=request_id(request),
        )
    return Status(204, None)


# ── Exercícios da equipe ────────────────────────────────────────────────────


class ExerciseOut(Schema):
    id: UUID
    title: str
    instructions: str
    approach: str
    estimated_minutes: int
    response_format: str
    frequency: str
    due_date: date | None
    assigned_by_name: str
    status: str
    response: str
    completed_at: datetime | None
    visibility: str


class ExerciseCompleteIn(Schema):
    response: str = Field(min_length=1, max_length=MAX_TEXT)
    visibility: Literal["private", "shareable", "confirmation_required"] = "private"


def _latest_completed(assignment: ExerciseAssignment) -> ExerciseExecution | None:
    done = [
        item for item in assignment.executions.all() if item.completed_at is not None
    ]
    return max(done, key=lambda item: item.completed_at) if done else None


def _exercise_out(
    assignment: ExerciseAssignment, names: dict[UUID, str]
) -> ExerciseOut:
    exercise = assignment.exercise
    execution = _latest_completed(assignment)
    return ExerciseOut(
        id=assignment.pk,
        title=exercise.title,
        instructions=exercise.instructions,
        approach=exercise.approach,
        estimated_minutes=exercise.estimated_minutes,
        response_format=exercise.response_format,
        frequency=assignment.frequency,
        due_date=assignment.due_date,
        assigned_by_name=names.get(assignment.assigned_by_id, ""),
        status=assignment.status,
        response=(
            str(execution.response_data.get("response", ""))
            if execution is not None
            else ""
        ),
        completed_at=execution.completed_at if execution is not None else None,
        visibility=execution.visibility if execution is not None else "private",
    )


@router.get("/exercises/", response=list[ExerciseOut])
def list_exercises(request: HttpRequest):
    """Exercícios que a equipe passou ao paciente, com a resposta já enviada."""
    context = mobile_context(request)
    assignments = patient_exercise_assignments(
        clinic_id=context.clinic_id, actor=context.user
    )
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={a.assigned_by_id for a in assignments}
    )
    return [_exercise_out(item, names) for item in assignments]


@router.post(
    "/exercises/{uuid:assignment_id}/complete/",
    response={
        200: ExerciseOut,
        404: MobileErrorOut,
        409: MobileErrorOut,
        422: MobileErrorOut,
    },
)
def complete_exercise(
    request: HttpRequest, assignment_id: UUID, payload: ExerciseCompleteIn
):
    """Envia a resposta do exercício. Só o próprio paciente, uma única vez."""
    context = mobile_context(request)
    assignments = patient_exercise_assignments(
        clinic_id=context.clinic_id, actor=context.user
    )
    assignment = next((a for a in assignments if a.pk == assignment_id), None)
    if assignment is None:
        return problem(404, "Exercício não encontrado.", "not_found")
    if assignment.status != "assigned":
        return problem(409, "Este exercício já foi concluído.", "already_completed")
    text = payload.response.strip()
    fmt = assignment.exercise.response_format
    if fmt == "scale_1_5":
        if text not in {"1", "2", "3", "4", "5"}:
            return problem(422, "Responda com um número de 1 a 5.", "invalid_response")
    elif fmt != "text":
        return problem(
            422,
            "Este tipo de exercício ainda não está disponível no app.",
            "unsupported",
        )
    if not text:
        return problem(422, "Escreva a resposta.", "invalid_response")
    try:
        execution = start_or_resume_execution(
            clinic_id=context.clinic_id,
            actor=context.user,
            assignment_id=assignment.pk,
            request_id=request_id(request),
        )
        submit_execution(
            clinic_id=context.clinic_id,
            actor=context.user,
            execution_id=execution.pk,
            response_data={"response": text},
            visibility=payload.visibility,
            request_id=request_id(request),
        )
    except PermissionDenied:
        return problem(404, "Exercício não encontrado.", "not_found")
    refreshed = patient_exercise_assignments(
        clinic_id=context.clinic_id, actor=context.user
    )
    current = next(a for a in refreshed if a.pk == assignment.pk)
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={current.assigned_by_id}
    )
    return Status(200, _exercise_out(current, names))


# ── Modo de pouca energia ───────────────────────────────────────────────────


class LowEnergyOut(Schema):
    actions: list[str]
    active: bool
    started_at: datetime | None
    ends_at: datetime | None
    can_activate: bool


class LowEnergyIn(Schema):
    active: bool


def _low_energy_out(context) -> LowEnergyOut:
    actions = low_energy_actions_for_patient(
        clinic_id=context.clinic_id, actor=context.user
    )
    state = get_low_energy_state(clinic_id=context.clinic_id, actor=context.user)
    return LowEnergyOut(
        actions=actions,
        active=state is not None,
        started_at=state.started_at if state is not None else None,
        ends_at=state.ends_at if state is not None else None,
        can_activate=bool(actions),
    )


@router.get("/low-energy/", response=LowEnergyOut)
def get_low_energy(request: HttpRequest):
    """Até três ações mínimas e se o modo está ligado agora."""
    return _low_energy_out(mobile_context(request))


@router.put("/low-energy/", response={200: LowEnergyOut, 422: MobileErrorOut})
def set_low_energy(request: HttpRequest, payload: LowEnergyIn):
    """Liga ou desliga o modo de pouca energia."""
    context = mobile_context(request)
    try:
        if payload.active:
            activate_low_energy_mode(
                clinic_id=context.clinic_id,
                actor=context.user,
                request_id=request_id(request),
            )
        else:
            deactivate_low_energy_mode(
                clinic_id=context.clinic_id,
                actor=context.user,
                request_id=request_id(request),
            )
    except ValidationError:
        return problem(
            422,
            "Defina as ações mínimas antes de ligar o modo.",
            "no_actions_configured",
        )
    return Status(200, _low_energy_out(context))
