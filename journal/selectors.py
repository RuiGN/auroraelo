"""Read selectors for the journal domain."""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from clinics.policies import has_active_clinic_role
from core.selectors import Selector as Selector
from people.selectors import linked_patients_for_therapist, patient_profile_for_user

from .models import (
    DEFAULT_CHECKIN_QUESTIONS,
    DailyCheckIn,
    HumanTriageItem,
    JournalAccessRequest,
    JournalEntry,
)
from .policies import therapist_may_read_patient_diary

__all__ = [
    "ACCESS_EXPIRED",
    "ACCESS_GRANTED",
    "ACCESS_NONE",
    "ACCESS_PENDING",
    "ACCESS_REJECTED",
    "ACCESS_REVOKED",
    "CHECKIN_SCALE_KEYS",
    "RELEASE_GRANTED",
    "RELEASE_SHARED",
    "STAFF_DIARY_PERIODS",
    "AccessRequestRow",
    "CalendarDayData",
    "CalendarMonthData",
    "CheckInDayRow",
    "CheckInSeries",
    "ConfirmationEntry",
    "QuestionSeries",
    "Selector",
    "StaffDiary",
    "StaffEntryRow",
    "access_request_state",
    "patient_checkins",
    "patient_journal_calendar_data",
    "patient_journal_entries",
    "patient_pending_access_requests",
    "pending_triage_for_therapist",
    "therapist_confirmation_entry",
    "therapist_patient_checkin_series",
    "therapist_patient_diary",
    "therapist_visible_checkins",
    "therapist_visible_journal_entries",
]

MONTH_NAMES_PT_BR = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

MOOD_LABELS = {
    1: "Muito mal",
    2: "Mal",
    3: "Neutro",
    4: "Bem",
    5: "Muito bem",
}

MOOD_CSS_CLASSES = {
    1: "mood-very-low",
    2: "mood-low",
    3: "mood-neutral",
    4: "mood-good",
    5: "mood-very-good",
}


@dataclass(frozen=True, slots=True)
class CalendarDayData:
    """One day's visual and accessible data in the emotional calendar."""

    date: date
    day_number: int
    is_current_month: bool
    is_today: bool
    entry_count: int
    dominant_mood: int | None
    dominant_mood_label: str
    mood_class: str
    accessible_label: str


@dataclass(frozen=True, slots=True)
class CalendarMonthData:
    """One month matrix for the emotional calendar with navigation metadata."""

    year: int
    month: int
    month_name: str
    previous_year: int
    previous_month: int
    next_year: int
    next_month: int
    days_header: Sequence[str]
    weeks: Sequence[Sequence[CalendarDayData]]
    legend: Sequence[tuple[int, str, str]]
    text_summary_rows: Sequence[tuple[str, str, int]]


