"""Journal API — diary entries and daily check-in endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from ninja import Router, Schema

from clinics.typing import ClinicRequest

router = Router(tags=["Journal"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class JournalEntryIn(Schema):
    mood: int
    emotions: list[str] = []
    intensity: int
    context: str
    triggers: str = ""
    reactions: str = ""
    strategies: str = ""
    visibility: str = "private"


class JournalEntryOut(Schema):
    id: UUID
    mood: int
    emotions: list[str]
    intensity: int
    context: str
    triggers: str
    reactions: str
    strategies: str
    visibility: str
    created_at: datetime
    updated_at: datetime


class CheckInIn(Schema):
    answers: dict[str, object]
    period: str = "daily"
    idempotency_key: str = ""


class CheckInOut(Schema):
    id: UUID
    date: date
    period: str
    answers: dict[str, object]
    is_draft: bool
    created_at: datetime


class ErrorOut(Schema):
    detail: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _request_id(request: HttpRequest) -> UUID:
    """Extract or generate a correlation ID from the request."""
    raw = getattr(request, "request_id", None)
    if raw:
        try:
            return UUID(raw) if isinstance(raw, str) else uuid4()
        except ValueError:
            pass
    return uuid4()


def _clinic_id(request: HttpRequest) -> UUID:
    """Extract the resolved clinic from the tenant middleware."""
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        raise PermissionDenied
    return clinic.pk


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/entries/", response=list[JournalEntryOut])
def list_entries(
    request: HttpRequest,
    period: str = "",
    emotion: str = "",
    mood: int | None = None,
):
    """List the authenticated patient's journal entries."""
    from journal.selectors import patient_journal_entries

    entries = patient_journal_entries(
        clinic_id=_clinic_id(request),
        actor=request.user,
        period=period,
        emotion=emotion,
        mood=mood,
    )
    return [JournalEntryOut.from_orm(e) for e in entries]


@router.post("/entries/", response={201: JournalEntryOut, 422: ErrorOut})
def create_entry(request: HttpRequest, payload: JournalEntryIn):
    """Create a new journal diary entry."""
    from people.selectors import patient_profile_for_user
    from journal.services import create_journal_entry

    clinic_id = _clinic_id(request)
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=request.user.pk)
    if profile is None:
        return 422, {"detail": "Perfil de paciente não encontrado."}

    try:
        entry = create_journal_entry(
            clinic_id=clinic_id,
            actor=request.user,
            patient_profile_id=profile.pk,
            request_id=_request_id(request),
            **payload.dict(),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return 201, JournalEntryOut.from_orm(entry)


@router.get("/checkins/", response=list[CheckInOut])
def list_checkins(request: HttpRequest):
    """List the authenticated patient's daily check-ins."""
    from journal.selectors import patient_checkins

    checkins = patient_checkins(
        clinic_id=_clinic_id(request),
        actor=request.user,
    )
    return [CheckInOut.from_orm(c) for c in checkins]


@router.post("/checkins/", response={201: CheckInOut, 422: ErrorOut})
def submit_checkin(request: HttpRequest, payload: CheckInIn):
    """Submit a daily check-in (idempotent per period)."""
    from people.selectors import patient_profile_for_user
    from journal.services import submit_daily_checkin

    clinic_id = _clinic_id(request)
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=request.user.pk)
    if profile is None:
        return 422, {"detail": "Perfil de paciente não encontrado."}

    try:
        checkin = submit_daily_checkin(
            clinic_id=clinic_id,
            actor=request.user,
            patient_profile_id=profile.pk,
            request_id=_request_id(request),
            **payload.dict(),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return 201, CheckInOut.from_orm(checkin)
