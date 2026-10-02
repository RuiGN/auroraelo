"""Transactional identity, invitation and authentication services."""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.crypto import salted_hmac
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop

from clinics.selectors import (
    active_clinic_ids_for_actor,
    active_clinics_for_actor,
    active_clinics_with_role,
    active_web_clinics_for_actor,
)
from clinics.services import (
    CLINIC_SESSION_KEY,
    activate_invited_membership,
    active_clinic_for_infrastructure,
    authorized_active_clinic,
    create_clinic_membership,
    is_membership_role_supported,
)
from core.policies import current_actor_is_active
from core.services import Service as Service

from .events import account_audit_required, invitation_accepted
from .models import (
    AccountSession,
    ClinicInvitation,
    User,
    UserManager,
    _session_digest,
)

INVALID_INVITATION_MESSAGE = "Convite inválido ou expirado."
GENERIC_LOGIN_ERROR = gettext_noop("Não foi possível entrar com os dados informados.")
GENERIC_RECOVERY_RESPONSE = gettext_noop(
    "Se existir uma conta ativa para este e-mail, você receberá as instruções."
)
logger = logging.getLogger("application.accounts")


class ClinicIdentity(Protocol):
    """Public tenant identity needed by authentication orchestration."""

    @property
    def id(self) -> UUID:
        """Return the stable tenant identifier."""
        ...

    @property
    def pk(self) -> UUID:
        """Return the stable primary key alias."""
        ...


class LoginRejectedError(ValueError):
    """Reject authentication without exposing which check failed."""


class LoginRateLimitedError(LoginRejectedError):
    """Reject authentication after the configured failure budget."""


class RecoveryRateLimitedError(ValueError):
    """Reject recovery requests after the configured request budget."""


class SensitiveActionRateLimitedError(ValueError):
    """Reject repeated password reauthentication for high-impact actions."""


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    """Return the persisted invitation and its one-time raw credential."""

    invitation: ClinicInvitation
    raw_token: str


