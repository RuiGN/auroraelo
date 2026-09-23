"""Master panel URL configuration."""

from django.urls import path

from master_panel.views.billing import (
    tenant_billing_portal,
    tenant_checkout,
)
from master_panel.views.dashboard import dashboard
from master_panel.views.tenants import (
    tenant_block,
    tenant_create,
    tenant_detail,
    tenant_list,
    tenant_unblock,
)
from master_panel.views.users import (
    invitation_revoke as master_invitation_revoke,
)
from master_panel.views.users import (
    user_edit,
    user_invite,
    user_list,
)
from master_panel.views.webhooks import stripe_webhook

app_name = "master_panel"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("tenants/", tenant_list, name="tenant_list"),
    path("tenants/create/", tenant_create, name="tenant_create"),
    path("tenants/<uuid:clinic_id>/", tenant_detail, name="tenant_detail"),
    path("tenants/<uuid:clinic_id>/block/", tenant_block, name="tenant_block"),
    path("tenants/<uuid:clinic_id>/unblock/", tenant_unblock, name="tenant_unblock"),
    path(
        "tenants/<uuid:clinic_id>/billing/portal/",
        tenant_billing_portal,
        name="tenant_billing_portal",
    ),
    path(
        "tenants/<uuid:clinic_id>/billing/checkout/",
        tenant_checkout,
        name="tenant_checkout",
    ),
    path("users/", user_list, name="user_list"),
    path("users/invite/", user_invite, name="user_invite"),
    path(
        "users/memberships/<uuid:membership_id>/edit/",
        user_edit,
        name="user_edit",
    ),
    path(
        "users/invitations/<uuid:invitation_id>/revoke/",
        master_invitation_revoke,
        name="master_invitation_revoke",
    ),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
]