def patient_journal_entries(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    period: str = "",
    emotion: str = "",
    mood: int | None = None,
) -> list[JournalEntry]:
    """Return filtered patient diary records in reverse chronological order."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []

    queryset = JournalEntry.objects.for_clinic(clinic_id).filter(
        patient_profile_id=profile.pk
    )

    today = timezone.localdate()
    if period == "7d":
        since = timezone.make_aware(
            datetime.combine(today - timedelta(days=7), time.min)
        )
        queryset = queryset.filter(created_at__gte=since)
    elif period == "30d":
        since = timezone.make_aware(
            datetime.combine(today - timedelta(days=30), time.min)
        )
        queryset = queryset.filter(created_at__gte=since)
    elif period == "90d":
        since = timezone.make_aware(
            datetime.combine(today - timedelta(days=90), time.min)
        )
        queryset = queryset.filter(created_at__gte=since)

    if mood is not None and mood in JournalEntry.Mood.values:
        queryset = queryset.filter(mood=mood)

    entries = list(queryset.order_by("-created_at", "-id"))

    if emotion and emotion in JournalEntry.Emotion.values:
        entries = [entry for entry in entries if emotion in (entry.emotions or [])]

    return entries


def patient_journal_calendar_data(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    year: int | None = None,
    month: int | None = None,
) -> CalendarMonthData:
    """Generate the calendar matrix and textual equivalent for one month."""
    today = timezone.localdate()
    current_year = year or today.year
    current_month = month or today.month

    if current_month < 1 or current_month > 12:
        current_month = today.month
    if current_year < 2000 or current_year > 2100:
        current_year = today.year

    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    entries_by_date: dict[date, list[JournalEntry]] = {}

    if profile is not None:
        _, num_days = calendar.monthrange(current_year, current_month)
        start_date = date(current_year, current_month, 1) - timedelta(days=7)
        end_date = date(current_year, current_month, num_days) + timedelta(days=7)

        start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))

        entries = (
            JournalEntry.objects.for_clinic(clinic_id)
            .filter(
                patient_profile_id=profile.pk,
                created_at__gte=start_dt,
                created_at__lte=end_dt,
            )
            .order_by("created_at")
        )

        for entry in entries:
            entry_local_date = timezone.localtime(entry.created_at).date()
            entries_by_date.setdefault(entry_local_date, []).append(entry)

    cal = calendar.Calendar(firstweekday=6)  # Sunday as first day of week
    weeks_raw = cal.monthdatescalendar(current_year, current_month)

    weeks: list[list[CalendarDayData]] = []
    text_summary_rows: list[tuple[str, str, int]] = []

    for week_dates in weeks_raw:
        week_data: list[CalendarDayData] = []
        for d in week_dates:
            is_current_month = d.month == current_month
            is_today = d == today
            day_entries = entries_by_date.get(d, [])
            entry_count = len(day_entries)

            if entry_count > 0:
                dominant_mood = day_entries[-1].mood
                dominant_mood_label = MOOD_LABELS.get(dominant_mood, "Registrado")
                mood_class = MOOD_CSS_CLASSES.get(dominant_mood, "mood-neutral")
                accessible_label = (
                    f"{d.day} de {MONTH_NAMES_PT_BR[d.month]}: "
                    f"Humor {dominant_mood_label} ({dominant_mood}/5) — "
                    f"{entry_count} registro{'s' if entry_count > 1 else ''}"
                )
                if is_current_month:
                    formatted_date = f"{d.day:02d}/{d.month:02d}/{d.year}"
                    text_summary_rows.append(
                        (formatted_date, dominant_mood_label, entry_count)
                    )
            else:
                dominant_mood = None
                dominant_mood_label = "Sem registro"
                mood_class = "mood-empty"
                accessible_label = (
                    f"{d.day} de {MONTH_NAMES_PT_BR[d.month]}: Sem registros"
                )

            week_data.append(
                CalendarDayData(
                    date=d,
                    day_number=d.day,
                    is_current_month=is_current_month,
                    is_today=is_today,
                    entry_count=entry_count,
                    dominant_mood=dominant_mood,
                    dominant_mood_label=dominant_mood_label,
                    mood_class=mood_class,
                    accessible_label=accessible_label,
                )
            )
        weeks.append(week_data)

    if current_month == 1:
        prev_year = current_year - 1
        prev_month = 12
    else:
        prev_year = current_year
        prev_month = current_month - 1

    if current_month == 12:
        next_year = current_year + 1
        next_month = 1
    else:
        next_year = current_year
        next_month = current_month + 1

    legend = [
        (1, "Muito mal", "mood-very-low"),
        (2, "Mal", "mood-low"),
        (3, "Neutro", "mood-neutral"),
        (4, "Bem", "mood-good"),
        (5, "Muito bem", "mood-very-good"),
    ]

    return CalendarMonthData(
        year=current_year,
        month=current_month,
        month_name=f"{MONTH_NAMES_PT_BR[current_month]} de {current_year}",
        previous_year=prev_year,
        previous_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        days_header=("Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"),
        weeks=tuple(tuple(w) for w in weeks),
        legend=tuple(legend),
        text_summary_rows=tuple(text_summary_rows),
    )


def patient_pending_access_requests(
    *, clinic_id: UUID, actor: AbstractBaseUser
) -> list[JournalAccessRequest]:
    """Return pending therapist access requests for one patient."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    return list(
        JournalAccessRequest.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=profile.pk,
            status=JournalAccessRequest.Status.PENDING,
        )
        .select_related("therapist", "journal_entry")
        .order_by("-requested_at")
    )


