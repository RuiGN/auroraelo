"""Read selectors for the goals domain."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.db.models import Prefetch

from core.selectors import Selector as Selector
from people.selectors import patient_profile_for_user

from .exercise_models import (
    AssignmentStatus,
    ExerciseAssignment,
    ExerciseExecution,
)
from .low_energy_models import LowEnergyActionTemplate, LowEnergyMode
from .models import Goal, GoalStep

__all__ = [
    "Selector",
    "low_energy_actions_for_patient",
    "patient_goals_with_steps",
    "patient_exercise_assignments",
    "patient_exercise_executions",
    "patient_goals",
    "patient_profile_low_energy_active",
    "therapist_visible_goals_selector",
]


def patient_goals(
    *, clinic_id: UUID, actor: AbstractBaseUser, status: str = ""
) -> list[Goal]:
    """Return the patient's own goals, newest first."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    queryset = Goal.objects.for_clinic(clinic_id).filter(patient_profile_id=profile.pk)
    if status and status in Goal.Status.values:
        queryset = queryset.filter(status=status)
    return list(queryset.order_by("priority", "due_date", "-created_at"))


def goal_steps_for_patient(
    *, clinic_id: UUID, actor: AbstractBaseUser, goal_id: UUID
) -> list[GoalStep]:
    """Return one owned goal's steps in stable order."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    return list(
        GoalStep.objects.for_clinic(clinic_id)
        .filter(goal_id=goal_id, goal__patient_profile_id=profile.pk)
        .order_by("order", "id")
    )


def therapist_visible_goals_selector(
    *, clinic_id: UUID, therapist_id: UUID, on_date: date
) -> list[Goal]:
    """Public read interface delegating to the domain service."""
    from .services import therapist_visible_goals

    return therapist_visible_goals(
        clinic_id=clinic_id, therapist_id=therapist_id, on_date=on_date
    )


def patient_profile_low_energy_active(
    *, clinic_id: UUID, patient_profile_id: UUID
) -> bool:
    """Return whether one patient profile has an active low-energy session.

    Used by the scheduling domain to suppress non-essential reminders while a
    low-energy mode is active. Appointment reminders remain essential and are
    never suppressed by this signal.
    """
    return any(
        session.is_active
        for session in LowEnergyMode.objects.for_clinic(clinic_id).filter(
            patient_profile_id=patient_profile_id,
            suppress_non_essential_notifications=True,
        )
    )


def patient_exercise_executions(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    completed_only: bool = False,
) -> list[ExerciseExecution]:
    """Return the patient's own exercise executions, newest first."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    queryset = ExerciseExecution.objects.for_clinic(clinic_id).filter(
        patient_profile_id=profile.pk
    )
    if completed_only:
        queryset = queryset.filter(completed_at__isnull=False)
    return list(queryset.order_by("-created_at", "-id"))


def patient_exercise_assignments(
    *, clinic_id: UUID, actor: AbstractBaseUser
) -> list[ExerciseAssignment]:
    """Return the patient's own assigned or completed exercises, newest first.

    Cancelled assignments and unpublished exercise drafts are never listed.
    """
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    return list(
        ExerciseAssignment.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=profile.pk,
            status__in=(AssignmentStatus.ASSIGNED, AssignmentStatus.COMPLETED),
        )
        .select_related("exercise")
        .prefetch_related(
            Prefetch(
                "executions",
                queryset=ExerciseExecution.objects.for_clinic(clinic_id),
            )
        )
        .order_by("status", "due_date", "-created_at")
    )


def low_energy_actions_for_patient(
    *, clinic_id: UUID, actor: AbstractBaseUser
) -> list[str]:
    """Return the patient's configured minimal actions (up to three)."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    template = (
        LowEnergyActionTemplate.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=profile.pk, is_active=True)
        .order_by("-version")
        .first()
    )
    if template is None:
        return []
    return [
        action
        for action in (template.action_1, template.action_2, template.action_3)
        if action
    ]


def patient_goals_with_steps(
    *, clinic_id: UUID, actor: AbstractBaseUser
) -> list[tuple[Goal, list[GoalStep]]]:
    """Return the patient's own goals, each with its steps in stable order."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    goals = list(
        Goal.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=profile.pk)
        .exclude(status=Goal.Status.ARCHIVED)
        .order_by("priority", "due_date", "-created_at")
    )
    steps_by_goal: dict[UUID, list[GoalStep]] = {goal.pk: [] for goal in goals}
    for step in (
        GoalStep.objects.for_clinic(clinic_id)
        .filter(goal_id__in=steps_by_goal)
        .order_by("order", "id")
    ):
        steps_by_goal[step.goal_id].append(step)
    return [(goal, steps_by_goal[goal.pk]) for goal in goals]
