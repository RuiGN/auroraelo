"""Rotas web do diário compartilhado pelo paciente (equipe da clínica)."""

from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path(
        "pacientes/<uuid:patient_id>/",
        views.patient_diary,
        name="patient_diary",
    ),
    path(
        "pacientes/<uuid:patient_id>/checkins/",
        views.patient_checkins,
        name="patient_checkins",
    ),
    path(
        "pacientes/<uuid:patient_id>/registros/<uuid:entry_id>/pedir-acesso/",
        views.access_request_create,
        name="access_request_create",
    ),
]
