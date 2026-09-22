"""Payment enforcement middleware for tenant billing."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


_BYPASS_PREFIXES = (
    "/master/",
    "/health/",
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/password/",
    "/admin/",
    "/static/",
    "/media/",
    "/stripe/",
    "/jsi18n/",
)


class PaymentRequiredMiddleware:
    """Block access to blocked tenants with HTTP 402 Payment Required."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path_info

        # Skip enforcement on bypass paths.
        if any(path.startswith(prefix) for prefix in _BYPASS_PREFIXES):
            return self.get_response(request)

        # Only enforce when a clinic has been resolved.
        clinic = getattr(request, "clinic", None)
        if clinic is None:
            return self.get_response(request)

        # Check subscription status.
        try:
            subscription = clinic.subscription
        except Exception:
            return self.get_response(request)

        if subscription.is_blocked:
            return render(
                request,
                "master_panel/payment_required.html",
                {
                    "clinic": clinic,
                    "subscription": subscription,
                    "support_email": getattr(
                        settings, "DEFAULT_FROM_EMAIL", "suporte@auroraelo.com.br"
                    ),
                },
                status=402,
            )

        return self.get_response(request)
