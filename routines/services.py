"""Service layer for habits, routine blocks, and check-ins (8.14.1, 8.14.2)."""

from __future__ import annotations

from datetime import date, time
from typing import Any
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.services import record_audit_event
from core.services import Service as CoreService

from .events import (
    habit_checked_in,
    habit_created,
    habit_paused,
    habit_resumed,
)
from .models import (
    CheckInStatus,
    Habit,
    HabitCheckIn,
    HabitFrequency,
    HabitOccurrence,
    HabitStatus,
    RoutineBlock,
    TimeOfDayWindow,
)


class Service(CoreService[Any, Any]):
    """Routines domain service base."""


def _audit_habit(
    *,
    clinic_id: UUID,
    actor_id: UUID | None,
    request_id: UUID | None,
    action: str,
    habit: Habit,
    justification: str,
) -> None:
    """Audit a team change to a habit (identifiers only, never the habit text).

    Callers that act for the patient's own flows (no ``actor_id``) are not audited
    here: those paths keep their own trail.
    """
    if actor_id is None:
        return
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action=action,
        resource_type="habit",
        resource_id=str(habit.pk),
        outcome="success",
        request_id=request_id or uuid4(),
        network_origin=None,
        justification=justification,
    )


@transaction.atomic
def create_routine_block(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    name: str,
    time_window: str = TimeOfDayWindow.MORNING,
    start_time: time | None = None,
    order: int = 0,
) -> RoutineBlock:
    """Create a structured block to organize daily habits without pressure."""
    clean_name = name.strip()
    if not clean_name:
        raise ValidationError("Nome do bloco de rotina é obrigatório.")

    block = RoutineBlock.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        name=clean_name,
        time_window=time_window,
        start_time=start_time,
        order=order,
        is_active=True,
    )
    return block


@transaction.atomic
def reorder_routine_blocks(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    block_ids_ordered: list[UUID],
) -> list[RoutineBlock]:
    """Reorder routine blocks for a patient preserving tenant isolation."""
    blocks = list(
        RoutineBlock.objects.for_clinic(clinic_id).filter(
            patient_profile_id=patient_profile_id,
            id__in=block_ids_ordered,
        )
    )
    block_map = {b.id: b for b in blocks}

    updated = []
    for idx, b_id in enumerate(block_ids_ordered):
        if b_id in block_map:
            b = block_map[b_id]
            b.order = idx
            b.save(update_fields=["order", "updated_at"])
            updated.append(b)
    return updated


@transaction.atomic
def create_habit(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    title: str,
    description: str = "",
    frequency: str = HabitFrequency.DAILY,
    active_days: list[int] | None = None,
    target_count: int = 1,
    time_window: str = TimeOfDayWindow.ANY_TIME,
    target_time: time | None = None,
    target_duration_minutes: int = 0,
    reminder_enabled: bool = False,
    reminder_lead_minutes: int = 15,
    quiet_hours_start: time | None = None,
    quiet_hours_end: time | None = None,
    timezone_name: str = "America/Sao_Paulo",
    routine_block_id: UUID | None = None,
    order: int = 0,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> Habit:
    """Create a new habit designed with self-compassionate, flexible framing."""
    clean_title = title.strip()
    if not clean_title:
        raise ValidationError("Título do hábito é obrigatório.")

    days = list(active_days or [0, 1, 2, 3, 4, 5, 6])
    if frequency == HabitFrequency.WEEKDAYS:
        days = [0, 1, 2, 3, 4]

    habit = Habit.objects.for_clinic(clinic_id).create(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        routine_block_id=routine_block_id,
        title=clean_title,
        description=description.strip(),
        frequency=frequency,
        active_days=days,
        target_count=max(1, target_count),
        time_window=time_window,
        target_time=target_time,
        target_duration_minutes=max(0, target_duration_minutes),
        status=HabitStatus.ACTIVE,
        version=1,
        reminder_enabled=reminder_enabled,
        reminder_lead_minutes=reminder_lead_minutes,
        quiet_hours_start=quiet_hours_start,
        quiet_hours_end=quiet_hours_end,
        timezone_name=timezone_name,
        order=order,
    )
    _audit_habit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        request_id=request_id,
        action="routines.habit_created",
        habit=habit,
        justification="Team created a habit",
    )
    habit_created.send(sender=Habit, habit=habit)
    return habit


