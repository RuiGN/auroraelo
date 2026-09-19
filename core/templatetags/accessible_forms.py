"""Template helpers for accessible Django form rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from django import forms, template
from django.forms.boundfield import BoundField
from django.utils import formats
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _

register = template.Library()


# --- Field presentation maps -------------------------------------------------
# Keyed by the Django field name so the same input reads consistently wherever
# a form reuses it. Values stay declarative; rendering logic lives below.

# Input masks applied on the client (form-behaviors.js) and canonicalized to
# digits on submit. Only names that always carry the same data shape appear.
_PHONE_FIELDS = frozenset({"phone", "administrative_phone", "emergency_contact_phone"})
_DOCUMENT_FIELDS = frozenset({"document"})
_POSTAL_FIELDS = frozenset({"address_postal_code"})

# Placeholder hints. Shown only when the widget does not already define one.
_PLACEHOLDERS: dict[str, Any] = {
    "email": _("seu@email.com"),
    "recipient_email": _("nome@dominio.com"),
    "administrative_email": _("contato@clinica.com"),
    "phone": "(11) 98765-4321",
    "administrative_phone": "(11) 3333-4444",
    "emergency_contact_phone": "(11) 98765-4321",
    "document": "000.000.000-00",
    "address_postal_code": "00000-000",
    "address_state": "SP",
    "country_code": "BR",
    "full_name": _("Nome e sobrenome"),
    "social_name": _("Como prefere ser chamado(a)"),
    "first_name": _("Nome"),
    "last_name": _("Sobrenome"),
    "legal_name": _("Razão social completa"),
    "display_name": _("Nome público da clínica"),
    "name": _("Informe o nome"),
    "city": _("Cidade"),
    "address_city": _("Cidade"),
    "region": _("Estado ou região"),
    "address_line": _("Rua, número e bairro"),
    "address_line_1": _("Rua, número e bairro"),
    "address_line_2": _("Apartamento, sala, referência"),
    "title": _("Título curto e objetivo"),
    "slug": _("identificador-sem-espacos"),
    "primary_color": "#2563EB",
    "secondary_color": "#0EA5E9",
    "advance_minutes": "30",
    "intensity": _("1 a 10"),
}

# Feather icon class per field name. Falls back to a type-based icon below.
_ICONS_BY_NAME: dict[str, str] = {
    "email": "feather-mail",
    "recipient_email": "feather-mail",
    "administrative_email": "feather-mail",
    "phone": "feather-phone",
    "administrative_phone": "feather-phone",
    "emergency_contact_phone": "feather-phone",
    "emergency_contact_name": "feather-user",
    "full_name": "feather-user",
    "social_name": "feather-user",
    "first_name": "feather-user",
    "last_name": "feather-user",
    "name": "feather-user",
    "legal_name": "feather-briefcase",
    "display_name": "feather-briefcase",
    "document": "feather-credit-card",
    "registration_identifier": "feather-hash",
    "address_line": "feather-map-pin",
    "address_line_1": "feather-map-pin",
    "address_line_2": "feather-map-pin",
    "address_city": "feather-map-pin",
    "city": "feather-map-pin",
    "region": "feather-map",
    "address_state": "feather-map",
    "address_postal_code": "feather-map-pin",
    "postal_code": "feather-map-pin",
    "country_code": "feather-flag",
    "timezone_name": "feather-globe",
    "language_code": "feather-globe",
    "title": "feather-type",
    "slug": "feather-hash",
    "amount": "feather-dollar-sign",
    "currency": "feather-dollar-sign",
    "advance_minutes": "feather-clock",
    "max_daily": "feather-hash",
    "intensity": "feather-activity",
    "expires_in_hours": "feather-clock",
}

# Narrow (short data) field names get a smaller column at desktop widths.
_SMALL_FIELDS = frozenset(
    {
        "address_state",
        "country_code",
        "address_postal_code",
        "postal_code",
        "amount",
        "currency",
        "advance_minutes",
        "max_daily",
        "intensity",
        "expires_in_hours",
        "language_code",
        "priority",
        "primary_color",
        "secondary_color",
    }
)

# Full-width field names regardless of their widget.
_LARGE_FIELDS = frozenset(
    {
        "description",
        "notes",
        "goals",
        "body",
        "address_line",
        "address_line_1",
        "contraindications",
        "source_reference",
        "out_of_hours_instructions",
        "accessibility_preferences",
    }
)


class _DuraluxRadioGroup(forms.RadioSelect):
    """Keep input styling on options, never on their containing element."""

    def get_context(self, name: str, value: Any, attrs: Any) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"] = {
            **context["widget"]["attrs"],
            "class": "d-grid gap-2",
        }
        return context


class _DuraluxCheckboxGroup(_DuraluxRadioGroup, forms.CheckboxSelectMultiple):
    """Preserve Django multiple-choice selection and validation semantics."""


def _mask_kind(field_name: str) -> str | None:
    """Return the client mask identifier for a field, if any."""
    if field_name in _PHONE_FIELDS:
        return "phone"
    if field_name in _DOCUMENT_FIELDS:
        return "document"
    if field_name in _POSTAL_FIELDS:
        return "cep"
    return None


@register.filter
def accessible_widget(field: BoundField) -> SafeString:
    """Render a bound field with deterministic accessibility attributes."""
    widget = field.field.widget
    if widget.is_hidden:
        return mark_safe(field.as_widget())
    input_type = getattr(widget, "input_type", "")
    described_by: list[str] = str(widget.attrs.get("aria-describedby", "")).split()
    if field.errors:
        described_by.extend(
            f"{field.auto_id}_error_{index}"
            for index, _error in enumerate(field.errors)
        )
    if field.help_text:
        described_by.append(f"{field.auto_id}_helptext")

    attrs: dict[str, str | bool] = {}
    if described_by:
        attrs["aria-describedby"] = " ".join(dict.fromkeys(described_by))
    if field.errors:
        attrs["aria-invalid"] = "true"

    if input_type in {"checkbox", "radio"}:
        attrs["class"] = "form-check-input"
    elif isinstance(widget, forms.Select):
        attrs["class"] = "form-select"
    else:
        attrs["class"] = "form-control"
    render_widget = widget
    # Adapt only stock widgets; domain subclasses retain their rendering hooks.
    if type(widget) in (forms.CheckboxSelectMultiple, forms.RadioSelect):
        render_widget = deepcopy(widget)
        render_widget.__class__ = (
            _DuraluxCheckboxGroup
            if type(widget) is forms.CheckboxSelectMultiple
            else _DuraluxRadioGroup
        )
    if (
        isinstance(field.field, forms.DateField)
        and not isinstance(field.field, forms.DateTimeField)
        and type(widget) is forms.DateInput
        and widget.format is None
    ):
        render_widget = deepcopy(widget)
        render_widget.format = "%Y-%m-%d"
        render_widget.input_type = "date"

    if type(widget) is forms.TimeInput and widget.format is None:
        render_widget = deepcopy(widget)
        render_widget.format = "%H:%M:%S"
        render_widget.input_type = "time"
        attrs["step"] = "1"

    mask = _mask_kind(field.name) if isinstance(widget, forms.TextInput) else None
    if mask == "phone":
        attrs.update(
            {
                "data-mask": "phone",
                "data-canonical-value": "",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        )
    elif mask == "document":
        attrs.update(
            {
                "data-mask": "document",
                "data-canonical-value": "",
                "inputmode": "numeric",
                "autocomplete": "off",
            }
        )
    elif mask == "cep":
        attrs.update(
            {
                "data-mask": "cep",
                "data-canonical-value": "",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
            }
        )
    elif field.name in {"email", "recipient_email", "administrative_email"}:
        attrs.setdefault("inputmode", "email")
        attrs.setdefault("autocomplete", "email")

    # Explicit domain attributes override presentation defaults.
    for attribute in ("inputmode", "autocomplete", "data-mask", "step"):
        if attribute in widget.attrs:
            attrs[attribute] = widget.attrs[attribute]

    # A hinted placeholder helps only text-like inputs, never choices/toggles.
    is_texty = isinstance(
        widget,
        (
            forms.TextInput,
            forms.EmailInput,
            forms.URLInput,
            forms.PasswordInput,
            forms.NumberInput,
            forms.Textarea,
        ),
    ) and input_type not in {"color", "range", "date", "time", "datetime-local"}
    if is_texty and "placeholder" not in widget.attrs:
        attrs["placeholder"] = str(_PLACEHOLDERS.get(field.name, field.label))
    if isinstance(field.field, forms.DecimalField):
        attrs.setdefault("inputmode", widget.attrs.get("inputmode", "decimal"))
        if "placeholder" not in widget.attrs:
            attrs["placeholder"] = formats.number_format(
                0,
                decimal_pos=field.field.decimal_places or 2,
                use_l10n=field.field.localize,
            )

    if field.name == "enabled" and type(widget) is forms.CheckboxInput:
        attrs["class"] = "form-check-input"
        attrs["role"] = "switch"

    attrs["class"] = " ".join(
        dict.fromkeys(
            [*str(widget.attrs.get("class", "")).split(), *str(attrs["class"]).split()]
        )
    )

    return mark_safe(field.as_widget(widget=render_widget, attrs=attrs))


@register.filter
def field_icon(field: BoundField) -> str:
    """Decorate editable text while preserving native non-text affordances."""
    widget = field.field.widget
    if (
        widget.is_hidden
        or isinstance(
            widget,
            (
                forms.CheckboxInput,
                forms.RadioSelect,
                forms.CheckboxSelectMultiple,
                forms.FileInput,
                forms.MultiWidget,
            ),
        )
        or getattr(widget, "input_type", "") in {"range", "color"}
    ):
        return ""
    if isinstance(widget, forms.PasswordInput):
        return "feather-lock"
    if isinstance(widget, forms.URLInput):
        return "feather-link"
    if isinstance(widget, forms.Textarea):
        return "feather-align-left"
    if field.name in _ICONS_BY_NAME:
        return _ICONS_BY_NAME[field.name]
    if isinstance(field.field, forms.EmailField):
        return "feather-mail"
    if isinstance(field.field, forms.DateTimeField):
        return "feather-calendar"
    if isinstance(field.field, forms.DateField):
        return "feather-calendar"
    if isinstance(field.field, forms.TimeField):
        return "feather-clock"
    if isinstance(field.field, (forms.IntegerField, forms.DecimalField)):
        return "feather-hash"
    if isinstance(widget, forms.Select):
        return "feather-list"
    if isinstance(widget, forms.widgets.Input):
        return "feather-edit-2"
    return ""


@register.filter
def field_span(field: BoundField) -> str:
    """Return a responsive column-span class sized to the expected data.

    Short data (state, CEP, phone, amount) takes a narrow column at desktop
    widths; long-form and choice inputs span the full row; everything else
    occupies a medium column. All fields are full width on small screens.
    """
    widget = field.field.widget
    if field.name in _LARGE_FIELDS:
        return "field-span--lg"
    if isinstance(widget, forms.Textarea):
        return "field-span--lg"
    if isinstance(widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
        return "field-span--lg"
    if isinstance(widget, forms.FileInput):
        return "field-span--lg"
    if field.name in _SMALL_FIELDS:
        return "field-span--sm"
    # Keep start/end time pairs side by side rather than three per row.
    if isinstance(field.field, (forms.TimeField, forms.DateTimeField)):
        return "field-span--md"
    if isinstance(field.field, forms.DateField):
        return "field-span--sm"
    max_length = getattr(field.field, "max_length", None)
    if isinstance(max_length, int) and max_length <= 8:
        return "field-span--sm"
    return "field-span--md"


@register.filter
def error_target_id(field: BoundField) -> str:
    """Return the focusable error-summary destination for a bound field."""
    if isinstance(
        field.field.widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)
    ):
        return f"{field.auto_id}_0"
    return field.auto_id
