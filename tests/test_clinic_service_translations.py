"""Translated service errors must retain validation and tenant data."""

from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils.translation import override

from clinics.models import ClinicConfiguration
from clinics.services import update_clinic_modules, update_clinic_operations
from core.uploads import PrivateUploadPolicy, require_clean_malware_scan
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "timezone_error", "module_error"),
    [
        (
            "pt-br",
            "Selecione um fuso horário IANA válido.",
            "Ative os pré-requisitos antes dos módulos dependentes: finance",
        ),
        (
            "en",
            "Select a valid IANA time zone.",
            "Enable prerequisites before dependent modules: finance",
        ),
        (
            "es",
            "Seleccione una zona horaria IANA válida.",
            "Active los requisitos previos antes de los módulos dependientes: finance",
        ),
    ],
)
def test_localized_service_errors_preserve_configuration(
    language: str, timezone_error: str, module_error: str
) -> None:
    clinic = ClinicFactory.create()
    administrator = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=administrator, role="clinic_admin"
    )
    configuration = ClinicConfiguration.infrastructure_objects.create(
        clinic=clinic,
        display_name="Nome original <paciente>",
        enabled_modules=["patient_management"],
        timezone_name="America/Recife",
    )
    with override(language):
        with pytest.raises(ValidationError) as invalid_timezone:
            update_clinic_operations(
                clinic_id=clinic.pk,
                actor=administrator,
                timezone_name="Invalid/Zone",
                language_code="pt-BR",
                service_channels=["in_person"],
                weekly_hours={},
                out_of_hours_instructions="Texto original",
                request_id=uuid4(),
            )
        assert invalid_timezone.value.messages == [timezone_error]
        with pytest.raises(ValidationError) as missing_prerequisite:
            update_clinic_modules(
                clinic_id=clinic.pk,
                actor=administrator,
                enabled_modules=["billing"],
                request_id=uuid4(),
            )
        assert missing_prerequisite.value.messages == [module_error]
        assert missing_prerequisite.value.params == {"modules": "finance"}
    configuration.refresh_from_db()
    assert configuration.display_name == "Nome original <paciente>"
    assert configuration.enabled_modules == ["patient_management"]
    assert configuration.timezone_name == "America/Recife"


@pytest.mark.parametrize(
    ("language", "invalid_content", "scanner_unavailable"),
    [
        (
            "pt-br",
            "O conteúdo do arquivo não corresponde ao tipo informado.",
            "A varredura de segurança do arquivo está indisponível.",
        ),
        (
            "en",
            "The file content does not match the declared type.",
            "File security scanning is unavailable.",
        ),
        (
            "es",
            "El contenido del archivo no coincide con el tipo declarado.",
            "El análisis de seguridad del archivo no está disponible.",
        ),
    ],
)
@override_settings(PRIVATE_UPLOAD_MALWARE_SCAN_COMMAND=())
def test_localized_upload_errors_keep_signature_and_scanner_checks(
    language: str, invalid_content: str, scanner_unavailable: str
) -> None:
    upload = SimpleUploadedFile("fake.png", b"not-a-png", content_type="image/png")
    with override(language):
        with pytest.raises(ValidationError) as mismatch:
            PrivateUploadPolicy().validate(upload)
        assert mismatch.value.messages == [invalid_content]
        assert upload.tell() == 0
        with pytest.raises(ValidationError) as unavailable:
            require_clean_malware_scan(upload)
        assert unavailable.value.messages == [scanner_unavailable]