@transaction.atomic
def update_habit(
    *,
    clinic_id: UUID,
    habit_id: UUID,
    title: str | None = None,
    description: str | None = None,
    frequency: str | None = None,
    active_days: list[int] | None = None,
    routine_block_id: UUID | None = None,
    target_duration_minutes: int | None = None,
    reminder_enabled: bool | None = None,
    time_window: str | None = None,
    target_time: time | None = None,
    clear_target_time: bool = False,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> Habit:
    """Update habit configuration, incrementing version for future occurrences.

    ``target_time=None`` leaves the time untouched; pass ``clear_target_time=True``
    to remove it.
    """
    habit = Habit.objects.for_clinic(clinic_id).filter(pk=habit_id).first()
    if not habit:
        raise ValidationError("Hábito não encontrado.")

    update_fields = ["updated_at", "version"]
    habit.version += 1

    if title is not None:
        clean = title.strip()
        if not clean:
            raise ValidationError("Título do hábito não pode ser vazio.")
        habit.title = clean
        update_fields.append("title")

    if description is not None:
        habit.description = description.strip()
        update_fields.append("description")

    if frequency is not None:
        habit.frequency = frequency
        update_fields.append("frequency")

    if active_days is not None:
        habit.active_days = active_days
        update_fields.append("active_days")

    if routine_block_id is not None:
        habit.routine_block_id = routine_block_id
        update_fields.append("routine_block")

    if target_duration_minutes is not None:
        habit.target_duration_minutes = max(0, target_duration_minutes)
        update_fields.append("target_duration_minutes")

    if reminder_enabled is not None:
        habit.reminder_enabled = reminder_enabled
        update_fields.append("reminder_enabled")

    if time_window is not None:
        habit.time_window = time_window
        update_fields.append("time_window")

    if target_time is not None or clear_target_time:
        habit.target_time = None if clear_target_time else target_time
        update_fields.append("target_time")

    habit.save(update_fields=update_fields)
    _audit_habit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        request_id=request_id,
        action="routines.habit_updated",
        habit=habit,
        justification="Team edited a habit",
    )
    return habit


@transaction.atomic
def pause_habit(
    *,
    clinic_id: UUID,
    habit_id: UUID,
    paused_until: date | None = None,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> Habit:
    """Pause habit without streak penalty, respecting user autonomy."""
    habit = Habit.objects.for_clinic(clinic_id).filter(pk=habit_id).first()
    if not habit:
        raise ValidationError("Hábito não encontrado.")
    if habit.status == HabitStatus.ARCHIVED:
        raise ValidationError("Um hábito arquivado não pode ser pausado.")

    habit.status = HabitStatus.PAUSED
    habit.paused_until = paused_until
    habit.save(update_fields=["status", "paused_until", "updated_at"])
    _audit_habit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        request_id=request_id,
        action="routines.habit_paused",
        habit=habit,
        justification="Team paused a habit",
    )
    habit_paused.send(sender=Habit, habit=habit)
    return habit


@transaction.atomic
def resume_habit(
    *,
    clinic_id: UUID,
    habit_id: UUID,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> Habit:
    """Resume a paused habit cleanly."""
    habit = Habit.objects.for_clinic(clinic_id).filter(pk=habit_id).first()
    if not habit:
        raise ValidationError("Hábito não encontrado.")
    if habit.status == HabitStatus.ARCHIVED:
        raise ValidationError("Um hábito arquivado não pode ser retomado.")

    habit.status = HabitStatus.ACTIVE
    habit.paused_until = None
    habit.save(update_fields=["status", "paused_until", "updated_at"])
    _audit_habit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        request_id=request_id,
        action="routines.habit_resumed",
        habit=habit,
        justification="Team resumed a habit",
    )
    habit_resumed.send(sender=Habit, habit=habit)
    return habit


