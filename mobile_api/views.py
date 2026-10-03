"""Painel web da equipe sobre o acesso do paciente ao aplicativo pós-alta.

O paciente nunca usa o web: ele entra só pelo app. Estas telas mostram à equipe a
situação do acesso (convite, conta, aparelhos) e permitem reenviar o convite (somente o
administrador) e desconectar aparelhos (administrador e terapeuta vinculado).

Nada aqui exibe token, resumo de token, endereço de rede ou o código de ativação já
emitido; o código novo aparece uma única vez, na resposta do reenvio.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from clinics.services import authorized_active_clinic
from core.services import current_correlation_id
from people.selectors import patient_invitation_state, patient_profile_in_clinic

from . import selectors, services
from .forms import ConfirmActionForm
from .policies import can_issue_patient_invitation, can_manage_patient_app

LAYOUT = "layouts/aurora_elo.html"

# Pré-requisito comum: equipe ativa da clínica (paciente e desconhecidos ficam de fora).
# Quem pode agir sobre ESTE paciente é decidido em `mobile_api.policies`.
CLINIC_GATE_ACTION = "patient.demographics.read"


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def _staff_context(
    request: HttpRequest, patient_id: UUID
) -> tuple[AbstractBaseUser, UUID, Any]:
    """Resolve ator, clínica ativa e paciente; negar é sempre o mesmo 403.

    Paciente inexistente, de outra clínica ou sem vínculo com o terapeuta respondem
    igual, para não revelar a existência de ninguém.
    """
    actor = request.user
    clinic = getattr(request, "clinic", None)
    if not isinstance(actor, AbstractBaseUser) or clinic is None:
        raise PermissionDenied
    clinic_id = cast(UUID, clinic.pk)
    authorized_active_clinic(
        clinic_id=clinic_id, actor=actor, action=CLINIC_GATE_ACTION
    )
    patient = patient_profile_in_clinic(
        clinic_id=clinic_id, patient_profile_id=patient_id
    )
    if patient is None or not can_manage_patient_app(
        clinic_id=clinic_id,
        actor_id=actor.pk,
        patient_profile_id=patient.pk,
        on_date=timezone.localdate(),
    ):
        raise PermissionDenied
    return actor, clinic_id, patient


def _page(
    request: HttpRequest, template: str, context: dict[str, Any]
) -> TemplateResponse:
    """Página com dado de paciente: nunca fica em cache do navegador ou de proxy."""
    response = TemplateResponse(
        request, template, {"layout_template": LAYOUT, **context}
    )
    response["Cache-Control"] = "private, no-store"
    return response


def _network_origin(request: HttpRequest) -> str | None:
    return str(request.META.get("REMOTE_ADDR", "")) or None


def _confirm_form(request: HttpRequest) -> ConfirmActionForm:
    """Formulário ligado a todo POST, mesmo vazio (caixa desmarcada não envia nada)."""
    return ConfirmActionForm(request.POST if request.method == "POST" else None)


def _back_to_panel(patient: Any) -> HttpResponse:
    return redirect("mobile_api:patient_app", patient_id=patient.pk)


# ── Painel do paciente ──────────────────────────────────────────────────────


@login_required
@require_GET
def patient_app(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id, patient = _staff_context(request, patient_id)
    access = selectors.patient_app_access(
        clinic_id=clinic_id,
        patient_profile_id=patient.pk,
        patient_user_id=patient.user_id,
    )
    # Ponto de extensão: resumos de adesão e links dos editores entram no bloco
    # `app_panels` do template (e seu contexto, aqui), depois da união dos domínios.
    return _page(
        request,
        "mobile_api/patient_app.html",
        {
            "page_title": _("Aplicativo do paciente"),
            "patient": patient,
            "access": access,
            "can_issue_invitation": can_issue_patient_invitation(
                clinic_id=clinic_id,
                actor_id=actor.pk,
                on_date=timezone.localdate(),
            ),
        },
    )


# ── Aparelhos ───────────────────────────────────────────────────────────────


@login_required
@require_http_methods(["GET", "POST"])
def device_revoke(
    request: HttpRequest, patient_id: UUID, session_id: UUID
) -> HttpResponse:
    actor, clinic_id, patient = _staff_context(request, patient_id)
    device = selectors.connected_device(
        clinic_id=clinic_id, patient_profile_id=patient.pk, session_id=session_id
    )
    if device is None:
        raise Http404
    form = _confirm_form(request)
    if request.method == "POST" and form.is_valid():
        try:
            services.revoke_patient_devices(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=patient.pk,
                session_id=session_id,
                request_id=_request_uuid(),
                network_origin=_network_origin(request),
            )
        except PermissionDenied:
            # Outro membro da equipe (ou o próprio paciente) acabou de desconectá-lo.
            messages.info(request, _("Este aparelho já não estava conectado."))
        else:
            messages.success(
                request,
                _(
                    "Aparelho desconectado. Para voltar a usar o aplicativo, o "
                    "paciente precisa entrar de novo."
                ),
            )
        return _back_to_panel(patient)
    return _page(
        request,
        "mobile_api/confirm.html",
        {
            "page_title": _("Desconectar aparelho"),
            "kind": "revoke_one",
            "patient": patient,
            "device": device,
            "form": form,
            "submit_label": _("Desconectar aparelho"),
            "danger": True,
            "cancel_url": reverse("mobile_api:patient_app", args=[patient.pk]),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def devices_revoke_all(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id, patient = _staff_context(request, patient_id)
    devices = selectors.connected_devices(
        clinic_id=clinic_id, patient_profile_id=patient.pk
    )
    if not devices:
        messages.info(request, _("Nenhum aparelho estava conectado."))
        return _back_to_panel(patient)
    form = _confirm_form(request)
    if request.method == "POST" and form.is_valid():
        services.revoke_patient_devices(
            clinic_id=clinic_id,
            actor=actor,
            patient_profile_id=patient.pk,
            session_id=None,
            request_id=_request_uuid(),
            network_origin=_network_origin(request),
        )
        messages.success(
            request,
            _(
                "Todos os aparelhos foram desconectados. Para voltar a usar o "
                "aplicativo, o paciente precisa entrar de novo."
            ),
        )
        return _back_to_panel(patient)
    return _page(
        request,
        "mobile_api/confirm.html",
        {
            "page_title": _("Desconectar todos os aparelhos"),
            "kind": "revoke_all",
            "patient": patient,
            "devices": devices,
            "form": form,
            "submit_label": _("Desconectar todos os aparelhos"),
            "danger": True,
            "cancel_url": reverse("mobile_api:patient_app", args=[patient.pk]),
        },
    )


# ── Convite de ativação ─────────────────────────────────────────────────────


@login_required
@require_http_methods(["GET", "POST"])
def invitation_send(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id, patient = _staff_context(request, patient_id)
    if not can_issue_patient_invitation(
        clinic_id=clinic_id, actor_id=actor.pk, on_date=timezone.localdate()
    ):
        raise PermissionDenied
    if patient.user_id is not None:
        messages.error(
            request,
            _("Este paciente já ativou a conta: não há convite a enviar."),
        )
        return _back_to_panel(patient)
    previous = patient_invitation_state(
        clinic_id=clinic_id, patient_profile_id=patient.pk
    )
    form = _confirm_form(request)
    if request.method == "POST" and form.is_valid():
        try:
            sent = services.send_patient_invitation(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=patient.pk,
                request_id=_request_uuid(),
            )
        except services.InvitationNotAvailableError:
            messages.error(
                request,
                _("Este paciente já ativou a conta: não há convite a enviar."),
            )
            return _back_to_panel(patient)
        # O código aparece só nesta resposta (não é guardado em claro nem vai à sessão).
        return _page(
            request,
            "mobile_api/invitation_issued.html",
            {
                "page_title": _("Convite do aplicativo"),
                "patient": patient,
                "code": sent.raw_token,
                "expires_at": sent.expires_at,
                "emailed": sent.emailed,
            },
        )
    resend = previous is not None
    return _page(
        request,
        "mobile_api/confirm.html",
        {
            "page_title": _("Reenviar convite") if resend else _("Enviar convite"),
            "kind": "resend_invitation" if resend else "send_invitation",
            "patient": patient,
            "invitation": previous,
            "form": form,
            "submit_label": _("Reenviar convite") if resend else _("Enviar convite"),
            "danger": False,
            "cancel_url": reverse("mobile_api:patient_app", args=[patient.pk]),
        },
    )
