"""Psychiatric clinical models for Aurora Elo Health Systems.

Implements DSM-5 and CID-11 diagnostic taxonomies, Mental Status Examination (MSE),
crisis stratification (Columbia C-SSRS), controlled psychopharmacology,
inpatient bed tracking, telepsychiatry, and mobile B2C mood/CBT logs.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DiagnosticCategory(models.Model):
    """CID-11 and DSM-5 Psychiatric Diagnosis Catalog."""

    cid11_code = models.CharField(
        max_length=20, unique=True, verbose_name="Código CID-11"
    )
    dsm5_code = models.CharField(max_length=20, blank=True, verbose_name="Código DSM-5")
    name = models.CharField(max_length=255, verbose_name="Nome do Transtorno")
    category = models.CharField(max_length=120, verbose_name="Categoria Diagnóstica")
    specifiers = models.TextField(blank=True, verbose_name="Especificadores Clínicos")

    class Meta:
        verbose_name = "Classificação Diagnóstica"
        verbose_name_plural = "Classificações Diagnósticas"
        ordering = ["cid11_code"]

    def __str__(self):
        return f"{self.cid11_code} - {self.name}"


class PsychiatricPatientProfile(models.Model):
    """Extended psychiatric profile for clinical tracking."""

    clinic = models.ForeignKey(
        "clinics.Clinic",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="psychiatric_profiles",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="psychiatric_profiles",
    )

    class RiskLevel(models.TextChoices):
        LOW = "LOW", "Baixo Risco (Ambulatorial Rotineiro)"
        MODERATE = "MODERATE", "Moderado (Acompanhamento Intensivo)"
        HIGH = "HIGH", "Alto Risco / Crise (Alerta SOS)"
        IMMINENT = "IMMINENT", "Risco Iminente de Autoextermínio"

    class TreatmentStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Em Acompanhamento"
        INPATIENT = "INPATIENT", "Internação Ativa"
        DISCHARGED = "DISCHARGED", "Alta Terapêutica"
        TRIAGE = "TRIAGE", "Triagem Inicial"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    full_name = models.CharField(max_length=255, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    date_of_birth = models.DateField(verbose_name="Data de Nascimento")
    phone = models.CharField(max_length=20, verbose_name="Telefone / WhatsApp")
    email = models.EmailField(blank=True, verbose_name="E-mail")
    record_number = models.CharField(
        max_length=30, unique=True, verbose_name="Número do Prontuário"
    )
    cns = models.CharField(
        max_length=20, blank=True, verbose_name="Cartão Nacional de Saúde (CNS)"
    )
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="CEP")

    primary_diagnosis = models.ForeignKey(
        DiagnosticCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients",
        verbose_name="Diagnóstico Principal CID-11",
    )
    status = models.CharField(
        max_length=20,
        choices=TreatmentStatus.choices,
        default=TreatmentStatus.ACTIVE,
        verbose_name="Situação Clínica",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
        verbose_name="Estratificação de Risco",
    )

    legal_guardian_name = models.CharField(
        max_length=255, blank=True, verbose_name="Responsável Legal"
    )
    legal_guardian_phone = models.CharField(
        max_length=20, blank=True, verbose_name="Telefone do Responsável"
    )
    known_allergies = models.TextField(
        blank=True,
        default="Nenhuma alergia conhecida",
        verbose_name="Alergias & Reações Adversas",
    )
    medical_comorbidities = models.TextField(
        blank=True, verbose_name="Comorbidades Clínicas"
    )
    tcle_signed = models.BooleanField(
        default=False, verbose_name="Termo de Consentimento Assinado"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil Psiquiátrico do Paciente"
        verbose_name_plural = "Perfis Psiquiátricos dos Pacientes"

    def __str__(self):
        return f"{self.full_name} ({self.record_number})"


class PsychiatricEvaluation(models.Model):
    """Complete Psychiatric Anamnesis and Mental Status Examination (MSE)."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="psychiatric_evaluations",
    )

    class Modality(models.TextChoices):
        IN_PERSON = "IN_PERSON", "Presencial na Clínica"
        TELEHEALTH = "TELEHEALTH", "Telepsiquiatria HD"
        HOME_CARE = "HOME_CARE", "Acompanhamento Domiciliar"

    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="Paciente",
    )
    doctor_name = models.CharField(
        max_length=255, default="Dr. Marcelo Arantes", verbose_name="Médico Psiquiatra"
    )
    doctor_crm = models.CharField(
        max_length=30, default="CRM/SP 148.920", verbose_name="CRM do Médico"
    )
    evaluation_date = models.DateTimeField(
        default=timezone.now, verbose_name="Data/Hora da Avaliação"
    )
    modality = models.CharField(
        max_length=20, choices=Modality.choices, default=Modality.IN_PERSON
    )

    chief_complaint = models.TextField(verbose_name="Queixa Principal")
    hda = models.TextField(verbose_name="História da Doença Atual (HDA)")
    past_psychiatric_history = models.TextField(
        blank=True, verbose_name="Antecedentes Psiquiátricos"
    )
    family_psychiatric_history = models.TextField(
        blank=True, verbose_name="Histórico Familiar"
    )
    substance_use_history = models.TextField(
        blank=True, verbose_name="Uso de Substâncias Psicoativas"
    )

    # Mental Status Examination (MSE / Exame do Estado Mental)
    mse_appearance_attitude = models.CharField(
        max_length=255,
        default="Adequada para idade e contexto, colaborativo",
        verbose_name="Aparência e Atitude",
    )
    mse_psychomotor = models.CharField(
        max_length=255,
        default="Normocinético, sem agitação ou acinesia",
        verbose_name="Psicomotricidade",
    )
    mse_mood_affect = models.CharField(
        max_length=255,
        default="Humor eutímico, afeto congruente e modulado",
        verbose_name="Humor e Afeto",
    )
    mse_speech = models.CharField(
        max_length=255,
        default="Fluxo normal, volume e velocidade adequados",
        verbose_name="Linguagem",
    )
    mse_thought_process = models.CharField(
        max_length=255,
        default="Lógico, coerente e orientado a metas",
        verbose_name="Processo do Pensamento",
    )
    mse_thought_content = models.TextField(
        default="Sem ideação delirante, delírios ou conteúdo paranoide",
        verbose_name="Conteúdo do Pensamento",
    )
    mse_perception = models.CharField(
        max_length=255,
        default="Sem alucinações auditivas ou visuais no momento",
        verbose_name="Sensopercepção",
    )
    mse_cognition = models.CharField(
        max_length=255,
        default="Orientado auto e alopsiquicamente, memória preservada",
        verbose_name="Cognição e Orientação",
    )
    mse_insight = models.CharField(
        max_length=255,
        default="Crítica e insight preservados sobre o quadro",
        verbose_name="Crítica e Insight",
    )

    # Risk Assessment (Columbia C-SSRS)
    suicidal_ideation_present = models.BooleanField(
        default=False, verbose_name="Presença de Ideação Suicida"
    )
    suicide_risk_stratification = models.CharField(
        max_length=20,
        choices=PsychiatricPatientProfile.RiskLevel.choices,
        default=PsychiatricPatientProfile.RiskLevel.LOW,
        verbose_name="Risco C-SSRS",
    )
    protective_factors = models.TextField(
        blank=True,
        default="Vínculo familiar positivo, adesão ao plano",
        verbose_name="Fatores de Proteção",
    )
    safety_plan = models.TextField(
        blank=True, verbose_name="Plano de Segurança para Crises"
    )

    anxiety_analog_scale = models.PositiveSmallIntegerField(
        default=3, verbose_name="Escala de Ansiedade (0-10)"
    )
    diagnostic_impression = models.TextField(verbose_name="Impressão Diagnóstica")
    therapeutic_plan = models.TextField(verbose_name="Conduta & Plano Terapêutico")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avaliação / Anamnese Psiquiátrica"
        verbose_name_plural = "Avaliações Psiquiátricas"
        ordering = ["-evaluation_date"]

    def __str__(self):
        return (
            f"Anamnese - {self.patient.full_name}"
            f" ({self.evaluation_date.strftime('%d/%m/%Y')})"
        )


