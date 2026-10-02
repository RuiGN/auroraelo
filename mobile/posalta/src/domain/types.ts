/**
 * Tipos de domínio do app Pós-Alta.
 *
 * Espelham, em camelCase, os campos dos modelos Django que o paciente enxerga
 * (journal, goals, routines, scheduling, wellness, support_network, content,
 * consents, privacy).
 *
 * Fora do escopo do app do paciente (pertencem ao aplicativo da clínica): régua
 * de acompanhamento pós-alta (ligações/visita), concierge e contato com a família,
 * e mensagens com a equipe.
 */

export type ISODate = string; // YYYY-MM-DD
export type ISODateTime = string; // ISO 8601 com fuso

export type Visibility = "private" | "shareable" | "confirmation_required";

export type Scale5 = 1 | 2 | 3 | 4 | 5;

// ── Paciente e equipe ───────────────────────────────────────────────────────

export type TeamRole =
  | "psychiatrist"
  | "psychologist"
  | "nurse"
  | "pharmacist"
  | "other";

export interface TeamMember {
  id: string;
  name: string;
  role: TeamRole;
}

export interface PatientSummary {
  id: string;
  /** Nome social quando existir (people.PatientProfile.social_name). */
  displayName: string;
  clinicName: string;
  /** `null` quando a clínica ainda não registrou a alta. */
  dischargeDate: ISODate | null;
  /** Fuso IANA do paciente: as doses programadas ("HH:MM") valem nesse fuso. */
  timezone: string;
  careTeam: TeamMember[];
}

// ── Check-in e diário (journal) ─────────────────────────────────────────────

export const CHECKIN_QUESTION_KEYS = [
  "general_state",
  "anxiety",
  "sadness",
  "irritability",
  "energy",
  "sleep_quality",
  "motivation",
] as const;
export type CheckInQuestionKey = (typeof CHECKIN_QUESTION_KEYS)[number];

export type CheckInScaleAnswers = Record<CheckInQuestionKey, Scale5>;

export interface DailyCheckIn {
  id: string;
  date: ISODate;
  answers: CheckInScaleAnswers;
  notes: string;
  visibility: Visibility;
  submittedAt: ISODateTime;
}

export const EMOTIONS = [
  "anxiety",
  "sadness",
  "anger",
  "joy",
  "fear",
  "calm",
  "frustration",
  "hope",
] as const;
export type Emotion = (typeof EMOTIONS)[number];

export interface JournalEntry {
  id: string;
  createdAt: ISODateTime;
  mood: Scale5;
  emotions: Emotion[];
  intensity: Scale5;
  context: string;
  triggers: string;
  reactions: string;
  strategies: string;
  visibility: Visibility;
}

// ── Fissura e meta de recuperação (wellness) ────────────────────────────────

export interface SobrietyGoal {
  id: string;
  goalType: "abstinence" | "reduction" | "moderation";
  /** Texto livre do paciente: substância ou comportamento. */
  focus: string;
  referenceDate: ISODate;
  restartCount: number;
  motivations: string;
  hideCounter: boolean;
}

export interface CravingLog {
  id: string;
  recordedAt: ISODateTime;
  /** 0 a 10. */
  intensity: number;
  triggersContext: string;
  copingStrategyUsed: string;
}

// ── Medicação (routines.PrescribedMedication / MedicationLog) ───────────────

export type MedicationRoute =
  | "oral"
  | "sublingual"
  | "topical"
  | "inhalation"
  | "injectable"
  | "ophthalmic"
  | "nasal"
  | "other";

export interface Medication {
  id: string;
  name: string;
  presentation: string;
  dose: string;
  route: MedicationRoute;
  /** Horários "HH:MM" no fuso do paciente. */
  scheduleTimes: string[];
  startDate: ISODate;
  endDate: ISODate | null;
  isContinuous: boolean;
  prescriberName: string;
  instructions: string;
}

export type DoseStatus = "taken" | "late" | "omitted";

export interface DoseLog {
  id: string;
  medicationId: string;
  /** Instante programado (data + horário). */
  scheduledFor: ISODateTime;
  status: DoseStatus;
  recordedAt: ISODateTime;
}

// ── Plano de cuidado (routines.CarePlan) ────────────────────────────────────

export type CarePlanStatus =
  | "draft"
  | "pending_signature"
  | "active"
  | "paused"
  | "completed"
  | "revoked";

export type CarePlanDecision =
  | "accepted"
  | "refused"
  | "paused"
  | "review_requested";

export interface CarePlanAction {
  id: string;
  description: string;
  targetFrequency: string;
  guidance: string;
  isMandatory: boolean;
}

export interface CarePlan {
  id: string;
  title: string;
  objective: string;
  contraindications: string;
  status: CarePlanStatus;
  version: number;
  validFrom: ISODate;
  validUntil: ISODate | null;
  prescriberName: string;
  actions: CarePlanAction[];
  response: {
    decision: CarePlanDecision;
    notes: string;
    respondedAt: ISODateTime;
  } | null;
}

// ── Rotina (routines.Habit) ─────────────────────────────────────────────────

export type TimeWindow =
  | "morning"
  | "afternoon"
  | "evening"
  | "night"
  | "any_time";
export type HabitStatus = "completed" | "partial" | "postponed" | "skipped";

export interface Habit {
  id: string;
  title: string;
  description: string;
  timeWindow: TimeWindow;
  /** "HH:MM" opcional. */
  targetTime: string | null;
}

