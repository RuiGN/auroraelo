"""HTTP localization contracts preserving consent evidence and authorization."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from consents.integrity import publication_payload
from consents.models import (
    ConsentDocument,
    ConsentManifestation,
    ConsentRevocationDispatch,
    ConsentRevocationWorkItem,
)
from consents.policies import purpose_label_pt_br
from consents.services import process_revocation_dispatch, publish_consent_document
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db
LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


def _login(client: Client, user: User, clinic: Clinic) -> None:
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()


def _context(client: Client) -> tuple[Clinic, User, User, ConsentDocument]:
    clinic = ClinicFactory.create()
    administrator, patient = UserFactory.create(), UserFactory.create()
    for user, role in (
        (administrator, ClinicMembership.Role.CLINIC_ADMIN),
        (patient, ClinicMembership.Role.PATIENT),
    ):
        ClinicMembershipFactory.create(clinic=clinic, user=user, role=role)
    document = publish_consent_document(
        clinic_id=clinic.pk,
        actor=administrator,
        document_type="consent",
        title="Autorização <original>",
        version="1.0",
        content="Documento original em português.\n<script>alert('original')</script>",
        purpose="communication",
        effective_from=timezone.now() - timedelta(minutes=1),
        audience="patient",
        is_mandatory=False,
        refusal_consequence="Consequência original <recusa>.",
        alternative_instructions="Alternativa original da clínica.",
        clinic_contact_instructions="Contato original da clínica.",
    )
    _login(client, patient, clinic)
    return clinic, administrator, patient, document


def _decide(
    client: Client, document: ConsentDocument, language: str, decision: str
) -> None:
    response = client.post(
        reverse("consent_decide", args=(document.pk,)),
        {"request_id": str(uuid4()), "decision": decision},
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert response.status_code == 302


def _revoke(client: Client, document: ConsentDocument, language: str) -> None:
    response = client.post(
        reverse("consent_revoke", args=(document.pk,)),
        {
            "request_id": str(uuid4()),
            "reason": "Motivo original privado.",
            "confirm_scope": "on",
        },
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert response.status_code == 302


@pytest.mark.parametrize(
    ("language", "heading", "purpose", "choice"),
    (
        ("pt-br", "Termos e consentimentos", "Comunicação", "Escolha uma opção"),
        ("en", "Terms and consents", "Communication", "Choose an option"),
        ("es", "Términos y consentimientos", "Comunicación", "Elija una opción"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_center_translates_only_interface_and_preserves_document(
    client: Client, language: str, heading: str, purpose: str, choice: str
) -> None:
    _clinic, _administrator, _patient, document = _context(client)
    original = publication_payload(document)
    response = client.get(reverse("consent_center"), HTTP_ACCEPT_LANGUAGE=language)
    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    content = response.content.decode()
    assert f'id="consent-center-title">{heading}</h1>' in content
    assert purpose in content
    assert choice in content
    assert "Autorização &lt;original&gt;" in content
    assert "Documento original em português." in content
    assert "&lt;script&gt;" in content
    assert "<script>alert('original')</script>" not in content
    assert "Consequência original &lt;recusa&gt;." in content
    assert "Alternativa original da clínica." in content
    assert "Contato original da clínica." in content
    assert 'value="accepted" required' in content
    assert 'value="refused" required' in content
    assert 'name="decision" value="accepted" checked' not in content
    document.refresh_from_db()
    assert publication_payload(document) == original


@pytest.mark.parametrize(
    ("language", "accepted", "refused", "revoked", "revoke_label"),
    (
        ("pt-br", "Aceitou", "Recusou", "Revogou", "Revogar autorização"),
        ("en", "Accepted", "Refused", "Revoked", "Revoke authorization"),
        ("es", "Aceptó", "Rechazó", "Revocó", "Revocar autorización"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_decisions_and_revocation_translate_labels_but_keep_canonical_evidence(
    client: Client,
    language: str,
    accepted: str,
    refused: str,
    revoked: str,
    revoke_label: str,
) -> None:
    clinic, _administrator, patient, document = _context(client)
    original = publication_payload(document)
    _decide(client, document, language, "refused")
    center = client.get(reverse("consent_center"), HTTP_ACCEPT_LANGUAGE=language)
    assert refused in center.content.decode()
    assert revoke_label not in center.content.decode()
    _decide(client, document, language, "accepted")
    center = client.get(reverse("consent_center"), HTTP_ACCEPT_LANGUAGE=language)
    assert accepted in center.content.decode()
    assert revoke_label in center.content.decode()
    _revoke(client, document, language)
    center = client.get(reverse("consent_center"), HTTP_ACCEPT_LANGUAGE=language)
    assert revoked in center.content.decode()
    assert revoke_label not in center.content.decode()
    history = list(
        ConsentManifestation.objects.for_clinic(clinic.pk)
        .filter(subject=patient, document=document)
        .order_by("sequence")
    )
    assert [entry.decision for entry in history] == ["refused", "accepted", "revoked"]
    assert all(entry.purpose == "communication" for entry in history)
    assert all(entry.document_hash == document.publication_hash for entry in history)
    assert history[-1].revocation_reason_digest
    assert "Motivo original privado." not in center.content.decode()
    document.refresh_from_db()
    assert publication_payload(document) == original


@pytest.mark.parametrize(
    ("language", "decision_title", "revocation_title", "conflict"),
    (
        (
            "pt-br",
            "Revise sua decisão",
            "Não foi possível revogar a autorização",
            "Uma autorização aceita só pode ser retirada pelo fluxo de revogação.",
        ),
        (
            "en",
            "Review your decision",
            "The authorization could not be revoked",
            "An accepted authorization can only be withdrawn through revocation.",
        ),
        (
            "es",
            "Revise su decisión",
            "No se pudo revocar la autorización",
            "Una autorización aceptada solo puede retirarse mediante la revocación.",
        ),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_localized_form_and_service_errors_do_not_add_manifestations(
    client: Client,
    language: str,
    decision_title: str,
    revocation_title: str,
    conflict: str,
) -> None:
    clinic, _administrator, _patient, document = _context(client)
    invalid = client.post(
        reverse("consent_decide", args=(document.pk,)),
        {"request_id": str(uuid4()), "decision": "translated-accept"},
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert invalid.status_code == 400
    assert decision_title in invalid.content.decode()
    assert 'role="alert"' in invalid.content.decode()
    unavailable_revocation = client.post(
        reverse("consent_revoke", args=(document.pk,)),
        {
            "request_id": str(uuid4()),
            "reason": "Motivo original",
            "confirm_scope": "on",
        },
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert unavailable_revocation.status_code == 409
    missing_authorization = {
        "pt-br": "Não existe autorização vigente para revogar.",
        "en": "There is no active authorization to revoke.",
        "es": "No existe una autorización vigente para revocar.",
    }
    assert missing_authorization[language] in unavailable_revocation.content.decode()
    assert ConsentManifestation.objects.for_clinic(clinic.pk).count() == 0
    _decide(client, document, language, "accepted")
    refused = client.post(
        reverse("consent_decide", args=(document.pk,)),
        {"request_id": str(uuid4()), "decision": "refused"},
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert refused.status_code == 409
    assert conflict in refused.content.decode()
    invalid_revocation = client.post(
        reverse("consent_revoke", args=(document.pk,)),
        {"request_id": str(uuid4()), "reason": "Motivo original"},
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert invalid_revocation.status_code == 400
    assert revocation_title in invalid_revocation.content.decode()
    assert "Autorização &lt;original&gt;" in invalid_revocation.content.decode()
    assert ConsentManifestation.objects.for_clinic(clinic.pk).count() == 1


@pytest.mark.parametrize(
    ("language", "heading", "reference_error", "empty"),
    (
        (
            "pt-br",
            "Revogações aguardando tratamento",
            "Informe a referência do atendimento operacional.",
            "Não há revogações aguardando tratamento.",
        ),
        (
            "en",
            "Revocations awaiting processing",
            "Enter the operational service reference.",
            "There are no revocations awaiting processing.",
        ),
        (
            "es",
            "Revocaciones pendientes de tramitación",
            "Indique la referencia de la atención operativa.",
            "No hay revocaciones pendientes de tramitación.",
        ),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_revocation_queue_localizes_and_keeps_role_and_tenant_scope(
    client: Client, language: str, heading: str, reference_error: str, empty: str
) -> None:
    clinic, administrator, patient, document = _context(client)
    _decide(client, document, language, "accepted")
    _revoke(client, document, language)
    dispatch = ConsentRevocationDispatch.objects.for_clinic(clinic.pk).get(
        destination="clinic_operations"
    )
    process_revocation_dispatch(clinic_id=clinic.pk, dispatch_id=dispatch.pk)
    item = ConsentRevocationWorkItem.objects.for_clinic(clinic.pk).get(
        dispatch=dispatch
    )
    queue_url = reverse("consent_revocation_work_queue")
    ack_url = reverse("consent_revocation_work_acknowledge", args=(item.pk,))
    assert client.get(queue_url, HTTP_ACCEPT_LANGUAGE=language).status_code == 403
    assert client.post(ack_url, HTTP_ACCEPT_LANGUAGE=language).status_code == 403
    _login(client, administrator, clinic)
    queue = client.get(queue_url, HTTP_ACCEPT_LANGUAGE=language)
    assert queue.status_code == 200
    content = queue.content.decode()
    assert heading in content
    assert "Autorização &lt;original&gt;" in content
    assert "PAT-" in content
    assert str(patient.pk) not in content
    assert patient.email not in content
    assert "Motivo original privado." not in content
    invalid = client.post(ack_url, HTTP_ACCEPT_LANGUAGE=language)
    assert invalid.status_code == 400
    assert reference_error in invalid.content.decode()
    other_clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(
        clinic=other_clinic, user=administrator, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    _login(client, administrator, other_clinic)
    other_queue = client.get(queue_url, HTTP_ACCEPT_LANGUAGE=language)
    assert empty in other_queue.content.decode()
    assert str(dispatch.pk) not in other_queue.content.decode()
    assert (
        client.post(
            ack_url,
            {"acknowledgement_reference": "other-clinic"},
            HTTP_ACCEPT_LANGUAGE=language,
        ).status_code
        == 400
    )
    item.refresh_from_db()
    assert item.status == "open"
    _login(client, administrator, clinic)
    acknowledged = client.post(
        ack_url,
        {"acknowledgement_reference": "atendimento-original-001"},
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert acknowledged.status_code == 302
    item.refresh_from_db()
    assert item.status == "acknowledged"
    assert item.acknowledged_by_id == administrator.pk
    assert (
        empty in client.get(queue_url, HTTP_ACCEPT_LANGUAGE=language).content.decode()
    )


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_purpose_label_is_resolved_for_each_active_language() -> None:
    for language, label in (
        ("en", "Communication"),
        ("es", "Comunicación"),
        ("pt-br", "Comunicação"),
    ):
        with translation.override(language):
            assert purpose_label_pt_br("communication") == label
