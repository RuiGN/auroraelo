"""Serviços de sessão do app do paciente.

- Login com a mesma verificação e o mesmo orçamento de tentativas do login web.
- Token de acesso curto (15 min) e token de renovação rotativo: cada renovação
  invalida o anterior. Apresentar um token já trocado revoga a sessão inteira.
- Só o resumo (SHA-256) dos tokens é gravado. Tokens têm 256 bits de entropia, então
  um resumo rápido basta e permite achar a sessão sem varrer a tabela.
- A clínica e o perfil de paciente ficam presos à sessão no servidor.
- A cada uso, o vínculo é conferido de novo: troca de senha, usuário inativo, papel ou
  clínica encerrados derrubam a sessão na hora.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.services import (
    LoginRateLimitedError as LoginRateLimitedError,
)
from accounts.services import (
    LoginRejectedError as LoginRejectedError,
)
from accounts.services import verify_credentials
from audit.services import record_audit_event
from clinics.policies import has_active_clinic_role
from clinics.selectors import active_clinics_with_role
from core.policies import current_actor_is_active
from core.services import Service as Service
from people.selectors import patient_profile_for_user

from .contracts import (
    ACCESS_TOKEN_PREFIX,
    LAST_USED_RESOLUTION,
    MAX_APP_VERSION_LENGTH,
    MAX_DEVICE_LABEL_LENGTH,
    MAX_TOKEN_LENGTH,
    PATIENT_ROLE,
    REFRESH_TOKEN_PREFIX,
    Platform,
    RevokeReason,
    access_token_ttl,
    max_sessions_per_user,
    refresh_token_ttl,
    session_absolute_ttl,
)
from .models import MobileSession

__all__ = [
    "AuthenticatedMobileSession",
    "ClinicChoiceRequiredError",
    "InvalidMobileTokenError",
    "IssuedTokens",
    "LoginRateLimitedError",
    "LoginRejectedError",
    "Service",
    "authenticate_access_token",
    "purge_finished_sessions",
    "refresh_session",
    "revoke_other_sessions",
    "revoke_session",
    "revoke_session_by_id",
    "start_session",
]

logger = logging.getLogger("application.mobile_api")


class InvalidMobileTokenError(Exception):
    """Token de renovação desconhecido, vencido, já trocado ou revogado."""


class ClinicChoiceRequiredError(Exception):
    """O paciente pertence a mais de uma clínica e precisa escolher uma."""

    def __init__(self, clinics: list[tuple[UUID, str]]) -> None:
        super().__init__("clinic choice required")
        self.clinics = clinics


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    """Credenciais devolvidas uma única vez ao aparelho."""

    session: MobileSession
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class AuthenticatedMobileSession:
    """Contexto resolvido no servidor para uma requisição autenticada."""

    session: MobileSession

    @property
    def user(self) -> Any:
        return self.session.user

    @property
    def clinic(self) -> Any:
        return self.session.clinic

    @property
    def patient_profile(self) -> Any:
        return self.session.patient_profile

    @property
    def clinic_id(self) -> UUID:
        return self.session.clinic_id

    @property
    def patient_profile_id(self) -> UUID:
        return self.session.patient_profile_id


# ── Auxiliares ──────────────────────────────────────────────────────────────


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token(prefix: str) -> str:
    return prefix + secrets.token_urlsafe(32)


def _plausible(token: str, prefix: str) -> bool:
    return (
        isinstance(token, str)
        and token.startswith(prefix)
        and len(prefix) < len(token) <= MAX_TOKEN_LENGTH
    )


def _network_hint(network_origin: str | None) -> str:
    if not network_origin:
        return ""
    return salted_hmac(
        "mobile_api.session-network",
        network_origin,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()[:16]


def _clean_label(value: str, *, limit: int, default: str) -> str:
    collapsed = " ".join(str(value).split())
    return collapsed[:limit] or default


def _clean_platform(value: str) -> str:
    return value if value in Platform.values else Platform.OTHER.value


def _origin(request: HttpRequest) -> str | None:
    return str(request.META.get("REMOTE_ADDR", "")) or None


def _audit(
    *,
    session: MobileSession,
    action: str,
    request_id: UUID,
    outcome: str = "success",
    network_origin: str | None = None,
) -> None:
    record_audit_event(
        clinic_id=session.clinic_id,
        actor_id=session.user_id,
        action=action,
        resource_type="mobile_session",
        resource_id=str(session.pk),
        outcome=outcome,
        request_id=request_id,
        network_origin=network_origin,
    )


def _revoke(session: MobileSession, *, reason: RevokeReason, now: datetime) -> None:
    if session.revoked_at is not None:
        return
    session.revoked_at = now
    session.revoked_reason = reason.value
    session.save(update_fields=("revoked_at", "revoked_reason", "updated_at"))


def _lost_authorization(session: MobileSession) -> RevokeReason | None:
    """Reconfere, a cada uso, tudo o que sustentava a sessão."""
    user = session.user
    if not current_actor_is_active(user):
        return RevokeReason.ACCESS_ENDED
    changed_at = max(user.credentials_changed_at, user.security_state_changed_at)
    if changed_at > session.created_at:
        return RevokeReason.CREDENTIALS_CHANGED
    if (
        not has_active_clinic_role(
            clinic_id=session.clinic_id,
            user_id=session.user_id,
            role=PATIENT_ROLE,
            on_date=timezone.localdate(),
        )
        or session.patient_profile.user_id != session.user_id
    ):
        return RevokeReason.ACCESS_ENDED
    return None


def _issue(session: MobileSession, *, now: datetime) -> tuple[str, str]:
    """Grava novos resumos de acesso e renovação e devolve os tokens em claro."""
    access = _new_token(ACCESS_TOKEN_PREFIX)
    refresh = _new_token(REFRESH_TOKEN_PREFIX)
    session.access_digest = _digest(access)
    session.access_expires_at = min(
        now + access_token_ttl(), session.absolute_expires_at
    )
    session.refresh_digest = _digest(refresh)
    session.refresh_expires_at = min(
        now + refresh_token_ttl(), session.absolute_expires_at
    )
    return access, refresh


# ── Login ───────────────────────────────────────────────────────────────────


def start_session(
    *,
    request: HttpRequest,
    email: str,
    password: str,
    clinic_id: UUID | None,
    device_label: str,
    platform: str,
    app_version: str,
    request_id: UUID,
) -> IssuedTokens:
    """Autentica o paciente e abre uma sessão presa a uma clínica."""
    user, _clinic_ids = verify_credentials(
        request=request, email=email, password=password, role=PATIENT_ROLE
    )
    candidates = active_clinics_with_role(user, PATIENT_ROLE)
    if clinic_id is None:
        if len(candidates) != 1:
            raise ClinicChoiceRequiredError([(c.pk, c.name) for c in candidates])
        clinic = candidates[0]
    else:
        match = next((c for c in candidates if c.pk == clinic_id), None)
        if match is None:
            raise LoginRejectedError("clinic not available")
        clinic = match
    profile = patient_profile_for_user(clinic_id=clinic.pk, user_id=user.pk)
    if profile is None:
        raise LoginRejectedError("patient profile not available")

    now = timezone.now()
    with transaction.atomic():
        session = MobileSession(
            clinic=clinic,
            user=user,
            patient_profile=profile,
            device_label=_clean_label(
                device_label, limit=MAX_DEVICE_LABEL_LENGTH, default="Dispositivo"
            ),
            platform=_clean_platform(platform),
            app_version=_clean_label(
                app_version, limit=MAX_APP_VERSION_LENGTH, default=""
            ),
            network_hint=_network_hint(_origin(request)),
            absolute_expires_at=now + session_absolute_ttl(),
            last_used_at=now,
        )
        access, refresh = _issue(session, now=now)
        session.save(force_insert=True)
        _evict_oldest(session, now=now)
        _audit(
            session=session,
            action="login",
            request_id=request_id,
            network_origin=_origin(request),
        )
    logger.info(
        "mobile session started",
        extra={"event": "mobile.session.started", "outcome": "success"},
    )
    return IssuedTokens(session=session, access_token=access, refresh_token=refresh)


def start_session_for_user(
    *,
    request: HttpRequest,
    user: Any,
    clinic_id: UUID | None,
    device_label: str,
    platform: str,
    app_version: str,
    request_id: UUID,
) -> IssuedTokens:
    """Abre uma sessão mobile para um ``User`` já autenticado (ex: via OTP).

    Idêntico a ``start_session`` mas não exige verificação de senha —
    o chamador é responsável por garantir que o usuário está autenticado.
    """
    candidates = active_clinics_with_role(user, PATIENT_ROLE)
    if clinic_id is None:
        if len(candidates) != 1:
            raise ClinicChoiceRequiredError([(c.pk, c.name) for c in candidates])
        clinic = candidates[0]
    else:
        match = next((c for c in candidates if c.pk == clinic_id), None)
        if match is None:
            raise LoginRejectedError("clinic not available")
        clinic = match

    profile = patient_profile_for_user(clinic_id=clinic.pk, user_id=user.pk)
    if profile is None:
        raise LoginRejectedError("patient profile not available")

    now = timezone.now()
    with transaction.atomic():
        session = MobileSession(
            clinic=clinic,
            user=user,
            patient_profile=profile,
            device_label=_clean_label(
                device_label, limit=MAX_DEVICE_LABEL_LENGTH, default="Dispositivo"
            ),
            platform=_clean_platform(platform),
            app_version=_clean_label(
                app_version, limit=MAX_APP_VERSION_LENGTH, default=""
            ),
            network_hint=_network_hint(_origin(request)),
            absolute_expires_at=now + session_absolute_ttl(),
            last_used_at=now,
        )
        access, refresh = _issue(session, now=now)
        session.save(force_insert=True)
        _evict_oldest(session, now=now)
        _audit(
            session=session,
            action="login",
            request_id=request_id,
            network_origin=_origin(request),
        )
    logger.info(
        "mobile session started via otp",
        extra={"event": "mobile.session.started", "outcome": "otp"},
    )
    return IssuedTokens(session=session, access_token=access, refresh_token=refresh)


def _evict_oldest(current: MobileSession, *, now: datetime) -> None:
    """Mantém no máximo N aparelhos ativos por pessoa e clínica."""
    active = list(
        MobileSession.objects.for_clinic(current.clinic_id)
        .active()
        .filter(user_id=current.user_id)
        .order_by("-last_used_at", "-created_at")
    )
    for stale in active[max_sessions_per_user() :]:
        _revoke(stale, reason=RevokeReason.EVICTED, now=now)


# ── Renovação rotativa ──────────────────────────────────────────────────────


def refresh_session(
    *, refresh_token: str, request_id: UUID, network_origin: str | None = None
) -> IssuedTokens:
    """Troca o token de renovação por um novo par. O anterior deixa de valer."""
    if not _plausible(refresh_token, REFRESH_TOKEN_PREFIX):
        raise InvalidMobileTokenError
    digest = _digest(refresh_token)
    failure: str | None = None
    issued: IssuedTokens | None = None
    audit_session: MobileSession | None = None
    with transaction.atomic():
        # Trava só a linha da sessão (não o usuário, a clínica e o perfil do join).
        session = (
            MobileSession.infrastructure_objects.select_for_update(of=("self",))
            .select_related("user", "clinic", "patient_profile")
            .filter(refresh_digest=digest)
            .first()
        )
        reused = None
        if session is None:
            reused = (
                MobileSession.infrastructure_objects.select_for_update(of=("self",))
                .select_related("user", "clinic", "patient_profile")
                .filter(previous_refresh_digest=digest)
                .first()
            )
        now = timezone.now()
        if session is None and reused is None:
            failure = "unknown"
        elif session is None and reused is not None:
            # Um token já trocado voltou: o par foi copiado. Derruba a sessão inteira.
            _revoke(reused, reason=RevokeReason.REUSE_DETECTED, now=now)
            audit_session = reused
            failure = "reuse"
        elif session is not None:
            if session.revoked_at is not None:
                failure = "revoked"
            elif (
                now >= session.refresh_expires_at or now >= session.absolute_expires_at
            ):
                failure = "expired"
            else:
                lost = _lost_authorization(session)
                if lost is not None:
                    _revoke(session, reason=lost, now=now)
                    audit_session = session
                    failure = "authorization"
                else:
                    session.previous_refresh_digest = session.refresh_digest
                    access, refresh = _issue(session, now=now)
                    session.last_used_at = now
                    session.save()
                    issued = IssuedTokens(
                        session=session, access_token=access, refresh_token=refresh
                    )
        # Renovação de rotina não entra na trilha (uma por 15 min por aparelho);
        # só as recusas que revogam a sessão.
        if audit_session is not None:
            _audit(
                session=audit_session,
                action="update",
                request_id=request_id,
                outcome="denied",
                network_origin=network_origin,
            )
    if issued is None:
        logger.warning(
            "mobile refresh refused",
            extra={"event": "mobile.session.refresh_refused", "outcome": failure},
        )
        raise InvalidMobileTokenError
    return issued


# ── Autenticação por requisição ─────────────────────────────────────────────


def authenticate_access_token(*, token: str) -> AuthenticatedMobileSession | None:
    """Resolve o token de acesso em sessão, usuário, clínica e perfil de paciente."""
    if not _plausible(token, ACCESS_TOKEN_PREFIX):
        return None
    session = (
        MobileSession.infrastructure_objects.select_related(
            "user", "clinic", "patient_profile"
        )
        .filter(access_digest=_digest(token))
        .first()
    )
    if session is None:
        return None
    now = timezone.now()
    if (
        session.revoked_at is not None
        or now >= session.access_expires_at
        or now >= session.absolute_expires_at
    ):
        return None
    lost = _lost_authorization(session)
    if lost is not None:
        _revoke(session, reason=lost, now=now)
        return None
    if now - session.last_used_at >= LAST_USED_RESOLUTION:
        session.last_used_at = now
        session.save(update_fields=("last_used_at", "updated_at"))
    return AuthenticatedMobileSession(session=session)


# ── Revogação ───────────────────────────────────────────────────────────────


@transaction.atomic
def revoke_session(
    *, session: MobileSession, reason: RevokeReason, request_id: UUID
) -> None:
    """Encerra uma sessão do próprio paciente (saída)."""
    locked = MobileSession.infrastructure_objects.select_for_update().get(pk=session.pk)
    if locked.revoked_at is not None:
        return
    _revoke(locked, reason=reason, now=timezone.now())
    _audit(session=locked, action="update", request_id=request_id)


@transaction.atomic
def revoke_session_by_id(
    *,
    clinic_id: UUID,
    user_id: UUID,
    session_id: UUID,
    request_id: UUID,
) -> None:
    """Encerra outro aparelho do próprio paciente; id alheio nunca é revelado."""
    target = (
        MobileSession.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(pk=session_id, user_id=user_id, revoked_at__isnull=True)
        .first()
    )
    if target is None:
        raise PermissionDenied
    _revoke(target, reason=RevokeReason.USER_REVOKED, now=timezone.now())
    _audit(session=target, action="update", request_id=request_id)


@transaction.atomic
def revoke_other_sessions(*, session: MobileSession, request_id: UUID) -> int:
    """Encerra todos os outros aparelhos do paciente nesta clínica."""
    others = list(
        MobileSession.objects.for_clinic(session.clinic_id)
        .select_for_update()
        .filter(user_id=session.user_id, revoked_at__isnull=True)
        .exclude(pk=session.pk)
    )
    now = timezone.now()
    for other in others:
        _revoke(other, reason=RevokeReason.USER_REVOKED, now=now)
    if others:
        record_audit_event(
            clinic_id=session.clinic_id,
            actor_id=session.user_id,
            action="update",
            resource_type="mobile_session_set",
            resource_id=str(session.user_id),
            outcome="success",
            request_id=request_id,
            network_origin=None,
        )
    return len(others)


def purge_finished_sessions(*, retention_days: int = 30) -> int:
    """Remove sessões vencidas ou revogadas há mais de `retention_days` dias."""
    cutoff = timezone.now() - timedelta(days=max(1, retention_days))
    finished = MobileSession.infrastructure_objects.filter(
        revoked_at__lt=cutoff
    ) | MobileSession.infrastructure_objects.filter(absolute_expires_at__lt=cutoff)
    count, _detail = finished.delete()
    return count
