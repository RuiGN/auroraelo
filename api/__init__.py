"""AuroraElo REST API v1 — Django Ninja application with automatic OpenAPI.

Provides authenticated, tenant-scoped JSON endpoints that delegate to
the existing Services/Selectors layer. Session-authenticated web clients
and Bearer-token API clients are both supported.

OpenAPI documentation is available at ``/api/v1/docs/`` (staff-only).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError, ValidationError
from ninja.security import HttpBearer, django_auth


class SessionOrBearerAuth(HttpBearer):
    """Authenticate API requests via Django session or Bearer token.

    - Browser clients use the existing session cookie (CSRF-protected).
    - Mobile / machine clients use a ``Bearer <token>`` header.
    """

    def authenticate(self, request: HttpRequest, token: str) -> Any:
        # Django session auth is handled by django_auth; this class
        # handles the Bearer path only.
        if request.user.is_authenticated:
            return request.user
        # The patient app's access tokens are accepted only by ``/api/v1/mobile/``
        # routes (``api.mobile_common.PatientBearerAuth``). They never authenticate
        # the generic routers below, which stay session-only.
        return None


api = NinjaAPI(
    title="AuroraElo API",
    version="1.0.0",
    description=(
        "Clinical management and therapeutic support platform API. "
        "All endpoints require authentication and operate within a "
        "tenant clinic context."
    ),
    urls_namespace="api-v1",
    auth=[django_auth, SessionOrBearerAuth()],
    docs_url="/docs/",
    openapi_url="/openapi.json",
)


# ── Error handlers ───────────────────────────────────────────────────────────


@api.exception_handler(AuthenticationError)
def on_auth_error(request: HttpRequest, exc: AuthenticationError) -> Any:
    return api.create_response(
        request,
        {"detail": "Autenticação necessária."},
        status=401,
    )


@api.exception_handler(HttpError)
def on_http_error(request: HttpRequest, exc: HttpError) -> Any:
    return api.create_response(
        request,
        {"detail": str(exc)},
        status=exc.status_code,
    )


@api.exception_handler(ValidationError)
def on_validation_error(request: HttpRequest, exc: ValidationError) -> Any:
    return api.create_response(
        request,
        {"detail": "Dados inválidos.", "errors": exc.errors},
        status=422,
    )


# ── Health ───────────────────────────────────────────────────────────────────


@api.get("/ping/", auth=None, tags=["Health"])
def api_ping(request: HttpRequest) -> dict[str, str]:
    """Verify API availability without authentication."""
    return {"status": "ok", "version": "1.0.0"}


# ── Domain routers ───────────────────────────────────────────────────────────

from api.goals_api import router as goals_router  # noqa: E402
from api.journal_api import router as journal_router  # noqa: E402
from api.mobile_agenda_api import router as mobile_agenda_router  # noqa: E402
from api.mobile_auth_api import router as mobile_auth_router  # noqa: E402
from api.mobile_authoring_api import router as mobile_authoring_router  # noqa: E402
from api.mobile_care_api import router as mobile_care_router  # noqa: E402
from api.mobile_diary_api import router as mobile_diary_router  # noqa: E402
from api.mobile_patient_api import router as mobile_patient_router  # noqa: E402
from api.mobile_recovery_api import help_router as mobile_help_router  # noqa: E402
from api.mobile_recovery_api import router as mobile_recovery_router  # noqa: E402
from api.mobile_support_api import router as mobile_support_router  # noqa: E402
from api.scheduling_api import router as scheduling_router  # noqa: E402

api.add_router("/journal/", journal_router)
api.add_router("/goals/", goals_router)
api.add_router("/scheduling/", scheduling_router)

# App do paciente (pós-alta): só token de acesso, nunca cookie de sessão.
api.add_router("/mobile/auth/", mobile_auth_router)
api.add_router("/mobile/", mobile_patient_router)
api.add_router("/mobile/", mobile_care_router)
api.add_router("/mobile/", mobile_diary_router)
api.add_router("/mobile/", mobile_agenda_router)
api.add_router("/mobile/", mobile_recovery_router)
api.add_router("/mobile/", mobile_help_router)
api.add_router("/mobile/", mobile_support_router)
api.add_router("/mobile/", mobile_authoring_router)
