"""Acceptance tests for PRD 8.7.1 goals and tracked steps."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, TypedDict
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client

from accounts.models import User
from accounts.services import accept_invitation
from clinics.models import Clinic, ClinicMembership
from goals import services as goal_services
from goals.models import Goal, GoalEvent, GoalStep
from people import services as people_services
from people.models import PatientProfile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db


class PatientPayload(TypedDict):
    full_name: str
    social_name: str
    birth_date: date
    gender: str
    email: str
    phone: str
    language_code: str
    timezone_name: str
    accessibility_preferences: str
    address: dict[str, object]
    address_purpose: str
    emergency_contact: dict[str, object]
    emergency_contact_purpose: str


def _payload(email: str) -> PatientPayload:
    return {
        "full_name": "Paciente Exemplo",
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


def _linked_patient(
    clinic: Clinic, *, email: str = "um@example.test"
) -> tuple[User, User, PatientProfile]:
    administrator = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=administrator, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    profile = people_services.register_patient_profile(
        clinic_id=clinic.pk, actor=administrator, request_id=uuid4(), **_payload(email)
    )
    issued = people_services.issue_patient_invitation(
        clinic_id=clinic.pk,
        actor=administrator,
        patient_profile_id=profile.pk,
        expires_at=people_services.invitation_expiration_after(days=2),
        request_id=uuid4(),
    )
    user = accept_invitation(
        raw_token=issued.raw_token,
        password="senha-sintetica-longa-e-nao-reutilizavel",
        first_name="Paciente",
        last_name="Exemplo",
    )
    profile.refresh_from_db()
    return administrator, user, profile


def _goal_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Retomar caminhadas diárias",
        "description": "Caminhar 20 minutos por dia.",
        "horizon": Goal.Horizon.SHORT.value,
        "priority": Goal.Priority.HIGH,
        "due_date": None,
        "steps": ["Separe os tênis", "Caminhe 5 minutos hoje"],
        "visibility": Goal.Visibility.PRIVATE.value,
    }
    base.update(overrides)
    return base


def _link_therapist(
    clinic: Clinic, administrator: User, profile: PatientProfile
) -> User:
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    people_services.create_patient_care_relationship(
        clinic_id=clinic.pk,
        actor=administrator,
        therapist_id=therapist.pk,
        patient_profile_id=profile.pk,
        function="primary_therapist",
        valid_from=date.today(),
        valid_until=None,
        request_id=uuid4(),
    )
    return therapist


# ---------------------------------------------------------------------------
# 8.7.1.1 Modeling tests
# ---------------------------------------------------------------------------


def test_goal_created_with_steps_priority_and_status() -> None:
    """8.7.1.1: Goal with steps, priority, defining actor, visibility and enum."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)

    goal = goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(),
    )

    assert goal.status == Goal.Status.ACTIVE
    assert goal.priority == Goal.Priority.HIGH
    assert goal.visibility == Goal.Visibility.PRIVATE
    assert goal.defining_actor_id == user.pk
    steps = list(GoalStep.infrastructure_objects.filter(goal=goal))
    assert [s.description for s in steps] == [
        "Separe os tênis",
        "Caminhe 5 minutos hoje",
    ]
    assert [s.order for s in steps] == [1, 2]


