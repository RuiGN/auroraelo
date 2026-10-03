"""Telas da equipe: o que o paciente compartilha do app (diário e check-ins).

O paciente escreve só no aplicativo (`/api/v1/mobile/`). Aqui o terapeuta com vínculo
ativo lê o que foi marcado como compartilhável, pede acesso aos registros "perguntar
antes" e acompanha o estado do pedido. A resposta ao pedido é só do paciente.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any, cast
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from clinics.services import authorized_active_clinic
from core.services import current_correlation_id
from people.selectors import patient_profile_in_clinic

from . import selectors, services
from .forms import (
    CHECKIN_WINDOW_CHOICES,
    PERIOD_CHOICES,
    AccessRequestForm,
    CheckInWindowForm,
    DiaryFilterForm,
)
from .policies import DiaryTarget, StaffDiaryPolicy
from .presentation import (
    ACCESS_STATE_LABELS,
    ACCESS_STATE_TONES,
    CHECKIN_QUESTION_LABELS,
    emotion_labels,
    mood_label,
)

LAYOUT = "layouts/aurora_elo.html"
PAGE_SIZE = 10
DEFAULT_PERIOD = "30d"
DEFAULT_CHECKIN_DAYS = 14
# Ação da matriz de autorização: o diário é dado clínico declarado (só terapeuta).
ACTION_CLINICAL_READ = "patient.clinical.read"


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def _no_store[ViewFunc: Callable[..., HttpResponse]](view: ViewFunc) -> ViewFunc:
    """Páginas com dado de paciente nunca ficam em cache de navegador ou proxy."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return cast(ViewFunc, wrapper)


def _context(
    request: HttpRequest, patient_id: UUID
) -> tuple[AbstractBaseUser, UUID, Any]:
    """Autoriza ator, clínica e vínculo; qualquer falha é o mesmo 403.

    O paciente da URL nunca é confiado: só abre se for da clínica ativa e estiver
    vinculado ao terapeuta. Paciente inexistente, de outra clínica ou sem vínculo
    respondem igual, sem revelar existência.
    """
    actor = request.user
    clinic = getattr(request, "clinic", None)
    if not isinstance(actor, AbstractBaseUser) or clinic is None:
        raise PermissionDenied
    clinic_id = cast(UUID, clinic.pk)
    authorized_active_clinic(
        clinic_id=clinic_id, actor=actor, action=ACTION_CLINICAL_READ
    )
    target = DiaryTarget(clinic_id=clinic_id, patient_profile_id=patient_id)
    if not StaffDiaryPolicy().is_allowed(actor, target):
        raise PermissionDenied
    patient = patient_profile_in_clinic(
        clinic_id=clinic_id, patient_profile_id=patient_id
    )
    if patient is None:
        raise PermissionDenied
    return actor, clinic_id, patient


def _page(
    request: HttpRequest, template: str, context: dict[str, Any]
) -> TemplateResponse:
    return TemplateResponse(request, template, {"layout_template": LAYOUT, **context})


def _patient_name(patient: Any) -> str:
    return str(patient.social_name or patient.full_name)


def _entry_card(row: selectors.StaffEntryRow) -> dict[str, Any]:
    entry = row.entry
    return {
        "entry": entry,
        "mood_label": mood_label(entry.mood),
        "emotions": emotion_labels(list(entry.emotions or [])),
        "is_granted": row.release == selectors.RELEASE_GRANTED,
        "granted_until": row.granted_until,
    }


def _state_view(state: str) -> dict[str, str]:
    return {
        "code": state,
        "label": str(ACCESS_STATE_LABELS[state]),
        "tone": ACCESS_STATE_TONES[state],
    }


# ── Diário do paciente ──────────────────────────────────────────────────────


