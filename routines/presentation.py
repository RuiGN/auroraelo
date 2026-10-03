"""Translatable labels for the routines vocabulary.

The domain stores stable codes (and a few Portuguese-only choice labels). The team
screens show these labels instead, so every language gets a real translation.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from .models import (
    CarePlanStatus,
    CheckInStatus,
    HabitFrequency,
    HabitStatus,
    MedicationAdministrationRoute,
    MedicationLogStatus,
    PatientResponseChoice,
    TimeOfDayWindow,
)

ROUTE_LABELS = {
    MedicationAdministrationRoute.ORAL: _("Oral"),
    MedicationAdministrationRoute.SUBLINGUAL: _("Sublingual"),
    MedicationAdministrationRoute.TOPICAL: _("Tópica"),
    MedicationAdministrationRoute.INHALATION: _("Inalação"),
    MedicationAdministrationRoute.INJECTABLE: _("Injetável"),
    MedicationAdministrationRoute.OPHTHALMIC: _("Oftálmica"),
    MedicationAdministrationRoute.NASAL: _("Nasal"),
    MedicationAdministrationRoute.OTHER: _("Outra"),
}

DOSE_STATUS_LABELS = {
    MedicationLogStatus.TAKEN: _("Tomada"),
    MedicationLogStatus.LATE: _("Tomada com atraso"),
    MedicationLogStatus.OMITTED: _("Não tomada"),
    MedicationLogStatus.NOT_REPORTED: _("Sem informação"),
}

PLAN_STATUS_LABELS = {
    CarePlanStatus.DRAFT: _("Rascunho"),
    CarePlanStatus.PENDING_SIGNATURE: _("Aguardando assinatura"),
    CarePlanStatus.ACTIVE: _("Ativo"),
    CarePlanStatus.PAUSED: _("Pausado"),
    CarePlanStatus.COMPLETED: _("Concluído"),
    CarePlanStatus.REVOKED: _("Revogado"),
}

PLAN_STATUS_BADGES = {
    CarePlanStatus.DRAFT: "muted",
    CarePlanStatus.PENDING_SIGNATURE: "warning",
    CarePlanStatus.ACTIVE: "success",
    CarePlanStatus.PAUSED: "warning",
    CarePlanStatus.COMPLETED: "info",
    CarePlanStatus.REVOKED: "danger",
}

# What the patient sees in the app at each status (mirrors the app API: drafts and
# plans awaiting signature never appear; closed plans stay visible without replies).
PLAN_VISIBILITY = {
    CarePlanStatus.DRAFT: _(
        "O paciente ainda não vê este plano. Ele só aparece no app depois que "
        "o profissional assina."
    ),
    CarePlanStatus.PENDING_SIGNATURE: _(
        "O paciente ainda não vê este plano. Ele passa a aparecer no app "
        "quando o profissional assinar."
    ),
    CarePlanStatus.ACTIVE: _(
        "O paciente vê o título, o objetivo, as ações e os cuidados do plano e "
        "pode aceitar, pausar, recusar ou pedir revisão. A justificativa clínica "
        "não aparece no app."
    ),
    CarePlanStatus.PAUSED: _(
        "O plano continua visível no app, marcado como pausado, e o paciente "
        "ainda pode responder."
    ),
    CarePlanStatus.COMPLETED: _(
        "O plano continua visível no app como concluído e não aceita novas respostas."
    ),
    CarePlanStatus.REVOKED: _(
        "O plano continua visível no app como revogado e não aceita novas respostas."
    ),
}

RESPONSE_LABELS = {
    PatientResponseChoice.ACCEPTED: _("Aceitou o plano"),
    PatientResponseChoice.REFUSED: _("Recusou o plano"),
    PatientResponseChoice.PAUSED: _("Pausou o plano"),
    PatientResponseChoice.REVIEW_REQUESTED: _("Pediu revisão do plano"),
}

RESPONSE_BADGES = {
    PatientResponseChoice.ACCEPTED: "success",
    PatientResponseChoice.REFUSED: "danger",
    PatientResponseChoice.PAUSED: "warning",
    PatientResponseChoice.REVIEW_REQUESTED: "info",
}

FREQUENCY_LABELS = {
    HabitFrequency.DAILY: _("Todos os dias"),
    HabitFrequency.WEEKDAYS: _("Dias úteis"),
    HabitFrequency.SPECIFIC_DAYS: _("Dias específicos"),
    HabitFrequency.FLEXIBLE: _("Meta flexível"),
}

WINDOW_LABELS = {
    TimeOfDayWindow.MORNING: _("Manhã"),
    TimeOfDayWindow.AFTERNOON: _("Tarde"),
    TimeOfDayWindow.EVENING: _("Noite"),
    TimeOfDayWindow.NIGHT: _("Madrugada"),
    TimeOfDayWindow.ANY_TIME: _("Qualquer horário"),
    TimeOfDayWindow.EXACT_TIME: _("Horário fixo"),
}

HABIT_STATUS_LABELS = {
    HabitStatus.ACTIVE: _("Ativo"),
    HabitStatus.PAUSED: _("Pausado"),
    HabitStatus.ARCHIVED: _("Arquivado"),
}

CHECKIN_LABELS = {
    CheckInStatus.COMPLETED: _("Feito"),
    CheckInStatus.PARTIAL: _("Parcial"),
    CheckInStatus.POSTPONED: _("Adiado"),
    CheckInStatus.SKIPPED: _("Pulado"),
}

CHECKIN_BADGES = {
    CheckInStatus.COMPLETED: "success",
    CheckInStatus.PARTIAL: "info",
    CheckInStatus.POSTPONED: "warning",
    CheckInStatus.SKIPPED: "muted",
}

# Segunda-feira = 0, como em ``date.weekday()`` (é o que o domínio grava).
WEEKDAY_LABELS = (
    _("Segunda-feira"),
    _("Terça-feira"),
    _("Quarta-feira"),
    _("Quinta-feira"),
    _("Sexta-feira"),
    _("Sábado"),
    _("Domingo"),
)

WEEKDAY_SHORT_LABELS = (
    _("Seg"),
    _("Ter"),
    _("Qua"),
    _("Qui"),
    _("Sex"),
    _("Sáb"),
    _("Dom"),
)

ROUTE_CHOICES = [(str(code.value), label) for code, label in ROUTE_LABELS.items()]
FREQUENCY_CHOICES = [
    (str(code.value), label) for code, label in FREQUENCY_LABELS.items()
]
WINDOW_CHOICES = [(str(code.value), label) for code, label in WINDOW_LABELS.items()]
WEEKDAY_CHOICES = [(str(index), label) for index, label in enumerate(WEEKDAY_LABELS)]


__all__ = [
    "CHECKIN_BADGES",
    "CHECKIN_LABELS",
    "DOSE_STATUS_LABELS",
    "FREQUENCY_CHOICES",
    "FREQUENCY_LABELS",
    "HABIT_STATUS_LABELS",
    "PLAN_STATUS_BADGES",
    "PLAN_STATUS_LABELS",
    "PLAN_VISIBILITY",
    "RESPONSE_BADGES",
    "RESPONSE_LABELS",
    "ROUTE_CHOICES",
    "ROUTE_LABELS",
    "WEEKDAY_CHOICES",
    "WEEKDAY_LABELS",
    "WEEKDAY_SHORT_LABELS",
    "WINDOW_CHOICES",
    "WINDOW_LABELS",
]
