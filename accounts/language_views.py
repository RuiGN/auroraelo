"""HTTP endpoint for an explicit user interface language choice."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.i18n import LANGUAGE_QUERY_PARAMETER, set_language

from .language_preferences import (
    published_language_codes,
    save_authenticated_preference,
)


@require_POST
def account_set_language(request: HttpRequest) -> HttpResponse:
    """Apply one published language and persist it for a managed identity."""
    language = request.POST.get(LANGUAGE_QUERY_PARAMETER, "")
    if language not in published_language_codes():
        return HttpResponseBadRequest(_("Unsupported language."))
    response = set_language(request)
    save_authenticated_preference(request, language)
    return response
