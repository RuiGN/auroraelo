"""Corpus público versionado, sem embeddings ou dados de pessoas."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from django.utils.translation import gettext as _

MAX_CORPUS_BYTES = 2_000_000
TOPICS = frozenset(
    {
        "alcohol",
        "substances",
        "gambling",
        "relapse_prevention",
        "exercise",
        "yoga",
        "art_therapy",
        "crisis",
    }
)
TEXT_LIMITS = {
    "id": 80,
    "title": 500,
    "publisher": 300,
    "url": 2048,
    "summary_pt_br": 6000,
    "evidence_quote": 6000,
    "evidence_limitations": 4000,
}


def text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(_("Texto ausente, inválido ou acima do limite."))
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(_("Caracteres de controle não permitidos."))
    return value


def public_https_url(value: Any) -> str:
    url = text(value, 2048)
    if any(char.isspace() for char in url) or "\\" in url:
        raise ValueError(_("URL pública HTTPS inválida."))
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
        or not re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host
        )
        or host.endswith((".local", ".localhost", ".internal", ".test"))
    ):
        raise ValueError(_("URL pública HTTPS inválida."))
    return url


def strict_json(raw: bytes | str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(_("Chave JSON duplicada."))
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(_("Constante JSON inválida."))

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError(_("JSON inválido.")) from exc


def _validate_source(source: Any) -> None:
    fields = set(TEXT_LIMITS) | {
        "published_date",
        "accessed_on",
        "topics",
        "safety_notes",
    }
    if not isinstance(source, dict) or set(source) != fields:
        raise ValueError(_("Campos da fonte inválidos."))
    for field, limit in TEXT_LIMITS.items():
        text(source[field], limit)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source["id"]):
        raise ValueError(_("Identificador da fonte inválido."))
    public_https_url(source["url"])
    for field in ("published_date", "accessed_on"):
        value = source[field]
        if field == "published_date" and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(_("Data da fonte inválida."))
        date.fromisoformat(value)
    topics = source["topics"]
    if (
        not isinstance(topics, list)
        or not 1 <= len(topics) <= len(TOPICS)
        or any(not isinstance(topic, str) or topic not in TOPICS for topic in topics)
        or len(set(topics)) != len(topics)
    ):
        raise ValueError(_("Tópicos da fonte inválidos."))
    notes = source["safety_notes"]
    if not isinstance(notes, list) or not 1 <= len(notes) <= 20:
        raise ValueError(_("Notas de segurança inválidas."))
    for note in notes:
        text(note, 2000)
    source["topics"] = sorted(topics)


@dataclass(frozen=True)
class Corpus:
    canonical: bytes
    sha256: str

    @property
    def version(self) -> str:
        return f"v1-{self.sha256}"

    @property
    def key(self) -> str:
        return f"auroraelo:knowledge:{self.version}"

    @property
    def sources(self) -> list[dict[str, Any]]:
        return list(json.loads(self.canonical)["sources"])


def load_corpus(raw: bytes) -> Corpus:
    if not isinstance(raw, bytes) or len(raw) > MAX_CORPUS_BYTES:
        raise ValueError(_("Corpus acima do limite."))
    payload = strict_json(raw)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "sources"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
    ):
        raise ValueError(_("Schema do corpus inválido."))
    sources = payload["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 200:
        raise ValueError(_("Quantidade de fontes inválida."))
    for source in sources:
        _validate_source(source)
    if len({source["id"] for source in sources}) != len(sources):
        raise ValueError(_("Identificador de fonte duplicado."))
    payload["sources"] = sorted(sources, key=lambda source: source["id"])
    canonical = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return Corpus(canonical, hashlib.sha256(canonical).hexdigest())


class KnowledgeUnavailableError(RuntimeError):
    """Falha fechada; mensagem não contém URL, corpus ou credenciais."""


_SYNC_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then
  if redis.call('HLEN', KEYS[1]) ~= #ARGV / 2 then return -1 end
  for i = 1, #ARGV, 2 do
    if redis.call('HGET', KEYS[1], ARGV[i]) ~= ARGV[i+1] then return -1 end
  end
  return 0
end
redis.call('HSET', KEYS[1], unpack(ARGV))
return 1
"""
_READ_SCRIPT = """
if redis.call('HLEN', KEYS[1]) ~= 5 then return {} end
if redis.call('HSTRLEN', KEYS[1], 'corpus') > 2000000 then return {} end
for _, field in ipairs({'sha256', 'schema_version', 'source_count', 'language'}) do
  if redis.call('HSTRLEN', KEYS[1], field) > 64 then return {} end
end
return redis.call('HGETALL', KEYS[1])
"""


