"""Rede de apoio, conteúdos, consentimentos e direitos LGPD no app do paciente.

(`/api/v1/mobile/`). Cada rota resolve o objeto pelo perfil/identidade da sessão;
id de outra pessoa responde 404. Mudar o que a rede de apoio enxerga exige
reautenticação por senha (mesma regra do web).
"""

from __future__ import annotations

import html.parser
import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from ninja import Field, Router, Schema, Status

from accounts.services import (
    SensitiveActionRateLimitedError,
    reauthenticate_sensitive_action,
)
from consents.models import ConsentDocument, ConsentManifestation
from consents.selectors import (
    current_documents_for_actor,
    latest_manifestations_for_subject,
)
from consents.services import record_consent_manifestation, revoke_consent
from content.models import Content
from content.selectors import current_version_body, published_content_by_slug
from content.services import recommendations_for_patient, search_published_content
from privacy.models import DataSubjectRequest
from privacy.selectors import data_subject_requests_for_subject
from privacy.services import DuplicateOpenRequestError, create_own_data_subject_request
from support_network.contracts import SupportPermissionScope
from support_network.models import SupportNetworkRelationship
from support_network.selectors import (
    active_supporter_for_patient,
    support_network_summary,
)
from support_network.services import (
    revoke_support_relationship,
    update_support_permissions,
)

from .mobile_common import (
    MobileErrorOut,
    PatientBearerAuth,
    mobile_context,
    network_origin,
    problem,
)

router = Router(tags=["Mobile · Apoio e privacidade"], auth=PatientBearerAuth())

APP_SOURCE = "mobile_app"
MAX_CONTENT_ITEMS = 100
_LANGUAGES = {"pt-br": "pt-BR", "en": "en", "es": "es"}


# ── Rede de apoio ───────────────────────────────────────────────────────────


class SupporterOut(Schema):
    id: UUID
    name: str
    relationship_type: str
    scopes: list[str]
    established_at: datetime


class InvitationOut(Schema):
    id: UUID
    name: str
    relationship_type: str
    expires_at: datetime


class SupportNetworkOut(Schema):
    supporters: list[SupporterOut]
    pending_invitations: list[InvitationOut]
    available_scopes: list[str]


class ScopesIn(Schema):
    scopes: list[str] = Field(max_length=16)
    password: str = Field(max_length=1024)


def _supporter_out(relationship: SupportNetworkRelationship) -> SupporterOut:
    permissions = relationship.permissions.all()
    return SupporterOut(
        id=relationship.pk,
        name=relationship.supporter_name,
        relationship_type=relationship.relationship_type,
        scopes=sorted(p.permission_scope for p in permissions if p.is_active),
        established_at=relationship.established_at,
    )


@router.get("/support-network/", response=SupportNetworkOut)
def get_support_network(request: HttpRequest):
    """Quem acompanha o paciente e o que cada pessoa enxerga.

    O diário e os registros clínicos nunca fazem parte do que pode ser compartilhado.
    """
    context = mobile_context(request)
    summary = support_network_summary(
        clinic_id=context.clinic_id, patient_profile_id=context.patient_profile_id
    )
    return SupportNetworkOut(
        supporters=[_supporter_out(item) for item in summary["relationships"]],
        pending_invitations=[
            InvitationOut(
                id=item.pk,
                name=item.invitee_name,
                relationship_type=item.relationship_type,
                expires_at=item.expires_at,
            )
            for item in summary["pending_invitations"]
        ],
        available_scopes=[scope.value for scope in SupportPermissionScope],
    )


