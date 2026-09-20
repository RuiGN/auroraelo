"""Schemas fechados, limitados e reutilizados no transporte JSON."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from . import services
from .policies import CAPABILITIES


class AwareDateTimeField(forms.DateTimeField):
    def to_python(self, value):
        parsed = parse_datetime(value) if isinstance(value, str) else None
        if parsed is None or timezone.is_naive(parsed):
            raise ValidationError("Informe ISO-8601 com fuso horário.")
        return parsed


def choice(values):
    return forms.ChoiceField(choices=[(value, value) for value in values])


def schema(**fields):
    return type("PayloadForm", (forms.Form,), fields)


COMMANDS = {
    "grants": (
        services.set_grant,
        schema(
            user_id=forms.UUIDField(),
            capability=choice(sorted(CAPABILITIES)),
            enabled=forms.BooleanField(required=False),
        ),
    ),
    "products": (
        services.create_product,
        schema(
            name=forms.CharField(max_length=160), sku=forms.CharField(max_length=48)
        ),
    ),
    "lots": (
        services.create_lot,
        schema(
            product_id=forms.UUIDField(),
            code=forms.CharField(max_length=64),
            expires_on=forms.DateField(input_formats=["%Y-%m-%d"]),
        ),
    ),
    "movements": (
        services.move_stock,
        schema(
            lot_id=forms.UUIDField(),
            quantity=forms.IntegerField(min_value=1, max_value=1000000),
            direction=choice(("in", "out")),
            key=forms.CharField(max_length=80, strip=False),
            patient_id=forms.UUIDField(required=False),
        ),
    ),
    "encounters": (
        services.schedule_encounter,
        schema(patient_id=forms.UUIDField(), starts_at=AwareDateTimeField()),
    ),
    "transitions": (
        services.transition_encounter,
        schema(
            encounter_id=forms.UUIDField(), status=choice(tuple(services.TRANSITIONS))
        ),
    ),
    "records": (
        services.append_record,
        schema(
            encounter_id=forms.UUIDField(), content=forms.CharField(max_length=8000)
        ),
    ),
    "sessions": (
        services.schedule_session,
        schema(
            kind=choice(("individual", "grupo")),
            modality=choice(services.MODALITIES),
            capacity=forms.IntegerField(min_value=1, max_value=100),
            starts_at=AwareDateTimeField(),
            ends_at=AwareDateTimeField(),
        ),
    ),
    "enrollments": (
        services.enroll_patient,
        schema(session_id=forms.UUIDField(), patient_id=forms.UUIDField()),
    ),
    "attendance": (
        services.set_attendance,
        schema(enrollment_id=forms.UUIDField(), status=choice(("presente", "ausente"))),
    ),
}


def validate_payload(form_class, payload):
    if not isinstance(payload, dict) or set(payload) - set(form_class.base_fields):
        raise ValidationError("Objeto JSON contém campos desconhecidos.")
    for name, field in form_class.base_fields.items():
        if name not in payload:
            if field.required or isinstance(field, forms.BooleanField):
                raise ValidationError("Campo obrigatório ausente.")
            continue
        value = payload[name]
        expected = (
            bool
            if isinstance(field, forms.BooleanField)
            else int
            if isinstance(field, forms.IntegerField)
            else str
        )
        if value is None and not field.required and isinstance(field, forms.UUIDField):
            continue
        if type(value) is not expected:
            raise ValidationError("Tipo JSON incompatível.")
    form = form_class(payload)
    if not form.is_valid():
        raise ValidationError("Payload inválido.")
    return form.cleaned_data
