"""Clinic and onboarding UI translation contracts."""

from __future__ import annotations

from collections.abc import Iterable
from types import SimpleNamespace
from typing import cast

import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import translation

from clinics.forms import ClinicIdentityForm, ClinicModulesForm, ClinicOperationsForm
from clinics.views import _domain_presentations, _module_presentations
from onboarding.forms import PatientPreferencesForm
from onboarding.models import PatientOnboarding
from onboarding.views import _STEP_LABELS, _STEPS
from tests.factories import ClinicFactory
from tests.test_onboarding import _linked_patient

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


@pytest.mark.parametrize(
    ("language", "identity_label", "module_label", "contact_label"),
    (
        ("pt-br", "Razão social", "Registros clínicos", "Telefone"),
        ("en", "Legal name", "Clinical records", "Phone"),
        ("es", "Razón social", "Registros clínicos", "Teléfono"),
    ),
)
def test_form_labels_translate_without_changing_submitted_codes(
    language: str,
    identity_label: str,
    module_label: str,
    contact_label: str,
) -> None:
    with translation.override(language):
        identity = ClinicIdentityForm()
        modules = ClinicModulesForm()
        preferences = PatientPreferencesForm()
        module_field = modules.fields["enabled_modules"]
        contact_field = preferences.fields["contact_preferences"]
        assert isinstance(module_field, forms.ChoiceField)
        assert isinstance(contact_field, forms.ChoiceField)
        module_choices = list(
            cast(
                Iterable[tuple[str, object]],
                module_field.choices,
            )
        )
        contact_choices = list(
            cast(
                Iterable[tuple[str, object]],
                contact_field.choices,
            )
        )

        assert str(identity.fields["legal_name"].label) == identity_label
        assert ("clinical_records", module_label) in [
            (code, str(label)) for code, label in module_choices
        ]
        assert ("phone", contact_label) in [
            (code, str(label)) for code, label in contact_choices
        ]


@pytest.mark.parametrize(
    ("language", "start_label", "end_label"),
    (
        ("pt-br", "Segunda-feira: início", "Segunda-feira: fim"),
        ("en", "Monday: start", "Monday: end"),
        ("es", "Lunes: inicio", "Lunes: fin"),
    ),
)
def test_weekday_time_labels_interpolate_the_translated_name(
    language: str, start_label: str, end_label: str
) -> None:
    with translation.override(language):
        form = ClinicOperationsForm()

        assert form.fields["monday_start"].label == start_label
        assert form.fields["monday_end"].label == end_label


@pytest.mark.parametrize(
    ("language", "expected_steps", "module_label", "statuses"),
    (
        (
            "pt-br",
            ("Objetivos", "Preferências", "Termos", "Concluído"),
            "Financeiro",
            ("Verificado", "Renovação pendente"),
        ),
        (
            "en",
            ("Goals", "Preferences", "Terms", "Complete"),
            "Finance",
            ("Verified", "Renewal due"),
        ),
        (
            "es",
            ("Objetivos", "Preferencias", "Términos", "Completado"),
            "Finanzas",
            ("Verificado", "Renovación pendiente"),
        ),
    ),
)
def test_presentation_labels_translate_and_retain_stable_codes(
    language: str,
    expected_steps: tuple[str, ...],
    module_label: str,
    statuses: tuple[str, str],
) -> None:
    domain = SimpleNamespace(
        domain="clinic.example.test", status="verified", tls_status="renewal_due"
    )
    with translation.override(language):
        step_presentations = tuple(
            {"code": code, "label": _STEP_LABELS[code]} for code in _STEPS
        )
        modules = _module_presentations(("finance",))
        domains = _domain_presentations((domain,))

        assert tuple(item["code"] for item in step_presentations) == _STEPS
        assert (
            tuple(str(item["label"]) for item in step_presentations) == expected_steps
        )
        assert modules[0]["code"] == "finance"
        assert str(modules[0]["label"]) == module_label
        assert domains[0]["domain"] is domain
        assert str(domains[0]["status_label"]) == statuses[0]
        assert str(domains[0]["tls_status_label"]) == statuses[1]


