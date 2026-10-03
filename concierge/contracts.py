"""Stable vocabulary and limits for the concierge and post-discharge domain."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

# Ações de autorização (clinics.policies.ACTION_ROLES; docs/authorization-matrix.md).
ACTION_READ = "aftercare.read"
ACTION_MANAGE = "aftercare.manage"
ACTION_MANAGE_RULES = "aftercare.rules.manage"

MAX_RULE_STEPS = 8
MAX_DAY_AFTER_DISCHARGE = 365
MAX_BACKDATE_DAYS = 365
MAX_SUMMARY_LENGTH = 2000
MIN_SUMMARY_LENGTH = 3
MAX_NOTES_LENGTH = 1000


class ContactKind(models.TextChoices):
    """Tipo de contato previsto na régua pós-alta."""

    CALL = "call", _("Ligação")
    VISIT = "visit", _("Visita presencial")


# Régua padrão sugerida pelo PRD: 1ª ligação aos 7 dias, 2ª aos 15 e visita aos 15.
DEFAULT_RULE_NAME = _("Régua padrão pós-alta")
DEFAULT_RULE_STEPS: tuple[tuple[str, int], ...] = (
    (ContactKind.CALL.value, 7),
    (ContactKind.CALL.value, 15),
    (ContactKind.VISIT.value, 15),
)


class ResponsibleRole(models.TextChoices):
    """Papel de clínica sugerido como responsável por uma etapa."""

    ADMINISTRATIVE_STAFF = (
        "administrative_staff",
        _("Equipe administrativa (concierge)"),
    )
    THERAPIST = "therapist", _("Terapeuta")
    CLINIC_ADMIN = "clinic_admin", _("Administrador da clínica")


class DischargeStatus(models.TextChoices):
    ACTIVE = "active", _("Em acompanhamento")
    COMPLETED = "completed", _("Acompanhamento concluído")
    CANCELED = "canceled", _("Cancelada")


class ContactStatus(models.TextChoices):
    SCHEDULED = "scheduled", _("Agendado")
    DONE = "done", _("Realizado")
    MISSED = "missed", _("Não realizado")
    CANCELED = "canceled", _("Cancelado")


class ContactOutcome(models.TextChoices):
    """Resultado de um contato de acompanhamento (sem conteúdo clínico)."""

    REACHED = "reached", _("Conseguiu falar")
    NO_ANSWER = "no_answer", _("Não atendeu")
    DECLINED = "declined", _("Recusou o contato")
    VISIT_DONE = "visit_done", _("Visita realizada")
    VISIT_NOT_POSSIBLE = "visit_not_possible", _("Visita não foi possível")


CALL_OUTCOMES = frozenset(
    {
        ContactOutcome.REACHED.value,
        ContactOutcome.NO_ANSWER.value,
        ContactOutcome.DECLINED.value,
    }
)
VISIT_OUTCOMES = frozenset(
    {ContactOutcome.VISIT_DONE.value, ContactOutcome.VISIT_NOT_POSSIBLE.value}
)
# Resultados em que o contato aconteceu; os demais viram "não realizado".
SUCCESS_OUTCOMES = frozenset(
    {ContactOutcome.REACHED.value, ContactOutcome.VISIT_DONE.value}
)


class LogChannel(models.TextChoices):
    CALL = "call", _("Ligação")
    VISIT = "visit", _("Visita")
    MESSAGE = "message", _("Mensagem")
    EMAIL = "email", _("E-mail")


class LogDirection(models.TextChoices):
    OUTBOUND = "outbound", _("Da clínica para a família")
    INBOUND = "inbound", _("Da família para a clínica")


class RequestKind(models.TextChoices):
    """Pedido do paciente à família, registrado pelo concierge."""

    CALL_ME = "call_me", _("Que me liguem")
    VISIT_ME = "visit_me", _("Que me visitem")
    BRING_ITEM = "bring_item", _("Que tragam algo")
    MESSAGE = "message", _("Que recebam um recado")


class RequestStatus(models.TextChoices):
    OPEN = "open", _("Aberto")
    FORWARDED = "forwarded", _("Encaminhado à família")
    FULFILLED = "fulfilled", _("Atendido")
    DECLINED = "declined", _("Não atendido")
    CANCELED = "canceled", _("Cancelado")


OPEN_REQUEST_STATUSES = frozenset(
    {RequestStatus.OPEN.value, RequestStatus.FORWARDED.value}
)