def therapist_visible_journal_entries(
    *, clinic_id: UUID, therapist_id: UUID
) -> list[JournalEntry]:
    """Return only shareable or active granted records for therapist's patients.

    Private (Vermelho) records are NEVER returned under any circumstances.
    Confirmation-required (Amarelo) records are ONLY returned if there is an active,
    unexpired, non-revoked granted JournalAccessRequest for this therapist.
    """
    today = timezone.localdate()
    if not has_active_clinic_role(
        clinic_id=clinic_id,
        user_id=therapist_id,
        role="therapist",
        on_date=today,
    ):
        raise PermissionDenied
    linked = linked_patients_for_therapist(
        clinic_id=clinic_id, therapist_id=therapist_id, on_date=today
    )
    profile_ids = {row.patient_profile_id for row in linked}
    if not profile_ids:
        return []

    # 1. Shareable entries (Verde)
    shareable_entries = list(
        JournalEntry.objects.for_clinic(clinic_id).filter(
            patient_profile_id__in=profile_ids,
            visibility=JournalEntry.Visibility.SHAREABLE,
        )
    )

    # 2. Granted Yellow entries (Amarelo)
    now = timezone.now()
    granted_entry_ids = set(
        JournalAccessRequest.objects.for_clinic(clinic_id)
        .filter(
            therapist_id=therapist_id,
            status=JournalAccessRequest.Status.GRANTED,
            revoked_at__isnull=True,
        )
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
        .values_list("journal_entry_id", flat=True)
    )

    granted_yellow_entries: list[JournalEntry] = []
    if granted_entry_ids:
        granted_yellow_entries = list(
            JournalEntry.objects.for_clinic(clinic_id).filter(
                id__in=granted_entry_ids,
                patient_profile_id__in=profile_ids,
                visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
            )
        )

    all_visible = shareable_entries + granted_yellow_entries
    all_visible.sort(key=lambda e: (e.created_at, e.id), reverse=True)
    return all_visible


def patient_checkins(
    *,
    clinic_id: UUID,
    actor: AbstractBaseUser,
    since: datetime | None = None,
) -> list[DailyCheckIn]:
    """Return the patient's own submitted check-ins, newest first."""
    profile = patient_profile_for_user(clinic_id=clinic_id, user_id=actor.pk)
    if profile is None:
        return []
    queryset = DailyCheckIn.objects.for_clinic(clinic_id).filter(
        patient_profile_id=profile.pk,
        is_draft=False,
        submitted_at__isnull=False,
    )
    if since is not None:
        queryset = queryset.filter(submitted_at__gte=since)
    return list(queryset.order_by("-submitted_at", "-id"))


def therapist_visible_checkins(
    *,
    clinic_id: UUID,
    therapist_id: UUID,
    since: datetime | None = None,
) -> list[DailyCheckIn]:
    """Return only shareable check-ins for one therapist's linked patients.

    Private (Vermelho) and un-authorized Amarelo check-ins are never returned.
    """
    today = timezone.localdate()
    if not has_active_clinic_role(
        clinic_id=clinic_id, user_id=therapist_id, role="therapist", on_date=today
    ):
        raise PermissionDenied
    linked = linked_patients_for_therapist(
        clinic_id=clinic_id, therapist_id=therapist_id, on_date=today
    )
    profile_ids = {row.patient_profile_id for row in linked}
    if not profile_ids:
        return []
    queryset = DailyCheckIn.objects.for_clinic(clinic_id).filter(
        patient_profile_id__in=profile_ids,
        visibility=JournalEntry.Visibility.SHAREABLE,
        is_draft=False,
        submitted_at__isnull=False,
    )
    if since is not None:
        queryset = queryset.filter(submitted_at__gte=since)
    return list(queryset.order_by("-submitted_at", "-id"))


