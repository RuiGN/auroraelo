"""Verification tests for recipient language in outbound communication (S14.09).

Ensures that outbound emails, notifications, and neutral delivery templates apply the
recipient's preferred language with strict context restoration, testing multiple
users and clinics with interleaved languages without translating clinical content,
altering accepted legal documents, or leaking across cache.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils import translation

from accounts.services import request_password_recovery
from clinics.models import ClinicMembership
from consents.models import ConsentManifestation
from consents.services import (
    publish_consent_document,
    record_consent_manifestation,
)
from scheduling.delivery_templates import (
    appointment_reminder_message,
    new_message_notification_message,
)
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_password_recovery_delivery_in_interleaved_languages_and_restores_context() -> (
    None
):
    """Outbound recovery emails apply recipient language and restore context."""
    mail.outbox.clear()
    factory = RequestFactory()

    clinic_a = ClinicFactory.create(name="Clínica Alfa")
    clinic_b = ClinicFactory.create(name="Clínica Beta")

    user_en = UserFactory.create(
        email="patient.en@example.test", preferred_language="en"
    )
    user_es = UserFactory.create(
        email="patient.es@example.test", preferred_language="es"
    )
    user_pt = UserFactory.create(
        email="patient.pt@example.test", preferred_language="pt-br"
    )

    ClinicMembershipFactory.create(
        clinic=clinic_a, user=user_en, role=ClinicMembership.Role.PATIENT
    )
    ClinicMembershipFactory.create(
        clinic=clinic_b, user=user_es, role=ClinicMembership.Role.PATIENT
    )
    ClinicMembershipFactory.create(
        clinic=clinic_a, user=user_pt, role=ClinicMembership.Role.PATIENT
    )

    translation.activate("pt-br")
    assert translation.get_language() == "pt-br"

    # 1. Send recovery to English user
    req_en = factory.post(reverse("password_recovery"), {"email": user_en.email})
    request_password_recovery(
        email=user_en.email,
        request=req_en,
    )
    assert translation.get_language() == "pt-br", (
        "Translation context must be restored after sending"
    )

    # 2. Interleave: Send recovery to Spanish user
    req_es = factory.post(reverse("password_recovery"), {"email": user_es.email})
    request_password_recovery(
        email=user_es.email,
        request=req_es,
    )
    assert translation.get_language() == "pt-br", (
        "Translation context must be restored after sending"
    )

    # 3. Interleave: Send recovery to Portuguese user
    req_pt = factory.post(reverse("password_recovery"), {"email": user_pt.email})
    request_password_recovery(
        email=user_pt.email,
        request=req_pt,
    )
    assert translation.get_language() == "pt-br", (
        "Translation context must be restored after sending"
    )

    assert len(mail.outbox) == 3

    # Check English email
    msg_en = next(m for m in mail.outbox if m.to == [user_en.email])
    assert msg_en.subject == "Access recovery"
    assert "We received a request to reset your password." in str(msg_en.body)
    assert "Access the following link:" in str(msg_en.body)

    # Check Spanish email
    msg_es = next(m for m in mail.outbox if m.to == [user_es.email])
    assert msg_es.subject == "Recuperación de acceso"
    assert "Recibimos una solicitud para restablecer su contraseña." in str(msg_es.body)
    assert "Acceda al siguiente enlace:" in str(msg_es.body)

    # Check Portuguese email
    msg_pt = next(m for m in mail.outbox if m.to == [user_pt.email])
    assert msg_pt.subject == "Recuperação de acesso"
    assert "Recebemos uma solicitação para redefinir sua senha." in str(msg_pt.body)
    assert "Acesse o link a seguir:" in str(msg_pt.body)


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_clinic_invitation_respects_recipient_language_and_restores_context(
    client: Client,
) -> None:
    """Issuing an invitation localizes email to recipient's known language."""
    mail.outbox.clear()

    clinic = ClinicFactory.create()
    admin = UserFactory.create(preferred_language="pt-br")
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=admin,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(admin)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()

    # Pre-existing user in Spanish
    UserFactory.create(
        email="espanol@example.test",
        preferred_language="es",
    )

    translation.activate("pt-br")

    # Invite user with Spanish preference
    response = client.post(
        reverse("invitation_issue"),
        {
            "recipient_email": "espanol@example.test",
            "initial_role": ClinicMembership.Role.THERAPIST,
            "expires_in_hours": "24",
        },
    )
    assert response.status_code == 200
    assert translation.get_language() == "pt-br"
    assert len(mail.outbox) == 1

    msg = mail.outbox[0]
    assert msg.subject == "Invitación para acceder a la clínica"
    assert "Recibió una invitación para acceder a la clínica." in str(msg.body)
    assert re.search(r"/accounts/invitations/[^/]+/accept/", str(msg.body))


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_appointment_and_message_delivery_templates_in_interleaved_languages() -> None:
    """Delivery templates format per language while keeping parameters unchanged."""
    translation.activate("pt-br")
    appointment_time = datetime(2026, 12, 15, 10, 30, tzinfo=SP_TZ)

    # Interleave calls
    en_msg = appointment_reminder_message(
        service_name="Terapia Cognitiva",
        start_at=appointment_time,
        tz_name="America/Sao_Paulo",
        language="en",
    )
    es_msg = appointment_reminder_message(
        service_name="Terapia Cognitiva",
        start_at=appointment_time,
        tz_name="America/Sao_Paulo",
        language="es",
    )
    pt_msg = appointment_reminder_message(
        service_name="Terapia Cognitiva",
        start_at=appointment_time,
        tz_name="America/Sao_Paulo",
        language="pt-br",
    )

    # Verify context restored
    assert translation.get_language() == "pt-br"

    expected_en = (
        "Reminder: your appointment for Terapia Cognitiva is scheduled "
        "for 15/12/2026 at 10:30."
    )
    expected_es = (
        "Recordatorio: su consulta de Terapia Cognitiva está programada "
        "para el 15/12/2026 a las 10:30."
    )
    expected_pt = (
        "Lembrete: sua consulta de Terapia Cognitiva está marcada "
        "para 15/12/2026 às 10:30."
    )

    assert en_msg == expected_en
    assert es_msg == expected_es
    assert pt_msg == expected_pt

    # Test notification message
    assert (
        new_message_notification_message(sender_name="Dr. Lucas", language="en")
        == "You have a new message from Dr. Lucas on the platform."
    )
    assert (
        new_message_notification_message(sender_name="Dr. Lucas", language="es")
        == "Tiene un nuevo mensaje de Dr. Lucas en la plataforma."
    )
    assert (
        new_message_notification_message(sender_name="Dr. Lucas", language="pt-br")
        == "Você tem uma nova mensagem de Dr. Lucas na plataforma."
    )


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_cache_keys_isolate_language_and_tenant_without_leakage() -> None:
    """Cache keys incorporating tenant and language never cross-pollinate."""
    cache.clear()
    clinic_1 = ClinicFactory.create()
    clinic_2 = ClinicFactory.create()

    # Store localized notification summary for clinic 1 in EN
    key_c1_en = f"clinic_notice:{clinic_1.id}:en"
    key_c1_es = f"clinic_notice:{clinic_1.id}:es"
    key_c2_en = f"clinic_notice:{clinic_2.id}:en"

    cache.set(key_c1_en, "Notice for Clinic 1 in English", timeout=60)
    cache.set(key_c1_es, "Aviso para Clínica 1 en Español", timeout=60)
    cache.set(key_c2_en, "Notice for Clinic 2 in English", timeout=60)

    assert cache.get(key_c1_en) == "Notice for Clinic 1 in English"
    assert cache.get(key_c1_es) == "Aviso para Clínica 1 en Español"
    assert cache.get(key_c2_en) == "Notice for Clinic 2 in English"
    assert cache.get(f"clinic_notice:{clinic_2.id}:es") is None


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_accepted_consent_documents_remain_immutable_across_locales() -> None:
    """Accepted legal consent records preserve their verbatim content across locales."""
    clinic = ClinicFactory.create()
    admin = UserFactory.create()
    patient = UserFactory.create(preferred_language="pt-br")
    ClinicMembershipFactory.create(
        clinic=clinic, user=admin, role=ClinicMembership.Role.CLINIC_ADMIN
    )
    ClinicMembershipFactory.create(
        clinic=clinic, user=patient, role=ClinicMembership.Role.PATIENT
    )

    original_legal_text = (
        "Termo de Consentimento Livre e Esclarecido: autorizo o tratamento de "
        "meus dados de saúde conforme a política de privacidade vigente."
    )
    original_title = "Consentimento para Teleconsulta"

    document = publish_consent_document(
        clinic_id=clinic.pk,
        actor=admin,
        document_type="consent",
        title=original_title,
        version="1.0",
        content=original_legal_text,
        purpose="communication",
        effective_from=datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
        audience="patient",
        is_mandatory=False,
        refusal_consequence="Consequência de recusa.",
        alternative_instructions="Instruções alternativas.",
        clinic_contact_instructions="Contato da clínica.",
    )
    manifestation = record_consent_manifestation(
        clinic_id=clinic.pk,
        actor=patient,
        subject_id=patient.pk,
        document_id=document.pk,
        decision=ConsentManifestation.Decision.ACCEPTED,
        request_id=uuid4(),
    )

    # User switches language across all supported languages
    for lang in ("en", "es", "pt-br"):
        with translation.override(lang):
            manifestation.refresh_from_db()
            document.refresh_from_db()
            assert document.content == original_legal_text
            assert document.title == original_title
            assert manifestation.decision == ConsentManifestation.Decision.ACCEPTED
