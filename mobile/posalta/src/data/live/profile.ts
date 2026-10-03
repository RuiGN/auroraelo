/**
 * Perfil no modo live: consentimentos por documento vigente e pedidos do titular
 * (LGPD) — api/mobile_support_api.py.
 *
 * Cada documento vigente da clínica vira um `ConsentRecord`; o texto completo vem de
 * `GET /mobile/consents/{id}/` (poucos documentos: uma leitura por documento).
 */
import { ApiError } from "../../api/errors";
import { newRequestId } from "../../api/ids";
import {
  bool,
  id,
  instant,
  list,
  maybeInstant,
  maybeText,
  oneOf,
  record,
  text,
} from "../../api/parse";
import {
  ConsentRecord,
  PrivacyRequest,
  PrivacyRequestType,
} from "../../domain/types";
import type { LiveActionRegistry } from "./actions";
import type { LoaderEntry } from "./registry";

const REQUEST_TYPES: readonly PrivacyRequestType[] = [
  "confirmation",
  "access",
  "correction",
  "portability",
  "revocation",
  "erasure",
];
const REQUEST_STATUSES: readonly PrivacyRequest["status"][] = [
  "identity_pending",
  "in_review",
  "approved",
  "rejected",
  "processing",
  "completed",
];

/** Motivo gravado quando o paciente revoga pelo app (o servidor exige um texto). */
export const REVOCATION_REASON = "Revogado pelo paciente no aplicativo.";

function consentStatus(raw: unknown): ConsentRecord["status"] {
  if (raw === "accepted") return "granted";
  if (raw === "pending") return "pending";
  return "revoked"; // recusado, revogado ou qualquer outra decisão que não vale
}

export function parseConsent(value: unknown): ConsentRecord {
  const source = record(value);
  return {
    id: id(source.document_id),
    purpose: text(source.purpose, 100),
    title: text(source.title, 300),
    documentVersion: text(source.version, 64),
    status: consentStatus(source.status),
    decidedAt: maybeInstant(source.decided_at),
    mandatory: bool(source.mandatory),
    canRevoke: bool(source.can_revoke),
  };
}

export const consentsLoader: LoaderEntry = {
  slices: ["consents"],
  load: async (api) => {
    const rows = await api.get("/mobile/consents/", {
      parse: (raw) => list(raw, parseConsent, 50),
    });
    const detailed = await Promise.all(
      rows.map(async (row): Promise<ConsentRecord> => {
        const detail = await api.get(`/mobile/consents/${row.id}/`, {
          parse: record,
        });
        return {
          ...row,
          content: text(detail.content, 200_000),
          refusalConsequence: maybeText(detail.refusal_consequence, 4000) ?? "",
          alternativeInstructions:
            maybeText(detail.alternative_instructions, 4000) ?? "",
          clinicContact:
            maybeText(detail.clinic_contact_instructions, 4000) ?? "",
        };
      }),
    );
    return { consents: detailed };
  },
};

export function parsePrivacyRequest(value: unknown): PrivacyRequest {
  const source = record(value);
  return {
    id: id(source.id),
    type: oneOf(source.type, REQUEST_TYPES, "access"),
    requestedAt: instant(source.requested_at),
    status: oneOf(source.status, REQUEST_STATUSES, "identity_pending"),
  };
}

export const privacyRequestsLoader: LoaderEntry = {
  slices: ["privacyRequests"],
  load: async (api) => ({
    privacyRequests: await api.get("/mobile/privacy-requests/", {
      parse: (raw) => list(raw, parsePrivacyRequest, 200),
    }),
  }),
};

export const profileLoaders: readonly LoaderEntry[] = [
  consentsLoader,
  privacyRequestsLoader,
];

export const profileActions: LiveActionRegistry = {
  setConsent: {
    run: (input) => async (api) => {
      if (input.granted) {
        await api.post(`/mobile/consents/${input.id}/decision/`, {
          decision: "accepted",
          request_id: newRequestId(),
        });
      } else {
        await api.post(`/mobile/consents/${input.id}/revoke/`, {
          reason: REVOCATION_REASON,
          request_id: newRequestId(),
        });
      }
      return { ok: true };
    },
    refresh: ["consents"],
  },
  createPrivacyRequest: {
    run: (type) => async (api) => {
      try {
        await api.post("/mobile/privacy-requests/", { type });
      } catch (error) {
        // Já existe um pedido aberto deste tipo: a tela explica (não é falha de rede).
        if (error instanceof ApiError && error.code === "already_open") {
          return { ok: false, reason: "invalid", code: "already_open" };
        }
        throw error;
      }
      return { ok: true };
    },
    refresh: ["privacyRequests"],
  },
};