class PsychopharmacologyPrescription(models.Model):
    """Controlled psychiatric digital prescription with safety checks."""

    class RecipeType(models.TextChoices):
        SIMPLES = "SIMPLES", "Receita Simples"
        CONTROLE_ESPECIAL_C1 = (
            "CONTROLE_ESPECIAL_C1",
            "Controle Especial C1 (Branca em 2 vias)",
        )
        NOTIFICACAO_B1 = (
            "NOTIFICACAO_B1",
            "Notificação de Receita B1 (Azul - Psicotrópicos)",
        )
        NOTIFICACAO_A = (
            "NOTIFICACAO_A",
            "Notificação de Receita A (Amarela - Entorpecentes)",
        )

    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="prescriptions",
    )
    doctor_name = models.CharField(max_length=255, default="Dr. Marcelo Arantes")
    doctor_crm = models.CharField(max_length=30, default="CRM/SP 148.920")
    recipe_type = models.CharField(
        max_length=30,
        choices=RecipeType.choices,
        default=RecipeType.CONTROLE_ESPECIAL_C1,
    )
    issued_date = models.DateField(default=timezone.now)
    expires_date = models.DateField()
    digital_signature_hash = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Prescrição Farmacológica"
        verbose_name_plural = "Prescrições Farmacológicas"
        ordering = ["-issued_date"]

    def __str__(self):
        return f"Prescrição {self.recipe_type} - {self.patient.full_name}"


