"""API do app do paciente: rede de apoio, conteúdos, consentimentos e direitos LGPD."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from accounts.models import User
from audit.models import AuditEvent
from clinics.models import Clinic
from consents.models import ConsentDocument, ConsentManifestation
from consents.services import publish_consent_document
from content.models import Content, ContentRecommendation, ContentVersion
from people.models import ProfessionalCredential, ProfessionalProfile
from privacy.models import DataSubjectRequest
from support_network.network_models import (
    SupportNetworkInvitation,
    SupportNetworkPermission,
    SupportNetworkRelationship,
)
from tests.aftercare_support import (
    PatientLogin,
    Stage,
    build_stage,
    make_patient_login,
)

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/mobile/auth/login/"
BASE = "/api/v1/mobile"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    cache.clear()


def _login(who: PatientLogin) -> dict[str, str]:
    response = Client().post(
        LOGIN,
        {"email": who.user.email, "password": who.password, "device_label": "Teste"},
        content_type="application/json",
    )
    assert response.status_code == 200, response.content
    return {"HTTP_AUTHORIZATION": f"Bearer {response.json()['access_token']}"}


def _call(method: str, url: str, headers: dict[str, str], body: Any = None) -> Any:
    kwargs: dict[str, Any] = dict(headers)
    if body is not None:
        kwargs["data"] = body
        kwargs["content_type"] = "application/json"
    return getattr(Client(), method)(url, **kwargs)


def _world() -> tuple[
    Stage, PatientLogin, PatientLogin, dict[str, str], dict[str, str]
]:
    stage = build_stage()
    ana = make_patient_login(stage.clinic, stage.admin, name="Ana Souza")
    bia = make_patient_login(stage.clinic, stage.admin, name="Bia Lima")
    return stage, ana, bia, _login(ana), _login(bia)


# ── Rede de apoio ───────────────────────────────────────────────────────────


def _supporter(
    stage: Stage, who: PatientLogin, name: str, scopes: tuple[str, ...] = ()
) -> SupportNetworkRelationship:
    relationship = SupportNetworkRelationship.objects.for_clinic(
        stage.clinic.pk
    ).create(
        clinic_id=stage.clinic.pk,
        patient_id=who.profile.pk,
        supporter_name=name,
        supporter_email=f"{name.lower()}@example.test",
        relationship_type="family",
    )
    for scope in scopes:
        SupportNetworkPermission.objects.for_clinic(stage.clinic.pk).create(
            clinic_id=stage.clinic.pk, relationship=relationship, permission_scope=scope
        )
    return relationship


def test_support_network_lists_only_the_patients_own_people() -> None:
    stage, ana, bia, ana_h, _ = _world()
    mine = _supporter(stage, ana, "Marta", ("view_wellness_summary",))
    _supporter(stage, bia, "Pedro", ("receive_urgent_alerts",))
    SupportNetworkInvitation.objects.for_clinic(stage.clinic.pk).create(
        clinic_id=stage.clinic.pk,
        patient_id=ana.profile.pk,
        invitee_name="Convidada",
        invitee_email="convidada@example.test",
        invitation_token="x" * 20,
        expires_at=timezone.now() + timedelta(days=3),
    )
    body = _call("get", f"{BASE}/support-network/", ana_h).json()
    assert [s["id"] for s in body["supporters"]] == [str(mine.pk)]
    assert body["supporters"][0]["scopes"] == ["view_wellness_summary"]
    assert [i["name"] for i in body["pending_invitations"]] == ["Convidada"]
    assert "Pedro" not in str(body)
    assert set(body["available_scopes"]) == {
        "view_wellness_summary",
        "receive_urgent_alerts",
        "view_relapse_plan_safe",
        "receive_checkin_summary",
    }
    assert "medical_records" not in body["available_scopes"]
    assert "email" not in str(body).lower().replace(
        "pending", ""
    )  # sem e-mail do apoio


def test_changing_scopes_needs_the_patients_password() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    marta = _supporter(stage, ana, "Marta", ("view_wellness_summary",))
    url = f"{BASE}/support-network/{marta.pk}/scopes/"
    wrong = _call(
        "put", url, ana_h, {"scopes": ["receive_urgent_alerts"], "password": "errada"}
    )
    assert (
        wrong.status_code == 403 and wrong.json()["code"] == "reauthentication_failed"
    )
    active = SupportNetworkPermission.objects.for_clinic(stage.clinic.pk).filter(
        relationship=marta, is_active=True
    )
    assert [p.permission_scope for p in active] == ["view_wellness_summary"]
    ok = _call(
        "put",
        url,
        ana_h,
        {
            "scopes": ["receive_urgent_alerts", "view_relapse_plan_safe"],
            "password": ana.password,
        },
    )
    assert ok.status_code == 200, ok.content
    assert ok.json()["scopes"] == ["receive_urgent_alerts", "view_relapse_plan_safe"]
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(action="support_network.permissions_updated", actor_id=ana.user.pk)
        .exists()
    )


@pytest.mark.parametrize(
    "scopes",
    [["medical_records"], ["view_wellness_summary", "prescriptions"], ["qualquer"]],
)
def test_forbidden_or_unknown_scopes_are_rejected_before_asking_the_password(
    scopes: list[str],
) -> None:
    stage, ana, _bia, ana_h, _ = _world()
    marta = _supporter(stage, ana, "Marta", ("view_wellness_summary",))
    response = _call(
        "put",
        f"{BASE}/support-network/{marta.pk}/scopes/",
        ana_h,
        {"scopes": scopes, "password": ana.password},
    )
    assert response.status_code == 422 and response.json()["code"] == "invalid_scope"


def test_scope_changes_and_revocation_never_touch_another_patients_people() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    theirs = _supporter(stage, bia, "Pedro", ("receive_urgent_alerts",))
    url = f"{BASE}/support-network/{theirs.pk}/"
    put = _call("put", f"{url}scopes/", ana_h, {"scopes": [], "password": ana.password})
    assert put.status_code == 404
    assert _call("delete", url, ana_h).status_code == 404
    theirs.refresh_from_db()
    assert theirs.is_active is True
    assert (
        SupportNetworkPermission.objects.for_clinic(stage.clinic.pk)
        .filter(relationship=theirs, is_active=True)
        .count()
        == 1
    )
    assert _call("delete", url, bia_h).status_code == 204  # a dona consegue


def test_ending_a_supporter_revokes_every_permission() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    marta = _supporter(
        stage, ana, "Marta", ("view_wellness_summary", "receive_urgent_alerts")
    )
    assert (
        _call("delete", f"{BASE}/support-network/{marta.pk}/", ana_h).status_code == 204
    )
    marta.refresh_from_db()
    assert marta.is_active is False and marta.revoked_by_id == ana.user.pk
    assert (
        not SupportNetworkPermission.objects.for_clinic(stage.clinic.pk)
        .filter(relationship=marta, is_active=True)
        .exists()
    )
    assert _call("get", f"{BASE}/support-network/", ana_h).json()["supporters"] == []
    assert (
        _call("delete", f"{BASE}/support-network/{marta.pk}/", ana_h).status_code == 404
    )


def test_repeated_wrong_passwords_are_rate_limited() -> None:
    stage, ana, _bia, ana_h, _ = _world()
    marta = _supporter(stage, ana, "Marta", ())
    url = f"{BASE}/support-network/{marta.pk}/scopes/"
    codes = [
        _call("put", url, ana_h, {"scopes": [], "password": "errada"}).status_code
        for _ in range(7)
    ]
    assert 429 in codes and codes[0] == 403
    assert (
        _call("put", url, ana_h, {"scopes": [], "password": ana.password}).status_code
        == 429
    )


# ── Conteúdos ───────────────────────────────────────────────────────────────


def _content(stage: Stage, slug: str, body: str, **over: Any) -> Content:
    values: dict[str, Any] = {
        "clinic_id": stage.clinic.pk,
        "slug": slug,
        "title": slug.replace("-", " ").title(),
        "kind": "article",
        "language_code": "pt-BR",
        "category": "Sono",
        "audience": "patient",
        "status": "published",
        "created_by": stage.admin,
        "contraindications": "Pare se sentir tontura.",
        "source_reference": "Fonte sintética",
    }
    values.update(over)
    content = Content.objects.for_clinic(stage.clinic.pk).create(**values)
    ContentVersion.infrastructure_objects.create(
        clinic_id=stage.clinic.pk,
        content=content,
        version=content.current_version,
        body=body,
        status="published",
    )
    return content


def _verified_therapist(stage: Stage) -> None:
    profile = ProfessionalProfile.infrastructure_objects.create(
        clinic=stage.clinic,
        user=stage.therapist,
        full_name="Dra. Exemplo",
        professional_email=stage.therapist.email,
        category="psychologist",
    )
    credential = ProfessionalCredential.objects.create(profile=profile)
    credential.status = ProfessionalCredential.Status.VERIFIED
    credential.council_name = "CRP"
    credential.council_number = "123456"
    credential.council_jurisdiction = "PE"
    credential.save()


def test_content_returns_plain_text_for_published_patient_items_only() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    _content(
        stage,
        "respiracao",
        "<p>Respire fundo.</p><ul><li>Conte até 4</li><li>Solte o ar</li></ul>",
    )
    _content(stage, "rascunho", "Ainda não publicado", status="draft")
    _content(stage, "para-equipe", "Material técnico", audience="professional")
    _content(stage, "em-ingles", "English body", language_code="en")
    _content(
        stage,
        "vencido",
        "Texto vencido",
        valid_until=timezone.localdate() - timedelta(days=1),
    )
    outsider = build_stage()
    _content(outsider, "de-outra-clinica", "Segredo de outra clínica")
    body = _call("get", f"{BASE}/content/", ana_h).json()
    assert [c["slug"] for c in body] == ["respiracao"]
    item = body[0]
    assert item["body"] == "Respire fundo.\n\n• Conte até 4\n• Solte o ar"
    assert "<" not in item["body"] and item["recommended_by_name"] is None
    assert item["contraindications"] == "Pare se sentir tontura."
    assert "Segredo" not in str(body) and "Material técnico" not in str(body)


def test_recommended_content_comes_first_with_the_professional_attribution() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    _verified_therapist(stage)
    _content(stage, "geral", "Texto geral")
    chosen = _content(stage, "indicado", "Texto indicado para você")
    ContentRecommendation.infrastructure_objects.create(
        clinic_id=stage.clinic.pk,
        content_id=chosen.pk,
        recommended_by_id=stage.therapist.pk,
        patient_id=ana.user.pk,
        objective="Dormir melhor",
        priority="high",
        status="active",
        credential_snapshot={},
        credential_digest="x",
    )
    body = _call("get", f"{BASE}/content/", ana_h).json()
    assert [c["slug"] for c in body] == ["indicado", "geral"]
    assert body[0]["recommended_by_name"] == "Dra. Exemplo"
    assert body[0]["recommendation_objective"] == "Dormir melhor"
    other = _call("get", f"{BASE}/content/", bia_h).json()
    assert [c["slug"] for c in other] == ["geral", "indicado"]
    assert all(c["recommended_by_name"] is None for c in other)
    assert bia.user.pk is not None


# ── Consentimentos ──────────────────────────────────────────────────────────


def _document(clinic: Clinic, admin: User, **over: Any) -> ConsentDocument:
    values: dict[str, Any] = {
        "clinic_id": clinic.pk,
        "actor": admin,
        "document_type": "consent",
        "title": "Acompanhamento clínico",
        "version": "1",
        "content": "Autorizo o acompanhamento clínico pela equipe.",
        "purpose": "clinical_follow_up",
        "effective_from": timezone.now() - timedelta(days=1),
        "audience": "patient",
        "is_mandatory": False,
        "refusal_consequence": "Sem acompanhamento pelo app",
        "alternative_instructions": "Atendimento presencial",
        "clinic_contact_instructions": "Recepção",
    }
    values.update(over)
    return publish_consent_document(**values)


def test_consents_list_shows_current_documents_and_the_patients_own_decision() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    optional = _document(stage.clinic, stage.admin)
    mandatory = _document(
        stage.clinic,
        stage.admin,
        document_type="terms",
        purpose="terms_of_use",
        title="Termos",
        is_mandatory=True,
    )
    _document(
        stage.clinic,
        stage.admin,
        audience="professional",
        title="Só equipe",
        purpose="staff_operations",
    )
    body = _call("get", f"{BASE}/consents/", ana_h).json()
    assert {c["title"] for c in body} == {"Acompanhamento clínico", "Termos"}
    assert all(c["status"] == "pending" and c["can_revoke"] is False for c in body)
    decision = _call(
        "post",
        f"{BASE}/consents/{optional.pk}/decision/",
        ana_h,
        {"decision": "accepted"},
    )
    assert decision.status_code == 200, decision.content
    assert (
        decision.json()["status"] == "accepted"
        and decision.json()["can_revoke"] is True
    )
    ana_view = {
        c["document_id"]: c for c in _call("get", f"{BASE}/consents/", ana_h).json()
    }
    bia_view = {
        c["document_id"]: c for c in _call("get", f"{BASE}/consents/", bia_h).json()
    }
    assert ana_view[str(optional.pk)]["status"] == "accepted"
    assert bia_view[str(optional.pk)]["status"] == "pending"
    assert ana_view[str(mandatory.pk)]["mandatory"] is True
    manifestation = ConsentManifestation.objects.for_clinic(stage.clinic.pk).get()
    assert (
        manifestation.source == "mobile_app" and manifestation.subject_id == ana.user.pk
    )


def test_consent_detail_has_the_full_text_and_the_refusal_consequences() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    document = _document(stage.clinic, stage.admin)
    body = _call("get", f"{BASE}/consents/{document.pk}/", ana_h).json()
    assert body["content"] == "Autorizo o acompanhamento clínico pela equipe."
    assert body["refusal_consequence"] == "Sem acompanhamento pelo app"
    assert _call("get", f"{BASE}/consents/{uuid4()}/", ana_h).status_code == 404


def test_consent_decisions_are_idempotent_and_follow_the_domain_rules() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    document = _document(stage.clinic, stage.admin)
    url = f"{BASE}/consents/{document.pk}/decision/"
    key = str(uuid4())
    first = _call("post", url, ana_h, {"decision": "accepted", "request_id": key})
    replay = _call("post", url, ana_h, {"decision": "accepted", "request_id": key})
    assert first.status_code == replay.status_code == 200
    assert ConsentManifestation.objects.for_clinic(stage.clinic.pk).count() == 1
    # aceita não vira recusa por decisão nova: só pela revogação
    refused = _call("post", url, ana_h, {"decision": "refused"})
    assert refused.status_code == 422 and refused.json()["code"] == "consent_rejected"
    assert _call("post", url, ana_h, {"decision": "maybe"}).status_code == 422


def test_revoking_requires_an_accepted_optional_document_and_a_reason() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    optional = _document(stage.clinic, stage.admin)
    mandatory = _document(
        stage.clinic,
        stage.admin,
        document_type="terms",
        purpose="terms_of_use",
        title="Termos",
        is_mandatory=True,
    )
    revoke = f"{BASE}/consents/{optional.pk}/revoke/"
    nothing = _call("post", revoke, ana_h, {"reason": "Mudei de ideia"})
    assert (
        nothing.status_code == 422 and nothing.json()["code"] == "revocation_rejected"
    )
    _call(
        "post",
        f"{BASE}/consents/{optional.pk}/decision/",
        ana_h,
        {"decision": "accepted"},
    )
    assert _call("post", revoke, ana_h, {"reason": "ab"}).status_code == 422
    done = _call("post", revoke, ana_h, {"reason": "Mudei de ideia"})
    assert done.status_code == 200 and done.json()["status"] == "revoked"
    assert done.json()["can_revoke"] is False
    _call(
        "post",
        f"{BASE}/consents/{mandatory.pk}/decision/",
        ana_h,
        {"decision": "accepted"},
    )
    blocked = _call(
        "post",
        f"{BASE}/consents/{mandatory.pk}/revoke/",
        ana_h,
        {"reason": "Quero sair"},
    )
    assert (
        blocked.status_code == 422
    )  # obrigatório: segue o fluxo de direitos do titular


def test_documents_of_another_clinic_or_audience_are_a_plain_404() -> None:
    stage, _ana, _bia, ana_h, _ = _world()
    foreign = _document(stage.other_clinic, stage.other_admin)
    staff_only = _document(
        stage.clinic, stage.admin, audience="professional", purpose="staff_operations"
    )
    for document in (foreign, staff_only):
        for action, body in (
            ("decision", {"decision": "accepted"}),
            ("revoke", {"reason": "teste"}),
        ):
            response = _call(
                "post", f"{BASE}/consents/{document.pk}/{action}/", ana_h, body
            )
            assert response.status_code == 404
    assert ConsentManifestation.objects.for_clinic(stage.clinic.pk).count() == 0


# ── Direitos do titular (LGPD) ──────────────────────────────────────────────


def test_privacy_request_is_filed_for_the_patient_with_identity_pending() -> None:
    stage, ana, bia, ana_h, bia_h = _world()
    created = _call("post", f"{BASE}/privacy-requests/", ana_h, {"type": "access"})
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["type"] == "access" and body["status"] == "identity_pending"
    row = DataSubjectRequest.infrastructure_objects.get()
    assert row.subject_id == ana.user.pk == row.requested_by_id
    assert row.channel == "mobile_app" and row.clinic_id == stage.clinic.pk
    assert (row.due_at - row.requested_at).days == 15
    assert (
        AuditEvent.objects.for_clinic(stage.clinic.pk)
        .filter(resource_type="data_subject_request", actor_id=ana.user.pk)
        .exists()
    )
    assert [
        r["type"] for r in _call("get", f"{BASE}/privacy-requests/", ana_h).json()
    ] == ["access"]
    assert _call("get", f"{BASE}/privacy-requests/", bia_h).json() == []
    assert bia.user.pk is not None


def test_privacy_requests_do_not_duplicate_while_open_and_validate_the_type() -> None:
    _stage, _ana, _bia, ana_h, _ = _world()
    url = f"{BASE}/privacy-requests/"
    assert _call("post", url, ana_h, {"type": "erasure"}).status_code == 201
    again = _call("post", url, ana_h, {"type": "erasure"})
    assert again.status_code == 409 and again.json()["code"] == "already_open"
    assert _call("post", url, ana_h, {"type": "portability"}).status_code == 201
    assert _call("post", url, ana_h, {"type": "delete-everything"}).status_code == 422
    DataSubjectRequest.infrastructure_objects.filter(request_type="erasure").update(
        status="completed"
    )
    assert _call("post", url, ana_h, {"type": "erasure"}).status_code == 201


# ── Transversais ────────────────────────────────────────────────────────────


def test_every_support_route_requires_the_app_token() -> None:
    client = Client()
    for method, url in (
        ("get", f"{BASE}/support-network/"),
        ("put", f"{BASE}/support-network/{uuid4()}/scopes/"),
        ("delete", f"{BASE}/support-network/{uuid4()}/"),
        ("get", f"{BASE}/content/"),
        ("get", f"{BASE}/consents/"),
        ("get", f"{BASE}/consents/{uuid4()}/"),
        ("post", f"{BASE}/consents/{uuid4()}/decision/"),
        ("post", f"{BASE}/consents/{uuid4()}/revoke/"),
        ("get", f"{BASE}/privacy-requests/"),
        ("post", f"{BASE}/privacy-requests/"),
    ):
        response = getattr(client, method)(url, content_type="application/json")
        assert response.status_code == 401, (method, url)
