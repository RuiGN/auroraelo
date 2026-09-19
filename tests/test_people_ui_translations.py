"""Focused localization contracts for the patient and professional UI."""

from __future__ import annotations

from datetime import date
from typing import TypedDict
from uuid import uuid4

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import User
from clinics.models import Clinic, ClinicMembership
from people.models import PatientProfile
from people.services import register_patient_profile, update_professional_profile
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


class PatientPayload(TypedDict):
    full_name: str
    social_name: str
    birth_date: date
    gender: str
    email: str
    phone: str
    language_code: str
    timezone_name: str
    accessibility_preferences: str
    address: dict[str, object]
    address_purpose: str
    emergency_contact: dict[str, object]
    emergency_contact_purpose: str


def _authenticated_admin(client: Client) -> tuple[Clinic, User]:
    clinic = ClinicFactory.create()
    administrator = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=administrator,
        role=ClinicMembership.Role.CLINIC_ADMIN,
    )
    client.force_login(administrator)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    return clinic, administrator


def _patient_payload(*, email: str = "marina@example.test") -> PatientPayload:
    return {
        "full_name": "Marina <Paciente> Exemplo",
        "social_name": "Mari",
        "birth_date": date(1994, 5, 18),
        "gender": PatientProfile.Gender.WOMAN,
        "email": email,
        "phone": "+55 (81) 99999-1234",
        "language_code": "pt-BR",
        "timezone_name": "America/Recife",
        "accessibility_preferences": "Manter instruções por escrito.",
        "address": {"line": "Rua da Aurora, 10", "city": "Recife", "state": "PE"},
        "address_purpose": "Contato administrativo original.",
        "emergency_contact": {"name": "João Original", "phone": "+5581888880000"},
        "emergency_contact_purpose": "Somente urgências.",
    }


