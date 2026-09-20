"""Validation stricte et bornée des contrats JSON/session de psychiatrie."""

import json
import math
import re
from uuid import UUID

from django.core.exceptions import ValidationError

MAX_BODY = 65536


class PayloadTooLargeError(Exception):
    pass


def invalid():
    raise ValidationError("Dados inválidos.")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid()
        result[key] = value
    return result


def payload(request, allowed):
    if request.content_type != "application/json":
        invalid()
    if len(request.body) > MAX_BODY:
        raise PayloadTooLargeError
    try:
        data = json.loads(
            request.body,
            object_pairs_hook=_pairs,
            parse_constant=lambda value: invalid(),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValidationError("JSON inválido.") from exc
    if not isinstance(data, dict) or set(data) - set(allowed):
        invalid()
    return data


def text(data, key, default="", maximum=4000, required=False):
    value = data.get(key, default)
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (required and not value.strip())
    ):
        invalid()
    return value


def integer(data, key, minimum, maximum, default=None):
    value = data.get(key, default)
    if type(value) is not int or not minimum <= value <= maximum:
        invalid()
    return value


def number(data, key, minimum, maximum, default=None):
    value = data.get(key, default)
    # Compare inteiros antes de isfinite: a conversão para float pode transbordar.
    if (
        type(value) not in (int, float)
        or not minimum <= value <= maximum
        or not math.isfinite(value)
    ):
        invalid()
    return value


def boolean(data, key, default=None):
    value = data.get(key, default)
    if type(value) is not bool:
        invalid()
    return value


def choice(data, key, choices, default=None):
    value = data.get(key, default)
    if not isinstance(value, str) or value not in choices:
        invalid()
    return value


def strings(data, key, choices=None):
    value = data.get(key, [])
    if not isinstance(value, list) or len(value) > 20:
        invalid()
    for item in value:
        if (
            not isinstance(item, str)
            or len(item) > 100
            or (choices and item not in choices)
        ):
            invalid()
    return value


def identifier(data, key):
    value = data.get(key)
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        value,
    ):
        invalid()
    return UUID(value)


def pagination(request, extra=()):
    if set(request.GET) - {"limit", "offset", *extra}:
        invalid()
    values = []
    for key, default, minimum, maximum in (
        ("limit", "50", 1, 100),
        ("offset", "0", 0, 10000),
    ):
        value = request.GET.get(key, default)
        if (
            not re.fullmatch(r"[0-9]{1,5}", value)
            or not minimum <= int(value) <= maximum
        ):
            invalid()
        values.append(int(value))
    return tuple(values)
