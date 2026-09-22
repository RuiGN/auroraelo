"""Master panel — dashboard view with KPIs and charts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, UTC

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpRequest, HttpResponse

from clinics.models import Clinic
from master_panel.models import TenantSubscription, TenantUsageSnapshot


@staff_member_required(login_url="/accounts/login/")
def dashboard(request: HttpRequest) -> HttpResponse:
    """Main master panel dashboard with KPIs and Chart.js charts."""
    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_tenants = TenantSubscription.objects.count()
    active_tenants = TenantSubscription.objects.filter(
        status__in=["active", "trialing"]
    ).count()
    blocked_tenants = TenantSubscription.objects.filter(status="blocked").count()
    past_due_tenants = TenantSubscription.objects.filter(status="past_due").count()

    # Plan distribution for donut chart
    plan_counts = list(
        TenantSubscription.objects.values("plan").annotate(n=Count("id"))
    )
    plan_labels = [d["plan"] for d in plan_counts]
    plan_data = [d["n"] for d in plan_counts]

    # ── New tenants by month (last 12 months) ─────────────────────────────────
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_tenants = (
        TenantSubscription.objects.filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(n=Count("id"))
        .order_by("month")
    )
    monthly_labels = [
        d["month"].strftime("%b/%Y") for d in monthly_tenants
    ]
    monthly_data = [d["n"] for d in monthly_tenants]

    # ── Top 10 tenants by active users (latest snapshot) ─────────────────────
    latest_snapshots = (
        TenantUsageSnapshot.objects.order_by("clinic_id", "-snapshot_at")
        .distinct("clinic_id")
        .select_related("clinic")[:10]
    )
    top_clinics = sorted(latest_snapshots, key=lambda s: s.active_users, reverse=True)[
        :10
    ]
    top_names = [s.clinic.name for s in top_clinics]
    top_users = [s.active_users for s in top_clinics]
    top_storage = [float(s.storage_mb) for s in top_clinics]

    # ── Recent tenants ────────────────────────────────────────────────────────
    recent_subs = (
        TenantSubscription.objects.select_related("clinic")
        .order_by("-created_at")[:10]
    )

    context = {
        "page_title": "Painel Master",
        # KPIs
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "blocked_tenants": blocked_tenants,
        "past_due_tenants": past_due_tenants,
        # Charts — serialised as JSON for Chart.js
        "chart_plan_labels": json.dumps(plan_labels),
        "chart_plan_data": json.dumps(plan_data),
        "chart_monthly_labels": json.dumps(monthly_labels),
        "chart_monthly_data": json.dumps(monthly_data),
        "chart_top_names": json.dumps(top_names),
        "chart_top_users": json.dumps(top_users),
        "chart_top_storage": json.dumps(top_storage),
        # Table
        "recent_subs": recent_subs,
    }
    return render(request, "master_panel/dashboard.html", context)
