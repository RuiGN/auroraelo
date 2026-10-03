"""Read selectors for routines, habits, medications, sleep and care plans."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from core.selectors import Selector as CoreSelector

from .models import (
    CarePlan,
    CarePlanStatus,
    CheckInStatus,
    Habit,
    HabitOccurrence,
    MedicationConsentShare,
    MedicationLog,
    MedicationLogStatus,
    PrescribedMedication,
    RoutineBlock,
    SleepEntry,
    SleepProvenance,
)


class Selector(CoreSelector[Any, Any]):
    """Routines domain selector."""


def daily_routine_agenda_for_patient(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    query_date: date,
) -> dict[str, Any]:
    """Return organized routine blocks and scheduled habits for a specific date."""
    blocks_qs = (
        RoutineBlock.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=patient_profile_id,
            is_active=True,
        )
        .order_by("order", "created_at")
    )

    habits_qs = (
        Habit.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=patient_profile_id,
        )
        .exclude(status="archived")
        .order_by("order", "created_at")
    )

    occurrences = (
        HabitOccurrence.objects.for_clinic(clinic_id)
        .filter(
            habit__patient_profile_id=patient_profile_id,
            scheduled_date=query_date,
            is_canceled=False,
        )
        .select_related("habit", "checkin")
    )

    occurrence_map = {occ.habit_id: occ for occ in occurrences}

    blocks_data = []
    for block in blocks_qs:
        block_habits = [h for h in habits_qs if h.routine_block_id == block.id]
        habits_info = []
        for h in block_habits:
            occ = occurrence_map.get(h.id)
            checkin = getattr(occ, "checkin", None) if occ else None
            habits_info.append(
                {
                    "habit_id": h.id,
                    "title": h.title,
                    "time_window": h.time_window,
                    "target_time": h.target_time,
                    "target_duration_minutes": h.target_duration_minutes,
                    "status": h.status,
                    "has_occurrence": occ is not None,
                    "checkin_status": checkin.status if checkin else None,
                    "intensity_level": (checkin.intensity_level if checkin else None),
                    "duration_executed": (
                        checkin.duration_minutes_executed if checkin else None
                    ),
                }
            )
        blocks_data.append(
            {
                "block_id": block.id,
                "name": block.name,
                "time_window": block.time_window,
                "start_time": block.start_time,
                "habits": habits_info,
            }
        )

    unassigned_habits = [h for h in habits_qs if h.routine_block_id is None]
    unassigned_data = []
    for h in unassigned_habits:
        occ = occurrence_map.get(h.id)
        checkin = getattr(occ, "checkin", None) if occ else None
        unassigned_data.append(
            {
                "habit_id": h.id,
                "title": h.title,
                "time_window": h.time_window,
                "target_time": h.target_time,
                "target_duration_minutes": h.target_duration_minutes,
                "status": h.status,
                "has_occurrence": occ is not None,
                "checkin_status": checkin.status if checkin else None,
                "intensity_level": (checkin.intensity_level if checkin else None),
                "duration_executed": (
                    checkin.duration_minutes_executed if checkin else None
                ),
            }
        )

    return {
        "date": query_date.isoformat(),
        "blocks": blocks_data,
        "standalone_habits": unassigned_data,
    }


def habit_trends_for_period(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Calculate descriptive habit trends without social comparisons or
    causal claims."""
    occurrences = (
        HabitOccurrence.objects.for_clinic(clinic_id)
        .filter(
            habit__patient_profile_id=patient_profile_id,
            scheduled_date__gte=start_date,
            scheduled_date__lte=end_date,
            is_canceled=False,
        )
        .select_related("checkin")
    )

    total_occurrences = occurrences.count()
    completed_count = 0
    partial_count = 0
    postponed_count = 0
    skipped_count = 0
    unreported_count = 0
    total_minutes_spent = 0

    for occ in occurrences:
        checkin = getattr(occ, "checkin", None)
        if not checkin:
            unreported_count += 1
            continue
        if checkin.status == CheckInStatus.COMPLETED:
            completed_count += 1
        elif checkin.status == CheckInStatus.PARTIAL:
            partial_count += 1
        elif checkin.status == CheckInStatus.POSTPONED:
            postponed_count += 1
        elif checkin.status == CheckInStatus.SKIPPED:
            skipped_count += 1

        if checkin.duration_minutes_executed:
            total_minutes_spent += checkin.duration_minutes_executed

    completion_rate = (
        round((completed_count / total_occurrences) * 100, 1)
        if total_occurrences > 0
        else 0.0
    )

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_scheduled": total_occurrences,
        "completed": completed_count,
        "partial": partial_count,
        "postponed": postponed_count,
        "skipped": skipped_count,
        "unreported": unreported_count,
        "completion_rate_percent": completion_rate,
        "total_minutes_spent": total_minutes_spent,
    }


def prescribed_medications_for_patient(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    include_inactive: bool = False,
) -> list[PrescribedMedication]:
    """Return prescribed medications for patient, tenant-isolated."""
    qs = PrescribedMedication.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id
    )
    if not include_inactive:
        qs = qs.filter(is_active=True)
    return list(qs)


