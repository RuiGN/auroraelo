/**
 * Domínio de cuidado no modo live: medicação e doses, plano de cuidado, rotina,
 * exercícios e pouca energia (api/mobile_care_api.py).
 *
 * Instantes entram normalizados em UTC (`instant`): `combineDateTime` do app gera o
 * mesmo texto, então a conferência de doses por igualdade continua valendo.
 */
import {
  bool,
  id,
  instant,
  isoDate,
  list,
  maybeInstant,
  maybeIsoDate,
  maybeText,
  oneOf,
  record,
  text,
  textList,
} from "../../api/parse";
import {
  CarePlan,
  CarePlanDecision,
  CarePlanStatus,
  DoseLog,
  DoseStatus,
  ExerciseAssignment,
  Habit,
  HabitCheck,
  HabitStatus,
  LowEnergyPlan,
  Medication,
  MedicationRoute,
  TimeWindow,
  Visibility,
} from "../../domain/types";
import type { LiveActionRegistry } from "./actions";
import type { LoaderEntry } from "./registry";

const ROUTES: readonly MedicationRoute[] = [
  "oral",
  "sublingual",
  "topical",
  "inhalation",
  "injectable",
  "ophthalmic",
  "nasal",
  "other",
];
const DOSE_STATUSES: readonly DoseStatus[] = ["taken", "late", "omitted"];
const PLAN_STATUSES: readonly CarePlanStatus[] = [
  "draft",
  "pending_signature",
  "active",
  "paused",
  "completed",
  "revoked",
];
const DECISIONS: readonly CarePlanDecision[] = [
  "accepted",
  "refused",
  "paused",
  "review_requested",
];
const WINDOWS: readonly TimeWindow[] = [
  "morning",
  "afternoon",
  "evening",
  "night",
  "any_time",
];
const HABIT_STATUSES: readonly HabitStatus[] = [
  "completed",
  "partial",
  "postponed",
  "skipped",
];
const VISIBILITIES: readonly Visibility[] = [
  "private",
  "shareable",
  "confirmation_required",
];
/** Formatos que o app sabe responder; os outros não aparecem (o servidor recusaria). */
const SUPPORTED_FORMATS = ["text", "scale_1_5"] as const;

/** Dias de rotina pedidos ao servidor (o máximo que o app consegue marcar). */
export const ROUTINE_DAYS = 8;

// ── Medicação ───────────────────────────────────────────────────────────────

function parseMedication(value: unknown): Medication {
  const source = record(value);
  return {
    id: id(source.id),
    name: text(source.name, 300),
    presentation: text(source.presentation, 300),
    dose: text(source.dose, 300),
    route: oneOf(source.route, ROUTES, "other"),
    scheduleTimes: list(
      source.schedule_times,
      (entry) => {
        const time = text(entry, 5);
        return /^\d{2}:\d{2}$/.test(time) ? time : text(null);
      },
      24,
    ),
    startDate: isoDate(source.start_date),
    endDate: maybeIsoDate(source.end_date),
    isContinuous: bool(source.is_continuous),
    prescriberName: text(source.prescriber_name, 300),
    instructions: text(source.instructions, 4000),
  };
}

function parseDoseLog(value: unknown): DoseLog | null {
  const source = record(value);
  const status = oneOf<DoseStatus | "">(source.status, DOSE_STATUSES, "");
  if (status === "") return null; // estado que o app não mostra (ex.: não informado)
  return {
    id: id(source.id),
    medicationId: id(source.medication_id),
    scheduledFor: instant(source.scheduled_for),
    status,
    recordedAt: instant(source.recorded_at),
  };
}

export const medicationsLoader: LoaderEntry = {
  slices: ["medications", "doseLogs"],
  load: async (api) => {
    const body = await api.get("/mobile/medications/", { parse: record });
    return {
      medications: list(body.medications, parseMedication),
      doseLogs: list(body.dose_logs, parseDoseLog, 2000).filter(
        (log): log is DoseLog => log !== null,
      ),
    };
  },
};

// ── Plano de cuidado ────────────────────────────────────────────────────────

export function parseCarePlan(value: unknown): CarePlan {
  const source = record(value);
  const response =
    source.response === null || source.response === undefined
      ? null
      : record(source.response);
  return {
    id: id(source.id),
    title: text(source.title, 300),
    objective: text(source.objective, 4000),
    contraindications: text(source.contraindications, 4000),
    status: oneOf(source.status, PLAN_STATUSES, "active"),
    version: typeof source.version === "number" ? source.version : 1,
    validFrom: isoDate(source.valid_from),
    validUntil: maybeIsoDate(source.valid_until),
    prescriberName: text(source.prescriber_name, 300),
    actions: list(source.actions, (entry) => {
      const action = record(entry);
      return {
        id: id(action.id),
        description: text(action.description, 4000),
        targetFrequency: text(action.target_frequency, 300),
        guidance: text(action.guidance, 4000),
        isMandatory: bool(action.is_mandatory),
      };
    }),
    response: response
      ? {
          decision: oneOf(response.decision, DECISIONS, "accepted"),
          notes: text(response.notes, 4000),
          respondedAt: instant(response.responded_at),
        }
      : null,
  };
}

