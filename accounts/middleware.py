"""Session lifetime and privileged multifactor enforcement."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterable, Iterator
from typing import cast

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest
from django.http.response import HttpResponseBase, StreamingHttpResponse
from django.shortcuts import redirect
from django.utils import translation
from django.utils.cache import patch_vary_headers

from .language_preferences import valid_profile_language
from .models import User
from .services import register_current_session, validate_current_session


class AccountSecurityMiddleware:
    """Enforce session revocation and expiration before navigation."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        actor = request.user if isinstance(request.user, User) else None
        if actor is None or not actor.is_authenticated:
            return self.get_response(request)
        if not validate_current_session(request=request, user=actor):
            logout(request)
            return redirect("account_login")
        account_session = register_current_session(request=request, user=actor)
        request.account_session = account_session  # type: ignore[attr-defined]
        return self.get_response(request)


def _restore_language(language: str | None) -> None:
    if language is None:
        translation.deactivate()
    else:
        translation.activate(language)


def _localized_stream(content: Iterable[bytes], language: str) -> Iterator[bytes]:
    """Evaluate lazy streaming content inside its request language context."""
    iterator = iter(content)
    while True:
        previous = translation.get_language()
        try:
            translation.activate(language)
            chunk = next(iterator)
        except StopIteration:
            return
        finally:
            _restore_language(previous)
        yield chunk


async def _localized_async_stream(
    content: AsyncIterable[bytes], language: str
) -> AsyncIterator[bytes]:
    """Evaluate async streaming content without leaking translation context."""
    iterator = aiter(content)
    while True:
        previous = translation.get_language()
        try:
            translation.activate(language)
            chunk = await anext(iterator)
        except StopAsyncIteration:
            return
        finally:
            _restore_language(previous)
        yield chunk


class UserLanguageMiddleware:
    """Give a valid authenticated profile preference highest precedence."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        previous = translation.get_language()
        user = request.user if isinstance(request.user, User) else None
        language = valid_profile_language(user) if user is not None else None
        request_language = getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE)
        effective = language or (
            request_language
            if isinstance(request_language, str)
            else settings.LANGUAGE_CODE
        )
        translation.activate(effective)
        request.LANGUAGE_CODE = effective
        try:
            response = self.get_response(request)
            if response.streaming and isinstance(response, StreamingHttpResponse):
                if response.is_async:
                    response.streaming_content = _localized_async_stream(
                        cast(AsyncIterable[bytes], response.streaming_content),
                        effective,
                    )
                else:
                    response.streaming_content = _localized_stream(
                        cast(Iterable[bytes], response.streaming_content), effective
                    )
            # Respeitar conteúdo com idioma fixado explicitamente pela view.
            response.headers.setdefault("Content-Language", effective)
            if response.get("Content-Type", "").split(";", 1)[0] == "text/html":
                patch_vary_headers(response, ("Cookie", "Accept-Language"))
            return response
        finally:
            _restore_language(previous)
