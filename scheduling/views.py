"""HTTP views for the team agenda (list, week, confirm, reschedule, complete).

Patients request, reschedule and cancel consultations only in the mobile app.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import cast
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from clinics.policies import has_active_clinic_role
from core.services import current_correlation_id

from .forms import (
    AppointmentActionForm,
    AppointmentRescheduleForm,
)
from .models import (
    Appointment,
    Service,
)
from .selectors import (
    appointments_visible_to,
)
from .services import (
    cancel_appointment,
    complete_appointment,
    confirm_appointment,
    record_no_show,
    request_reschedule,
)

NON_EMERGENCY_NOTICE = _lazy(
    "Este canal não atende emergências. Em perigo imediato, acione o serviço "
    "de emergência da sua localidade."
)


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def _clinic_and_actor(request: HttpRequest) -> tuple[UUID, AbstractBaseUser]:
    actor = request.user
    if not isinstance(actor, AbstractBaseUser):
        raise PermissionDenied
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        raise PermissionDenied
    return cast(UUID, clinic.pk), actor


def _active_service(clinic_id: UUID, service_id: str) -> Service | None:
    try:
        parsed = UUID(service_id)
    except ValueError, TypeError:
        return None
    return (
        Service.objects.for_clinic(clinic_id).filter(pk=parsed, is_active=True).first()
    )


# ---------------------------------------------------------------------------
# Agenda / appointments (8.8.2)
# ---------------------------------------------------------------------------


@login_required
@require_GET
def appointment_list(request: HttpRequest) -> HttpResponse:
    """Render the actor's authorized appointments as a textual agenda."""
    clinic_id, actor = _clinic_and_actor(request)
    status_filter = request.GET.get("status", "")
    appointments = appointments_visible_to(
        clinic_id=clinic_id, actor=actor, status=status_filter
    )
    today = timezone.localdate()
    can_manage = any(
        has_active_clinic_role(
            clinic_id=clinic_id, user_id=actor.pk, role=role, on_date=today
        )
        for role in ("clinic_admin", "administrative_staff", "therapist")
    )
    return TemplateResponse(
        request,
        "scheduling/appointment_list.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Agenda"),
            "appointments": appointments,
            "selected_status": status_filter,
            "can_manage": can_manage,
            "non_emergency_notice": NON_EMERGENCY_NOTICE,
        },
    )


@login_required
@require_GET
def appointment_calendar(request: HttpRequest) -> HttpResponse:
    """Render a weekly calendar grid plus an equivalent textual list (8.8.1.3)."""
    clinic_id, actor = _clinic_and_actor(request)
    today = timezone.localdate()
    raw_date = request.GET.get("date", "")
    if raw_date:
        try:
            today = date.fromisoformat(raw_date)
        except ValueError:
            today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    days = [week_start + timedelta(days=offset) for offset in range(7)]

    from_at = timezone.make_aware(datetime.combine(days[0], time.min))
    to_at = timezone.make_aware(
        datetime.combine(days[-1] + timedelta(days=1), time.min)
    )
    appointments = appointments_visible_to(
        clinic_id=clinic_id, actor=actor, from_at=from_at, to_at=to_at
    )
    by_day: dict[date, list[Appointment]] = {day: [] for day in days}
    for appointment in appointments:
        local_day = timezone.localtime(appointment.start_at).date()
        if local_day in by_day:
            by_day[local_day].append(appointment)
    week_days = [(day, by_day[day]) for day in days]

    return TemplateResponse(
        request,
        "scheduling/partials/calendar_grid.html"
        if request.headers.get("HX-Request")
        else "scheduling/appointment_calendar.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Agenda semanal"),
            "days": days,
            "week_days": week_days,
            "appointments": appointments,
            "week_start": week_start,
            "prev_week": (week_start - timedelta(days=7)).isoformat(),
            "next_week": (week_start + timedelta(days=7)).isoformat(),
            "can_manage": any(
                has_active_clinic_role(
                    clinic_id=clinic_id, user_id=actor.pk, role=role, on_date=today
                )
                for role in ("clinic_admin", "administrative_staff", "therapist")
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def appointment_reschedule(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    """Propose a new slot for one appointment."""
    clinic_id, actor = _clinic_and_actor(request)
    form = AppointmentRescheduleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        appointment = (
            Appointment.objects.for_clinic(clinic_id).filter(pk=appointment_id).first()
        )
        if appointment is None:
            raise PermissionDenied
        start_at = form.cleaned_data["start_at"]
        end_at = start_at + timedelta(minutes=appointment.service.duration_minutes)
        request_reschedule(
            clinic_id=clinic_id,
            actor=actor,
            appointment_id=appointment_id,
            start_at=start_at,
            end_at=end_at,
            request_id=_request_uuid(),
        )
        return HttpResponseRedirect(reverse("appointment_list"))
    return TemplateResponse(
        request,
        "scheduling/appointment_reschedule.html",
        {
            "layout_template": "layouts/vertical.html",
            "page_title": _("Remarcar consulta"),
            "form": form,
            "submit_label": _("Propor novo horário"),
        },
    )


@login_required
@require_POST
def appointment_confirm(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    clinic_id, actor = _clinic_and_actor(request)
    confirm_appointment(
        clinic_id=clinic_id,
        actor=actor,
        appointment_id=appointment_id,
        request_id=_request_uuid(),
    )
    return HttpResponseRedirect(reverse("appointment_list"))


@login_required
@require_POST
def appointment_cancel(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    clinic_id, actor = _clinic_and_actor(request)
    form = AppointmentActionForm(request.POST or None)
    reason = form["reason"].value() if "reason" in form.data else ""
    cancel_appointment(
        clinic_id=clinic_id,
        actor=actor,
        appointment_id=appointment_id,
        reason=reason or "",
        request_id=_request_uuid(),
    )
    return HttpResponseRedirect(reverse("appointment_list"))


@login_required
@require_POST
def appointment_complete(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    clinic_id, actor = _clinic_and_actor(request)
    complete_appointment(
        clinic_id=clinic_id,
        actor=actor,
        appointment_id=appointment_id,
        request_id=_request_uuid(),
    )
    return HttpResponseRedirect(reverse("appointment_list"))


@login_required
@require_POST
def appointment_no_show(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    clinic_id, actor = _clinic_and_actor(request)
    record_no_show(
        clinic_id=clinic_id,
        actor=actor,
        appointment_id=appointment_id,
        request_id=_request_uuid(),
    )
    return HttpResponseRedirect(reverse("appointment_list"))
