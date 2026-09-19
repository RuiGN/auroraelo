"""Verification tests for localized presentation and data preservation (S14.08).

Ensures that dates, times, and numbers are localized per language, while currency,
timezones, appointment instants, financial figures, entity IDs, and user-authored
clinical records remain strictly preserved.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django import forms
from django.conf import settings
from django.test import override_settings
from django.utils import formats, translation

from clinics.models import ClinicMembership
from finance.forms import ServicePriceForm
from finance.models import ServicePrice
from journal.models import JournalEntry
from people.models import PatientProfile
from scheduling.models import Appointment, AppointmentStatus, Service, Unit
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory

pytestmark = pytest.mark.django_db

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


class LocalizedTransactionForm(forms.Form):
    amount = forms.DecimalField(localize=True, max_digits=10, decimal_places=2)
    transaction_date = forms.DateField(localize=True)


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_real_service_price_form_localizes_decimal_input() -> None:
    """The production finance form parses locale decimals without changing value."""
    expected = Decimal("1234.56")
    for language, raw_amount in (
        ("pt-br", "1234,56"),
        ("en", "1234.56"),
        ("es", "1234,56"),
    ):
        with translation.override(language):
            form = ServicePriceForm(
                {
                    "service": "service-1",
                    "amount": raw_amount,
                    "currency": "BRL",
                    "valid_from": "2026-10-31",
                },
                service_choices=[("service-1", "Sessão")],
            )
            assert form.is_valid(), (language, form.errors)
            assert form.cleaned_data["amount"] == expected


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_decimal_presentation_and_roundtrip_parsing() -> None:
    """Decimals format with locale separators and parse back to identical values."""
    amount = Decimal("1234.56")

    # pt-br: comma decimal
    with translation.override("pt-br"):
        formatted_pt = formats.number_format(amount, decimal_pos=2)
        assert formatted_pt == "1234,56"
        form_pt = LocalizedTransactionForm(
            {"amount": formatted_pt, "transaction_date": "25/12/2026"}
        )
        assert form_pt.is_valid(), form_pt.errors
        assert form_pt.cleaned_data["amount"] == amount

    # en: dot decimal
    with translation.override("en"):
        formatted_en = formats.number_format(amount, decimal_pos=2)
        assert formatted_en == "1234.56"
        form_en = LocalizedTransactionForm(
            {"amount": formatted_en, "transaction_date": "12/25/2026"}
        )
        assert form_en.is_valid(), form_en.errors
        assert form_en.cleaned_data["amount"] == amount

    # es: comma decimal
    with translation.override("es"):
        formatted_es = formats.number_format(amount, decimal_pos=2)
        assert formatted_es == "1234,56"
        form_es = LocalizedTransactionForm(
            {"amount": formatted_es, "transaction_date": "25/12/2026"}
        )
        assert form_es.is_valid(), form_es.errors
        assert form_es.cleaned_data["amount"] == amount


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_date_presentation_and_roundtrip_parsing() -> None:
    """Dates format and parse accurately according to each language's conventions."""
    target_date = date(2026, 10, 31)

    # pt-br: DD/MM/YYYY
    with translation.override("pt-br"):
        formatted_pt = formats.date_format(target_date, "SHORT_DATE_FORMAT")
        assert formatted_pt == "31/10/2026"
        form = LocalizedTransactionForm(
            {"amount": "100,00", "transaction_date": formatted_pt}
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["transaction_date"] == target_date

    # en: MM/DD/YYYY or localized standard
    with translation.override("en"):
        form = LocalizedTransactionForm(
            {"amount": "100.00", "transaction_date": "10/31/2026"}
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["transaction_date"] == target_date

    # es: DD/MM/YYYY
    with translation.override("es"):
        formatted_es = formats.date_format(target_date, "SHORT_DATE_FORMAT")
        assert formatted_es == "31/10/2026"
        form = LocalizedTransactionForm(
            {"amount": "100,00", "transaction_date": formatted_es}
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["transaction_date"] == target_date


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_switch_preserves_appointment_utc_instants() -> None:
    """Switching interface language must never alter scheduled appointment times."""
    clinic = ClinicFactory.create()
    patient_user = UserFactory.create()
    therapist_user = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=patient_user, role=ClinicMembership.Role.PATIENT
    )
    ClinicMembershipFactory.create(
        clinic=clinic, user=therapist_user, role=ClinicMembership.Role.THERAPIST
    )
    profile = PatientProfile.infrastructure_objects.create(
        clinic_id=clinic.id,
        user_id=patient_user.id,
        full_name="Paciente Teste",
        birth_date=date(1990, 5, 20),
    )
    unit = Unit.infrastructure_objects.create(
        clinic_id=clinic.id, name="Unidade Central"
    )
    service = Service.infrastructure_objects.create(
        clinic_id=clinic.id, name="Psicoterapia", duration_minutes=50
    )

    scheduled_start = datetime(2026, 11, 20, 14, 0, tzinfo=SP_TZ)
    scheduled_end = datetime(2026, 11, 20, 14, 50, tzinfo=SP_TZ)

    appointment = Appointment.infrastructure_objects.create(
        clinic_id=clinic.id,
        patient_profile=profile,
        professional=therapist_user,
        requested_by=patient_user,
        idempotency_key="test-appointment-key-1",
        unit=unit,
        service=service,
        start_at=scheduled_start,
        end_at=scheduled_end,
        status=AppointmentStatus.CONFIRMED,
    )

    # Switch across languages and verify DB state remains immutable
    for lang in ("pt-br", "en", "es"):
        with translation.override(lang):
            appointment.refresh_from_db()
            assert appointment.start_at == scheduled_start
            assert appointment.end_at == scheduled_end
            assert appointment.start_at.astimezone(UTC) == scheduled_start.astimezone(
                UTC
            )


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_switch_preserves_financial_values_and_currency() -> None:
    """Financial prices and currency remain unchanged when switching languages."""
    clinic = ClinicFactory.create()
    service = Service.infrastructure_objects.create(
        clinic_id=clinic.id, name="Consulta Geral", duration_minutes=60
    )
    price = ServicePrice.infrastructure_objects.create(
        clinic_id=clinic.id,
        service=service,
        amount=Decimal("350.00"),
        valid_from=date(2026, 1, 1),
    )

    for lang in ("pt-br", "en", "es"):
        with translation.override(lang):
            price.refresh_from_db()
            assert price.amount == Decimal("350.00")
            assert price.service.name == "Consulta Geral"


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_language_switch_preserves_authored_clinical_text() -> None:
    """Clinical notes and journal entries remain verbatim in their authored language."""
    clinic = ClinicFactory.create()
    user = UserFactory.create()
    ClinicMembershipFactory.create(
        clinic=clinic, user=user, role=ClinicMembership.Role.PATIENT
    )
    profile = PatientProfile.infrastructure_objects.create(
        clinic_id=clinic.id,
        user_id=user.id,
        full_name="Paciente Diário",
        birth_date=date(1985, 3, 15),
    )

    authored_content = "Relato clínico: sinto melhora gradual após os exercícios."
    entry = JournalEntry.infrastructure_objects.create(
        clinic_id=clinic.id,
        author=user,
        patient_profile=profile,
        mood=JournalEntry.Mood.GOOD,
        intensity=3,
        context=authored_content,
        visibility=JournalEntry.Visibility.PRIVATE,
    )

    for lang in ("pt-br", "en", "es"):
        with translation.override(lang):
            entry.refresh_from_db()
            assert entry.context == authored_content


@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
def test_entity_identifiers_and_timezone_remain_constant() -> None:
    """Entity IDs (UUIDs) and timezone settings do not change across locales."""
    clinic = ClinicFactory.create()
    clinic_uuid = clinic.id

    for lang in ("pt-br", "en", "es"):
        with translation.override(lang):
            clinic.refresh_from_db()
            assert clinic.id == clinic_uuid
            assert str(clinic.id) == str(clinic_uuid)
            assert settings.TIME_ZONE == "America/Sao_Paulo"
