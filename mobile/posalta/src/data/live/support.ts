/**
 * Apoio no modo live: rede de apoio, plano de apoio urgente, plano de prevenção de
 * recaída e conteúdos (api/mobile_support_api.py e mobile_recovery_api.py).
 */
import {
  id,
  instant,
  int,
  list,
  maybeInstant,
  maybeText,
  oneOf,
  record,
  text,
  textList,
} from "../../api/parse";
import {
  ContentItem,
  ContentKind,
  RelapsePlan,
  RelapseSectionType,
  SupportRelationship,
  SupportScope,
  UrgentPlan,
} from "../../domain/types";
import type { LiveActionRegistry } from "./actions";
import type { LoaderEntry } from "./registry";

const SCOPES: readonly SupportScope[] = [
  "view_wellness_summary",
  "receive_urgent_alerts",
  "view_relapse_plan_safe",
  "receive_checkin_summary",
];
const CONTENT_KINDS: readonly ContentKind[] = [
  "article",
  "video",
  "audio",
  "exercise",
];
export const RELAPSE_SECTION_TYPES: readonly RelapseSectionType[] = [
  "triggers",
  "early_warning_signs",
  "protective_factors",
  "coping_strategies",
  "safe_environments",
  "support_contacts",
  "professional_resources",
];

// ── Rede de apoio ───────────────────────────────────────────────────────────

export const supportNetworkLoader: LoaderEntry = {
  slices: ["supportNetwork"],
  load: async (api) => {
    const body = await api.get("/mobile/support-network/", { parse: record });
    return {
      supportNetwork: list(
        body.supporters,
        (entry): SupportRelationship => {
          const source = record(entry);
          return {
            id: id(source.id),
            name: text(source.name, 300),
            relationship: text(source.relationship_type, 300),
            scopes: list(
              source.scopes,
              (scope) => oneOf<SupportScope | "">(scope, SCOPES, ""),
              20,
            ).filter((scope): scope is SupportScope => scope !== ""),
            // O servidor só lista quem está ativo.
            active: true,
          };
        },
        200,
      ),
    };
  },
};

// ── Plano de apoio urgente (vem junto da Ajuda) ─────────────────────────────

function parseUrgentPlan(value: unknown): UrgentPlan {
  const source = record(value);
  return {
    personalInstructions: text(source.personal_instructions, 4000),
    calmingStrategies: textList(source.calming_strategies, 20, 500),
    contacts: list(
      source.contacts,
      (entry) => {
        const contact = record(entry);
        return {
          id: id(contact.id),
          name: text(contact.name, 300),
          relationship: text(contact.relationship, 300),
          phone: text(contact.phone, 40),
          messageTemplate: text(contact.message_template, 1000),
        };
      },
      20,
    ),
    lastReviewedAt: instant(source.last_reviewed_at),
  };
}

export const urgentPlanLoader: LoaderEntry = {
  slices: ["urgentPlan"],
  load: async (api) => {
    const body = await api.get("/mobile/help/", { parse: record });
    return {
      urgentPlan:
        body.urgent_plan === null || body.urgent_plan === undefined
          ? null
          : parseUrgentPlan(body.urgent_plan),
    };
  },
};

// ── Plano de prevenção de recaída ───────────────────────────────────────────

export function parseRelapsePlan(value: unknown): RelapsePlan {
  const source = record(value);
  return {
    id: id(source.id),
    title: text(source.title, 300),
    version: int(source.version),
    lastReviewedAt: maybeInstant(source.last_reviewed_at),
    sections: list(source.sections, (entry) => {
      const section = record(entry);
      return {
        id: id(section.id),
        type: oneOf(section.type, RELAPSE_SECTION_TYPES, "coping_strategies"),
        title: text(section.title, 300),
        content: text(section.content, 8000),
      };
    }),
  };
}

export const relapsePlanLoader: LoaderEntry = {
  slices: ["relapsePlan"],
  load: async (api) => {
    const body = await api.get("/mobile/relapse-plan/", { parse: record });
    return {
      relapsePlan:
        body.relapse_plan === null || body.relapse_plan === undefined
          ? null
          : parseRelapsePlan(body.relapse_plan),
    };
  },
};

// ── Conteúdos ───────────────────────────────────────────────────────────────

/** Leitura em ~200 palavras por minuto, no mínimo 1 minuto. */
export function estimateMinutes(body: string): number {
  const words = body.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 200));
}

function parseContent(value: unknown): ContentItem {
  const source = record(value);
  const body = text(source.body, 200_000);
  return {
    id: id(source.id),
    title: text(source.title, 300),
    kind: oneOf(source.kind, CONTENT_KINDS, "article"),
    category: text(source.category, 300),
    body,
    contraindications: text(source.contraindications, 4000),
    sourceReference: text(source.source_reference, 1000),
    recommendedByName: maybeText(source.recommended_by_name, 300),
    recommendationObjective: maybeText(source.recommendation_objective, 1000),
    estimatedMinutes: estimateMinutes(body),
    // Favorito e "lido" não existem no servidor.
    favorite: false,
    read: false,
  };
}

export const contentLoader: LoaderEntry = {
  slices: ["content"],
  load: async (api) => ({
    content: await api.get("/mobile/content/", {
      parse: (raw) => list(raw, parseContent, 100),
    }),
  }),
};

export const supportLoaders: readonly LoaderEntry[] = [
  supportNetworkLoader,
  urgentPlanLoader,
  relapsePlanLoader,
  contentLoader,
];

// ── Ações ───────────────────────────────────────────────────────────────────

export const supportActions: LiveActionRegistry = {
  toggleSupportScope: {
    run:
      (input, { snapshot }) =>
      async (api) => {
        const person = snapshot?.supportNetwork.find(
          (item) => item.id === input.id,
        );
        // Mudar o que a rede vê exige a senha (reautenticação no servidor).
        if (!person || !input.password) return { ok: false, reason: "invalid" };
        const scopes = person.scopes.includes(input.scope)
          ? person.scopes.filter((scope) => scope !== input.scope)
          : [...person.scopes, input.scope];
        await api.put(`/mobile/support-network/${input.id}/scopes/`, {
          scopes,
          password: input.password,
        });
        return { ok: true };
      },
    refresh: ["supportNetwork"],
  },
  revokeSupport: {
    run: (relationshipId) => async (api) => {
      await api.delete(`/mobile/support-network/${relationshipId}/`);
      return { ok: true };
    },
    refresh: ["supportNetwork"],
  },
};
