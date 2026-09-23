"""Administração global de identidades, separada do painel de tenants."""

from django.urls import path

from master_panel.views.users import (
    invitation_revoke,
    user_edit,
    user_invite,
    user_list,
)

app_name = "administration"

urlpatterns = [
    path("", user_list, name="user_list"),
    path("convites/", user_invite, name="user_invite"),
    path("vinculos/<uuid:membership_id>/", user_edit, name="user_edit"),
    path(
        "convites/<uuid:invitation_id>/revogar/",
        invitation_revoke,
        name="invitation_revoke",
    ),
]
