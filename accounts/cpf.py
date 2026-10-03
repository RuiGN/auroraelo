"""CPF (Brazilian taxpayer number) parsing, validation and masking.

The CPF is the login of the clinic team. It is stored as eleven digits, shown masked
(``***.456.789-**``) in lists and never written to logs or audit payloads.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Accepted typing: digits with the usual dot, dash and space separators, nothing else.
_TYPED_CPF = re.compile(r"[\d.\-\s]+")
_NON_DIGITS = re.compile(r"\D")


def normalize_cpf(value: str | None) -> str:
    """Return only the digits of ``value`` (empty for ``None``)."""
    return _NON_DIGITS.sub("", value or "")


def _check_digit(digits: str, length: int) -> int:
    total = sum(
        int(digit) * weight
        for digit, weight in zip(digits[:length], range(length + 1, 1, -1), strict=True)
    )
    return (total * 10) % 11 % 10


def is_valid_cpf(value: str | None) -> bool:
    """Return whether ``value`` has eleven digits and both check digits match."""
    digits = normalize_cpf(value)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    return all(
        _check_digit(digits, length) == int(digits[length]) for length in (9, 10)
    )


def parse_cpf(value: str | None) -> str:
    """Return the canonical eleven digits or raise a field-ready ``ValidationError``."""
    typed = (value or "").strip()
    if not _TYPED_CPF.fullmatch(typed) or not is_valid_cpf(typed):
        raise ValidationError(_("Informe um CPF válido."), code="invalid_cpf")
    return normalize_cpf(typed)


def validate_cpf(value: str) -> None:
    """Model/form validator wrapping :func:`parse_cpf`."""
    parse_cpf(value)


def format_cpf(value: str | None) -> str:
    """Return ``123.456.789-09`` for a valid CPF and the input unchanged otherwise."""
    digits = normalize_cpf(value)
    if len(digits) != 11:
        return value or ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def mask_cpf(value: str | None) -> str:
    """Return ``***.456.789-**``: recognisable, but not enough to reuse the number."""
    digits = normalize_cpf(value)
    if len(digits) != 11:
        return ""
    return f"***.{digits[3:6]}.{digits[6:9]}-**"