def pending_triage_for_therapist(
    *, clinic_id: UUID, therapist_id: UUID
) -> list[HumanTriageItem]:
    """Return pending human-review triage items for one therapist's patients."""
    today = timezone.localdate()
    if not has_active_clinic_role(
        clinic_id=clinic_id, user_id=therapist_id, role="therapist", on_date=today
    ):
        raise PermissionDenied
    linked = linked_patients_for_therapist(
        clinic_id=clinic_id, therapist_id=therapist_id, on_date=today
    )
    profile_ids = {row.patient_profile_id for row in linked}
    if not profile_ids:
        return []
    return list(
        HumanTriageItem.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id__in=profile_ids,
            status=HumanTriageItem.Status.PENDING,
        )
        .select_related("rule", "checkin")
        .order_by("-created_at")
    )


# ---------------------------------------------------------------------------
# Team view of what one patient shares in the app (diary and check-ins)
# ---------------------------------------------------------------------------

ACCESS_NONE = "none"
ACCESS_PENDING = JournalAccessRequest.Status.PENDING.value
ACCESS_GRANTED = JournalAccessRequest.Status.GRANTED.value
ACCESS_REJECTED = JournalAccessRequest.Status.REJECTED.value
ACCESS_REVOKED = JournalAccessRequest.Status.REVOKED.value
ACCESS_EXPIRED = JournalAccessRequest.Status.EXPIRED.value

RELEASE_SHARED = "shared"
RELEASE_GRANTED = "granted"

# Chosen period -> days back; None means the whole history.
STAFF_DIARY_PERIODS: dict[str, int | None] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "todos": None,
}
_REQUEST_HISTORY_LIMIT = 20

# The seven 1-5 questions of the default questionnaire, in presentation order.
CHECKIN_SCALE_KEYS: tuple[str, ...] = tuple(
    str(question["key"])
    for question in DEFAULT_CHECKIN_QUESTIONS
    if question["type"] == "scale_1_5"
)


@dataclass(frozen=True, slots=True)
class StaffEntryRow:
    """One diary record the team may read, and why it is readable."""

    entry: JournalEntry
    release: str  # RELEASE_SHARED or RELEASE_GRANTED
    granted_until: datetime | None


@dataclass(frozen=True, slots=True)
class ConfirmationEntry:
    """A confirmation-required record seen from the team: date and request state only.

    The content is never loaded here; it becomes readable only through an approved,
    unexpired request, and then it appears as a ``StaffEntryRow``.
    """

    entry_id: UUID
    created_at: datetime
    state: str  # ACCESS_* of the latest request made by this therapist
    can_request: bool


@dataclass(frozen=True, slots=True)
class AccessRequestRow:
    """One access request made by the therapist, with its derived state."""

    request: JournalAccessRequest
    state: str
    entry_created_at: datetime | None


@dataclass(frozen=True, slots=True)
class StaffDiary:
    """What the team sees of one patient's diary for one period."""

    entries: tuple[StaffEntryRow, ...]
    confirmation: tuple[ConfirmationEntry, ...]
    requests: tuple[AccessRequestRow, ...]


def access_request_state(request: JournalAccessRequest, *, now: datetime) -> str:
    """Return the displayed state: a lapsed validity reads as expired."""
    if request.status in {ACCESS_REVOKED, ACCESS_REJECTED, ACCESS_EXPIRED}:
        return str(request.status)
    if request.expires_at is not None and request.expires_at < now:
        return ACCESS_EXPIRED
    return str(request.status)


def _authorize_staff_diary(
    *, clinic_id: UUID, therapist_id: UUID, patient_profile_id: UUID
) -> None:
    """Defense in depth for selectors: same decision the views take."""
    if not therapist_may_read_patient_diary(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
    ):
        raise PermissionDenied


def _period_start(period: str, *, now: datetime) -> datetime | None:
    days = STAFF_DIARY_PERIODS.get(period, STAFF_DIARY_PERIODS["30d"])
    if days is None:
        return None
    first_day = timezone.localtime(now).date() - timedelta(days=days)
    return timezone.make_aware(datetime.combine(first_day, time.min))


def _latest_request_by_entry(
    requests: Sequence[JournalAccessRequest],
) -> dict[UUID, JournalAccessRequest]:
    """Keep the newest request per entry (the input is newest first)."""
    latest: dict[UUID, JournalAccessRequest] = {}
    for request in requests:
        latest.setdefault(request.journal_entry_id, request)
    return latest