def test_goal_creation_validations() -> None:
    """8.7.1.1: Title, horizon, priority and visibility are validated."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)

    with pytest.raises(ValidationError, match="título"):
        goal_services.create_goal(
            clinic_id=clinic.pk,
            actor=user,
            request_id=uuid4(),
            **_goal_kwargs(title="  "),
        )

    with pytest.raises(ValidationError, match="horizonte"):
        goal_services.create_goal(
            clinic_id=clinic.pk,
            actor=user,
            request_id=uuid4(),
            **_goal_kwargs(horizon="decade"),
        )

    with pytest.raises(ValidationError, match="prioridade"):
        goal_services.create_goal(
            clinic_id=clinic.pk,
            actor=user,
            request_id=uuid4(),
            **_goal_kwargs(priority=9),
        )

    with pytest.raises(ValidationError, match="visibilidade"):
        goal_services.create_goal(
            clinic_id=clinic.pk,
            actor=user,
            request_id=uuid4(),
            **_goal_kwargs(visibility="blue"),
        )


def test_goal_denied_for_non_patient() -> None:
    """8.7.1.1: Only patient role creates goals for themselves."""
    clinic = ClinicFactory.create()
    outsider = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=outsider, role=ClinicMembership.Role.CLINIC_ADMIN
    )

    with pytest.raises(PermissionDenied):
        goal_services.create_goal(
            clinic_id=clinic.pk,
            actor=outsider,
            request_id=uuid4(),
            **_goal_kwargs(),
        )


# ---------------------------------------------------------------------------
# 8.7.1.2 Progress and history tests
# ---------------------------------------------------------------------------


def test_progress_calculated_from_completed_steps() -> None:
    """8.7.1.2: Progress comes from completed steps."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)
    goal = goal_services.create_goal(
        clinic_id=clinic.pk, actor=user, request_id=uuid4(), **_goal_kwargs()
    )
    steps = list(GoalStep.infrastructure_objects.filter(goal=goal))

    goal_services.complete_step(
        clinic_id=clinic.pk,
        actor=user,
        step_id=steps[0].pk,
        is_done=True,
        request_id=uuid4(),
    )
    done, total, percent = goal_services.goal_progress(goal=goal)
    assert (done, total, percent) == (1, 2, 50)

    goal_services.complete_step(
        clinic_id=clinic.pk,
        actor=user,
        step_id=steps[1].pk,
        is_done=True,
        request_id=uuid4(),
    )
    done, total, percent = goal_services.goal_progress(goal=goal)
    assert (done, total, percent) == (2, 2, 100)


def test_reopen_and_due_date_change_preserve_history() -> None:
    """8.7.1.2: Reopening and due-date changes are recorded."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)
    goal = goal_services.create_goal(
        clinic_id=clinic.pk, actor=user, request_id=uuid4(), **_goal_kwargs()
    )
    future = date.today() + timedelta(days=10)

    updated = goal_services.update_goal(
        clinic_id=clinic.pk,
        actor=user,
        goal_id=goal.pk,
        title=goal.title,
        priority=goal.priority,
        due_date=future,
        request_id=uuid4(),
    )
    assert updated.due_date == future

    goal_services.set_goal_status(
        clinic_id=clinic.pk,
        actor=user,
        goal_id=goal.pk,
        status=Goal.Status.COMPLETED,
        request_id=uuid4(),
    )
    reopened = goal_services.set_goal_status(
        clinic_id=clinic.pk,
        actor=user,
        goal_id=goal.pk,
        status=Goal.Status.ACTIVE,
        request_id=uuid4(),
    )
    assert reopened.status == Goal.Status.ACTIVE
    assert reopened.completed_at is None

    kinds = set(
        GoalEvent.infrastructure_objects.filter(goal=goal).values_list(
            "kind", flat=True
        )
    )
    assert {
        GoalEvent.Kind.CREATED,
        GoalEvent.Kind.UPDATED,
        GoalEvent.Kind.DUE_DATE_CHANGED,
        GoalEvent.Kind.COMPLETED,
        GoalEvent.Kind.REOPENED,
    } <= kinds


def test_goal_without_steps_zero_progress() -> None:
    """8.7.1.4: A goal without steps reports zero progress, never errors."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)
    goal = goal_services.create_goal(
        clinic_id=clinic.pk, actor=user, request_id=uuid4(), **_goal_kwargs(steps=[])
    )
    done, total, percent = goal_services.goal_progress(goal=goal)
    assert (done, total, percent) == (0, 0, 0)


# ---------------------------------------------------------------------------
# 8.7.1.3 Traffic-light tests
# ---------------------------------------------------------------------------