def medication_adherence_summary(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Return descriptive adherence statistics without compensation advice."""
    logs = MedicationLog.objects.for_clinic(clinic_id).filter(
        medication__patient_profile_id=patient_profile_id,
        scheduled_time__date__gte=start_date,
        scheduled_time__date__lte=end_date,
    )

    total_doses = logs.count()
    taken_count = logs.filter(status=MedicationLogStatus.TAKEN).count()
    late_count = logs.filter(status=MedicationLogStatus.LATE).count()
    omitted_count = logs.filter(status=MedicationLogStatus.OMITTED).count()
    not_reported_count = logs.filter(status=MedicationLogStatus.NOT_REPORTED).count()

    adherence_rate = (
        round(((taken_count + late_count) / total_doses) * 100, 1)
        if total_doses > 0
        else 0.0
    )

    return {
        "total_scheduled_doses": total_doses,
        "taken": taken_count,
        "late": late_count,
        "omitted": omitted_count,
        "not_reported": not_reported_count,
        "adherence_rate_percent": adherence_rate,
    }


def sleep_entries_for_patient(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    start_date: date,
    end_date: date,
) -> list[SleepEntry]:
    """Return sleep records for date interval."""
    return list(
        SleepEntry.objects.for_clinic(clinic_id).filter(
            patient_profile_id=patient_profile_id,
            reference_date__gte=start_date,
            reference_date__lte=end_date,
        )
    )


def sleep_trends_summary(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Descriptive sleep statistics without clinical diagnosis."""
    entries = sleep_entries_for_patient(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        start_date=start_date,
        end_date=end_date,
    )

    total_entries = len(entries)
    if total_entries == 0:
        return {
            "total_entries": 0,
            "avg_duration_minutes": 0,
            "avg_perceived_quality": 0.0,
            "self_reported_count": 0,
            "device_imported_count": 0,
            "total_naps_count": 0,
        }

    total_duration = sum(e.duration_minutes for e in entries)
    total_quality = sum(e.perceived_quality for e in entries)
    self_reported = sum(
        1 for e in entries if e.provenance == SleepProvenance.SELF_REPORTED
    )
    device_imported = sum(
        1 for e in entries if e.provenance == SleepProvenance.DEVICE_IMPORTED
    )
    naps_count = sum(1 for e in entries if e.nap_duration_minutes > 0)

    return {
        "total_entries": total_entries,
        "avg_duration_minutes": round(total_duration / total_entries),
        "avg_perceived_quality": round(total_quality / total_entries, 1),
        "self_reported_count": self_reported,
        "device_imported_count": device_imported,
        "total_naps_count": naps_count,
    }


def care_plans_for_patient(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
) -> list[CarePlan]:
    """Return care plans for patient with actions and responses."""
    return list(
        CarePlan.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=patient_profile_id)
        .prefetch_related("actions", "patient_responses")
    )


def professional_supervision_dashboard(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    period_days: int = 30,
) -> dict[str, Any]:
    """Provide clinicians with transparent overview separating provenances."""
    end_date = date.today()
    start_date = end_date - timedelta(days=period_days)

    habits_summary = habit_trends_for_period(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        start_date=start_date,
        end_date=end_date,
    )

    has_med_consent = (
        MedicationConsentShare.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=patient_profile_id,
            is_active=True,
        )
        .exists()
    )

    meds_summary = None
    if has_med_consent:
        meds_summary = medication_adherence_summary(
            clinic_id=clinic_id,
            patient_profile_id=patient_profile_id,
            start_date=start_date,
            end_date=end_date,
        )

    sleep_summary = sleep_trends_summary(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
        start_date=start_date,
        end_date=end_date,
    )

    care_plans = care_plans_for_patient(
        clinic_id=clinic_id,
        patient_profile_id=patient_profile_id,
    )

    return {
        "patient_profile_id": str(patient_profile_id),
        "period_days": period_days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "habits": habits_summary,
        "medication_adherence": meds_summary,
        "medication_consent_active": has_med_consent,
        "sleep": sleep_summary,
        "active_care_plans_count": sum(1 for p in care_plans if p.status == "active"),
    }


# ── Leituras do paciente sobre os próprios dados (app do paciente) ────────────
#
# Os serviços de escrita deste domínio autorizam só por clínica. Estes seletores
# resolvem o objeto **já restrito ao perfil do paciente**: quem chama nunca recebe
# (nem grava em) um item de outra pessoa da mesma clínica.

PATIENT_VISIBLE_PLAN_STATUSES = (
    CarePlanStatus.ACTIVE,
    CarePlanStatus.PAUSED,
    CarePlanStatus.COMPLETED,
    CarePlanStatus.REVOKED,
)


def medication_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID, medication_id: UUID
) -> PrescribedMedication | None:
    """Return one active medication of this patient, or ``None``."""
    return (
        PrescribedMedication.objects.for_clinic(clinic_id)
        .filter(pk=medication_id, patient_profile_id=patient_profile_id, is_active=True)
        .first()
    )


