"""Presentation must enhance fields without changing their data contract."""

from datetime import date, time

import pytest
from django import forms
from django.template.loader import render_to_string
from django.utils.translation import override

from clinics.forms import ClinicIdentityForm
from core.templatetags.accessible_forms import accessible_widget, field_icon, field_span


def bound(field: forms.Field, name: str = "example") -> forms.BoundField:
    form = forms.Form()
    form.fields[name] = field
    return form[name]


@pytest.mark.parametrize(
    "field, icon",
    [
        (forms.CharField(), "feather-edit-2"),
        (forms.CharField(widget=forms.PasswordInput), "feather-lock"),
        (forms.URLField(), "feather-link"),
        (forms.DateField(), "feather-calendar"),
        (forms.TimeField(), "feather-clock"),
        (forms.ChoiceField(choices=[("a", "A")]), "feather-list"),
        (forms.CharField(widget=forms.Textarea), "feather-align-left"),
    ],
)
def test_textual_controls_receive_decorative_icon(
    field: forms.Field, icon: str
) -> None:
    bound_field = bound(field)
    assert field_icon(bound_field) == icon
    html = render_to_string("components/duralux_field.html", {"field": bound_field})
    assert f'class="{icon}"' in html
    assert 'aria-hidden="true"' in html
    assert 'for="id_example"' in html


@pytest.mark.parametrize(
    "widget",
    [
        forms.HiddenInput(),
        forms.CheckboxInput(),
        forms.RadioSelect(),
        forms.CheckboxSelectMultiple(),
        forms.FileInput(),
        forms.TextInput(attrs={"type": "color"}),
        forms.NumberInput(attrs={"type": "range"}),
    ],
)
def test_non_text_controls_keep_native_affordances(widget: forms.Widget) -> None:
    field = bound(forms.CharField(widget=widget))
    assert field_icon(field) == ""
    assert "placeholder=" not in accessible_widget(field)


def test_general_postal_codes_are_not_forced_into_brazilian_cep() -> None:
    field = ClinicIdentityForm()["postal_code"]
    assert 'data-mask="cep"' not in accessible_widget(field)


def test_brazilian_address_cep_has_explicit_mask() -> None:
    html = accessible_widget(bound(forms.CharField(), "address_postal_code"))
    assert 'data-mask="cep"' in html
    assert 'inputmode="numeric"' in html


@pytest.mark.parametrize(
    "field", [forms.DateTimeField(), forms.TimeField(), forms.CharField(max_length=32)]
)
def test_longer_short_values_are_not_squeezed_into_quarter_column(
    field: forms.Field,
) -> None:
    assert (
        field_span(
            bound(field, "phone" if isinstance(field, forms.CharField) else "starts_at")
        )
        == "field-span--md"
    )


def test_time_input_uses_native_picker_and_canonical_initial() -> None:
    field = bound(forms.TimeField(initial=time(9, 30)))
    html = accessible_widget(field)
    assert 'type="time"' in html
    assert 'value="09:30:00"' in html


def test_explicit_presentation_and_form_value_are_preserved() -> None:
    field = bound(
        forms.CharField(
            widget=forms.TextInput(
                attrs={
                    "placeholder": "Existing hint",
                    "autocomplete": "off",
                    "class": "domain-class",
                }
            )
        ),
        "email",
    )
    html = accessible_widget(field)
    assert 'placeholder="Existing hint"' in html
    assert 'autocomplete="off"' in html
    assert 'class="domain-class form-control"' in html
    assert field.field.widget.attrs["class"] == "domain-class"


def test_generic_text_hint_is_translatable_label_not_an_example_value() -> None:
    html = accessible_widget(bound(forms.CharField(label="Justificativa")))
    assert 'placeholder="Justificativa"' in html


@pytest.mark.parametrize("language, hint", [("pt-br", "0,00"), ("en", "0.00")])
def test_decimal_hint_matches_active_locale(language: str, hint: str) -> None:
    with override(language):
        html = accessible_widget(bound(forms.DecimalField(localize=True), "amount"))
    assert f'placeholder="{hint}"' in html
    assert 'inputmode="decimal"' in html


def test_date_value_remains_iso_and_has_no_text_mask() -> None:
    html = accessible_widget(bound(forms.DateField(initial=date(2026, 9, 11))))
    assert 'value="2026-09-11"' in html
    assert "data-mask" not in html
