"""Public HTTP views for authentication and credential recovery."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from clinics.services import CLINIC_SESSION_KEY

from .forms import (
    InvitationAcceptanceForm,
    InvitationIssueForm,
    LoginForm,
    PasswordRecoveryForm,
    PasswordResetForm,
    SensitiveActionReauthenticationForm,
)
from .models import AccountSession, User
from .services import (
    GENERIC_LOGIN_ERROR,
    GENERIC_RECOVERY_RESPONSE,
    LoginRateLimitedError,
    LoginRejectedError,
    RecoveryRateLimitedError,
    SensitiveActionRateLimitedError,
    accept_invitation,
    invitation_clinic_id,
    issue_invitation,
    login_user,
    logout_user,
    password_reset_identity,
    reauthenticate_sensitive_action,
    request_password_recovery,
    reset_password,
    revoke_account_session,
    revoke_invitation,
    revoke_other_sessions,
)


def _form_response(
    request: HttpRequest,
    *,
    form: (
        InvitationAcceptanceForm
        | InvitationIssueForm
        | LoginForm
        | PasswordRecoveryForm
        | PasswordResetForm
    ),
    title: str,
    description: str,
    submit_label: str,
    status: int = 200,
    secondary_url: str | None = None,
    secondary_label: str | None = None,
) -> TemplateResponse:
    """Render the shared accessible authentication form shell."""
    return TemplateResponse(
        request,
        "accounts/auth_form.html",
        {
            "page_title": title,
            "title": title,
            "description": description,
            "form": form,
            "submit_label": submit_label,
            "secondary_url": secondary_url,
            "secondary_label": secondary_label,
        },
        status=status,
    )


def _safe_local_next(request: HttpRequest, value: object) -> str | None:
    """Return an application-local destination or reject the supplied value."""
    if (
        isinstance(value, str)
        and value.startswith("/")
        and not value.startswith("//")
        and url_has_allowed_host_and_scheme(
            value,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        return value
    return None


@require_http_methods(["GET", "POST"])
def account_login(request: HttpRequest) -> HttpResponse:
    """Authenticate with a canonical e-mail and select one authorized clinic."""
    form = LoginForm(request.POST or None)
    status = 200
    if request.method == "POST" and form.is_valid():
        try:
            login_user(
                request=request,
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
        except LoginRateLimitedError:
            form.add_error(None, _(GENERIC_LOGIN_ERROR))
            status = 429
        except LoginRejectedError:
            form.add_error(None, _(GENERIC_LOGIN_ERROR))
        else:
            next_url = _safe_local_next(request, request.GET.get("next"))
            if next_url is not None:
                return redirect(next_url)
            return redirect("workspace_vertical")
    response = _form_response(
        request,
        form=form,
        title=_("Entrar na plataforma"),
        description=_(
            "Use seu e-mail e sua senha para acessar uma clínica autorizada."
        ),
        submit_label=_("Entrar"),
        status=status,
        secondary_url=reverse("password_recovery"),
        secondary_label=_("Esqueci minha senha"),
    )
    if status == 429:
        response.headers["Retry-After"] = str(
            max(1, int(settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS))
        )
    return response


@require_POST
def account_logout(request: HttpRequest) -> HttpResponse:
    """End the current session through a POST-only auditable action."""
    logout_user(request=request)
    return redirect("account_login")


def _active_clinic_id(request: HttpRequest) -> UUID:
    """Resolve the session tenant; domain services reauthorize every action."""
    try:
        return UUID(str(request.session.get(CLINIC_SESSION_KEY)))
    except (TypeError, ValueError, AttributeError) as error:
        raise PermissionDenied("Active clinic is required.") from error


@login_required
@require_http_methods(["GET", "POST"])
def invitation_issue(request: HttpRequest) -> HttpResponse:
    """Issue and deliver a single-use clinic invitation in PT-BR."""
    actor = request.user
    if not isinstance(actor, User):
        raise PermissionDenied
    form = InvitationIssueForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        issued = issue_invitation(
            clinic_id=_active_clinic_id(request),
            issuer=actor,
            recipient_email=form.cleaned_data["recipient_email"],
            initial_role=form.cleaned_data["initial_role"],
            expires_at=timezone.now()
            + timedelta(hours=form.cleaned_data["expires_in_hours"]),
        )
        path = reverse(
            "invitation_accept",
            kwargs={"raw_token": issued.raw_token},
        )
        recipient_user = User.objects.filter(
            email=issued.invitation.recipient_email, is_active=True
        ).first()
        recipient_lang = (
            recipient_user.preferred_language
            if recipient_user and recipient_user.preferred_language
            else getattr(request, "LANGUAGE_CODE", "pt-br")
        )
        with translation.override(recipient_lang):
            subject = _("Convite para acessar a clínica")
            body = _(
                "Você recebeu um convite para acessar a clínica.\n\n"
                "Acesse: %(accept_url)s\n\n"
                "O convite é individual, temporário e pode ser usado uma única vez."
            ) % {"accept_url": request.build_absolute_uri(path)}
            message = EmailMultiAlternatives(
                subject=str(subject),
                body=str(body),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[issued.invitation.recipient_email],
            )
            message.send()
        return TemplateResponse(
            request,
            "accounts/auth_message.html",
            {
                "page_title": _("Convite enviado"),
                "title": _("Convite enviado"),
                "message": _("O convite foi enviado para o endereço informado."),
                "action_url": reverse("invitation_issue"),
                "action_label": _("Enviar outro convite"),
            },
        )
    return _form_response(
        request,
        form=form,
        title=_("Convidar pessoa"),
        description=_("Defina o acesso inicial e a validade do convite."),
        submit_label=_("Enviar convite"),
    )


@require_http_methods(["GET", "POST"])
def invitation_accept(request: HttpRequest, raw_token: str) -> HttpResponse:
    """Accept an invitation for a new or already authenticated identity."""
    actor = request.user if isinstance(request.user, User) else None
    if request.method == "POST" and actor is not None:
        clinic_id = invitation_clinic_id(raw_token=raw_token)
        accept_invitation(
            raw_token=raw_token,
            password="",
            first_name="",
            last_name="",
            actor=actor,
        )
        request.session[CLINIC_SESSION_KEY] = str(clinic_id)
        return redirect("workspace_vertical")

    form = InvitationAcceptanceForm(request.POST or None)
    if request.method == "POST":
        if not request.POST:
            return redirect(f"{reverse('account_login')}?next={request.path}")
        if form.is_valid():
            try:
                accept_invitation(
                    raw_token=raw_token,
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                )
            except PermissionDenied, ValueError, ValidationError:
                form.add_error(None, _("Convite inválido ou expirado."))
            else:
                return redirect("account_login")
    return _form_response(
        request,
        form=form,
        title=_("Aceitar convite"),
        description=_("Confirme seus dados para criar o acesso à clínica."),
        submit_label=_("Aceitar convite"),
    )


@login_required
@require_POST
def invitation_revoke(request: HttpRequest, invitation_id: UUID) -> HttpResponse:
    """Revoke one pending invitation through a POST-only tenant action."""
    actor = request.user
    if not isinstance(actor, User):
        raise PermissionDenied
    revoke_invitation(
        clinic_id=_active_clinic_id(request),
        invitation_id=invitation_id,
        actor=actor,
    )
    return redirect("invitation_issue")


@require_http_methods(["GET", "POST"])
def password_recovery(request: HttpRequest) -> HttpResponse:
    """Accept a recovery request with a generic non-enumerating response."""
    form = PasswordRecoveryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        status = 200
        try:
            request_password_recovery(
                request=request,
                email=form.cleaned_data["email"],
            )
        except RecoveryRateLimitedError:
            status = 429
        response = TemplateResponse(
            request,
            "accounts/auth_message.html",
            {
                "page_title": _("Solicitação recebida"),
                "title": _("Verifique seu e-mail"),
                "message": _(GENERIC_RECOVERY_RESPONSE),
                "action_url": reverse("account_login"),
                "action_label": _("Voltar para entrar"),
            },
            status=status,
        )
        if status == 429:
            response.headers["Retry-After"] = str(
                max(1, int(settings.PASSWORD_RECOVERY_RATE_LIMIT_WINDOW_SECONDS))
            )
        return response
    return _form_response(
        request,
        form=form,
        title=_("Recuperar acesso"),
        description=_("Informe seu e-mail para receber instruções de recuperação."),
        submit_label=_("Enviar instruções"),
        secondary_url=reverse("account_login"),
        secondary_label=_("Voltar para entrar"),
    )


@require_http_methods(["GET", "POST"])
def password_reset(request: HttpRequest, uid: str, token: str) -> HttpResponse:
    """Replace a credential through one valid, short-lived reset token."""
    identity = password_reset_identity(uid=uid, token=token)
    if identity is None:
        return TemplateResponse(
            request,
            "accounts/auth_message.html",
            {
                "page_title": _("Link inválido"),
                "title": _("Link inválido ou expirado."),
                "message": _("Solicite novas instruções para recuperar seu acesso."),
                "action_url": reverse("password_recovery"),
                "action_label": _("Solicitar novo link"),
            },
            status=400,
        )
    form = PasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if reset_password(
            uid=uid,
            token=token,
            new_password=form.cleaned_data["new_password"],
        ):
            return redirect("password_reset_complete")
        return TemplateResponse(
            request,
            "accounts/auth_message.html",
            {
                "page_title": _("Link inválido"),
                "title": _("Link inválido ou expirado."),
                "message": _("Solicite novas instruções para recuperar seu acesso."),
                "action_url": reverse("password_recovery"),
                "action_label": _("Solicitar novo link"),
            },
            status=400,
        )
    return _form_response(
        request,
        form=form,
        title=_("Definir nova senha"),
        description=_("Escolha uma nova senha para proteger sua conta."),
        submit_label=_("Salvar nova senha"),
    )


def password_reset_complete(request: HttpRequest) -> TemplateResponse:
    """Confirm successful credential replacement without exposing account data."""
    return TemplateResponse(
        request,
        "accounts/auth_message.html",
        {
            "page_title": _("Senha alterada"),
            "title": _("Senha alterada com segurança"),
            "message": _("Entre novamente em todos os seus dispositivos."),
            "action_url": reverse("account_login"),
            "action_label": _("Entrar"),
        },
    )


def _authenticated_user(request: HttpRequest) -> User:
    actor = request.user
    if not isinstance(actor, User):
        raise PermissionDenied
    return actor


@login_required
@require_http_methods(["GET", "POST"])
def account_sessions(request: HttpRequest) -> HttpResponse:
    """List minimized active devices and process explicit revocation actions."""
    actor = _authenticated_user(request)
    current = getattr(request, "account_session", None)
    reauthentication_form = SensitiveActionReauthenticationForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "revoke_others" and isinstance(current, AccountSession):
            try:
                reauthenticated = (
                    reauthentication_form.is_valid()
                    and reauthenticate_sensitive_action(
                        actor=actor,
                        password=reauthentication_form.cleaned_data.get("password", ""),
                    )
                )
            except SensitiveActionRateLimitedError:
                reauthentication_form.add_error(
                    "password", _("Muitas tentativas. Tente novamente mais tarde.")
                )
                sessions = AccountSession.objects.filter(user=actor).order_by(
                    "-last_seen_at"
                )
                response = TemplateResponse(
                    request,
                    "accounts/sessions.html",
                    {
                        "account_sessions": sessions,
                        "current_session": current,
                        "reauthentication_form": reauthentication_form,
                    },
                    status=429,
                )
                response.headers["Retry-After"] = str(
                    settings.SENSITIVE_REAUTH_RATE_LIMIT_WINDOW_SECONDS
                )
                return response
            if not reauthenticated:
                reauthentication_form.add_error(
                    "password", _("Não foi possível confirmar sua senha atual.")
                )
                sessions = AccountSession.objects.filter(user=actor).order_by(
                    "-last_seen_at"
                )
                return TemplateResponse(
                    request,
                    "accounts/sessions.html",
                    {
                        "account_sessions": sessions,
                        "current_session": current,
                        "reauthentication_form": reauthentication_form,
                    },
                    status=400,
                )
            revoke_other_sessions(
                actor=actor,
                current_session_id=current.pk,
                clinic_id=_active_clinic_id(request),
            )
        elif action == "revoke":
            try:
                session_id = UUID(str(request.POST.get("session_id")))
            except TypeError, ValueError, AttributeError:
                raise PermissionDenied from None
            revoke_account_session(
                actor=actor,
                account_session_id=session_id,
                clinic_id=_active_clinic_id(request),
            )
        return redirect("account_sessions")
    sessions = AccountSession.objects.filter(user=actor).order_by("-last_seen_at")
    return TemplateResponse(
        request,
        "accounts/sessions.html",
        {
            "account_sessions": sessions,
            "current_session": current,
            "reauthentication_form": reauthentication_form,
        },
    )
