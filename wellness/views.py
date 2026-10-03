"""Staff screens of the wellness domain: the patient app's crisis resources."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from clinics.policies import ClinicAuthorizationPolicy
from clinics.services import authorized_active_clinic
from core.services import current_correlation_id

from .crisis_services import update_crisis_resources
from .forms import CrisisResourcesForm
from .models import MANDATORY_CRISIS_DISCLAIMER
from .selectors import crisis_settings_for_clinic

__all__ = ["crisis_resources"]

LAYOUT = "layouts/aurora_elo.html"
ACTION_READ = "clinic.read"
ACTION_MANAGE = "clinic.manage"


def _private_no_store[**P](
    view: Callable[P, HttpResponse],
) -> Callable[P, HttpResponse]:
    """Keep browsers and proxies from storing the screen."""

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        response = view(*args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def _context(
    request: HttpRequest, *, manage: bool
) -> tuple[AbstractBaseUser, UUID, bool]:
    """Resolve actor and clinic; reading is for the team, writing for the admin."""
    actor = request.user
    clinic_ref = getattr(request, "clinic", None)
    if not isinstance(actor, AbstractBaseUser) or clinic_ref is None:
        raise PermissionDenied
    clinic = authorized_active_clinic(
        clinic_id=clinic_ref.pk,
        actor=actor,
        action=ACTION_MANAGE if manage else ACTION_READ,
    )
    can_manage = manage or ClinicAuthorizationPolicy().is_allowed(
        actor, clinic, ACTION_MANAGE
    )
    return actor, clinic.pk, can_manage


@login_required
@require_http_methods(["GET", "POST"])
@_private_no_store
def crisis_resources(request: HttpRequest) -> HttpResponse:
    """Show what the app tells a patient in crisis; the clinic admin edits it."""
    actor, clinic_id, can_manage = _context(request, manage=request.method == "POST")
    current = crisis_settings_for_clinic(clinic_id=clinic_id)
    form: CrisisResourcesForm | None = None
    if can_manage:
        form = CrisisResourcesForm(
            request.POST or None,
            initial={
                "emergency_medical_number": current.emergency_medical_number,
                "emergency_fire_number": current.emergency_fire_number,
                "emotional_support_number": current.emotional_support_number,
                "custom_helpline_name": current.custom_helpline_name,
                "custom_helpline_number": current.custom_helpline_number,
                "mandatory_disclaimer_text": current.mandatory_disclaimer_text,
            },
        )
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            try:
                update_crisis_resources(
                    clinic_id=clinic_id,
                    actor=actor,
                    emergency_medical_number=data["emergency_medical_number"],
                    emergency_fire_number=data["emergency_fire_number"],
                    emotional_support_number=data["emotional_support_number"],
                    custom_helpline_name=data["custom_helpline_name"],
                    custom_helpline_number=data["custom_helpline_number"],
                    mandatory_disclaimer_text=data["mandatory_disclaimer_text"],
                    request_id=_request_uuid(),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    _("Recursos de crise salvos. O aplicativo já usa os novos dados."),
                )
                return HttpResponseRedirect(reverse("wellness:crisis_resources"))
    return TemplateResponse(
        request,
        "wellness/crisis_resources.html",
        {
            "layout_template": LAYOUT,
            "page_title": _("Recursos de crise"),
            "current": current,
            "form": form,
            "can_manage": can_manage,
            "mandatory_text": MANDATORY_CRISIS_DISCLAIMER,
        },
    )