@transaction.atomic
def archive_habit(
    *,
    clinic_id: UUID,
    habit_id: UUID,
    actor_id: UUID | None = None,
    request_id: UUID | None = None,
) -> Habit:
    """Archive a habit so it no longer generates future occurrences."""
    habit = Habit.objects.for_clinic(clinic_id).filter(pk=habit_id).first()
    if not habit:
        raise ValidationError("Hábito não encontrado.")

    habit.status = HabitStatus.ARCHIVED
    habit.save(update_fields=["status", "updated_at"])
    _audit_habit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        request_id=request_id,
        action="routines.habit_archived",
        habit=habit,
        justification="Team archived a habit",
    )
    return habit


@transaction.atomic
def generate_habit_occurrences_for_date(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    scheduled_date: date,
) -> list[HabitOccurrence]:
    """Generate daily habit occurrences idempotently based on active days."""
    habits = Habit.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id,
        status=HabitStatus.ACTIVE,
    )

    day_of_week = scheduled_date.weekday()
    created_occurrences: list[HabitOccurrence] = []

    for habit in habits:
        if habit.paused_until and scheduled_date <= habit.paused_until:
            continue

        if habit.active_days and day_of_week not in habit.active_days:
            continue

        plan_key = f"plan_{habit.id}_{scheduled_date}_{habit.version}"

        occ, created = HabitOccurrence.objects.for_clinic(clinic_id).get_or_create(
            habit=habit,
            scheduled_date=scheduled_date,
            defaults={
                "clinic_id": clinic_id,
                "plan_key": plan_key,
                "version": habit.version,
                "is_canceled": False,
            },
        )
        created_occurrences.append(occ)

    return created_occurrences


@transaction.atomic
def ensure_habit_occurrence(
    *, clinic_id: UUID, habit_id: UUID, scheduled_date: date
) -> HabitOccurrence | None:
    """Return the occurrence of one habit on one date, creating it when due.

    Returns ``None`` when the habit is not scheduled that day (paused, not an
    active weekday or not active at all), so callers can refuse the check-in.
    """
    habit = Habit.objects.for_clinic(clinic_id).filter(pk=habit_id).first()
    if habit is None or habit.status != HabitStatus.ACTIVE:
        return None
    if habit.paused_until and scheduled_date <= habit.paused_until:
        return None
    if habit.active_days and scheduled_date.weekday() not in habit.active_days:
        return None
    occurrence, _created = HabitOccurrence.objects.for_clinic(clinic_id).get_or_create(
        habit=habit,
        scheduled_date=scheduled_date,
        defaults={
            "clinic_id": clinic_id,
            "plan_key": f"plan_{habit.id}_{scheduled_date}_{habit.version}",
            "version": habit.version,
            "is_canceled": False,
        },
    )
    return occurrence


@transaction.atomic
def clear_habit_checkin(
    *, clinic_id: UUID, occurrence_id: UUID, actor_id: UUID, request_id: UUID
) -> bool:
    """Remove the patient's own check-in of one occurrence (undo), with audit."""
    checkin = (
        HabitCheckIn.objects.for_clinic(clinic_id)
        .filter(occurrence_id=occurrence_id)
        .first()
    )
    if checkin is None:
        return False
    checkin_id = checkin.pk
    checkin.delete()
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="delete",
        resource_type="habit_checkin",
        resource_id=str(checkin_id),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return True


