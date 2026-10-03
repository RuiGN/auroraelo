/**
 * Diário no modo live: check-in, registros do diário, pedidos de acesso da equipe,
 * recuperação (meta, contador e vontade de usar) e metas
 * (api/mobile_diary_api.py, mobile_recovery_api.py e mobile_agenda_api.py → /goals/).
 */
import {
  bool,
  id,
  instant,
  int,
  intBetween,
  isoDate,
  list,
  maybeIsoDate,
  oneOf,
  record,
  text,
} from "../../api/parse";
import {
  CHECKIN_QUESTION_KEYS,
  CheckInScaleAnswers,
  CravingLog,
  DailyCheckIn,
  EMOTIONS,
  Emotion,
  Goal,
  GoalHorizon,
  GoalStatus,
  JournalAccessRequest,
  JournalEntry,
  Scale5,
  SobrietyGoal,
  Visibility,
} from "../../domain/types";
import type { LiveActionRegistry } from "./actions";
import type { LoaderEntry } from "./registry";

const VISIBILITIES: readonly Visibility[] = [
  "private",
  "shareable",
  "confirmation_required",
];
const GOAL_TYPES: readonly SobrietyGoal["goalType"][] = [
  "abstinence",
  "reduction",
  "moderation",
];
const HORIZONS: readonly GoalHorizon[] = ["short", "medium", "long"];
const GOAL_STATUSES: readonly GoalStatus[] = [
  "active",
  "paused",
  "completed",
  "archived",
];

function scale5(value: unknown): Scale5 {
  return intBetween(value, 1, 5) as Scale5;
}

// ── Check-in e diário ───────────────────────────────────────────────────────

/** Um check-in sem as sete respostas não é mostrado (o app sempre envia as sete). */
function parseCheckIn(value: unknown): DailyCheckIn | null {
  const source = record(value);
  const raw = record(source.answers);
  const answers: Partial<CheckInScaleAnswers> = {};
  for (const key of CHECKIN_QUESTION_KEYS) {
    const answer = raw[key];
    if (typeof answer !== "number") return null;
    answers[key] = scale5(answer);
  }
  return {
    id: id(source.id),
    date: isoDate(source.date),
    answers: answers as CheckInScaleAnswers,
    notes: text(source.notes, 4000),
    visibility: oneOf(source.visibility, VISIBILITIES, "private"),
    submittedAt: instant(source.submitted_at),
  };
}

function parseEntry(value: unknown): JournalEntry {
  const source = record(value);
  return {
    id: id(source.id),
    createdAt: instant(source.created_at),
    mood: scale5(source.mood),
    emotions: list(
      source.emotions,
      (entry) => oneOf<Emotion | "">(entry, EMOTIONS, ""),
      20,
    ).filter((entry): entry is Emotion => entry !== ""),
    intensity: scale5(source.intensity),
    context: text(source.context, 8000),
    triggers: text(source.triggers, 4000),
    reactions: text(source.reactions, 4000),
    strategies: text(source.strategies, 4000),
    visibility: oneOf(source.visibility, VISIBILITIES, "private"),
  };
}

export const diaryLoader: LoaderEntry = {
  slices: ["checkIns", "journal"],
  load: async (api) => {
    const body = await api.get("/mobile/diary/", { parse: record });
    return {
      checkIns: list(body.checkins, parseCheckIn, 1000).filter(
        (item): item is DailyCheckIn => item !== null,
      ),
      journal: list(body.entries, parseEntry, 2000),
    };
  },
};

function parseAccessRequest(value: unknown): JournalAccessRequest {
  const source = record(value);
  return {
    id: id(source.id),
    entryId: id(source.entry_id),
    entryCreatedAt: instant(source.entry_created_at),
    therapistName: text(source.therapist_name, 300),
    purpose: text(source.purpose, 1000),
    requestedAt: instant(source.requested_at),
  };
}

export const accessRequestsLoader: LoaderEntry = {
  slices: ["accessRequests"],
  load: async (api) => ({
    accessRequests: await api.get("/mobile/journal/access-requests/", {
      parse: (raw) => list(raw, parseAccessRequest, 200),
    }),
  }),
};

// ── Recuperação ─────────────────────────────────────────────────────────────

function parseSobriety(value: unknown): SobrietyGoal {
  const source = record(value);
  return {
    id: id(source.id),
    goalType: oneOf(source.goal_type, GOAL_TYPES, "abstinence"),
    focus: text(source.focus, 300),
    referenceDate: isoDate(source.reference_date),
    restartCount: int(source.restart_count),
    motivations: text(source.motivations, 4000),
    hideCounter: bool(source.hide_counter),
  };
}

