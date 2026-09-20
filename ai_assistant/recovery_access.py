"""Fronteira B2C deny-by-default, sem consultas de tenant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.utils import timezone
from django.utils.translation import gettext as _

from core.policies import current_actor_is_active


@dataclass(frozen=True, slots=True)
class RecoveryConsent:
    """Decisão atual de um adaptador servidor de consentimento persistido e revogável.

    Não é token de cliente nem persistência. O adaptador proprietário de consentimentos
    deve validar documento vigente/integridade e a última manifestação a cada chamada.
    As finalidades B2C NÃO equivalem a clinical_follow_up ou communication.
    """

    subject_id: UUID
    purpose: str
    document_version: str
    explicit: bool
    accepted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class AccessDeniedError(RuntimeError):
    pass


def authorize(actor: AbstractBaseUser, purpose: str) -> RecoveryConsent:
    """Derivar ator no HTTP de request.user; jamais de JSON/query/header customizado."""
    try:
        if (
            purpose not in {"recovery_library", "recovery_ai"}
            or not actor.is_authenticated
            or not actor.is_active
            or not current_actor_is_active(actor)
        ):
            raise ValueError
        resolver = getattr(settings, "RECOVERY_CONSENT_RESOLVER", None)
        if not callable(resolver):
            raise ValueError
        grant = resolver(actor=actor, purpose=purpose)
        now = timezone.now()
        if (
            not isinstance(grant, RecoveryConsent)
            or grant.subject_id != actor.pk
            or grant.purpose != purpose
            or grant.explicit is not True
            or grant.revoked_at is not None
            or not isinstance(grant.document_version, str)
            or not 1 <= len(grant.document_version.strip()) <= 100
            or not isinstance(grant.accepted_at, datetime)
            or not isinstance(grant.expires_at, datetime)
            or not timezone.is_aware(grant.accepted_at)
            or not timezone.is_aware(grant.expires_at)
            or not grant.accepted_at <= now < grant.expires_at
        ):
            raise ValueError
        return grant
    except Exception as exc:
        # Falhas do backend de autorização também negam acesso, sem log do relato.
        raise AccessDeniedError(
            _("Acesso requer consentimento expresso vigente.")
        ) from exc