@transaction.atomic
def record_habit_checkin(
    *,
    clinic_id: UUID,
    occurrence_id: UUID,
    status: str = CheckInStatus.COMPLETED,
    intensity_level: int | None = None,
    duration_minutes_executed: int | None = None,
    notes: str = "",
    actor_id: UUID | None = None,
) -> HabitCheckIn:
    """Record one effective, auditable check-in for a scheduled occurrence."""
    occ = HabitOccurrence.objects.for_clinic(clinic_id).filter(pk=occurrence_id).first()
    if not occ:
        raise ValidationError("Ocorrência de hábito não encontrada.")

    checkin = HabitCheckIn.objects.for_clinic(clinic_id).filter(occurrence=occ).first()

    now = timezone.now()
    history_entry = {
        "previous_status": checkin.status if checkin else None,
        "new_status": status,
        "changed_at": now.isoformat(),
        "actor_id": str(actor_id) if actor_id else None,
        "notes": notes.strip(),
    }

    if checkin is None:
        checkin = HabitCheckIn.objects.for_clinic(clinic_id).create(
            clinic_id=clinic_id,
            occurrence=occ,
            status=status,
            intensity_level=intensity_level,
            duration_minutes_executed=duration_minutes_executed,
            notes=notes.strip(),
            checked_in_at=now,
            history=[history_entry],
        )
    else:
        history = list(checkin.history)
        history.append(history_entry)
        checkin.status = status
        checkin.intensity_level = intensity_level
        checkin.duration_minutes_executed = duration_minutes_executed
        checkin.notes = notes.strip()
        checkin.checked_in_at = now
        checkin.history = history
        checkin.save(
            update_fields=[
                "status",
                "intensity_level",
                "duration_minutes_executed",
                "notes",
                "checked_in_at",
                "history",
                "updated_at",
            ]
        )

    habit_checked_in.send(sender=HabitCheckIn, checkin=checkin)
    return checkin


@transaction.atomic
def export_patient_routine_data(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
) -> dict[str, Any]:
    """Export all patient habits and check-in history under LGPD data portability."""
    habits = Habit.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id
    )
    habits_data = [
        {
            "id": str(h.id),
            "title": h.title,
            "description": h.description,
            "frequency": h.frequency,
            "status": h.status,
            "created_at": h.created_at.isoformat(),
        }
        for h in habits
    ]

    checkins = (
        HabitCheckIn.objects.for_clinic(clinic_id)
        .filter(occurrence__habit__patient_profile_id=patient_profile_id)
        .select_related("occurrence__habit")
    )

    checkins_data = [
        {
            "habit_title": c.occurrence.habit.title,
            "scheduled_date": c.occurrence.scheduled_date.isoformat(),
            "status": c.status,
            "duration_executed": c.duration_minutes_executed,
            "checked_in_at": c.checked_in_at.isoformat(),
        }
        for c in checkins
    ]

    return {
        "patient_profile_id": str(patient_profile_id),
        "exported_at": timezone.now().isoformat(),
        "habits": habits_data,
        "checkins": checkins_data,
    }


@transaction.atomic
def delete_patient_routine_data(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    actor_id: UUID,
) -> None:
    """Erase patient habits and check-ins under LGPD right to deletion."""
    Habit.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id
    ).delete()
    RoutineBlock.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id
    ).delete()

    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action="routines.patient_data_deleted",
        resource_type="patient_routine_data",
        resource_id=str(patient_profile_id),
        outcome="success",
        request_id=uuid4(),
        network_origin=None,
        justification="LGPD titular deletion request",
    )


__all__ = [
    "Service",
    "archive_habit",
    "create_habit",
    "create_routine_block",
    "clear_habit_checkin",
    "delete_patient_routine_data",
    "ensure_habit_occurrence",
    "export_patient_routine_data",
    "generate_habit_occurrences_for_date",
    "pause_habit",
    "record_habit_checkin",
    "reorder_routine_blocks",
    "resume_habit",
    "update_habit",
]