/** Registro sem intensidade (feito antes da escala atual) não entra na lista. */
function parseCraving(value: unknown): CravingLog | null {
  const source = record(value);
  if (typeof source.intensity !== "number") return null;
  return {
    id: id(source.id),
    recordedAt: instant(source.recorded_at),
    intensity: intBetween(source.intensity, 0, 10),
    triggersContext: text(source.triggers_context, 4000),
    copingStrategyUsed: text(source.coping_strategy_used, 4000),
  };
}

export const recoveryLoader: LoaderEntry = {
  slices: ["sobriety", "cravings"],
  load: async (api) => {
    const body = await api.get("/mobile/recovery/", { parse: record });
    return {
      sobriety:
        body.sobriety === null || body.sobriety === undefined
          ? null
          : parseSobriety(body.sobriety),
      cravings: list(body.cravings, parseCraving, 1000).filter(
        (item): item is CravingLog => item !== null,
      ),
    };
  },
};

// ── Metas ───────────────────────────────────────────────────────────────────

function parseGoal(value: unknown): Goal {
  const source = record(value);
  return {
    id: id(source.id),
    title: text(source.title, 300),
    description: text(source.description, 4000),
    horizon: oneOf(source.horizon, HORIZONS, "short"),
    dueDate: maybeIsoDate(source.due_date),
    status: oneOf(source.status, GOAL_STATUSES, "active"),
    steps: list(source.steps, (entry) => {
      const step = record(entry);
      return {
        id: id(step.id),
        description: text(step.description, 1000),
        order: int(step.order),
        isDone: bool(step.is_done),
      };
    }),
  };
}

export const goalsLoader: LoaderEntry = {
  slices: ["goals"],
  load: async (api) => ({
    goals: await api.get("/mobile/goals/", {
      parse: (raw) => list(raw, parseGoal, 200),
    }),
  }),
};

export const diaryLoaders: readonly LoaderEntry[] = [
  diaryLoader,
  accessRequestsLoader,
  recoveryLoader,
  goalsLoader,
];

// ── Ações ───────────────────────────────────────────────────────────────────

/** O servidor só aceita estes estados de meta (arquivar é da equipe). */
const SETTABLE_GOAL_STATUS = ["active", "paused", "completed"] as const;

export const diaryActions: LiveActionRegistry = {
  submitCheckIn: {
    run: (input) => async (api) => {
      await api.post("/mobile/checkins/", {
        answers: input.answers,
        notes: input.notes.trim(),
        visibility: input.visibility,
      });
      return { ok: true };
    },
    refresh: ["checkIns"],
  },
  addJournalEntry: {
    run: (input) => async (api) => {
      await api.post("/mobile/journal/", {
        mood: input.mood,
        emotions: input.emotions,
        intensity: input.intensity,
        context: input.context.trim(),
        triggers: input.triggers.trim(),
        reactions: input.reactions.trim(),
        strategies: input.strategies.trim(),
        visibility: input.visibility,
      });
      return { ok: true };
    },
    refresh: ["journal"],
  },
  respondAccessRequest: {
    run: (input) => async (api) => {
      await api.post(`/mobile/journal/access-requests/${input.id}/respond/`, {
        approve: input.approve,
      });
      return { ok: true };
    },
    refresh: ["accessRequests"],
  },
  addCraving: {
    run: (input) => async (api) => {
      await api.post("/mobile/recovery/cravings/", {
        intensity: input.intensity,
        triggers_context: input.triggersContext.trim(),
        coping_strategy_used: input.copingStrategyUsed.trim(),
      });
      return { ok: true };
    },
    refresh: ["cravings"],
  },
  setCounterHidden: {
    run: (hidden) => async (api) => {
      await api.put("/mobile/recovery/counter/", { hidden });
      return { ok: true };
    },
    refresh: ["sobriety"],
  },
  restartCounter: {
    run: () => async (api) => {
      await api.post("/mobile/recovery/restart/");
      return { ok: true };
    },
    refresh: ["sobriety"],
  },
  toggleGoalStep: {
    run:
      (input, { snapshot }) =>
      async (api) => {
        const step = snapshot?.goals
          .find((goal) => goal.id === input.goalId)
          ?.steps.find((item) => item.id === input.stepId);
        if (!step) return { ok: false, reason: "invalid" };
        await api.put(`/mobile/goals/steps/${input.stepId}/`, {
          is_done: !step.isDone,
        });
        return { ok: true };
      },
    refresh: ["goals"],
  },
  setGoalStatus: {
    run: (input) => async (api) => {
      if (!(SETTABLE_GOAL_STATUS as readonly string[]).includes(input.status)) {
        return { ok: false, reason: "invalid" };
      }
      await api.put(`/mobile/goals/${input.goalId}/status/`, {
        status: input.status,
      });
      return { ok: true };
    },
    refresh: ["goals"],
  },
};
