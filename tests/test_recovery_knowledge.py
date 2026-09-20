"""Corpus exclusivamente sintético; nenhuma fonte ou sessão real."""

import hashlib
import importlib
import json
from typing import Any

import pytest


def corpus() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sources": [
            {
                "id": "synthetic-exercise",
                "title": "Exercício: exemplo sintético",
                "publisher": "Synthetic public education",
                "url": "https://example.org/education/exercise",
                "published_date": None,
                "accessed_on": "2026-09-20",
                "topics": ["exercise", "relapse_prevention"],
                "summary_pt_br": "Atividade física pode apoiar o bem-estar.",
                "evidence_quote": "Synthetic example: exercise may support wellbeing.",
                "evidence_limitations": (
                    "Exemplo inventado para teste, não evidência clínica."
                ),
                "safety_notes": ["Não substitui avaliação profissional."],
            }
        ],
    }


def test_versioned_loader_has_deterministic_canonical_digest() -> None:
    from importlib.util import find_spec

    assert find_spec("ai_assistant.recovery_knowledge") is not None
    module = importlib.import_module("ai_assistant.recovery_knowledge")
    first = module.load_corpus(json.dumps(corpus()).encode())
    second = module.load_corpus(json.dumps(corpus(), indent=4).encode())
    assert first.canonical == second.canonical
    assert first.sha256 == hashlib.sha256(first.canonical).hexdigest()
    assert first.version == f"v1-{first.sha256}"
    assert first.key == f"auroraelo:knowledge:{first.version}"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "UPPER"),
        ("id", "acentuádo"),
        ("id", "bad--id"),
        ("id", "../key"),
        ("id", "x" * 81),
        ("title", 3),
        ("title", " "),
        ("title", "x" * 501),
        ("publisher", None),
        ("url", "http://example.org"),
        ("url", "https://user:pass@example.org"),
        ("url", "https://127.0.0.1/"),
        ("url", "https://localhost/"),
        ("url", "https://example.org:444/"),
        ("url", "https://example.org/a#b"),
        ("url", "https://example.org/\\n"),
        ("topics", ["unknown"]),
        ("topics", []),
        ("topics", "exercise"),
        ("topics", ["exercise", "exercise"]),
        ("summary_pt_br", "x" * 6001),
        ("evidence_quote", None),
        ("evidence_limitations", ""),
        ("safety_notes", [False]),
        ("accessed_on", "yesterday"),
        ("published_date", "2026-02-30"),
        ("extra", "forbidden"),
    ],
)
def test_loader_rejects_invalid_source(field: str, value: Any) -> None:
    from ai_assistant.recovery_knowledge import load_corpus

    data = corpus()
    data["sources"][0][field] = value
    with pytest.raises(ValueError):
        load_corpus(json.dumps(data).encode())


@pytest.mark.parametrize(
    "data",
    [
        {"schema_version": True, "sources": []},
        {"schema_version": 2, "sources": []},
        {"schema_version": 1, "sources": []},
        {"schema_version": 1, "sources": {}, "extra": 1},
        [],
        None,
    ],
)
def test_loader_rejects_invalid_root(data: Any) -> None:
    from ai_assistant.recovery_knowledge import load_corpus

    with pytest.raises(ValueError):
        load_corpus(json.dumps(data).encode())


def test_loader_rejects_duplicates_oversize_and_canonicalizes_order() -> None:
    from ai_assistant.recovery_knowledge import load_corpus

    data = corpus()
    data["sources"].append(dict(data["sources"][0]))
    with pytest.raises(ValueError):
        load_corpus(json.dumps(data).encode())
    for raw in [b"x" * 2_000_001, b'{"schema_version":1,"schema_version":1}', b"NaN"]:
        with pytest.raises(ValueError):
            load_corpus(raw)
    data["sources"][1]["id"] = "another-source"
    first = load_corpus(json.dumps(data).encode())
    data["sources"].reverse()
    data["sources"][0]["topics"].reverse()
    assert first.sha256 == load_corpus(json.dumps(data).encode()).sha256


@pytest.fixture
def recovery_redis() -> Any:
    import os

    import redis

    url = os.environ.get("RECOVERY_TEST_REDIS_URL", "")
    if url != "redis://127.0.0.1:56389/13":
        pytest.skip("Redis descartável exige RECOVERY_TEST_REDIS_URL em localhost DB13")
    client = redis.Redis.from_url(url, socket_timeout=1, socket_connect_timeout=1)
    assert client.ping()
    yield client
    # Apenas os namespaces novos deste domínio no DB13 reservado para estes testes.
    for pattern in ("auroraelo:knowledge:*", "auroraelo:recovery-usage:*"):
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    client.close()


