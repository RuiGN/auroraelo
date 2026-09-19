"""Shared presentation must preserve Django form and submission contracts."""

from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

import pytest
from django import forms
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

from core.templatetags.accessible_forms import accessible_widget, error_target_id
from tests.factories import ClinicFactory, ClinicMembershipFactory, UserFactory


class Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))


def _elements(html: str) -> list[tuple[str, dict[str, str | None]]]:
    parser = Elements()
    parser.feed(html)
    return parser.elements


def test_date_time_widget_retains_time_and_custom_format() -> None:
    class AppointmentForm(forms.Form):
        when = forms.DateTimeField(
            widget=forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            )
        )

    form = AppointmentForm(initial={"when": datetime(2026, 9, 8, 14, 35)})
    element = _elements(accessible_widget(form["when"]))[0][1]
    assert element["type"] == "datetime-local"
    assert element["value"] == "2026-09-08T14:35"


@pytest.mark.parametrize(
    "base_widget", [forms.RadioSelect, forms.CheckboxSelectMultiple]
)
def test_custom_choice_widget_rendering_hook_survives(base_widget: Any) -> None:
    class DomainChoices(base_widget):  # type: ignore[misc]
        def create_option(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            option = super().create_option(*args, **kwargs)
            option["attrs"]["data-domain-option"] = "preserved"
            return dict(option)

    form = forms.Form()
    form.fields["choice"] = forms.ChoiceField(
        choices=(("email", "E-mail"),), widget=DomainChoices
    )
    html = accessible_widget(form["choice"])
    assert 'data-domain-option="preserved"' in html


def test_custom_date_widget_keeps_format_and_rendering_hook() -> None:
    class DomainDate(forms.DateInput):
        def get_context(self, name: str, value: Any, attrs: Any) -> dict[str, Any]:
            context = super().get_context(name, value, attrs)
            context["widget"]["attrs"]["data-domain-date"] = "preserved"
            return context

    form = forms.Form(initial={"day": datetime(2026, 9, 8)})
    form.fields["day"] = forms.DateField(widget=DomainDate(format="%d/%m/%Y"))
    html = accessible_widget(form["day"])
    assert 'value="08/09/2026"' in html
    assert 'data-domain-date="preserved"' in html


def test_widget_preserves_existing_accessibility_and_behavior_attributes() -> None:
    class ExampleForm(forms.Form):
        name = forms.CharField(
            help_text="Ajuda",
            widget=forms.TextInput(
                attrs={
                    "class": "custom-control-hook",
                    "aria-describedby": "external-help",
                    "data-custom": "keep",
                    "readonly": True,
                }
            ),
        )

    form = ExampleForm(data={})
    element = _elements(accessible_widget(form["name"]))[0][1]
    assert {"custom-control-hook", "form-control"} <= set(str(element["class"]).split())
    assert set(str(element["aria-describedby"]).split()) == {
        "external-help",
        "id_name_helptext",
        "id_name_error_0",
    }
    assert element["data-custom"] == "keep"
    assert "readonly" in element
    assert form.fields["name"].widget.attrs["class"] == "custom-control-hook"


def test_hidden_date_and_grouped_checkbox_render_without_inaccessible_labels() -> None:
    class ExampleForm(forms.Form):
        date_token = forms.DateField(widget=forms.HiddenInput)
        choices = forms.MultipleChoiceField(
            label="Canais",
            choices=(("email", "E-mail"),),
            widget=forms.CheckboxSelectMultiple,
        )

    form = ExampleForm(data={})
    html = render_to_string(
        "components/form.html",
        {"form": form, "form_id": "example", "submit_label": "Salvar"},
    )
    elements = _elements(html)
    hidden = next(
        a for t, a in elements if t == "input" and a.get("name") == "date_token"
    )
    assert hidden["type"] == "hidden"
    assert not any(
        t == "label" and a.get("for") == "id_date_token" for t, a in elements
    )
    assert any(t == "fieldset" for t, a in elements)
    assert error_target_id(form["choices"]) == "id_choices_0"
    assert not any(t == "a" and a.get("href") == "#id_date_token" for t, a in elements)


@pytest.mark.django_db
def test_component_catalog_posts_with_real_csrf_validation() -> None:
    user = UserFactory.create(is_staff=True)
    clinic = ClinicFactory.create()
    ClinicMembershipFactory.create(user=user, clinic=clinic, role="clinic_admin")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    session = client.session
    session["active_clinic_id"] = str(clinic.pk)
    session.save()
    page = client.get(reverse("design_system_reference"))
    # Other independent POST forms (language choice) have their own CSRF token.
    form_html = re.search(
        r'<form id="reference-form"[^>]*>.*?</form>',
        page.content.decode(),
        flags=re.DOTALL,
    )
    assert form_html is not None
    tokens = [
        a["value"]
        for t, a in _elements(form_html.group())
        if t == "input" and a.get("name") == "csrfmiddlewaretoken"
    ]
    assert len(tokens) == 1
    response = client.post(
        reverse("design_system_reference"),
        {
            "csrfmiddlewaretoken": tokens[0],
            "display_name": "Unidade de validação",
            "category": "individual",
            "start_date": "2026-09-08",
            "contact_method": "email",
        },
    )
    assert response.status_code == 200
    assert "Exemplo validado pelo servidor" in response.content.decode()
