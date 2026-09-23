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

    # Interactive Mobile Views
    path("mobile/conectado/", views.mobile_connected_view, name="mobile_connected"),
    path("mobile/b2c/", views.mobile_b2c_view, name="mobile_b2c"),

    # Addiction, Gambling & 12 Steps Module
    path("adictologia/", views.addiction_dashboard_view, name="addiction_dashboard"),
    path("adictologia/12-passos/", views.twelve_steps_anamnesis_view, name="twelve_steps_anamnesis"),

    # REST APIs for Web Portal & Mobile Apps (Canonical & Aliased)
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
    path("api/v1/adictologia/craving/", api.api_record_craving, name="api_record_craving"),
    path("api/v1/adictologia/dashboard/", api.api_addiction_dashboard_kpis, name="api_addiction_kpis"),

    # Connected Mobile App APIs
    path("api/v1/patient/summary/", api.patient_mobile_summary, name="api_patient_summary"),
    path("api/v1/patient/medications/log/", api.log_medication_adherence, name="api_medication_log"),
    path("api/v1/patient/sos/", api.trigger_patient_sos, name="api_patient_sos"),
    path("api/v1/mobile/connected/summary/", api.patient_mobile_summary),
    path("api/v1/mobile/connected/adherence/", api.log_medication_adherence),
    path("api/v1/mobile/connected/sos/", api.trigger_patient_sos),

    # Retail B2C Mobile App APIs (Aurora Mind)
    path("api/v1/mind/mood/", api.b2c_mood, name="api_b2c_mood"),
    path("api/v1/mind/cbt-diary/", api.b2c_cbt_diary, name="api_b2c_cbt_diary"),
    path("api/v1/mind/breathing/", api.b2c_breathing_exercises, name="api_b2c_breathing"),
    path("api/v1/mind/subscription/", api.b2c_subscription_status, name="api_b2c_subscription"),
    path("api/v1/mobile/b2c/mood/", api.b2c_mood),
    path("api/v1/mobile/b2c/cbt-diary/", api.b2c_cbt_diary),
    path("api/v1/mobile/b2c/breathing/", api.b2c_breathing_exercises),
    path("api/v1/mobile/b2c/subscription/", api.b2c_subscription_status),
]
