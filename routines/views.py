"""Team screens for a patient's medication, care plan and habits.

The patient never opens these pages: they use the post-discharge app
(``/api/v1/mobile/``), which shows exactly what the team registers here. Because the
app publishes a medication or a habit as soon as it is saved, every screen says what
the patient will see and when, and a prescription needs an explicit confirmation.

Authorization lives here, with the domain policy: the routines services only check
the clinic, so each view first resolves the patient (same clinic, current care link
for therapists) and then resolves every object restricted to that patient.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import wraps
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from audit.services import record_audit_event
from core.services import current_correlation_id
from people.selectors import patient_profile_in_clinic, professional_display_names

from . import selectors
from .care_plan_services import (
    close_care_plan,
    pause_care_plan,
    propose_care_plan,
    reopen_care_plan_draft,
    resume_care_plan,
    sign_care_plan,
    submit_care_plan_for_signature,
    update_care_plan_draft,
)
from .forms import (
    CarePlanCloseForm,
    CarePlanForm,
    ConfirmForm,
    HabitForm,
    HabitPauseForm,
    MedicationForm,
    MedicationStopForm,
    care_plan_action_formset,
)
from .medication_services import (
    course_has_ended,
    end_prescribed_medication,
    register_prescribed_medication,
    resume_prescribed_medication,
    suspend_prescribed_medication,
    update_prescribed_medication,
)
from .models import (
    CarePlan,
    CarePlanStatus,
    CheckInStatus,
    HabitFrequency,
    HabitStatus,
    MedicationLogStatus,
    PatientResponseChoice,
    TimeOfDayWindow,
)
from .policies import (
    can_author_care_plan,
    can_staff_manage_patient_care,
    can_view_medication_adherence,
)
from .presentation import (
    CHECKIN_BADGES,
    CHECKIN_LABELS,
    DOSE_STATUS_LABELS,
    FREQUENCY_LABELS,
    HABIT_STATUS_LABELS,
    PLAN_STATUS_BADGES,
    PLAN_STATUS_LABELS,
    PLAN_VISIBILITY,
    RESPONSE_BADGES,
    RESPONSE_LABELS,
    ROUTE_LABELS,
    WEEKDAY_SHORT_LABELS,
    WINDOW_LABELS,
)
from .services import (
    archive_habit,
    create_habit,
    pause_habit,
    resume_habit,
    update_habit,
)

LAYOUT = "layouts/aurora_elo.html"
RECENT_DAYS = 14
MAX_RECENT_ROWS = 30
DEFAULT_ZONE = "America/Sao_Paulo"

ViewFunc = Callable[..., HttpResponse]


def private_no_store(view: ViewFunc) -> ViewFunc:
    """Mark the response as private health data: no browser or proxy cache."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = view(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    return wrapper


def _request_uuid() -> UUID:
    try:
        return UUID(current_correlation_id())
    except ValueError, TypeError:
        return uuid4()


# ── Autorização e contexto ──────────────────────────────────────────────────


@dataclass(frozen=True)
class Staff:
    """The authorized actor, the active clinic and the patient of the URL."""

    actor: AbstractBaseUser
    clinic_id: UUID
    patient: Any
    patient_id: UUID


def _staff(request: HttpRequest, patient_id: UUID) -> Staff:
    """Resolve actor and patient or deny with the same 403 for every refusal.

    A patient of another clinic, an unknown id, a therapist without a care link,
    administrative staff and a patient session all get the same answer, so the
    response never reveals whether the patient exists.
    """
    actor = request.user
    clinic = getattr(request, "clinic", None)
    if not isinstance(actor, AbstractBaseUser) or clinic is None:
        raise PermissionDenied
    patient = patient_profile_in_clinic(
        clinic_id=clinic.pk, patient_profile_id=patient_id
    )
    if patient is None or not can_staff_manage_patient_care(
        user=actor,
        clinic_id=clinic.pk,
        patient_profile_id=patient.pk,
        patient_user_id=patient.user_id,
    ):
        raise PermissionDenied
    return Staff(
        actor=actor, clinic_id=clinic.pk, patient=patient, patient_id=patient.pk
    )


def _patient_zone(patient: Any) -> ZoneInfo:
    try:
        return ZoneInfo(str(patient.timezone_name))
    except ZoneInfoNotFoundError, ValueError:
        return ZoneInfo(DEFAULT_ZONE)


def _patient_today(patient: Any) -> date:
    return timezone.now().astimezone(_patient_zone(patient)).date()


def _bound(request: HttpRequest) -> Any:
    return request.POST if request.method == "POST" else None


Crumb = tuple[str, str | None]


def _crumbs(staff: Staff, section: str, *trail: Crumb) -> list[Crumb]:
    pid = staff.patient_id
    sections = {
        "medication": (_("Medicação"), reverse("routines:medication_list", args=[pid])),
        "plans": (
            _("Planos de cuidado"),
            reverse("routines:care_plan_list", args=[pid]),
        ),
        "habits": (_("Hábitos"), reverse("routines:habit_list", args=[pid])),
    }
    label, url = sections[section]
    return [(label, url if trail else None), *trail]


def _page(
    request: HttpRequest,
    template: str,
    staff: Staff,
    *,
    section: str,
    title: str,
    lead: str = "",
    crumbs: list[Crumb] | None = None,
    **context: Any,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        template,
        {
            "layout_template": LAYOUT,
            "patient": staff.patient,
            "section": section,
            "page_title": title,
            "lead": lead,
            "breadcrumb": crumbs if crumbs is not None else _crumbs(staff, section),
            **context,
        },
    )


def _form_page(
    request: HttpRequest,
    staff: Staff,
    *,
    section: str,
    title: str,
    form: Any,
    submit_label: str,
    cancel_url: str,
    lead: str = "",
    notice: str = "",
    crumbs: list[Crumb] | None = None,
) -> TemplateResponse:
    return _page(
        request,
        "routines/form.html",
        staff,
        section=section,
        title=title,
        lead=lead,
        crumbs=crumbs,
        form=form,
        submit_label=submit_label,
        cancel_url=cancel_url,
        notice=notice,
    )


def _service_failed(form: Any) -> None:
    """A rule the form could not foresee (a concurrent change); nothing was saved."""
    form.add_error(
        None,
        _("A alteração não foi concluída. Atualize a página e tente novamente."),
    )


def _confirm_page(
    request: HttpRequest,
    staff: Staff,
    *,
    section: str,
    title: str,
    form: Any,
    submit_label: str,
    cancel_url: str,
    perform: Callable[[], object],
    success: str,
    next_url: str,
    lead: str = "",
    notice: str = "",
    danger: bool = False,
    rows: list[tuple[str, str]] | None = None,
    crumbs: list[Crumb] | None = None,
    **extra: Any,
) -> HttpResponse:
    """One confirmation screen: GET shows it, a valid POST performs and redirects."""
    if request.method == "POST" and form.is_valid():
        try:
            perform()
        except ValidationError:
            _service_failed(form)
        else:
            messages.success(request, success)
            return redirect(next_url)
    return _page(
        request,
        "routines/confirm.html",
        staff,
        section=section,
        title=title,
        lead=lead,
        crumbs=crumbs,
        form=form,
        submit_label=submit_label,
        cancel_url=cancel_url,
        notice=notice,
        danger=danger,
        rows=rows or [],
        **extra,
    )


def _refuse(request: HttpRequest, message: str, url: str) -> HttpResponse:
    messages.error(request, message)
    return redirect(url)


def _fmt_date(value: date | None) -> str:
    return date_format(value, "SHORT_DATE_FORMAT") if value else "—"


# ═══ Medicação ══════════════════════════════════════════════════════════════

_MEDICATION_ORDER = {"visible": 0, "finished": 1, "suspended": 2, "ended": 3}


@dataclass(frozen=True)
class MedicationRow:
    medication: Any
    state: str
    label: str
    badge: str
    times: str
    visible_in_app: bool


def _medication_state(medication: Any, today: date) -> str:
    if medication.is_active:
        ongoing = (
            medication.is_continuous
            or medication.end_date is None
            or medication.end_date >= today
        )
        return "visible" if ongoing else "finished"
    return "ended" if course_has_ended(medication, today=today) else "suspended"


def _medication_row(medication: Any, today: date) -> MedicationRow:
    state = _medication_state(medication, today)
    label, badge = {
        "visible": (_("Visível no app"), "success"),
        "finished": (_("Curso terminado"), "muted"),
        "suspended": (_("Suspenso"), "warning"),
        "ended": (_("Encerrado"), "muted"),
    }[state]
    return MedicationRow(
        medication=medication,
        state=state,
        label=label,
        badge=badge,
        times=", ".join(str(t)[:5] for t in medication.schedule_times),
        visible_in_app=state == "visible",
    )


def _local_naive(value: datetime, zone: ZoneInfo) -> datetime:
    """Wall-clock time in the patient's zone (naive, so templates do not shift it)."""
    return value.astimezone(zone).replace(tzinfo=None)


def _adherence(
    request: HttpRequest,
    staff: Staff,
    medications: list[Any],
    zone: ZoneInfo,
    today: date,
) -> dict[str, Any]:
    """Recent doses the patient logged in the app: read-only and consent-gated."""
    if not can_view_medication_adherence(
        user=staff.actor, clinic_id=staff.clinic_id, patient_profile_id=staff.patient_id
    ):
        return {"allowed": False}
    summary = selectors.medication_adherence_summary(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        start_date=today - timedelta(days=RECENT_DAYS),
        end_date=today,
    )
    logs = selectors.medication_logs_for_patient(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        since=timezone.now() - timedelta(days=RECENT_DAYS),
    )
    names = {item.pk: item.medication_name for item in medications}
    rows = [
        {
            "when": _local_naive(log.scheduled_time, zone),
            "medication": names.get(log.medication_id, ""),
            "label": DOSE_STATUS_LABELS.get(
                MedicationLogStatus(log.status), log.status
            ),
            "badge": {
                MedicationLogStatus.TAKEN: "success",
                MedicationLogStatus.LATE: "info",
                MedicationLogStatus.OMITTED: "warning",
            }.get(MedicationLogStatus(log.status), "muted"),
        }
        for log in reversed(logs)
    ][:MAX_RECENT_ROWS]
    record_audit_event(
        clinic_id=staff.clinic_id,
        actor_id=staff.actor.pk,
        action="view",
        resource_type="medication_adherence",
        resource_id=str(staff.patient_id),
        outcome="success",
        request_id=_request_uuid(),
        network_origin=None,
    )
    return {"allowed": True, "summary": summary, "rows": rows, "days": RECENT_DAYS}


