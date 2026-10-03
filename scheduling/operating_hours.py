"""Pure operating-hours helpers used to gate out-of-hours responses."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

WEEKDAY_KEYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# Same order as WEEKDAY_KEYS and as ``datetime.weekday()`` (Monday is 0).
WEEKDAY_LABELS = (
    _("Segunda-feira"),
    _("Terça-feira"),
    _("Quarta-feira"),
    _("Quinta-feira"),
    _("Sexta-feira"),
    _("Sábado"),
    _("Domingo"),
)

DEFAULT_OUT_OF_HOURS_NOTICE = (
    "Estamos fora do horário de atendimento. Sua mensagem foi registrada e "
    "será respondida dentro do horário comercial. Este canal não atende "
    "emergências."
)


def _local_time(value: datetime, tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.get_current_timezone()
    return value.astimezone(tz)


def within_operating_hours(
    *, weekly_hours: dict[str, list[dict[str, str]]], now: datetime, tz_name: str
) -> bool:
    """Return whether `now` falls inside the configured weekly intervals."""
    local = _local_time(now, tz_name)
    key = WEEKDAY_KEYS[local.weekday()]
    current = local.strftime("%H:%M")
    for interval in weekly_hours.get(key, []):
        start = interval.get("start", "")
        end = interval.get("end", "")
        if start and end and start <= current < end:
            return True
    return False


def out_of_hours_response(
    *,
    weekly_hours: dict[str, list[dict[str, str]]],
    now: datetime,
    tz_name: str,
    instructions: str,
) -> str | None:
    """Return the configured out-of-hours text, or None when inside hours."""
    if within_operating_hours(weekly_hours=weekly_hours, now=now, tz_name=tz_name):
        return None
    return instructions.strip() or DEFAULT_OUT_OF_HOURS_NOTICE


def has_configured_hours(weekly_hours: dict[str, list[dict[str, str]]]) -> bool:
    """Return whether the clinic defined at least one opening interval.

    A configuration with every day closed is how an unfinished setup looks, so
    it must not forbid every availability window.
    """
    return any(weekly_hours.get(key) for key in WEEKDAY_KEYS)


def weekday_intervals(
    weekly_hours: dict[str, list[dict[str, str]]], weekday: int
) -> list[tuple[time, time]]:
    """Parse the opening intervals of one weekday; malformed entries are ignored."""
    intervals: list[tuple[time, time]] = []
    for interval in weekly_hours.get(WEEKDAY_KEYS[weekday], []):
        try:
            start = time.fromisoformat(interval.get("start", ""))
            end = time.fromisoformat(interval.get("end", ""))
        except ValueError:
            continue
        if start < end:
            intervals.append((start, end))
    return sorted(intervals)
