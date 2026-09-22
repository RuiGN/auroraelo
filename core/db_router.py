"""Database router for read-replica offloading.

Routes read-only queries to the ``replica`` database alias when available.
Only safe, analytics-oriented apps are offloaded; transactional domains
always use the primary to avoid stale reads in state machines.

Activate by setting ``DATABASE_ROUTERS`` in settings and configuring
``DATABASES["replica"]`` in production.
"""

from __future__ import annotations

from typing import Any

from django.db import models

# Apps whose reads can safely go to a replica (no strong consistency needed).
_REPLICA_SAFE_APPS: frozenset[str] = frozenset(
    {
        "analytics",
        "audit",
    }
)


class ReadReplicaRouter:
    """Route analytics reads to replica, everything else to primary."""

    def db_for_read(self, model: type[models.Model], **hints: Any) -> str:
        """Direct replica-safe app reads to the replica database."""
        from django.conf import settings

        if (
            model._meta.app_label in _REPLICA_SAFE_APPS
            and "replica" in settings.DATABASES
        ):
            return "replica"
        return "default"

    def db_for_write(self, model: type[models.Model], **hints: Any) -> str:
        """All writes go to the primary database."""
        return "default"

    def allow_relation(
        self,
        obj1: models.Model,
        obj2: models.Model,
        **hints: Any,
    ) -> bool:
        """Allow relations between all databases (same logical dataset)."""
        return True

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        **hints: Any,
    ) -> bool:
        """Only allow migrations on the primary database."""
        return db == "default"
