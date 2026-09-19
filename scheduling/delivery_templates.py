"""Neutral reminder and message delivery text with no sensitive content.

These templates accept only non-clinical inputs (service name, appointment
time, sender name) so that a lock screen can never reveal mood, responses,
exercises or any health condition.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone, translation
from django.utils.translation import gettext as _


def _local_time(value: datetime, tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.get_current_timezone()
    return value.astimezone(tz)


def appointment_reminder_message(
    *, service_name: str, start_at: datetime, tz_name: str, language: str | None = None
) -> str:
    """Return a neutral appointment reminder with date/time only."""
    local = _local_time(start_at, tz_name)
    lang = language or translation.get_language() or "pt-br"
    with translation.override(lang):
        date_str = local.strftime("%d/%m/%Y")
        time_str = local.strftime("%H:%M")
        return _(
            "Lembrete: sua consulta de %(service_name)s está marcada para "
            "%(date)s às %(time)s."
        ) % {
            "service_name": service_name,
            "date": date_str,
            "time": time_str,
        }


def new_message_notification_message(
    *, sender_name: str, language: str | None = None
) -> str:
    """Return a neutral new-message notice without reproducing message content."""
    lang = language or translation.get_language() or "pt-br"
    with translation.override(lang):
        return _("Você tem uma nova mensagem de %(sender_name)s na plataforma.") % {
            "sender_name": sender_name,
        }
