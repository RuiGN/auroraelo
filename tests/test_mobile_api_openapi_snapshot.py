"""Foto versionada do contrato do app (`/api/v1/mobile/`).

O app (Jest) valida os seus loaders e ações contra `openapi-mobile.json`: dados de
exemplo gerados do esquema precisam passar nos parsers e o corpo de cada gravação
precisa respeitar o esquema de entrada. Este teste impede a foto de ficar para trás:
mudou a API → regenere com

    UPDATE_MOBILE_OPENAPI=1 python -m pytest tests/test_mobile_api_openapi_snapshot.py

e rode `npm test` em mobile/posalta (os testes de contrato do app dizem o que quebrou).
Sem a pasta `mobile/` (ex.: cópia só do web) o teste é ignorado.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from api import api

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "mobile" / "posalta" / "tests" / "fixtures" / "openapi-mobile.json"
PREFIX = "/api/v1/mobile/"


def _refs(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            found |= _refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= _refs(value)
    return found


def build_snapshot() -> dict[str, Any]:
    """Só as rotas do app e os esquemas que elas alcançam, em ordem estável."""
    full = api.get_openapi_schema()
    paths = {
        path: operations
        for path, operations in sorted(full["paths"].items())
        if path.startswith(PREFIX)
    }
    schemas = full.get("components", {}).get("schemas", {})
    needed = _refs(paths)
    queue = list(needed)
    while queue:
        name = queue.pop()
        for inner in _refs(schemas.get(name, {})):
            if inner not in needed:
                needed.add(inner)
                queue.append(inner)
    return {
        "openapi": full.get("openapi", "3.1.0"),
        "paths": paths,
        "components": {"schemas": {name: schemas[name] for name in sorted(needed)}},
    }


def _dump(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def test_openapi_snapshot_matches_the_api() -> None:
    if not SNAPSHOT.parent.parent.parent.exists():
        pytest.skip("mobile/posalta não existe nesta cópia")
    current = _dump(build_snapshot())
    if os.environ.get("UPDATE_MOBILE_OPENAPI") == "1":
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(current, encoding="utf-8")
    assert SNAPSHOT.exists(), "gere com UPDATE_MOBILE_OPENAPI=1"
    assert SNAPSHOT.read_text(encoding="utf-8") == current, (
        "o contrato mudou: regenere mobile/posalta/tests/fixtures/openapi-mobile.json "
        "(UPDATE_MOBILE_OPENAPI=1) e rode os testes do app"
    )
