"""Redis State Engine for Aurora Elo Addiction & 12 Steps Recovery.

Provides high-performance transient state storage for:
- 12 Steps multi-step interactive anamnesis with live draft auto-saving.
- Real-time Craving/Fissura telemetry with threshold escalation (>7 triggers emergency alert).
- Sobriety streak & clean-time caching.
"""

import json
import logging
from typing import Any, Optional
from django.conf import settings

logger = logging.getLogger("application")

# In-memory fallback dictionary for testing or when Redis is not available
_MEMORY_FALLBACK: dict[str, Any] = {}


def get_redis_client():
    """Return a configured Redis client or None if unavailable."""
    try:
        import redis
        redis_url = getattr(settings, "REDIS_STATE_URL", "redis://redis:6379/3")
        client = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis State Server unavailable (%s). Using local fallback store.", str(e))
        return None


class TwelveStepsRedisService:
    """Manages 12-Step wizard progress and real-time state in Redis."""

    DRAFT_PREFIX = "auroraelo:12steps:draft:"
    CRAVING_PREFIX = "auroraelo:craving:active:"
    STREAK_PREFIX = "auroraelo:streak:"
    TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days draft persistence

    @classmethod
    def save_step_draft(cls, session_id: str, step_number: int, step_data: dict) -> bool:
        """Saves intermediate step progress into Redis."""
        key = f"{cls.DRAFT_PREFIX}{session_id}"
        client = get_redis_client()
        payload = cls.get_session_draft(session_id) or {
            "session_id": session_id,
            "completed_steps": [],
            "steps": {},
        }
        payload["steps"][f"step_{step_number}"] = step_data
        if step_number not in payload["completed_steps"]:
            payload["completed_steps"].append(step_number)
            payload["completed_steps"].sort()
        payload["last_step"] = step_number

        serialized = json.dumps(payload, ensure_ascii=False)
        if client:
            try:
                client.setex(key, cls.TTL_SECONDS, serialized)
                return True
            except Exception as e:
                logger.error("Failed to write draft to Redis: %s", str(e))
        
        _MEMORY_FALLBACK[key] = serialized
        return True

    @classmethod
    def get_session_draft(cls, session_id: str) -> Optional[dict]:
        """Retrieves active 12-step draft from Redis."""
        key = f"{cls.DRAFT_PREFIX}{session_id}"
        client = get_redis_client()
        raw = None
        if client:
            try:
                raw = client.get(key)
            except Exception as e:
                logger.error("Failed to read draft from Redis: %s", str(e))

        if not raw:
            raw = _MEMORY_FALLBACK.get(key)

        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    @classmethod
    def clear_draft(cls, session_id: str) -> bool:
        """Deletes draft once consolidated into PostgreSQL."""
        key = f"{cls.DRAFT_PREFIX}{session_id}"
        client = get_redis_client()
        if client:
            try:
                client.delete(key)
            except Exception:
                pass
        _MEMORY_FALLBACK.pop(key, None)
        return True

    @classmethod
    def record_craving_spike(cls, patient_cpf: str, intensity: int, urge_target: str) -> dict:
        """Records high-priority craving in Redis with automatic expiration."""
        key = f"{cls.CRAVING_PREFIX}{patient_cpf}"
        alert_level = "CRITICAL" if intensity >= 8 else ("HIGH" if intensity >= 6 else "MODERATE")
        data = {
            "cpf": patient_cpf,
            "intensity": intensity,
            "urge_target": urge_target,
            "alert_level": alert_level,
            "requires_intervention": intensity >= 7,
        }
        client = get_redis_client()
        if client:
            try:
                client.setex(key, 3600 * 4, json.dumps(data))
            except Exception:
                pass
        _MEMORY_FALLBACK[key] = json.dumps(data)
        return data

    @classmethod
    def get_active_craving_alert(cls, patient_cpf: str) -> Optional[dict]:
        """Checks if a patient has an active high-intensity craving recorded in Redis."""
        key = f"{cls.CRAVING_PREFIX}{patient_cpf}"
        client = get_redis_client()
        raw = None
        if client:
            try:
                raw = client.get(key)
            except Exception:
                pass
        if not raw:
            raw = _MEMORY_FALLBACK.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None
