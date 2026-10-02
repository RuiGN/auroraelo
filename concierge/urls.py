"""Rotas web do concierge e do acompanhamento pós-alta."""

from django.urls import path

from . import views

app_name = "concierge"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("contatos/", views.contact_queue, name="contact_queue"),
    path(
        "contatos/<uuid:contact_id>/concluir/",
        views.contact_complete,
        name="contact_complete",
    ),
    path(
        "contatos/<uuid:contact_id>/reagendar/",
        views.contact_reschedule,
        name="contact_reschedule",
    ),
    path(
        "contatos/<uuid:contact_id>/nao-realizado/",
        views.contact_missed,
        name="contact_missed",
    ),
    path("altas/", views.discharge_list, name="discharge_list"),
    path("altas/nova/", views.discharge_create, name="discharge_create"),
    path("altas/<uuid:discharge_id>/", views.discharge_detail, name="discharge_detail"),
    path(
        "altas/<uuid:discharge_id>/cancelar/",
        views.discharge_cancel,
        name="discharge_cancel",
    ),
    path("pacientes/<uuid:patient_id>/", views.patient_detail, name="patient_detail"),
    path(
        "pacientes/<uuid:patient_id>/familia/novo/",
        views.family_create,
        name="family_create",
    ),
    path(
        "pacientes/<uuid:patient_id>/registros/novo/",
        views.log_create,
        name="log_create",
    ),
    path(
        "pacientes/<uuid:patient_id>/pedidos/novo/",
        views.request_create,
        name="request_create",
    ),
    path("familia/<uuid:family_id>/editar/", views.family_edit, name="family_edit"),
    path(
        "familia/<uuid:family_id>/autorizacao/",
        views.family_consent,
        name="family_consent",
    ),
    path(
        "familia/<uuid:family_id>/inativar/",
        views.family_deactivate,
        name="family_deactivate",
    ),
    path("registros/", views.log_list, name="log_list"),
    path("registros/<uuid:log_id>/corrigir/", views.log_correct, name="log_correct"),
    path("pedidos/", views.request_list, name="request_list"),
    path(
        "pedidos/<uuid:request_pk>/encaminhar/",
        views.request_forward,
        name="request_forward",
    ),
    path(
        "pedidos/<uuid:request_pk>/concluir/",
        views.request_resolve,
        name="request_resolve",
    ),
    path(
        "pedidos/<uuid:request_pk>/cancelar/",
        views.request_cancel,
        name="request_cancel",
    ),
    path("regua/", views.rule_list, name="rule_list"),
    path("regua/editar/", views.rule_edit, name="rule_edit"),
]
