"""Staff screens for the bookable service catalog (what the app offers to book)."""

from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .catalog_services import create_service, set_service_active, update_service
from .selectors import service_for_clinic, services_for_clinic
from .setup_common import private_no_store, request_uuid, setup_context, setup_page
from .setup_forms import ServiceForm

__all__ = [
    "service_activate",
    "service_create",
    "service_deactivate",
    "service_list",
    "service_update",
]


def _list_url() -> str:
    return reverse("scheduling:service_list")


def _form_page(
    request: HttpRequest, *, title: str, form: ServiceForm, submit_label: str
) -> HttpResponse:
    return setup_page(
        request,
        "scheduling/setup_form.html",
        {
            "page_title": title,
            "form": form,
            "submit_label": submit_label,
            "cancel_url": _list_url(),
            "lead": _(
                "A duração e o intervalo definem os horários que o paciente vê "
                "ao pedir consulta no aplicativo."
            ),
            "breadcrumb": [(_("Serviços de agendamento"), _list_url())],
        },
    )


@login_required
@require_GET
@private_no_store
def service_list(request: HttpRequest) -> HttpResponse:
    """List the clinic's services; only the administrator sees the write actions."""
    context = setup_context(request)
    services = services_for_clinic(clinic_id=context.clinic_id)
    return setup_page(
        request,
        "scheduling/service_list.html",
        {
            "page_title": _("Serviços de agendamento"),
            "services": services,
            "active_count": sum(1 for service in services if service.is_active),
            "can_manage": context.can_manage,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@private_no_store
def service_create(request: HttpRequest) -> HttpResponse:
    """Create one service."""
    context = setup_context(request, manage=True)
    form = ServiceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_service(
                clinic_id=context.clinic_id,
                actor=context.actor,
                name=form.cleaned_data["name"],
                duration_minutes=form.cleaned_data["duration_minutes"],
                buffer_minutes=form.cleaned_data["buffer_minutes"],
                request_id=request_uuid(),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, _("Serviço criado."))
            return HttpResponseRedirect(_list_url())
    return _form_page(
        request,
        title=_("Novo serviço"),
        form=form,
        submit_label=_("Salvar serviço"),
    )


@login_required
@require_http_methods(["GET", "POST"])
@private_no_store
def service_update(request: HttpRequest, service_id: UUID) -> HttpResponse:
    """Edit one service's name and timing."""
    context = setup_context(request, manage=True)
    service = service_for_clinic(clinic_id=context.clinic_id, service_id=service_id)
    if service is None:
        raise PermissionDenied
    form = ServiceForm(
        request.POST or None,
        initial={
            "name": service.name,
            "duration_minutes": service.duration_minutes,
            "buffer_minutes": service.buffer_minutes,
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_service(
                clinic_id=context.clinic_id,
                actor=context.actor,
                service_id=service.pk,
                name=form.cleaned_data["name"],
                duration_minutes=form.cleaned_data["duration_minutes"],
                buffer_minutes=form.cleaned_data["buffer_minutes"],
                request_id=request_uuid(),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, _("Serviço atualizado."))
            return HttpResponseRedirect(_list_url())
    return _form_page(
        request,
        title=_("Editar serviço"),
        form=form,
        submit_label=_("Salvar serviço"),
    )


def _toggle(request: HttpRequest, service_id: UUID, *, is_active: bool) -> HttpResponse:
    context = setup_context(request, manage=True)
    set_service_active(
        clinic_id=context.clinic_id,
        actor=context.actor,
        service_id=service_id,
        is_active=is_active,
        request_id=request_uuid(),
    )
    messages.success(
        request,
        _("Serviço ativado. O paciente já pode pedi-lo no aplicativo.")
        if is_active
        else _("Serviço inativado. O paciente deixa de ver este serviço."),
    )
    return HttpResponseRedirect(_list_url())


@login_required
@require_POST
@private_no_store
def service_activate(request: HttpRequest, service_id: UUID) -> HttpResponse:
    """Offer the service again in the app."""
    return _toggle(request, service_id, is_active=True)


@login_required
@require_POST
@private_no_store
def service_deactivate(request: HttpRequest, service_id: UUID) -> HttpResponse:
    """Stop offering the service; consultations already booked are untouched."""
    return _toggle(request, service_id, is_active=False)
