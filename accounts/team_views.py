"""Tenant-scoped team administration for clinic administrators."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from accounts.forms import (
    translated_membership_role_choices,
    translated_membership_role_label,
)
from accounts.models import ClinicInvitation, ClinicInvitationQuerySet, User
from accounts.services import IssuedInvitation, resend_invitation, revoke_invitation
from clinics.selectors import memberships_visible_to
from clinics.services import (
    CLINIC_SESSION_KEY,
    Clinic,
    authorized_active_clinic,
    set_membership_active,
)

INVITATION_RESEND_HOURS = 24


def _clinic_for_team(request: HttpRequest) -> tuple[User, Clinic]:
    """Resolve the active session clinic and reauthorize the team action."""
    actor = request.user
    if not isinstance(actor, User):
        raise PermissionDenied
    try:
        clinic_id = UUID(str(request.session.get(CLINIC_SESSION_KEY)))
    except (TypeError, ValueError, AttributeError) as error:
        raise PermissionDenied from error
    return actor, authorized_active_clinic(
        clinic_id=clinic_id,
        actor=actor,
        action="membership.enumerate",
    )


def _pending_invitations(clinic_id: UUID) -> ClinicInvitationQuerySet:
    """List only unused, unrevoked invitations from the explicit clinic."""
    return (
        ClinicInvitation.objects.for_clinic(clinic_id)
        .filter(used_at__isnull=True, revoked_at__isnull=True)
        .order_by("expires_at", "pk")
    )


def _email_invitation_link(request: HttpRequest, issued: IssuedInvitation) -> None:
    """Deliver one single-use acceptance link in the recipient's language."""
    accept_path = reverse(
        "invitation_accept",
        kwargs={"raw_token": issued.raw_token},
    )
    recipient = User.objects.filter(
        email=issued.invitation.recipient_email, is_active=True
    ).first()
    recipient_language = (
        recipient.preferred_language
        if recipient is not None and recipient.preferred_language
        else getattr(request, "LANGUAGE_CODE", "pt-br")
    )
    with translation.override(recipient_language):
        subject = _("Convite para acessar a clínica")
        body = _(
            "Você recebeu um convite para acessar a clínica.\n\n"
            "Acesse: %(accept_url)s\n\n"
            "O convite é individual, temporário e pode ser usado uma única vez."
        ) % {"accept_url": request.build_absolute_uri(accept_path)}
        message = EmailMultiAlternatives(
            subject=str(subject),
            body=str(body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[issued.invitation.recipient_email],
        )
        message.send()


@login_required
@require_GET
def team_list(request: HttpRequest) -> HttpResponse:
    """List only memberships from the administrator's explicitly active clinic."""
    actor, clinic = _clinic_for_team(request)
    memberships = memberships_visible_to(actor, clinic).order_by("user__email", "pk")
    role = request.GET.get("role", "").strip()
    if role:
        memberships = memberships.filter(role=role)
    membership_rows = [
        {
            "membership": membership,
            "role_label": translated_membership_role_label(membership.role),
        }
        for membership in memberships
    ]
    invitation_rows = [
        {
            "invitation": invitation,
            "role_label": translated_membership_role_label(invitation.initial_role),
        }
        for invitation in _pending_invitations(clinic.pk)
    ]
    return render(
        request,
        "accounts/team.html",
        {
            "page_title": _("Usuários e equipe"),
            "clinic": clinic,
            "membership_rows": membership_rows,
            "invitation_rows": invitation_rows,
            "role_filter": role,
            "roles": translated_membership_role_choices(),
        },
    )


@login_required
@require_POST
def team_set_active(request: HttpRequest, membership_id: UUID) -> HttpResponse:
    """Suspend or reactivate one same-clinic membership, never delete it."""
    actor, clinic = _clinic_for_team(request)
    raw_active = request.POST.get("is_active") == "1"
    try:
        set_membership_active(
            clinic_id=clinic.pk,
            actor=actor,
            membership_id=membership_id,
            is_active=raw_active,
            request_id=uuid4(),
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("team_list")
    messages.success(
        request,
        _("Vínculo reativado.") if raw_active else _("Vínculo suspenso."),
    )
    return redirect("team_list")


@login_required
@require_POST
def team_revoke_invitation(request: HttpRequest, invitation_id: UUID) -> HttpResponse:
    """Revoke one pending invitation from the administrator's own clinic."""
    actor, clinic = _clinic_for_team(request)
    try:
        revoke_invitation(
            clinic_id=clinic.pk,
            invitation_id=invitation_id,
            actor=actor,
        )
    except PermissionDenied:
        messages.error(request, _("Convite indisponível para revogação."))
        return redirect("team_list")
    messages.success(request, _("Convite revogado."))
    return redirect("team_list")


@login_required
@require_POST
def team_resend_invitation(request: HttpRequest, invitation_id: UUID) -> HttpResponse:
    """Issue a fresh single-use invitation and revoke the replaced one."""
    actor, clinic = _clinic_for_team(request)
    try:
        issued = resend_invitation(
            clinic_id=clinic.pk,
            invitation_id=invitation_id,
            actor=actor,
            expires_at=timezone.now() + timedelta(hours=INVITATION_RESEND_HOURS),
        )
    except PermissionDenied:
        messages.error(request, _("Convite indisponível para reenvio."))
        return redirect("team_list")
    _email_invitation_link(request, issued)
    messages.success(request, _("Convite reenviado."))
    return redirect("team_list")
