"""Resolve and persist allowlisted user interface language preferences."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest

from .models import User


def published_language_codes() -> tuple[str, ...]:
    """Return the deployment's reviewed, publicly available language codes."""
    return tuple(code for code, _name in settings.LANGUAGES)


def valid_profile_language(user: User) -> str | None:
    """Return an explicit profile preference only while it remains published."""
    preference = user.preferred_language
    return preference if preference in published_language_codes() else None


def save_authenticated_preference(request: HttpRequest, language: str) -> None:
    """Persist a manual preference only for a validated managed session."""
    user = request.user
    account_session = getattr(request, "account_session", None)
    if (
        isinstance(user, User)
        and user.is_authenticated
        and account_session is not None
        and getattr(account_session, "user_id", None) == user.pk
    ):
        user.preferred_language = language
        user.save(update_fields=("preferred_language",))
