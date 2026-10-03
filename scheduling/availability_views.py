"""Staff screens for weekly availability and the preview of what patients see."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from people.selectors import professional_display_names

from .availability_services import (
    create_availability_patterns,
    deactivate_availability_pattern,
    update_availability_pattern,
)
from .models import AvailabilityPattern
from .operating_hours import WEEKDAY_LABELS
from .selectors import (
    active_rooms_for_clinic,
    active_services_for_clinic,
    active_units_for_clinic,
    availability_pattern_for_clinic,
    availability_patterns_for_clinic,
    schedulable_professionals,
)
from .services import free_slots
from .setup_common import private_no_store, request_uuid, setup_context, setup_page
from .setup_forms import (
    AvailabilityCreateForm,
    AvailabilityUpdateForm,
    ConfirmForm,
    PreviewFilterForm,
)

__all__ = [
    "availability_create",
    "availability_list",
    "availability_preview",
    "availability_remove",
    "availability_update",
]

PREVIEW_DAYS = 7
MAX_PREVIEW_PAIRS = 20


def _list_url() -> str:
    return reverse("scheduling:availability_list")


def _breadcrumb() -> list[tuple[str, str]]:
    return [(_("Disponibilidade"), _list_url())]


def _professional_name(names: dict[UUID, str], user_id: UUID) -> str:
    return names.get(user_id) or _("Profissional sem perfil")


def _pattern_state(pattern: AvailabilityPattern, today: date) -> str:
    if pattern.valid_until is not None and pattern.valid_until < today:
        return "expired"
    if pattern.valid_from > today:
        return "scheduled"
    return "current"


def _window(pattern: AvailabilityPattern) -> str:
    return f"{pattern.start_time:%H:%M}–{pattern.end_time:%H:%M}"


@dataclass(frozen=True, slots=True)
class _FormChoices:
    units: list[tuple[str, str]]
    rooms: list[tuple[str, str]]
    room_units: dict[str, str]


def _form_choices(clinic_id: UUID) -> _FormChoices:
    units = active_units_for_clinic(clinic_id=clinic_id)
    unit_ids = {unit.pk for unit in units}
    rooms = [
        room
        for room in active_rooms_for_clinic(clinic_id=clinic_id)
        if room.unit_id in unit_ids
    ]
    return _FormChoices(
        units=[(str(unit.pk), unit.name) for unit in units],
        rooms=[(str(room.pk), f"{room.unit.name} — {room.name}") for room in rooms],
        room_units={str(room.pk): str(room.unit_id) for room in rooms},
    )


def _form_page(
    request: HttpRequest,
    *,
    title: str,
    form: Any,
    submit_label: str,
    lead: str = "",
    danger: bool = False,
) -> HttpResponse:
    return setup_page(
        request,
        "scheduling/setup_form.html",
        {
            "page_title": title,
            "form": form,
            "submit_label": submit_label,
            "cancel_url": _list_url(),
            "lead": lead,
            "danger": danger,
            "breadcrumb": _breadcrumb(),
        },
    )


# ── Lista ───────────────────────────────────────────────────────────────────


@login_required
@require_GET
@private_no_store
def availability_list(request: HttpRequest) -> HttpResponse:
    """Weekly windows grouped by professional; read-only for non-administrators."""
    context = setup_context(request)
    patterns = availability_patterns_for_clinic(clinic_id=context.clinic_id)
    names = professional_display_names(
        clinic_id=context.clinic_id,
        user_ids={pattern.professional_id for pattern in patterns},
    )
    today = timezone.localdate()
    grouped: dict[UUID, list[dict[str, Any]]] = {}
    for pattern in patterns:
        grouped.setdefault(pattern.professional_id, []).append(
            {
                "pattern": pattern,
                "weekday_label": WEEKDAY_LABELS[pattern.weekday],
                "window": _window(pattern),
                "state": _pattern_state(pattern, today),
            }
        )
    groups = sorted(
        (
            {"name": _professional_name(names, user_id), "rows": rows}
            for user_id, rows in grouped.items()
        ),
        key=lambda group: str(group["name"]).casefold(),
    )
    return setup_page(
        request,
        "scheduling/availability_list.html",
        {
            "page_title": _("Disponibilidade dos profissionais"),
            "groups": groups,
            "pattern_count": len(patterns),
            "can_manage": context.can_manage,
        },
    )


# ── Criar, editar e remover ─────────────────────────────────────────────────


@login_required
@require_http_methods(["GET", "POST"])
@private_no_store
def availability_create(request: HttpRequest) -> HttpResponse:
    """Create one window on one or more weekdays for a professional."""
    context = setup_context(request, manage=True)
    choices = _form_choices(context.clinic_id)
    professionals = [
        (str(user_id), name)
        for user_id, name in schedulable_professionals(
            clinic_id=context.clinic_id, actor=context.actor
        )
    ]
    form = AvailabilityCreateForm(
        request.POST or None,
        professional_choices=professionals,
        unit_choices=choices.units,
        room_choices=choices.rooms,
        room_units=choices.room_units,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            create_availability_patterns(
                clinic_id=context.clinic_id,
                actor=context.actor,
                professional_id=UUID(data["professional"]),
                unit_id=UUID(data["unit"]),
                room_id=UUID(data["room"]) if data["room"] else None,
                weekdays=[int(day) for day in data["weekdays"]],
                start_time=data["start_time"],
                end_time=data["end_time"],
                valid_from=data["valid_from"],
                valid_until=data["valid_until"],
                request_id=request_uuid(),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                _("Horários salvos. Confira a prévia dos horários livres."),
            )
            return HttpResponseRedirect(_list_url())
    return _form_page(
        request,
        title=_("Novo horário de atendimento"),
        form=form,
        submit_label=_("Salvar horário"),
        lead=_(
            "O horário precisa caber no funcionamento da clínica e não pode "
            "se sobrepor a outro horário do mesmo profissional."
        ),
    )


def _pattern_or_denied(clinic_id: UUID, pattern_id: UUID) -> AvailabilityPattern:
    pattern = availability_pattern_for_clinic(
        clinic_id=clinic_id, pattern_id=pattern_id
    )
    if pattern is None or not pattern.is_active:
        raise PermissionDenied
    return pattern


@login_required
@require_http_methods(["GET", "POST"])
@private_no_store
def availability_update(request: HttpRequest, pattern_id: UUID) -> HttpResponse:
    """Edit one window (the professional stays; remove and recreate to change)."""
    context = setup_context(request, manage=True)
    pattern = _pattern_or_denied(context.clinic_id, pattern_id)
    choices = _form_choices(context.clinic_id)
    form = AvailabilityUpdateForm(
        request.POST or None,
        initial={
            "unit": str(pattern.unit_id),
            "room": str(pattern.room_id) if pattern.room_id else "",
            "weekday": str(pattern.weekday),
            "start_time": pattern.start_time,
            "end_time": pattern.end_time,
            "valid_from": pattern.valid_from,
            "valid_until": pattern.valid_until,
        },
        unit_choices=choices.units,
        room_choices=choices.rooms,
        room_units=choices.room_units,
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            update_availability_pattern(
                clinic_id=context.clinic_id,
                actor=context.actor,
                pattern_id=pattern.pk,
                unit_id=UUID(data["unit"]),
                room_id=UUID(data["room"]) if data["room"] else None,
                weekday=int(data["weekday"]),
                start_time=data["start_time"],
                end_time=data["end_time"],
                valid_from=data["valid_from"],
                valid_until=data["valid_until"],
                request_id=request_uuid(),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, _("Horário atualizado. Confira a prévia dos horários livres.")
            )
            return HttpResponseRedirect(_list_url())
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={pattern.professional_id}
    )
    return _form_page(
        request,
        title=_("Editar horário de atendimento"),
        form=form,
        submit_label=_("Salvar horário"),
        lead=_("Profissional: %(name)s.")
        % {"name": _professional_name(names, pattern.professional_id)},
    )


@login_required
@require_http_methods(["GET", "POST"])
@private_no_store
def availability_remove(request: HttpRequest, pattern_id: UUID) -> HttpResponse:
    """Ask for confirmation, then take one window out of the schedule."""
    context = setup_context(request, manage=True)
    pattern = _pattern_or_denied(context.clinic_id, pattern_id)
    if request.method == "POST":
        deactivate_availability_pattern(
            clinic_id=context.clinic_id,
            actor=context.actor,
            pattern_id=pattern.pk,
            request_id=request_uuid(),
        )
        messages.success(request, _("Horário removido."))
        return HttpResponseRedirect(_list_url())
    names = professional_display_names(
        clinic_id=context.clinic_id, user_ids={pattern.professional_id}
    )
    return _form_page(
        request,
        title=_("Remover horário de atendimento"),
        form=ConfirmForm(),
        submit_label=_("Remover horário"),
        lead=_(
            "Remover o horário de %(name)s, %(day)s, das %(start)s às %(end)s? "
            "Os pacientes deixam de ver estes horários. Consultas já marcadas "
            "não são alteradas."
        )
        % {
            "name": _professional_name(names, pattern.professional_id),
            "day": WEEKDAY_LABELS[pattern.weekday],
            "start": f"{pattern.start_time:%H:%M}",
            "end": f"{pattern.end_time:%H:%M}",
        },
        danger=True,
    )


# ── Prévia dos horários livres ──────────────────────────────────────────────


def _selected_ids(
    form: PreviewFilterForm, *, default_service: UUID | None
) -> tuple[UUID | None, UUID | None]:
    """Resolve the filter; an invalid or foreign choice falls back to the default."""
    if form.is_bound and form.is_valid():
        service = form.cleaned_data["service"]
        professional = form.cleaned_data["professional"]
        return UUID(service), UUID(professional) if professional else None
    return default_service, None


def _slot_blocks(
    *,
    clinic_id: UUID,
    service_id: UUID,
    professional_filter: UUID | None,
    patterns: list[AvailabilityPattern],
    names: dict[UUID, str],
) -> tuple[list[dict[str, Any]], bool]:
    units = {unit.pk: unit for unit in active_units_for_clinic(clinic_id=clinic_id)}
    pairs = sorted(
        {
            (pattern.professional_id, pattern.unit_id)
            for pattern in patterns
            if pattern.unit_id in units
            and (
                professional_filter is None
                or pattern.professional_id == professional_filter
            )
        },
        key=lambda pair: (
            _professional_name(names, pair[0]).casefold(),
            units[pair[1]].name.casefold(),
            str(pair),
        ),
    )
    truncated = len(pairs) > MAX_PREVIEW_PAIRS
    today = timezone.localdate()
    last_day = today + timedelta(days=PREVIEW_DAYS - 1)
    now = timezone.now()
    blocks: list[dict[str, Any]] = []
    for professional_id, unit_id in pairs[:MAX_PREVIEW_PAIRS]:
        slots = [
            slot
            for slot in free_slots(
                clinic_id=clinic_id,
                professional_id=professional_id,
                unit_id=unit_id,
                service_id=service_id,
                from_date=today,
                to_date=last_day,
            )
            if slot > now
        ]
        by_day: dict[date, list[str]] = {}
        for slot in slots:
            by_day.setdefault(slot.date(), []).append(f"{slot:%H:%M}")
        blocks.append(
            {
                "professional": _professional_name(names, professional_id),
                "unit": units[unit_id].name,
                "total": len(slots),
                "days": [
                    {
                        "date": today + timedelta(days=offset),
                        "slots": by_day.get(today + timedelta(days=offset), []),
                    }
                    for offset in range(PREVIEW_DAYS)
                ],
            }
        )
    return blocks, truncated


@login_required
@require_GET
@private_no_store
def availability_preview(request: HttpRequest) -> HttpResponse:
    """Free slots of the next seven days, as the app computes them for patients."""
    context = setup_context(request)
    services = active_services_for_clinic(clinic_id=context.clinic_id)
    patterns = availability_patterns_for_clinic(clinic_id=context.clinic_id)
    names = professional_display_names(
        clinic_id=context.clinic_id,
        user_ids={pattern.professional_id for pattern in patterns},
    )
    professional_choices = sorted(
        {
            (
                str(pattern.professional_id),
                _professional_name(names, pattern.professional_id),
            )
            for pattern in patterns
        },
        key=lambda item: (item[1].casefold(), item[0]),
    )
    form = PreviewFilterForm(
        request.GET or None,
        service_choices=[(str(service.pk), service.name) for service in services],
        professional_choices=professional_choices,
    )
    service_id, professional_id = _selected_ids(
        form, default_service=services[0].pk if services else None
    )
    blocks: list[dict[str, Any]] = []
    truncated = False
    if service_id is not None and patterns:
        blocks, truncated = _slot_blocks(
            clinic_id=context.clinic_id,
            service_id=service_id,
            professional_filter=professional_id,
            patterns=patterns,
            names=names,
        )
    selected_service = next((s for s in services if s.pk == service_id), None)
    return setup_page(
        request,
        "scheduling/availability_preview.html",
        {
            "page_title": _("Prévia dos horários livres"),
            "form": form,
            "has_services": bool(services),
            "has_patterns": bool(patterns),
            "blocks": blocks,
            "truncated": truncated,
            "selected_service": selected_service,
            "preview_days": PREVIEW_DAYS,
            "can_manage": context.can_manage,
        },
    )
