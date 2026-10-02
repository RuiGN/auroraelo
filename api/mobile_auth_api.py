"""Login, renovação e sessões do app do paciente (`/api/v1/mobile/auth/`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from ninja import Field, Router, Schema, Status

from accounts.services import (
    GENERIC_LOGIN_ERROR,
    GENERIC_RECOVERY_RESPONSE,
    RecoveryRateLimitedError,
    activate_patient_account,
    activate_patient_by_otp,
    invitation_clinic_id,
    issue_patient_otp,
    password_reset_identity,
    request_password_recovery,
    reset_password,
)
from mobile_api.contracts import RevokeReason
from mobile_api.selectors import active_sessions_for_patient
from mobile_api.services import (
    ClinicChoiceRequiredError,
    InvalidMobileTokenError,
    IssuedTokens,
    LoginRateLimitedError,
    LoginRejectedError,
    refresh_session,
    revoke_other_sessions,
    revoke_session,
    revoke_session_by_id,
    start_session,
    start_session_for_user,
)

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    network_origin,
    request_id,
)

router = Router(tags=["Mobile · Sessão"])
bearer = PatientBearerAuth(allow_blocked_tenant=True)


class LoginIn(Schema):
    email: str = Field(max_length=254)
    password: str = Field(max_length=1024)
    clinic_id: UUID | None = None
    device_label: str = Field(default="", max_length=500)
    platform: str = Field(default="other", max_length=16)
    app_version: str = Field(default="", max_length=100)


class RefreshIn(Schema):
    refresh_token: str = Field(max_length=128)


class ClinicOut(Schema):
    id: UUID
    name: str


class PatientOut(Schema):
    id: UUID
    display_name: str


class TokensOut(Schema):
    session_id: UUID
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    clinic: ClinicOut
    patient: PatientOut


class ClinicChoiceOut(Schema):
    detail: str
    code: str
    clinics: list[ClinicOut]


class SessionOut(Schema):
    id: UUID
    device_label: str
    platform: str
    app_version: str
    created_at: datetime
    last_used_at: datetime
    is_current: bool


def _tokens(issued: IssuedTokens) -> TokensOut:
    session = issued.session
    profile = session.patient_profile
    return TokensOut(
        session_id=session.pk,
        access_token=issued.access_token,
        access_expires_at=session.access_expires_at,
        refresh_token=issued.refresh_token,
        refresh_expires_at=session.refresh_expires_at,
        clinic=ClinicOut(id=session.clinic.pk, name=session.clinic.name),
        patient=PatientOut(
            id=profile.pk, display_name=profile.social_name or profile.full_name
        ),
    )


@router.post(
    "/login/",
    auth=None,
    response={
        200: TokensOut,
        401: MobileErrorOut,
        409: ClinicChoiceOut,
        429: MobileErrorOut,
    },
)
def login(request: HttpRequest, payload: LoginIn):
    """Abre uma sessão para o paciente. Devolve o par de tokens uma única vez."""
    try:
        issued = start_session(
            request=request,
            email=payload.email,
            password=payload.password,
            clinic_id=payload.clinic_id,
            device_label=payload.device_label,
            platform=payload.platform,
            app_version=payload.app_version,
            request_id=request_id(request),
        )
    except LoginRateLimitedError:
        return Status(
            429,
            {
                "detail": "Muitas tentativas. Aguarde alguns minutos.",
                "code": "rate_limited",
            },
        )
    except LoginRejectedError:
        return Status(
            401, {"detail": GENERIC_LOGIN_ERROR, "code": "invalid_credentials"}
        )
    except ClinicChoiceRequiredError as exc:
        return Status(
            409,
            {
                "detail": "Escolha a clínica para continuar.",
                "code": "clinic_choice_required",
                "clinics": [{"id": pk, "name": name} for pk, name in exc.clinics],
            },
        )
    return Status(200, _tokens(issued))


class ActivateIn(Schema):
    code: str = Field(max_length=128)
    password: str = Field(max_length=1024)
    first_name: str = Field(default="", max_length=150)
    last_name: str = Field(default="", max_length=150)
    device_label: str = Field(default="", max_length=500)
    platform: str = Field(default="other", max_length=16)
    app_version: str = Field(default="", max_length=100)


class RecoveryIn(Schema):
    email: str = Field(max_length=254)


class ResetIn(Schema):
    code: str = Field(max_length=256)
    new_password: str = Field(max_length=1024)


class PasswordErrorOut(Schema):
    detail: str
    code: str
    errors: list[str]


@router.post(
    "/activate/",
    auth=None,
    response={
        200: TokensOut,
        401: MobileErrorOut,
        422: PasswordErrorOut,
        429: MobileErrorOut,
    },
)
def activate(request: HttpRequest, payload: ActivateIn):
    """Ativa a conta do paciente com o código do convite e já abre a sessão.

    Conta nova escolhe a senha aqui. Quem já tem conta (por exemplo, paciente de
    outra clínica) informa a senha atual. O código vem por e-mail com um link que
    abre o app.
    """
    code = payload.code.strip()
    try:
        clinic_id = invitation_clinic_id(raw_token=code)
        user = activate_patient_account(
            request=request,
            raw_token=code,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except LoginRateLimitedError:
        return Status(
            429,
            {
                "detail": "Muitas tentativas. Aguarde alguns minutos.",
                "code": "rate_limited",
            },
        )
    except LoginRejectedError:
        return Status(
            401, {"detail": GENERIC_LOGIN_ERROR, "code": "invalid_credentials"}
        )
    except ValidationError as exc:
        return Status(
            422,
            {
                "detail": "Senha não aceita.",
                "code": "weak_password",
                "errors": list(exc.messages),
            },
        )
    except ValueError, PermissionDenied:
        return Status(
            422,
            {
                "detail": "Convite inválido ou expirado.",
                "code": "invalid_code",
                "errors": [],
            },
        )
    try:
        issued = start_session(
            request=request,
            email=user.email,
            password=payload.password,
            clinic_id=clinic_id,
            device_label=payload.device_label,
            platform=payload.platform,
            app_version=payload.app_version,
            request_id=request_id(request),
        )
    except LoginRateLimitedError:
        return Status(
            429,
            {
                "detail": "Muitas tentativas. Aguarde alguns minutos.",
                "code": "rate_limited",
            },
        )
    except LoginRejectedError, ClinicChoiceRequiredError:
        return Status(
            401, {"detail": GENERIC_LOGIN_ERROR, "code": "invalid_credentials"}
        )
    return Status(200, _tokens(issued))


class ActivateOtpIn(Schema):
    """Dados para ativação via código de 6 dígitos (sem senha)."""

    code: str = Field(max_length=128, description="Token do convite (vem no link do email)")
    pin: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$", description="PIN de 6 dígitos")
    first_name: str = Field(default="", max_length=150)
    last_name: str = Field(default="", max_length=150)
    device_label: str = Field(default="", max_length=500)
    platform: str = Field(default="other", max_length=16)
    app_version: str = Field(default="", max_length=100)


@router.post(
    "/activate-otp/",
    auth=None,
    response={
        200: TokensOut,
        401: MobileErrorOut,
        429: MobileErrorOut,
    },
)
def activate_otp(request: HttpRequest, payload: ActivateOtpIn):
    """Ativa conta do paciente com nome + PIN de 6 dígitos e abre a sessão.

    Fluxo:
      - A clínica chama ``POST /patients/{id}/send-otp/`` → paciente recebe PIN por email.
      - Paciente abre o app, informa nome e digita o PIN.
      - Endpoint valida, cria conta se necessária, e retorna os tokens Bearer.
    """
    code = payload.code.strip()
    try:
        clinic_id = invitation_clinic_id(raw_token=code)
        user = activate_patient_by_otp(
            request=request,
            raw_token=code,
            pin=payload.pin,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except LoginRateLimitedError:
        return Status(
            429,
            {"detail": "Muitas tentativas. Aguarde alguns minutos.", "code": "rate_limited"},
        )
    except (LoginRejectedError, ValueError, PermissionDenied):
        return Status(
            401, {"detail": GENERIC_LOGIN_ERROR, "code": "invalid_credentials"}
        )
    try:
        issued = start_session_for_user(
            request=request,
            user=user,
            clinic_id=clinic_id,
            device_label=payload.device_label,
            platform=payload.platform,
            app_version=payload.app_version,
            request_id=request_id(request),
        )
    except LoginRateLimitedError:
        return Status(
            429,
            {"detail": "Muitas tentativas. Aguarde alguns minutos.", "code": "rate_limited"},
        )
    return Status(200, _tokens(issued))


@router.post(
    "/password-recovery/",
    auth=None,
    response={202: dict[str, str], 429: MobileErrorOut},
)
def password_recovery(request: HttpRequest, payload: RecoveryIn):
    """Pede o código de recuperação; a resposta é sempre a mesma."""
    try:
        request_password_recovery(
            request=request, email=payload.email, channel="mobile"
        )
    except RecoveryRateLimitedError:
        return Status(
            429,
            {
                "detail": "Muitas tentativas. Aguarde alguns minutos.",
                "code": "rate_limited",
            },
        )
    return Status(202, {"detail": GENERIC_RECOVERY_RESPONSE})


@router.post(
    "/password-reset/",
    auth=None,
    response={204: None, 400: MobileErrorOut, 422: PasswordErrorOut},
)
def password_reset(request: HttpRequest, payload: ResetIn):
    """Troca a senha com o código recebido por e-mail. Encerra todas as sessões."""
    uid, _, token = payload.code.strip().partition(".")
    if password_reset_identity(uid=uid, token=token) is None:
        return Status(
            400, {"detail": "Código inválido ou expirado.", "code": "invalid_code"}
        )
    try:
        done = reset_password(uid=uid, token=token, new_password=payload.new_password)
    except ValidationError as exc:
        return Status(
            422,
            {
                "detail": "Senha não aceita.",
                "code": "weak_password",
                "errors": list(exc.messages),
            },
        )
    if not done:
        return Status(
            400, {"detail": "Código inválido ou expirado.", "code": "invalid_code"}
        )
    return Status(204, None)


@router.post(
    "/refresh/",
    auth=None,
    response={200: TokensOut, 401: MobileErrorOut},
)
def refresh(request: HttpRequest, payload: RefreshIn):
    """Troca o token de renovação. O token anterior deixa de valer imediatamente."""
    try:
        issued = refresh_session(
            refresh_token=payload.refresh_token,
            request_id=request_id(request),
            network_origin=network_origin(request),
        )
    except InvalidMobileTokenError:
        return Status(
            401,
            {
                "detail": "Sessão encerrada. Entre novamente.",
                "code": "invalid_token",
            },
        )
    return Status(200, _tokens(issued))


@router.post("/logout/", auth=bearer, response={204: None})
def logout(request: HttpRequest):
    """Encerra a sessão deste aparelho."""
    context = mobile_context(request)
    revoke_session(
        session=context.session,
        reason=RevokeReason.LOGOUT,
        request_id=request_id(request),
    )
    return Status(204, None)


@router.get("/sessions/", auth=bearer, response=list[SessionOut])
def list_sessions(request: HttpRequest):
    """Aparelhos com sessão ativa da própria pessoa (nunca de outra)."""
    context = mobile_context(request)
    sessions = active_sessions_for_patient(
        clinic_id=context.clinic_id, user_id=context.user.pk
    )
    return [
        SessionOut(
            id=item.pk,
            device_label=item.device_label,
            platform=item.platform,
            app_version=item.app_version,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            is_current=item.pk == context.session.pk,
        )
        for item in sessions
    ]


@router.delete(
    "/sessions/{uuid:session_id}/",
    auth=bearer,
    response={204: None, 404: MobileErrorOut},
)
def revoke_device(
    request: HttpRequest, session_id: UUID
) -> Any:  # Ninja: Status[T]
    """Encerra outro aparelho. Id inexistente ou alheio responde igual (404)."""
    context = mobile_context(request)
    try:
        revoke_session_by_id(
            clinic_id=context.clinic_id,
            user_id=context.user.pk,
            session_id=session_id,
            request_id=request_id(request),
        )
    except PermissionDenied:
        return Status(404, {"detail": "Sessão não encontrada.", "code": "not_found"})
    return Status(204, None)


@router.post("/sessions/revoke-others/", auth=bearer, response={200: dict[str, int]})
def revoke_others(request: HttpRequest) -> Any:  # Ninja: Status[T]
    """Encerra todos os outros aparelhos, mantendo este."""
    context = mobile_context(request)
    count = revoke_other_sessions(
        session=context.session, request_id=request_id(request)
    )
    return Status(200, {"revoked": count})