export interface HabitCheck {
  habitId: string;
  date: ISODate;
  status: HabitStatus;
}

// ── Exercícios terapêuticos (goals.ExerciseAssignment) ──────────────────────

export interface ExerciseAssignment {
  id: string;
  title: string;
  instructions: string;
  approach: string;
  estimatedMinutes: number;
  responseFormat: "text" | "scale_1_5";
  frequency: string;
  dueDate: ISODate | null;
  assignedByName: string;
  status: "assigned" | "completed";
  response: string;
  completedAt: ISODateTime | null;
  visibility: Visibility;
}

// ── Plano de prevenção de recaída (wellness.RelapsePreventionPlan) ──────────

export type RelapseSectionType =
  | "triggers"
  | "early_warning_signs"
  | "protective_factors"
  | "coping_strategies"
  | "safe_environments"
  | "support_contacts"
  | "professional_resources";

export interface RelapsePlanSection {
  id: string;
  type: RelapseSectionType;
  title: string;
  content: string;
}

export interface RelapsePlan {
  id: string;
  title: string;
  version: number;
  lastReviewedAt: ISODateTime | null;
  sections: RelapsePlanSection[];
}

// ── Metas (goals.Goal) ──────────────────────────────────────────────────────

export type GoalStatus = "active" | "paused" | "completed" | "archived";
export type GoalHorizon = "short" | "medium" | "long";

export interface GoalStep {
  id: string;
  description: string;
  order: number;
  isDone: boolean;
}

export interface Goal {
  id: string;
  title: string;
  description: string;
  horizon: GoalHorizon;
  dueDate: ISODate | null;
  status: GoalStatus;
  steps: GoalStep[];
}

// ── Modo de pouca energia (goals.LowEnergyMode) ─────────────────────────────

export interface LowEnergyPlan {
  /** Até três ações mínimas definidas com a equipe. */
  actions: string[];
  active: boolean;
  startedAt: ISODateTime | null;
}

// ── Agenda (scheduling) ─────────────────────────────────────────────────────

export type AppointmentStatus =
  | "requested"
  | "confirmed"
  | "reschedule_requested"
  | "canceled"
  | "completed"
  | "no_show";

export interface Appointment {
  id: string;
  serviceName: string;
  professionalName: string;
  unitName: string;
  startAt: ISODateTime;
  endAt: ISODateTime;
  status: AppointmentStatus;
  cancelReason: string;
}

export interface BookableService {
  id: string;
  name: string;
  durationMinutes: number;
  professionalName: string;
  unitName: string;
  /** Horários livres devolvidos por GET /scheduling/appointments/free-slots/. */
  freeSlots: ISODateTime[];
}

// ── Rede de apoio (support_network) ─────────────────────────────────────────

export type SupportScope =
  | "view_goals"
  | "view_routine"
  | "view_appointments"
  | "receive_alerts";

export interface SupportRelationship {
  id: string;
  name: string;
  relationship: string;
  scopes: SupportScope[];
  active: boolean;
}

// ── Plano de apoio urgente (support_network.UrgentSupportPlan) ──────────────

export interface UrgentContact {
  id: string;
  name: string;
  relationship: string;
  phone: string;
  messageTemplate: string;
}

export interface UrgentPlan {
  personalInstructions: string;
  calmingStrategies: string[];
  contacts: UrgentContact[];
  lastReviewedAt: ISODateTime;
}

// ── Conteúdo (content.Content / ContentRecommendation) ──────────────────────

export type ContentKind = "article" | "video" | "audio" | "exercise";

export interface ContentItem {
  id: string;
  title: string;
  kind: ContentKind;
  category: string;
  body: string;
  contraindications: string;
  sourceReference: string;
  recommendedByName: string | null;
  recommendationObjective: string | null;
  estimatedMinutes: number;
  favorite: boolean;
  read: boolean;
}

// ── Consentimento e privacidade (consents / privacy) ────────────────────────

/** Subconjunto de consents.policies.ConsentPurpose relevante ao paciente no app. */
export type ConsentPurposeKey =
  | "terms_of_use"
  | "clinical_limits"
  | "clinical_follow_up"
  | "communication";

export interface ConsentRecord {
  id: string;
  purpose: ConsentPurposeKey;
  documentVersion: string;
  status: "granted" | "revoked";
  decidedAt: ISODateTime;
  mandatory: boolean;
}

export type PrivacyRequestType =
  | "confirmation"
  | "access"
  | "correction"
  | "portability"
  | "revocation"
  | "erasure";

export interface PrivacyRequest {
  id: string;
  type: PrivacyRequestType;
  requestedAt: ISODateTime;
  status: "identity_pending" | "in_review" | "completed";
}

// ── Instantâneo completo mantido pelo store ─────────────────────────────────

export interface Snapshot {
  patient: PatientSummary;
  checkIns: DailyCheckIn[];
  journal: JournalEntry[];
  sobriety: SobrietyGoal | null;
  cravings: CravingLog[];
  medications: Medication[];
  doseLogs: DoseLog[];
  carePlan: CarePlan | null;
  habits: Habit[];
  habitChecks: HabitCheck[];
  exercises: ExerciseAssignment[];
  relapsePlan: RelapsePlan | null;
  goals: Goal[];
  lowEnergy: LowEnergyPlan;
  appointments: Appointment[];
  services: BookableService[];
  supportNetwork: SupportRelationship[];
  urgentPlan: UrgentPlan | null;
  content: ContentItem[];
  consents: ConsentRecord[];
  privacyRequests: PrivacyRequest[];
}