@pytest.mark.parametrize(
    ("language", "title", "create_label", "linked_label"),
    (
        ("pt-br", "Pacientes", "Cadastrar paciente", "Conta vinculada"),
        ("en", "Patients", "Register patient", "Linked account"),
        ("es", "Pacientes", "Registrar paciente", "Cuenta vinculada"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_patient_list_translates_chrome_and_preserves_authored_data(
    client: Client,
    language: str,
    title: str,
    create_label: str,
    linked_label: str,
) -> None:
    clinic, administrator = _authenticated_admin(client)
    patient = register_patient_profile(
        clinic_id=clinic.pk,
        actor=administrator,
        request_id=uuid4(),
        **_patient_payload(),
    )
    patient.user = UserFactory.create()
    patient.save(update_fields=("user", "updated_at"))

    response = client.get(reverse("patient_list"), HTTP_ACCEPT_LANGUAGE=language)

    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    content = response.content.decode()
    assert f'id="patient-list-title">{title}</h1>' in content
    assert create_label in content
    assert linked_label in content
    if language == "en":
        assert '<th scope="col">Name</th>' in content
        assert '<th scope="col">First name</th>' not in content
    assert "Marina &lt;Paciente&gt; Exemplo" in content
    assert "Marina <Paciente> Exemplo" not in content
    assert str(clinic.pk) not in content


@pytest.mark.parametrize(
    ("language", "summary", "purpose_error"),
    (
        (
            "en",
            "Review the highlighted fields",
            "Enter the purpose for recording the address.",
        ),
        (
            "es",
            "Revise los campos indicados",
            "Indique la finalidad para registrar la dirección.",
        ),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_patient_form_localizes_errors_and_preserves_submitted_values(
    client: Client, language: str, summary: str, purpose_error: str
) -> None:
    _clinic, _administrator = _authenticated_admin(client)

    response = client.post(
        reverse("patient_create"),
        {
            "full_name": "Nome Digitado <original>",
            "social_name": "",
            "birth_date": "1990-04-12",
            "gender": "undisclosed",
            "email": "digitado@example.test",
            "phone": "",
            "language_code": "pt-BR",
            "timezone_name": "America/Recife",
            "accessibility_preferences": "Texto livre não traduzido.",
            "address_line": "Rua Digitada, 20",
            "address_city": "Recife",
            "address_state": "PE",
            "address_postal_code": "50000-000",
            "address_purpose": "",
            "emergency_contact_name": "",
            "emergency_contact_phone": "",
            "emergency_contact_purpose": "",
        },
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert summary in content
    assert purpose_error in content
    assert "data-focus-error-summary" in content
    assert 'href="#id_address_purpose"' in content
    assert 'value="Nome Digitado &lt;original&gt;"' in content
    assert "Texto livre não traduzido." in content


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_english_patient_submission_keeps_domain_values(client: Client) -> None:
    clinic, _administrator = _authenticated_admin(client)
    data = {
        "full_name": "Original Name",
        "social_name": "Chosen name",
        "birth_date": "1990-04-12",
        "gender": "non_binary",
        "email": "original@example.test",
        "phone": "+55 81 99999-0000",
        "language_code": "pt-BR",
        "timezone_name": "America/Recife",
        "accessibility_preferences": "Keep this original sentence.",
        "address_line": "",
        "address_city": "",
        "address_state": "",
        "address_postal_code": "",
        "address_purpose": "",
        "emergency_contact_name": "",
        "emergency_contact_phone": "",
        "emergency_contact_purpose": "",
    }

    response = client.post(reverse("patient_create"), data, HTTP_ACCEPT_LANGUAGE="en")

    assert response.status_code == 302
    patient = PatientProfile.infrastructure_objects.get(clinic_id=clinic.pk)
    assert patient.full_name == "Original Name"
    assert patient.social_name == "Chosen name"
    assert patient.gender == "non_binary"
    assert patient.language_code == "pt-BR"
    assert patient.timezone_name == "America/Recife"
    assert patient.accessibility_preferences == "Keep this original sentence."


@pytest.mark.parametrize(
    ("language", "identity_label", "gender_label", "back_label"),
    (
        ("en", "Identification", "Woman", "Back to patient list"),
        ("es", "Identificación", "Mujer", "Volver a la lista de pacientes"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_patient_detail_translates_labels_and_keeps_clinical_content(
    client: Client,
    language: str,
    identity_label: str,
    gender_label: str,
    back_label: str,
) -> None:
    clinic, administrator = _authenticated_admin(client)
    patient = register_patient_profile(
        clinic_id=clinic.pk,
        actor=administrator,
        request_id=uuid4(),
        **_patient_payload(),
    )

    response = client.get(
        reverse("patient_detail", args=(patient.pk,)),
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert identity_label in content
    assert gender_label in content
    assert back_label in content
    assert "Manter instruções por escrito." in content
    assert "Contato administrativo original." in content
    assert "João Original" in content


@pytest.mark.parametrize(
    ("language", "role_label", "status_label", "filters_label"),
    (
        ("en", "Therapist", "Active", "Professional filters"),
        ("es", "Terapeuta", "Activo", "Filtros de profesionales"),
    ),
)
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_professional_list_translates_display_labels_and_keeps_filter_codes(
    client: Client,
    language: str,
    role_label: str,
    status_label: str,
    filters_label: str,
) -> None:
    clinic, administrator = _authenticated_admin(client)
    professional = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic,
        user=professional,
        role=ClinicMembership.Role.THERAPIST,
        unit_name="Unidade Original",
    )
    update_professional_profile(
        clinic_id=clinic.pk,
        actor=administrator,
        user_id=professional.pk,
        full_name="Dra. Ana Original",
        social_name="Ana",
        professional_email="ana@example.test",
        professional_phone="",
        photo=None,
        biography="",
        accessibility_preferences="",
        category="psychologist",
        specialties=["adult_care"],
        council_name="CRP",
        council_number="00/000000",
        council_jurisdiction="PE",
        request_id=uuid4(),
    )

    response = client.get(
        reverse("professional_list"),
        {"status": "active", "role": "therapist", "specialty": "adult_care"},
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert f'aria-label="{filters_label}"' in content
    assert role_label in content
    assert status_label in content
    if language == "en":
        assert '<th scope="col">Name</th>' in content
    assert "Dra. Ana Original" in content
    assert "Unidade Original" in content
    assert "adult_care" in content
    assert 'option value="therapist" selected' in content
    assert 'option value="active" selected' in content
    assert (
        PatientProfile.infrastructure_objects.filter(clinic_id=clinic.pk).count() == 0
    )


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_unlinked_therapist_remains_denied_in_english(client: Client) -> None:
    clinic, administrator = _authenticated_admin(client)
    therapist = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist, role=ClinicMembership.Role.THERAPIST
    )
    patient = register_patient_profile(
        clinic_id=clinic.pk,
        actor=administrator,
        request_id=uuid4(),
        **_patient_payload(email="private@example.test"),
    )
    client.force_login(therapist)
    # A different authenticated user starts a new session without clinic state.
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()

    response = client.get(
        reverse("patient_detail", args=(patient.pk,)),
        HTTP_ACCEPT_LANGUAGE="en",
    )

    assert response.status_code == 403
    assert "Marina" not in response.content.decode()