@router.put(
    "/support-network/{uuid:relationship_id}/scopes/",
    response={
        200: SupporterOut,
        403: MobileErrorOut,
        404: MobileErrorOut,
        422: MobileErrorOut,
        429: MobileErrorOut,
    },
)
def set_scopes(request: HttpRequest, relationship_id: UUID, payload: ScopesIn):
    """Define o que uma pessoa pode ver. Exige a senha do paciente."""
    context = mobile_context(request)
    relationship = active_supporter_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        relationship_id=relationship_id,
    )
    if relationship is None:
        return problem(404, "Pessoa de apoio não encontrada.", "not_found")
    allowed = {scope.value for scope in SupportPermissionScope}
    if not set(payload.scopes) <= allowed:
        return problem(422, "Permissão desconhecida.", "invalid_scope")
    try:
        verified = reauthenticate_sensitive_action(
            actor=context.user, password=payload.password
        )
    except SensitiveActionRateLimitedError:
        return problem(429, "Muitas tentativas. Aguarde.", "rate_limited")
    if not verified:
        return problem(403, "Senha incorreta.", "reauthentication_failed")
    try:
        update_support_permissions(
            clinic_id=context.clinic_id,
            relationship_id=relationship.pk,
            granted_scopes=set(payload.scopes),
            user=context.user,
            step_up_authenticated=True,
            actor_id=context.user.pk,
        )
    except ValueError, PermissionDenied:
        return problem(422, "Não foi possível alterar as permissões.", "rejected")
    refreshed = active_supporter_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        relationship_id=relationship.pk,
    )
    assert refreshed is not None
    return Status(200, _supporter_out(refreshed))


@router.delete(
    "/support-network/{uuid:relationship_id}/",
    response={204: None, 404: MobileErrorOut},
)
def end_support(request: HttpRequest, relationship_id: UUID):
    """Encerra o vínculo e retira todas as permissões dessa pessoa."""
    context = mobile_context(request)
    relationship = active_supporter_for_patient(
        clinic_id=context.clinic_id,
        patient_profile_id=context.patient_profile_id,
        relationship_id=relationship_id,
    )
    if relationship is None:
        return problem(404, "Pessoa de apoio não encontrada.", "not_found")
    revoke_support_relationship(
        clinic_id=context.clinic_id,
        relationship_id=relationship.pk,
        revoked_by=context.user,
        actor_id=context.user.pk,
    )
    return Status(204, None)


# ── Conteúdos ───────────────────────────────────────────────────────────────


class ContentOut(Schema):
    id: UUID
    slug: str
    title: str
    kind: str
    category: str
    body: str
    contraindications: str
    source_reference: str
    recommended_by_name: str | None
    recommendation_objective: str | None
    recommendation_priority: str | None