class PrescriptionItem(models.Model):
    """Specific medication item within a psychiatric prescription."""

    prescription = models.ForeignKey(
        PsychopharmacologyPrescription, on_delete=models.CASCADE, related_name="items"
    )
    drug_name = models.CharField(
        max_length=150, verbose_name="Nome do Fármaco (Princípio Ativo)"
    )
    drug_class = models.CharField(max_length=100, verbose_name="Classe Terapêutica")
    dosage = models.CharField(max_length=50, verbose_name="Dosagem (ex: 15mg)")
    posology = models.CharField(
        max_length=255, verbose_name="Posologia / Horário de Tomada"
    )
    instructions = models.TextField(blank=True, verbose_name="Instruções e Alertas")

    def __str__(self):
        return f"{self.drug_name} {self.dosage} - {self.posology}"


class MedicationAdherenceLog(models.Model):
    """Real-time medication adherence log from the connected mobile app."""

    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="adherence_logs",
    )
    item = models.ForeignKey(PrescriptionItem, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    taken_at = models.DateTimeField(null=True, blank=True)
    is_taken = models.BooleanField(default=False)
    patient_notes = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Registro de Adesão Medicamentosa"
        verbose_name_plural = "Registros de Adesão Medicamentosa"
        ordering = ["-scheduled_time"]


class InpatientBed(models.Model):
    """Hospitalization bed management in psychiatric ward."""

    clinic = models.ForeignKey(
        "clinics.Clinic",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="psychiatric_beds",
    )

    class BedStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponível"
        OCCUPIED = "OCCUPIED", "Ocupado"
        MAINTENANCE = "MAINTENANCE", "Higienização / Manutenção"
        RESERVED = "RESERVED", "Reservado para Crise"

    class AdmissionType(models.TextChoices):
        VOLUNTARY = "VOLUNTARY", "Internação Voluntária"
        INVOLUNTARY = "INVOLUNTARY", "Internação Involuntária (Lei 10.216/2001)"
        COMPULSORY = "COMPULSORY", "Internação Compulsória Judicial"

    bed_code = models.CharField(
        max_length=20, unique=True, verbose_name="Código do Leito"
    )
    ward = models.CharField(max_length=100, verbose_name="Ala / Enfermaria")
    status = models.CharField(
        max_length=20, choices=BedStatus.choices, default=BedStatus.AVAILABLE
    )

    current_patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inpatient_bed",
    )
    admission_type = models.CharField(
        max_length=20, choices=AdmissionType.choices, blank=True
    )
    admission_date = models.DateTimeField(null=True, blank=True)
    nursing_notes = models.TextField(
        blank=True, verbose_name="Notas de Enfermagem Psiquiátrica"
    )

    class Meta:
        verbose_name = "Leito de Internação"
        verbose_name_plural = "Leitos de Internação"
        ordering = ["bed_code"]

    def __str__(self):
        return f"{self.bed_code} ({self.ward}) - {self.get_status_display()}"


class TelepsychiatryRoom(models.Model):
    """Encrypted telepsychiatry room session."""

    class SessionStatus(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Agendada"
        IN_PROGRESS = "IN_PROGRESS", "Em Andamento (HD E2EE)"
        COMPLETED = "COMPLETED", "Concluída"
        CANCELLED = "CANCELLED", "Cancelada"

    room_token = models.UUIDField(default=uuid.uuid4, unique=True)
    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="tele_sessions",
    )
    doctor_name = models.CharField(max_length=255, default="Dr. Marcelo Arantes")
    scheduled_for = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=SessionStatus.choices, default=SessionStatus.SCHEDULED
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    session_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sala de Telepsiquiatria"
        verbose_name_plural = "Salas de Telepsiquiatria"
        ordering = ["-scheduled_for"]

    def __str__(self):
        return (
            f"Teleconsulta {self.patient.full_name}"
            f" ({self.scheduled_for.strftime('%d/%m %H:%M')})"
        )