def _token_digest(raw_token: str) -> str:
    """Return a deterministic digest without retaining the bearer credential."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _rate_limit_key(*, scope: str, request: HttpRequest, identity: str) -> str:
    """Build a bounded cache key without retaining network or identity data."""
    network_origin = str(request.META.get("REMOTE_ADDR", "unknown"))
    digest = salted_hmac(
        f"accounts.rate-limit.{scope}",
        f"{network_origin}\0{identity}",
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()
    return f"accounts:{scope}:{digest}"


def _identity_rate_limit_key(*, scope: str, identity: str) -> str:
    """Build an account-wide pseudonymous key resistant to origin rotation."""
    digest = salted_hmac(
        f"accounts.rate-limit.{scope}.identity",
        identity,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()
    return f"accounts:{scope}:identity:{digest}"


def _rate_limit_settings(*, attempts_name: str, window_name: str) -> tuple[int, int]:
    """Return safe positive settings even if deployment input is malformed."""
    attempts = max(1, int(getattr(settings, attempts_name)))
    window = max(1, int(getattr(settings, window_name)))
    return attempts, window


def _is_rate_limited(*, key: str, attempts: int) -> bool:
    """Return whether the fixed-window counter has exhausted its budget."""
    value = cache.get(key, 0)
    return isinstance(value, int) and value >= attempts


def _record_rate_limited_action(*, key: str, window: int) -> None:
    """Atomically start or increment one fixed-window cache counter."""
    if cache.add(key, 1, timeout=window):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.add(key, 1, timeout=window)


def _request_id(request: HttpRequest) -> UUID:
    """Use request correlation when available and a safe fallback otherwise."""
    candidate = getattr(request, "request_id", None)
    try:
        return UUID(str(candidate))
    except TypeError, ValueError, AttributeError:
        return uuid4()


def _session_resource_id(request: HttpRequest) -> str:
    """Return an audit-safe digest instead of the bearer session identifier."""
    session_key = request.session.session_key or "pending-session"
    return salted_hmac(
        "accounts.audit.session",
        session_key,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()


def _publish_account_audit(
    *,
    clinic_id: UUID,
    actor_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    request_id: UUID,
    network_origin: str | None = None,
    justification: str | None = None,
) -> None:
    """Publish one minimized audit requirement to the audit domain."""
    account_audit_required.send(
        sender=User,
        clinic_id=clinic_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        network_origin=network_origin,
        justification=justification,
    )


def _audit_session(
    *,
    request: HttpRequest,
    clinic_id: UUID,
    actor_id: UUID,
    action: str,
) -> None:
    """Publish a minimized successful authentication lifecycle event."""
    _publish_account_audit(
        clinic_id=clinic_id,
        actor_id=actor_id,
        action=action,
        resource_type="session",
        resource_id=_session_resource_id(request),
        request_id=_request_id(request),
        network_origin=str(request.META.get("REMOTE_ADDR", "")) or None,
    )


def _login_budget(
    *, request: HttpRequest, canonical_email: str
) -> tuple[tuple[str, str], int]:
    """Return the throttle keys and window, or refuse when the budget is spent."""
    attempts, window = _rate_limit_settings(
        attempts_name="LOGIN_RATE_LIMIT_ATTEMPTS",
        window_name="LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    )
    origin_key = _rate_limit_key(
        scope="login",
        request=request,
        identity=canonical_email,
    )
    identity_key = _identity_rate_limit_key(scope="login", identity=canonical_email)
    keys = (origin_key, identity_key)
    if any(_is_rate_limited(key=key, attempts=attempts) for key in keys):
        raise LoginRateLimitedError(GENERIC_LOGIN_ERROR)
    return keys, window


def verify_credentials(
    *, request: HttpRequest, email: str, password: str, role: str
) -> tuple[User, list[UUID]]:
    """Authenticate token-based clients without opening a Django session.

    Shares the failure budget with web login, so switching channel never resets it.
    The identity must hold ``role`` in at least one active clinic; otherwise the
    attempt counts as a failure and the caller learns nothing about why. Returns the
    identity and the identifiers of the clinics where it holds that role.
    """
    canonical_email = UserManager.canonical_email(email)
    keys, window = _login_budget(request=request, canonical_email=canonical_email)
    authenticated = authenticate(
        request,
        username=canonical_email,
        password=password,
    )
    user = authenticated if isinstance(authenticated, User) else None
    clinics = active_clinics_with_role(user, role) if user is not None else []
    if user is None or not clinics:
        for key in keys:
            _record_rate_limited_action(key=key, window=window)
        raise LoginRejectedError(GENERIC_LOGIN_ERROR)
    cache.delete_many(keys)
    return user, [clinic.pk for clinic in clinics]


def login_user(
    *, request: HttpRequest, email: str, password: str
) -> ClinicIdentity | None:
    """Authenticate canonically and select a tenant unless this is global staff."""
    canonical_email = UserManager.canonical_email(email)
    keys, window = _login_budget(request=request, canonical_email=canonical_email)

    authenticated = authenticate(
        request,
        username=canonical_email,
        password=password,
    )
    user = authenticated if isinstance(authenticated, User) else None
    # O sistema web é só da equipe: paciente entra apenas pelo aplicativo.
    clinics = active_web_clinics_for_actor(user) if user is not None else []
    global_staff = user is not None and (user.is_staff or user.is_superuser)
    if user is None or (not clinics and not global_staff):
        for key in keys:
            _record_rate_limited_action(key=key, window=window)
        raise LoginRejectedError(GENERIC_LOGIN_ERROR)

    clinic = clinics[0] if clinics else None
    django_login(request, user)
    if clinic is not None:
        request.session[CLINIC_SESSION_KEY] = str(clinic.pk)
    else:
        request.session.pop(CLINIC_SESSION_KEY, None)
    register_current_session(request=request, user=user)
    cache.delete_many(keys)
    if clinic is not None:
        _audit_session(
            request=request,
            clinic_id=clinic.pk,
            actor_id=user.pk,
            action="login",
        )
    return clinic


def logout_user(*, request: HttpRequest) -> None:
    """Audit the active tenant session when possible and always flush it."""
    user = request.user if isinstance(request.user, User) else None
    raw_clinic_id = request.session.get(CLINIC_SESSION_KEY)
    try:
        clinic_id = UUID(str(raw_clinic_id))
    except TypeError, ValueError, AttributeError:
        clinic_id = None
    try:
        if user is not None and clinic_id is not None:
            allowed_clinics = {clinic.pk for clinic in active_clinics_for_actor(user)}
            if clinic_id in allowed_clinics:
                _audit_session(
                    request=request,
                    clinic_id=clinic_id,
                    actor_id=user.pk,
                    action="update",
                )
    finally:
        django_logout(request)


def _app_link(path: str, **params: str) -> str:
    """Deep link into the patient app (custom scheme registered by the app)."""
    from urllib.parse import urlencode

    scheme = str(getattr(settings, "MOBILE_APP_SCHEME", "auroraelo-posalta"))
    return f"{scheme}://{path}?{urlencode(params)}"


def request_password_recovery(
    *, request: HttpRequest, email: str, channel: str = "web"
) -> None:
    """Send a short-lived reset link while preserving a generic HTTP contract.

    Team members get the web link. Patients use only the mobile app, so a person who
    is only a patient gets the code and the app link instead. ``channel="mobile"``
    (requested from the app) sends mail only to people who are patients.
    """
    canonical_email = UserManager.canonical_email(email)
    attempts, window = _rate_limit_settings(
        attempts_name="PASSWORD_RECOVERY_RATE_LIMIT_ATTEMPTS",
        window_name="PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS",
    )
    origin_key = _rate_limit_key(
        scope="password-recovery",
        request=request,
        identity=canonical_email,
    )
    identity_key = _identity_rate_limit_key(
        scope="password-recovery", identity=canonical_email
    )
    keys = (origin_key, identity_key)
    if any(_is_rate_limited(key=key, attempts=attempts) for key in keys):
        raise RecoveryRateLimitedError(GENERIC_RECOVERY_RESPONSE)
    for key in keys:
        _record_rate_limited_action(key=key, window=window)

    user = User.objects.filter(email=canonical_email, is_active=True).first()
    if user is None:
        return
    is_patient = bool(active_clinics_with_role(user, "patient"))
    on_team = bool(active_web_clinics_for_actor(user))
    if channel == "mobile":
        if not is_patient:
            return
        use_app = True
    else:
        use_app = is_patient and not on_team
        if not (on_team or is_patient):
            return
    if not use_app and not on_team:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    recipient_lang = getattr(user, "preferred_language", None) or "pt-br"
    with translation.override(recipient_lang):
        subject = _("Recuperação de acesso")
        if use_app:
            code = f"{uid}.{token}"
            body = _(
                "Recebemos uma solicitação para redefinir sua senha no aplicativo "
                "Aurora Elo Pós-alta.\n\n"
                "Abra o link no celular em que o aplicativo está instalado: "
                "%(app_link)s\n\n"
                "Se o link não abrir, copie o código abaixo no aplicativo: "
                "%(code)s\n\n"
                "Se você não fez esta solicitação, ignore esta mensagem."
            ) % {"app_link": _app_link("reset", code=code), "code": code}
        else:
            path = reverse("password_reset", kwargs={"uid": uid, "token": token})
            reset_url = request.build_absolute_uri(path)
            body = _(
                "Recebemos uma solicitação para redefinir sua senha.\n\n"
                "Acesse o link a seguir: %(reset_url)s\n\n"
                "Se você não fez esta solicitação, ignore esta mensagem."
            ) % {"reset_url": reset_url}
        message = EmailMultiAlternatives(
            subject=str(subject),
            body=str(body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
    try:
        message.send()
    except Exception:
        logger.exception(
            "password recovery delivery failed",
            extra={"event": "accounts.password_recovery.delivery_error"},
        )


def password_reset_identity(*, uid: str, token: str) -> User | None:
    """Resolve and validate a reset credential without exposing lookup details."""
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.filter(pk=user_id, is_active=True).first()
    except ValueError, TypeError, OverflowError, ValidationError:
        return None
    if user is None or not default_token_generator.check_token(user, token):
        return None
    return user


@transaction.atomic
def reset_password(*, uid: str, token: str, new_password: str) -> bool:
    """Consume a reset token and invalidate every session through the auth hash."""
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = (
            User.objects.select_for_update().filter(pk=user_id, is_active=True).first()
        )
    except ValueError, TypeError, OverflowError, ValidationError:
        return False
    if user is None or not default_token_generator.check_token(user, token):
        return False
    validate_password(new_password, user=user)

    affected_clinic_ids = active_clinic_ids_for_actor(user)
    changed_at = timezone.now()
    user.set_password(new_password)
    user.security_state_changed_at = changed_at
    user.save(
        update_fields=(
            "password",
            "credentials_changed_at",
            "security_state_changed_at",
        )
    )
    for clinic_id in affected_clinic_ids:
        _publish_account_audit(
            clinic_id=clinic_id,
            actor_id=user.pk,
            action="update",
            resource_type="user_credential",
            resource_id=str(user.pk),
            request_id=uuid4(),
            network_origin=None,
        )
    return True


def _active_clinic_for_action(
    *, clinic_id: UUID, actor: User, action: str
) -> ClinicIdentity:
    """Resolve one active tenant for a member or global platform operator."""
    if current_actor_is_active(actor) and (actor.is_staff or actor.is_superuser):
        return active_clinic_for_infrastructure(clinic_id=clinic_id)
    return authorized_active_clinic(
        clinic_id=clinic_id,
        actor=actor,
        action=action,
    )


def _audit_invitation(
    *, invitation: ClinicInvitation, actor_id: UUID | None, action: str
) -> None:
    """Publish one minimized invitation event without recipient or token data."""
    _publish_account_audit(
        clinic_id=invitation.clinic_id,
        actor_id=actor_id,
        action=action,
        resource_type="clinic_invitation",
        resource_id=str(invitation.id),
        request_id=uuid4(),
        network_origin=None,
    )


@transaction.atomic
def issue_invitation(
    *,
    clinic_id: UUID,
    issuer: User,
    recipient_email: str,
    initial_role: str,
    expires_at: datetime,
    initial_category: str = "",
    unit_name: str = "",
    valid_from: date | None = None,
    valid_until: date | None = None,
) -> IssuedInvitation:
    """Issue one auditable invitation for a clinic member or global operator."""
    clinic = _active_clinic_for_action(
        clinic_id=clinic_id,
        actor=issuer,
        action="invitation.issue",
    )
    if expires_at <= timezone.now():
        raise ValueError(INVALID_INVITATION_MESSAGE)
    if not is_membership_role_supported(initial_role):
        raise ValueError("initial_role is invalid")
    allowed_categories = {"", "psychologist", "psychiatrist", "therapist", "other"}
    if initial_category not in allowed_categories:
        raise ValueError("initial_category is invalid")
    if initial_category and initial_role != "therapist":
        raise ValueError("initial_category requires the therapist role")
    effective_valid_from = valid_from or timezone.localdate()
    if valid_until is not None and valid_until < effective_valid_from:
        raise ValueError("valid_until must not precede valid_from")
    recipient = UserManager.canonical_email(recipient_email)
    if not recipient:
        raise ValueError("recipient_email is required")

    raw_token = secrets.token_urlsafe(32)
    invitation = ClinicInvitation.infrastructure_objects.create(
        clinic_id=clinic.id,
        issuer=issuer,
        recipient_email=recipient,
        initial_role=initial_role,
        initial_category=initial_category,
        unit_name=unit_name.strip(),
        valid_from=effective_valid_from,
        valid_until=valid_until,
        token_digest=_token_digest(raw_token),
        expires_at=expires_at,
    )
    _audit_invitation(
        invitation=invitation,
        actor_id=issuer.id,
        action="create",
    )
    return IssuedInvitation(invitation=invitation, raw_token=raw_token)


@transaction.atomic
def accept_invitation(
    *,
    raw_token: str,
    password: str,
    first_name: str,
    last_name: str,
    actor: User | None = None,
) -> User:
    """Consume one invitation for a new or explicitly authenticated identity."""
    now = timezone.now()
    invitation = (
        ClinicInvitation.infrastructure_objects.select_for_update()
        .filter(
            token_digest=_token_digest(raw_token),
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
            clinic__is_active=True,
        )
        .first()
    )
    if invitation is None:
        raise ValueError(INVALID_INVITATION_MESSAGE)

    existing = (
        User.objects.select_for_update()
        .filter(email=invitation.recipient_email, is_active=True)
        .first()
    )
    if existing is not None:
        if actor is None or actor.pk != existing.pk or not actor.is_authenticated:
            raise PermissionDenied
        user = existing
        if invitation.clinic_id not in active_clinic_ids_for_actor(user):
            activate_invited_membership(
                clinic_id=invitation.clinic_id,
                user_id=user.id,
                role=invitation.initial_role,
                unit_name=invitation.unit_name,
                valid_from=invitation.valid_from,
                valid_until=invitation.valid_until,
                authorized_by_id=invitation.issuer_id,
            )
    else:
        if actor is not None:
            raise PermissionDenied

        candidate = User(
            email=invitation.recipient_email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        validate_password(password, user=candidate)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=candidate.email,
                    password=password,
                    first_name=candidate.first_name,
                    last_name=candidate.last_name,
                )
        except IntegrityError as error:
            raise ValueError(INVALID_INVITATION_MESSAGE) from error
        create_clinic_membership(
            clinic_id=invitation.clinic_id,
            user_id=user.id,
            role=invitation.initial_role,
            unit_name=invitation.unit_name,
            valid_from=invitation.valid_from,
            valid_until=invitation.valid_until,
            authorized_by_id=invitation.issuer_id,
        )
    invitation.used_at = now
    invitation.save(update_fields=("used_at", "updated_at"))
    _audit_invitation(
        invitation=invitation,
        actor_id=user.id,
        action="update",
    )
    invitation_accepted.send(
        sender=ClinicInvitation,
        clinic_id=invitation.clinic_id,
        invitation_id=invitation.pk,
        actor_id=user.pk,
    )
    return user


def invitation_clinic_id(*, raw_token: str) -> UUID:
    """Resolve a high-entropy invitation credential to its server-owned tenant."""
    clinic_id = (
        ClinicInvitation.infrastructure_objects.filter(
            token_digest=_token_digest(raw_token),
        )
        .values_list("clinic_id", flat=True)
        .first()
    )
    if clinic_id is None:
        raise ValueError(INVALID_INVITATION_MESSAGE)
    return clinic_id


def invitation_initial_role(*, raw_token: str) -> str:
    """Resolve a valid, unused invitation credential to the role it grants."""
    row = (
        ClinicInvitation.infrastructure_objects.filter(
            token_digest=_token_digest(raw_token),
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            clinic__is_active=True,
        )
        .values_list("initial_role", flat=True)
        .first()
    )
    if row is None:
        raise ValueError(INVALID_INVITATION_MESSAGE)
    return str(row)


def authenticate_identity(*, request: HttpRequest, email: str, password: str) -> User:
    """Verify an existing account password under the shared login failure budget."""
    canonical_email = UserManager.canonical_email(email)
    keys, window = _login_budget(request=request, canonical_email=canonical_email)
    authenticated = authenticate(request, username=canonical_email, password=password)
    user = authenticated if isinstance(authenticated, User) else None
    if user is None:
        for key in keys:
            _record_rate_limited_action(key=key, window=window)
        raise LoginRejectedError(GENERIC_LOGIN_ERROR)
    cache.delete_many(keys)
    return user


def activate_patient_account(
    *,
    request: HttpRequest,
    raw_token: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    """Consume a patient invitation from the mobile app.

    A new identity chooses its password here. A person who already has an account
    (for example, a patient of another clinic) proves it with the current password.
    Only invitations that grant the ``patient`` role are accepted.
    """
    if invitation_initial_role(raw_token=raw_token) != "patient":
        raise ValueError(INVALID_INVITATION_MESSAGE)
    recipient = (
        ClinicInvitation.infrastructure_objects.filter(
            token_digest=_token_digest(raw_token)
        )
        .values_list("recipient_email", flat=True)
        .first()
    )
    existing = (
        User.objects.filter(email=recipient, is_active=True).first()
        if recipient
        else None
    )
    if existing is not None:
        actor = authenticate_identity(
            request=request, email=existing.email, password=password
        )
        return accept_invitation(
            raw_token=raw_token,
            password="",
            first_name="",
            last_name="",
            actor=actor,
        )
    return accept_invitation(
        raw_token=raw_token,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )


def send_patient_activation_email(
    *, recipient_email: str, raw_token: str, language: str
) -> bool:
    """Send the activation code and the app link to a newly invited patient."""
    with translation.override(language or "pt-br"):
        subject = _("Seu acesso ao aplicativo Aurora Elo Pós-alta")
        body = _(
            "Sua clínica convidou você para o aplicativo Aurora Elo Pós-alta.\n\n"
            "Abra o link no celular em que o aplicativo está instalado: "
            "%(app_link)s\n\n"
            "Se o link não abrir, copie o código abaixo no aplicativo: "
            "%(code)s\n\n"
            "O convite vale por 7 dias e só pode ser usado uma vez."
        ) % {"app_link": _app_link("activate", code=raw_token), "code": raw_token}
        message = EmailMultiAlternatives(
            subject=str(subject),
            body=str(body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
    try:
        message.send()
    except Exception:
        logger.exception(
            "patient activation delivery failed",
            extra={"event": "accounts.patient_activation.delivery_error"},
        )
        return False
    return True


# ─── OTP de 6 dígitos para ativação sem senha ─────────────────────────────
# Gerado via CSPRNG; armazenado no Redis com TTL de 15 min; zero migrations.

_OTP_TTL_SECONDS: int = 15 * 60  # 15 minutos
_OTP_MAX_ATTEMPTS: int = 5


def _otp_cache_key(*, token_digest: str) -> str:
    """Derive a stable, namespaced Redis key from the invitation digest."""
    return f"accounts:patient_otp:{token_digest}"


def _otp_attempts_key(*, token_digest: str) -> str:
    return f"accounts:patient_otp_attempts:{token_digest}"


def issue_patient_otp(*, raw_token: str, language: str, recipient_email: str) -> str:
    """Generate a 6-digit PIN, cache it in Redis, and email it to the patient.

    Returns the plain PIN (used only in admin display; never persisted in DB).
    Raises ``ValueError`` if the invitation is already used or expired.
    """
    token_digest = _token_digest(raw_token)

    valid = (
        ClinicInvitation.infrastructure_objects.filter(
            token_digest=token_digest,
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            clinic__is_active=True,
        )
        .values_list("id", flat=True)
        .exists()
    )
    if not valid:
        raise ValueError(INVALID_INVITATION_MESSAGE)

    pin = f"{secrets.randbelow(1_000_000):06d}"
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()

    cache_key = _otp_cache_key(token_digest=token_digest)
    cache.set(cache_key, pin_hash, timeout=_OTP_TTL_SECONDS)
    cache.delete(_otp_attempts_key(token_digest=token_digest))

    _send_otp_email(
        recipient_email=recipient_email,
        pin=pin,
        language=language,
    )

    logger.info(
        "patient otp issued",
        extra={
            "event": "accounts.patient_otp.issued",
            "token_digest_prefix": token_digest[:8],
        },
    )
    return pin


def _send_otp_email(
    *, recipient_email: str, pin: str, language: str
) -> None:
    """Send the 6-digit PIN email to the patient."""
    with translation.override(language or "pt-br"):
        subject = _("Seu código de acesso — Aurora Elo Pós-alta")
        body = _(
            "Sua clínica gerou um código de acesso para o aplicativo "
            "Aurora Elo Pós-alta.\n\n"
            "Código de 6 dígitos: %(pin)s\n\n"
            "Abra o aplicativo, informe seu nome e depois este código.\n"
            "O código expira em 15 minutos e só pode ser usado uma vez.\n\n"
            "Se você não esperava este código, entre em contato com sua clínica."
        ) % {"pin": pin}
        message = EmailMultiAlternatives(
            subject=str(subject),
            body=str(body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
    try:
        message.send()
    except Exception:
        logger.exception(
            "patient otp delivery failed",
            extra={"event": "accounts.patient_otp.delivery_error"},
        )


def activate_patient_by_otp(
    *,
    request: HttpRequest,
    raw_token: str,
    pin: str,
    first_name: str,
    last_name: str,
) -> User:
    """Consume a 6-digit OTP to activate a patient account without a password.

    Steps:
      1. Rate-limit attempts (5 tries per 15-min window).
      2. Validate PIN against cached hash (constant-time compare).
      3. Validate invitation role = ``patient``.
      4. Create or link the user via ``accept_invitation``.
      5. New accounts get an unusable password — app auth via Bearer only.
      6. Consume the OTP from cache (one-time use).
    """
    token_digest = _token_digest(raw_token)

    attempts_key = _otp_attempts_key(token_digest=token_digest)
    attempts: int = cache.get(attempts_key, 0)
    if attempts >= _OTP_MAX_ATTEMPTS:
        raise LoginRateLimitedError("Muitas tentativas. Aguarde 15 minutos.")

    cache_key = _otp_cache_key(token_digest=token_digest)
    stored_hash: str | None = cache.get(cache_key)
    if not stored_hash:
        raise LoginRejectedError(GENERIC_LOGIN_ERROR)

    candidate_hash = hashlib.sha256(pin.strip().encode()).hexdigest()
    if not secrets.compare_digest(candidate_hash, stored_hash):
        cache.set(attempts_key, attempts + 1, timeout=_OTP_TTL_SECONDS)
        raise LoginRejectedError(GENERIC_LOGIN_ERROR)

    if invitation_initial_role(raw_token=raw_token) != "patient":
        raise ValueError(INVALID_INVITATION_MESSAGE)

    recipient = (
        ClinicInvitation.infrastructure_objects.filter(token_digest=token_digest)
        .values_list("recipient_email", flat=True)
        .first()
    )
    existing = (
        User.objects.filter(email=recipient, is_active=True).first()
        if recipient
        else None
    )

    if existing is not None:
        user = accept_invitation(
            raw_token=raw_token,
            password="",
            first_name="",
            last_name="",
            actor=existing,
        )
    else:
        dummy_password = secrets.token_urlsafe(32)
        user = accept_invitation(
            raw_token=raw_token,
            password=dummy_password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

    cache.delete(cache_key)
    cache.delete(attempts_key)

    logger.info(
        "patient otp consumed",
        extra={"event": "accounts.patient_otp.consumed", "user_id": str(user.pk)},
    )
    return user


@transaction.atomic
def revoke_invitation(
    *, clinic_id: UUID, invitation_id: UUID, actor: User
) -> ClinicInvitation:
    """Revoke one unused invitation through its tenant-scoped interface."""
    _active_clinic_for_action(
        clinic_id=clinic_id,
        actor=actor,
        action="invitation.revoke",
    )
    invitation = (
        ClinicInvitation.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(pk=invitation_id, used_at__isnull=True, revoked_at__isnull=True)
        .first()
    )
    if invitation is None:
        raise PermissionDenied
    invitation.revoked_at = timezone.now()
    invitation.revoked_by = actor
    invitation.save(update_fields=("revoked_at", "revoked_by", "updated_at"))
    _audit_invitation(
        invitation=invitation,
        actor_id=actor.id,
        action="update",
    )
    return invitation


@transaction.atomic
def resend_invitation(
    *,
    clinic_id: UUID,
    invitation_id: UUID,
    actor: User,
    expires_at: datetime,
) -> IssuedInvitation:
    """Replace a pending invitation with a fresh one without erasing history."""
    original = (
        ClinicInvitation.objects.for_clinic(clinic_id)
        .select_for_update()
        .filter(pk=invitation_id, used_at__isnull=True, revoked_at__isnull=True)
        .first()
    )
    if original is None:
        raise PermissionDenied
    revoke_invitation(clinic_id=clinic_id, invitation_id=invitation_id, actor=actor)
    return issue_invitation(
        clinic_id=clinic_id,
        issuer=actor,
        recipient_email=original.recipient_email,
        initial_role=original.initial_role,
        initial_category=original.initial_category,
        unit_name=original.unit_name,
        valid_from=original.valid_from,
        valid_until=original.valid_until,
        expires_at=expires_at,
    )


def _client_label(request: HttpRequest) -> str:
    raw = str(request.META.get("HTTP_USER_AGENT", "Navegador desconhecido"))
    product = raw.rsplit("/", 1)[0].strip()
    return product[:120] or "Navegador desconhecido"


def _network_hint(request: HttpRequest) -> str:
    origin = str(request.META.get("REMOTE_ADDR", ""))
    if not origin:
        return ""
    return salted_hmac(
        "accounts.session-network",
        origin,
        secret=settings.SECRET_KEY,
        algorithm="sha256",
    ).hexdigest()[:16]


def register_current_session(
    *,
    request: HttpRequest,
    user: User,
    absolute_expires_at: datetime | None = None,
) -> AccountSession:
    """Register or refresh minimized metadata for the current bearer session."""
    if request.session.session_key is None:
        request.session.save()
    session_key = request.session.session_key
    if session_key is None:
        raise RuntimeError("Authenticated session key is unavailable.")
    now = timezone.now()
    absolute_seconds = max(1, int(settings.ACCOUNT_SESSION_ABSOLUTE_SECONDS))
    digest = _session_digest(session_key)
    existing = AccountSession.objects.filter(session_key_digest=digest).first()
    if existing is not None:
        existing.last_seen_at = now
        existing.client_label = _client_label(request)
        existing.network_hint = _network_hint(request)
        existing.save(
            update_fields=(
                "last_seen_at",
                "client_label",
                "network_hint",
                "updated_at",
            )
        )
        return existing
    return AccountSession.objects.create_for_session(
        user=user,
        session_key=session_key,
        client_label=_client_label(request),
        network_hint=_network_hint(request),
        absolute_expires_at=absolute_expires_at
        or now + timedelta(seconds=absolute_seconds),
    )


@transaction.atomic
def rotate_current_session_tracking(
    *, request: HttpRequest, user: User
) -> AccountSession:
    """Replace device tracking after intentional Django session-key rotation."""
    previous = getattr(request, "account_session", None)
    previous_absolute_expiry = None
    if (
        isinstance(previous, AccountSession)
        and previous.user_id == user.pk
        and previous.revoked_at is None
    ):
        previous_absolute_expiry = previous.absolute_expires_at
        previous.revoked_at = timezone.now()
        previous.save(update_fields=("revoked_at", "updated_at"))
    return register_current_session(
        request=request,
        user=user,
        absolute_expires_at=previous_absolute_expiry,
    )


def validate_current_session(*, request: HttpRequest, user: User) -> bool:
    """Fail closed on revoked, idle, absolute-expired, or unknown sessions."""
    session_key = request.session.session_key
    if session_key is None:
        return False
    account_session = AccountSession.objects.filter(
        user=user,
        session_key_digest=_session_digest(session_key),
    ).first()
    if account_session is None:
        if not getattr(settings, "ACCOUNT_SESSION_ALLOW_UNKNOWN", False):
            return False
        account_session = register_current_session(request=request, user=user)
    now = timezone.now()
    idle_seconds = max(1, int(settings.ACCOUNT_SESSION_IDLE_SECONDS))
    expired = (
        account_session.revoked_at is not None
        or account_session.absolute_expires_at <= now
        or account_session.last_seen_at <= now - timedelta(seconds=idle_seconds)
    )
    if expired:
        if account_session.revoked_at is None:
            account_session.revoked_at = now
            account_session.save(update_fields=("revoked_at", "updated_at"))
        Session.objects.filter(session_key=session_key).delete()
        return False
    account_session.last_seen_at = now
    account_session.save(update_fields=("last_seen_at", "updated_at"))
    return True


@transaction.atomic
def revoke_account_session(
    *,
    actor: User,
    account_session_id: UUID,
    clinic_id: UUID | None = None,
) -> None:
    """Revoke one session owned by the authenticated identity."""
    account_session = (
        AccountSession.objects.select_for_update()
        .filter(
            pk=account_session_id,
            user=actor,
            revoked_at__isnull=True,
        )
        .first()
    )
    if account_session is None:
        raise PermissionDenied
    clinics = active_clinics_for_actor(actor)
    authorized_clinic_ids = {clinic.pk for clinic in clinics}
    audit_clinic_id = clinic_id or (clinics[0].pk if clinics else None)
    if audit_clinic_id is not None and audit_clinic_id not in authorized_clinic_ids:
        raise PermissionDenied
    Session.objects.filter(session_key=account_session.decrypt_session_key()).delete()
    account_session.revoked_at = timezone.now()
    account_session.save(update_fields=("revoked_at", "updated_at"))
    if audit_clinic_id is not None:
        _publish_account_audit(
            clinic_id=audit_clinic_id,
            actor_id=actor.pk,
            action="update",
            resource_type="session",
            resource_id=str(account_session.pk),
            request_id=uuid4(),
            network_origin=None,
        )


@transaction.atomic
def revoke_other_sessions(
    *,
    actor: User,
    current_session_id: UUID,
    clinic_id: UUID | None = None,
) -> int:
    """Revoke every live session except the explicitly retained current one."""
    sessions = list(
        AccountSession.objects.select_for_update()
        .filter(
            user=actor,
            revoked_at__isnull=True,
        )
        .exclude(pk=current_session_id)
    )
    clinics = active_clinics_for_actor(actor)
    authorized_clinic_ids = {clinic.pk for clinic in clinics}
    audit_clinic_id = clinic_id or (clinics[0].pk if clinics else None)
    if audit_clinic_id is not None and audit_clinic_id not in authorized_clinic_ids:
        raise PermissionDenied
    now = timezone.now()
    for account_session in sessions:
        Session.objects.filter(
            session_key=account_session.decrypt_session_key()
        ).delete()
        account_session.revoked_at = now
        account_session.save(update_fields=("revoked_at", "updated_at"))
    if audit_clinic_id is not None:
        _publish_account_audit(
            clinic_id=audit_clinic_id,
            actor_id=actor.pk,
            action="update",
            resource_type="session_set",
            resource_id=str(actor.pk),
            request_id=uuid4(),
            network_origin=None,
        )
    return len(sessions)


def reauthenticate_sensitive_action(*, actor: User, password: str) -> bool:
    """Verify the current credential immediately before a high-impact action."""
    attempts, window = _rate_limit_settings(
        attempts_name="SENSITIVE_REAUTH_RATE_LIMIT_ATTEMPTS",
        window_name="SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS",
    )
    key = _identity_rate_limit_key(scope="sensitive-reauth", identity=str(actor.pk))
    if cache.add(key, 1, timeout=window):
        reserved_attempts = 1
    else:
        try:
            reserved_attempts = cache.incr(key)
        except ValueError:
            cache.add(key, 1, timeout=window)
            reserved_attempts = 1
    if reserved_attempts > attempts:
        raise SensitiveActionRateLimitedError(
            "Muitas tentativas. Tente novamente mais tarde."
        )
    verified = bool(password) and actor.check_password(password)
    if verified:
        cache.delete(key)
    return verified


__all__ = [
    "GENERIC_LOGIN_ERROR",
    "GENERIC_RECOVERY_RESPONSE",
    "ClinicInvitation",
    "IssuedInvitation",
    "LoginRateLimitedError",
    "LoginRejectedError",
    "SensitiveActionRateLimitedError",
    "RecoveryRateLimitedError",
    "Service",
    "User",
    "accept_invitation",
    "activate_patient_account",
    "authenticate_identity",
    "invitation_initial_role",
    "send_patient_activation_email",
    "invitation_clinic_id",
    "issue_invitation",
    "login_user",
    "logout_user",
    "password_reset_identity",
    "request_password_recovery",
    "reset_password",
    "register_current_session",
    "reauthenticate_sensitive_action",
    "rotate_current_session_tracking",
    "revoke_account_session",
    "resend_invitation",
    "revoke_invitation",
    "revoke_other_sessions",
    "validate_current_session",
    "verify_credentials",
    "issue_patient_otp",
    "activate_patient_by_otp",
]
