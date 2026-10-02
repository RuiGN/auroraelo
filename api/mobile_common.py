"""Autenticação e utilidades comuns às rotas do app do paciente (`/api/v1/mobile/`).

As rotas do app aceitam **somente** token de acesso no cabeçalho `Authorization`.
Cookie de sessão não vale aqui, o que também elimina CSRF. A clínica e o perfil de
paciente vêm da sessão gravada no servidor; nenhum cabeçalho ou parâmetro do app
escolhe clínica ou paciente.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.http import HttpRequest
from ninja import Schema, Status
from ninja.errors import HttpError
from ninja.security import HttpBearer

from core.services import update_observability_context
from mobile_api.services import AuthenticatedMobileSession, authenticate_access_token


class MobileErrorOut(Schema):
    """Erro estável: o app decide o texto pelo `code`; `detail` é só diagnóstico."""

    detail: str
    code: str = ""


def tenant_is_blocked(clinic: Any) -> bool:
    """Mesma regra do web (HTTP 402) para clínica com cobrança bloqueada."""
    try:
        return bool(clinic.subscription.is_blocked)
    except Exception:  # sem assinatura cadastrada não bloqueia, como no web
        return False


class PatientBearerAuth(HttpBearer):
    """Valida o token de acesso do app e fixa usuário, clínica e perfil do paciente.

    `allow_blocked_tenant=True` é reservado ao plano de apoio urgente: o paciente
    não perde o acesso à própria ajuda por pendência de cobrança da clínica.
    """

    def __init__(self, *, allow_blocked_tenant: bool = False) -> None:
        super().__init__()
        self.allow_blocked_tenant = allow_blocked_tenant

    def authenticate(self, request: HttpRequest, token: str) -> Any:
        resolved = authenticate_access_token(token=token)
        if resolved is None:
            return None
        if not self.allow_blocked_tenant and tenant_is_blocked(resolved.clinic):
            raise HttpError(402, "Acesso suspenso pela clínica.")
        request.user = resolved.user
        cast(Any, request).clinic = resolved.clinic
        update_observability_context(
            actor_id=str(resolved.user.pk), tenant_id=str(resolved.clinic.pk)
        )
        return resolved


def mobile_context(request: HttpRequest) -> AuthenticatedMobileSession:
    """Contexto da sessão já autenticada (preenchido por `PatientBearerAuth`)."""
    resolved = getattr(request, "auth", None)
    if not isinstance(resolved, AuthenticatedMobileSession):
        raise HttpError(401, "Autenticação necessária.")
    return resolved


def request_id(request: HttpRequest) -> UUID:
    """Correlação da requisição, com fallback seguro."""
    raw = getattr(request, "request_id", None)
    if raw:
        try:
            return UUID(str(raw))
        except ValueError:
            pass
    return uuid4()


def problem(status: int, detail: str, code: str) -> Status[dict[str, str]]:
    """Resposta de erro estável: o app escolhe o texto pelo ``code``."""
    return Status(status, {"detail": detail, "code": code})


def patient_zone(timezone_name: str) -> ZoneInfo:
    """Fuso do paciente, com o de Brasília como padrão se o cadastro for inválido."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError, ValueError:
        return ZoneInfo("America/Sao_Paulo")


def network_origin(request: HttpRequest) -> str | None:
    return str(request.META.get("REMOTE_ADDR", "")) or None
