"""Check-in, diário e pedidos de acesso ao diário (`/api/v1/mobile/`).

Os serviços do diário já autorizam pelo próprio paciente (ator da sessão). O
compartilhamento é sempre decisão dele: nada vai para a equipe sem ele marcar.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Router, Schema, Status

from journal.models import DailyCheckIn, JournalEntry
from journal.selectors import (
    patient_checkins,
    patient_journal_entries,
    patient_pending_access_requests,
)
from journal.services import (
    create_journal_entry,
    ensure_default_checkin_questionnaire,
    respond_journal_entry_access_request,
    set_journal_entry_visibility,
    submit_daily_checkin,
)
from people.selectors import professional_display_names

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    problem,
    request_id,
)

router = Router(tags=["Mobile · Diário"], auth=PatientBearerAuth())

CHECKIN_KEYS = (
    "general_state",
    "anxiety",
    "sadness",
    "irritability",
    "energy",
    "sleep_quality",
    "motivation",
)
HISTORY_DAYS_DEFAULT = 60
MAX_NOTES = 2000
Visibility = Literal["private", "shareable", "confirmation_required"]


class CheckInOut(Schema):
    id: UUID
    date: str
    answers: dict[str, int | None]
    notes: str
    visibility: str
    submitted_at: datetime


class EntryOut(Schema):
    id: UUID
    created_at: datetime
    mood: int
    emotions: list[str]
    intensity: int
    context: str
    triggers: str
    reactions: str
    strategies: str
    visibility: str


class DiaryOut(Schema):
    checkins: list[CheckInOut]
    entries: list[EntryOut]


class CheckInIn(Schema):
    answers: dict[str, int]
    notes: str = Field(default="", max_length=MAX_NOTES)
    visibility: Visibility = "private"


class EntryIn(Schema):
    mood: int = Field(ge=1, le=5)
    emotions: list[str] = Field(default_factory=list, max_length=8)
    intensity: int = Field(ge=1, le=5)
    context: str = Field(min_length=1, max_length=4000)
    triggers: str = Field(default="", max_length=MAX_NOTES)
    reactions: str = Field(default="", max_length=MAX_NOTES)
    strategies: str = Field(default="", max_length=MAX_NOTES)
    visibility: Visibility = "private"


class VisibilityIn(Schema):
    visibility: Visibility


class AccessRequestOut(Schema):
    id: UUID
    entry_id: UUID
    entry_created_at: datetime
    therapist_name: str
    purpose: str
    requested_at: datetime


class RespondIn(Schema):
    approve: bool
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


def _checkin_out(item: DailyCheckIn) -> CheckInOut:
    answers = {key: item.answers.get(key) for key in CHECKIN_KEYS}
    return CheckInOut(
        id=item.pk,
        date=item.date.isoformat(),
        answers={k: (int(v) if v is not None else None) for k, v in answers.items()},
        notes=str(item.answers.get("notes") or ""),
        visibility=item.visibility,
        submitted_at=item.submitted_at or item.created_at,
    )


def _entry_out(item: JournalEntry) -> EntryOut:
    return EntryOut(
        id=item.pk,
        created_at=item.created_at,
        mood=item.mood,
        emotions=list(item.emotions or []),
        intensity=item.intensity,
        context=item.context,
        triggers=item.triggers,
        reactions=item.reactions,
        strategies=item.strategies,
        visibility=item.visibility,
    )


@router.get("/diary/", response=DiaryOut)
def get_diary(request: HttpRequest, days: int = HISTORY_DAYS_DEFAULT):
    """Check-ins e registros do diário do próprio paciente (últimos ``days`` dias)."""
    days = max(1, min(days, 365))
    context = mobile_context(request)
    since = timezone.now() - timedelta(days=days)
    checkins = patient_checkins(
        clinic_id=context.clinic_id, actor=context.user, since=since
    )
    entries = [
        entry
        for entry in patient_journal_entries(
            clinic_id=context.clinic_id, actor=context.user
        )
        if entry.created_at >= since
    ]
    return DiaryOut(
        checkins=[_checkin_out(item) for item in checkins],
        entries=[_entry_out(item) for item in entries],
    )


@router.post("/checkins/", response={200: CheckInOut, 422: MobileErrorOut})
def submit_checkin(request: HttpRequest, payload: CheckInIn):
    """Envia o check-in do dia. Reenviar no mesmo dia atualiza o anterior."""
    context = mobile_context(request)
    if set(payload.answers) != set(CHECKIN_KEYS) or any(
        not 1 <= value <= 5 for value in payload.answers.values()
    ):
        return problem(422, "Responda as sete perguntas de 1 a 5.", "invalid_answers")
    ensure_default_checkin_questionnaire(clinic_id=context.clinic_id)
    answers: dict[str, object] = dict(payload.answers)
    if payload.notes.strip():
        answers["notes"] = payload.notes.strip()
    try:
        checkin = submit_daily_checkin(
            clinic_id=context.clinic_id,
            actor=context.user,
            patient_profile_id=context.patient_profile_id,
            answers=answers,
            period="daily",
            idempotency_key=f"app:{uuid4()}",
            visibility=payload.visibility,
            request_id=request_id(request),
        )
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "checkin_rejected")
    return Status(200, _checkin_out(checkin))


@router.post("/journal/", response={201: EntryOut, 422: MobileErrorOut})
def add_entry(request: HttpRequest, payload: EntryIn):
    """Registra no diário. Privado por padrão; compartilhar é escolha do paciente."""
    context = mobile_context(request)
    try:
        entry = create_journal_entry(
            clinic_id=context.clinic_id,
            actor=context.user,
            patient_profile_id=context.patient_profile_id,
            mood=payload.mood,
            emotions=payload.emotions,
            intensity=payload.intensity,
            context=payload.context,
            triggers=payload.triggers,
            reactions=payload.reactions,
            strategies=payload.strategies,
            visibility=payload.visibility,
            request_id=request_id(request),
        )
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "entry_rejected")
    return Status(201, _entry_out(entry))


@router.put(
    "/journal/{uuid:entry_id}/visibility/",
    response={200: EntryOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def set_entry_visibility(request: HttpRequest, entry_id: UUID, payload: VisibilityIn):
    """Muda quem pode ver um registro. Voltar a privado revoga acessos já dados."""
    context = mobile_context(request)
    try:
        entry = set_journal_entry_visibility(
            clinic_id=context.clinic_id,
            actor=context.user,
            journal_entry_id=entry_id,
            visibility=payload.visibility,
            request_id=request_id(request),
        )
    except PermissionDenied:
        return problem(404, "Registro não encontrado.", "not_found")
    except ValidationError as exc:
        return problem(422, "; ".join(exc.messages), "visibility_rejected")
    return Status(200, _entry_out(entry))


@router.get("/journal/access-requests/", response=list[AccessRequestOut])
def list_access_requests(request: HttpRequest):
    """Pedidos da equipe para ver registros marcados como "confirmar antes"."""
    context = mobile_context(request)
    pending = patient_pending_access_requests(
        clinic_id=context.clinic_id, actor=context.user
    )
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={item.therapist_id for item in pending}
    )
    return [
        AccessRequestOut(
            id=item.pk,
            entry_id=item.journal_entry_id,
            entry_created_at=item.journal_entry.created_at,
            therapist_name=names.get(item.therapist_id, ""),
            purpose=item.purpose,
            requested_at=item.requested_at,
        )
        for item in pending
    ]


@router.post(
    "/journal/access-requests/{uuid:request_pk}/respond/",
    response={204: None, 404: MobileErrorOut, 409: MobileErrorOut},
)
def respond_access_request(request: HttpRequest, request_pk: UUID, payload: RespondIn):
    """Aprova (com validade opcional) ou recusa o pedido. A decisão é do paciente."""
    context = mobile_context(request)
    expires_at = (
        timezone.now() + timedelta(days=payload.expires_in_days)
        if payload.approve and payload.expires_in_days
        else None
    )
    try:
        respond_journal_entry_access_request(
            clinic_id=context.clinic_id,
            actor=context.user,
            access_request_id=request_pk,
            approved=payload.approve,
            expires_at=expires_at,
            request_id=request_id(request),
        )
    except PermissionDenied:
        return problem(404, "Pedido não encontrado.", "not_found")
    except ValidationError:
        return problem(409, "Este pedido já foi respondido.", "already_answered")
    return Status(204, None)
