"""Authorization policy contract."""

from typing import Any, Protocol, TypeVar

from django.contrib.auth.base_user import AbstractBaseUser

SubjectT = TypeVar("SubjectT", contravariant=True)
ResourceT = TypeVar("ResourceT", contravariant=True)


class AuthorizationPolicy(Protocol[SubjectT, ResourceT]):
    """Decide whether a subject may act on a resource."""

    def is_allowed(self, subject: SubjectT, resource: ResourceT, /) -> bool:
        """Return the explicit authorization decision."""
        ...


def current_actor_is_active(actor: AbstractBaseUser) -> bool:
    """Confirm a framework user still exists and is active in its own store."""
    model = getattr(getattr(actor, "_meta", None), "model", type(actor))
    manager: Any = getattr(model, "_default_manager", None)
    return bool(
        actor.is_authenticated
        and actor.pk is not None
        and manager is not None
        and manager.filter(pk=actor.pk, is_active=True).exists()
    )


_TENANT_INDEPENDENT_PATHS = frozenset(
    {
        "/api/v1/recovery/library/",
        "/api/v1/recovery/assistant/",
        "/psiquiatria/login/",
        "/psiquiatria/api/v1/mind/breathing/",
        "/psiquiatria/api/v1/mobile/b2c/breathing/",
        "/psiquiatria/api/v1/mind/mood/",
        "/psiquiatria/api/v1/mind/cbt-diary/",
        "/psiquiatria/api/v1/mind/subscription/",
        "/psiquiatria/api/v1/mobile/b2c/mood/",
        "/psiquiatria/api/v1/mobile/b2c/cbt-diary/",
        "/psiquiatria/api/v1/mobile/b2c/subscription/",
    }
)


def is_tenant_independent_path(path: str) -> bool:
    """Dispensar somente tenant em rotas exatas; sessão/CSRF continuam obrigatórios."""
    return path in _TENANT_INDEPENDENT_PATHS


__all__ = [
    "AuthorizationPolicy",
    "current_actor_is_active",
    "is_tenant_independent_path",
]
