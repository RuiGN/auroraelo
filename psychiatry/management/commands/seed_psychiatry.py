"""Seed script for Aurora Elo Health Systems.

Populates CID-11 / DSM-5 psychiatric diagnoses, initial patient profiles,
inpatient beds, clinical evaluations, controlled prescriptions, and B2C data.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
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
    AddictionProfile,
    TwelveStepsAnamnesis,
    CravingTrackingLog,
)


class Command(BaseCommand):
    help = "Seed initial psychiatric diagnoses, beds, patients and clinical records."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Iniciando seed do ecossistema Aurora Elo Psiquiatria..."))

        # 1. Classificações Diagnósticas (CID-11 & DSM-5)
        diagnoses_data = [
            {
                "cid11": "6A70",
                "dsm5": "296.22",
                "name": "Transtorno Depressivo Maior, Episódio Único",
                "category": "Transtornos do Humor",
                "specifiers": "Moderado a grave, sem características psicóticas. Resposta parcial a ISRS.",
            },
            {
                "cid11": "6A71",
                "dsm5": "296.33",
                "name": "Transtorno Depressivo Recorrente",
                "category": "Transtornos do Humor",
                "specifiers": "Episódio atual grave com ideação suicida prévia em remissão.",
            },
            {
                "cid11": "6A60",
                "dsm5": "296.40",
                "name": "Transtorno Bipolar Tipo I",
                "category": "Transtornos Bipolares",
                "specifiers": "Episódio maníaco com sintomas mistos; estabilizado com carbonato de lítio.",
            },
            {
                "cid11": "6A61",
                "dsm5": "296.89",
                "name": "Transtorno Bipolar Tipo II",
                "category": "Transtornos Bipolares",
                "specifiers": "Episódios hipomaníacos alternados com episódios depressivos maiores.",
            },
            {
                "cid11": "6B00",
                "dsm5": "300.02",
                "name": "Transtorno de Ansiedade Generalizada (TAG)",
                "category": "Transtornos de Ansiedade",
                "specifiers": "Tensão muscular, hiperarousal autonômico, insônia intermediária.",
            },
            {
                "cid11": "6B01",
                "dsm5": "300.01",
                "name": "Transtorno de Pânico",
                "category": "Transtornos de Ansiedade",
                "specifiers": "Com agorafobia e esquiva fóbica de transportes públicos e aglomerações.",
            },
            {
                "cid11": "6B20",
                "dsm5": "300.3",
                "name": "Transtorno Obsessivo-Compulsivo (TOC)",
                "category": "Transtornos Obsessivo-Compulsivos",
                "specifiers": "Obsessões de contaminação e checagem ritualística com sofrimento acentuado.",
            },
            {
                "cid11": "6B40",
                "dsm5": "309.81",
                "name": "Transtorno de Estresse Pós-Traumático (TEPT)",
                "category": "Transtornos Relacionados ao Estresse",
                "specifiers": "Flashbacks intrusivos, hipervigilância, histórico de evento ameaçador à vida.",
            },
            {
                "cid11": "6A20",
                "dsm5": "295.90",
                "name": "Esquizofrenia Paranóide",
                "category": "Esquizofrenia e Outros Transtornos Psicóticos",
                "specifiers": "Sintomas positivos predominantes (delírios persecutórios e alucinações auditivas).",
            },
            {
                "cid11": "6A05",
                "dsm5": "314.01",
                "name": "Transtorno de Déficit de Atenção e Hiperatividade (TDAH)",
                "category": "Transtornos do Neurodesenvolvimento",
                "specifiers": "Apresentação combinada (desatenção e hiperatividade-impulsividade).",
            },
            {
                "cid11": "6B80",
                "dsm5": "307.1",
                "name": "Anorexia Nervosa",
                "category": "Transtornos Alimentares",
                "specifiers": "Tipo restritivo, distorção de imagem corporal, IMC limítrofe.",
            },
            {
                "cid11": "6C40",
                "dsm5": "303.90",
                "name": "Transtorno por Uso de Álcool",
                "category": "Transtornos por Uso de Substâncias",
                "specifiers": "Dependência grave com síndrome de abstinência moderada.",
            },
            {
                "cid11": "6C50",
                "dsm5": "312.31",
                "name": "Transtorno do Jogo / Ludopatia (Gambling Disorder)",
                "category": "Transtornos Devido a Comportamentos Aditivos",
                "specifiers": "Padrão persistente de apostas online (Bets e cassinos virtuais), perseguição de perdas e endividamento crítico.",
            },
            {
                "cid11": "6C45",
                "dsm5": "304.20",
                "name": "Transtorno por Uso de Cocaína e Estimulantes",
                "category": "Transtornos por Uso de Substâncias",
                "specifiers": "Dependência com fissura (craving) intensa associada ao consumo de álcool.",
            },
        ]

        diagnoses = {}
        for d in diagnoses_data:
            obj, created = DiagnosticCategory.objects.update_or_create(
                cid11_code=d["cid11"],
                defaults={
                    "dsm5_code": d["dsm5"],
                    "name": d["name"],
                    "category": d["category"],
                    "specifiers": d["specifiers"],
                }
            )
            diagnoses[d["cid11"]] = obj
        self.stdout.write(self.style.SUCCESS(f"✓ {len(diagnoses)} classificações diagnósticas sincronizadas."))

        # 2. Leitos de Internação Psiquiátrica
        wards_and_beds = [
            ("L-101", "Ala Aurora Norte (Agudos)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.VOLUNTARY),
            ("L-102", "Ala Aurora Norte (Agudos)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.VOLUNTARY),
            ("L-103", "Ala Aurora Norte (Agudos)", InpatientBed.BedStatus.AVAILABLE, ""),
            ("L-104", "Ala Aurora Norte (Agudos)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.INVOLUNTARY),
            ("L-201", "Ala Aurora Sul (Estabilização)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.VOLUNTARY),
            ("L-202", "Ala Aurora Sul (Estabilização)", InpatientBed.BedStatus.AVAILABLE, ""),
            ("L-203", "Ala Aurora Sul (Estabilização)", InpatientBed.BedStatus.AVAILABLE, ""),
            ("L-204", "Ala Aurora Sul (Estabilização)", InpatientBed.BedStatus.MAINTENANCE, ""),
            ("L-301", "Unidade Intensiva de Crise (UIC)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.INVOLUNTARY),
            ("L-302", "Unidade Intensiva de Crise (UIC)", InpatientBed.BedStatus.RESERVED, ""),
            ("L-303", "Unidade Intensiva de Crise (UIC)", InpatientBed.BedStatus.OCCUPIED, InpatientBed.AdmissionType.COMPULSORY),
            ("L-304", "Unidade Intensiva de Crise (UIC)", InpatientBed.BedStatus.AVAILABLE, ""),
        ]

        beds = {}
        for bed_code, ward, status, adm_type in wards_and_beds:
            b_obj, _ = InpatientBed.objects.update_or_create(
                bed_code=bed_code,
                defaults={
                    "ward": ward,
                    "status": status,
                    "admission_type": adm_type,
                    "admission_date": timezone.now() - timedelta(days=4) if status == InpatientBed.BedStatus.OCCUPIED else None,
                    "nursing_notes": "Sinais vitais estáveis. Avaliação de risco de fuga e autoagressão negativa nas últimas 24h." if status == InpatientBed.BedStatus.OCCUPIED else "Leito higienizado e pronto para admissão.",
                }
            )
            beds[bed_code] = b_obj
        self.stdout.write(self.style.SUCCESS(f"✓ {len(beds)} leitos hospitalares cadastrados."))

        # 3. Pacientes Psiquiátricos Exemplares
        patients_data = [
            {
                "full_name": "Mariana Silveira Fagundes",
                "cpf": "184.920.381-04",
                "dob": "1994-06-14",
                "phone": "(11) 98765-4321",
                "email": "mariana.fagundes@exemplo.com.br",
                "record": "PR-2026-0842",
                "cns": "892019283710002",
                "postal_code": "01310-100",
                "diagnosis": diagnoses.get("6A70"),
                "status": PsychiatricPatientProfile.TreatmentStatus.ACTIVE,
                "risk_level": PsychiatricPatientProfile.RiskLevel.LOW,
                "guardian": "Roberto Fagundes (Pai)",
                "guardian_phone": "(11) 98765-4320",
                "allergies": "Alérgica a Penicilina e Dipirona",
                "comorbidities": "Hipotireoidismo em uso de Levotiroxina 50mcg",
            },
            {
                "full_name": "Carlos Eduardo Brandão",
                "cpf": "291.839.402-19",
                "dob": "1988-11-23",
                "phone": "(11) 97654-3210",
                "email": "carlos.brandao@exemplo.com.br",
                "record": "PR-2026-0914",
                "cns": "892019283710003",
                "postal_code": "04538-133",
                "diagnosis": diagnoses.get("6A60"),
                "status": PsychiatricPatientProfile.TreatmentStatus.INPATIENT,
                "risk_level": PsychiatricPatientProfile.RiskLevel.HIGH,
                "guardian": "Fernanda Brandão (Esposa)",
                "guardian_phone": "(11) 97654-3211",
                "allergies": "Nenhuma alergia relatada",
                "comorbidities": "Hipertensão arterial estágio 1",
            },
            {
                "full_name": "Beatriz Alencar Mendes",
                "cpf": "402.193.847-55",
                "dob": "1999-03-08",
                "phone": "(11) 99123-8877",
                "email": "beatriz.mendes@exemplo.com.br",
                "record": "PR-2026-1022",
                "cns": "892019283710004",
                "postal_code": "05422-010",
                "diagnosis": diagnoses.get("6B00"),
                "status": PsychiatricPatientProfile.TreatmentStatus.ACTIVE,
                "risk_level": PsychiatricPatientProfile.RiskLevel.MODERATE,
                "guardian": "Helena Mendes (Mãe)",
                "guardian_phone": "(11) 99123-8876",
                "allergies": "Dermatite de contato a látex",
                "comorbidities": "Enxaqueca crônica",
            },
            {
                "full_name": "Lucas Henrique de Souza",
                "cpf": "319.482.019-33",
                "dob": "1991-09-17",
                "phone": "(11) 98844-5511",
                "email": "lucas.souza@exemplo.com.br",
                "record": "PR-2026-1108",
                "cns": "892019283710005",
                "postal_code": "01452-000",
                "diagnosis": diagnoses.get("6A20"),
                "status": PsychiatricPatientProfile.TreatmentStatus.INPATIENT,
                "risk_level": PsychiatricPatientProfile.RiskLevel.HIGH,
                "guardian": "Clara de Souza (Irmã)",
                "guardian_phone": "(11) 98844-5512",
                "allergies": "Reação extrapiramidal prévia a haloperidol em altas doses",
                "comorbidities": "Tabagismo",
            },
            {
                "full_name": "Juliana Prado Cavalcanti",
                "cpf": "520.194.839-88",
                "dob": "2001-12-05",
                "phone": "(11) 97112-3344",
                "email": "juliana.prado@exemplo.com.br",
                "record": "PR-2026-1250",
                "cns": "892019283710006",
                "postal_code": "04012-001",
                "diagnosis": diagnoses.get("6B01"),
                "status": PsychiatricPatientProfile.TreatmentStatus.ACTIVE,
                "risk_level": PsychiatricPatientProfile.RiskLevel.LOW,
                "guardian": "",
                "guardian_phone": "",
                "allergies": "Nenhuma conhecida",
                "comorbidities": "Gastrite nervosa",
            },
            {
                "full_name": "Thiago Ramos Mendonça",
                "cpf": "631.902.847-11",
                "dob": "1992-04-18",
                "phone": "(11) 98112-9900",
                "email": "thiago.mendonca@exemplo.com.br",
                "record": "PR-2026-1301",
                "cns": "892019283710007",
                "postal_code": "04561-000",
                "diagnosis": diagnoses.get("6C50"),
                "status": PsychiatricPatientProfile.TreatmentStatus.ACTIVE,
                "risk_level": PsychiatricPatientProfile.RiskLevel.MODERATE,
                "guardian": "Camila Mendonça (Esposa)",
                "guardian_phone": "(11) 98112-9901",
                "allergies": "Nenhuma",
                "comorbidities": "Insônia e ansiedade grave pós-perdas em apostas",
            },
            {
                "full_name": "Fernando Castilho Prado",
                "cpf": "742.019.384-22",
                "dob": "1985-08-30",
                "phone": "(11) 99445-6677",
                "email": "fernando.castilho@exemplo.com.br",
                "record": "PR-2026-1302",
                "cns": "892019283710008",
                "postal_code": "01311-200",
                "diagnosis": diagnoses.get("6C40"),
                "status": PsychiatricPatientProfile.TreatmentStatus.ACTIVE,
                "risk_level": PsychiatricPatientProfile.RiskLevel.HIGH,
                "guardian": "Marcos Castilho (Irmão)",
                "guardian_phone": "(11) 99445-6678",
                "allergies": "Sulfas",
                "comorbidities": "Esteatose hepática",
            },
        ]

        created_patients = []
        for p in patients_data:
            pat_obj, _ = PsychiatricPatientProfile.objects.update_or_create(
                cpf=p["cpf"],
                defaults={
                    "full_name": p["full_name"],
                    "date_of_birth": p["dob"],
                    "phone": p["phone"],
                    "email": p["email"],
                    "record_number": p["record"],
                    "cns": p["cns"],
                    "postal_code": p["postal_code"],
                    "primary_diagnosis": p["diagnosis"],
                    "status": p["status"],
                    "risk_level": p["risk_level"],
                    "legal_guardian_name": p["guardian"],
                    "legal_guardian_phone": p["guardian_phone"],
                    "known_allergies": p["allergies"],
                    "medical_comorbidities": p["comorbidities"],
                    "tcle_signed": True,
                }
            )
            created_patients.append(pat_obj)

        self.stdout.write(self.style.SUCCESS(f"✓ {len(created_patients)} pacientes psiquiátricos cadastrados."))

        # Associar pacientes internados aos leitos
        p_carlos = next(p for p in created_patients if "Carlos" in p.full_name)
        p_lucas = next(p for p in created_patients if "Lucas" in p.full_name)
        beds["L-101"].current_patient = p_carlos
        beds["L-101"].save()
        beds["L-301"].current_patient = p_lucas
        beds["L-301"].save()

        # 4. Avaliações Clínicas e Anamneses (MSE & C-SSRS)
        p_mariana = next(p for p in created_patients if "Mariana" in p.full_name)
        PsychiatricEvaluation.objects.get_or_create(
            patient=p_mariana,
            evaluation_date=timezone.now() - timedelta(days=7),
            defaults={
                "doctor_name": "Dr. Marcelo Arantes",
                "doctor_crm": "CRM/SP 148.920",
                "modality": PsychiatricEvaluation.Modality.TELEHEALTH,
                "chief_complaint": "Episódio de desânimo acentuado, anedonia e insônia terminal há 3 meses.",
                "hda": "Paciente relata início insidioso de humor deprimido após término de relacionamento e sobrecarga laboral. Refere choro fácil, fadiga crônica e perda de interesse por hobbies. Nega ideação suicida estruturada ou sintomas psicóticos.",
                "past_psychiatric_history": "Episódio depressivo prévio aos 22 anos tratado com Sertralina 50mg com remissão completa.",
                "family_psychiatric_history": "Mãe com histórico de depressão unipolar; tia materna com transtorno de ansiedade.",
                "substance_use_history": "Uso social esporádico de álcool (1 dose quinzenal). Nega tabagismo ou substâncias ilícitas.",
                "mse_appearance_attitude": "Vestes adequadas, asseada, postura curvada, contato visual mantido porém hesitante, plenamente colaborativa.",
                "mse_psychomotor": "Discreta lentificação psicomotora, sem tiques ou acatisia.",
                "mse_mood_affect": "Humor hipotímico auto-referido como 'vazio e exaustão'. Afeto restrito, congruente com o tema depressivo.",
                "mse_speech": "Voz baixa, latência de resposta discretamente aumentada, ritmo e articulação preservados.",
                "mse_thought_process": "Coerente, linear, sem fuga de ideias ou afrouxamento associativo.",
                "mse_thought_content": "Pensamentos de autocrítica exacerbada e preocupação com o futuro. Ausência de delírios ou ideação de ruína.",
                "mse_perception": "Sem alterações sensoperceptivas (ausência de alucinações ou ilusões).",
                "mse_cognition": "Lúcida, orientada no tempo e espaço. Atenção concentrada preservada ao exame sumário.",
                "mse_insight": "Insight grau 6 (plena consciência do adoecimento psíquico e motivação para o tratamento).",
                "suicidal_ideation_present": False,
                "suicide_risk_stratification": PsychiatricPatientProfile.RiskLevel.LOW,
                "protective_factors": "Rede de apoio familiar sólida (pais e irmã), estabilidade profissional, vínculo terapêutico estabelecido.",
                "safety_plan": "Orientada sobre canais de emergência da clínica Aurora Elo (botão SOS 24h no aplicativo móvel) e CVV 188.",
                "anxiety_analog_scale": 4,
                "diagnostic_impression": "Transtorno Depressivo Maior, Episódio Único, Moderado (CID-11 6A70 / DSM-5 296.22).",
                "therapeutic_plan": "1. Iniciar Escitalopram 10mg/dia pela manhã; 2. Titular para 15mg após 14 dias conforme tolerabilidade; 3. Encaminhamento para Psicoterapia TCC semanal; 4. Monitoramento diário via App Aurora Elo Conectado.",
            }
        )

        # 5. Prescrição Farmacológica e Itens
        presc, _ = PsychopharmacologyPrescription.objects.get_or_create(
            patient=p_mariana,
            is_active=True,
            defaults={
                "doctor_name": "Dr. Marcelo Arantes",
                "doctor_crm": "CRM/SP 148.920",
                "recipe_type": PsychopharmacologyPrescription.RecipeType.CONTROLE_ESPECIAL_C1,
                "issued_date": timezone.now().date(),
                "expires_date": (timezone.now() + timedelta(days=30)).date(),
                "digital_signature_hash": "SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            }
        )

        item1, _ = PrescriptionItem.objects.get_or_create(
            prescription=presc,
            drug_name="Oxalato de Escitalopram",
            defaults={
                "drug_class": "Antidepressivo / ISRS",
                "dosage": "15 mg",
                "posology": "Tomar 1 comprimido pela manhã após o desjejum",
                "instructions": "Não interromper abruptamente. Efeitos terapêuticos esperados entre 2 e 4 semanas de uso contínuo.",
            }
        )

        item2, _ = PrescriptionItem.objects.get_or_create(
            prescription=presc,
            drug_name="Melatonina de Liberação Prolongada",
            defaults={
                "drug_class": "Regulador Circadiano",
                "dosage": "3 mg",
                "posology": "Tomar 1 cápsula 45 minutos antes de deitar",
                "instructions": "Associar com higiene do sono (desligar telas luminosas e ambiente escuro).",
            }
        )

        # Adesão Medicamentosa
        MedicationAdherenceLog.objects.get_or_create(
            patient=p_mariana,
            item=item1,
            scheduled_time=timezone.now().replace(hour=8, minute=0, second=0),
            defaults={
                "taken_at": timezone.now().replace(hour=8, minute=12, second=0),
                "is_taken": True,
                "patient_notes": "Tomei no horário com o café da manhã.",
            }
        )

        # 6. Alerta de Crise SOS Ativo
        PsychiatricCrisisAlert.objects.get_or_create(
            patient=p_carlos,
            status=PsychiatricCrisisAlert.AlertStatus.OPEN,
            defaults={
                "latitude": -23.561684,
                "longitude": -46.655981,
                "responder_notes": "Paciente admitido na Ala Aurora Norte. Quadro de agitação psicomotora estabilizado com contenção verbal e farmacológica.",
            }
        )

        # 7. Sala Virtual de Telepsiquiatria
        TelepsychiatryRoom.objects.get_or_create(
            patient=p_mariana,
            doctor_name="Dr. Marcelo Arantes",
            defaults={
                "scheduled_for": timezone.now() + timedelta(hours=2),
                "status": TelepsychiatryRoom.SessionStatus.SCHEDULED,
                "session_notes": "Consulta de retorno programada para ajuste de dosagem e avaliação da adesão medicamentosa.",
            }
        )

        # 8. Dados B2C (App Retail Aurora Mind & Wellness)
        demo_user = "aurora_demo_user_retail_001"
        B2CSubscription.objects.get_or_create(
            user_identifier=demo_user,
            defaults={
                "plan": B2CSubscription.PlanTier.PLUS_ANNUAL,
                "platform": B2CSubscription.StorePlatform.APPLE,
                "is_active": True,
                "valid_until": timezone.now() + timedelta(days=330),
            }
        )

        B2CMindLog.objects.get_or_create(
            user_identifier=demo_user,
            logged_at=timezone.now() - timedelta(hours=3),
            defaults={
                "mood": B2CMindLog.MoodState.CALM,
                "anxiety_score": 2,
                "energy_score": 4,
                "sleep_hours": 8.0,
                "emotions_tags": ["Serenidade", "Foco", "Gratidão"],
                "gratitude_note": "A respiração guiada 4-4-4-4 antes de dormir ajudou muito a relaxar.",
            }
        )

        B2CCBTDiary.objects.get_or_create(
            user_identifier=demo_user,
            trigger_situation="Apresentação do projeto na reunião executiva da empresa.",
            defaults={
                "automatic_thought": "Vou esquecer os slides e todos vão achar que sou incapaz.",
                "cognitive_distortion": "Catastrofização e Leitura Mental",
                "rational_response": "Eu me preparei durante toda a semana, conheço os dados técnicos em detalhes e esquecer um detalhe é perfeitamente humano.",
                "emotion_before_percent": 85,
                "emotion_after_percent": 25,
            }
        )

        # 9. Adictologia, Jogos de Azar e 12 Passos
        p_thiago = next(p for p in created_patients if "Thiago" in p.full_name)
        p_fernando = next(p for p in created_patients if "Fernando" in p.full_name)

        # Perfil de Jogos de Azar / Ludopatia (Thiago)
        AddictionProfile.objects.update_or_create(
            patient=p_thiago,
            defaults={
                "category": AddictionProfile.AddictionCategory.GAMBLING,
                "severity": AddictionProfile.SeverityLevel.SEVERE,
                "gambling_modalities": ["Bets Esportivas", "Cassino Virtual (Tigrinho)", "Roleta"],
                "estimated_financial_debt": 145000.00,
                "chasing_losses": True,
                "pgsi_score": 21,
                "sobriety_since": (timezone.now() - timedelta(days=54)).date(),
                "longest_sobriety_days": 54,
                "relapse_count": 3,
                "sponsor_name": "Eduardo M. (Jogadores Anônimos - J.A.)",
                "sponsor_phone": "(11) 98777-1234",
                "fellowship_group": "Jogadores Anônimos (J.A.) Grupo Esperança",
            }
        )

        # Perfil de Polidependência Álcool + Cocaína (Fernando)
        AddictionProfile.objects.update_or_create(
            patient=p_fernando,
            defaults={
                "category": AddictionProfile.AddictionCategory.POLYADDICTION,
                "severity": AddictionProfile.SeverityLevel.SEVERE,
                "primary_substance": "Álcool e Cocaína",
                "secondary_substances": ["Nicotina"],
                "audit_score": 28,
                "dast_score": 8,
                "ciwa_score": 12,
                "sobriety_since": (timezone.now() - timedelta(days=92)).date(),
                "longest_sobriety_days": 92,
                "relapse_count": 4,
                "sponsor_name": "Carlos B. (Alcoólicos Anônimos - A.A.)",
                "sponsor_phone": "(11) 97666-5544",
                "fellowship_group": "A.A. / N.A. Grupo Alvorada",
            }
        )

        # Anamnese dos 12 Passos Consolidada com IA
        TwelveStepsAnamnesis.objects.get_or_create(
            patient=p_thiago,
            defaults={
                "completed_steps_count": 12,
                "status": TwelveStepsAnamnesis.Status.CONSOLIDATED,
                "step1_powerlessness": "Admito que perdi completamente o controle sobre as apostas online. Cheguei a pedir empréstimos bancários e comprometi o patrimônio familiar sem que minha esposa soubesse.",
                "step2_restoration_hope": "Acredito que o acompanhamento psiquiátrico na Aurora Elo e o grupo dos Jogadores Anônimos podem me restaurar a sanidade e a paz mental.",
                "step3_surrender_care": "Entreguei a custódia das contas bancárias à minha esposa e instalei software de bloqueio (Gamban) em todos os dispositivos móveis.",
                "step4_moral_inventory": "Levantei a dívida exata de R$ 145.000,00 dividida em 3 instituições e 2 cartões de crédito. Reconheço que menti repetidamente para encobrir as perdas.",
                "step5_confession_admission": "Confessei todos os valores e segredos diante do Dr. Marcelo Arantes e da minha esposa Camila sem reservas.",
                "step6_readiness": "Estou plenamente disposto a tratar a ansiedade subjacente e abandonar a ilusão do dinheiro fácil e das recompensas rápidas.",
                "step7_humility": "Peço humildemente a superação da impulsividade e aceito a medicação de estabilização dopaminérgica prescrita.",
                "step8_amends_list": "Lista de pessoas: Camila (esposa), meus pais, e 2 amigos próximos dos quais tomei dinheiro emprestado sob falsos pretextos.",
                "step9_reparations_plan": "Plano financeiro aprovado com a família para quitação em 36 parcelas com acompanhamento de consultoria financeira neutra.",
                "step10_daily_inventory": "Realizo reflexão diária todas as noites. Se surge o impulso de apostar, relato imediatamente ao padrinho Eduardo.",
                "step11_mindfulness_prayer": "Pratico 10 minutos de respiração 4-4-4-4 pela manhã para manter a mente no momento presente e sem ansiedade.",
                "step12_service_purpose": "Participo como orador nas reuniões do J.A. para acolher recém-chegados que perderam economias em Bets.",
                "relapse_triggers": ["Propaganda de Bets na TV e Internet", "Sexta-feira pós-expediente", "Frustração financeira", "Celular desprotegido"],
                "relapse_risk_index": 35,
                "ai_prevention_plan": "PLANO INDIVIDUALIZADO DE PREVENÇÃO DE RECAÍDA (AURORA ELO & MARLATT):\n1. Manter Gamban ativo em todos os dispositivos.\n2. Limite Pix diário travado em R$ 100.\n3. Presença semanal no grupo de Jogadores Anônimos.\n4. Se surgir fissura súbita: aplicar a regra dos 15 minutos e acionar o botão SOS no App Aurora Elo.",
                "doctor_conclusions": "Paciente em evolução favorável no 2º mês limpo. Excelente insight terapêutico e cumprimento rigoroso das reparações do Passo 9.",
            }
        )

        # Fissura Registrada no Histórico
        CravingTrackingLog.objects.get_or_create(
            patient=p_thiago,
            target_urge="Apostas Online / Bets",
            defaults={
                "craving_intensity": 7,
                "trigger_detail": "Notificação push durante partida da semifinal de futebol.",
                "halt_factors": ["Angry", "Tired"],
                "coping_technique": "Desligou o aparelho, realizou 5 min de respiração guiada 4-4-4-4 e ligou para o padrinho.",
                "urge_surfed_successfully": True,
            }
        )

        self.stdout.write(self.style.SUCCESS("✓ Seed psiquiátrico e adictologia concluído com sucesso total!"))

