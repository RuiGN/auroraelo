"""Rotas web do painel da equipe sobre o acesso do paciente ao aplicativo."""

from django.urls import path

from . import views

app_name = "mobile_api"

urlpatterns = [
    path("<uuid:patient_id>/", views.patient_app, name="patient_app"),
    path(
        "<uuid:patient_id>/convite/",
        views.invitation_send,
        name="invitation_send",
    ),
    path(
        "<uuid:patient_id>/aparelhos/revogar-todos/",
        views.devices_revoke_all,
        name="devices_revoke_all",
    ),
    path(
        "<uuid:patient_id>/aparelhos/<uuid:session_id>/revogar/",
        views.device_revoke,
        name="device_revoke",
    ),
]
