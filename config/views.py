"""Foundation HTTP views, safe health probes, and error handlers."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlencode
from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Page, Paginator
from django.db import connection
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import gettext_noop
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User
from accounts.services import rotate_current_session_tracking
from clinics.selectors import active_clinics_for_actor
from clinics.services import UnauthorizedClinicError, switch_active_clinic
from clinics.typing import ClinicRequest
from core.forms import DesignSystemExampleForm
from core.observability import current_request_id
from core.presentation import build_query_url

ACTIVITY_ROWS = (
    ("activity-1", gettext_noop("Configuração inicial"), gettext_noop("Concluída")),
    (
        "activity-2",
        gettext_noop("Permissões da equipe"),
        gettext_noop("Revisão pendente"),
    ),
    ("activity-3", gettext_noop("Identidade visual"), gettext_noop("Configurada")),
    (
        "activity-4",
        gettext_noop("Canais institucionais"),
        gettext_noop("Disponível"),
    ),
    (
        "activity-5",
        gettext_noop("Horários de atendimento"),
        gettext_noop("Pendente"),
    ),
)
ALLOWED_COMPONENT_QUERY_KEYS = {"q", "order", "page"}


def _pagination_context(
    page: Page[tuple[str, str, str]], query: dict[str, str]
) -> dict[str, object]:
    """Build safe, server-generated pagination destinations."""

    def destination(number: int) -> str:
        return build_query_url(
            query,
            overrides={"page": str(number)},
            allowed_keys=ALLOWED_COMPONENT_QUERY_KEYS,
        )

    return {
        "current": page.number,
        "current_label": _("Página %(current)s de %(total)s")
        % {"current": page.number, "total": page.paginator.num_pages},
        "page_count": page.paginator.num_pages,
        "first": destination(1) if page.has_previous() else None,
        "previous": destination(page.previous_page_number())
        if page.has_previous()
        else None,
        "pages": [
            {
                "number": number,
                "url": destination(number),
                "current": number == page.number,
            }
            for number in page.paginator.page_range
        ],
        "next": destination(page.next_page_number()) if page.has_next() else None,
        "last": destination(page.paginator.num_pages) if page.has_next() else None,
    }


def _component_examples(request: HttpRequest) -> dict[str, object]:
    """Return synthetic, non-clinical primitives for component demonstrations."""
    query: dict[str, str] = {
        key: str(value)
        for key, value in request.GET.items()
        if key in ALLOWED_COMPONENT_QUERY_KEYS
    }
    search_query = query.get("q", "").strip()
    order = query.get("order", "name")
    if order not in {"name", "-name", "status", "-status"}:
        order = "name"
    query["order"] = order

    rows = [
        (identifier, _(name), _(status)) for identifier, name, status in ACTIVITY_ROWS
    ]
    if search_query:
        normalized_query = search_query.casefold()
        rows = [
            row
            for row in rows
            if normalized_query in row[1].casefold()
            or normalized_query in row[2].casefold()
        ]
    field_index = 1 if order.lstrip("-") == "name" else 2
    rows.sort(
        key=lambda row: row[field_index].casefold(), reverse=order.startswith("-")
    )

    page = Paginator(rows, 2).get_page(query.get("page", "1"))
    table_rows = [
        {
            "id": identifier,
            "cells": [name, status],
            "actions": [
                {
                    "label": _("Abrir %(name)s") % {"name": name},
                    "url": build_query_url(
                        query,
                        overrides={"item": identifier},
                        allowed_keys=ALLOWED_COMPONENT_QUERY_KEYS | {"item"},
                    ),
                }
            ],
        }
        for identifier, name, status in page.object_list
    ]
    ordering = {
        "name": ("-name", "ascending"),
        "-name": ("name", "descending"),
        "status": ("-status", "ascending"),
        "-status": ("status", "descending"),
    }
    columns = []
    for key, label in (("name", _("Atividade")), ("status", _("Situação"))):
        next_order = f"-{key}"
        aria_sort = None
        if order.lstrip("-") == key:
            next_order, aria_sort = ordering[order]
        columns.append(
            {
                "key": key,
                "label": label,
                "order_url": build_query_url(
                    query,
                    overrides={"order": next_order, "page": "1"},
                    allowed_keys=ALLOWED_COMPONENT_QUERY_KEYS,
                ),
                "aria_sort": aria_sort,
                "next_sort_label": (
                    _("decrescente") if next_order.startswith("-") else _("crescente")
                ),
            }
        )

    summary_cards = [
        {
            "id": "modules-available",
            "title": _("Módulos disponíveis"),
            "description": _("Recursos operacionais liberados para a clínica ativa."),
            "value": "4",
            "raw_value": 4,
            "trend_label": _("sem alteração no período"),
            "tone": "neutral",
            "action": None,
        },
        {
            "id": "settings-pending",
            "title": _("Configurações pendentes"),
            "description": _("Ajustes factuais que ainda precisam de revisão."),
            "value": "2",
            "raw_value": 2,
            "trend_label": _("1 revisão concluída"),
            "tone": "warning",
            "action": {"label": _("Revisar configurações"), "url": "#activity-list"},
        },
        {
            "id": "catalog-info",
            "title": _("Informações disponíveis"),
            "description": _("Exemplo de indicador informativo."),
            "value": "8",
            "raw_value": 8,
            "trend_label": _("2 novos registros"),
            "tone": "info",
            "action": None,
        },
        {
            "id": "catalog-success",
            "title": _("Etapas concluídas"),
            "description": _("Conclusões confirmadas no fluxo operacional."),
            "value": "6",
            "raw_value": 6,
            "trend_label": _("2 conclusões no período"),
            "tone": "success",
            "action": None,
        },
        {
            "id": "catalog-danger",
            "title": _("Falhas operacionais"),
            "description": _("Erros técnicos que exigem nova tentativa."),
            "value": "1",
            "raw_value": 1,
            "trend_label": _("sem dados sensíveis"),
            "tone": "danger",
            "action": None,
        },
    ]
    states = [
        {
            "kind": kind,
            "title": title,
            "message": message,
            "announce": kind == "loading",
            "action": None,
        }
        for kind, title, message in (
            (
                "loading",
                _("Carregando conteúdo"),
                _("Aguarde enquanto os dados autorizados são preparados."),
            ),
            (
                "empty",
                _("Nenhum item cadastrado"),
                _("Cadastre o primeiro item quando estiver pronto."),
            ),
            (
                "no_results",
                _("Nenhum resultado encontrado"),
                _("Revise os filtros aplicados."),
            ),
            (
                "unavailable",
                _("Conteúdo temporariamente indisponível"),
                _("Tente novamente em alguns instantes."),
            ),
            (
                "error",
                _("Não foi possível carregar o conteúdo"),
                _("Tente novamente sem reenviar dados."),
            ),
            (
                "restricted",
                _("Acesso não autorizado"),
                _("Você não tem permissão para acessar este conteúdo."),
            ),
        )
    ]
    return {
        "summary_cards": summary_cards,
        "content_states": states,
        "search_query": search_query,
        "current_order": order,
        "activity_table": {
            "id": "activity-list",
            "caption": _("Atividades operacionais recentes"),
            "columns": columns,
            "rows": table_rows,
        },
        "activity_pagination": _pagination_context(page, query),
        "reference_form": DesignSystemExampleForm(),
    }


def home(request: HttpRequest) -> HttpResponse:
    """Return the official landing page for visitors, or redirect authenticated users."""
    if request.user.is_authenticated:
        return redirect("account_login")

    from django.utils.translation import gettext as _

    # Machine-readable plain text if explicitly requested via format or header
    if request.GET.get("format") == "text" or request.headers.get("Accept") == "text/plain":
        return HttpResponse(
            _("Plataforma terapêutica disponível."),
            content_type="text/plain; charset=utf-8",
        )

    contact_sent = False
    if request.method == "POST":
        contact_sent = True

    context = {
        "page_title": "Aurora Elo — Plataforma de Saúde Mental, Psiquiatria e Cuidado Contínuo",
        "availability_notice": _("Plataforma terapêutica disponível."),
        "contact_sent": contact_sent,
    }
    return render(request, "landing/index.html", context)


def liveness(request: HttpRequest) -> JsonResponse:
    """Report process responsiveness without touching external dependencies."""
    return JsonResponse({"status": "ok"})


def readiness(request: HttpRequest) -> JsonResponse:
    """Check required database and cache dependencies without exposing failures."""
    cache_key = f"readiness:{uuid4().hex}"
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise RuntimeError("Unexpected database readiness response")
        cache.set(cache_key, "ok", timeout=5)
        if cache.get(cache_key) != "ok":
            raise RuntimeError("Unexpected cache readiness response")
        cache.delete(cache_key)
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def design_system_reference(request: HttpRequest) -> HttpResponse:
    """Redirect to the comprehensive Aurora Elo Tailwind Design System showcase."""
    return redirect("/static/design_system/index.html")


def _workspace_response(request: HttpRequest, layout_variant: str) -> TemplateResponse:
    """Render one workspace route through the requested reusable shell."""
    return TemplateResponse(
        request,
        "workspace/home.html",
        {
            "layout_template": f"layouts/{layout_variant}.html",
            "layout_variant": layout_variant,
            "page_title": _("Área de trabalho"),
        },
    )


@login_required(login_url="/admin/login/")
def workspace_vertical(request: HttpRequest) -> HttpResponse:
    """Restore the saved layout from the canonical workspace entry point."""
    actor = cast(User, request.user)
    if actor.preferred_layout == User.Layout.DETACHED:
        response = HttpResponse(status=302)
        response.headers["Location"] = reverse("workspace_detached")
        return response
    return _workspace_response(request, "vertical")


@login_required(login_url="/admin/login/")
def workspace_detached(request: HttpRequest) -> TemplateResponse:
    """Render the detached workspace layout with equivalent navigation."""
    return _workspace_response(request, "detached")


@require_POST
@login_required(login_url="/admin/login/")
def save_workspace_layout(request: HttpRequest) -> HttpResponse:
    """Persist an allowlisted workspace layout for the authenticated actor."""
    actor = cast(User, request.user)
    layout = request.POST.get("layout")
    if layout not in User.Layout.values:
        return HttpResponseBadRequest(_("Preferência de layout inválida."))

    actor.preferred_layout = layout
    actor.save(update_fields=["preferred_layout"])
    destination = (
        reverse("workspace_detached")
        if layout == User.Layout.DETACHED
        else reverse("workspace_vertical")
    )
    response = HttpResponse(status=302)
    response.headers["Location"] = destination
    return response


def _safe_workspace_redirect(request: HttpRequest, candidate: object) -> str:
    """Return an allowed local destination or the default workspace route."""
    if isinstance(candidate, str) and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("workspace_vertical")


@require_GET
@login_required(login_url="/admin/login/")
def review_clinic_switch(request: HttpRequest) -> TemplateResponse:
    """Review an authorized clinic switch without changing server state."""
    actor = cast(User, request.user)
    raw_clinic_id = request.GET.get("clinic_id")
    target = next(
        (
            clinic
            for clinic in active_clinics_for_actor(actor)
            if str(clinic.pk) == raw_clinic_id
        ),
        None,
    )
    if target is None:
        raise PermissionDenied
    clinic_request = cast(ClinicRequest, request)
    return TemplateResponse(
        request,
        "clinics/confirm_switch.html",
        {
            "current_clinic": clinic_request.clinic,
            "target_clinic": target,
            "next_url": _safe_workspace_redirect(request, request.GET.get("next")),
        },
    )


@require_POST
@login_required(login_url="/admin/login/")
def confirm_clinic_switch(request: HttpRequest) -> HttpResponse:
    """Reauthorize and persist a confirmed clinic selection."""
    try:
        actor = cast(User, request.user)
        switch_active_clinic(
            request,
            actor,
            request.POST.get("clinic_id"),
        )
        rotate_current_session_tracking(request=request, user=actor)
    except UnauthorizedClinicError as exc:
        raise PermissionDenied from exc
    destination = _safe_workspace_redirect(request, request.POST.get("next"))
    response = HttpResponse(status=302)
    response.headers["Location"] = destination
    return response


def admin_login_redirect(request: HttpRequest) -> HttpResponse:
    """Route Django Admin authentication through the protected account entrypoint."""
    next_param = request.GET.get("next") or "/admin/"
    response = HttpResponse(status=302)
    response.headers["Location"] = (
        f"{reverse('account_login')}?{urlencode({'next': next_param})}"
    )
    return response


def _error_response(
    request: HttpRequest, *, status: int, title: str, message: str
) -> TemplateResponse:
    request_id = getattr(request, "request_id", current_request_id())
    return TemplateResponse(
        request,
        f"errors/{status}.html",
        {"title": title, "message": message, "request_id": request_id},
        status=status,
    )


def bad_request(request: HttpRequest, exception: Any = None) -> TemplateResponse:
    """Render a safe PT-BR 400 response."""
    return _error_response(
        request,
        status=400,
        title=_("Solicitação inválida"),
        message=_("Não foi possível processar sua solicitação."),
    )


def permission_denied(request: HttpRequest, exception: Any = None) -> TemplateResponse:
    """Render a safe PT-BR 403 response."""
    return _error_response(
        request,
        status=403,
        title=_("Acesso não autorizado"),
        message=_("Você não tem permissão para acessar este conteúdo."),
    )


def page_not_found(request: HttpRequest, exception: Any = None) -> TemplateResponse:
    """Render a safe PT-BR 404 response."""
    return _error_response(
        request,
        status=404,
        title=_("Página não encontrada"),
        message=_("A página solicitada não foi encontrada."),
    )


def server_error(request: HttpRequest, exception: Any = None) -> TemplateResponse:
    """Render a safe PT-BR 500 response."""
    return _error_response(
        request,
        status=500,
        title=_("Erro inesperado"),
        message=_("Ocorreu um erro inesperado."),
    )
