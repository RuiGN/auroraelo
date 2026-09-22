"""Master panel — tenant CRUD and block/unblock views."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from clinics.models import Clinic
from master_panel.models import TenantSubscription, TenantUsageSnapshot
from master_panel.services import create_stripe_customer


@staff_member_required(login_url="/accounts/login/")
def tenant_list(request: HttpRequest) -> HttpResponse:
    subscriptions = (
        TenantSubscription.objects.select_related("clinic")
        .order_by("-created_at")
    )
    q = request.GET.get("q", "").strip()
    if q:
        subscriptions = subscriptions.filter(clinic__name__icontains=q)
    status_filter = request.GET.get("status", "")
    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)

    return render(
        request,
        "master_panel/tenant_list.html",
        {
            "page_title": "Tenants",
            "subscriptions": subscriptions,
            "q": q,
            "status_filter": status_filter,
            "status_choices": TenantSubscription.Status.choices,
        },
    )


@staff_member_required(login_url="/accounts/login/")
def tenant_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("admin_email", "").strip()
        plan = request.POST.get("plan", "free")

        if not name or not email:
            messages.error(request, "Nome da clínica e e-mail do administrador são obrigatórios.")
            return render(request, "master_panel/tenant_create.html", {
                "page_title": "Nova Clínica",
                "plan_choices": TenantSubscription.Plan.choices,
            })

        slug_base = slugify(name)
        slug = slug_base
        counter = 1
        while Clinic.infrastructure_objects.filter(slug=slug).exists():
            slug = f"{slug_base}-{counter}"
            counter += 1

        with transaction.atomic():
            clinic = Clinic(name=name, slug=slug, is_active=True)
            clinic.save()

            # Create Stripe customer (silently skip if no API key configured).
            stripe_customer_id = ""
            try:
                stripe_customer_id = create_stripe_customer(name, email)
            except Exception:
                pass

            sub = TenantSubscription.objects.create(
                clinic=clinic,
                plan=plan,
                status=TenantSubscription.Status.TRIALING,
                stripe_customer_id=stripe_customer_id,
            )

        messages.success(request, f"Clínica «{name}» criada com sucesso.")
        return redirect("master_panel:tenant_detail", clinic_id=clinic.pk)

    return render(
        request,
        "master_panel/tenant_create.html",
        {
            "page_title": "Nova Clínica",
            "plan_choices": TenantSubscription.Plan.choices,
        },
    )


@staff_member_required(login_url="/accounts/login/")
def tenant_detail(request: HttpRequest, clinic_id) -> HttpResponse:
    clinic = get_object_or_404(Clinic.infrastructure_objects, pk=clinic_id)
    sub, _ = TenantSubscription.objects.get_or_create(
        clinic=clinic,
        defaults={"status": TenantSubscription.Status.TRIALING},
    )
    snapshots = TenantUsageSnapshot.objects.filter(clinic=clinic).order_by("-snapshot_at")[:30]

    return render(
        request,
        "master_panel/tenant_detail.html",
        {
            "page_title": clinic.name,
            "clinic": clinic,
            "sub": sub,
            "snapshots": snapshots,
            "plan_choices": TenantSubscription.Plan.choices,
        },
    )


@staff_member_required(login_url="/accounts/login/")
@require_POST
def tenant_block(request: HttpRequest, clinic_id) -> HttpResponse:
    clinic = get_object_or_404(Clinic.infrastructure_objects, pk=clinic_id)
    sub = get_object_or_404(TenantSubscription, clinic=clinic)
    reason = request.POST.get("reason", "Bloqueio administrativo.").strip()
    sub.block(reason=reason)
    messages.warning(request, f"Clínica «{clinic.name}» bloqueada.")
    return redirect("master_panel:tenant_detail", clinic_id=clinic_id)


@staff_member_required(login_url="/accounts/login/")
@require_POST
def tenant_unblock(request: HttpRequest, clinic_id) -> HttpResponse:
    clinic = get_object_or_404(Clinic.infrastructure_objects, pk=clinic_id)
    sub = get_object_or_404(TenantSubscription, clinic=clinic)
    sub.unblock()
    messages.success(request, f"Clínica «{clinic.name}» desbloqueada.")
    return redirect("master_panel:tenant_detail", clinic_id=clinic_id)
