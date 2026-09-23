"""Master panel — dashboard view with KPIs and charts."""

import json
from collections import Counter
from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from master_panel.tenant_services import latest_usage_snapshots, tenant_panel_rows


@staff_member_required(login_url="/master/login/")
def dashboard(request: HttpRequest) -> HttpResponse:
    """Main master panel dashboard with KPIs and every infrastructure clinic."""
    rows = tenant_panel_rows()
    total_tenants = len(rows)
    active_tenants = sum(row.status in {"active", "trialing"} for row in rows)
    blocked_tenants = sum(row.status == "blocked" for row in rows)
    past_due_tenants = sum(row.status == "past_due" for row in rows)

    plan_counts = Counter(row.plan for row in rows)
    plan_labels = list(plan_counts)
    plan_data = [plan_counts[label] for label in plan_labels]

    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_counts: Counter[str] = Counter()
    for row in rows:
        if row.clinic.created_at >= twelve_months_ago:
            month = row.clinic.created_at.strftime("%Y-%m")
            monthly_counts[month] += 1
    month_keys = sorted(monthly_counts)
    monthly_labels = [
        datetime.strptime(month, "%Y-%m").strftime("%b/%Y") for month in month_keys
    ]
    monthly_data = [monthly_counts[month] for month in month_keys]

    latest_snapshots = latest_usage_snapshots()
    top_clinics = sorted(
        latest_snapshots,
        key=lambda snapshot: snapshot.active_users,
        reverse=True,
    )[:10]
    top_names = [snapshot.clinic.name for snapshot in top_clinics]
    top_users = [snapshot.active_users for snapshot in top_clinics]
    top_storage = [float(snapshot.storage_mb) for snapshot in top_clinics]

    context = {
        "page_title": "Painel Master",
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "blocked_tenants": blocked_tenants,
        "past_due_tenants": past_due_tenants,
        "chart_plan_labels": json.dumps(plan_labels),
        "chart_plan_data": json.dumps(plan_data),
        "chart_monthly_labels": json.dumps(monthly_labels),
        "chart_monthly_data": json.dumps(monthly_data),
        "chart_top_names": json.dumps(top_names),
        "chart_top_users": json.dumps(top_users),
        "chart_top_storage": json.dumps(top_storage),
        "recent_subs": rows[:10],
    }
    return render(request, "master_panel/dashboard.html", context)
