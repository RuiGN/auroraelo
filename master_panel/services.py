"""Stripe integration services for the master control panel."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _stripe():
    """Return the stripe module, configured with the secret key."""
    import stripe as _stripe_lib

    _stripe_lib.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    return _stripe_lib


def create_stripe_customer(clinic_name: str, email: str) -> str:
    """Create a Stripe customer for a new tenant and return the customer ID."""
    stripe = _stripe()
    customer = stripe.Customer.create(
        name=clinic_name,
        email=email,
        metadata={"source": "aurora_elo_master_panel"},
    )
    return customer["id"]


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session and return its URL."""
    stripe = _stripe()
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        billing_address_collection="required",
    )
    return session["url"]


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Return a Stripe Customer Portal URL for self-service billing management."""
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session["url"]


def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
    """Parse and verify an incoming Stripe webhook event."""
    stripe = _stripe()
    return stripe.Webhook.construct_event(
        payload,
        sig_header,
        getattr(settings, "STRIPE_WEBHOOK_SECRET", ""),
    )


def handle_stripe_event(event: Any) -> None:
    """Dispatch a verified Stripe event to the appropriate handler."""
    from master_panel.models import TenantSubscription

    event_type: str = event["type"]
    data: dict[str, Any] = event["data"]["object"]

    logger.info("Stripe webhook received: %s", event_type)

    handlers = {
        "customer.subscription.created": _on_subscription_created,
        "customer.subscription.updated": _on_subscription_updated,
        "customer.subscription.deleted": _on_subscription_deleted,
        "invoice.payment_succeeded": _on_payment_succeeded,
        "invoice.payment_failed": _on_payment_failed,
        "checkout.session.completed": _on_checkout_completed,
    }

    handler = handlers.get(event_type)
    if handler:
        handler(data)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)


def _subscription_by_stripe_id(sub_id: str):
    from master_panel.models import TenantSubscription

    try:
        return TenantSubscription.objects.get(stripe_subscription_id=sub_id)
    except TenantSubscription.DoesNotExist:
        return None


def _subscription_by_customer_id(customer_id: str):
    from master_panel.models import TenantSubscription

    try:
        return TenantSubscription.objects.get(stripe_customer_id=customer_id)
    except TenantSubscription.DoesNotExist:
        return None


@transaction.atomic
def _on_subscription_created(data: dict[str, Any]) -> None:
    sub = _subscription_by_customer_id(data.get("customer", ""))
    if not sub:
        return
    sub.stripe_subscription_id = data["id"]
    sub.status = _map_stripe_status(data["status"])
    sub.current_period_end = _ts_to_dt(data.get("current_period_end"))
    sub.save()


@transaction.atomic
def _on_subscription_updated(data: dict[str, Any]) -> None:
    sub = _subscription_by_stripe_id(data["id"])
    if not sub:
        return
    new_status = _map_stripe_status(data["status"])
    # Do not override a manual block.
    if sub.status != "blocked":
        sub.status = new_status
    sub.current_period_end = _ts_to_dt(data.get("current_period_end"))
    sub.save()


@transaction.atomic
def _on_subscription_deleted(data: dict[str, Any]) -> None:
    sub = _subscription_by_stripe_id(data["id"])
    if not sub:
        return
    sub.block(reason="Assinatura cancelada no Stripe.")


@transaction.atomic
def _on_payment_succeeded(data: dict[str, Any]) -> None:
    customer_id = data.get("customer", "")
    sub = _subscription_by_customer_id(customer_id)
    if not sub:
        return
    if sub.status == "past_due":
        sub.status = "active"
        sub.save(update_fields=["status", "updated_at"])


@transaction.atomic
def _on_payment_failed(data: dict[str, Any]) -> None:
    customer_id = data.get("customer", "")
    sub = _subscription_by_customer_id(customer_id)
    if not sub:
        return
    if sub.status not in ("blocked", "canceled"):
        sub.status = "past_due"
        sub.save(update_fields=["status", "updated_at"])


@transaction.atomic
def _on_checkout_completed(data: dict[str, Any]) -> None:
    customer_id = data.get("customer", "")
    sub = _subscription_by_customer_id(customer_id)
    if not sub:
        return
    sub.stripe_subscription_id = data.get("subscription", "")
    sub.status = "active"
    sub.save(update_fields=["stripe_subscription_id", "status", "updated_at"])


def _map_stripe_status(stripe_status: str) -> str:
    mapping = {
        "trialing": "trialing",
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
        "paused": "past_due",
    }
    return mapping.get(stripe_status, "past_due")


def _ts_to_dt(timestamp) -> "timezone.datetime | None":
    if timestamp is None:
        return None
    from datetime import datetime, UTC

    return datetime.fromtimestamp(timestamp, tz=UTC)


def capture_usage_snapshot(clinic) -> None:
    """Collect and persist a usage snapshot for the given clinic."""
    from accounts.models import User
    from master_panel.models import TenantUsageSnapshot

    active_users = (
        User.infrastructure_objects.filter(
            clinicmembership__clinic=clinic,
            clinicmembership__is_active=True,
        )
        .distinct()
        .count()
    )

    TenantUsageSnapshot.objects.create(
        clinic=clinic,
        active_users=active_users,
    )
