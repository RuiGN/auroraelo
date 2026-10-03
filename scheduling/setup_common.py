"""Shared plumbing for the clinic setup screens (services and availability).

The screens are staff-only. Reading needs ``clinic.read`` (administrator,
therapist and administrative staff); writing needs ``clinic.manage``
(administrator only). The clinic always comes from ``request.clinic``, never
from the URL, and every write goes through a domain service that authorizes
again.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any
from uuid import UUID, uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from clinics.policies import ClinicAuthorizationPolicy
from clinics.services import authorized_active_clinic
from core.services import current_correlation_id

LAYOUT = "layouts/aurora_elo.html"
ACTION_READ = "clinic.read"
ACTION_MANAGE = "clinic.manage"


@dataclass(frozen=True, slots=True)
class SetupContext:
    """Resolved actor and clinic of one authorized request."""

    actor: AbstractBaseUser
    clinic_id: UUID
    can_manage: bool


def request_uuid() -> UUID:
    """Return the request correlation id as a UUID for audit trails."""
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def setup_context(request: HttpRequest, *, manage: bool = False) -> SetupContext:
    """Authorize the request for reading, or for writing when ``manage`` is set."""
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
    return SetupContext(actor=actor, clinic_id=clinic.pk, can_manage=can_manage)


def setup_page(
    request: HttpRequest, template: str, context: dict[str, Any]
) -> TemplateResponse:
    """Render a setup screen in the Aurora Elo layout."""
    return TemplateResponse(request, template, {"layout_template": LAYOUT, **context})


def private_no_store[**P](view: Callable[P, HttpResponse]) -> Callable[P, HttpResponse]:
    """Keep browsers and proxies from storing the screen."""

    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> HttpResponse:
        response = view(*args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapped
