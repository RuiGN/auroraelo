"""Conteúdo pessoal que o próprio paciente escreve no app (`/api/v1/mobile/`).

Meta de recuperação, plano de prevenção de recaída, plano de apoio urgente (com as
pessoas de confiança) e as ações do modo de pouca energia. O conteúdo é do paciente:
só ele lê e só ele altera, e nada aqui é lido pela equipe por esta API.

Regras que valem para todas as rotas:

- **Posse.** Cada rota resolve o objeto restrito ao perfil do paciente da sessão antes
  de gravar; id de outra pessoa responde `404` e nada é gravado. Os serviços de
  domínio autorizam só por clínica, então a posse é daqui.
- **Clínica e paciente vêm da sessão.** O cliente nunca os informa.
- **Cobrança bloqueada responde `402`** (diferente de `/mobile/help/`, que continua
  aberto): escrever não é ajuda urgente.
- **Auditoria sem conteúdo.** Cada gravação deixa um evento com ator, recurso e origem
  da rede, nunca o texto escrito nem o telefone de ninguém.
- **Telefone de terceiro é dado pessoal.** Nunca vai para log nem para mensagem de erro;
  só volta ao próprio paciente. Registrar, alterar ou ler o plano **não contata
  ninguém**: a ligação só acontece quando o paciente toca no discador, no aparelho.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Field, Router, Schema, Status

from audit.services import record_audit_event
from goals.low_energy_services import configure_low_energy_actions
from support_network.selectors import (
    urgent_contact_for_patient,
    urgent_support_plan_for_patient,
)
from support_network.urgent_services import (
    UrgentContactLimitError,
    create_or_update_urgent_plan,
    deactivate_urgent_contact,
    register_urgent_contact,
    update_urgent_contact,
)
from wellness.models import RelapsePlanSectionType
from wellness.relapse_services import (
    create_or_update_relapse_plan,
    remove_relapse_plan_section,
)
from wellness.selectors import relapse_plan_for_patient
from wellness.sobriety_services import (
    ActiveSobrietyGoalExistsError,
    setup_sobriety_goal,
)

from .mobile_care_api import LowEnergyOut, low_energy_out
from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    network_origin,
    patient_zone,
    problem,
    request_id,
)
from .mobile_recovery_api import (
    RelapsePlanEnvelope,
    SobrietyOut,
    UrgentContactOut,
    UrgentPlanOut,
    relapse_plan_envelope,
    sobriety_out,
    urgent_contact_out,
    urgent_plan_out,
)
from .mobile_recovery_api import router as recovery_router

router = Router(tags=["Mobile · Conteúdo pessoal"], auth=PatientBearerAuth())

# Limites do app. Os de texto curto respeitam o tamanho das colunas do domínio
# (meta e título de seção: 128), para o banco nunca recusar o que a API aceitou.
MAX_FOCUS = 128
MAX_MOTIVATIONS = 2000
MAX_PLAN_TITLE = 200
MAX_SECTION_TITLE = 128
MAX_SECTION_CONTENT = 4000
MAX_INSTRUCTIONS = 2000
MAX_STRATEGIES = 10
MAX_STRATEGY = 200
MAX_CONTACT_NAME = 120
MAX_CONTACT_RELATIONSHIP = 80
MAX_CONTACT_MESSAGE = 500
MAX_ACTIVE_CONTACTS = 5
MAX_LOW_ENERGY_ACTIONS = 3
MAX_LOW_ENERGY_ACTION = 120
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 20
MAX_PHONE_INPUT = 40
MIN_REFERENCE_DATE = date(1900, 1, 1)

DEFAULT_RELAPSE_PLAN_TITLE = "Plano de Prevenção de Recaída"
_SECTION_ORDER = {
    kind.value: index for index, kind in enumerate(RelapsePlanSectionType)
}
_SECTION_LABELS = {kind.value: str(kind.label) for kind in RelapsePlanSectionType}
_PHONE_SHAPE = re.compile(r"\+?[0-9() \-]+")


# ── Meta de recuperação ─────────────────────────────────────────────────────


class GoalIn(Schema):
    goal_type: Literal["abstinence", "reduction", "moderation"]
    focus: str = Field(min_length=1, max_length=MAX_FOCUS)
    reference_date: date
    motivations: str = Field(default="", max_length=MAX_MOTIVATIONS)
    hide_counter: bool = False


@router.post(
    "/recovery/goal/",
    response={201: SobrietyOut, 409: MobileErrorOut, 422: MobileErrorOut},
)
def create_goal(request: HttpRequest, payload: GoalIn) -> Any:
    """Cria a meta de recuperação do paciente. Sempre privada; o cliente não escolhe.

    A data de referência é o dia em que a contagem começa: hoje ou antes, no fuso do
    paciente. Só pode haver uma meta ativa; para recomeçar, `POST /recovery/restart/`.
    """
    context = mobile_context(request)
    zone = patient_zone(context.patient_profile.timezone_name)
    today = timezone.now().astimezone(zone).date()
    if not MIN_REFERENCE_DATE <= payload.reference_date <= today:
        return problem(422, "A data de referência não pode ser futura.", "invalid_date")
    try:
        goal = setup_sobriety_goal(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
            goal_type=payload.goal_type,
            substance_or_behavior=payload.focus,
            reference_date=payload.reference_date,
            motivations=payload.motivations,
            hide_counter=payload.hide_counter,
            is_private=True,
            one_active_goal_only=True,
            actor_id=context.user.pk,
            request_id=request_id(request),
            network_origin=network_origin(request),
        )
    except ActiveSobrietyGoalExistsError:
        return problem(
            409, "Já existe uma meta de recuperação ativa.", "already_exists"
        )
    except ValidationError:
        return problem(422, "Informe o foco da meta.", "invalid_focus")
    return Status(201, sobriety_out(goal))


# ── Plano de prevenção de recaída ───────────────────────────────────────────


class RelapseSectionIn(Schema):
    section_type: str = Field(max_length=64)
    title: str = Field(default="", max_length=MAX_SECTION_TITLE)
    content: str = Field(default="", max_length=MAX_SECTION_CONTENT)


class RelapsePlanIn(Schema):
    title: str = Field(default="", max_length=MAX_PLAN_TITLE)
    sections: list[RelapseSectionIn] = Field(
        default_factory=list, max_length=len(_SECTION_ORDER)
    )


# O GET deste caminho vive no roteador de recuperação. O Ninja gera um padrão de URL
# por roteador e o Django usa o primeiro que casa, então o PUT precisa estar no mesmo
# roteador do GET; em outro, ele responderia 405.
@recovery_router.put(
    "/relapse-plan/",
    response={200: RelapsePlanEnvelope, 422: MobileErrorOut},
)
def save_relapse_plan(request: HttpRequest, payload: RelapsePlanIn) -> Any:
    """Grava o plano do próprio paciente; cada gravação gera uma nova versão.

    `sections` traz as seções a gravar (no máximo uma por tipo; seção com texto vazio
    é ignorada, e as que não vierem ficam como estão). Para apagar uma seção use
    `DELETE /relapse-plan/sections/{tipo}/`. A resposta é o plano completo.
    """
    context = mobile_context(request)
    existing = relapse_plan_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    saved_titles = (
        {item.section_type: item.title for item in existing.sections.all()}
        if existing is not None
        else {}
    )
    seen: set[str] = set()
    sections: list[dict[str, Any]] = []
    for item in payload.sections:
        if item.section_type not in _SECTION_ORDER:
            return problem(422, "Tipo de seção desconhecido.", "invalid_section_type")
        if item.section_type in seen:
            return problem(
                422, "Há mais de uma seção do mesmo tipo.", "duplicate_section"
            )
        seen.add(item.section_type)
        content = item.content.strip()
        if not content:
            continue
        sections.append(
            {
                "section_type": item.section_type,
                "title": item.title.strip()
                or saved_titles.get(item.section_type)
                or _SECTION_LABELS[item.section_type],
                "content": content,
                "order": _SECTION_ORDER[item.section_type],
            }
        )
    title = payload.title.strip() or (
        existing.title if existing is not None else DEFAULT_RELAPSE_PLAN_TITLE
    )
    create_or_update_relapse_plan(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        title=title,
        sections_data=sections,
        actor_id=context.user.pk,
        request_id=request_id(request),
        network_origin=network_origin(request),
    )
    return Status(
        200,
        relapse_plan_envelope(
            relapse_plan_for_patient(
                clinic_id=context.clinic_id,
                patient_profile_id=context.patient_profile_id,
            )
        ),
    )


@router.delete(
    "/relapse-plan/sections/{section_type}/",
    response={200: RelapsePlanEnvelope, 404: MobileErrorOut, 422: MobileErrorOut},
)
def delete_relapse_section(request: HttpRequest, section_type: str) -> Any:
    """Remove uma seção do plano do paciente; o plano ganha uma nova versão."""
    if section_type not in _SECTION_ORDER:
        return problem(422, "Tipo de seção desconhecido.", "invalid_section_type")
    context = mobile_context(request)
    try:
        remove_relapse_plan_section(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
            section_type=section_type,
            actor_id=context.user.pk,
            request_id=request_id(request),
            network_origin=network_origin(request),
        )
    except ValidationError:
        return problem(404, "Seção não encontrada.", "not_found")
    return Status(
        200,
        relapse_plan_envelope(
            relapse_plan_for_patient(
                clinic_id=context.clinic_id,
                patient_profile_id=context.patient_profile_id,
            )
        ),
    )


# ── Plano de apoio urgente ──────────────────────────────────────────────────


class UrgentPlanIn(Schema):
    personal_instructions: str = Field(default="", max_length=MAX_INSTRUCTIONS)
    calming_strategies: list[Annotated[str, Field(max_length=MAX_STRATEGY)]] = Field(
        default_factory=list, max_length=MAX_STRATEGIES
    )


class UrgentContactIn(Schema):
    name: str = Field(min_length=1, max_length=MAX_CONTACT_NAME)
    relationship: str = Field(min_length=1, max_length=MAX_CONTACT_RELATIONSHIP)
    phone_number: str = Field(min_length=1, max_length=MAX_PHONE_INPUT)
    message_template: str = Field(default="", max_length=MAX_CONTACT_MESSAGE)


def normalize_phone(raw: str) -> str | None:
    """Telefone com espaços normalizados, ou ``None`` se não for um telefone válido.

    Só dígitos, `+` (apenas no início), espaços, parênteses e hífen, com 8 a 20 dígitos.
    """
    text = " ".join(raw.split())
    if not _PHONE_SHAPE.fullmatch(text):
        return None
    digits = sum(char.isdigit() for char in text)
    return text if MIN_PHONE_DIGITS <= digits <= MAX_PHONE_DIGITS else None


def _clean_contact(payload: UrgentContactIn) -> dict[str, str] | Status[dict[str, str]]:
    """Campos prontos para gravar, ou a resposta de erro (sem ecoar o que veio)."""
    name = " ".join(payload.name.split())
    relationship = " ".join(payload.relationship.split())
    if not name or not relationship:
        return problem(422, "Informe o nome e o vínculo da pessoa.", "invalid_contact")
    phone = normalize_phone(payload.phone_number)
    if phone is None:
        return problem(422, "Telefone inválido.", "invalid_phone")
    return {
        "name": name,
        "relationship": relationship,
        "phone_number": phone,
        "message_template": payload.message_template.strip(),
    }


@router.put(
    "/urgent-plan/",
    response={200: UrgentPlanOut, 422: MobileErrorOut},
)
def save_urgent_plan(request: HttpRequest, payload: UrgentPlanIn) -> Any:
    """Grava o texto do plano e as estratégias de acalmar. Não mexe nos contatos.

    Idioma, região e prazo de revisão já gravados são preservados. Salvar o plano não
    avisa nem contata ninguém. A resposta tem o formato de `urgent_plan` em
    `GET /mobile/help/` (que segue sendo a leitura, até com cobrança bloqueada).
    """
    context = mobile_context(request)
    existing = urgent_support_plan_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )["plan"]
    preserved: dict[str, Any] = {}
    if existing is not None:
        preserved = {
            "preferred_language": existing.preferred_language,
            "region": existing.region,
            "review_period_days": existing.review_period_days,
        }
    strategies = [text for item in payload.calming_strategies if (text := item.strip())]
    plan = create_or_update_urgent_plan(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        personal_instructions=payload.personal_instructions,
        calming_strategies=strategies,
        actor_id=context.user.pk,
        request_id=request_id(request),
        network_origin=network_origin(request),
        **preserved,
    )
    contacts = urgent_support_plan_for_patient(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )["contacts"]
    return Status(200, urgent_plan_out(plan, contacts))


@router.post(
    "/urgent-plan/contacts/",
    response={
        201: UrgentContactOut,
        404: MobileErrorOut,
        409: MobileErrorOut,
        422: MobileErrorOut,
    },
)
def add_urgent_contact(request: HttpRequest, payload: UrgentContactIn) -> Any:
    """Acrescenta uma pessoa de confiança, no fim da ordem (até 5 ativas).

    Se o paciente ainda não tem plano, cria um vazio. Nada é enviado à pessoa.
    """
    context = mobile_context(request)
    cleaned = _clean_contact(payload)
    if isinstance(cleaned, Status):
        return cleaned
    try:
        with transaction.atomic():
            plan = urgent_support_plan_for_patient(
                clinic_id=context.clinic_id,
                patient_profile_id=context.patient_profile_id,
            )["plan"]
            if plan is None:
                plan = create_or_update_urgent_plan(
                    clinic_id=context.clinic_id,
                    patient_profile_id=context.patient_profile_id,
                    actor_id=context.user.pk,
                    request_id=request_id(request),
                    network_origin=network_origin(request),
                )
            contact = register_urgent_contact(
                clinic_id=context.clinic_id,
                plan_id=plan.pk,
                priority_order=None,
                max_active_contacts=MAX_ACTIVE_CONTACTS,
                actor_id=context.user.pk,
                request_id=request_id(request),
                network_origin=network_origin(request),
                **cleaned,
            )
    except UrgentContactLimitError:
        return problem(
            409,
            f"O plano já tem {MAX_ACTIVE_CONTACTS} pessoas de confiança.",
            "limit_reached",
        )
    except ValueError:
        return problem(404, "Plano de apoio não encontrado.", "not_found")
    return Status(201, urgent_contact_out(contact))


@router.put(
    "/urgent-plan/contacts/{uuid:contact_id}/",
    response={200: UrgentContactOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def edit_urgent_contact(
    request: HttpRequest, contact_id: UUID, payload: UrgentContactIn
) -> Any:
    """Troca os dados de uma pessoa de confiança do paciente (a ordem é mantida)."""
    context = mobile_context(request)
    own = urgent_contact_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        contact_id=contact_id,
    )
    if own is None:
        return problem(404, "Pessoa de confiança não encontrada.", "not_found")
    cleaned = _clean_contact(payload)
    if isinstance(cleaned, Status):
        return cleaned
    try:
        contact = update_urgent_contact(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
            contact_id=own.pk,
            actor_id=context.user.pk,
            request_id=request_id(request),
            network_origin=network_origin(request),
            **cleaned,
        )
    except ValueError:
        return problem(404, "Pessoa de confiança não encontrada.", "not_found")
    return Status(200, urgent_contact_out(contact))


@router.delete(
    "/urgent-plan/contacts/{uuid:contact_id}/",
    response={204: None, 404: MobileErrorOut},
)
def remove_urgent_contact(request: HttpRequest, contact_id: UUID) -> Any:
    """Tira a pessoa do plano (o registro fica inativo; some de todas as leituras)."""
    context = mobile_context(request)
    own = urgent_contact_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        contact_id=contact_id,
    )
    if own is None:
        return problem(404, "Pessoa de confiança não encontrada.", "not_found")
    try:
        deactivate_urgent_contact(
            clinic_id=context.clinic_id,
            patient_profile_id=context.patient_profile_id,
            contact_id=own.pk,
            actor_id=context.user.pk,
            request_id=request_id(request),
            network_origin=network_origin(request),
        )
    except ValueError:
        return problem(404, "Pessoa de confiança não encontrada.", "not_found")
    return Status(204, None)


# ── Pouca energia ───────────────────────────────────────────────────────────


class LowEnergyActionsIn(Schema):
    actions: list[Annotated[str, Field(max_length=MAX_LOW_ENERGY_ACTION)]] = Field(
        max_length=MAX_LOW_ENERGY_ACTIONS
    )


@router.put(
    "/low-energy/actions/",
    response={200: LowEnergyOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def set_low_energy_actions(request: HttpRequest, payload: LowEnergyActionsIn) -> Any:
    """Define as ações mínimas (1 a 3) do modo de pouca energia.

    Cada gravação é uma nova versão. O modo já ligado segue com as ações de quando foi
    ligado; as novas valem na próxima vez. Ligar e desligar é `PUT /low-energy/`.
    """
    context = mobile_context(request)
    texts = [text for item in payload.actions if (text := " ".join(item.split()))]
    if not texts:
        return problem(
            422, "Informe pelo menos uma ação mínima.", "no_actions_configured"
        )
    slots = dict(zip(("action_1", "action_2", "action_3"), texts, strict=False))
    try:
        with transaction.atomic():
            template = configure_low_energy_actions(
                clinic_id=context.clinic_id,
                actor=context.user,
                request_id=request_id(request),
                **slots,
            )
            # O domínio de metas não tem trilha própria nem pode depender de `audit`
            # (regra de fronteiras); a trilha, sem o texto das ações, é desta camada.
            record_audit_event(
                clinic_id=context.clinic_id,
                actor_id=context.user.pk,
                action="goals.low_energy_actions_configured",
                resource_type="low_energy_action_template",
                resource_id=str(template.pk),
                outcome="success",
                request_id=request_id(request),
                network_origin=network_origin(request),
            )
    except PermissionDenied:
        return problem(404, "Paciente não encontrado.", "not_found")
    except ValidationError:
        return problem(
            422, "Informe pelo menos uma ação mínima.", "no_actions_configured"
        )
    return Status(200, low_energy_out(context))
