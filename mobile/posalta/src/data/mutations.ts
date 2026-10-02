import { toISODate } from "../domain/logic";
import {
  CarePlanDecision,
  CheckInScaleAnswers,
  ConsentPurposeKey,
  DoseStatus,
  Emotion,
  GoalStatus,
  HabitStatus,
  ISODateTime,
  PrivacyRequestType,
  Scale5,
  Snapshot,
  SupportScope,
  Visibility,
} from "../domain/types";

/**
 * Transformações puras do instantâneo — aplicadas SOMENTE no modo demonstração, onde
 * o estado vive na memória do app e some ao fechá-lo. Retornam `null` quando a
 * entrada é inválida. Nada aqui é enviado a servidor nem gravado no aparelho.
 *
 * No modo live a mesma chamada (`store.run(mutations.logDose(input))`) não executa a
 * função: o store lê `meta` ({ key, input }) e procura a ação remota registrada em
 * `src/data/live/actions.ts` para essa `key`. Assim as telas têm um único caminho de
 * escrita e cada domínio liga a sua API sem mexer nelas.
 */
export interface MutationMeta<K extends string = string, I = unknown> {
  readonly key: K;
  /** Primeiro argumento da fábrica (`undefined` quando ela não recebe nada). */
  readonly input: I;
}

export interface Mutation {
  (snapshot: Snapshot, now: Date): Snapshot | null;
  /** Presente nas mutações criadas por `defineMutations`. */
  readonly meta?: MutationMeta;
}

type Factory = (...args: never[]) => Mutation;

type InputOf<F> = F extends (...args: infer A) => unknown
  ? A extends [infer I, ...unknown[]]
    ? I
    : undefined
  : never;

/** Mutação com os metadados garantidos. */
export type TaggedMutation<K extends string, I> = Mutation & {
  readonly meta: MutationMeta<K, I>;
};

/**
 * Registra as fábricas e devolve as mesmas funções com o mesmo comportamento puro,
 * mas cada mutação criada carrega `meta = { key, input }`.
 */
export type DefinedMutations<T extends Record<string, Factory>> = {
  [K in keyof T & string]: (
    ...args: Parameters<T[K]>
  ) => TaggedMutation<K, InputOf<T[K]>>;
};

export function defineMutations<T extends Record<string, Factory>>(
  factories: T,
): DefinedMutations<T> {
  const tagged: Record<string, (...args: never[]) => Mutation> = {};
  for (const [key, factory] of Object.entries(factories)) {
    tagged[key] = (...args: never[]) => {
      const pure = factory(...args);
      const mutation: Mutation = (snapshot, now) => pure(snapshot, now);
      return Object.defineProperty(mutation, "meta", {
        value: Object.freeze({ key, input: args[0] }),
        enumerable: true,
      });
    };
  }
  return tagged as unknown as DefinedMutations<T>;
}

export const MAX_TEXT = 4000;
export const MAX_DETAIL = 2000;

let counter = 0;
function newId(prefix: string, now: Date): string {
  counter += 1;
  return `${prefix}-${now.getTime().toString(36)}-${counter}`;
}

function blank(value: string): boolean {
  return value.trim().length === 0;
}

