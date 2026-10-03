"""Telas web do concierge e do acompanhamento pós-alta (equipe da clínica)."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from clinics.services import authorized_active_clinic
from core.services import current_correlation_id
from people.selectors import patient_profile_in_clinic

from . import selectors, services
from .contracts import (
    ACTION_MANAGE,
    ACTION_MANAGE_RULES,
    ACTION_READ,
    MAX_RULE_STEPS,
    ContactStatus,
    DischargeStatus,
)
from .forms import (
    CompleteContactForm,
    CorrectLogForm,
    DischargeForm,
    FamilyConsentForm,
    FamilyContactForm,
    FamilyRequestForm,
    ForwardRequestForm,
    LogForm,
    MissedForm,
    NewFamilyContactForm,
    ReasonForm,
    RescheduleForm,
    ResolveRequestForm,
    RuleForm,
)
from .models import (
    AftercareContact,
    ConciergeLog,
    FamilyContact,
    FamilyRequest,
)

LAYOUT = "layouts/aurora_elo.html"


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


def _context(request: HttpRequest, action: str) -> tuple[AbstractBaseUser, UUID]:
    """Resolve ator e clínica ativa e exige a ação; nunca confia em IDs da URL."""
    actor = request.user
    clinic = getattr(request, "clinic", None)
    if not isinstance(actor, AbstractBaseUser) or clinic is None:
        raise PermissionDenied
    authorized_active_clinic(clinic_id=clinic.pk, actor=actor, action=action)
    return actor, cast(UUID, clinic.pk)


def _page(
    request: HttpRequest, template: str, context: dict[str, Any]
) -> TemplateResponse:
    return TemplateResponse(request, template, {"layout_template": LAYOUT, **context})


def _form_page(
    request: HttpRequest,
    *,
    title: str,
    form: Any,
    submit_label: str,
    cancel_url: str,
    lead: str = "",
    danger: bool = False,
    breadcrumb: list[tuple[str, str]] | None = None,
) -> TemplateResponse:
    return _page(
        request,
        "concierge/form.html",
        {
            "page_title": title,
            "form": form,
            "submit_label": submit_label,
            "cancel_url": cancel_url,
            "lead": lead,
            "danger": danger,
            "breadcrumb": breadcrumb or [],
        },
    )


def _family_choices(
    clinic_id: UUID, patient_profile_id: UUID, *, only_contactable: bool
) -> list[tuple[str, str]]:
    return [
        (str(item.pk), f"{item.full_name} ({item.relationship})")
        for item in selectors.family_contacts_for_patient(
            clinic_id=clinic_id, patient_profile_id=patient_profile_id
        )
        if item.can_be_contacted or not only_contactable
    ]


def _fail(request: HttpRequest, form: Any, error: ValidationError) -> None:
    form.add_error(None, error)


def _patient_or_denied(clinic_id: UUID, patient_id: UUID) -> Any:
    patient = patient_profile_in_clinic(
        clinic_id=clinic_id, patient_profile_id=patient_id
    )
    if patient is None:
        raise PermissionDenied
    return patient


# ── Painel e fila ───────────────────────────────────────────────────────────


@login_required
@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    summary = selectors.dashboard_summary(
        clinic_id=clinic_id, today=timezone.localdate()
    )
    return _page(
        request,
        "concierge/dashboard.html",
        {"page_title": _("Acompanhamento pós-alta"), "summary": summary},
    )


@login_required
@require_GET
def contact_queue(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    window = request.GET.get("janela", "all")
    kind = request.GET.get("tipo", "")
    rows = selectors.contact_queue(
        clinic_id=clinic_id, today=timezone.localdate(), window=window, kind=kind
    )
    return _page(
        request,
        "concierge/contact_queue.html",
        {
            "page_title": _("Fila de contatos"),
            "rows": rows,
            "window": window if window in selectors.QUEUE_WINDOWS else "all",
            "kind": kind,
        },
    )


# ── Altas ───────────────────────────────────────────────────────────────────


@login_required
@require_GET
def discharge_list(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    status = request.GET.get("situacao", "")
    return _page(
        request,
        "concierge/discharge_list.html",
        {
            "page_title": _("Altas"),
            "discharges": selectors.discharge_list(clinic_id=clinic_id, status=status),
            "status": status if status in DischargeStatus.values else "",
            "today": timezone.localdate(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def discharge_create(request: HttpRequest) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    options = selectors.patient_options_for_discharge(clinic_id=clinic_id)
    form = DischargeForm(
        request.POST or None,
        patient_choices=[(str(p.pk), p.full_name) for p in options],
        initial={"discharge_date": timezone.localdate()},
    )
    if request.method == "POST" and form.is_valid():
        try:
            discharge = services.register_discharge(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=UUID(form.cleaned_data["patient"]),
                discharge_date=form.cleaned_data["discharge_date"],
                notes=form.cleaned_data["notes"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(
                request, _("Alta registrada. A agenda de contatos foi criada.")
            )
            return redirect("concierge:discharge_detail", discharge_id=discharge.pk)
    return _form_page(
        request,
        title=_("Registrar alta"),
        form=form,
        submit_label=_("Registrar alta"),
        cancel_url=reverse("concierge:discharge_list"),
        lead=_(
            "A agenda de ligações e visita é gerada automaticamente pela régua "
            "vigente da clínica."
        ),
    )


@login_required
@require_GET
def discharge_detail(request: HttpRequest, discharge_id: UUID) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    discharge = selectors.discharge_detail(
        clinic_id=clinic_id, discharge_id=discharge_id
    )
    if discharge is None:
        raise PermissionDenied
    today = timezone.localdate()
    contacts = sorted(discharge.contacts.all(), key=lambda c: (c.due_date, c.kind))
    rows = [
        selectors.ContactRow(
            contact=c,
            patient_profile_id=discharge.patient_profile_id,
            patient_name=discharge.patient_profile.full_name,
            discharge_date=discharge.discharge_date,
            state=selectors.contact_state(c, today),
        )
        for c in contacts
    ]
    return _page(
        request,
        "concierge/discharge_detail.html",
        {
            "page_title": _("Alta de %(name)s")
            % {"name": discharge.patient_profile.full_name},
            "discharge": discharge,
            "rows": rows,
            "scheduled": ContactStatus.SCHEDULED.value,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def discharge_cancel(request: HttpRequest, discharge_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    discharge = selectors.discharge_detail(
        clinic_id=clinic_id, discharge_id=discharge_id
    )
    if discharge is None:
        raise PermissionDenied
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.cancel_discharge(
                clinic_id=clinic_id,
                actor=actor,
                discharge_id=discharge_id,
                reason=form.cleaned_data["reason"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Alta cancelada."))
            return redirect("concierge:discharge_list")
    return _form_page(
        request,
        title=_("Cancelar alta"),
        form=form,
        submit_label=_("Cancelar alta"),
        cancel_url=reverse("concierge:discharge_detail", args=[discharge_id]),
        lead=_(
            "Use apenas para alta registrada por engano. Os contatos ainda "
            "agendados serão cancelados."
        ),
        danger=True,
    )


# ── Contatos pós-alta ───────────────────────────────────────────────────────


def _contact_or_denied(clinic_id: UUID, contact_id: UUID) -> AftercareContact:
    contact = (
        AftercareContact.objects.for_clinic(clinic_id)
        .select_related("discharge", "discharge__patient_profile")
        .filter(pk=contact_id)
        .first()
    )
    if contact is None:
        raise PermissionDenied
    return contact


@login_required
@require_http_methods(["GET", "POST"])
def contact_complete(request: HttpRequest, contact_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    contact = _contact_or_denied(clinic_id, contact_id)
    patient_id = contact.discharge.patient_profile_id
    form = CompleteContactForm(
        request.POST or None,
        kind=contact.kind,
        family_choices=_family_choices(clinic_id, patient_id, only_contactable=True),
    )
    if request.method == "POST" and form.is_valid():
        family_id = form.cleaned_data["family_contact"]
        try:
            services.complete_contact(
                clinic_id=clinic_id,
                actor=actor,
                contact_id=contact_id,
                outcome=form.cleaned_data["outcome"],
                notes=form.cleaned_data["notes"],
                family_contact_id=UUID(family_id) if family_id else None,
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Contato registrado."))
            return redirect(
                "concierge:discharge_detail", discharge_id=contact.discharge_id
            )
    return _form_page(
        request,
        title=_("Registrar %(kind)s do %(day)dº dia")
        % {
            "kind": contact.get_kind_display().lower(),
            "day": contact.day_after_discharge,
        },
        form=form,
        submit_label=_("Registrar resultado"),
        cancel_url=reverse("concierge:discharge_detail", args=[contact.discharge_id]),
        lead=_("Paciente: %(name)s")
        % {"name": contact.discharge.patient_profile.full_name},
    )


@login_required
@require_http_methods(["GET", "POST"])
def contact_reschedule(request: HttpRequest, contact_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    contact = _contact_or_denied(clinic_id, contact_id)
    form = RescheduleForm(
        request.POST or None, initial={"new_due_date": contact.due_date}
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.reschedule_contact(
                clinic_id=clinic_id,
                actor=actor,
                contact_id=contact_id,
                new_due_date=form.cleaned_data["new_due_date"],
                reason=form.cleaned_data["reason"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Contato reagendado."))
            return redirect(
                "concierge:discharge_detail", discharge_id=contact.discharge_id
            )
    return _form_page(
        request,
        title=_("Reagendar contato"),
        form=form,
        submit_label=_("Reagendar"),
        cancel_url=reverse("concierge:discharge_detail", args=[contact.discharge_id]),
        lead=_("Data prevista atual: %(date)s")
        % {"date": contact.due_date.strftime("%d/%m/%Y")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def contact_missed(request: HttpRequest, contact_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    contact = _contact_or_denied(clinic_id, contact_id)
    form = MissedForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.mark_contact_missed(
                clinic_id=clinic_id,
                actor=actor,
                contact_id=contact_id,
                notes=form.cleaned_data["notes"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Contato encerrado como não realizado."))
            return redirect(
                "concierge:discharge_detail", discharge_id=contact.discharge_id
            )
    return _form_page(
        request,
        title=_("Encerrar como não realizado"),
        form=form,
        submit_label=_("Encerrar contato"),
        cancel_url=reverse("concierge:discharge_detail", args=[contact.discharge_id]),
        danger=True,
    )


# ── Paciente: visão consolidada ─────────────────────────────────────────────


@login_required
@require_GET
def patient_detail(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    patient = _patient_or_denied(clinic_id, patient_id)
    discharges = [
        d
        for d in selectors.discharge_list(clinic_id=clinic_id)
        if d.patient_profile_id == patient.pk
    ]
    return _page(
        request,
        "concierge/patient_detail.html",
        {
            "page_title": patient.full_name,
            "patient": patient,
            "discharges": discharges,
            "family_contacts": selectors.family_contacts_for_patient(
                clinic_id=clinic_id,
                patient_profile_id=patient.pk,
                include_inactive=True,
            ),
            "requests": selectors.family_request_list(
                clinic_id=clinic_id, status="all", patient_profile_id=patient.pk
            ),
            "timeline": selectors.patient_timeline(
                clinic_id=clinic_id, patient_profile_id=patient.pk
            ),
        },
    )


# ── Família ─────────────────────────────────────────────────────────────────


@login_required
@require_http_methods(["GET", "POST"])
def family_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    patient = _patient_or_denied(clinic_id, patient_id)
    form = NewFamilyContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.add_family_contact(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=patient.pk,
                full_name=data["full_name"],
                relationship=data["relationship"],
                phone=data["phone"],
                email=data["email"],
                is_primary=data["is_primary"],
                consent_to_contact=data["consent_to_contact"],
                consent_note=data["consent_note"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Familiar cadastrado."))
            return redirect("concierge:patient_detail", patient_id=patient.pk)
    return _form_page(
        request,
        title=_("Novo contato da família"),
        form=form,
        submit_label=_("Salvar familiar"),
        cancel_url=reverse("concierge:patient_detail", args=[patient.pk]),
        lead=_(
            "A clínica só entra em contato com a família quando o paciente "
            "autoriza. Telefone e e-mail ficam cifrados no banco."
        ),
    )


def _family_or_denied(clinic_id: UUID, family_id: UUID) -> FamilyContact:
    contact = FamilyContact.objects.for_clinic(clinic_id).filter(pk=family_id).first()
    if contact is None:
        raise PermissionDenied
    return contact


@login_required
@require_http_methods(["GET", "POST"])
def family_edit(request: HttpRequest, family_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    family = _family_or_denied(clinic_id, family_id)
    form = FamilyContactForm(
        request.POST or None,
        initial={
            "full_name": family.full_name,
            "relationship": family.relationship,
            "phone": family.phone,
            "email": family.email,
            "is_primary": family.is_primary,
        },
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.update_family_contact(
                clinic_id=clinic_id,
                actor=actor,
                family_contact_id=family_id,
                full_name=data["full_name"],
                relationship=data["relationship"],
                phone=data["phone"],
                email=data["email"],
                is_primary=data["is_primary"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Dados do familiar atualizados."))
            return redirect(
                "concierge:patient_detail", patient_id=family.patient_profile_id
            )
    return _form_page(
        request,
        title=_("Editar contato da família"),
        form=form,
        submit_label=_("Salvar"),
        cancel_url=reverse(
            "concierge:patient_detail", args=[family.patient_profile_id]
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def family_consent(request: HttpRequest, family_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    family = _family_or_denied(clinic_id, family_id)
    form = FamilyConsentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.set_family_consent(
                clinic_id=clinic_id,
                actor=actor,
                family_contact_id=family_id,
                granted=form.cleaned_data["decision"] == "grant",
                note=form.cleaned_data["note"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Autorização do paciente registrada."))
            return redirect(
                "concierge:patient_detail", patient_id=family.patient_profile_id
            )
    return _form_page(
        request,
        title=_("Autorização de contato com a família"),
        form=form,
        submit_label=_("Registrar decisão"),
        cancel_url=reverse(
            "concierge:patient_detail", args=[family.patient_profile_id]
        ),
        lead=_("Familiar: %(name)s") % {"name": family.full_name},
    )


@login_required
@require_POST
def family_deactivate(request: HttpRequest, family_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    family = _family_or_denied(clinic_id, family_id)
    try:
        services.deactivate_family_contact(
            clinic_id=clinic_id,
            actor=actor,
            family_contact_id=family_id,
            request_id=_request_uuid(),
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, _("Contato da família inativado."))
    return redirect("concierge:patient_detail", patient_id=family.patient_profile_id)


# ── Registro do concierge ───────────────────────────────────────────────────


@login_required
@require_GET
def log_list(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    return _page(
        request,
        "concierge/log_list.html",
        {
            "page_title": _("Registro do concierge"),
            "logs": selectors.recent_logs(clinic_id=clinic_id),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def log_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    patient = _patient_or_denied(clinic_id, patient_id)
    choices = _family_choices(clinic_id, patient.pk, only_contactable=True)
    form = LogForm(
        request.POST or None,
        family_choices=choices,
        initial={"direction": "outbound", "channel": "call"},
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.record_log(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=patient.pk,
                family_contact_id=UUID(data["family_contact"]),
                channel=data["channel"],
                direction=data["direction"],
                occurred_at=data["occurred_at"],
                summary=data["summary"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Contato registrado."))
            return redirect("concierge:patient_detail", patient_id=patient.pk)
    return _form_page(
        request,
        title=_("Registrar contato com a família"),
        form=form,
        submit_label=_("Registrar contato"),
        cancel_url=reverse("concierge:patient_detail", args=[patient.pk]),
        lead=_(
            "O registro não pode ser editado nem apagado. Se errar, use "
            "«Corrigir»: o texto original permanece no histórico."
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def log_correct(request: HttpRequest, log_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    log = ConciergeLog.objects.for_clinic(clinic_id).filter(pk=log_id).first()
    if log is None:
        raise PermissionDenied
    form = CorrectLogForm(request.POST or None, initial={"new_summary": log.summary})
    if request.method == "POST" and form.is_valid():
        try:
            services.correct_log(
                clinic_id=clinic_id,
                actor=actor,
                log_id=log_id,
                new_summary=form.cleaned_data["new_summary"],
                reason=form.cleaned_data["reason"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Correção registrada."))
            return redirect(
                "concierge:patient_detail", patient_id=log.patient_profile_id
            )
    return _form_page(
        request,
        title=_("Corrigir registro"),
        form=form,
        submit_label=_("Salvar correção"),
        cancel_url=reverse("concierge:patient_detail", args=[log.patient_profile_id]),
        lead=_("O texto original continua visível no histórico."),
    )


# ── Pedidos do paciente à família ───────────────────────────────────────────


@login_required
@require_GET
def request_list(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    status = request.GET.get("situacao", "open")
    return _page(
        request,
        "concierge/request_list.html",
        {
            "page_title": _("Pedidos dos pacientes"),
            "requests": selectors.family_request_list(
                clinic_id=clinic_id, status=status
            ),
            "status": status,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def request_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    patient = _patient_or_denied(clinic_id, patient_id)
    form = FamilyRequestForm(
        request.POST or None,
        family_choices=_family_choices(clinic_id, patient.pk, only_contactable=True),
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.register_family_request(
                clinic_id=clinic_id,
                actor=actor,
                patient_profile_id=patient.pk,
                family_contact_id=UUID(data["family_contact"]),
                kind=data["kind"],
                description=data["description"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(
                request,
                _("Pedido registrado. A família ainda não foi contatada."),
            )
            return redirect("concierge:patient_detail", patient_id=patient.pk)
    return _form_page(
        request,
        title=_("Registrar pedido do paciente"),
        form=form,
        submit_label=_("Registrar pedido"),
        cancel_url=reverse("concierge:patient_detail", args=[patient.pk]),
        lead=_(
            "O pedido só é dado como encaminhado depois que você registrar o "
            "contato com a família."
        ),
    )


def _request_or_denied(clinic_id: UUID, request_pk: UUID) -> FamilyRequest:
    obj = FamilyRequest.objects.for_clinic(clinic_id).filter(pk=request_pk).first()
    if obj is None:
        raise PermissionDenied
    return obj


@login_required
@require_http_methods(["GET", "POST"])
def request_forward(request: HttpRequest, request_pk: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    family_request = _request_or_denied(clinic_id, request_pk)
    form = ForwardRequestForm(request.POST or None, initial={"channel": "call"})
    if request.method == "POST" and form.is_valid():
        try:
            services.forward_family_request(
                clinic_id=clinic_id,
                actor=actor,
                family_request_id=request_pk,
                channel=form.cleaned_data["channel"],
                summary=form.cleaned_data["summary"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Encaminhamento à família registrado."))
            return redirect("concierge:request_list")
    return _form_page(
        request,
        title=_("Registrar encaminhamento à família"),
        form=form,
        submit_label=_("Registrar encaminhamento"),
        cancel_url=reverse("concierge:request_list"),
        lead=_("Pedido: %(text)s") % {"text": family_request.description},
    )


@login_required
@require_http_methods(["GET", "POST"])
def request_resolve(request: HttpRequest, request_pk: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    family_request = _request_or_denied(clinic_id, request_pk)
    form = ResolveRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.resolve_family_request(
                clinic_id=clinic_id,
                actor=actor,
                family_request_id=request_pk,
                fulfilled=form.cleaned_data["outcome"] == "fulfilled",
                note=form.cleaned_data["note"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Pedido concluído."))
            return redirect("concierge:request_list")
    return _form_page(
        request,
        title=_("Concluir pedido"),
        form=form,
        submit_label=_("Concluir pedido"),
        cancel_url=reverse("concierge:request_list"),
        lead=_("Pedido: %(text)s") % {"text": family_request.description},
    )


@login_required
@require_http_methods(["GET", "POST"])
def request_cancel(request: HttpRequest, request_pk: UUID) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE)
    _request_or_denied(clinic_id, request_pk)
    form = ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.cancel_family_request(
                clinic_id=clinic_id,
                actor=actor,
                family_request_id=request_pk,
                reason=form.cleaned_data["reason"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(request, _("Pedido cancelado."))
            return redirect("concierge:request_list")
    return _form_page(
        request,
        title=_("Cancelar pedido"),
        form=form,
        submit_label=_("Cancelar pedido"),
        cancel_url=reverse("concierge:request_list"),
        danger=True,
    )


# ── Régua de comunicação ────────────────────────────────────────────────────


@login_required
@require_GET
def rule_list(request: HttpRequest) -> HttpResponse:
    _actor, clinic_id = _context(request, ACTION_READ)
    rules = selectors.rule_history(clinic_id=clinic_id)
    current = next((rule for rule in rules if rule.is_active), None)
    return _page(
        request,
        "concierge/rule_list.html",
        {
            "page_title": _("Régua de comunicação"),
            "current": current,
            "steps": selectors.rule_steps(clinic_id=clinic_id, rule_id=current.pk)
            if current
            else [],
            "history": rules,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def rule_edit(request: HttpRequest) -> HttpResponse:
    actor, clinic_id = _context(request, ACTION_MANAGE_RULES)
    current = selectors.active_rule(clinic_id=clinic_id)
    initial: dict[str, Any] = {"name": current.name if current else ""}
    if current is not None:
        for index, step in enumerate(
            selectors.rule_steps(clinic_id=clinic_id, rule_id=current.pk)
        ):
            initial[f"step_{index}_kind"] = step.kind
            initial[f"step_{index}_day"] = step.day_after_discharge
            initial[f"step_{index}_role"] = step.responsible_role
    form = RuleForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_communication_rule(
                clinic_id=clinic_id,
                actor=actor,
                name=form.cleaned_data["name"],
                steps=form.cleaned_data["steps"],
                request_id=_request_uuid(),
            )
        except ValidationError as error:
            _fail(request, form, error)
        else:
            messages.success(
                request,
                _("Nova versão da régua salva. Vale para as próximas altas."),
            )
            return redirect("concierge:rule_list")
    return _page(
        request,
        "concierge/rule_form.html",
        {
            "page_title": _("Editar régua de comunicação"),
            "form": form,
            "step_rows": [
                {
                    "number": index + 1,
                    "kind": form[f"step_{index}_kind"],
                    "day": form[f"step_{index}_day"],
                    "role": form[f"step_{index}_role"],
                }
                for index in range(MAX_RULE_STEPS)
            ],
            "cancel_url": reverse("concierge:rule_list"),
        },
    )


__all__ = [
    "contact_complete",
    "contact_missed",
    "contact_queue",
    "contact_reschedule",
    "dashboard",
    "discharge_cancel",
    "discharge_create",
    "discharge_detail",
    "discharge_list",
    "family_consent",
    "family_create",
    "family_deactivate",
    "family_edit",
    "log_correct",
    "log_create",
    "log_list",
    "patient_detail",
    "request_cancel",
    "request_create",
    "request_forward",
    "request_list",
    "request_resolve",
    "rule_edit",
    "rule_list",
]
