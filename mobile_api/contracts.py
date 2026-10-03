"""Contratos da sessão mobile: papéis, prefixos de token, limites e motivos."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import models

# Só o papel de paciente abre sessão no app. Equipe usa o sistema web da clínica.
PATIENT_ROLE = "patient"

# Prefixos legíveis ajudam varreduras de segredo e deixam claro o que vazou.
ACCESS_TOKEN_PREFIX = "aem_"
REFRESH_TOKEN_PREFIX = "aer_"
MAX_TOKEN_LENGTH = 96

# Painel web da equipe: o convite segue a matriz da clínica (`invitation.issue`), então
# só o administrador o emite. Revogar aparelhos também cabe ao terapeuta vinculado.
INVITATION_ROLE = "clinic_admin"
INVITATION_VALID_DAYS = 7

MAX_DEVICE_LABEL_LENGTH = 80
MAX_APP_VERSION_LENGTH = 32
LAST_USED_RESOLUTION = timedelta(minutes=5)


class Platform(models.TextChoices):
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"
    OTHER = "other", "Outro"


class RevokeReason(models.TextChoices):
    """Por que a sessão deixou de valer (nunca guarda dado do paciente)."""

    LOGOUT = "logout", "Saída pelo paciente"
    USER_REVOKED = "user_revoked", "Encerrada pelo paciente em outro aparelho"
    EVICTED = "evicted", "Substituída por um limite de aparelhos"
    REUSE_DETECTED = "reuse_detected", "Reuso de credencial de renovação"
    CREDENTIALS_CHANGED = "credentials_changed", "Senha ou segurança alterada"
    ACCESS_ENDED = "access_ended", "Vínculo com a clínica encerrado"
    STAFF_REVOKED = "staff_revoked", "Encerrada pela equipe da clínica"


def access_token_ttl() -> timedelta:
    return timedelta(
        seconds=max(60, int(getattr(settings, "MOBILE_ACCESS_TOKEN_SECONDS", 900)))
    )


def refresh_token_ttl() -> timedelta:
    return timedelta(
        days=max(1, int(getattr(settings, "MOBILE_REFRESH_TOKEN_DAYS", 30)))
    )


def session_absolute_ttl() -> timedelta:
    return timedelta(
        days=max(1, int(getattr(settings, "MOBILE_SESSION_ABSOLUTE_DAYS", 90)))
    )


def max_sessions_per_user() -> int:
    return max(1, int(getattr(settings, "MOBILE_MAX_SESSIONS_PER_USER", 5)))
