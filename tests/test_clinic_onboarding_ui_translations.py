"""Clinic and onboarding UI translation contracts."""

from __future__ import annotations

from collections.abc import Iterable
from types import SimpleNamespace
from typing import cast

import pytest
from django import forms
from django.template.loader import render_to_string
from django.utils import translation

from clinics.forms import ClinicIdentityForm, ClinicModulesForm, ClinicOperationsForm
from clinics.views import _domain_presentations, _module_presentations
from onboarding.views import _STEP_LABELS, _STEPS

LAUNCH_LANGUAGES = (
    ("pt-br", "Português (Brasil)"),
    ("en", "English"),
    ("es", "Español"),
)


@pytest.mark.parametrize(
    ("language", "identity_label", "module_label"),
    (
        ("pt-br", "Razão social", "Registros clínicos"),
        ("en", "Legal name", "Clinical records"),
        ("es", "Razón social", "Registros clínicos"),
    ),
)
def test_form_labels_translate_without_changing_submitted_codes(
    language: str,
    identity_label: str,
    module_label: str,
) -> None:
    with translation.override(language):
        identity = ClinicIdentityForm()
        modules = ClinicModulesForm()
        module_field = modules.fields["enabled_modules"]
        assert isinstance(module_field, forms.ChoiceField)
        module_choices = list(
            cast(
                Iterable[tuple[str, object]],
                module_field.choices,
            )
        )

        assert str(identity.fields["legal_name"].label) == identity_label
        assert ("clinical_records", module_label) in [
            (code, str(label)) for code, label in module_choices
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
