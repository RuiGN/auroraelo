"""Global user and membership administration views."""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from accounts.forms import (
    translated_membership_role_choices,
    translated_membership_role_label,
)
from accounts.models import ClinicInvitation, User, UserManager
from accounts.services import issue_invitation
from clinics.models import Clinic, ClinicMembership
from core.policies import current_actor_is_active
from people.models import ProfessionalProfile

from ..forms import MasterMembershipForm, MasterUserInviteForm
from ..user_services import (
    link_or_update_membership,
    revoke_invitation_as_operator,
    update_membership_as_operator,
)

logger = logging.getLogger("application.master_panel.users")


def _operator(request: HttpRequest) -> User:
    """Resolve the active staff identity required by every global action."""
    actor = request.user
    if not isinstance(actor, User) or not current_actor_is_active(actor):
        raise PermissionDenied
    if not (actor.is_staff or actor.is_superuser):
        raise PermissionDenied
    return actor


@staff_member_required(login_url="/master/login/")
def user_list(request: HttpRequest) -> HttpResponse:
    """List memberships and pending invitations without exposing bearer tokens."""
    q = request.GET.get("q", "").strip()
    clinic_id = request.GET.get("clinic", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    memberships = ClinicMembership.infrastructure_objects.select_related(
        "user", "clinic"
    ).order_by("clinic__name", "user__email", "pk")
    if q:
        memberships = memberships.filter(
            Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(clinic__name__icontains=q)
        )
    if clinic_id:
        memberships = memberships.filter(clinic_id=clinic_id)
    if role:
        memberships = memberships.filter(role=role)
    if status == "active":
        memberships = memberships.filter(is_active=True)
    elif status == "suspended":
        memberships = memberships.filter(is_active=False)

    pending = (
        ClinicInvitation.infrastructure_objects.filter(
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .select_related("clinic")
        .order_by("expires_at", "pk")
    )
    if q:
        pending = pending.filter(
            Q(recipient_email__icontains=q) | Q(clinic__name__icontains=q)
        )
    if clinic_id:
        pending = pending.filter(clinic_id=clinic_id)

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
        for invitation in pending
    ]

    return render(
        request,
        "master_panel/users.html",
        {
            "page_title": _("Usuários e equipe"),
            "membership_rows": membership_rows,
            "invitation_rows": invitation_rows,
            "clinics": Clinic.infrastructure_objects.order_by("name"),
            "roles": translated_membership_role_choices(),
            "q": q,
            "clinic_filter": clinic_id,
            "role_filter": role,
            "status_filter": status,
        },
    )


@require_http_methods(["GET", "POST"])
@staff_member_required(login_url="/master/login/")
def user_invite(request: HttpRequest) -> HttpResponse:
    """Invite or link an identity while keeping credentials outside administration."""
    actor = _operator(request)
    form = MasterUserInviteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        email = UserManager.canonical_email(data["recipient_email"])
        existing = User.objects.filter(email=email).first()
        if existing is not None:
            try:
                link_or_update_membership(
                    actor=actor,
                    user=existing,
                    clinic_id=data["clinic"].pk,
                    role=data["initial_role"],
                    category=data["initial_category"],
                    unit_name=data["unit_name"],
                    valid_from=data["valid_from"],
                    valid_until=data["valid_until"],
                    is_active=True,
                )
            except (PermissionDenied, ValidationError, ValueError) as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, _("Vínculo da identidade atualizado."))
                return redirect("administration:user_list")
        else:
            try:
                issued = issue_invitation(
                    clinic_id=data["clinic"].pk,
                    issuer=actor,
                    recipient_email=email,
                    initial_role=data["initial_role"],
                    initial_category=data["initial_category"],
                    unit_name=data["unit_name"],
                    valid_from=data["valid_from"],
                    valid_until=data["valid_until"],
                    expires_at=timezone.now()
                    + timedelta(hours=data["expires_in_hours"]),
                )
                accept_path = reverse(
                    "invitation_accept",
                    kwargs={"raw_token": issued.raw_token},
                )
                message = EmailMultiAlternatives(
                    subject=str(_("Convite para acessar uma clínica")),
                    body=(
                        _(
                            "Você recebeu um convite para acessar uma clínica.\n\n"
                            "Acesse: %(accept_url)s\n\n"
                            "O convite é individual e pode ser usado uma única vez."
                        )
                        % {"accept_url": request.build_absolute_uri(accept_path)}
                    ),
                    from_email="no-reply@auroraelo.invalid",
                    to=[email],
                )
                message.send()
            except (PermissionDenied, ValidationError, ValueError) as error:
                form.add_error(None, str(error))
            except Exception:
                logger.exception("master invitation delivery failed")
                form.add_error(
                    None,
                    _("Não foi possível enviar o convite. Tente novamente."),
                )
            else:
                messages.success(
                    request, _("Convite enviado sem criar senha administrativa.")
                )
                return redirect("administration:user_list")
    return render(
        request,
        "master_panel/user_invite.html",
        {"page_title": _("Convidar usuário"), "form": form},
    )


@require_http_methods(["GET", "POST"])
@staff_member_required(login_url="/master/login/")
def user_edit(request: HttpRequest, membership_id: UUID) -> HttpResponse:
    """Edit one membership by stable identifier inside global infrastructure scope."""
    actor = _operator(request)
    membership = get_object_or_404(
        ClinicMembership.infrastructure_objects.select_related("user", "clinic"),
        pk=membership_id,
        clinic__is_active=True,
    )
    profile = ProfessionalProfile.infrastructure_objects.filter(
        clinic_id=membership.clinic_id,
        user_id=membership.user_id,
    ).first()
    form = MasterMembershipForm(
        request.POST or None,
        initial={
            "role": membership.role,
            "category": profile.category if profile is not None else "",
            "unit_name": membership.unit_name,
            "valid_from": membership.valid_from,
            "valid_until": membership.valid_until,
            "is_active": membership.is_active,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_membership_as_operator(
                actor=actor,
                membership_id=membership.pk,
                role=form.cleaned_data["role"],
                category=form.cleaned_data["category"],
                unit_name=form.cleaned_data["unit_name"],
                valid_from=form.cleaned_data["valid_from"],
                valid_until=form.cleaned_data["valid_until"],
                is_active=form.cleaned_data["is_active"],
            )
        except (PermissionDenied, ValidationError, ValueError) as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, _("Vínculo atualizado."))
            return redirect("administration:user_list")
    return render(
        request,
        "master_panel/user_edit.html",
        {
            "page_title": _("Editar vínculo"),
            "form": form,
            "membership": membership,
        },
    )


@require_POST
@staff_member_required(login_url="/master/login/")
def invitation_revoke(request: HttpRequest, invitation_id: UUID) -> HttpResponse:
    """Revoke a pending invitation without displaying its token."""
    actor = _operator(request)
    revoke_invitation_as_operator(actor=actor, invitation_id=invitation_id)
    messages.success(request, _("Convite revogado."))
    return redirect("administration:user_list")