class _PlainText(html.parser.HTMLParser):
    """Converte o HTML já saneado do conteúdo em texto simples para o app."""

    _BLOCKS = frozenset({"p", "div", "h1", "h2", "h3", "h4", "ul", "ol", "blockquote"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n• ")
        elif tag in self._BLOCKS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCKS:
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(body: str) -> str:
    parser = _PlainText()
    parser.feed(body)
    parser.close()
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


@router.get("/content/", response=list[ContentOut])
def list_content(request: HttpRequest):
    """Conteúdos indicados pela equipe e a biblioteca publicada para pacientes.

    Só texto simples. Favoritos e "lido" não existem no servidor: ficam fora.
    """
    context = mobile_context(request)
    language = _LANGUAGES.get(
        (context.user.preferred_language or "").lower(),
        context.patient_profile.language_code or "pt-BR",
    )
    recommended = recommendations_for_patient(
        clinic_id=context.clinic_id, user=context.user
    )
    items: list[ContentOut] = []
    seen: set[UUID] = set()
    for row in recommended:
        content = published_content_by_slug(
            clinic_id=context.clinic_id, slug=str(row["content_slug"])
        )
        if content is None or content.pk in seen:
            continue
        seen.add(content.pk)
        items.append(
            _content_out(
                context.clinic_id,
                content,
                recommended_by=str(row["recommended_by"]) or None,
                objective=str(row["objective"]) or None,
                priority=str(row["priority"]) or None,
            )
        )
    for content in search_published_content(
        clinic_id=context.clinic_id,
        query="",
        language_code=language,
        audience="patient",
    ):
        if content.pk in seen:
            continue
        seen.add(content.pk)
        items.append(_content_out(context.clinic_id, content))
    return items[:MAX_CONTENT_ITEMS]


def _content_out(
    clinic_id: UUID,
    content: Content,
    *,
    recommended_by: str | None = None,
    objective: str | None = None,
    priority: str | None = None,
) -> ContentOut:
    return ContentOut(
        id=content.pk,
        slug=content.slug,
        title=content.title,
        kind=content.kind,
        category=content.category,
        body=plain_text(current_version_body(clinic_id=clinic_id, content=content)),
        contraindications=content.contraindications,
        source_reference=content.source_reference,
        recommended_by_name=recommended_by,
        recommendation_objective=objective,
        recommendation_priority=priority,
    )


# ── Consentimentos ──────────────────────────────────────────────────────────


class ConsentOut(Schema):
    document_id: UUID
    purpose: str
    kind: str
    title: str
    version: str
    mandatory: bool
    status: str
    decided_at: datetime | None
    can_revoke: bool


class ConsentDetailOut(ConsentOut):
    content: str
    refusal_consequence: str
    alternative_instructions: str
    clinic_contact_instructions: str


class DecisionIn(Schema):
    decision: Literal["accepted", "refused"]
    request_id: UUID | None = None


class RevokeIn(Schema):
    reason: str = Field(min_length=3, max_length=500)
    request_id: UUID | None = None


def _consent_rows(context):
    documents = current_documents_for_actor(
        clinic_id=context.clinic_id, actor=context.user
    )
    latest = latest_manifestations_for_subject(
        clinic_id=context.clinic_id,
        subject_id=context.user.pk,
        document_ids={d.pk for d in documents},
    )
    return documents, latest


def _consent_out(
    document: ConsentDocument, latest: dict[UUID, ConsentManifestation]
) -> dict[str, Any]:
    decision = latest.get(document.pk)
    status = decision.decision if decision is not None else "pending"
    return {
        "document_id": document.pk,
        "purpose": document.purpose,
        "kind": document.document_type,
        "title": document.title,
        "version": document.version,
        "mandatory": document.is_mandatory,
        "status": status,
        "decided_at": decision.manifested_at if decision is not None else None,
        "can_revoke": status == "accepted" and not document.is_mandatory,
    }


@router.get("/consents/", response=list[ConsentOut])
def list_consents(request: HttpRequest):
    """Documentos vigentes para o paciente e a última decisão dele em cada um."""
    documents, latest = _consent_rows(mobile_context(request))
    return [ConsentOut(**_consent_out(document, latest)) for document in documents]


@router.get(
    "/consents/{uuid:document_id}/",
    response={200: ConsentDetailOut, 404: MobileErrorOut},
)
def get_consent(request: HttpRequest, document_id: UUID):
    """Texto completo do documento, para ler antes de decidir."""
    documents, latest = _consent_rows(mobile_context(request))
    document = next((d for d in documents if d.pk == document_id), None)
    if document is None:
        return problem(404, "Documento não encontrado.", "not_found")
    return Status(
        200,
        ConsentDetailOut(
            **_consent_out(document, latest),
            content=document.content,
            refusal_consequence=document.refusal_consequence,
            alternative_instructions=document.alternative_instructions,
            clinic_contact_instructions=document.clinic_contact_instructions,
        ),
    )


def _consent_state(context, document_id: UUID):
    documents, latest = _consent_rows(context)
    document = next((d for d in documents if d.pk == document_id), None)
    if document is None:
        return None
    return ConsentOut(**_consent_out(document, latest))


@router.post(
    "/consents/{uuid:document_id}/decision/",
    response={200: ConsentOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def decide_consent(request: HttpRequest, document_id: UUID, payload: DecisionIn):
    """Aceita ou recusa a versão vigente (mesmo ``request_id`` = idempotente)."""
    context = mobile_context(request)
    if _consent_state(context, document_id) is None:
        return problem(404, "Documento não encontrado.", "not_found")
    try:
        record_consent_manifestation(
            clinic_id=context.clinic_id,
            actor=context.user,
            subject_id=context.user.pk,
            document_id=document_id,
            decision=payload.decision,
            request_id=payload.request_id or uuid4(),
            network_origin=network_origin(request),
            client_context=APP_SOURCE,
            source=APP_SOURCE,
        )
    except PermissionDenied:
        return problem(404, "Documento não encontrado.", "not_found")
    except ValidationError as exc:
        return problem(422, " ".join(exc.messages), "consent_rejected")
    state = _consent_state(context, document_id)
    assert state is not None
    return Status(200, state)


@router.post(
    "/consents/{uuid:document_id}/revoke/",
    response={200: ConsentOut, 404: MobileErrorOut, 422: MobileErrorOut},
)
def revoke_document_consent(request: HttpRequest, document_id: UUID, payload: RevokeIn):
    """Revoga uma autorização opcional já aceita (a partir de agora)."""
    context = mobile_context(request)
    if _consent_state(context, document_id) is None:
        return problem(404, "Documento não encontrado.", "not_found")
    try:
        revoke_consent(
            clinic_id=context.clinic_id,
            actor=context.user,
            subject_id=context.user.pk,
            document_id=document_id,
            request_id=payload.request_id or uuid4(),
            reason=payload.reason,
            network_origin=network_origin(request),
            client_context=APP_SOURCE,
            source=APP_SOURCE,
        )
    except PermissionDenied:
        return problem(404, "Documento não encontrado.", "not_found")
    except ValidationError as exc:
        return problem(422, " ".join(exc.messages), "revocation_rejected")
    state = _consent_state(context, document_id)
    assert state is not None
    return Status(200, state)


# ── Direitos do titular (LGPD) ──────────────────────────────────────────────


class PrivacyRequestOut(Schema):
    id: UUID
    type: str
    status: str
    requested_at: datetime
    due_at: datetime
    completed_at: datetime | None


class PrivacyRequestIn(Schema):
    type: Literal[
        "confirmation", "access", "correction", "portability", "revocation", "erasure"
    ]


def _privacy_out(item: DataSubjectRequest) -> PrivacyRequestOut:
    return PrivacyRequestOut(
        id=item.pk,
        type=item.request_type,
        status=item.status,
        requested_at=item.requested_at,
        due_at=item.due_at,
        completed_at=item.completed_at,
    )


@router.get("/privacy-requests/", response=list[PrivacyRequestOut])
def list_privacy_requests(request: HttpRequest):
    """Pedidos do próprio paciente sobre os dados dele, do mais recente."""
    context = mobile_context(request)
    return [
        _privacy_out(item)
        for item in data_subject_requests_for_subject(
            clinic_id=context.clinic_id, subject_id=context.user.pk
        )
    ]


@router.post(
    "/privacy-requests/",
    response={201: PrivacyRequestOut, 409: MobileErrorOut, 422: MobileErrorOut},
)
def create_privacy_request(request: HttpRequest, payload: PrivacyRequestIn):
    """Registra um pedido. Nasce com a identidade a verificar pela clínica."""
    context = mobile_context(request)
    try:
        item = create_own_data_subject_request(
            clinic_id=context.clinic_id,
            actor=context.user,
            request_type=payload.type,
            channel=APP_SOURCE,
        )
    except DuplicateOpenRequestError:
        return problem(409, "Já existe um pedido aberto deste tipo.", "already_open")
    except ValueError, PermissionDenied:
        return problem(422, "Não foi possível registrar o pedido.", "rejected")
    return Status(201, _privacy_out(item))