class PsychiatricCrisisAlert(models.Model):
    """Emergency 24h psychiatric SOS crisis alert."""

    class AlertStatus(models.TextChoices):
        OPEN = "OPEN", "Em Atendimento / Ativo"
        TRIAGED = "TRIAGED", "Triado pela Equipe Médica"
        DISPATCHED = "DISPATCHED", "Equipe de Apoio Deslocada"
        RESOLVED = "RESOLVED", "Estabilizado / Encerrado"

    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="crisis_alerts",
    )
    created_at = models.DateTimeField(default=timezone.now)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN
    )
    responder_notes = models.TextField(
        blank=True, verbose_name="Conduta de Intervenção Imediata"
    )

    class Meta:
        verbose_name = "Alerta de Crise SOS 24h"
        verbose_name_plural = "Alertas de Crise SOS 24h"
        ordering = ["-created_at"]


# ==============================================================================
# B2C RETAIL APP STORE MODULE (Mobile App 2: Aurora Mind & Wellness)
# ==============================================================================


class B2CMindLog(models.Model):
    """Daily mood and wellness check-in for the commercial retail mobile app."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="b2cmindlog_records",
    )

    class MoodState(models.TextChoices):
        RADIANT = "RADIANT", "Radiante ✨"
        CALM = "CALM", "Calmo 🌿"
        EUTHYMIC = "EUTHYMIC", "Estável ⚖️"
        ANXIOUS = "ANXIOUS", "Ansioso ⚡"
        LOW = "LOW", "Para Baixo 🌧️"

    user_identifier = models.CharField(max_length=100, db_index=True)
    logged_at = models.DateTimeField(default=timezone.now)
    mood = models.CharField(
        max_length=20, choices=MoodState.choices, default=MoodState.CALM
    )
    anxiety_score = models.PositiveSmallIntegerField(default=3)  # 0 to 10
    energy_score = models.PositiveSmallIntegerField(default=4)  # 1 to 5
    sleep_hours = models.DecimalField(max_digits=3, decimal_places=1, default=7.5)
    emotions_tags = models.JSONField(default=list)
    gratitude_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Registro de Humor B2C"
        verbose_name_plural = "Registros de Humor B2C"
        ordering = ["-logged_at"]


class B2CCBTDiary(models.Model):
    """Cognitive Behavioral Therapy (CBT) Thought Record."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="b2ccbtdiary_records",
    )
    user_identifier = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    trigger_situation = models.TextField(verbose_name="Situação Desencadeadora")
    automatic_thought = models.TextField(verbose_name="Pensamento Automático")
    cognitive_distortion = models.CharField(
        max_length=150, verbose_name="Distorção Cognitiva Identificada"
    )
    rational_response = models.TextField(verbose_name="Resposta Racional e Adaptativa")
    emotion_before_percent = models.PositiveSmallIntegerField(default=80)
    emotion_after_percent = models.PositiveSmallIntegerField(default=30)

    class Meta:
        verbose_name = "Diário de Pensamentos TCC"
        verbose_name_plural = "Diários de Pensamentos TCC"
        ordering = ["-created_at"]