def test_redis_atomic_idempotent_hash_and_readback(recovery_redis: Any) -> None:
    from ai_assistant import recovery_knowledge as knowledge

    assert hasattr(knowledge, "sync_corpus")
    loaded = knowledge.load_corpus(json.dumps(corpus()).encode())
    assert knowledge.sync_corpus(recovery_redis, loaded) is True
    assert recovery_redis.type(loaded.key) == b"hash"
    snapshot = recovery_redis.hgetall(loaded.key)
    assert knowledge.sync_corpus(recovery_redis, loaded) is False
    assert snapshot == recovery_redis.hgetall(loaded.key)
    assert knowledge.read_corpus(recovery_redis, loaded.version) == loaded
    recovery_redis.hset(loaded.key, "corpus", b"{}")
    with pytest.raises(knowledge.KnowledgeUnavailableError):
        knowledge.read_corpus(recovery_redis, loaded.version)
    with pytest.raises(knowledge.KnowledgeUnavailableError):
        knowledge.sync_corpus(recovery_redis, loaded)
    assert recovery_redis.hget(loaded.key, "corpus") == b"{}"


def test_redis_concurrent_sync_is_one_atomic_publication(recovery_redis: Any) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from ai_assistant.recovery_knowledge import load_corpus, read_corpus, sync_corpus

    loaded = load_corpus(json.dumps(corpus()).encode())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: sync_corpus(recovery_redis, loaded), range(8))
        )
    assert results.count(True) == 1
    assert results.count(False) == 7
    assert read_corpus(recovery_redis, loaded.version) == loaded


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sha256", "0" * 64),
        ("source_count", "2"),
        ("language", "en"),
        ("schema_version", "2"),
        ("corpus", "x" * 2_000_001),
    ],
)
def test_hash_metadata_or_payload_tampering_is_refused(
    recovery_redis: Any, field: str, value: str
) -> None:
    from ai_assistant.recovery_knowledge import (
        KnowledgeUnavailableError,
        load_corpus,
        read_corpus,
        sync_corpus,
    )

    loaded = load_corpus(json.dumps(corpus()).encode())
    sync_corpus(recovery_redis, loaded)
    recovery_redis.hset(loaded.key, field, value)
    with pytest.raises(KnowledgeUnavailableError):
        read_corpus(recovery_redis, loaded.version)


def test_sync_command_verifies_real_redis(
    recovery_redis: Any, tmp_path: Any, settings: Any
) -> None:
    from io import StringIO

    from django.core.management import call_command, get_commands

    assert "sync_recovery_knowledge" in get_commands()
    settings.RECOVERY_KNOWLEDGE_REDIS_URL = "redis://127.0.0.1:56389/13"
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(corpus()))
    output = StringIO()
    call_command(
        "sync_recovery_knowledge", corpus=str(path), verify=True, stdout=output
    )
    assert '"verified": true' in output.getvalue()


def test_redis_down_and_missing_configuration_fail_closed(settings: Any) -> None:
    from ai_assistant import recovery_knowledge as knowledge

    assert hasattr(knowledge, "redis_client")
    settings.RECOVERY_KNOWLEDGE_REDIS_URL = ""
    with pytest.raises(knowledge.KnowledgeUnavailableError):
        knowledge.redis_client()
    settings.RECOVERY_KNOWLEDGE_REDIS_URL = "redis://127.0.0.1:1/13"
    settings.RECOVERY_REDIS_TIMEOUT_SECONDS = 0.1
    client = knowledge.redis_client()
    loaded = knowledge.load_corpus(json.dumps(corpus()).encode())
    with pytest.raises(knowledge.KnowledgeUnavailableError):
        knowledge.sync_corpus(client, loaded)
    with pytest.raises(knowledge.KnowledgeUnavailableError):
        knowledge.read_corpus(client, loaded.version)


def test_lexical_library_returns_evidence_and_refuses_no_match() -> None:
    from ai_assistant import recovery_knowledge as knowledge

    assert hasattr(knowledge, "retrieve")
    loaded = knowledge.load_corpus(json.dumps(corpus()).encode())
    sources = knowledge.retrieve(loaded, query="atividade física", topics=[])
    assert sources[0]["id"] == "synthetic-exercise"
    assert sources[0]["evidence_limitations"]
    assert sources[0]["evidence_quote"]
    assert sources[0]["url"].startswith("https://")
    assert knowledge.retrieve(loaded, query="astronomia", topics=[]) == []
    assert knowledge.retrieve(loaded, query="atividade", topics=["gambling"]) == []
    assert knowledge.retrieve(loaded, query="exercício", topics=["exercise"])
