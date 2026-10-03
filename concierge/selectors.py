"""Leituras do concierge e do acompanhamento pós-alta (sem efeitos colaterais)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from django.utils import timezone

from core.selectors import Selector as Selector
from people.selectors import patient_profiles_for_clinic

from .contracts import (
    OPEN_REQUEST_STATUSES,
    ContactKind,
    ContactStatus,
    DischargeStatus,
    RequestStatus,
)
from .models import (
    AftercareContact,
    CommunicationRule,
    CommunicationRuleStep,
    ConciergeLog,
    Discharge,
    FamilyContact,
    FamilyRequest,
)

__all__ = [
    "ContactRow",
    "DashboardSummary",
    "Selector",
    "TimelineItem",
    "active_rule",
    "contact_queue",
    "contact_state",
    "dashboard_summary",
    "discharge_detail",
    "discharge_list",
    "family_contacts_for_patient",
    "family_request_list",
    "patient_options_for_discharge",
    "patient_timeline",
    "recent_logs",
    "rule_history",
    "rule_steps",
]

QUEUE_WINDOWS = ("overdue", "today", "week", "all")


@dataclass(frozen=True, slots=True)
class ContactRow:
    """Contato da fila com os dados mínimos do paciente."""

    contact: AftercareContact
    patient_profile_id: UUID
    patient_name: str
    discharge_date: date
    state: str  # overdue | today | upcoming | done | missed | canceled


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    active_discharges: int
    overdue: int
    due_today: int
    due_next_7_days: int
    open_requests: int
    patients_without_family_consent: int
    queue: list[ContactRow]


@dataclass(frozen=True, slots=True)
class TimelineItem:
    """Item da linha do tempo de um paciente (contato, registro ou pedido)."""

    when: datetime
    kind: str  # contact | log | request
    title: str
    detail: str
    obj: Any


def contact_state(contact: AftercareContact, today: date) -> str:
    if contact.status == ContactStatus.DONE:
        return "done"
    if contact.status == ContactStatus.MISSED:
        return "missed"
    if contact.status == ContactStatus.CANCELED:
        return "canceled"
    if contact.due_date < today:
        return "overdue"
    if contact.due_date == today:
        return "today"
    return "upcoming"


def _rows(contacts: Any, today: date) -> list[ContactRow]:
    return [
        ContactRow(
            contact=contact,
            patient_profile_id=contact.discharge.patient_profile_id,
            patient_name=contact.discharge.patient_profile.full_name,
            discharge_date=contact.discharge.discharge_date,
            state=contact_state(contact, today),
        )
        for contact in contacts
    ]


# ── Régua ───────────────────────────────────────────────────────────────────


def active_rule(*, clinic_id: UUID) -> CommunicationRule | None:
    return (
        CommunicationRule.objects.for_clinic(clinic_id).filter(is_active=True).first()
    )


def rule_steps(*, clinic_id: UUID, rule_id: UUID) -> list[CommunicationRuleStep]:
    return list(
        CommunicationRuleStep.objects.for_clinic(clinic_id)
        .filter(rule_id=rule_id)
        .order_by("day_after_discharge", "order", "kind")
    )


def rule_history(*, clinic_id: UUID) -> list[CommunicationRule]:
    return list(
        CommunicationRule.objects.for_clinic(clinic_id)
        .select_related("created_by")
        .order_by("-version")
    )


# ── Altas e fila de contatos ────────────────────────────────────────────────


def contact_queue(
    *,
    clinic_id: UUID,
    today: date,
    window: str = "all",
    kind: str = "",
    status: str = "",
) -> list[ContactRow]:
    """Contatos ordenados por data. `window`: overdue | today | week | all (abertos)."""
    queryset = (
        AftercareContact.objects.for_clinic(clinic_id)
        .select_related("discharge", "discharge__patient_profile")
        .filter(discharge__status=DischargeStatus.ACTIVE)
    )
    if kind in ContactKind.values:
        queryset = queryset.filter(kind=kind)
    if status in ContactStatus.values:
        queryset = queryset.filter(status=status)
    else:
        queryset = queryset.filter(status=ContactStatus.SCHEDULED)
    if window == "overdue":
        queryset = queryset.filter(due_date__lt=today)
    elif window == "today":
        queryset = queryset.filter(due_date=today)
    elif window == "week":
        queryset = queryset.filter(
            due_date__gte=today, due_date__lte=today + timedelta(days=7)
        )
    return _rows(queryset.order_by("due_date", "kind"), today)


def dashboard_summary(
    *, clinic_id: UUID, today: date, queue_limit: int = 12
) -> DashboardSummary:
    scheduled = AftercareContact.objects.for_clinic(clinic_id).filter(
        status=ContactStatus.SCHEDULED, discharge__status=DischargeStatus.ACTIVE
    )
    week = today + timedelta(days=7)
    focus = (
        scheduled.filter(due_date__lte=week)
        .select_related("discharge", "discharge__patient_profile")
        .order_by("due_date", "kind")[:queue_limit]
    )
    without_consent = (
        Discharge.objects.for_clinic(clinic_id)
        .filter(status=DischargeStatus.ACTIVE)
        .exclude(
            patient_profile_id__in=FamilyContact.objects.for_clinic(clinic_id)
            .filter(is_active=True, consent_to_contact=True)
            .values("patient_profile_id")
        )
        .count()
    )
    return DashboardSummary(
        active_discharges=Discharge.objects.for_clinic(clinic_id)
        .filter(status=DischargeStatus.ACTIVE)
        .count(),
        overdue=scheduled.filter(due_date__lt=today).count(),
        due_today=scheduled.filter(due_date=today).count(),
        due_next_7_days=scheduled.filter(
            due_date__gt=today, due_date__lte=week
        ).count(),
        open_requests=FamilyRequest.objects.for_clinic(clinic_id)
        .filter(status__in=OPEN_REQUEST_STATUSES)
        .count(),
        patients_without_family_consent=without_consent,
        queue=_rows(focus, today),
    )


def discharge_list(*, clinic_id: UUID, status: str = "") -> list[Discharge]:
    queryset = (
        Discharge.objects.for_clinic(clinic_id)
        .select_related("patient_profile")
        .prefetch_related("contacts")
    )
    if status in DischargeStatus.values:
        queryset = queryset.filter(status=status)
    return list(queryset.order_by("-discharge_date", "-created_at"))


def discharge_detail(*, clinic_id: UUID, discharge_id: UUID) -> Discharge | None:
    return (
        Discharge.objects.for_clinic(clinic_id)
        .select_related("patient_profile")
        .prefetch_related("contacts")
        .filter(pk=discharge_id)
        .first()
    )


def patient_options_for_discharge(*, clinic_id: UUID) -> list[Any]:
    """Pacientes da clínica que ainda não têm alta em acompanhamento."""
    busy = set(
        Discharge.objects.for_clinic(clinic_id)
        .filter(status=DischargeStatus.ACTIVE)
        .values_list("patient_profile_id", flat=True)
    )
    return [
        p for p in patient_profiles_for_clinic(clinic_id=clinic_id) if p.pk not in busy
    ]


# ── Família, registro e pedidos ─────────────────────────────────────────────


def family_contacts_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID, include_inactive: bool = False
) -> list[FamilyContact]:
    queryset = FamilyContact.objects.for_clinic(clinic_id).filter(
        patient_profile_id=patient_profile_id
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return list(queryset.order_by("-is_primary", "full_name"))


def recent_logs(
    *, clinic_id: UUID, patient_profile_id: UUID | None = None, limit: int = 100
) -> list[ConciergeLog]:
    queryset = (
        ConciergeLog.objects.for_clinic(clinic_id)
        .select_related("patient_profile", "family_contact", "recorded_by")
        .prefetch_related("corrections")
    )
    if patient_profile_id is not None:
        queryset = queryset.filter(patient_profile_id=patient_profile_id)
    return list(queryset.order_by("-occurred_at", "-created_at")[:limit])


def family_request_list(
    *, clinic_id: UUID, status: str = "open", patient_profile_id: UUID | None = None
) -> list[FamilyRequest]:
    queryset = FamilyRequest.objects.for_clinic(clinic_id).select_related(
        "patient_profile", "family_contact"
    )
    if status == "open":
        queryset = queryset.filter(status__in=OPEN_REQUEST_STATUSES)
    elif status in RequestStatus.values:
        queryset = queryset.filter(status=status)
    if patient_profile_id is not None:
        queryset = queryset.filter(patient_profile_id=patient_profile_id)
    return list(queryset.order_by("-requested_at"))


def patient_timeline(
    *, clinic_id: UUID, patient_profile_id: UUID
) -> list[TimelineItem]:
    """Contatos pós-alta, registros e pedidos de um paciente (mais novo primeiro)."""
    items: list[TimelineItem] = []
    contacts = (
        AftercareContact.objects.for_clinic(clinic_id)
        .filter(discharge__patient_profile_id=patient_profile_id)
        .exclude(status=ContactStatus.SCHEDULED)
        .select_related("discharge")
    )
    for contact in contacts:
        when = contact.completed_at or timezone.make_aware(
            datetime.combine(contact.due_date, time.min)
        )
        items.append(
            TimelineItem(
                when=when,
                kind="contact",
                title=contact.get_kind_display(),
                detail=contact.get_outcome_display()
                if contact.outcome
                else contact.get_status_display(),
                obj=contact,
            )
        )
    for log in recent_logs(clinic_id=clinic_id, patient_profile_id=patient_profile_id):
        items.append(
            TimelineItem(
                when=log.occurred_at,
                kind="log",
                title=log.get_channel_display(),
                detail=log.summary,
                obj=log,
            )
        )
    for family_request in family_request_list(
        clinic_id=clinic_id, status="all", patient_profile_id=patient_profile_id
    ):
        items.append(
            TimelineItem(
                when=family_request.requested_at,
                kind="request",
                title=family_request.get_kind_display(),
                detail=family_request.description,
                obj=family_request,
            )
        )

    return sorted(items, key=lambda item: item.when, reverse=True)


def discharge_date_for_patient(
    *, clinic_id: UUID, patient_profile_id: UUID
) -> date | None:
    """Data da alta mais recente não cancelada; só a data, nunca o acompanhamento.

    Usada pelo app do paciente para contar os dias desde a alta. Notas, contatos e
    régua são da clínica e não saem daqui.
    """
    discharge = (
        Discharge.objects.for_clinic(clinic_id)
        .filter(patient_profile_id=patient_profile_id)
        .exclude(status=DischargeStatus.CANCELED)
        .order_by("-discharge_date", "-created_at")
        .first()
    )
    return discharge.discharge_date if discharge is not None else None
