"""Transactional services for professional availability management."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from audit.services import record_audit_event
from clinics.policies import has_active_clinic_role
from clinics.selectors import clinic_operating_hours
from clinics.services import authorized_active_clinic, lock_clinic_for_update
from core.services import Service as Service

from .models import (
    AvailabilityOverride,
    AvailabilityPattern,
    Room,
    ScheduleBlock,
    Unit,
)
from .operating_hours import WEEKDAY_LABELS, has_configured_hours, weekday_intervals

__all__ = [
    "Service",
    "create_availability_block",
    "create_availability_override",
    "create_availability_pattern",
    "create_availability_patterns",
    "deactivate_availability_pattern",
    "update_availability_pattern",
]

DEFAULT_TIMEZONE_NAME = "America/Sao_Paulo"


def _require_admin(*, clinic_id: UUID, actor: AbstractBaseUser) -> None:
    authorized_active_clinic(clinic_id=clinic_id, actor=actor, action="clinic.manage")


def _require_active_therapist(*, clinic_id: UUID, professional_id: UUID) -> None:
    from django.utils import timezone

    if not has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=professional_id,
        role="therapist",
        on_date=timezone.localdate(),
    ):
        raise ValidationError(
            _("O profissional não possui vínculo ativo como terapeuta nesta clínica.")
        )


def _active_unit(*, clinic_id: UUID, unit_id: UUID) -> Unit:
    unit = Unit.infrastructure_objects.filter(pk=unit_id, clinic_id=clinic_id).first()
    if unit is None:
        raise ValidationError(_("Unidade não encontrada."))
    if not unit.is_active:
        raise ValidationError(_("A unidade está inativa."))
    return unit


def _validate_room(*, clinic_id: UUID, unit_id: UUID, room_id: UUID | None) -> None:
    """A room, when given, must be an active room of that unit and clinic."""
    if room_id is None:
        return
    found = Room.infrastructure_objects.filter(
        pk=room_id, clinic_id=clinic_id, unit_id=unit_id, is_active=True
    ).exists()
    if not found:
        raise ValidationError(_("Sala não encontrada nesta unidade."))


def _validate_window(
    *,
    weekday: int,
    start_time: time,
    end_time: time,
    valid_from: date,
    valid_until: date | None,
) -> None:
    if not 0 <= weekday <= 6:
        raise ValidationError(_("Dia da semana inválido."))
    if start_time >= end_time:
        raise ValidationError(_("O horário inicial deve ser anterior ao final."))
    if valid_until is not None and valid_until < valid_from:
        raise ValidationError(_("A data final não pode ser anterior à inicial."))


def _validate_operating_hours(
    *, clinic_id: UUID, unit: Unit, weekday: int, start_time: time, end_time: time
) -> None:
    """Keep the window inside the clinic's weekly operating hours.

    Nothing is enforced while the clinic has not defined its hours. Operating
    hours are wall-clock times in the clinic's timezone, so a unit in another
    timezone cannot be compared without guessing and is not checked.
    """
    hours = clinic_operating_hours(clinic_id=clinic_id)
    if hours is None or not has_configured_hours(hours.weekly_hours):
        return
    if (unit.timezone_name or DEFAULT_TIMEZONE_NAME) != hours.timezone_name:
        return
    intervals = weekday_intervals(hours.weekly_hours, weekday)
    day = WEEKDAY_LABELS[weekday]
    if not intervals:
        raise ValidationError(
            gettext("A clínica não funciona em %(day)s.") % {"day": day}
        )
    if any(opens <= start_time and end_time <= closes for opens, closes in intervals):
        return
    raise ValidationError(
        gettext(
            "O horário %(start)s–%(end)s fica fora do funcionamento da clínica "
            "em %(day)s (%(hours)s)."
        )
        % {
            "start": f"{start_time:%H:%M}",
            "end": f"{end_time:%H:%M}",
            "day": day,
            "hours": ", ".join(f"{a:%H:%M}–{b:%H:%M}" for a, b in intervals),
        }
    )


def _assert_no_overlap(
    *,
    clinic_id: UUID,
    professional_id: UUID,
    weekday: int,
    start_time: time,
    end_time: time,
    valid_from: date,
    valid_until: date | None,
    exclude_id: UUID | None = None,
) -> None:
    """One professional cannot have two windows at once, in any unit."""
    clashes = AvailabilityPattern.infrastructure_objects.filter(
        clinic_id=clinic_id,
        professional_id=professional_id,
        weekday=weekday,
        is_active=True,
        start_time__lt=end_time,
        end_time__gt=start_time,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from))
    if valid_until is not None:
        clashes = clashes.filter(valid_from__lte=valid_until)
    if exclude_id is not None:
        clashes = clashes.exclude(pk=exclude_id)
    clash = clashes.select_related("unit").order_by("start_time", "pk").first()
    if clash is not None:
        raise ValidationError(
            gettext(
                "Este horário se sobrepõe a outro horário do profissional em "
                "%(day)s, das %(start)s às %(end)s, na unidade %(unit)s."
            )
            % {
                "day": WEEKDAY_LABELS[weekday],
                "start": f"{clash.start_time:%H:%M}",
                "end": f"{clash.end_time:%H:%M}",
                "unit": clash.unit.name,
            }
        )


@transaction.atomic
def create_availability_pattern(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    professional_id: UUID,
    unit_id: UUID,
    room_id: UUID | None,
    weekday: int,
    start_time: time,
    end_time: time,
    valid_from: date,
    valid_until: date | None,
    request_id: UUID,
) -> AvailabilityPattern:
    """Create one recurring weekly availability window for a professional."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    _require_active_therapist(clinic_id=clinic_id, professional_id=professional_id)
    unit = _active_unit(clinic_id=clinic_id, unit_id=unit_id)
    _validate_room(clinic_id=clinic_id, unit_id=unit.pk, room_id=room_id)
    _validate_window(
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    _validate_operating_hours(
        clinic_id=clinic_id,
        unit=unit,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )
    _assert_no_overlap(
        clinic_id=clinic_id,
        professional_id=professional_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    pattern = AvailabilityPattern.infrastructure_objects.create(
        clinic_id=clinic_id,
        professional_id=professional_id,
        unit_id=unit.pk,
        room_id=room_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="create",
        resource_type="availability_pattern",
        resource_id=str(pattern.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return pattern


@transaction.atomic
def create_availability_patterns(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    professional_id: UUID,
    unit_id: UUID,
    room_id: UUID | None,
    weekdays: Sequence[int],
    start_time: time,
    end_time: time,
    valid_from: date,
    valid_until: date | None,
    request_id: UUID,
) -> list[AvailabilityPattern]:
    """Create the same window on several weekdays, all or nothing."""
    days = sorted(set(weekdays))
    if not days:
        raise ValidationError(_("Escolha ao menos um dia da semana."))
    return [
        create_availability_pattern(
            clinic_id=clinic_id,
            actor=actor,
            professional_id=professional_id,
            unit_id=unit_id,
            room_id=room_id,
            weekday=day,
            start_time=start_time,
            end_time=end_time,
            valid_from=valid_from,
            valid_until=valid_until,
            request_id=request_id,
        )
        for day in days
    ]


@transaction.atomic
def update_availability_pattern(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    pattern_id: UUID,
    unit_id: UUID,
    room_id: UUID | None,
    weekday: int,
    start_time: time,
    end_time: time,
    valid_from: date,
    valid_until: date | None,
    request_id: UUID,
) -> AvailabilityPattern:
    """Change one window; the professional stays the same.

    Consultations already booked are not touched: only the slots offered from
    now on follow the new window.
    """
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    pattern = (
        AvailabilityPattern.infrastructure_objects.select_for_update()
        .filter(pk=pattern_id, clinic_id=clinic_id)
        .first()
    )
    if pattern is None:
        raise PermissionDenied
    if not pattern.is_active:
        raise ValidationError(_("Este horário foi removido."))
    _require_active_therapist(
        clinic_id=clinic_id, professional_id=pattern.professional_id
    )
    unit = _active_unit(clinic_id=clinic_id, unit_id=unit_id)
    _validate_room(clinic_id=clinic_id, unit_id=unit.pk, room_id=room_id)
    _validate_window(
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    _validate_operating_hours(
        clinic_id=clinic_id,
        unit=unit,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )
    _assert_no_overlap(
        clinic_id=clinic_id,
        professional_id=pattern.professional_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_until=valid_until,
        exclude_id=pattern.pk,
    )
    pattern.unit_id = unit.pk
    pattern.room_id = room_id
    pattern.weekday = weekday
    pattern.start_time = start_time
    pattern.end_time = end_time
    pattern.valid_from = valid_from
    pattern.valid_until = valid_until
    pattern.save(
        update_fields=(
            "unit",
            "room",
            "weekday",
            "start_time",
            "end_time",
            "valid_from",
            "valid_until",
            "updated_at",
        )
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="update",
        resource_type="availability_pattern",
        resource_id=str(pattern.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return pattern


@transaction.atomic
def deactivate_availability_pattern(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    pattern_id: UUID,
    request_id: UUID,
) -> AvailabilityPattern:
    """Deactivate one recurring availability window."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    pattern = (
        AvailabilityPattern.infrastructure_objects.select_for_update()
        .filter(pk=pattern_id, clinic_id=clinic_id)
        .first()
    )
    if pattern is None:
        raise PermissionDenied
    pattern.is_active = False
    pattern.save(update_fields=("is_active", "updated_at"))
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="update",
        resource_type="availability_pattern",
        resource_id=str(pattern.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return pattern


@transaction.atomic
def create_availability_override(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    professional_id: UUID,
    unit_id: UUID,
    room_id: UUID | None,
    override_date: date,
    start_time: time | None,
    end_time: time | None,
    available: bool,
    reason: str,
    request_id: UUID,
) -> AvailabilityOverride:
    """Create one one-off availability exception for a specific date."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    _require_active_therapist(clinic_id=clinic_id, professional_id=professional_id)
    unit = Unit.infrastructure_objects.filter(pk=unit_id, clinic_id=clinic_id).first()
    if unit is None:
        raise ValidationError(_("Unidade não encontrada."))
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise ValidationError(_("O horário inicial deve ser anterior ao final."))
    override = AvailabilityOverride.infrastructure_objects.create(
        clinic_id=clinic_id,
        professional_id=professional_id,
        unit_id=unit.pk,
        room_id=room_id,
        date=override_date,
        start_time=start_time,
        end_time=end_time,
        available=available,
        reason=reason.strip(),
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="create",
        resource_type="availability_override",
        resource_id=str(override.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return override


@transaction.atomic
def create_availability_block(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    professional_id: UUID,
    unit_id: UUID,
    room_id: UUID | None,
    start_at: datetime,
    end_at: datetime,
    reason: str,
    request_id: UUID,
) -> ScheduleBlock:
    """Create one non-recurring blocking window that removes availability."""
    _require_admin(clinic_id=clinic_id, actor=actor)
    lock_clinic_for_update(clinic_id=clinic_id)
    _require_active_therapist(clinic_id=clinic_id, professional_id=professional_id)
    unit = Unit.infrastructure_objects.filter(pk=unit_id, clinic_id=clinic_id).first()
    if unit is None:
        raise ValidationError(_("Unidade não encontrada."))
    if end_at <= start_at:
        raise ValidationError(_("O horário final deve ser posterior ao inicial."))
    block = ScheduleBlock.infrastructure_objects.create(
        clinic_id=clinic_id,
        professional_id=professional_id,
        unit_id=unit.pk,
        room_id=room_id,
        start_at=start_at,
        end_at=end_at,
        reason=reason.strip(),
    )
    record_audit_event(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        action="create",
        resource_type="schedule_block",
        resource_id=str(block.pk),
        outcome="success",
        request_id=request_id,
        network_origin=None,
    )
    return block
