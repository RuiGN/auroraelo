from django.urls import path

from . import api, views

app_name = "psychiatry"

urlpatterns = [
    # Web Clinical Portal Routes
    path("", views.dashboard_view, name="dashboard"),
    path("anamnese/", views.anamnesis_view, name="anamnesis"),
    path("pacientes/", views.patients_view, name="patients"),
    path("telepsiquiatria/", views.telepsychiatry_room_view, name="telepsychiatry"),
    path("crise-sos/", views.crisis_protocol_view, name="crisis_protocol"),
    path("leitos/", views.inpatient_beds_view, name="inpatient_beds"),
    path("login/", views.login_view, name="login"),

    # Addiction, Gambling & 12 Steps Module
    path("adictologia/", views.addiction_dashboard_view, name="addiction_dashboard"),
    path("adictologia/12-passos/", views.twelve_steps_anamnesis_view, name="twelve_steps_anamnesis"),

    # REST APIs for the clinic web portal (canonical & aliased)
    path("api/v1/clinic/dashboard/", api.clinic_dashboard_kpis, name="api_clinic_dashboard"),
    path("api/v1/clinic/patients/", api.list_patients, name="api_list_patients"),
    path("api/v1/clinic/anamnese/", api.save_anamnesis, name="api_save_anamnesis"),
    path("api/v1/dashboard/", api.clinic_dashboard_kpis),
    path("api/v1/patients/", api.list_patients),
    path("api/v1/anamnesis/save/", api.save_anamnesis),

    # Addictology, Gambling & 12 Steps APIs
    path("api/v1/adictologia/12-passos/step/", api.api_save_12steps_step, name="api_save_12steps_step"),
    path("api/v1/adictologia/12-passos/draft/", api.api_get_12steps_draft, name="api_get_12steps_draft"),
    path("api/v1/adictologia/12-passos/consolidate/", api.api_consolidate_12steps, name="api_consolidate_12steps"),
    path("api/v1/adictologia/dashboard/", api.api_addiction_dashboard_kpis, name="api_addiction_kpis"),

]