class B2CSubscription(models.Model):
    """Commercial in-app purchase & subscription management."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="b2csubscription_records",
    )

    class PlanTier(models.TextChoices):
        FREE = "FREE", "Gratuito"
        PLUS_MONTHLY = "PLUS_MONTHLY", "Aurora Mind Plus (Mensal - R$ 29,90)"
        PLUS_ANNUAL = "PLUS_ANNUAL", "Aurora Mind Plus (Anual - R$ 249,90)"

    class StorePlatform(models.TextChoices):
        APPLE = "APPLE", "Apple App Store"
        GOOGLE = "GOOGLE", "Google Play Store"
        DIRECT = "DIRECT", "Assinatura Direta Aurora Elo"

    user_identifier = models.CharField(max_length=100, unique=True)
    plan = models.CharField(
        max_length=30, choices=PlanTier.choices, default=PlanTier.FREE
    )
    platform = models.CharField(
        max_length=20, choices=StorePlatform.choices, default=StorePlatform.APPLE
    )
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField()

    class Meta:
        verbose_name = "Assinatura B2C Aurora Mind"
        verbose_name_plural = "Assinaturas B2C Aurora Mind"


# ==============================================================================
# 4. ADDICTOLOGY & 12 STEPS RECOVERY MODULE (Apostas, Álcool e Drogas)
# ==============================================================================


class AddictionProfile(models.Model):
    """Specialized psychiatric addiction profile for Gambling, Alcohol,

    and Chemical Dependency."""

    class AddictionCategory(models.TextChoices):
        GAMBLING = "GAMBLING", "Transtorno do Jogo / Ludopatia (Bets & Cassinos)"
        ALCOHOL = "ALCOHOL", "Dependência Alcoólica (Alcoolismo)"
        CHEMICAL = (
            "CHEMICAL",
            "Dependência Química (Cocaína, Crack, Opioides, Estimulantes)",
        )
        POLYADDICTION = "POLYADDICTION", "Polidependência / Adicção Cruzada"

    class SeverityLevel(models.TextChoices):
        MILD = "MILD", "Leve (Ambulatorial Inicial)"
        MODERATE = "MODERATE", "Moderada (Acompanhamento Intensivo)"
        SEVERE = "SEVERE", "Grave (Indicação de Internação / Desintoxicação)"
        CRITICAL = "CRITICAL", "Crítica (Risco Iminente / Fissura Incontrolável)"

    patient = models.OneToOneField(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="addiction_profile",
        verbose_name="Paciente",
    )
    category = models.CharField(
        max_length=30,
        choices=AddictionCategory.choices,
        default=AddictionCategory.GAMBLING,
        verbose_name="Categoria Aditiva Principal",
    )
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        default=SeverityLevel.MODERATE,
        verbose_name="Gravidade Clínica",
    )

    # Jogos de Azar / Ludopatia (CID-11 6C50)
    gambling_modalities = models.JSONField(
        default=list,
        blank=True,
        verbose_name=(
            "Modalidades de Aposta (Bets Esportivas, Slots, Tigrinho, Pôquer, Roleta)"
        ),
    )
    estimated_financial_debt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Dívida Financeira Acumulada em R$",
    )
    chasing_losses = models.BooleanField(
        default=True,
        verbose_name="Comportamento de Correr Atrás do Prejuízo (Chasing)",
    )
    pgsi_score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Escore PGSI (Problem Gambling Severity Index: 0-27)",
    )

    # Álcool e Substâncias Psicoativas (CID-11 6C40, 6C45, etc.)
    primary_substance = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Substância Psicoativa Principal",
    )
    secondary_substances = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Substâncias Secundárias",
    )
    audit_score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Escore AUDIT (Álcool: 0-40)",
    )
    dast_score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Escore DAST-10 (Drogas: 0-10)",
    )
    ciwa_score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Escore CIWA-Ar (Abstinência Alcoólica: 0-67)",
    )

    # Sobriedade & 12 Passos
    sobriety_since = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Início da Sobriedade Atual (Clean Time)",
    )
    longest_sobriety_days = models.PositiveIntegerField(
        default=0,
        verbose_name="Recorde de Dias Limpos",
    )
    relapse_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Número de Recaídas Pregressas",
    )
    sponsor_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Nome do Padrinho/Madrinha dos 12 Passos",
    )
    sponsor_phone = models.CharField(
        max_length=25,
        blank=True,
        verbose_name="Telefone de Apoio do Padrinho",
    )
    fellowship_group = models.CharField(
        max_length=120,
        blank=True,
        default="A.A. / N.A. / J.A.",
        verbose_name="Irmandade de Mútuo Apoio Frequentada",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Adictologia (Apostas, Álcool e Drogas)"
        verbose_name_plural = "Perfis de Adictologia"

    def clean_days_count(self) -> int:
        """Calculate continuous clean/sober days."""
        if not self.sobriety_since:
            return 0
        delta = timezone.now().date() - self.sobriety_since
        return max(0, delta.days)

    def __str__(self):
        return (
            f"{self.patient.full_name}"
            f" - {self.get_category_display()} ({self.clean_days_count()} dias limpos)"
        )


class TwelveStepsAnamnesis(models.Model):
    """Clinical 12-Step Psychiatric Anamnesis backed by Redis state engine."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="psychiatric_step_records",
    )
    draft_steps = models.JSONField(default=dict, blank=True)

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Rascunho no Redis (Em Preenchimento)"
        IN_PROGRESS = "IN_PROGRESS", "Em Análise pela Equipe Multidisciplinar"
        CONSOLIDATED = "CONSOLIDATED", "Consolidada com Plano de Prevenção de Recaída"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="twelve_steps_records",
        verbose_name="Paciente",
    )
    session_date = models.DateTimeField(default=timezone.now)
    completed_steps_count = models.PositiveSmallIntegerField(
        default=1, verbose_name="Passos Concluídos (1-12)"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Os 12 Passos Clínicos Adaptados
    step1_powerlessness = models.TextField(
        blank=True,
        verbose_name=(
            "Passo 1: Reconhecimento da impotência e ingovernabilidade da vida"
        ),
    )
    step2_restoration_hope = models.TextField(
        blank=True,
        verbose_name="Passo 2: Crença na restauração da sanidade e equilíbrio",
    )
    step3_surrender_care = models.TextField(
        blank=True,
        verbose_name="Passo 3: Decisão de entregar o controle ao cuidado terapêutico",
    )
    step4_moral_inventory = models.TextField(
        blank=True,
        verbose_name="Passo 4: Inventário moral, financeiro, culpas e segredos",
    )
    step5_confession_admission = models.TextField(
        blank=True,
        verbose_name="Passo 5: Admissão da natureza exata dos erros e padrões aditivos",
    )
    step6_readiness = models.TextField(
        blank=True,
        verbose_name=(
            "Passo 6: Prontidão para transformar defeitos de caráter e impulsividade"
        ),
    )
    step7_humility = models.TextField(
        blank=True,
        verbose_name="Passo 7: Superação humilde das próprias fraquezas e limitações",
    )
    step8_amends_list = models.TextField(
        blank=True,
        verbose_name="Passo 8: Lista de familiares, credores e pessoas prejudicadas",
    )
    step9_reparations_plan = models.TextField(
        blank=True,
        verbose_name="Passo 9: Plano de reparação direta, solvência e reconciliação",
    )
    step10_daily_inventory = models.TextField(
        blank=True,
        verbose_name="Passo 10: Vigilância diária e admissão imediata de deslizes",
    )
    step11_mindfulness_prayer = models.TextField(
        blank=True,
        verbose_name="Passo 11: Práticas meditativas, conexão interior e serenidade",
    )
    step12_service_purpose = models.TextField(
        blank=True,
        verbose_name=(
            "Passo 12: Despertar terapêutico e transmissão da mensagem de sobriedade"
        ),
    )

    # Análise de Risco & IA Relapse Prevention
    relapse_triggers = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Gatilhos Críticos de Recaída Identificados (HALT)",
    )
    relapse_risk_index = models.PositiveSmallIntegerField(
        default=None,
        null=True,
        blank=True,
        verbose_name="Índice de Risco de Recaída (0-100)",
    )
    ai_prevention_plan = models.TextField(
        blank=True,
        verbose_name="Plano Individual de Prevenção de Recaída (Gerado por IA)",
    )
    doctor_conclusions = models.TextField(
        blank=True,
        verbose_name="Parecer do Médico Psiquiatra Especialista",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Anamnese Psiquiátrica dos 12 Passos"
        verbose_name_plural = "Anamneses dos 12 Passos"
        ordering = ["-session_date"]

    def __str__(self):
        return (
            f"12 Passos - {self.patient.full_name}"
            f" ({self.session_date.strftime('%d/%m/%Y')})"
        )


class CravingTrackingLog(models.Model):
    """Real-time craving and urge tracking for gambling, alcohol, or

    substance cravings."""

    patient = models.ForeignKey(
        PsychiatricPatientProfile,
        on_delete=models.CASCADE,
        related_name="craving_logs",
        verbose_name="Paciente",
    )
    timestamp = models.DateTimeField(default=timezone.now)
    craving_intensity = models.PositiveSmallIntegerField(
        default=5,
        verbose_name="Intensidade da Fissura (0 a 10)",
    )
    target_urge = models.CharField(
        max_length=80,
        verbose_name="Objeto da Fissura (ex: Bet/Cassino, Cerveja, Cocaína)",
    )
    trigger_detail = models.TextField(
        blank=True,
        verbose_name="Gatilho Desencadeante",
    )
    halt_factors = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Fatores HALT Ativos (Hungry, Angry, Lonely, Tired)",
    )
    coping_technique = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Técnica de Enfrentamento Utilizada",
    )
    urge_surfed_successfully = models.BooleanField(
        default=True,
        verbose_name="Fissura Superada sem Recaída (Urge Surfing)",
    )

    class Meta:
        verbose_name = "Registro de Fissura / Craving"
        verbose_name_plural = "Registros de Fissura / Craving"
        ordering = ["-timestamp"]