def _confirmation_rows(
    *,
    clinic_id: UUID,
    therapist_id: UUID,
    patient_profile_id: UUID,
    now: datetime,
    since: datetime | None,
    entry_id: UUID | None = None,
) -> tuple[list[ConfirmationEntry], dict[UUID, JournalAccessRequest]]:
    """List confirmation-required records of the patient with this therapist's state."""
    entries = JournalEntry.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id,
        visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
    )
    if entry_id is not None:
        entries = entries.filter(pk=entry_id)
    if since is not None:
        entries = entries.filter(created_at__gte=since)
    # Only identity and date: the content of a "ask me first" record stays unread.
    pairs = list(entries.order_by("-created_at", "-id").values_list("pk", "created_at"))
    if not pairs:
        return [], {}
    requests = list(
        JournalAccessRequest.objects.for_clinic(clinic_id)
        .filter(
            therapist_id=therapist_id,
            patient_profile_id=patient_profile_id,
            journal_entry_id__in=[pk for pk, _ in pairs],
        )
        .order_by("-requested_at", "-id")
    )
    latest = _latest_request_by_entry(requests)
    rows: list[ConfirmationEntry] = []
    for pk, created_at in pairs:
        request = latest.get(pk)
        state = access_request_state(request, now=now) if request else ACCESS_NONE
        rows.append(
            ConfirmationEntry(
                entry_id=pk,
                created_at=created_at,
                state=state,
                # A refusal is final here: only the patient can release the record
                # again (by changing it in the app). Pending/active are not repeated.
                can_request=state in {ACCESS_NONE, ACCESS_EXPIRED, ACCESS_REVOKED},
            )
        )
    return rows, latest


def therapist_confirmation_entry(
    *, clinic_id: UUID, therapist_id: UUID, patient_profile_id: UUID, entry_id: UUID
) -> ConfirmationEntry | None:
    """Resolve one confirmation-required record of this patient, else ``None``.

    Private, shareable and foreign records all answer ``None``: the caller cannot
    tell them apart from a record that does not exist.
    """
    _authorize_staff_diary(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
    )
    rows, _latest = _confirmation_rows(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
        now=timezone.now(),
        since=None,
        entry_id=entry_id,
    )
    return rows[0] if rows else None


def therapist_patient_diary(
    *,
    clinic_id: UUID,
    therapist_id: UUID,
    patient_profile_id: UUID,
    period: str = "30d",
) -> StaffDiary:
    """Return what one linked patient shares with this therapist.

    Shareable (green) records, plus confirmation-required (yellow) records with an
    approved, unrevoked and unexpired request made by this same therapist. Private
    (red) records are never queried and are not counted anywhere.
    """
    _authorize_staff_diary(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
    )
    now = timezone.now()
    since = _period_start(period, now=now)

    shareable = JournalEntry.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id,
        visibility=JournalEntry.Visibility.SHAREABLE,
    )
    if since is not None:
        shareable = shareable.filter(created_at__gte=since)
    rows = [
        StaffEntryRow(entry=entry, release=RELEASE_SHARED, granted_until=None)
        for entry in shareable
    ]

    confirmation, latest = _confirmation_rows(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
        now=now,
        since=since,
    )
    granted_ids = [row.entry_id for row in confirmation if row.state == ACCESS_GRANTED]
    if granted_ids:
        granted_entries = JournalEntry.objects.for_clinic(clinic_id).filter(
            pk__in=granted_ids,
            patient_profile_id=patient_profile_id,
            visibility=JournalEntry.Visibility.CONFIRMATION_REQUIRED,
        )
        rows.extend(
            StaffEntryRow(
                entry=entry,
                release=RELEASE_GRANTED,
                granted_until=latest[entry.pk].expires_at,
            )
            for entry in granted_entries
        )
    rows.sort(key=lambda row: (row.entry.created_at, row.entry.pk), reverse=True)

    history = list(
        JournalAccessRequest.objects.for_clinic(clinic_id)
        .filter(therapist_id=therapist_id, patient_profile_id=patient_profile_id)
        .order_by("-requested_at", "-id")[:_REQUEST_HISTORY_LIMIT]
    )
    created_by_entry = dict(
        JournalEntry.objects.for_clinic(clinic_id)
        .filter(pk__in={request.journal_entry_id for request in history})
        .values_list("pk", "created_at")
    )
    return StaffDiary(
        entries=tuple(rows),
        confirmation=tuple(row for row in confirmation if row.state != ACCESS_GRANTED),
        requests=tuple(
            AccessRequestRow(
                request=request,
                state=access_request_state(request, now=now),
                entry_created_at=created_by_entry.get(request.journal_entry_id),
            )
            for request in history
        ),
    )