export const carePlanLoader: LoaderEntry = {
  slices: ["carePlan"],
  load: async (api) => {
    const body = await api.get("/mobile/care-plan/", { parse: record });
    return {
      carePlan:
        body.care_plan === null || body.care_plan === undefined
          ? null
          : parseCarePlan(body.care_plan),
    };
  },
};

// ── Rotina ──────────────────────────────────────────────────────────────────

function parseHabit(value: unknown): Habit {
  const source = record(value);
  return {
    id: id(source.id),
    title: text(source.title, 300),
    description: text(source.description, 4000),
    timeWindow: oneOf(source.time_window, WINDOWS, "any_time"),
    targetTime: maybeText(source.target_time, 5),
  };
}

function parseHabitCheck(value: unknown): HabitCheck | null {
  const source = record(value);
  const status = oneOf<HabitStatus | "">(source.status, HABIT_STATUSES, "");
  if (status === "") return null;
  return {
    habitId: id(source.habit_id),
    date: isoDate(source.date),
    status,
  };
}

export const routineLoader: LoaderEntry = {
  slices: ["habits", "habitChecks"],
  load: async (api) => {
    const body = await api.get("/mobile/routine/", {
      query: { days: ROUTINE_DAYS },
      parse: record,
    });
    return {
      habits: list(body.habits, parseHabit),
      habitChecks: list(body.checks, parseHabitCheck, 5000).filter(
        (check): check is HabitCheck => check !== null,
      ),
    };
  },
};

// ── Exercícios ──────────────────────────────────────────────────────────────

function parseExercise(value: unknown): ExerciseAssignment | null {
  const source = record(value);
  const format = oneOf<(typeof SUPPORTED_FORMATS)[number] | "">(
    source.response_format,
    SUPPORTED_FORMATS,
    "",
  );
  if (format === "") return null;
  return {
    id: id(source.id),
    title: text(source.title, 300),
    instructions: text(source.instructions, 8000),
    approach: text(source.approach, 300),
    estimatedMinutes:
      typeof source.estimated_minutes === "number"
        ? source.estimated_minutes
        : 0,
    responseFormat: format,
    frequency: text(source.frequency, 300),
    dueDate: maybeIsoDate(source.due_date),
    assignedByName: text(source.assigned_by_name, 300),
    status: source.status === "completed" ? "completed" : "assigned",
    response: text(source.response, 8000),
    completedAt: maybeInstant(source.completed_at),
    visibility: oneOf(source.visibility, VISIBILITIES, "private"),
  };
}

export const exercisesLoader: LoaderEntry = {
  slices: ["exercises"],
  load: async (api) => {
    const body = await api.get("/mobile/exercises/", {
      parse: (raw) => list(raw, parseExercise),
    });
    return {
      exercises: body.filter(
        (item): item is ExerciseAssignment => item !== null,
      ),
    };
  },
};

// ── Pouca energia ───────────────────────────────────────────────────────────

export function parseLowEnergy(value: unknown): LowEnergyPlan {
  const source = record(value);
  return {
    actions: textList(source.actions, 3, 300),
    active: bool(source.active),
    startedAt: maybeInstant(source.started_at),
  };
}

export const lowEnergyLoader: LoaderEntry = {
  slices: ["lowEnergy"],
  load: async (api) => ({
    lowEnergy: await api.get("/mobile/low-energy/", { parse: parseLowEnergy }),
  }),
};

// ── Ações ───────────────────────────────────────────────────────────────────

export const careLoaders: readonly LoaderEntry[] = [
  medicationsLoader,
  carePlanLoader,
  routineLoader,
  exercisesLoader,
  lowEnergyLoader,
];

export const careActions: LiveActionRegistry = {
  logDose: {
    run: (input) => async (api) => {
      await api.put(`/mobile/medications/${input.medicationId}/doses/`, {
        scheduled_for: input.scheduledFor,
        status: input.status,
      });
      return { ok: true };
    },
    refresh: ["doseLogs"],
  },
  undoDose: {
    run: (input) => async (api) => {
      await api.put(`/mobile/medications/${input.medicationId}/doses/`, {
        scheduled_for: input.scheduledFor,
        status: "not_reported",
      });
      return { ok: true };
    },
    refresh: ["doseLogs"],
  },
  respondCarePlan: {
    run:
      (input, { snapshot }) =>
      async (api) => {
        const plan = snapshot?.carePlan;
        if (!plan) return { ok: false, reason: "invalid" };
        await api.post(`/mobile/care-plan/${plan.id}/response/`, {
          decision: input.decision,
          notes: input.notes.trim(),
        });
        return { ok: true };
      },
    refresh: ["carePlan"],
  },
  setHabitStatus: {
    run: (input) => async (api) => {
      const path = `/mobile/habits/${input.habitId}/checks/${input.date}/`;
      if (input.status === null) await api.delete(path);
      else await api.put(path, { status: input.status });
      return { ok: true };
    },
    refresh: ["habitChecks"],
  },
  completeExercise: {
    run: (input) => async (api) => {
      await api.post(`/mobile/exercises/${input.id}/complete/`, {
        response: input.response.trim(),
        visibility: input.visibility,
      });
      return { ok: true };
    },
    refresh: ["exercises"],
  },
  setLowEnergy: {
    run: (active) => async (api) => {
      await api.put("/mobile/low-energy/", { active });
      return { ok: true };
    },
    refresh: ["lowEnergy"],
  },
};
