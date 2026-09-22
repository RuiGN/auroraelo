"""Master panel — Stripe webhook endpoint."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from master_panel.services import construct_webhook_event, handle_stripe_event

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Receive and process Stripe webhook events."""
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except Exception as exc:
        logger.warning("Stripe webhook signature validation failed: %s", exc)
        return JsonResponse({"error": "Invalid signature."}, status=400)

    try:
        handle_stripe_event(event)
    except Exception as exc:
        logger.exception("Error handling Stripe event %s: %s", event.get("type"), exc)
        return JsonResponse({"error": "Internal error."}, status=500)

    return JsonResponse({"status": "ok"})
