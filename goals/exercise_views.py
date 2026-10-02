"""HTTP views for the team: exercise catalog, assignment and execution review.

Patients answer exercises only in the mobile app (``/api/v1/mobile/exercises/``).
"""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from core.services import current_correlation_id
from people.selectors import (
    patient_profiles_for_clinic,
)

from .exercise_models import (
    ExerciseComment,
    ExerciseExecution,
    ExerciseStatus,
    ExerciseVisibility,
    ResponseFormat,
    TherapeuticExercise,
)
from .exercise_services import (
    assign_exercise,
    comment_on_execution,
    create_exercise,
    ensure_default_exercises_for_clinic,
    update_exercise,
)


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError:
        return uuid4()


def _clinic_and_actor(request: HttpRequest) -> tuple[UUID, AbstractBaseUser]:
    actor = request.user
    if not isinstance(actor, AbstractBaseUser):
        raise PermissionDenied
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        raise PermissionDenied
    return cast(UUID, clinic.pk), actor


# --- Therapist/Admin Catalog Views (8.7.4) ---


@login_required
@require_GET
def exercise_catalog(request: HttpRequest) -> HttpResponse:
    """Therapist/admin catalog of exercises for the active clinic (8.7.4.1)."""
    clinic_id, actor = _clinic_and_actor(request)
    ensure_default_exercises_for_clinic(clinic_id=clinic_id, author=actor)

    exercises = TherapeuticExercise.objects.for_clinic(clinic_id).order_by(
        "-created_at"
    )
    return TemplateResponse(
        request,
        "goals/exercise_catalog.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Catálogo de exercícios terapêuticos"),
            "exercises": exercises,
        },
    )


@login_required
def exercise_form(
    request: HttpRequest, exercise_id: UUID | None = None
) -> HttpResponse:
    """Create or edit an exercise template (8.7.4.2)."""
    clinic_id, actor = _clinic_and_actor(request)
    exercise = None
    if exercise_id is not None:
        exercise = (
            TherapeuticExercise.objects.for_clinic(clinic_id)
            .filter(pk=exercise_id)
            .first()
        )
        if exercise is None:
            raise PermissionDenied

    if request.method == "POST":
        title = request.POST.get("title", "")
        instructions = request.POST.get("instructions", "")
        approach = request.POST.get("approach", "Geral")
        estimated_minutes = int(request.POST.get("estimated_minutes", "10"))
        response_format = request.POST.get("response_format", ResponseFormat.TEXT)
        accessibility_notes = request.POST.get("accessibility_notes", "")
        status = request.POST.get("status", ExerciseStatus.PUBLISHED)

        if exercise is None:
            create_exercise(
                clinic_id=clinic_id,
                actor=actor,
                title=title,
                instructions=instructions,
                approach=approach,
                estimated_minutes=estimated_minutes,
                response_format=response_format,
                accessibility_notes=accessibility_notes,
                status=status,
                request_id=_request_uuid(),
            )
        else:
            update_exercise(
                clinic_id=clinic_id,
                actor=actor,
                exercise_id=exercise.pk,
                title=title,
                instructions=instructions,
                approach=approach,
                estimated_minutes=estimated_minutes,
                response_format=response_format,
                accessibility_notes=accessibility_notes,
                status=status,
                request_id=_request_uuid(),
            )
        return HttpResponseRedirect(reverse("exercise_catalog"))

    return TemplateResponse(
        request,
        "goals/exercise_form.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": (
                _("Novo exercício") if exercise is None else _("Editar exercício")
            ),
            "exercise": exercise,
            "response_formats": ResponseFormat.choices,
            "statuses": ExerciseStatus.choices,
        },
    )


@login_required
def exercise_assign_view(request: HttpRequest, exercise_id: UUID) -> HttpResponse:
    """Assign a published exercise to a patient (8.7.4.3)."""
    clinic_id, actor = _clinic_and_actor(request)
    exercise = (
        TherapeuticExercise.objects.for_clinic(clinic_id)
        .filter(pk=exercise_id, status=ExerciseStatus.PUBLISHED)
        .first()
    )
    if exercise is None:
        raise PermissionDenied("Exercício não encontrado ou não publicado.")

    if request.method == "POST":
        patient_profile_id = UUID(request.POST.get("patient_profile_id", ""))
        frequency = request.POST.get("frequency", "Pontual")
        due_date_str = request.POST.get("due_date", "")
        notes = request.POST.get("notes", "")

        from datetime import date

        due_date = date.fromisoformat(due_date_str) if due_date_str else None

        assign_exercise(
            clinic_id=clinic_id,
            actor=actor,
            exercise_id=exercise.pk,
            patient_profile_id=patient_profile_id,
            frequency=frequency,
            due_date=due_date,
            notes=notes,
            request_id=_request_uuid(),
        )
        return HttpResponseRedirect(reverse("exercise_catalog"))

    patients = patient_profiles_for_clinic(clinic_id=clinic_id)
    return TemplateResponse(
        request,
        "goals/exercise_assign.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Atribuir exercício a paciente"),
            "exercise": exercise,
            "patients": patients,
        },
    )


@login_required
def exercise_execution_detail_view(
    request: HttpRequest, execution_id: UUID
) -> HttpResponse:
    """View execution response and comments (8.7.5.3). Semaphore enforced."""
    clinic_id, actor = _clinic_and_actor(request)
    execution = (
        ExerciseExecution.objects.for_clinic(clinic_id)
        .filter(pk=execution_id)
        .select_related("assignment__exercise", "patient_profile")
        .first()
    )
    if execution is None:
        raise PermissionDenied("Execução não encontrada.")

    # Privada: só o paciente a vê, e o paciente usa apenas o aplicativo.
    if execution.visibility == ExerciseVisibility.PRIVATE:
        raise PermissionDenied("Esta resposta foi marcada como privada pelo paciente.")

    if request.method == "POST":
        content = request.POST.get("content", "")
        comment_on_execution(
            clinic_id=clinic_id,
            actor=actor,
            execution_id=execution.pk,
            content=content,
            request_id=_request_uuid(),
        )
        return HttpResponseRedirect(
            reverse("exercise_execution_detail", kwargs={"execution_id": execution.pk})
        )

    comments = (
        ExerciseComment.objects.for_clinic(clinic_id)
        .filter(execution_id=execution.pk)
        .select_related("author")
        .order_by("created_at")
    )

    return TemplateResponse(
        request,
        "goals/exercise_execution_detail.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Resposta: %(title)s")
            % {"title": execution.assignment.exercise.title},
            "execution": execution,
            "comments": comments,
        },
    )
