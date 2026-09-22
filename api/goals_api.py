"""Goals API — therapeutic goals and step tracking endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from ninja import Router, Schema

router = Router(tags=["Goals"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class GoalIn(Schema):
    title: str
    description: str = ""
    horizon: str = "short"
    priority: int = 2
    due_date: date | None = None
    steps: list[str] = []
    visibility: str = "private"


class GoalOut(Schema):
    id: UUID
    title: str
    description: str
    horizon: str
    priority: int
    due_date: date | None
    status: str
    visibility: str
    steps_done: int = 0
    steps_total: int = 0
    progress_percentage: int = 0
    created_at: datetime
    updated_at: datetime


class GoalStepOut(Schema):
    id: UUID
    description: str
    order: int
    is_done: bool
    done_at: datetime | None
    created_at: datetime


class StepToggleIn(Schema):
    is_done: bool


class StatusChangeIn(Schema):
    status: str
    reason: str = ""


class ErrorOut(Schema):
    detail: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _request_id(request: HttpRequest) -> UUID:
    raw = getattr(request, "request_id", None)
    if raw:
        try:
            return UUID(raw) if isinstance(raw, str) else uuid4()
        except ValueError:
            pass
    return uuid4()


def _clinic_id(request: HttpRequest) -> UUID:
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        raise PermissionDenied
    return clinic.pk


def _enrich_goal(goal) -> dict:
    """Add computed progress fields to a goal for the API response."""
    from goals.services import goal_progress

    done, total, pct = goal_progress(goal=goal)
    return {
        "id": goal.pk,
        "title": goal.title,
        "description": goal.description,
        "horizon": goal.horizon,
        "priority": goal.priority,
        "due_date": goal.due_date,
        "status": goal.status,
        "visibility": goal.visibility,
        "steps_done": done,
        "steps_total": total,
        "progress_percentage": pct,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
    }


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/", response=list[GoalOut])
def list_goals(request: HttpRequest, status: str = ""):
    """List the authenticated patient's goals with progress."""
    from goals.selectors import patient_goals

    goals = patient_goals(
        clinic_id=_clinic_id(request),
        actor=request.user,
        status=status,
    )
    return [_enrich_goal(g) for g in goals]


@router.post("/", response={201: GoalOut, 422: ErrorOut})
def create_goal(request: HttpRequest, payload: GoalIn):
    """Create a new therapeutic goal with optional steps."""
    from goals.services import create_goal as svc_create_goal

    try:
        goal = svc_create_goal(
            clinic_id=_clinic_id(request),
            actor=request.user,
            request_id=_request_id(request),
            **payload.dict(),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return 201, _enrich_goal(goal)


@router.get("/{goal_id}/steps/", response=list[GoalStepOut])
def list_steps(request: HttpRequest, goal_id: UUID):
    """List steps for a specific goal."""
    from goals.selectors import goal_steps_for_patient

    steps = goal_steps_for_patient(
        clinic_id=_clinic_id(request),
        actor=request.user,
        goal_id=goal_id,
    )
    return [GoalStepOut.from_orm(s) for s in steps]


@router.post(
    "/steps/{step_id}/toggle/",
    response={200: GoalStepOut, 422: ErrorOut},
)
def toggle_step(request: HttpRequest, step_id: UUID, payload: StepToggleIn):
    """Mark a goal step as done or undone."""
    from goals.services import complete_step

    try:
        step = complete_step(
            clinic_id=_clinic_id(request),
            actor=request.user,
            step_id=step_id,
            is_done=payload.is_done,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return GoalStepOut.from_orm(step)


@router.post("/{goal_id}/status/", response={200: GoalOut, 422: ErrorOut})
def change_status(request: HttpRequest, goal_id: UUID, payload: StatusChangeIn):
    """Change goal status (active, paused, completed, archived)."""
    from goals.services import set_goal_status

    try:
        goal = set_goal_status(
            clinic_id=_clinic_id(request),
            actor=request.user,
            goal_id=goal_id,
            status=payload.status,
            reason=payload.reason,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return _enrich_goal(goal)