def test_therapist_sees_only_shareable_goals() -> None:
    """8.7.1.3: Only Verde goals reach the therapist; sharing is never inferred."""
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = _link_therapist(clinic, administrator, profile)

    shareable = goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(visibility=Goal.Visibility.SHAREABLE, title="Meta verde"),
    )
    goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(
            visibility=Goal.Visibility.CONFIRMATION_REQUIRED, title="Meta amarela"
        ),
    )
    goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(visibility=Goal.Visibility.PRIVATE, title="Meta privada"),
    )

    visible = goal_services.therapist_visible_goals(
        clinic_id=clinic.pk, therapist_id=therapist.pk
    )
    assert [g.pk for g in visible] == [shareable_pk(shareable=shareable)]


def shareable_pk(*, shareable: Goal) -> object:
    return shareable.pk


def test_goal_access_denied_after_revocation() -> None:
    """8.7.1.4: Revoking visibility immediately blocks therapist access."""
    clinic = ClinicFactory.create()
    administrator, user, profile = _linked_patient(clinic)
    therapist = _link_therapist(clinic, administrator, profile)
    goal = goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(visibility=Goal.Visibility.SHAREABLE),
    )
    assert (
        len(
            goal_services.therapist_visible_goals(
                clinic_id=clinic.pk, therapist_id=therapist.pk
            )
        )
        == 1
    )

    goal_services.set_goal_visibility(
        clinic_id=clinic.pk,
        actor=user,
        goal_id=goal.pk,
        visibility=Goal.Visibility.PRIVATE,
        request_id=uuid4(),
    )
    assert (
        goal_services.therapist_visible_goals(
            clinic_id=clinic.pk, therapist_id=therapist.pk
        )
        == []
    )


def test_overdue_due_date_is_flagged_not_blocked() -> None:
    """8.7.1.4: Overdue goals remain accessible — no punitive blocking."""
    clinic = ClinicFactory.create()
    _administrator, user, _profile = _linked_patient(clinic)
    past = date.today() - timedelta(days=5)
    goal = goal_services.create_goal(
        clinic_id=clinic.pk,
        actor=user,
        request_id=uuid4(),
        **_goal_kwargs(due_date=past),
    )
    # Past due date does not prevent further edits
    updated = goal_services.update_goal(
        clinic_id=clinic.pk,
        actor=user,
        goal_id=goal.pk,
        title="Prazo renovado sem culpa",
        priority=goal.priority,
        due_date=None,
        request_id=uuid4(),
    )
    assert updated.due_date is None


def test_cross_clinic_goal_access_denied() -> None:
    """8.7.1.4: Goals from another clinic are never reachable."""
    clinic_a = ClinicFactory.create()
    _administrator_a, user_a, _profile_a = _linked_patient(clinic_a)
    goal_a = goal_services.create_goal(
        clinic_id=clinic_a.pk,
        actor=user_a,
        request_id=uuid4(),
        **_goal_kwargs(visibility=Goal.Visibility.SHAREABLE),
    )

    clinic_b = ClinicFactory.create()
    _administrator_b, user_b, profile_b = _linked_patient(
        clinic_b, email="b@example.test"
    )
    therapist_b = _link_therapist(clinic_b, _administrator_b, profile_b)

    with pytest.raises(PermissionDenied):
        goal_services.set_goal_visibility(
            clinic_id=clinic_a.pk,
            actor=user_b,
            goal_id=goal_a.pk,
            visibility=Goal.Visibility.PRIVATE,
            request_id=uuid4(),
        )
    with pytest.raises(PermissionDenied):
        goal_services.update_goal(
            clinic_id=clinic_a.pk,
            actor=user_b,
            goal_id=goal_a.pk,
            title="Invadir",
            priority=Goal.Priority.LOW,
            due_date=None,
            request_id=uuid4(),
        )
    with pytest.raises(PermissionDenied):
        goal_services.therapist_visible_goals(
            clinic_id=clinic_a.pk, therapist_id=therapist_b.pk
        )


# ---------------------------------------------------------------------------
# 8.7.2 HTTP panel tests
# ---------------------------------------------------------------------------


def _force_patient_client(client: Client, clinic: Clinic, user: User) -> None:
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
