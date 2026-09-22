"""Project URL configuration."""

from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from .views import (
    admin_login_redirect,
    confirm_clinic_switch,
    design_system_reference,
    home,
    liveness,
    readiness,
    review_clinic_switch,
    save_workspace_layout,
    workspace_detached,
    workspace_vertical,
)

from core.metrics import metrics_view

from api import api

handler400 = "config.views.bad_request"
handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"

from accounts.views import master_login

urlpatterns = [
    path("", home, name="home"),
    path("master/login/", master_login, name="master_login"),
    path("master/", include("master_panel.urls", namespace="master_panel")),
    path("accounts/", include("accounts.urls")),
    path("clinics/", include("clinics.urls")),
    path("people/", include("people.urls")),
    path("consents/", include("consents.urls")),
    path("journal/", include("journal.urls")),
    path("goals/", include("goals.urls")),
    path("agenda/", include("scheduling.urls")),
    path("analytics/", include("analytics.urls")),
    path("financeiro/", include("finance.urls")),
    path("onboarding/", include("onboarding.urls")),
    path("conteudos/", include("content.urls")),
    path("dashboard/", include("therapist_dashboard.urls")),
    path("psiquiatria/", include("psychiatry.urls")),
    path("api/v1/clinical-operations/", include("clinical_operations.urls")),
    path("api/v1/", api.urls),
    path("", include("ai_assistant.urls")),
    path("design-system/", design_system_reference, name="design_system_reference"),
    path("workspace/", workspace_vertical, name="workspace_vertical"),
    path("workspace/detached/", workspace_detached, name="workspace_detached"),
    path(
        "workspace/preferences/layout/",
        save_workspace_layout,
        name="workspace_layout_preference",
    ),
    path("clinics/switch/review/", review_clinic_switch, name="clinic_switch_review"),
    path(
        "clinics/switch/confirm/", confirm_clinic_switch, name="clinic_switch_confirm"
    ),
    path("health/live/", liveness, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("health/metrics/", metrics_view, name="health-metrics"),
    path(
        "admin/login/",
        admin_login_redirect,
        name="admin_login",
    ),
    path(
        "jsi18n/",
        JavaScriptCatalog.as_view(domain="djangojs"),
        name="javascript-catalog",
    ),
    path("admin/", admin.site.urls),
]
