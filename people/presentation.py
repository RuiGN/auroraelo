"""Translated display labels kept separate from persisted people codes."""

from django.utils.translation import gettext_lazy as _

GENDER_LABELS = {
    "woman": _("Mulher"),
    "man": _("Homem"),
    "non_binary": _("Pessoa não binária"),
    "other": _("Outro"),
    "undisclosed": _("Prefiro não informar"),
}
ROLE_LABELS = {
    "clinic_admin": _("Administrador da clínica"),
    "therapist": _("Terapeuta"),
    "administrative_staff": _("Equipe administrativa"),
    "patient": _("Paciente"),
}
STATUS_LABELS = {
    "active": _("Ativo"),
    "scheduled": _("Agendado"),
    "suspended": _("Suspenso"),
    "expired": _("Encerrado"),
}
