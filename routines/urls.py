"""Team routes for a patient's medication, care plan and habits."""

from django.urls import path

from . import views

app_name = "routines"

_PATIENT = "pacientes/<uuid:patient_id>/"

urlpatterns = [
    # Medicação
    path(f"{_PATIENT}medicacao/", views.medication_list, name="medication_list"),
    path(
        f"{_PATIENT}medicacao/nova/",
        views.medication_create,
        name="medication_create",
    ),
    path(
        f"{_PATIENT}medicacao/<uuid:medication_id>/editar/",
        views.medication_edit,
        name="medication_edit",
    ),
    path(
        f"{_PATIENT}medicacao/<uuid:medication_id>/suspender/",
        views.medication_stop,
        name="medication_stop",
    ),
    path(
        f"{_PATIENT}medicacao/<uuid:medication_id>/retomar/",
        views.medication_resume,
        name="medication_resume",
    ),
    # Plano de cuidado
    path(f"{_PATIENT}planos/", views.care_plan_list, name="care_plan_list"),
    path(f"{_PATIENT}planos/novo/", views.care_plan_create, name="care_plan_create"),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/",
        views.care_plan_detail,
        name="care_plan_detail",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/editar/",
        views.care_plan_edit,
        name="care_plan_edit",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/enviar-para-assinatura/",
        views.care_plan_submit,
        name="care_plan_submit",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/voltar-para-rascunho/",
        views.care_plan_reopen,
        name="care_plan_reopen",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/assinar/",
        views.care_plan_sign,
        name="care_plan_sign",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/pausar/",
        views.care_plan_pause,
        name="care_plan_pause",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/retomar/",
        views.care_plan_resume,
        name="care_plan_resume",
    ),
    path(
        f"{_PATIENT}planos/<uuid:care_plan_id>/encerrar/",
        views.care_plan_close,
        name="care_plan_close",
    ),
    # Hábitos
    path(f"{_PATIENT}habitos/", views.habit_list, name="habit_list"),
    path(f"{_PATIENT}habitos/novo/", views.habit_create, name="habit_create"),
    path(
        f"{_PATIENT}habitos/<uuid:habit_id>/editar/",
        views.habit_edit,
        name="habit_edit",
    ),
    path(
        f"{_PATIENT}habitos/<uuid:habit_id>/pausar/",
        views.habit_pause,
        name="habit_pause",
    ),
    path(
        f"{_PATIENT}habitos/<uuid:habit_id>/retomar/",
        views.habit_resume,
        name="habit_resume",
    ),
    path(
        f"{_PATIENT}habitos/<uuid:habit_id>/arquivar/",
        views.habit_archive,
        name="habit_archive",
    ),
]