def medication_logs_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID, since: datetime
) -> list[MedicationLog]:
    """Return this patient's dose records scheduled at or after ``since``."""
    return list(
        MedicationLog.objects.for_clinic(clinic_id)
        .filter(
            medication__patient_profile_id=patient_profile_id,
            scheduled_time__gte=since,
        )
        .order_by("scheduled_time")
    )


def current_care_plan_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID
) -> CarePlan | None:
    """Return the newest care plan the patient may see (never drafts)."""
    return (
        CarePlan.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=patient_profile_id,
            status__in=PATIENT_VISIBLE_PLAN_STATUSES,
        )
        .prefetch_related("actions", "patient_responses")
        .order_by("-version", "-created_at")
        .first()
    )


def care_plan_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID, care_plan_id: UUID
) -> CarePlan | None:
    """Return one visible care plan of this patient, or ``None``."""
    return (
        CarePlan.objects.for_clinic(clinic_id)
        .filter(
            pk=care_plan_id,
            patient_profile_id=patient_profile_id,
            status__in=PATIENT_VISIBLE_PLAN_STATUSES,
        )
        .prefetch_related("actions", "patient_responses")
        .first()
    )


def habits_for_patient(*, clinic_id: UUID, patient_profile_id: UUID) -> list[Habit]:
    """Return the patient's habits that are active or temporarily paused."""
    return list(
        Habit.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=patient_profile_id)
        .exclude(status="archived")
        .order_by("order", "created_at")
    )


def habit_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID, habit_id: UUID
) -> Habit | None:
    """Return one non-archived habit of this patient, or ``None``."""
    return (
        Habit.objects.for_clinic(clinic_id)
        .filter(pk=habit_id, patient_profile_id=patient_profile_id)
        .exclude(status="archived")
        .first()
    )


def habit_checks_for_patient(
    *,
    clinic_id: UUID,
    patient_profile_id: UUID,
    start_date: date,
    end_date: date,
) -> list[tuple[UUID, date, str]]:
    """Return ``(habit_id, date, status)`` for effective check-ins in the range."""
    rows = (
        HabitOccurrence.objects.for_clinic(clinic_id)
        .filter(
            habit__patient_profile_id=patient_profile_id,
            scheduled_date__gte=start_date,
            scheduled_date__lte=end_date,
            is_canceled=False,
            checkin__isnull=False,
        )
        .select_related("checkin")
        .order_by("scheduled_date")
    )
    return [(row.habit_id, row.scheduled_date, row.checkin.status) for row in rows]


# ── Leituras da equipe (telas web de medicação, plano e hábitos) ──────────────
#
# Diferente das leituras do paciente acima, estas enxergam também o que o app não
# mostra (rascunho, aguardando assinatura, suspenso, arquivado). Quem chama já
# autorizou a equipe sobre o paciente; o objeto continua restrito a ele.


def medication_for_staff(
    *, clinic_id: UUID, patient_profile_id: UUID, medication_id: UUID
) -> PrescribedMedication | None:
    """Return one medication of this patient in any state, or ``None``."""
    return (
        PrescribedMedication.objects.for_clinic(clinic_id)
        .filter(pk=medication_id, patient_profile_id=patient_profile_id)
        .first()
    )


def care_plan_for_staff(
    *, clinic_id: UUID, patient_profile_id: UUID, care_plan_id: UUID
) -> CarePlan | None:
    """Return one care plan of this patient in any status, with its reply history."""
    return (
        CarePlan.objects.for_clinic(clinic_id)
        .filter(pk=care_plan_id, patient_profile_id=patient_profile_id)
        .prefetch_related("actions", "patient_responses")
        .first()
    )


def habit_for_staff(
    *, clinic_id: UUID, patient_profile_id: UUID, habit_id: UUID
) -> Habit | None:
    """Return one habit of this patient in any state, or ``None``."""
    return (
        Habit.objects.for_clinic(clinic_id)
        .filter(pk=habit_id, patient_profile_id=patient_profile_id)
        .first()
    )


def habits_for_staff(*, clinic_id: UUID, patient_profile_id: UUID) -> list[Habit]:
    """Return every habit of this patient, archived ones included."""
    return list(
        Habit.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=patient_profile_id)
        .order_by("order", "created_at")
    )


__all__ = [
    "Selector",
    "PATIENT_VISIBLE_PLAN_STATUSES",
    "care_plan_for_patient",
    "care_plan_for_staff",
    "care_plans_for_patient",
    "current_care_plan_for_patient",
    "daily_routine_agenda_for_patient",
    "habit_checks_for_patient",
    "habit_for_patient",
    "habit_for_staff",
    "habit_trends_for_period",
    "habits_for_patient",
    "habits_for_staff",
    "medication_adherence_summary",
    "medication_for_patient",
    "medication_for_staff",
    "medication_logs_for_patient",
    "prescribed_medications_for_patient",
    "professional_supervision_dashboard",
    "sleep_entries_for_patient",
    "sleep_trends_summary",
]