@_no_store
@login_required
@require_GET
def patient_diary(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    """Registros que o paciente compartilha (ou liberou a pedido) e os pedidos."""
    actor, clinic_id, patient = _context(request, patient_id)
    form = DiaryFilterForm(request.GET)
    period = DEFAULT_PERIOD
    if form.is_valid() and form.cleaned_data["periodo"]:
        period = form.cleaned_data["periodo"]
    diary = selectors.therapist_patient_diary(
        clinic_id=clinic_id,
        therapist_id=actor.pk,
        patient_profile_id=patient.pk,
        period=period,
    )
    # A leitura é auditada antes de o conteúdo sair; só o paciente aparece no log.
    services.record_staff_diary_read(
        clinic_id=clinic_id,
        actor=actor,
        patient_profile_id=patient.pk,
        request_id=_request_uuid(),
    )
    page = Paginator(diary.entries, PAGE_SIZE).get_page(request.GET.get("pagina"))
    cards = [_entry_card(row) for row in page.object_list]
    return _page(
        request,
        "journal/staff_diary.html",
        {
            "page_title": _("Diário de %(name)s") % {"name": _patient_name(patient)},
            "patient": patient,
            "patient_name": _patient_name(patient),
            "section": "diary",
            "period": period,
            "period_choices": PERIOD_CHOICES,
            "page": page,
            "cards": cards,
            "entry_count": len(diary.entries),
            "confirmation_rows": [
                {"row": row, "state": _state_view(row.state)}
                for row in diary.confirmation
            ],
            "request_rows": [
                {"row": row, "state": _state_view(row.state)} for row in diary.requests
            ],
        },
    )


# ── Check-ins ───────────────────────────────────────────────────────────────


@_no_store
@login_required
@require_GET
def patient_checkins(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    """Série curta das sete perguntas 1 a 5 dos check-ins compartilhados."""
    actor, clinic_id, patient = _context(request, patient_id)
    form = CheckInWindowForm(request.GET)
    days = DEFAULT_CHECKIN_DAYS
    if form.is_valid() and form.cleaned_data["dias"]:
        days = int(form.cleaned_data["dias"])
    series = selectors.therapist_patient_checkin_series(
        clinic_id=clinic_id,
        therapist_id=actor.pk,
        patient_profile_id=patient.pk,
        days=days,
    )
    services.record_staff_checkins_read(
        clinic_id=clinic_id,
        actor=actor,
        patient_profile_id=patient.pk,
        request_id=_request_uuid(),
    )
    questions = [
        {
            "series": item,
            "label": CHECKIN_QUESTION_LABELS[item.key],
            "bars": [
                {"day": day, "score": score}
                for day, score in zip(series.days, item.scores, strict=True)
            ],
        }
        for item in series.questions
    ]
    question_labels = [
        CHECKIN_QUESTION_LABELS[key] for key in selectors.CHECKIN_SCALE_KEYS
    ]
    day_rows = [
        {"day": row.day, "cells": list(zip(question_labels, row.scores, strict=True))}
        for row in series.rows
    ]
    return _page(
        request,
        "journal/staff_checkins.html",
        {
            "page_title": _("Check-ins de %(name)s") % {"name": _patient_name(patient)},
            "patient": patient,
            "patient_name": _patient_name(patient),
            "section": "checkins",
            "days": days,
            "window_choices": CHECKIN_WINDOW_CHOICES,
            "series": series,
            "questions": questions,
            "day_rows": day_rows,
            "question_labels": question_labels,
        },
    )


# ── Pedido de acesso ────────────────────────────────────────────────────────


def _blocked_message(state: str) -> str:
    if state == selectors.ACCESS_PENDING:
        return _("Já existe um pedido aguardando a resposta do paciente.")
    if state == selectors.ACCESS_GRANTED:
        return _("Este registro já foi liberado pelo paciente.")
    return _(
        "O paciente recusou este pedido. Só ele pode liberar o registro, "
        "pelo aplicativo."
    )


@_no_store
@login_required
@require_http_methods(["GET", "POST"])
def access_request_create(
    request: HttpRequest, patient_id: UUID, entry_id: UUID
) -> HttpResponse:
    """A equipe pede ao paciente acesso a um registro "perguntar antes"."""
    actor, clinic_id, patient = _context(request, patient_id)
    confirmation = selectors.therapist_confirmation_entry(
        clinic_id=clinic_id,
        therapist_id=actor.pk,
        patient_profile_id=patient.pk,
        entry_id=entry_id,
    )
    if confirmation is None:
        # Registro privado, compartilhável, de outro paciente ou inexistente.
        raise PermissionDenied
    diary_url = reverse("journal:patient_diary", args=[patient.pk])
    if not confirmation.can_request:
        messages.warning(request, _blocked_message(confirmation.state))
        return redirect(diary_url)

    form = AccessRequestForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        expires_at = timezone.now() + timedelta(
            days=int(form.cleaned_data["validity_days"])
        )
        try:
            services.request_journal_entry_access(
                clinic_id=clinic_id,
                therapist=actor,
                journal_entry_id=confirmation.entry_id,
                purpose=form.cleaned_data["purpose"],
                expires_at=expires_at,
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(
                request,
                _("Pedido enviado. O paciente responde pelo aplicativo."),
            )
            return redirect(diary_url)
    return _page(
        request,
        "journal/staff_access_request_form.html",
        {
            "page_title": _("Pedir acesso a um registro"),
            "patient": patient,
            "patient_name": _patient_name(patient),
            "entry": confirmation,
            "form": form,
            "cancel_url": diary_url,
        },
    )