@login_required
@private_no_store
@require_GET
def medication_list(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    today = _patient_today(staff.patient)
    medications = selectors.prescribed_medications_for_patient(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        include_inactive=True,
    )
    rows = sorted(
        (_medication_row(item, today) for item in medications),
        key=lambda row: _MEDICATION_ORDER[row.state],
    )
    return _page(
        request,
        "routines/medication_list.html",
        staff,
        section="medication",
        title=_("Medicação de %(name)s") % {"name": staff.patient.full_name},
        lead=_(
            "O que você registra aqui aparece no app do paciente assim que for "
            "publicado. A plataforma não sugere medicamento, dose nem horário."
        ),
        rows=rows,
        adherence=_adherence(
            request, staff, medications, _patient_zone(staff.patient), today
        ),
    )


def _medication_initial(medication: Any) -> dict[str, Any]:
    return {
        "medication_name": medication.medication_name,
        "presentation": medication.presentation,
        "prescribed_dose": medication.prescribed_dose,
        "route": medication.route,
        "schedule_times": ", ".join(str(t)[:5] for t in medication.schedule_times),
        "start_date": medication.start_date,
        "is_continuous": medication.is_continuous,
        "end_date": medication.end_date,
        "prescriber_name": medication.prescriber_name,
        "prescriber_registration": medication.prescriber_registration,
        "prescription_date": medication.prescription_date,
        "instructions": medication.instructions,
    }


def _medication_summary(data: dict[str, Any], zone_name: str) -> list[tuple[str, str]]:
    period = (
        _("A partir de %(start)s, uso contínuo")
        % {"start": _fmt_date(data["start_date"])}
        if data["is_continuous"]
        else _("De %(start)s a %(end)s")
        % {"start": _fmt_date(data["start_date"]), "end": _fmt_date(data["end_date"])}
    )
    return [
        (_("Medicamento"), data["medication_name"]),
        (_("Apresentação"), data["presentation"]),
        (_("Dose prescrita"), data["prescribed_dose"]),
        (
            _("Via de administração"),
            str(ROUTE_LABELS.get(data["route"], data["route"])),
        ),
        (
            _("Horários das doses (fuso %(zone)s)") % {"zone": zone_name},
            ", ".join(data["schedule_times"]),
        ),
        (_("Período"), period),
        (
            _("Prescritor"),
            f"{data['prescriber_name']} · {data['prescriber_registration']}",
        ),
        (_("Data da receita"), _fmt_date(data["prescription_date"])),
        (_("Orientações da receita"), data["instructions"] or "—"),
    ]


def _medication_flow(
    request: HttpRequest, staff: Staff, medication: Any | None
) -> HttpResponse:
    """Fill in, review, then publish: nothing is saved before the confirmation."""
    editing = medication is not None
    form = MedicationForm(
        _bound(request),
        initial=_medication_initial(medication)
        if editing
        else {"start_date": timezone.localdate()},
        timezone_name=staff.patient.timezone_name,
    )
    list_url = reverse("routines:medication_list", args=[staff.patient_id])
    title = _("Editar medicação") if editing else _("Registrar medicação")
    confirm_label = _(
        "Conferi os dados com a receita e confirmo que o paciente passará a vê-los "
        "no app agora."
    )
    confirm = ConfirmForm(None, label=confirm_label)
    review = False
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action", "review")
        if action == "publish":
            confirm = ConfirmForm(request.POST, label=confirm_label)
            review = True
            if confirm.is_valid():
                data = form.cleaned_data
                common: dict[str, Any] = {
                    "clinic_id": staff.clinic_id,
                    "patient_profile_id": staff.patient_id,
                    "medication_name": data["medication_name"],
                    "presentation": data["presentation"],
                    "prescribed_dose": data["prescribed_dose"],
                    "route": data["route"],
                    "schedule_times": data["schedule_times"],
                    "start_date": data["start_date"],
                    "end_date": data["end_date"],
                    "is_continuous": data["is_continuous"],
                    "prescriber_name": data["prescriber_name"],
                    "prescriber_registration": data["prescriber_registration"],
                    "prescription_date": data["prescription_date"],
                    "instructions": data["instructions"],
                    "actor_id": staff.actor.pk,
                    "request_id": _request_uuid(),
                }
                try:
                    if medication is not None:
                        update_prescribed_medication(
                            medication_id=medication.pk, **common
                        )
                    else:
                        register_prescribed_medication(**common)
                except ValidationError:
                    _service_failed(form)
                else:
                    messages.success(
                        request,
                        _("Medicação atualizada no app do paciente.")
                        if editing
                        else _("Medicação publicada no app do paciente."),
                    )
                    return redirect(list_url)
        elif action != "edit":
            review = True
    if review:
        return _page(
            request,
            "routines/confirm.html",
            staff,
            section="medication",
            title=_("Revisar antes de publicar"),
            lead=_("Confira cada campo com a receita. Nada foi salvo ainda."),
            crumbs=_crumbs(staff, "medication", (title, None)),
            form=confirm,
            hidden_form=form,
            back_action=True,
            submit_label=_("Publicar no app do paciente"),
            cancel_url=list_url,
            notice=_(
                "Ao publicar, o paciente passa a ver o medicamento, a dose e os "
                "horários no app e poderá registrar cada dose. A plataforma não "
                "sugere medicamento, dose nem horário: o conteúdo é o da receita "
                "que você informou."
            ),
            rows=_medication_summary(form.cleaned_data, staff.patient.timezone_name),
        )
    return _form_page(
        request,
        staff,
        section="medication",
        title=title,
        form=form,
        submit_label=_("Revisar antes de publicar"),
        cancel_url=list_url,
        lead=_(
            "Registre a receita externa do paciente. Você vai revisar tudo antes de "
            "publicar."
        ),
        notice=_(
            "O paciente verá o nome, a dose, os horários e as orientações no app. "
            "Esta tela não sugere nem calcula doses."
        ),
        crumbs=_crumbs(staff, "medication", (title, None)),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def medication_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    return _medication_flow(request, staff, None)


def _medication_or_denied(staff: Staff, medication_id: UUID) -> Any:
    medication = selectors.medication_for_staff(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        medication_id=medication_id,
    )
    if medication is None:
        raise PermissionDenied
    return medication


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def medication_edit(
    request: HttpRequest, patient_id: UUID, medication_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    medication = _medication_or_denied(staff, medication_id)
    list_url = reverse("routines:medication_list", args=[staff.patient_id])
    state = _medication_state(medication, _patient_today(staff.patient))
    if state == "ended":
        return _refuse(
            request,
            _("Este tratamento foi encerrado. Registre uma nova prescrição."),
            list_url,
        )
    return _medication_flow(request, staff, medication)


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def medication_stop(
    request: HttpRequest, patient_id: UUID, medication_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    medication = _medication_or_denied(staff, medication_id)
    list_url = reverse("routines:medication_list", args=[staff.patient_id])
    state = _medication_state(medication, _patient_today(staff.patient))
    if state == "ended":
        return _refuse(request, _("Este tratamento já foi encerrado."), list_url)
    form = MedicationStopForm(
        _bound(request),
        label=_("Entendi que o medicamento deixa de aparecer no app agora."),
        allow_suspend=state != "suspended",
    )

    def perform() -> None:
        common: dict[str, Any] = {
            "clinic_id": staff.clinic_id,
            "patient_profile_id": staff.patient_id,
            "medication_id": medication.pk,
            "actor_id": staff.actor.pk,
            "request_id": _request_uuid(),
        }
        if form.cleaned_data["kind"] == "end":
            end_prescribed_medication(**common)
        else:
            suspend_prescribed_medication(**common)

    return _confirm_page(
        request,
        staff,
        section="medication",
        title=_("Suspender ou encerrar %(name)s")
        % {"name": medication.medication_name},
        lead=_("Registros de dose já feitos pelo paciente são mantidos no histórico."),
        notice=_(
            "O medicamento sai do app do paciente assim que você confirmar. "
            "Avise o paciente: o app não envia aviso sobre a mudança."
        ),
        form=form,
        submit_label=_("Confirmar"),
        cancel_url=list_url,
        perform=perform,
        success=_("Medicação retirada do app do paciente."),
        next_url=list_url,
        danger=True,
        crumbs=_crumbs(staff, "medication", (medication.medication_name, None)),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def medication_resume(
    request: HttpRequest, patient_id: UUID, medication_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    medication = _medication_or_denied(staff, medication_id)
    list_url = reverse("routines:medication_list", args=[staff.patient_id])
    if _medication_state(medication, _patient_today(staff.patient)) != "suspended":
        return _refuse(
            request, _("Só um medicamento suspenso pode ser retomado."), list_url
        )
    form = ConfirmForm(
        _bound(request),
        label=_("Entendi que o medicamento volta a aparecer no app agora."),
    )

    def perform() -> None:
        resume_prescribed_medication(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            medication_id=medication.pk,
            actor_id=staff.actor.pk,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="medication",
        title=_("Retomar %(name)s") % {"name": medication.medication_name},
        notice=_(
            "O paciente volta a ver este medicamento e a registrar as doses no app. "
            "Confira se a receita continua valendo."
        ),
        form=form,
        submit_label=_("Retomar medicação"),
        cancel_url=list_url,
        perform=perform,
        success=_("Medicação publicada de novo no app do paciente."),
        next_url=list_url,
        crumbs=_crumbs(staff, "medication", (medication.medication_name, None)),
    )


# ═══ Plano de cuidado ═══════════════════════════════════════════════════════


def _plan_or_denied(staff: Staff, care_plan_id: UUID) -> CarePlan:
    plan = selectors.care_plan_for_staff(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        care_plan_id=care_plan_id,
    )
    if plan is None:
        raise PermissionDenied
    return plan


def _plan_status(plan: CarePlan) -> str:
    return str(PLAN_STATUS_LABELS[CarePlanStatus(plan.status)])


def _plan_badge(plan: CarePlan) -> str:
    return PLAN_STATUS_BADGES[CarePlanStatus(plan.status)]


def _latest_reply(plan: CarePlan) -> Any | None:
    """The patient's newest reply to the plan's current version, if any."""
    replies = [
        item
        for item in plan.patient_responses.all()
        if item.plan_version_reviewed == plan.version
    ]
    return max(replies, key=lambda item: item.responded_at, default=None)


def _response_view(response: Any, plan: CarePlan) -> dict[str, Any]:
    choice = PatientResponseChoice(response.decision)
    return {
        "label": RESPONSE_LABELS[choice],
        "badge": RESPONSE_BADGES[choice],
        "notes": response.patient_notes,
        "responded_at": response.responded_at,
        "version": response.plan_version_reviewed,
        "is_current": response.plan_version_reviewed == plan.version,
        "decision": response.decision,
    }


def _plan_content(staff: Staff, plan: CarePlan) -> dict[str, Any]:
    names = professional_display_names(
        clinic_id=staff.clinic_id, user_ids={plan.prescribing_professional_id}
    )
    actions = sorted(plan.actions.all(), key=lambda a: (a.order, a.created_at))
    responses = [
        _response_view(item, plan)
        for item in sorted(
            plan.patient_responses.all(), key=lambda r: r.responded_at, reverse=True
        )
    ]
    current = next((item for item in responses if item["is_current"]), None)
    return {
        "plan": plan,
        "status_label": _plan_status(plan),
        "status_badge": _plan_badge(plan),
        "prescriber": names.get(plan.prescribing_professional_id, _("Profissional")),
        "actions": actions,
        "responses": responses,
        "current_response": current,
        "visibility": PLAN_VISIBILITY[CarePlanStatus(plan.status)],
    }


@login_required
@private_no_store
@require_GET
def care_plan_list(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    plans = selectors.care_plans_for_patient(
        clinic_id=staff.clinic_id, patient_profile_id=staff.patient_id
    )
    names = professional_display_names(
        clinic_id=staff.clinic_id,
        user_ids={plan.prescribing_professional_id for plan in plans},
    )
    rows = []
    for plan in plans:
        latest = _latest_reply(plan)
        rows.append(
            {
                "plan": plan,
                "status_label": _plan_status(plan),
                "status_badge": _plan_badge(plan),
                "prescriber": names.get(
                    plan.prescribing_professional_id, _("Profissional")
                ),
                "response": _response_view(latest, plan) if latest else None,
            }
        )
    return _page(
        request,
        "routines/care_plan_list.html",
        staff,
        section="plans",
        title=_("Planos de cuidado de %(name)s") % {"name": staff.patient.full_name},
        lead=_(
            "O paciente só vê um plano depois que o profissional o assina. Rascunhos "
            "e planos aguardando assinatura nunca aparecem no app."
        ),
        rows=rows,
    )


def _plan_initial(plan: CarePlan | None) -> dict[str, Any]:
    if plan is None:
        return {"valid_from": timezone.localdate()}
    return {
        "title": plan.title,
        "objective": plan.objective,
        "clinical_rationale": plan.clinical_rationale,
        "contraindications": plan.contraindications,
        "valid_from": plan.valid_from,
        "valid_until": plan.valid_until,
    }


def _care_plan_flow(
    request: HttpRequest, staff: Staff, plan: CarePlan | None
) -> HttpResponse:
    editing = plan is not None
    formset_class = care_plan_action_formset(extra=3 if editing else 4)
    initial_actions = (
        [
            {
                "description": action.action_description,
                "target_frequency": action.target_frequency,
                "guidance": action.guidance,
                "is_mandatory": action.is_mandatory,
            }
            for action in sorted(
                plan.actions.all(), key=lambda a: (a.order, a.created_at)
            )
        ]
        if plan is not None
        else []
    )
    form = CarePlanForm(_bound(request), initial=_plan_initial(plan))
    formset = formset_class(_bound(request), initial=initial_actions)
    list_url = reverse("routines:care_plan_list", args=[staff.patient_id])
    if request.method == "POST":
        form_ok = form.is_valid()
        actions_ok = formset.is_valid()
        if form_ok and actions_ok:
            data = form.cleaned_data
            common: dict[str, Any] = {
                "clinic_id": staff.clinic_id,
                "professional_user": staff.actor,
                "title": data["title"],
                "objective": data["objective"],
                "clinical_rationale": data["clinical_rationale"],
                "contraindications": data["contraindications"],
                "valid_from": data["valid_from"],
                "valid_until": data["valid_until"],
                "actions_data": formset.actions_data(),
                "request_id": _request_uuid(),
            }
            try:
                if plan is None:
                    saved = propose_care_plan(
                        patient_profile_id=staff.patient_id, **common
                    )
                else:
                    saved = update_care_plan_draft(
                        patient_profile_id=staff.patient_id,
                        care_plan_id=plan.pk,
                        **common,
                    )
            except ValidationError:
                _service_failed(form)
            else:
                messages.success(
                    request, _("Rascunho salvo. O paciente ainda não vê este plano.")
                )
                return redirect(
                    "routines:care_plan_detail",
                    patient_id=staff.patient_id,
                    care_plan_id=saved.pk,
                )
    title = _("Editar rascunho do plano") if editing else _("Propor plano de cuidado")
    return _page(
        request,
        "routines/care_plan_form.html",
        staff,
        section="plans",
        title=title,
        lead=_(
            "O plano nasce como rascunho: o paciente só o vê depois do envio para "
            "assinatura e da assinatura do profissional."
        ),
        crumbs=_crumbs(staff, "plans", (title, None)),
        form=form,
        formset=formset,
        cancel_url=(
            reverse(
                "routines:care_plan_detail",
                args=[staff.patient_id, plan.pk],
            )
            if plan is not None
            else list_url
        ),
        submit_label=_("Salvar rascunho"),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    return _care_plan_flow(request, staff, None)


def _author_or_denied(staff: Staff, plan: CarePlan) -> None:
    if not can_author_care_plan(
        user=staff.actor,
        clinic_id=staff.clinic_id,
        prescribing_professional_id=plan.prescribing_professional_id,
    ):
        raise PermissionDenied


def _detail_url(staff: Staff, plan: CarePlan) -> str:
    return reverse("routines:care_plan_detail", args=[staff.patient_id, plan.pk])


@login_required
@private_no_store
@require_GET
def care_plan_detail(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    content = _plan_content(staff, plan)
    status = CarePlanStatus(plan.status)
    is_author = can_author_care_plan(
        user=staff.actor,
        clinic_id=staff.clinic_id,
        prescribing_professional_id=plan.prescribing_professional_id,
    )
    latest = content["responses"][0] if content["responses"] else None
    return _page(
        request,
        "routines/care_plan_detail.html",
        staff,
        section="plans",
        title=plan.title,
        crumbs=_crumbs(staff, "plans", (plan.title, None)),
        can_edit=is_author and status == CarePlanStatus.DRAFT,
        can_submit=is_author and status == CarePlanStatus.DRAFT,
        can_sign=is_author and status == CarePlanStatus.PENDING_SIGNATURE,
        can_reopen=is_author and status == CarePlanStatus.PENDING_SIGNATURE,
        can_pause=status == CarePlanStatus.ACTIVE,
        can_resume=status == CarePlanStatus.PAUSED,
        can_close=status in {CarePlanStatus.ACTIVE, CarePlanStatus.PAUSED},
        refused=status == CarePlanStatus.REVOKED
        and latest is not None
        and latest["decision"] == PatientResponseChoice.REFUSED,
        **content,
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_edit(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    _author_or_denied(staff, plan)
    if plan.status != CarePlanStatus.DRAFT:
        return _refuse(
            request, _("Só um rascunho pode ser editado."), _detail_url(staff, plan)
        )
    return _care_plan_flow(request, staff, plan)


def _plan_crumbs(staff: Staff, plan: CarePlan, label: str) -> list[Crumb]:
    return _crumbs(
        staff, "plans", (plan.title, _detail_url(staff, plan)), (label, None)
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_submit(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    _author_or_denied(staff, plan)
    detail_url = _detail_url(staff, plan)
    if plan.status != CarePlanStatus.DRAFT:
        return _refuse(
            request, _("Só um rascunho pode ser enviado para assinatura."), detail_url
        )
    form = ConfirmForm(
        _bound(request),
        label=_("Revisei o plano e quero enviá-lo para assinatura."),
    )

    def perform() -> None:
        submit_care_plan_for_signature(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            care_plan_id=plan.pk,
            professional_user=staff.actor,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Enviar para assinatura"),
        lead=plan.title,
        notice=_(
            "O plano deixa de ser editável e aguarda a sua assinatura. O paciente "
            "ainda não vê nada: ele só aparece no app depois que você assinar."
        ),
        form=form,
        submit_label=_("Enviar para assinatura"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano aguardando assinatura. O paciente ainda não o vê."),
        next_url=detail_url,
        crumbs=_plan_crumbs(staff, plan, _("Enviar para assinatura")),
        content_template="routines/partials/plan_content.html",
        **_plan_content(staff, plan),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_reopen(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    _author_or_denied(staff, plan)
    detail_url = _detail_url(staff, plan)
    if plan.status != CarePlanStatus.PENDING_SIGNATURE:
        return _refuse(
            request,
            _("Só um plano aguardando assinatura volta a rascunho."),
            detail_url,
        )
    form = ConfirmForm(_bound(request), label=_("Quero devolver o plano para edição."))

    def perform() -> None:
        reopen_care_plan_draft(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            care_plan_id=plan.pk,
            professional_user=staff.actor,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Voltar para rascunho"),
        lead=plan.title,
        notice=_("O plano volta a ser editável. O paciente continua sem vê-lo."),
        form=form,
        submit_label=_("Voltar para rascunho"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano devolvido para rascunho."),
        next_url=detail_url,
        crumbs=_plan_crumbs(staff, plan, _("Voltar para rascunho")),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_sign(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    _author_or_denied(staff, plan)
    detail_url = _detail_url(staff, plan)
    if plan.status != CarePlanStatus.PENDING_SIGNATURE:
        return _refuse(
            request, _("Este plano não está aguardando assinatura."), detail_url
        )
    others = [
        item
        for item in selectors.care_plans_for_patient(
            clinic_id=staff.clinic_id, patient_profile_id=staff.patient_id
        )
        if item.pk != plan.pk
        and item.status in {CarePlanStatus.ACTIVE, CarePlanStatus.PAUSED}
    ]
    if others:
        return _refuse(
            request,
            _("O paciente já tem um plano em vigor. Encerre-o antes de assinar outro."),
            detail_url,
        )
    form = ConfirmForm(
        _bound(request),
        label=_(
            "Revisei o plano, assino digitalmente e confirmo que o paciente passará "
            "a vê-lo no app agora."
        ),
    )

    def perform() -> None:
        sign_care_plan(
            clinic_id=staff.clinic_id,
            care_plan_id=plan.pk,
            signing_professional=staff.actor,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Assinar e publicar no app"),
        lead=plan.title,
        notice=_(
            "Ao assinar, o plano aparece imediatamente no app do paciente, que "
            "poderá aceitar, pausar, recusar ou pedir revisão. Recusar encerra o "
            "plano. A justificativa clínica não aparece para o paciente."
        ),
        form=form,
        submit_label=_("Assinar e publicar"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano assinado e publicado no app do paciente."),
        next_url=detail_url,
        crumbs=_plan_crumbs(staff, plan, _("Assinar e publicar")),
        content_template="routines/partials/plan_content.html",
        **_plan_content(staff, plan),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_pause(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    detail_url = _detail_url(staff, plan)
    if plan.status != CarePlanStatus.ACTIVE:
        return _refuse(request, _("Só um plano ativo pode ser pausado."), detail_url)
    form = ConfirmForm(
        _bound(request),
        label=_("Entendi que o plano aparece como pausado no app do paciente."),
    )

    def perform() -> None:
        pause_care_plan(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            care_plan_id=plan.pk,
            professional_user=staff.actor,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Pausar plano"),
        lead=plan.title,
        notice=_(
            "O plano continua visível no app, marcado como pausado. Combine a pausa "
            "com o paciente."
        ),
        form=form,
        submit_label=_("Pausar plano"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano pausado."),
        next_url=detail_url,
        crumbs=_plan_crumbs(staff, plan, _("Pausar")),
    )


def _patient_paused(plan: CarePlan) -> bool:
    latest = _latest_reply(plan)
    return latest is not None and latest.decision == PatientResponseChoice.PAUSED


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_resume(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    detail_url = _detail_url(staff, plan)
    if plan.status != CarePlanStatus.PAUSED:
        return _refuse(request, _("Só um plano pausado pode ser retomado."), detail_url)
    paused_by_patient = _patient_paused(plan)
    form = ConfirmForm(
        _bound(request),
        label=(
            _("Combinei a retomada com o paciente, que pausou o plano.")
            if paused_by_patient
            else _("Entendi que o plano volta a aparecer como ativo no app.")
        ),
    )

    def perform() -> None:
        resume_care_plan(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            care_plan_id=plan.pk,
            professional_user=staff.actor,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Retomar plano"),
        lead=plan.title,
        notice=(
            _(
                "O paciente pausou este plano. Só o retome depois de combinar com "
                "ele: o app mostrará o plano como ativo de novo."
            )
            if paused_by_patient
            else _("O plano volta a aparecer como ativo no app do paciente.")
        ),
        form=form,
        submit_label=_("Retomar plano"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano retomado."),
        next_url=detail_url,
        crumbs=_plan_crumbs(staff, plan, _("Retomar")),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def care_plan_close(
    request: HttpRequest, patient_id: UUID, care_plan_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    plan = _plan_or_denied(staff, care_plan_id)
    detail_url = _detail_url(staff, plan)
    if plan.status not in {CarePlanStatus.ACTIVE, CarePlanStatus.PAUSED}:
        return _refuse(
            request, _("Só um plano ativo ou pausado pode ser encerrado."), detail_url
        )
    form = CarePlanCloseForm(
        _bound(request),
        label=_(
            "Entendi que o plano encerrado não aceita novas respostas do paciente."
        ),
    )

    def perform() -> None:
        close_care_plan(
            clinic_id=staff.clinic_id,
            patient_profile_id=staff.patient_id,
            care_plan_id=plan.pk,
            professional_user=staff.actor,
            outcome=form.cleaned_data["outcome"],
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="plans",
        title=_("Encerrar plano"),
        lead=plan.title,
        notice=_(
            "O plano continua visível no app, mas encerrado: o paciente não poderá "
            "mais responder. Para propor mudanças, crie um novo plano."
        ),
        form=form,
        submit_label=_("Encerrar plano"),
        cancel_url=detail_url,
        perform=perform,
        success=_("Plano encerrado."),
        next_url=detail_url,
        danger=True,
        crumbs=_plan_crumbs(staff, plan, _("Encerrar")),
    )


# ═══ Hábitos ════════════════════════════════════════════════════════════════


def _habit_or_denied(staff: Staff, habit_id: UUID) -> Any:
    habit = selectors.habit_for_staff(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        habit_id=habit_id,
    )
    if habit is None:
        raise PermissionDenied
    return habit


def _active_days(frequency: str, selected: list[str]) -> list[int]:
    if frequency == HabitFrequency.WEEKDAYS:
        return [0, 1, 2, 3, 4]
    if frequency == HabitFrequency.SPECIFIC_DAYS:
        return sorted({int(day) for day in selected})
    return list(range(7))


def _habit_when(habit: Any) -> str:
    window = str(
        WINDOW_LABELS.get(TimeOfDayWindow(habit.time_window), habit.time_window)
    )
    if habit.target_time:
        return f"{window} · {habit.target_time.strftime('%H:%M')}"
    return window


def _habit_frequency(habit: Any) -> str:
    label = str(FREQUENCY_LABELS.get(HabitFrequency(habit.frequency), habit.frequency))
    if habit.frequency == HabitFrequency.SPECIFIC_DAYS:
        days = ", ".join(
            str(WEEKDAY_SHORT_LABELS[d]) for d in sorted(habit.active_days)
        )
        return f"{label}: {days}"
    return label


@login_required
@private_no_store
@require_GET
def habit_list(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    today = _patient_today(staff.patient)
    habits = selectors.habits_for_staff(
        clinic_id=staff.clinic_id, patient_profile_id=staff.patient_id
    )
    checks = selectors.habit_checks_for_patient(
        clinic_id=staff.clinic_id,
        patient_profile_id=staff.patient_id,
        start_date=today - timedelta(days=RECENT_DAYS - 1),
        end_date=today,
    )
    counts: dict[UUID, Counter[str]] = {}
    for habit_id, _day, status in checks:
        counts.setdefault(habit_id, Counter())[status] += 1
    titles = {habit.pk: habit.title for habit in habits}

    def row(habit: Any) -> dict[str, Any]:
        done = counts.get(habit.pk, Counter())
        return {
            "habit": habit,
            "frequency": _habit_frequency(habit),
            "when": _habit_when(habit),
            "status_label": HABIT_STATUS_LABELS[HabitStatus(habit.status)],
            "summary": [
                (CHECKIN_LABELS[key], done.get(key.value, 0)) for key in CHECKIN_LABELS
            ],
            "total": sum(done.values()),
        }

    recent: list[dict[str, Any]] = []
    for habit_id, day, status in sorted(checks, key=lambda c: c[1], reverse=True):
        key = CheckInStatus(status)
        recent.append(
            {
                "date": day,
                "title": titles.get(habit_id, ""),
                "label": CHECKIN_LABELS[key],
                "badge": CHECKIN_BADGES[key],
            }
        )
    recent = recent[: MAX_RECENT_ROWS * 2]
    return _page(
        request,
        "routines/habit_list.html",
        staff,
        section="habits",
        title=_("Hábitos de %(name)s") % {"name": staff.patient.full_name},
        lead=_(
            "O paciente vê os hábitos ativos e pausados no app e registra por lá. "
            "Os registros abaixo são só para leitura."
        ),
        current=[row(h) for h in habits if h.status != HabitStatus.ARCHIVED],
        archived=[row(h) for h in habits if h.status == HabitStatus.ARCHIVED],
        recent=recent,
        recent_days=RECENT_DAYS,
    )


def _habit_initial(habit: Any) -> dict[str, Any]:
    return {
        "title": habit.title,
        "description": habit.description,
        "frequency": habit.frequency,
        "active_days": [str(day) for day in habit.active_days],
        "time_window": habit.time_window,
        "target_time": habit.target_time,
        "target_duration_minutes": habit.target_duration_minutes or None,
    }


def _habit_flow(request: HttpRequest, staff: Staff, habit: Any | None) -> HttpResponse:
    editing = habit is not None
    form = HabitForm(
        _bound(request),
        initial=_habit_initial(habit)
        if editing
        else {
            "frequency": HabitFrequency.DAILY,
            "time_window": TimeOfDayWindow.ANY_TIME,
        },
    )
    list_url = reverse("routines:habit_list", args=[staff.patient_id])
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        days = _active_days(data["frequency"], data["active_days"])
        duration = data["target_duration_minutes"] or 0
        try:
            if habit is not None:
                update_habit(
                    clinic_id=staff.clinic_id,
                    habit_id=habit.pk,
                    title=data["title"],
                    description=data["description"],
                    frequency=data["frequency"],
                    active_days=days,
                    target_duration_minutes=duration,
                    time_window=data["time_window"],
                    target_time=data["target_time"],
                    clear_target_time=data["target_time"] is None,
                    actor_id=staff.actor.pk,
                    request_id=_request_uuid(),
                )
            else:
                create_habit(
                    clinic_id=staff.clinic_id,
                    patient_profile_id=staff.patient_id,
                    title=data["title"],
                    description=data["description"],
                    frequency=data["frequency"],
                    active_days=days,
                    time_window=data["time_window"],
                    target_time=data["target_time"],
                    target_duration_minutes=duration,
                    timezone_name=str(staff.patient.timezone_name),
                    actor_id=staff.actor.pk,
                    request_id=_request_uuid(),
                )
        except ValidationError:
            _service_failed(form)
        else:
            messages.success(
                request,
                _("Hábito atualizado. O paciente vê a mudança no app.")
                if editing
                else _("Hábito criado. O paciente já o vê no app."),
            )
            return redirect(list_url)
    title = _("Editar hábito") if editing else _("Novo hábito")
    return _form_page(
        request,
        staff,
        section="habits",
        title=title,
        form=form,
        submit_label=_("Salvar hábito"),
        cancel_url=list_url,
        lead=_("Horários seguem o fuso do paciente (%(zone)s).")
        % {"zone": staff.patient.timezone_name},
        notice=_(
            "O paciente verá este hábito no app assim que você salvar. Os hábitos "
            "são metas flexíveis: o app não cobra nem mede sequências."
        ),
        crumbs=_crumbs(staff, "habits", (title, None)),
    )


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def habit_create(request: HttpRequest, patient_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    return _habit_flow(request, staff, None)


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def habit_edit(request: HttpRequest, patient_id: UUID, habit_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    habit = _habit_or_denied(staff, habit_id)
    if habit.status == HabitStatus.ARCHIVED:
        return _refuse(
            request,
            _("Um hábito arquivado não pode ser editado."),
            reverse("routines:habit_list", args=[staff.patient_id]),
        )
    return _habit_flow(request, staff, habit)


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def habit_pause(request: HttpRequest, patient_id: UUID, habit_id: UUID) -> HttpResponse:
    staff = _staff(request, patient_id)
    habit = _habit_or_denied(staff, habit_id)
    list_url = reverse("routines:habit_list", args=[staff.patient_id])
    if habit.status != HabitStatus.ACTIVE:
        return _refuse(request, _("Só um hábito ativo pode ser pausado."), list_url)
    form = HabitPauseForm(_bound(request))
    if request.method == "POST" and form.is_valid():
        try:
            pause_habit(
                clinic_id=staff.clinic_id,
                habit_id=habit.pk,
                paused_until=form.cleaned_data["paused_until"],
                actor_id=staff.actor.pk,
                request_id=_request_uuid(),
            )
        except ValidationError:
            _service_failed(form)
        else:
            messages.success(request, _("Hábito pausado."))
            return redirect(list_url)
    return _form_page(
        request,
        staff,
        section="habits",
        title=_("Pausar %(name)s") % {"name": habit.title},
        form=form,
        submit_label=_("Pausar hábito"),
        cancel_url=list_url,
        notice=_(
            "O hábito continua no app, marcado como pausado, e o paciente não "
            "consegue registrá-lo até que seja retomado."
        ),
        crumbs=_crumbs(staff, "habits", (habit.title, None)),
    )


@login_required
@private_no_store
@require_POST
def habit_resume(
    request: HttpRequest, patient_id: UUID, habit_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    habit = _habit_or_denied(staff, habit_id)
    list_url = reverse("routines:habit_list", args=[staff.patient_id])
    if habit.status != HabitStatus.PAUSED:
        return _refuse(request, _("Só um hábito pausado pode ser retomado."), list_url)
    try:
        resume_habit(
            clinic_id=staff.clinic_id,
            habit_id=habit.pk,
            actor_id=staff.actor.pk,
            request_id=_request_uuid(),
        )
    except ValidationError:
        return _refuse(request, _("O hábito não pôde ser retomado."), list_url)
    messages.success(request, _("Hábito retomado. O paciente já pode registrá-lo."))
    return redirect(list_url)


@login_required
@private_no_store
@require_http_methods(["GET", "POST"])
def habit_archive(
    request: HttpRequest, patient_id: UUID, habit_id: UUID
) -> HttpResponse:
    staff = _staff(request, patient_id)
    habit = _habit_or_denied(staff, habit_id)
    list_url = reverse("routines:habit_list", args=[staff.patient_id])
    if habit.status == HabitStatus.ARCHIVED:
        return _refuse(request, _("Este hábito já está arquivado."), list_url)
    form = ConfirmForm(
        _bound(request),
        label=_("Entendi que o hábito deixa de aparecer no app do paciente."),
    )

    def perform() -> None:
        archive_habit(
            clinic_id=staff.clinic_id,
            habit_id=habit.pk,
            actor_id=staff.actor.pk,
            request_id=_request_uuid(),
        )

    return _confirm_page(
        request,
        staff,
        section="habits",
        title=_("Arquivar %(name)s") % {"name": habit.title},
        notice=_(
            "O hábito sai do app e não gera novos dias. Os registros já feitos ficam "
            "guardados."
        ),
        form=form,
        submit_label=_("Arquivar hábito"),
        cancel_url=list_url,
        perform=perform,
        success=_("Hábito arquivado."),
        next_url=list_url,
        danger=True,
        crumbs=_crumbs(staff, "habits", (habit.title, None)),
    )
