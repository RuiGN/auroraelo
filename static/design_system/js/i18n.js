/**
 * Aurora Elo Design System - Internationalization (i18n) Engine
 * Languages: pt-BR (Portuguese), en (English), es (Spanish)
 */

const AuroraI18n = {
  currentLang: 'pt-BR',

  translations: {
    'pt-BR': {
      // General & Brand
      clinic_name: 'Aurora Elo',
      clinic_subtitle: 'Saúde Mental & Psiquiatria Integrada',
      ecosystem_title: 'Sistema de Design Unificado',
      ecosystem_desc: 'Design System para ecossistema web clínico e dois aplicativos mobiles (clínico conectado e B2C nas app stores).',
      lang_name: 'Português (Brasil)',

      // Layout Switcher
      layout_vertical: 'Menu Vertical (Sidebar)',
      layout_horizontal: 'Menu Horizontal (Topbar)',
      theme_light: 'Claro',
      theme_dark: 'Escuro',

      // Navigation
      nav_dashboard: 'Painel Clínico',
      nav_patients: 'Pacientes',
      nav_appointments: 'Consultas & Agenda',
      nav_records: 'Prontuários & DSM-5',
      nav_inpatient: 'Leitos & Internação',
      nav_telepsychiatry: 'Telepsiquiatria',
      nav_pharmacy: 'Farmacologia & Prescrições',
      nav_crisis_protocol: 'Protocolo de Crise SOS',
      nav_analytics: 'Indicadores & Relatórios',
      nav_settings: 'Configurações',
      nav_quick_new_patient: '+ Novo Paciente',
      nav_quick_appointment: '+ Nova Consulta',
      nav_emergency_btn: 'SOS Crise 24h',
      nav_search_placeholder: 'Buscar paciente, CPF, prontuário ou CID-11... (Ctrl+K)',
      nav_doctor_role: 'Psiquiatra Responsável',
      nav_doctor_crm: 'CRM/SP 148.920',

      // Tabs in Showcase
      tab_overview: 'Visão Geral & Tokens',
      tab_navigation: 'Menus & Navegação',
      tab_login: 'Tela de Login',
      tab_lists: 'Listagens & Tabelas',
      tab_cards: 'Cards & Indicadores',
      tab_forms: 'Formulários & Máscaras',
      tab_mobiles: 'Aplicativos Mobiles',

      // Overview Section
      brand_colors_title: 'Paleta Cromática Oficial',
      brand_colors_desc: 'Extraída do logotipo Aurora Elo: o azul profundo da aurora representa acolhimento e estabilidade clínica; o ciano e cerúleo simbolizam o elo neural, claridade e recomeço.',
      tokens_typography: 'Tipografia & Escala',
      tokens_elevation: 'Sombras & Efeitos Aurora',

      // Login Screen
      login_title: 'Portal Clínico Aurora Elo',
      login_subtitle: 'Acesse o ambiente seguro de gestão psiquiátrica e cuidado integrado.',
      login_role_doctor: 'Corpo Clínico & Psiquiatria',
      login_role_patient: 'Paciente & Familiar',
      login_role_admin: 'Recepção & Gestão',
      login_email_label: 'E-mail ou Prontuário',
      login_email_placeholder: 'ex: dr.marcelo@auroraelo.med.br ou CPF',
      login_password_label: 'Senha de Acesso',
      login_password_placeholder: 'Digite sua senha com segurança',
      login_remember: 'Lembrar deste dispositivo por 30 dias',
      login_forgot: 'Esqueceu a senha?',
      login_submit: 'Acessar Sistema Seguro',
      login_2fa_alert: 'Autenticação de Dois Fatores (2FA) Ativa',
      login_crisis_banner: 'Em situação de crise aguda ou emergência emocional? Ligue 188 (CVV) ou contate nosso plantão 24h: 0800 770 ELO.',
      login_security_badge: 'Conformidade LGPD & Criptografia Ponta a Ponta',

      // Forms & Inputs
      form_title: 'Admissão & Anamnese Psiquiátrica',
      form_subtitle: 'Demonstração de todos os tipos de inputs com máscaras dinâmicas, validação e placeholders.',
      input_name_label: 'Nome Completo do Paciente',
      input_name_placeholder: 'Ex: Mariana Silveira Fagundes',
      input_cpf_label: 'CPF (com máscara)',
      input_cpf_placeholder: '000.000.000-00',
      input_phone_label: 'Telefone / WhatsApp (com máscara)',
      input_phone_placeholder: '(11) 98765-4321',
      input_dob_label: 'Data de Nascimento (com máscara)',
      input_dob_placeholder: 'DD/MM/AAAA',
      input_time_label: 'Horário da Sessão (com máscara)',
      input_time_placeholder: '14:30',
      input_currency_label: 'Valor da Consulta (com máscara)',
      input_currency_placeholder: 'R$ 450,00',
      input_cep_label: 'CEP / Código Postal (com máscara)',
      input_cep_placeholder: '01310-100',
      input_record_label: 'Código do Prontuário (com máscara)',
      input_record_placeholder: 'PRON-2026-0842',
      input_cns_label: 'Cartão Nacional de Saúde (CNS)',
      input_cns_placeholder: '741 2045 8921 0004',
      input_email_label: 'E-mail para Contato & Teleconsulta',
      input_email_placeholder: 'paciente@email.com',
      input_password_label: 'Senha Temporária / Chave de Acesso',
      input_password_placeholder: 'Mínimo de 8 dígitos, maiúsculas e símbolos',
      input_diagnosis_label: 'Diagnóstico Principal (CID-11 / DSM-5)',
      input_diagnosis_placeholder: 'Selecione a categoria diagnóstica...',
      input_notes_label: 'Queixa Principal & História da Doença Atual (HDA)',
      input_notes_placeholder: 'Descreva a evolução dos sintomas, ciclos de humor, histórico medicamentoso, sono e fatores de proteção...',
      input_slider_label: 'Escala Analógica de Ansiedade / Estresse (0 a 10)',
      input_risk_label: 'Estratificação de Risco Psiquiátrico',
      input_risk_low: 'Baixo Risco (Ambulatorial)',
      input_risk_mod: 'Moderado (Acompanhamento Intensivo)',
      input_risk_high: 'Alto Risco / Crise Imediata (Alerta SOS)',
      input_modality_label: 'Modalidade de Atendimento',
      input_modality_inperson: 'Presencial na Clínica',
      input_modality_telehealth: 'Telepsiquiatria HD',
      input_modality_home: 'Acompanhamento Domiciliar',
      input_tags_label: 'Tags de Alergias & Comorbidades',
      input_upload_label: 'Upload de Exames Laboratoriais, ECG & Receitas',
      input_upload_drop: 'Arraste arquivos aqui ou clique para selecionar',
      input_upload_hint: 'Suporte a PDF, DICOM, JPG e PNG até 25MB',
      input_consent_label: 'Paciente assinou Termo de Consentimento Livre e Esclarecido (TCLE) para Telemedicina e LGPD',
      input_btn_save: 'Salvar Anamnese & Gerar Prontuário',
      input_btn_cancel: 'Limpar Formulário',

      // Lists & Tables
      list_title: 'Gestão de Pacientes em Acompanhamento',
      list_search_placeholder: 'Filtrar por nome, prontuário, CPF ou diagnóstico...',
      list_filter_status_all: 'Todos os Status',
      list_filter_status_active: 'Em Acompanhamento',
      list_filter_status_inpatient: 'Internação',
      list_filter_status_discharged: 'Alta Clínica',
      list_filter_risk_all: 'Todos os Riscos',
      list_col_patient: 'Paciente / Contato',
      list_col_record: 'Prontuário',
      list_col_diag: 'CID-11 / DSM-5',
      list_col_risk: 'Nível de Risco',
      list_col_next: 'Próxima Consulta',
      list_col_status: 'Situação',
      list_col_actions: 'Ações',
      list_badge_low: 'Baixo Risco',
      list_badge_mod: 'Moderado',
      list_badge_high: 'Alto Risco / SOS',
      list_badge_inpatient: 'Leito 04-B',
      list_badge_active: 'Ativo',
      list_badge_discharged: 'Alta Terapêutica',
      list_action_view: 'Ver Prontuário',
      list_action_tele: 'Iniciar Teleconsulta',
      list_action_edit: 'Editar',
      list_pagination_info: 'Mostrando 1-4 de 128 pacientes cadastrados',
      list_pagination_prev: 'Anterior',
      list_pagination_next: 'Próximo',

      // Cards
      cards_title: 'Biblioteca de Cards Clínicos & Métricas',
      card_kpi_active_patients: 'Pacientes Ativos',
      card_kpi_today_sessions: 'Consultas Hoje',
      card_kpi_bed_occupancy: 'Ocupação de Leitos',
      card_kpi_adherence_rate: 'Adesão Medicamentosa',
      card_kpi_urgent_alerts: 'Alertas de Crise 24h',
      card_tele_title: 'Sala Virtual de Telepsiquiatria',
      card_tele_patient: 'Mariana Silveira Fagundes (34 anos)',
      card_tele_time: 'Iniciando em 12 minutos (14:30)',
      card_tele_btn: 'Entrar na Sala Virtual Criptografada',
      card_crisis_title: 'Protocolo de Emergência Psiquiátrica (SOS Elo)',
      card_crisis_desc: 'Guia de resposta rápida para contenção verbal, acolhimento, regulação de leitos e acionamento de rede de suporte.',
      card_crisis_call_btn: 'Ligar Plantão Psiquiátrico 24h',
      card_crisis_hotline_btn: 'Central CVV 188',
      card_mood_tracker_title: 'Avaliação de Humor & Bem-Estar (PHQ-9)',
      card_mood_score: 'Humor Eutímico e Estável',

      // Mobile Apps Showcase
      mobiles_section_title: 'Dois Aplicativos Mobile: Ecossistema Completo',
      mobiles_section_desc: 'O Design System alimenta perfeitamente o aplicativo clínico conectado ao prontuário web e o aplicativo B2C de autocuidado comercializado nas lojas de apps.',
      mobile_app1_title: 'App 1: Aurora Elo Clínica (Conectado ao Web)',
      mobile_app1_subtitle: 'Uso por Pacientes, Familiares e Equipe Médica',
      mobile_app1_badge: 'Conectado ao Web ERP / Prontuário',
      mobile_app2_title: 'App 2: Aurora Mind & Wellness (B2C Lojas de Apps)',
      mobile_app2_subtitle: 'Vendido no Google Play e Apple App Store',
      mobile_app2_badge: 'Monetização B2C & Assinatura Premium',

      // Mobile 1 UI Strings
      m1_welcome: 'Olá, Mariana',
      m1_status: 'Seu plano terapêutico está em dia',
      m1_quick_tele: 'Teleconsulta Hoje, 14:30',
      m1_doctor: 'Dr. Marcelo Arantes • Psiquiatra',
      m1_join_call: 'Acessar Teleconsulta',
      m1_meds_title: 'Medicamentos de Hoje',
      m1_med_1: 'Escitalopram 15mg • 08:00 (Tomado ✓)',
      m1_med_2: 'Quetiapina 25mg • 21:00 (Pendente)',
      m1_sos_btn: 'Botão de Ajuda Imediata / SOS',
      m1_chat_doc: 'Mensagem com Equipe Clínica',

      // Mobile 2 UI Strings
      m2_brand: 'Aurora Mind',
      m2_greeting: 'Como você está se sentindo hoje?',
      m2_mood_happy: 'Radiante',
      m2_mood_calm: 'Calmo',
      m2_mood_anxious: 'Ansioso',
      m2_mood_low: 'Para Baixo',
      m2_feature_cbt: 'Diário de Pensamentos TCC',
      m2_feature_cbt_desc: 'Reestruture pensamentos automáticos disfuncionais',
      m2_feature_breathe: 'Respiração Guiada 4-4-4-4',
      m2_feature_breathe_desc: 'Alívio instantâneo da tensão e taquicardia',
      m2_feature_sleep: 'Sons Noturnos & Aurora Calm',
      m2_feature_sleep_desc: 'Frequências sonoras e meditação para insônia',
      m2_premium_card: 'Aurora Mind Plus',
      m2_premium_desc: 'Desbloqueie testes diagnósticos validados e relatórios semanais para seu médico.',
      m2_premium_btn: 'Experimentar 7 Dias Grátis'
    },

    'en': {
      // General & Brand
      clinic_name: 'Aurora Elo',
      clinic_subtitle: 'Mental Health & Integrated Psychiatry',
      ecosystem_title: 'Unified Design System',
      ecosystem_desc: 'Design System for psychiatric clinic web portal and two mobile apps (clinic-connected companion & retail B2C app store edition).',
      lang_name: 'English (US)',

      // Layout Switcher
      layout_vertical: 'Vertical Menu (Sidebar)',
      layout_horizontal: 'Horizontal Menu (Topbar)',
      theme_light: 'Light',
      theme_dark: 'Dark',

      // Navigation
      nav_dashboard: 'Clinical Dashboard',
      nav_patients: 'Patients',
      nav_appointments: 'Appointments & Schedule',
      nav_records: 'EHR & DSM-5',
      nav_inpatient: 'Beds & Inpatient Care',
      nav_telepsychiatry: 'Telepsychiatry',
      nav_pharmacy: 'Pharmacology & Prescriptions',
      nav_crisis_protocol: 'SOS Crisis Protocol',
      nav_analytics: 'Metrics & Reports',
      nav_settings: 'Settings',
      nav_quick_new_patient: '+ New Patient',
      nav_quick_appointment: '+ New Appointment',
      nav_emergency_btn: 'SOS Crisis 24/7',
      nav_search_placeholder: 'Search patient, ID, record or ICD-11... (Ctrl+K)',
      nav_doctor_role: 'Attending Psychiatrist',
      nav_doctor_crm: 'MD License #148920',

      // Tabs in Showcase
      tab_overview: 'Overview & Tokens',
      tab_navigation: 'Menus & Navigation',
      tab_login: 'Login Screen',
      tab_lists: 'Data Lists & Tables',
      tab_cards: 'Cards & Metrics',
      tab_forms: 'Forms & Masked Inputs',
      tab_mobiles: 'Mobile Applications',

      // Overview Section
      brand_colors_title: 'Official Color Palette',
      brand_colors_desc: 'Extracted directly from the Aurora Elo emblem: midnight navy represents clinical trust, stability and protection; cyan and cerulean symbolize neural dawn, clarity and renewal.',
      tokens_typography: 'Typography & Scale',
      tokens_elevation: 'Shadows & Aurora Glows',

      // Login Screen
      login_title: 'Aurora Elo Clinical Portal',
      login_subtitle: 'Sign in to the secure psychiatric care and integrated health system.',
      login_role_doctor: 'Clinical Staff & Psychiatrists',
      login_role_patient: 'Patient & Family Companion',
      login_role_admin: 'Reception & Hospital Admin',
      login_email_label: 'Email or Medical ID',
      login_email_placeholder: 'e.g. dr.marcelo@auroraelo.med.br or Tax ID',
      login_password_label: 'Password',
      login_password_placeholder: 'Enter your secure password',
      login_remember: 'Keep me signed in for 30 days',
      login_forgot: 'Forgot password?',
      login_submit: 'Secure System Sign In',
      login_2fa_alert: 'Two-Factor Authentication (2FA) Active',
      login_crisis_banner: 'In acute emotional distress or emergency? Dial 988 or reach our 24/7 psychiatric hotline: 0800 770 ELO.',
      login_security_badge: 'HIPAA/GDPR Compliant & End-to-End Encrypted',

      // Forms & Inputs
      form_title: 'Psychiatric Admission & Anamnesis',
      form_subtitle: 'Demonstration of all input types with dynamic masks, validation states, and placeholders.',
      input_name_label: 'Patient Full Name',
      input_name_placeholder: 'e.g., Mariana Silveira Fagundes',
      input_cpf_label: 'Tax ID / Social Security (Masked)',
      input_cpf_placeholder: '000.000.000-00',
      input_phone_label: 'Phone / Cell (Masked)',
      input_phone_placeholder: '(11) 98765-4321',
      input_dob_label: 'Date of Birth (Masked)',
      input_dob_placeholder: 'DD/MM/YYYY',
      input_time_label: 'Session Time (Masked)',
      input_time_placeholder: '14:30',
      input_currency_label: 'Consultation Fee (Masked)',
      input_currency_placeholder: '$ 450.00',
      input_cep_label: 'Postal Code / ZIP (Masked)',
      input_cep_placeholder: '01310-100',
      input_record_label: 'Medical Record ID (Masked)',
      input_record_placeholder: 'PRON-2026-0842',
      input_cns_label: 'Health Insurance / National ID',
      input_cns_placeholder: '741 2045 8921 0004',
      input_email_label: 'Patient Contact & Telehealth Email',
      input_email_placeholder: 'patient@email.com',
      input_password_label: 'Temporary Portal Password',
      input_password_placeholder: 'Min 8 chars, uppercase, digits & symbols',
      input_diagnosis_label: 'Primary Diagnosis (ICD-11 / DSM-5)',
      input_diagnosis_placeholder: 'Select diagnostic category...',
      input_notes_label: 'Chief Complaint & History of Present Illness (HPI)',
      input_notes_placeholder: 'Describe symptom onset, mood episodes, pharmacology history, sleep patterns and protective factors...',
      input_slider_label: 'Anxiety & Stress Visual Analog Scale (0 to 10)',
      input_risk_label: 'Psychiatric Risk Stratification',
      input_risk_low: 'Low Risk (Outpatient Routine)',
      input_risk_mod: 'Moderate (Intensive Follow-up)',
      input_risk_high: 'High Risk / Acute Crisis (SOS Alert)',
      input_modality_label: 'Care Modality',
      input_modality_inperson: 'Clinic In-Person Visit',
      input_modality_telehealth: 'Telepsychiatry HD',
      input_modality_home: 'Home Visit Follow-up',
      input_tags_label: 'Allergies & Medical Comorbidities',
      input_upload_label: 'Lab Tests, ECG & Prior Prescription Upload',
      input_upload_drop: 'Drop files here or click to browse',
      input_upload_hint: 'Supports PDF, DICOM, JPG and PNG up to 25MB',
      input_consent_label: 'Patient signed Informed Consent Form for Telehealth & Privacy Data processing',
      input_btn_save: 'Save Clinical Record & Generate EHR',
      input_btn_cancel: 'Reset Form',

      // Lists & Tables
      list_title: 'Active Patient Management',
      list_search_placeholder: 'Filter by name, record ID, tax code or diagnosis...',
      list_filter_status_all: 'All Statuses',
      list_filter_status_active: 'Active Care',
      list_filter_status_inpatient: 'Inpatient Unit',
      list_filter_status_discharged: 'Discharged',
      list_filter_risk_all: 'All Risk Levels',
      list_col_patient: 'Patient / Contact',
      list_col_record: 'Record #',
      list_col_diag: 'ICD-11 / DSM-5',
      list_col_risk: 'Risk Level',
      list_col_next: 'Next Appointment',
      list_col_status: 'Status',
      list_col_actions: 'Actions',
      list_badge_low: 'Low Risk',
      list_badge_mod: 'Moderate',
      list_badge_high: 'High Risk / SOS',
      list_badge_inpatient: 'Bed 04-B',
      list_badge_active: 'Active',
      list_badge_discharged: 'Discharged',
      list_action_view: 'View EHR',
      list_action_tele: 'Start Telehealth',
      list_action_edit: 'Edit',
      list_pagination_info: 'Showing 1-4 of 128 registered patients',
      list_pagination_prev: 'Previous',
      list_pagination_next: 'Next',

      // Cards
      cards_title: 'Clinical Cards & Metric Widgets',
      card_kpi_active_patients: 'Active Patients',
      card_kpi_today_sessions: 'Today Sessions',
      card_kpi_bed_occupancy: 'Bed Occupancy',
      card_kpi_adherence_rate: 'Medication Adherence',
      card_kpi_urgent_alerts: '24h Crisis Alerts',
      card_tele_title: 'Telepsychiatry Virtual Room',
      card_tele_patient: 'Mariana Silveira Fagundes (34 yo)',
      card_tele_time: 'Starts in 12 minutes (02:30 PM)',
      card_tele_btn: 'Join Encrypted Video Session',
      card_crisis_title: 'Psychiatric Crisis Response Protocol (SOS Elo)',
      card_crisis_desc: 'Rapid de-escalation guidelines, bed admission routing, and immediate emergency contact triggering.',
      card_crisis_call_btn: 'Call 24/7 Psychiatric On-Call',
      card_crisis_hotline_btn: 'Suicide Lifeline 988',
      card_mood_tracker_title: 'Mood & Well-being Tracker (PHQ-9)',
      card_mood_score: 'Euthymic & Stable Mood',

      // Mobile Apps Showcase
      mobiles_section_title: 'Two Mobile Apps: Complete Ecosystem',
      mobiles_section_desc: 'The Design System powers both the clinical mobile app linked to the clinic EHR and the retail B2C wellness app sold on the app stores.',
      mobile_app1_title: 'App 1: Aurora Elo Clinic (EHR Connected)',
      mobile_app1_subtitle: 'For Patients, Family Companions & Clinical Staff',
      mobile_app1_badge: 'Synchronized with Web EHR',
      mobile_app2_title: 'App 2: Aurora Mind & Wellness (B2C App Store)',
      mobile_app2_subtitle: 'Available on Apple App Store & Google Play',
      mobile_app2_badge: 'Retail B2C & Premium Subscription',

      // Mobile 1 UI Strings
      m1_welcome: 'Hello, Mariana',
      m1_status: 'Your care plan is on track',
      m1_quick_tele: 'Telehealth Today, 02:30 PM',
      m1_doctor: 'Dr. Marcelo Arantes • Psychiatrist',
      m1_join_call: 'Join Video Consultation',
      m1_meds_title: 'Today Medications',
      m1_med_1: 'Escitalopram 15mg • 08:00 AM (Taken ✓)',
      m1_med_2: 'Quetiapine 25mg • 09:00 PM (Upcoming)',
      m1_sos_btn: 'Immediate Crisis / SOS Help',
      m1_chat_doc: 'Secure Message with Doctor',

      // Mobile 2 UI Strings
      m2_brand: 'Aurora Mind',
      m2_greeting: 'How are you feeling today?',
      m2_mood_happy: 'Radiant',
      m2_mood_calm: 'Calm',
      m2_mood_anxious: 'Anxious',
      m2_mood_low: 'Down',
      m2_feature_cbt: 'CBT Thought Journal',
      m2_feature_cbt_desc: 'Challenge negative automatic thoughts',
      m2_feature_breathe: 'Box Breathing 4-4-4-4',
      m2_feature_breathe_desc: 'Fast nervous system reset and panic relief',
      m2_feature_sleep: 'Night Soundscapes & Aurora Calm',
      m2_feature_sleep_desc: 'Clinically calibrated binaural tones for deep sleep',
      m2_premium_card: 'Aurora Mind Plus',
      m2_premium_desc: 'Unlock clinical-grade assessments and weekly exportable reports for your doctor.',
      m2_premium_btn: 'Start 7-Day Free Trial'
    },

    'es': {
      // General & Brand
      clinic_name: 'Aurora Elo',
      clinic_subtitle: 'Salud Mental & Psiquiatría Integrada',
      ecosystem_title: 'Sistema de Diseño Unificado',
      ecosystem_desc: 'Design System para el ecosistema web clínico y dos aplicaciones móviles (clínica conectada y B2C en tiendas de apps).',
      lang_name: 'Español',

      // Layout Switcher
      layout_vertical: 'Menú Vertical (Sidebar)',
      layout_horizontal: 'Menú Horizontal (Topbar)',
      theme_light: 'Claro',
      theme_dark: 'Oscuro',

      // Navigation
      nav_dashboard: 'Panel Clínico',
      nav_patients: 'Pacientes',
      nav_appointments: 'Citas & Agenda',
      nav_records: 'Expedientes & DSM-5',
      nav_inpatient: 'Camas & Hospitalización',
      nav_telepsychiatry: 'Telepsiquiatría',
      nav_pharmacy: 'Farmacología & Recetas',
      nav_crisis_protocol: 'Protocolo de Crisis SOS',
      nav_analytics: 'Analíticas & Reportes',
      nav_settings: 'Configuración',
      nav_quick_new_patient: '+ Nuevo Paciente',
      nav_quick_appointment: '+ Nueva Cita',
      nav_emergency_btn: 'SOS Crisis 24h',
      nav_search_placeholder: 'Buscar paciente, documento, expediente o CIE-11... (Ctrl+K)',
      nav_doctor_role: 'Psiquiatra Titular',
      nav_doctor_crm: 'Cédula Médica #148920',

      // Tabs in Showcase
      tab_overview: 'Visión General & Tokens',
      tab_navigation: 'Menús & Navegación',
      tab_login: 'Pantalla de Inicio',
      tab_lists: 'Listados & Tablas',
      tab_cards: 'Tarjetas & Métricas',
      tab_forms: 'Formularios & Máscaras',
      tab_mobiles: 'Aplicaciones Móviles',

      // Overview Section
      brand_colors_title: 'Paleta Cromática Oficial',
      brand_colors_desc: 'Inspirada en el logotipo Aurora Elo: el azul marino profundo evoca solidez, protección y rigor clínico; el cian y cerúleo reflejan el lazo neuronal, claridad mental y renacer.',
      tokens_typography: 'Tipografía & Escala',
      tokens_elevation: 'Sombras & Resplandores Aurora',

      // Login Screen
      login_title: 'Portal Clínico Aurora Elo',
      login_subtitle: 'Acceda al entorno seguro de gestión psiquiátrica y cuidado integral.',
      login_role_doctor: 'Cuerpo Clínico & Psiquiatría',
      login_role_patient: 'Paciente & Familiar',
      login_role_admin: 'Recepción & Administración',
      login_email_label: 'Correo o Identificación',
      login_email_placeholder: 'ej: dr.marcelo@auroraelo.med.br o DNI',
      login_password_label: 'Contraseña de Acceso',
      login_password_placeholder: 'Introduzca su contraseña con seguridad',
      login_remember: 'Recordar este dispositivo por 30 días',
      login_forgot: '¿Olvidó su contraseña?',
      login_submit: 'Ingresar al Sistema Seguro',
      login_2fa_alert: 'Autenticación de Dos Factores (2FA) Activa',
      login_crisis_banner: '¿En crisis emocional o emergencia aguda? Llame al 024 / 988 o contacte nuestra guardia 24h: 0800 770 ELO.',
      login_security_badge: 'Cumplimiento Normativo & Cifrado de Extremo a Extremo',

      // Forms & Inputs
      form_title: 'Admisión & Anamnesis Psiquiátrica',
      form_subtitle: 'Demostración de todos los tipos de entradas con máscaras dinámicas, validación y marcadores de posición.',
      input_name_label: 'Nombre Completo del Paciente',
      input_name_placeholder: 'Ej: Mariana Silveira Fagundes',
      input_cpf_label: 'Documento / DNI (Con máscara)',
      input_cpf_placeholder: '000.000.000-00',
      input_phone_label: 'Teléfono / Móvil (Con máscara)',
      input_phone_placeholder: '(11) 98765-4321',
      input_dob_label: 'Fecha de Nacimiento (Con máscara)',
      input_dob_placeholder: 'DD/MM/AAAA',
      input_time_label: 'Hora de la Sesión (Con máscara)',
      input_time_placeholder: '14:30',
      input_currency_label: 'Honorario de Consulta (Con máscara)',
      input_currency_placeholder: '$ 450,00',
      input_cep_label: 'Código Postal (Con máscara)',
      input_cep_placeholder: '01310-100',
      input_record_label: 'Código de Expediente (Con máscara)',
      input_record_placeholder: 'PRON-2026-0842',
      input_cns_label: 'Seguro Médico / Registro Nacional',
      input_cns_placeholder: '741 2045 8921 0004',
      input_email_label: 'Correo de Contacto & Teleconsulta',
      input_email_placeholder: 'paciente@correo.com',
      input_password_label: 'Contraseña Provisional de Acceso',
      input_password_placeholder: 'Mínimo 8 caracteres, mayúsculas y símbolos',
      input_diagnosis_label: 'Diagnóstico Principal (CIE-11 / DSM-5)',
      input_diagnosis_placeholder: 'Seleccione la categoría diagnóstica...',
      input_notes_label: 'Motivo de Consulta & Historia de la Enfermedad Actual',
      input_notes_placeholder: 'Describa evolución de síntomas, ciclos de ánimo, antecedentes farmacológicos y factores protectores...',
      input_slider_label: 'Escala Visual Analógica de Ansiedad / Estrés (0 a 10)',
      input_risk_label: 'Estratificación del Riesgo Psiquiátrico',
      input_risk_low: 'Bajo Riesgo (Ambulatorio)',
      input_risk_mod: 'Moderado (Seguimiento Intensivo)',
      input_risk_high: 'Alto Riesgo / Crisis Inmediata (Alerta SOS)',
      input_modality_label: 'Modalidad de Atención',
      input_modality_inperson: 'Presencial en Clínica',
      input_modality_telehealth: 'Telepsiquiatría HD',
      input_modality_home: 'Atención Domiciliaria',
      input_tags_label: 'Alergias & Comorbilidades Médicas',
      input_upload_label: 'Cargar Análisis de Laboratorio, ECG & Recetas',
      input_upload_drop: 'Arrastre los archivos aquí o haga clic para seleccionar',
      input_upload_hint: 'Admite PDF, DICOM, JPG y PNG hasta 25MB',
      input_consent_label: 'El paciente firmó el Consentimiento Informado para Telemedicina y Protección de Datos',
      input_btn_save: 'Guardar Expediente & Registrar Consulta',
      input_btn_cancel: 'Restablecer Formulario',

      // Lists & Tables
      list_title: 'Gestión de Pacientes en Seguimiento',
      list_search_placeholder: 'Filtrar por nombre, expediente, documento o diagnóstico...',
      list_filter_status_all: 'Todos los Estados',
      list_filter_status_active: 'En Seguimiento',
      list_filter_status_inpatient: 'Hospitalización',
      list_filter_status_discharged: 'Alta Médica',
      list_filter_risk_all: 'Todos los Niveles de Riesgo',
      list_col_patient: 'Paciente / Contacto',
      list_col_record: 'Expediente',
      list_col_diag: 'CIE-11 / DSM-5',
      list_col_risk: 'Nivel de Riesgo',
      list_col_next: 'Próxima Cita',
      list_col_status: 'Estado',
      list_col_actions: 'Acciones',
      list_badge_low: 'Bajo Riesgo',
      list_badge_mod: 'Moderado',
      list_badge_high: 'Alto Riesgo / SOS',
      list_badge_inpatient: 'Cama 04-B',
      list_badge_active: 'Activo',
      list_badge_discharged: 'Alta Terapéutica',
      list_action_view: 'Ver Expediente',
      list_action_tele: 'Iniciar Teleconsulta',
      list_action_edit: 'Editar',
      list_pagination_info: 'Mostrando 1-4 de 128 pacientes registrados',
      list_pagination_prev: 'Anterior',
      list_pagination_next: 'Siguiente',

      // Cards
      cards_title: 'Biblioteca de Tarjetas Clínicas & Métricas',
      card_kpi_active_patients: 'Pacientes Activos',
      card_kpi_today_sessions: 'Citas de Hoy',
      card_kpi_bed_occupancy: 'Ocupación de Camas',
      card_kpi_adherence_rate: 'Adherencia a Fármacos',
      card_kpi_urgent_alerts: 'Alertas de Crisis 24h',
      card_tele_title: 'Sala Virtual de Telepsiquiatría',
      card_tele_patient: 'Mariana Silveira Fagundes (34 años)',
      card_tele_time: 'Comienza en 12 minutos (14:30)',
      card_tele_btn: 'Entrar a la Sala Virtual Cifrada',
      card_crisis_title: 'Protocolo de Emergencia Psiquiátrica (SOS Elo)',
      card_crisis_desc: 'Guía de respuesta rápida para contención verbal, derivación de camas y activación de red de apoyo.',
      card_crisis_call_btn: 'Llamar a Guardia Psiquiátrica 24h',
      card_crisis_hotline_btn: 'Línea de Prevención 024 / 988',
      card_mood_tracker_title: 'Evaluación de Ánimo & Bienestar (PHQ-9)',
      card_mood_score: 'Ánimo Eutímico y Estable',

      // Mobile Apps Showcase
      mobiles_section_title: 'Dos Aplicaciones Móviles: Ecosistema Completo',
      mobiles_section_desc: 'El Design System potencia la app clínica conectada al expediente web y la app B2C de autocuidado comercializada en las tiendas de apps.',
      mobile_app1_title: 'App 1: Aurora Elo Clínica (Conectada a la Web)',
      mobile_app1_subtitle: 'Para Pacientes, Familiares y Equipo Médico',
      mobile_app1_badge: 'Sincronizada con el Expediente Web',
      mobile_app2_title: 'App 2: Aurora Mind & Wellness (B2C Tiendas de Apps)',
      mobile_app2_subtitle: 'Disponible en Google Play y Apple App Store',
      mobile_app2_badge: 'Monetización B2C & Suscripción Premium',

      // Mobile 1 UI Strings
      m1_welcome: 'Hola, Mariana',
      m1_status: 'Tu plan terapéutico está al día',
      m1_quick_tele: 'Teleconsulta Hoy, 14:30',
      m1_doctor: 'Dr. Marcelo Arantes • Psiquiatra',
      m1_join_call: 'Acceder a la Teleconsulta',
      m1_meds_title: 'Medicamentos de Hoy',
      m1_med_1: 'Escitalopram 15mg • 08:00 (Tomado ✓)',
      m1_med_2: 'Quetiapina 25mg • 21:00 (Pendiente)',
      m1_sos_btn: 'Botón de Ayuda Inmediata / SOS',
      m1_chat_doc: 'Mensaje Seguro con el Doctor',

      // Mobile 2 UI Strings
      m2_brand: 'Aurora Mind',
      m2_greeting: '¿Cómo te sientes hoy?',
      m2_mood_happy: 'Radiante',
      m2_mood_calm: 'En Calma',
      m2_mood_anxious: 'Ansioso',
      m2_mood_low: 'Desanimado',
      m2_feature_cbt: 'Diario de Pensamientos TCC',
      m2_feature_cbt_desc: 'Reestructura pensamientos automáticos desadaptativos',
      m2_feature_breathe: 'Respiración Guiada 4-4-4-4',
      m2_feature_breathe_desc: 'Alivio rápido de la tensión y taquicardia',
      m2_feature_sleep: 'Sonidos del Sueño & Aurora Calm',
      m2_feature_sleep_desc: 'Frecuencias binaurales y meditación para el insomnio',
      m2_premium_card: 'Aurora Mind Plus',
      m2_premium_desc: 'Desbloquea evaluaciones clínicas validadas e informes semanales para tu médico.',
      m2_premium_btn: 'Probar 7 Días Gratis'
    }
  },

  setLanguage(lang) {
    if (!this.translations[lang]) return;
    this.currentLang = lang;
    document.documentElement.setAttribute('lang', lang);
    localStorage.setItem('aurora_lang', lang);
    this.applyTranslations();
  },

  t(key) {
    const dict = this.translations[this.currentLang] || this.translations['pt-BR'];
    return dict[key] || key;
  },

  applyTranslations() {
    // Update elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translation = this.t(key);
      if (translation) {
        el.textContent = translation;
      }
    });

    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const translation = this.t(key);
      if (translation) {
        el.setAttribute('placeholder', translation);
      }
    });

    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      const translation = this.t(key);
      if (translation) {
        el.setAttribute('title', translation);
      }
    });

    // Fire event for custom components
    window.dispatchEvent(new CustomEvent('aurora-language-changed', { detail: { lang: this.currentLang } }));
  },

  init() {
    const saved = localStorage.getItem('aurora_lang');
    if (saved && this.translations[saved]) {
      this.currentLang = saved;
    }
    this.applyTranslations();
  }
};

if (typeof window !== 'undefined') {
  window.AuroraI18n = AuroraI18n;
}
