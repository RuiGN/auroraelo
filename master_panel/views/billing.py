"""Master panel — Stripe billing portal and checkout views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from clinics.models import Clinic
from master_panel.models import TenantSubscription
from master_panel.services import (
    create_billing_portal_session,
    create_checkout_session,
)


@staff_member_required(login_url="/master/login/")
def tenant_billing_portal(request: HttpRequest, clinic_id) -> HttpResponse:
    """Redirect to the Stripe Customer Portal for self-service billing."""
    clinic = get_object_or_404(Clinic.infrastructure_objects, pk=clinic_id)
    sub = get_object_or_404(TenantSubscription, clinic=clinic)

    if not sub.stripe_customer_id:
        messages.error(request, "Esta clínica não possui um Customer no Stripe.")
        return redirect("master_panel:tenant_detail", clinic_id=clinic_id)

    return_url = request.build_absolute_uri(
        reverse("master_panel:tenant_detail", kwargs={"clinic_id": clinic_id})
    )
    try:
        portal_url = create_billing_portal_session(sub.stripe_customer_id, return_url)
        return redirect(portal_url)
    except Exception as exc:
        messages.error(request, f"Erro ao abrir portal Stripe: {exc}")
        return redirect("master_panel:tenant_detail", clinic_id=clinic_id)


@staff_member_required(login_url="/master/login/")
def tenant_checkout(request: HttpRequest, clinic_id) -> HttpResponse:
    """Start a Stripe Checkout session for a new subscription."""
    clinic = get_object_or_404(Clinic.infrastructure_objects, pk=clinic_id)
    sub = get_object_or_404(TenantSubscription, clinic=clinic)

    if not sub.stripe_customer_id:
        messages.error(request, "Esta clínica não possui um Customer no Stripe.")
        return redirect("master_panel:tenant_detail", clinic_id=clinic_id)

    from django.conf import settings

    price_id = getattr(settings, "STRIPE_PRICE_IDS", {}).get(
        sub.plan, getattr(settings, "STRIPE_DEFAULT_PRICE_ID", "")
    )
    if not price_id:
        messages.error(request, "Nenhum Price ID configurado para este plano.")
        return redirect("master_panel:tenant_detail", clinic_id=clinic_id)

    success_url = request.build_absolute_uri(
        reverse("master_panel:tenant_detail", kwargs={"clinic_id": clinic_id})
    ) + "?checkout=success"
    cancel_url = request.build_absolute_uri(
        reverse("master_panel:tenant_detail", kwargs={"clinic_id": clinic_id})
    )

    try:
        checkout_url = create_checkout_session(
            sub.stripe_customer_id, price_id, success_url, cancel_url
        )
        return redirect(checkout_url)
    except Exception as exc:
        messages.error(request, f"Erro ao iniciar checkout Stripe: {exc}")
        return redirect("master_panel:tenant_detail", clinic_id=clinic_id)