def redis_client() -> Any:
    import redis
    from django.conf import settings

    url = getattr(settings, "RECOVERY_KNOWLEDGE_REDIS_URL", "")
    timeout = getattr(settings, "RECOVERY_REDIS_TIMEOUT_SECONDS", 2.0)
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"redis", "rediss"}
            or not parsed.hostname
            or parsed.query
            or parsed.fragment
            or isinstance(timeout, bool)
            or not 0.1 <= float(timeout) <= 10
        ):
            raise ValueError
        return redis.Redis.from_url(
            url,
            socket_timeout=float(timeout),
            socket_connect_timeout=float(timeout),
            decode_responses=False,
            retry=redis.retry.Retry(redis.backoff.NoBackoff(), 0),
        )
    except (TypeError, ValueError) as exc:
        raise KnowledgeUnavailableError(
            _("Biblioteca temporariamente indisponível.")
        ) from exc


def _hash_fields(corpus: Corpus) -> dict[bytes, bytes]:
    return {
        b"corpus": corpus.canonical,
        b"sha256": corpus.sha256.encode(),
        b"schema_version": b"1",
        b"source_count": str(len(corpus.sources)).encode(),
        b"language": b"pt-br",
    }


def sync_corpus(client: Any, corpus: Corpus) -> bool:
    import redis

    try:
        validated = load_corpus(corpus.canonical)
        if validated != corpus:
            raise ValueError
        args = [item for pair in _hash_fields(corpus).items() for item in pair]
        result = client.eval(_SYNC_SCRIPT, 1, corpus.key, *args)
        if result not in (0, 1) or read_corpus(client, corpus.version) != corpus:
            raise ValueError
        return bool(result == 1)
    except (redis.RedisError, ValueError, TypeError) as exc:
        raise KnowledgeUnavailableError(
            _("Falha de integridade na biblioteca.")
        ) from exc


def read_corpus(client: Any, version: str) -> Corpus:
    import redis

    try:
        if not isinstance(version, str) or not re.fullmatch(
            r"v1-[a-f0-9]{64}", version
        ):
            raise ValueError
        pairs = client.eval(_READ_SCRIPT, 1, f"auroraelo:knowledge:{version}")
        fields = dict(zip(pairs[::2], pairs[1::2], strict=True))
        loaded = load_corpus(fields.get(b"corpus", b""))
        if loaded.version != version or fields != _hash_fields(loaded):
            raise ValueError
        return loaded
    except (redis.RedisError, ValueError, TypeError) as exc:
        raise KnowledgeUnavailableError(
            _("Biblioteca indisponível ou sem integridade.")
        ) from exc


def normalized(value: str) -> str:
    import unicodedata

    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char)
    )


def retrieve(
    corpus: Corpus, *, query: str, topics: list[str], limit: int = 3
) -> list[dict[str, Any]]:
    """Correspondência lexical, não avaliação clínica nem resposta à pergunta."""
    text(query, 2000)
    if (
        type(limit) is not int
        or not 1 <= limit <= 5
        or not isinstance(topics, list)
        or any(not isinstance(topic, str) or topic not in TOPICS for topic in topics)
    ):
        raise ValueError(_("Filtro da biblioteca inválido."))
    stopwords = {
        "como",
        "para",
        "uma",
        "que",
        "por",
        "com",
        "das",
        "dos",
        "the",
        "and",
        "how",
        "can",
        "with",
        "what",
        "los",
        "las",
        "una",
        "del",
        "quiero",
    }
    terms = set(re.findall(r"[a-z0-9_]{3,}", normalized(query))) - stopwords
    ranked = []
    for source in corpus.sources:
        if topics and not set(topics).intersection(source["topics"]):
            continue
        haystack = normalized(
            " ".join(
                [
                    source["title"],
                    source["summary_pt_br"],
                    source["evidence_quote"],
                    *source["topics"],
                ]
            )
        )
        words = set(re.findall(r"[a-z0-9_]{3,}", haystack))
        score = len(terms.intersection(words))
        if score:
            ranked.append((score, source))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [source for _, source in ranked[:limit]]
