/**
 * Texto por `code` de erro da API. O servidor manda `{ detail, code }`: `detail` é só
 * diagnóstico (pt-BR) e nunca é mostrado; o app escolhe a mensagem pelo `code`, nos
 * três idiomas (chaves `error.code.*`). Código desconhecido cai em `error.code.unknown`.
 */
import type { AuthFailureReason } from "../api/session";
import type { TranslationKey } from "./index";

export const ERROR_CODE_KEYS = {
  // Cliente
  network: "error.code.network",
  timeout: "error.code.network",
  clinic_blocked: "error.code.clinic_blocked",
  rate_limited: "error.code.rate_limited",
  // Contrato do servidor (docs/mobile-patient-api.md)
  invalid_credentials: "error.code.invalid_credentials",
  clinic_choice_required: "error.code.clinic_choice_required",
  invalid_token: "error.code.invalid_token",
  not_found: "error.code.not_found",
  invalid_dose_time: "error.code.invalid_dose_time",
  timezone_required: "error.code.timezone_required",
  plan_closed: "error.code.plan_closed",
  invalid_date: "error.code.invalid_date",
  not_scheduled: "error.code.not_scheduled",
  already_completed: "error.code.already_completed",
  invalid_response: "error.code.invalid_response",
  unsupported: "error.code.unsupported",
  no_actions_configured: "error.code.no_actions_configured",
  invalid_intensity: "error.code.invalid_intensity",
  invalid_scope: "error.code.invalid_scope",
  reauthentication_failed: "error.code.reauthentication_failed",
  consent_rejected: "error.code.consent_rejected",
  revocation_rejected: "error.code.revocation_rejected",
  already_open: "error.code.already_open",
  rejected: "error.code.rejected",
  slot_unavailable: "error.code.slot_unavailable",
  weak_password: "error.code.weak_password",
  invalid_code: "error.code.invalid_code",
  invalid_contact: "error.code.invalid_contact",
  invalid_focus: "error.code.invalid_focus",
  invalid_phone: "error.code.invalid_phone",
  invalid_section_type: "error.code.invalid_section_type",
  already_exists: "error.code.already_exists",
  limit_reached: "error.code.limit_reached",
} as const satisfies Record<string, TranslationKey>;

/** Chave do texto para um `code`, ou `null` quando ele não tem mensagem própria. */
export function errorCodeKey(code: string | undefined): TranslationKey | null {
  if (code === undefined) return null;
  return Object.prototype.hasOwnProperty.call(ERROR_CODE_KEYS, code)
    ? ERROR_CODE_KEYS[code as keyof typeof ERROR_CODE_KEYS]
    : null;
}

/** Como `errorCodeKey`, com o texto genérico para códigos desconhecidos. */
export function errorMessageKey(code: string | undefined): TranslationKey {
  return errorCodeKey(code) ?? "error.code.unknown";
}

/** Texto de um motivo de falha de entrada/saída (`AuthResult`). */
export function authFailureKey(reason: AuthFailureReason): TranslationKey {
  switch (reason) {
    case "invalid_credentials":
      return "error.code.invalid_credentials";
    case "rate_limited":
      return "error.code.rate_limited";
    case "offline":
      return "error.code.network";
    case "invalid_code":
      return "error.code.invalid_code";
    case "weak_password":
      return "error.code.weak_password";
    case "clinic_choice":
      return "error.code.clinic_choice_required";
    case "blocked":
      return "error.code.clinic_blocked";
    default:
      return "error.code.unknown";
  }
}
