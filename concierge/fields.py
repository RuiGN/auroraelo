"""Campo de texto cifrado em repouso para dados de contato e registros do concierge."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

_PREFIX = "enc1:"


@lru_cache(maxsize=4)
def _fernet_for(raw_key: str) -> Fernet:
    digest = hashlib.sha256(f"concierge-field:{raw_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _cipher() -> Fernet:
    raw_key = getattr(settings, "CONCIERGE_FIELD_ENCRYPTION_KEY", "") or str(
        settings.SECRET_KEY
    )
    return _fernet_for(raw_key)


def encrypt_text(value: str) -> str:
    """Cifra um texto com prefixo de versão (permite trocar o esquema depois)."""
    return _PREFIX + _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    """Decifra um valor gravado por :func:`encrypt_text`."""
    if not value.startswith(_PREFIX):
        return value
    try:
        return _cipher().decrypt(value[len(_PREFIX) :].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:  # chave trocada ou dado adulterado: nunca devolve lixo
        raise ValueError("Campo cifrado ilegível com a chave atual.") from exc


class EncryptedTextField(models.TextField):  # type: ignore[type-arg]
    """Texto cifrado com Fernet. Não é pesquisável nem ordenável no banco."""

    description = "Texto cifrado em repouso"

    def get_prep_value(self, value: Any) -> Any:
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt_text(str(value))

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None or value == "":
            return value
        return decrypt_text(str(value))

    def get_lookup(self, lookup_name: str) -> Any:
        if lookup_name not in {"isnull", "exact"}:
            raise ValueError(
                "Campos cifrados não aceitam busca parcial nem ordenação no banco."
            )
        return super().get_lookup(lookup_name)