@dataclass(frozen=True, slots=True)
class CheckInDayRow:
    """One day with a shared check-in; scores follow ``CHECKIN_SCALE_KEYS``."""

    day: date
    scores: tuple[int | None, ...]


@dataclass(frozen=True, slots=True)
class QuestionSeries:
    """One 1-5 question over the period, one slot per calendar day (oldest first)."""

    key: str
    scores: tuple[int | None, ...]
    answered: int
    average: float | None
    latest: int | None


@dataclass(frozen=True, slots=True)
class CheckInSeries:
    """The shared check-ins of one patient over a short window."""

    start: date
    end: date
    days: tuple[date, ...]
    shared_count: int
    rows: tuple[CheckInDayRow, ...]  # only days with a shared check-in, newest first
    questions: tuple[QuestionSeries, ...]


def _scale_score(value: object) -> int | None:
    """Accept only the 1-5 scale; anything else reads as not answered."""
    if isinstance(value, bool):
        return None
    try:
        score = int(str(value))
    except ValueError:
        return None
    return score if 1 <= score <= 5 else None


def therapist_patient_checkin_series(
    *,
    clinic_id: UUID,
    therapist_id: UUID,
    patient_profile_id: UUID,
    days: int = 14,
    today: date | None = None,
) -> CheckInSeries:
    """Return the 1-5 answers of the check-ins the patient chose to share.

    Only submitted, shareable (green) check-ins count. Yellow and private ones are
    not read, and a day without a shared check-in is simply empty: the view cannot
    tell "did not answer" from "kept it private". Free-text notes are not read.
    """
    _authorize_staff_diary(
        clinic_id=clinic_id,
        therapist_id=therapist_id,
        patient_profile_id=patient_profile_id,
    )
    days = max(1, min(days, 90))
    end = today or timezone.localdate()
    start = end - timedelta(days=days - 1)
    window = tuple(start + timedelta(days=offset) for offset in range(days))

    per_day: dict[date, DailyCheckIn] = {}
    checkins = (
        DailyCheckIn.objects.for_clinic(clinic_id)
        .filter(
            patient_profile_id=patient_profile_id,
            visibility=JournalEntry.Visibility.SHAREABLE,
            is_draft=False,
            submitted_at__isnull=False,
            date__gte=start,
            date__lte=end,
        )
        .only("date", "answers", "submitted_at")
        .order_by("date", "submitted_at", "id")
    )
    for checkin in checkins:
        per_day[checkin.date] = checkin  # the latest submission of the day wins

    day_scores: dict[date, tuple[int | None, ...]] = {
        day: tuple(
            _scale_score((checkin.answers or {}).get(key))
            for key in CHECKIN_SCALE_KEYS
        )
        for day, checkin in per_day.items()
    }
    questions: list[QuestionSeries] = []
    for position, key in enumerate(CHECKIN_SCALE_KEYS):
        scores = tuple(
            day_scores[day][position] if day in day_scores else None for day in window
        )
        answered = [score for score in scores if score is not None]
        questions.append(
            QuestionSeries(
                key=key,
                scores=scores,
                answered=len(answered),
                average=round(sum(answered) / len(answered), 1) if answered else None,
                latest=answered[-1] if answered else None,
            )
        )
    return CheckInSeries(
        start=start,
        end=end,
        days=window,
        shared_count=len(per_day),
        rows=tuple(
            CheckInDayRow(day=day, scores=day_scores[day])
            for day in sorted(day_scores, reverse=True)
        ),
        questions=tuple(questions),
    )
