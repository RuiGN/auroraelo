"""Scheduling API — appointments, free slots, and services endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from ninja import Router, Schema

router = Router(tags=["Scheduling"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class ServiceOut(Schema):
    id: UUID
    name: str
    duration_minutes: int
    buffer_minutes: int
    is_active: bool


class AppointmentOut(Schema):
    id: UUID
    service_id: UUID
    professional_id: UUID
    patient_profile_id: UUID
    unit_id: UUID
    room_id: UUID | None = None
    start_at: datetime
    end_at: datetime
    status: str
    idempotency_key: str
    cancel_reason: str = ""
    created_at: datetime
    updated_at: datetime


class AppointmentRequestIn(Schema):
    service_id: UUID
    professional_id: UUID
    unit_id: UUID
    start_at: datetime
    end_at: datetime
    idempotency_key: str


class RescheduleIn(Schema):
    start_at: datetime
    end_at: datetime


class CancelIn(Schema):
    reason: str = ""


class FreeSlotsQuery(Schema):
    professional_id: UUID
    unit_id: UUID
    service_id: UUID
    from_date: date
    to_date: date


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


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/services/", response=list[ServiceOut])
def list_services(request: HttpRequest):
    """List active bookable services for the current clinic."""
    from scheduling.selectors import active_services_for_clinic

    services = active_services_for_clinic(clinic_id=_clinic_id(request))
    return [ServiceOut.from_orm(s) for s in services]


@router.get("/appointments/", response=list[AppointmentOut])
def list_appointments(
    request: HttpRequest,
    status: str = "",
    from_at: datetime | None = None,
    to_at: datetime | None = None,
):
    """List appointments visible to the authenticated user (role-scoped)."""
    from scheduling.selectors import appointments_visible_to

    appointments = appointments_visible_to(
        clinic_id=_clinic_id(request),
        actor=request.user,
        status=status,
        from_at=from_at,
        to_at=to_at,
    )
    return [AppointmentOut.from_orm(a) for a in appointments]


@router.get("/appointments/free-slots/", response=list[datetime])
def free_slots(
    request: HttpRequest,
    professional_id: UUID,
    unit_id: UUID,
    service_id: UUID,
    from_date: date,
    to_date: date,
):
    """Return available appointment slots for a professional."""
    from scheduling.services import free_slots as svc_free_slots

    return svc_free_slots(
        clinic_id=_clinic_id(request),
        professional_id=professional_id,
        unit_id=unit_id,
        service_id=service_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.post("/appointments/", response={201: AppointmentOut, 422: ErrorOut})
def request_appointment(request: HttpRequest, payload: AppointmentRequestIn):
    """Request a new appointment (idempotent via idempotency_key)."""
    from scheduling.services import request_appointment as svc_request

    try:
        appointment = svc_request(
            clinic_id=_clinic_id(request),
            actor=request.user,
            request_id=_request_id(request),
            **payload.dict(),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return 201, AppointmentOut.from_orm(appointment)


@router.post(
    "/appointments/{appointment_id}/confirm/",
    response={200: AppointmentOut, 422: ErrorOut},
)
def confirm_appointment(request: HttpRequest, appointment_id: UUID):
    """Confirm a requested appointment."""
    from scheduling.services import confirm_appointment as svc_confirm

    try:
        appointment = svc_confirm(
            clinic_id=_clinic_id(request),
            actor=request.user,
            appointment_id=appointment_id,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return AppointmentOut.from_orm(appointment)


@router.post(
    "/appointments/{appointment_id}/reschedule/",
    response={200: AppointmentOut, 422: ErrorOut},
)
def reschedule_appointment(
    request: HttpRequest, appointment_id: UUID, payload: RescheduleIn
):
    """Request appointment reschedule to a new time slot."""
    from scheduling.services import request_reschedule

    try:
        appointment = request_reschedule(
            clinic_id=_clinic_id(request),
            actor=request.user,
            appointment_id=appointment_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return AppointmentOut.from_orm(appointment)


@router.post(
    "/appointments/{appointment_id}/cancel/",
    response={200: AppointmentOut, 422: ErrorOut},
)
def cancel_appointment(
    request: HttpRequest, appointment_id: UUID, payload: CancelIn
):
    """Cancel an appointment with optional reason."""
    from scheduling.services import cancel_appointment as svc_cancel

    try:
        appointment = svc_cancel(
            clinic_id=_clinic_id(request),
            actor=request.user,
            appointment_id=appointment_id,
            reason=payload.reason,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return AppointmentOut.from_orm(appointment)


@router.post(
    "/appointments/{appointment_id}/complete/",
    response={200: AppointmentOut, 422: ErrorOut},
)
def complete_appointment(request: HttpRequest, appointment_id: UUID):
    """Mark appointment as completed after session."""
    from scheduling.services import complete_appointment as svc_complete

    try:
        appointment = svc_complete(
            clinic_id=_clinic_id(request),
            actor=request.user,
            appointment_id=appointment_id,
            request_id=_request_id(request),
        )
    except ValidationError as exc:
        return 422, {"detail": str(exc.message)}

    return AppointmentOut.from_orm(appointment)
