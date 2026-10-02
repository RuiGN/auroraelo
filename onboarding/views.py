"""Onboarding views for clinic administrators and patients."""

from __future__ import annotations

from typing import cast
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from core.services import current_correlation_id

from .selectors import clinic_onboarding_checklist

_STEPS = ("goals", "preferences", "terms", "complete")
_NEXT_STEP = {"goals": "preferences", "preferences": "terms", "terms": "complete"}
_STEP_LABELS = {
    "goals": _("Objetivos"),
    "preferences": _("Preferências"),
    "terms": _("Termos"),
    "complete": _("Concluído"),
}


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError:
        return uuid4()


def _clinic_id(request: HttpRequest) -> UUID:
    clinic = getattr(request, "clinic", None)
    if clinic is None:
        raise PermissionDenied
    return cast(UUID, clinic.pk)


@login_required
@require_GET
def clinic_onboarding(request: HttpRequest) -> HttpResponse:
    """Render the factual clinic onboarding checklist."""
    actor = request.user
    if not isinstance(actor, AbstractBaseUser):
        raise PermissionDenied
    clinic_id = _clinic_id(request)
    items = clinic_onboarding_checklist(clinic_id=clinic_id, actor=actor)
    return TemplateResponse(
        request,
        "onboarding/clinic_checklist.html",
        {"layout_template": "layouts/vertical.html", "items": items},
    )