@pytest.mark.parametrize(
    ("language", "heading"),
    (
        ("pt-br", "Objetivos pessoais"),
        ("en", "Personal goals"),
        ("es", "Objetivos personales"),
    ),
)
def test_patient_onboarding_template_translates_and_escapes_user_data(
    language: str, heading: str
) -> None:
    malicious_goal = '<img src=x onerror="alert(1)">'
    goals_form = forms.Form()
    goals_form.fields["goals"] = forms.CharField(
        initial=malicious_goal, widget=forms.Textarea
    )
    with translation.override(language):
        html = render_to_string(
            "onboarding/patient_onboarding.html",
            {
                "form": goals_form,
                "step": "goals",
                "steps": _STEPS,
                "step_presentations": tuple(
                    {"code": code, "label": _STEP_LABELS[code]} for code in _STEPS
                ),
                "layout_template": "layouts/vertical.html",
                "user": {"email": "synthetic@example.test"},
            },
        )

    assert heading in html
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in html
    assert '<img src=x onerror="alert(1)">' not in html


@pytest.mark.parametrize(
    ("language", "heading"),
    (
        ("pt-br", "Trocar clínica ativa?"),
        ("en", "Switch active clinic?"),
        ("es", "¿Cambiar la clínica activa?"),
    ),
)
def test_clinic_switch_template_translates_and_escapes_clinic_names(
    language: str, heading: str
) -> None:
    malicious_name = '<script>alert("clinic")</script>'
    with translation.override(language):
        html = render_to_string(
            "clinics/confirm_switch.html",
            {
                "current_clinic": SimpleNamespace(name=malicious_name),
                "target_clinic": SimpleNamespace(
                    name="Target clinic", pk="original-clinic-id"
                ),
                "next_url": "/workspace/?return=original",
                "user": {"email": "synthetic@example.test"},
            },
        )

    assert heading in html
    assert "&lt;script&gt;alert(&quot;" in html
    assert "<script>alert" not in html
    assert 'value="original-clinic-id"' in html
    assert 'value="/workspace/?return=original"' in html


@pytest.mark.django_db
@override_settings(LANGUAGES=LAUNCH_LANGUAGES)
@pytest.mark.parametrize("existing_record", (False, True))
@pytest.mark.parametrize(
    ("language", "heading"),
    (
        ("pt-br", "Preferências de contato e lembretes"),
        ("en", "Contact and reminder preferences"),
        ("es", "Preferencias de contacto y recordatorios"),
    ),
)
def test_invalid_preferences_post_keeps_bound_translated_form_without_writing(
    client: Client, language: str, heading: str, existing_record: bool
) -> None:
    clinic = ClinicFactory.create()
    user, profile = _linked_patient(clinic)
    previous = None
    if existing_record:
        previous = PatientOnboarding.infrastructure_objects.create(
            clinic=clinic,
            patient_profile=profile,
            goals=["Meu objetivo original"],
            contact_preferences={"phone": True},
            reminder_windows={"evening": True},
            current_step=PatientOnboarding.Step.PREFERENCES,
        )
        previous_values = (
            PatientOnboarding.infrastructure_objects.filter(pk=previous.pk)
            .values()
            .get()
        )
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()

    response = client.post(
        f"{reverse('patient_onboarding')}?step=goals",
        {
            "step": "preferences",
            "contact_preferences": ["email", "carrier_pigeon"],
            "reminder_windows": ["morning"],
        },
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 200
    assert response.headers["Content-Language"] == language
    content = response.content.decode()
    assert heading in content
    assert 'name="step" value="preferences"' in content
    assert "carrier_pigeon" in content
    assert 'aria-invalid="true"' in content
    returned_form = response.context["form"]
    assert isinstance(returned_form, PatientPreferencesForm)
    assert returned_form.is_bound
    assert returned_form["contact_preferences"].value() == [
        "email",
        "carrier_pigeon",
    ]
    assert returned_form["reminder_windows"].value() == ["morning"]
    if previous is None:
        assert not PatientOnboarding.infrastructure_objects.filter(
            clinic_id=clinic.pk, patient_profile=profile
        ).exists()
    else:
        assert (
            PatientOnboarding.infrastructure_objects.filter(pk=previous.pk)
            .values()
            .get()
        ) == previous_values