export const mutations = defineMutations({
  submitCheckIn:
    (input: {
      answers: CheckInScaleAnswers;
      notes: string;
      visibility: Visibility;
    }): Mutation =>
    (snapshot, now) => {
      if (input.notes.length > MAX_DETAIL) return null;
      const date = toISODate(now);
      const entry = {
        id: newId("ci", now),
        date,
        answers: input.answers,
        notes: input.notes.trim(),
        visibility: input.visibility,
        submittedAt: now.toISOString(),
      };
      // Um check-in por dia: o envio do mesmo dia substitui o anterior (idempotente).
      return {
        ...snapshot,
        checkIns: [
          entry,
          ...snapshot.checkIns.filter((item) => item.date !== date),
        ],
      };
    },

  addJournalEntry:
    (input: {
      mood: Scale5;
      emotions: Emotion[];
      intensity: Scale5;
      context: string;
      triggers: string;
      reactions: string;
      strategies: string;
      visibility: Visibility;
    }): Mutation =>
    (snapshot, now) => {
      if (blank(input.context) || input.context.length > MAX_TEXT) return null;
      for (const field of [input.triggers, input.reactions, input.strategies]) {
        if (field.length > MAX_DETAIL) return null;
      }
      const entry = {
        id: newId("j", now),
        createdAt: now.toISOString(),
        mood: input.mood,
        emotions: input.emotions,
        intensity: input.intensity,
        context: input.context.trim(),
        triggers: input.triggers.trim(),
        reactions: input.reactions.trim(),
        strategies: input.strategies.trim(),
        visibility: input.visibility,
      };
      return { ...snapshot, journal: [entry, ...snapshot.journal] };
    },

  logDose:
    (input: {
      medicationId: string;
      scheduledFor: ISODateTime;
      status: DoseStatus;
    }): Mutation =>
    (snapshot, now) => {
      if (!snapshot.medications.some((item) => item.id === input.medicationId))
        return null;
      const others = snapshot.doseLogs.filter(
        (log) =>
          !(
            log.medicationId === input.medicationId &&
            log.scheduledFor === input.scheduledFor
          ),
      );
      return {
        ...snapshot,
        doseLogs: [
          ...others,
          {
            id: newId("d", now),
            medicationId: input.medicationId,
            scheduledFor: input.scheduledFor,
            status: input.status,
            recordedAt: now.toISOString(),
          },
        ],
      };
    },

  undoDose:
    (input: { medicationId: string; scheduledFor: ISODateTime }): Mutation =>
    (snapshot) => ({
      ...snapshot,
      doseLogs: snapshot.doseLogs.filter(
        (log) =>
          !(
            log.medicationId === input.medicationId &&
            log.scheduledFor === input.scheduledFor
          ),
      ),
    }),

  respondCarePlan:
    (input: { decision: CarePlanDecision; notes: string }): Mutation =>
    (snapshot, now) => {
      if (!snapshot.carePlan || input.notes.length > MAX_DETAIL) return null;
      return {
        ...snapshot,
        carePlan: {
          ...snapshot.carePlan,
          response: {
            decision: input.decision,
            notes: input.notes.trim(),
            respondedAt: now.toISOString(),
          },
        },
      };
    },

  setHabitStatus:
    (input: {
      habitId: string;
      date: string;
      status: HabitStatus | null;
    }): Mutation =>
    (snapshot) => {
      if (!snapshot.habits.some((habit) => habit.id === input.habitId))
        return null;
      const others = snapshot.habitChecks.filter(
        (check) =>
          !(check.habitId === input.habitId && check.date === input.date),
      );
      return {
        ...snapshot,
        habitChecks: input.status
          ? [
              ...others,
              {
                habitId: input.habitId,
                date: input.date,
                status: input.status,
              },
            ]
          : others,
      };
    },

  completeExercise:
    (input: {
      id: string;
      response: string;
      visibility: Visibility;
    }): Mutation =>
    (snapshot, now) => {
      const target = snapshot.exercises.find((item) => item.id === input.id);
      if (!target || blank(input.response) || input.response.length > MAX_TEXT)
        return null;
      return {
        ...snapshot,
        exercises: snapshot.exercises.map((item) =>
          item.id === input.id
            ? {
                ...item,
                status: "completed" as const,
                response: input.response.trim(),
                completedAt: now.toISOString(),
                visibility: input.visibility,
              }
            : item,
        ),
      };
    },

  toggleGoalStep:
    (input: { goalId: string; stepId: string }): Mutation =>
    (snapshot) => {
      const goal = snapshot.goals.find((item) => item.id === input.goalId);
      if (!goal || !goal.steps.some((step) => step.id === input.stepId))
        return null;
      return {
        ...snapshot,
        goals: snapshot.goals.map((item) =>
          item.id === input.goalId
            ? {
                ...item,
                steps: item.steps.map((step) =>
                  step.id === input.stepId
                    ? { ...step, isDone: !step.isDone }
                    : step,
                ),
              }
            : item,
        ),
      };
    },

  setGoalStatus:
    (input: { goalId: string; status: GoalStatus }): Mutation =>
    (snapshot) => {
      if (!snapshot.goals.some((item) => item.id === input.goalId)) return null;
      return {
        ...snapshot,
        goals: snapshot.goals.map((item) =>
          item.id === input.goalId ? { ...item, status: input.status } : item,
        ),
      };
    },

  addCraving:
    (input: {
      intensity: number;
      triggersContext: string;
      copingStrategyUsed: string;
    }): Mutation =>
    (snapshot, now) => {
      if (
        !Number.isInteger(input.intensity) ||
        input.intensity < 0 ||
        input.intensity > 10
      ) {
        return null;
      }
      if (
        input.triggersContext.length > MAX_DETAIL ||
        input.copingStrategyUsed.length > MAX_DETAIL
      ) {
        return null;
      }
      return {
        ...snapshot,
        cravings: [
          {
            id: newId("cr", now),
            recordedAt: now.toISOString(),
            intensity: input.intensity,
            triggersContext: input.triggersContext.trim(),
            copingStrategyUsed: input.copingStrategyUsed.trim(),
          },
          ...snapshot.cravings,
        ],
      };
    },

  setCounterHidden:
    (hidden: boolean): Mutation =>
    (snapshot) =>
      snapshot.sobriety
        ? {
            ...snapshot,
            sobriety: { ...snapshot.sobriety, hideCounter: hidden },
          }
        : null,

  restartCounter: (): Mutation => (snapshot, now) =>
    snapshot.sobriety
      ? {
          ...snapshot,
          sobriety: {
            ...snapshot.sobriety,
            referenceDate: toISODate(now),
            restartCount: snapshot.sobriety.restartCount + 1,
          },
        }
      : null,

  setLowEnergy:
    (active: boolean): Mutation =>
    (snapshot, now) => ({
      ...snapshot,
      lowEnergy: {
        ...snapshot.lowEnergy,
        active,
        startedAt: active ? now.toISOString() : null,
      },
    }),

  requestAppointment:
    (input: { serviceId: string; slot: ISODateTime }): Mutation =>
    (snapshot, now) => {
      const service = snapshot.services.find(
        (item) => item.id === input.serviceId,
      );
      if (!service || !service.freeSlots.includes(input.slot)) return null;
      const start = new Date(input.slot);
      const end = new Date(start.getTime() + service.durationMinutes * 60_000);
      return {
        ...snapshot,
        appointments: [
          ...snapshot.appointments,
          {
            id: newId("a", now),
            serviceName: service.name,
            professionalName: service.professionalName,
            unitName: service.unitName,
            startAt: start.toISOString(),
            endAt: end.toISOString(),
            status: "requested",
            cancelReason: "",
          },
        ],
        // O horário solicitado deixa de aparecer como livre.
        services: snapshot.services.map((item) =>
          item.id === service.id
            ? {
                ...item,
                freeSlots: item.freeSlots.filter((slot) => slot !== input.slot),
              }
            : item,
        ),
      };
    },

  cancelAppointment:
    (input: { id: string; reason: string }): Mutation =>
    (snapshot) => {
      const target = snapshot.appointments.find((item) => item.id === input.id);
      if (
        !target ||
        target.status === "canceled" ||
        target.status === "completed"
      )
        return null;
      if (input.reason.length > 255) return null;
      return {
        ...snapshot,
        appointments: snapshot.appointments.map((item) =>
          item.id === input.id
            ? {
                ...item,
                status: "canceled" as const,
                cancelReason: input.reason.trim(),
              }
            : item,
        ),
      };
    },

  requestReschedule:
    (input: { id: string }): Mutation =>
    (snapshot) => {
      const target = snapshot.appointments.find((item) => item.id === input.id);
      if (
        !target ||
        (target.status !== "confirmed" && target.status !== "requested")
      )
        return null;
      return {
        ...snapshot,
        appointments: snapshot.appointments.map((item) =>
          item.id === input.id
            ? { ...item, status: "reschedule_requested" as const }
            : item,
        ),
      };
    },

  toggleSupportScope:
    (input: { id: string; scope: SupportScope }): Mutation =>
    (snapshot) => {
      if (!snapshot.supportNetwork.some((item) => item.id === input.id))
        return null;
      return {
        ...snapshot,
        supportNetwork: snapshot.supportNetwork.map((item) =>
          item.id === input.id
            ? {
                ...item,
                scopes: item.scopes.includes(input.scope)
                  ? item.scopes.filter((scope) => scope !== input.scope)
                  : [...item.scopes, input.scope],
              }
            : item,
        ),
      };
    },

  revokeSupport:
    (id: string): Mutation =>
    (snapshot) => {
      if (!snapshot.supportNetwork.some((item) => item.id === id)) return null;
      return {
        ...snapshot,
        supportNetwork: snapshot.supportNetwork.map((item) =>
          item.id === id ? { ...item, active: false, scopes: [] } : item,
        ),
      };
    },

  toggleContent:
    (input: { id: string; flag: "favorite" | "read" }): Mutation =>
    (snapshot) => {
      if (!snapshot.content.some((item) => item.id === input.id)) return null;
      return {
        ...snapshot,
        content: snapshot.content.map((item) =>
          item.id === input.id
            ? { ...item, [input.flag]: !item[input.flag] }
            : item,
        ),
      };
    },

  setConsent:
    (input: { purpose: ConsentPurposeKey; granted: boolean }): Mutation =>
    (snapshot, now) => {
      const current = snapshot.consents.find(
        (item) => item.purpose === input.purpose,
      );
      if (!current) return null;
      // Consentimentos obrigatórios não podem ser revogados por aqui: a revogação
      // exige o fluxo de solicitação ao titular (LGPD) e encerra o uso do serviço.
      if (current.mandatory && !input.granted) return null;
      return {
        ...snapshot,
        consents: snapshot.consents.map((item) =>
          item.purpose === input.purpose
            ? {
                ...item,
                status: input.granted
                  ? ("granted" as const)
                  : ("revoked" as const),
                decidedAt: now.toISOString(),
              }
            : item,
        ),
      };
    },

  createPrivacyRequest:
    (type: PrivacyRequestType): Mutation =>
    (snapshot, now) => {
      const open = snapshot.privacyRequests.some(
        (item) => item.type === type && item.status !== "completed",
      );
      if (open) return null;
      return {
        ...snapshot,
        privacyRequests: [
          {
            id: newId("pr", now),
            type,
            requestedAt: now.toISOString(),
            status: "identity_pending",
          },
          ...snapshot.privacyRequests,
        ],
      };
    },
});

/** Nome de cada mutação: é a chave do registro de ações remotas. */
export type MutationKey = keyof typeof mutations;

/** Tipo da entrada de uma mutação (o argumento da fábrica). */
export type MutationInput<K extends MutationKey> = ReturnType<
  (typeof mutations)[K]
>["meta"]["input"];
