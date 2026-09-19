"""Automated tests for Aurora Elo Psychiatric Platform & Mobile APIs."""

import json
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from psychiatry.models import (
    DiagnosticCategory,
    PsychiatricPatientProfile,
    PsychiatricEvaluation,
    PsychopharmacologyPrescription,
    PrescriptionItem,
    MedicationAdherenceLog,
    InpatientBed,
    TelepsychiatryRoom,
    PsychiatricCrisisAlert,
    B2CMindLog,
    B2CCBTDiary,
    B2CSubscription,
)


class PsychiatricSeedTest(TestCase):
    """Verifies that the seed management command populates all required clinical catalogs."""

    def test_seed_psychiatry_command(self):
        call_command("seed_psychiatry")
        self.assertGreaterEqual(DiagnosticCategory.objects.count(), 10)
        self.assertGreaterEqual(InpatientBed.objects.count(), 12)
        self.assertGreaterEqual(PsychiatricPatientProfile.objects.count(), 5)
        self.assertTrue(PsychiatricEvaluation.objects.exists())
        self.assertTrue(PsychopharmacologyPrescription.objects.exists())
        self.assertTrue(PrescriptionItem.objects.exists())
        self.assertTrue(B2CSubscription.objects.exists())
        self.assertTrue(B2CMindLog.objects.exists())
        self.assertTrue(B2CCBTDiary.objects.exists())


class PsychiatricWebViewsTest(TestCase):
    """Verifies that all psychiatric web views render with status 200."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_psychiatry")

    def setUp(self):
        self.client = Client()

    def test_dashboard_view(self):
        response = self.client.get("/psiquiatria/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Painel Clínico")
        self.assertContains(response, "Aurora Elo")

    def test_anamnesis_view(self):
        response = self.client.get("/psiquiatria/anamnese/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anamnese")
        self.assertContains(response, "Estado Mental")

    def test_patients_view(self):
        response = self.client.get("/psiquiatria/pacientes/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pacientes")

    def test_telepsychiatry_room_view(self):
        response = self.client.get("/psiquiatria/telepsiquiatria/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telepsiquiatria")

    def test_crisis_protocol_view(self):
        response = self.client.get("/psiquiatria/crise-sos/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Protocolo de Crise")

    def test_inpatient_beds_view(self):
        response = self.client.get("/psiquiatria/leitos/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leitos")

    def test_mobile_connected_view(self):
        response = self.client.get("/psiquiatria/mobile/conectado/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aurora Elo")

    def test_mobile_b2c_view(self):
        response = self.client.get("/psiquiatria/mobile/b2c/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aurora Mind")

    def test_login_view(self):
        response = self.client.get("/psiquiatria/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Portal Clínico")


class PsychiatricAPITest(TestCase):
    """Verifies REST endpoints for Web Portal and both Mobile Apps."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_psychiatry")

    def setUp(self):
        self.client = Client()

    def test_clinic_dashboard_kpis(self):
        response = self.client.get("/psiquiatria/api/v1/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("active_patients", data["data"])
        self.assertIn("bed_occupancy_percent", data["data"])

    def test_list_patients(self):
        response = self.client.get("/psiquiatria/api/v1/patients/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["patients"]), 0)

    def test_save_anamnesis_api(self):
        patient = PsychiatricPatientProfile.objects.first()
        payload = {
            "patient_cpf": patient.cpf,
            "patient_name": patient.full_name,
            "chief_complaint": "Insônia inicial e agitação noturna.",
            "hda": "Quadro com início há 2 semanas.",
            "mse_appearance": "Asseada, atenta",
            "mse_mood": "Ansioso",
            "anxiety_scale": 7,
            "diagnostic_code": "6B00",
            "therapeutic_plan": "Prescrição de ansiolítico e encaminhamento para psicoterapia",
            "suicidal_risk": "LOW",
        }
        response = self.client.post(
            "/psiquiatria/api/v1/anamnesis/save/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_mobile_connected_summary(self):
        patient = PsychiatricPatientProfile.objects.filter(record_number="PR-2026-0842").first()
        response = self.client.get(f"/psiquiatria/api/v1/mobile/connected/summary/?cpf={patient.cpf}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("patient", data["data"])
        self.assertIn("medications", data["data"])

    def test_mobile_connected_adherence(self):
        log = MedicationAdherenceLog.objects.first()
        payload = {
            "log_id": log.id,
            "is_taken": True,
            "notes": "Tomado pontualmente com água."
        }
        response = self.client.post(
            "/psiquiatria/api/v1/mobile/connected/adherence/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_mobile_connected_sos(self):
        patient = PsychiatricPatientProfile.objects.first()
        payload = {
            "patient_cpf": patient.cpf,
            "latitude": -23.55052,
            "longitude": -46.633308,
        }
        response = self.client.post(
            "/psiquiatria/api/v1/mobile/connected/sos/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("alert_id", data)

    def test_mobile_b2c_mood(self):
        # GET
        response = self.client.get("/psiquiatria/api/v1/mobile/b2c/mood/?user_id=test_b2c_user")
        self.assertEqual(response.status_code, 200)

        # POST
        payload = {
            "user_id": "test_b2c_user",
            "mood": "RADIANT",
            "anxiety": 1,
            "energy": 5,
            "sleep_hours": 8.5,
            "emotions": ["Alegria", "Entusiasmo"],
            "gratitude": "Dia muito produtivo.",
        }
        post_res = self.client.post(
            "/psiquiatria/api/v1/mobile/b2c/mood/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(post_res.status_code, 200)
        self.assertTrue(post_res.json()["success"])

    def test_mobile_b2c_cbt_diary(self):
        payload = {
            "user_id": "test_b2c_user",
            "situation": "Reunião de avaliação de desempenho.",
            "automatic_thought": "Vão apontar apenas meus erros.",
            "distortion": "Filtro Negativo",
            "rational_response": "Recebi elogios no último trimestre e estou preparado.",
            "emotion_before": 75,
            "emotion_after": 20,
        }
        response = self.client.post(
            "/psiquiatria/api/v1/mobile/b2c/cbt-diary/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_mobile_b2c_breathing(self):
        response = self.client.get("/psiquiatria/api/v1/mobile/b2c/breathing/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("protocols", data["data"])

    def test_mobile_b2c_subscription(self):
        # GET
        response = self.client.get("/psiquiatria/api/v1/mobile/b2c/subscription/?user_id=test_b2c_user")
        self.assertEqual(response.status_code, 200)

        # POST
        payload = {
            "user_id": "test_b2c_user",
            "plan": "PLUS_ANNUAL",
            "platform": "APPLE",
        }
        post_res = self.client.post(
            "/psiquiatria/api/v1/mobile/b2c/subscription/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(post_res.status_code, 200)
        self.assertTrue(post_res.json()["success"])
