"""Contadores mínimos e efêmeros; nunca guarda mensagens, sessões ou relatos."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any
from uuid import UUID

import redis
from django.conf import settings

from .recovery_knowledge import KnowledgeUnavailableError

_SCRIPT = """
for i = 1, #KEYS do
  local raw = redis.call('GET', KEYS[i])
  local count = tonumber(raw or '0')
  if not count or count < 0 or (raw and redis.call('TTL', KEYS[i]) < 0) then
    return -1
  end
  if count >= tonumber(ARGV[i * 2 - 1]) then return 0 end
end
for i = 1, #KEYS do
  local count = redis.call('INCR', KEYS[i])
  if count == 1 then redis.call('EXPIRE', KEYS[i], ARGV[i * 2]) end
end
return 1
"""


class UsageExceededError(RuntimeError):
    pass


def consume_usage(client: Any, actor_id: UUID) -> None:
    try:
        secret = getattr(settings, "RECOVERY_USAGE_HMAC_KEY", "")
        if (
            not isinstance(secret, str)
            or len(secret) < 32
            or not isinstance(actor_id, UUID)
        ):
            raise ValueError
        limits = [
            getattr(settings, "RECOVERY_USAGE_PER_MINUTE", 10),
            getattr(settings, "RECOVERY_USAGE_PER_DAY", 100),
            getattr(settings, "RECOVERY_USAGE_GLOBAL_PER_DAY", 10000),
        ]
        ceilings = [60, 1000, 100000]
        if any(
            type(limit) is not int or not 1 <= limit <= ceiling
            for limit, ceiling in zip(limits, ceilings, strict=True)
        ):
            raise ValueError
        digest = hmac.new(
            secret.encode(), str(actor_id).encode(), hashlib.sha256
        ).hexdigest()
        prefix = "auroraelo:recovery-usage:"
        keys = [
            f"{prefix}{digest}:minute",
            f"{prefix}{digest}:day",
            f"{prefix}global:day",
        ]
        result = client.eval(
            _SCRIPT, 3, *keys, limits[0], 60, limits[1], 86400, limits[2], 86400
        )
        if result == 0:
            raise UsageExceededError
        if result != 1:
            raise ValueError
    except (redis.RedisError, TypeError, ValueError) as exc:
        raise KnowledgeUnavailableError("Contador de uso indisponível.") from exc
