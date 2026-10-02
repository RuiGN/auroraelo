import {
  CheckInScaleAnswers,
  DoseLog,
  Goal,
  Habit,
  HabitCheck,
  HabitStatus,
  ISODate,
  ISODateTime,
  Medication,
  Snapshot,
} from "./types";

const DAY_MS = 24 * 60 * 60 * 1000;

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** Data local (YYYY-MM-DD) de um instante, no fuso do aparelho. */
export function toISODate(date: Date): ISODate {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Interpreta YYYY-MM-DD como data local ao meio-dia (evita saltos de fuso/horário de verão). */
export function parseISODate(value: ISODate): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12, 0, 0, 0);
}

export function addDays(value: ISODate, days: number): ISODate {
  const date = parseISODate(value);
  date.setDate(date.getDate() + days);
  return toISODate(date);
}

/** Diferença em dias de calendário: positiva quando `to` é posterior a `from`. */
export function daysBetween(from: ISODate, to: ISODate): number {
  return Math.round(
    (parseISODate(to).getTime() - parseISODate(from).getTime()) / DAY_MS,
  );
}

export function daysSince(date: ISODate, now: Date): number {
  return daysBetween(date, toISODate(now));
}

/** Combina data e horário "HH:MM" locais em ISO com fuso. */
export function combineDateTime(date: ISODate, time: string): ISODateTime {
  const [hours, minutes] = time.split(":").map(Number);
  const [year, month, day] = date.split("-").map(Number);
  return new Date(year, month - 1, day, hours, minutes, 0, 0).toISOString();
}

export type PartOfDay = "morning" | "afternoon" | "evening";

export function partOfDay(now: Date): PartOfDay {
  const hour = now.getHours();
  if (hour < 12) return "morning";
  if (hour < 18) return "afternoon";
  return "evening";
}

export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName;
}

// ── Medicação ───────────────────────────────────────────────────────────────

export function isMedicationActiveOn(
  medication: Medication,
  day: ISODate,
): boolean {
  if (day < medication.startDate) return false;
  if (
    !medication.isContinuous &&
    medication.endDate &&
    day > medication.endDate
  )
    return false;
  return true;
}

export interface DoseSlot {
  key: string;
  medication: Medication;
  /** Horário "HH:MM". */
  time: string;
  scheduledFor: ISODateTime;
  log: DoseLog | null;
}

export function doseSlotsForDay(snapshot: Snapshot, day: ISODate): DoseSlot[] {
  const slots: DoseSlot[] = [];
  for (const medication of snapshot.medications) {
    if (!isMedicationActiveOn(medication, day)) continue;
    for (const time of medication.scheduleTimes) {
      const scheduledFor = combineDateTime(day, time);
      const log =
        snapshot.doseLogs.find(
          (entry) =>
            entry.medicationId === medication.id &&
            entry.scheduledFor === scheduledFor,
        ) ?? null;
      slots.push({
        key: `${medication.id}@${scheduledFor}`,
        medication,
        time,
        scheduledFor,
        log,
      });
    }
  }
  return slots.sort(
    (a, b) => a.time.localeCompare(b.time) || a.key.localeCompare(b.key),
  );
}

export function doseSummary(slots: DoseSlot[]): {
  done: number;
  total: number;
} {
  return {
    done: slots.filter((slot) => slot.log !== null).length,
    total: slots.length,
  };
}

// ── Rotina ──────────────────────────────────────────────────────────────────

export function habitStatusOn(
  checks: HabitCheck[],
  habitId: string,
  day: ISODate,
): HabitStatus | null {
  return (
    checks.find((check) => check.habitId === habitId && check.date === day)
      ?.status ?? null
  );
}

export function habitSummary(
  habits: Habit[],
  checks: HabitCheck[],
  day: ISODate,
): { done: number; total: number } {
  const done = habits.filter(
    (habit) => habitStatusOn(checks, habit.id, day) === "completed",
  ).length;
  return { done, total: habits.length };
}

// ── Metas ───────────────────────────────────────────────────────────────────

export function goalProgress(goal: Goal): {
  done: number;
  total: number;
  percent: number;
} {
  const total = goal.steps.length;
  const done = goal.steps.filter((step) => step.isDone).length;
  return {
    done,
    total,
    percent: total === 0 ? 0 : Math.round((done / total) * 100),
  };
}

// ── Check-in ────────────────────────────────────────────────────────────────

export function checkInDoneOn(snapshot: Snapshot, day: ISODate): boolean {
  return snapshot.checkIns.some((checkIn) => checkIn.date === day);
}

/**
 * Regra determinística e conservadora para oferecer apoio (não é diagnóstico nem
 * triagem clínica): estado geral baixo ou ansiedade/tristeza altas.
 */
export function suggestsExtraSupport(answers: CheckInScaleAnswers): boolean {
  return (
    answers.general_state <= 2 || answers.anxiety >= 4 || answers.sadness >= 4
  );
}

// ── Agenda ──────────────────────────────────────────────────────────────────

export function nextAppointment(snapshot: Snapshot, now: Date) {
  const nowIso = now.toISOString();
  return (
    snapshot.appointments
      .filter(
        (item) =>
          item.endAt >= nowIso &&
          (item.status === "confirmed" || item.status === "requested"),
      )
      .sort((a, b) => a.startAt.localeCompare(b.startAt))[0] ?? null
  );
}

// ── Contador de recuperação ─────────────────────────────────────────────────

/** Dias desde a data de referência da meta; nunca negativo. */
export function recoveryDays(referenceDate: ISODate, now: Date): number {
  return Math.max(0, daysSince(referenceDate, now));
}
