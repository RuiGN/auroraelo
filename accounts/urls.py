"""English-language endpoint names for account authentication flows."""

from django.urls import path

from .language_views import account_set_language
from .team_views import (
    team_list,
    team_resend_invitation,
    team_revoke_invitation,
    team_set_active,
)
from .views import (
    account_login,
    account_logout,
    account_sessions,
    invitation_accept,
    invitation_issue,
    invitation_revoke,
    password_recovery,
    password_reset,
    password_reset_complete,
)

urlpatterns = [
    path("language/", account_set_language, name="account_set_language"),
    path("login/", account_login, name="account_login"),
    path("logout/", account_logout, name="account_logout"),
    path("team/", team_list, name="team_list"),
    path(
        "team/<uuid:membership_id>/active/",
        team_set_active,
        name="team_set_active",
    ),
    path(
        "team/invitations/<uuid:invitation_id>/revoke/",
        team_revoke_invitation,
        name="team_revoke_invitation",
    ),
    path(
        "team/invitations/<uuid:invitation_id>/resend/",
        team_resend_invitation,
        name="team_resend_invitation",
    ),
    path("sessions/", account_sessions, name="account_sessions"),
    path("invitations/", invitation_issue, name="invitation_issue"),
    path(
        "invitations/<str:raw_token>/accept/",
        invitation_accept,
        name="invitation_accept",
    ),
    path(
        "invitations/<uuid:invitation_id>/revoke/",
        invitation_revoke,
        name="invitation_revoke",
    ),
    path("password-recovery/", password_recovery, name="password_recovery"),
    path(
        "password-reset/<str:uid>/<str:token>/",
        password_reset,
        name="password_reset",
    ),
    path(
        "password-reset/complete/",
        password_reset_complete,
        name="password_reset_complete",
    ),
]
