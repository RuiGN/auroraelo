/**
 * Erros do cliente HTTP.
 *
 * Regras de segurança: nenhum token, corpo de resposta ou URL entra na mensagem do
 * erro nem em estado do app. O texto mostrado ao paciente é escolhido pelo `code`
 * (ver `src/i18n/errorCodes.ts`); `detail` vem do servidor só para diagnóstico.
 */

/** Códigos criados pelo próprio cliente (o servidor nunca os envia). */
export const CLIENT_CODES = {
  /** Nenhuma resposta HTTP: sem rede, DNS, TLS, conexão recusada. */
  network: "network",
  timeout: "timeout",
  /** Resposta que não é JSON, não segue o formato esperado ou foi redirecionada. */
  malformedResponse: "malformed_response",
  /** Endereço do servidor ausente ou inválido (não há requisição). */
  configuration: "configuration",
  /** Caminho de rota inválido (erro de programação; não há requisição). */
  invalidRequest: "invalid_request",
  /** Sem token, ou a renovação foi recusada: a sessão acabou. */
  sessionLost: "session_lost",
  /** A sessão mudou (saída ou novo login) enquanto a requisição estava em voo. */
  sessionChanged: "session_changed",
  /** HTTP 402: a clínica está com cobrança pendente. */
  clinicBlocked: "clinic_blocked",
  /** HTTP 429. */
  rateLimited: "rate_limited",
  /** HTTP 5xx. */
  serverError: "server_error",
} as const;

export interface ClinicRef {
  id: string;
  name: string;
}

export interface ApiErrorInit {
  detail?: string;
  clinics?: ClinicRef[];
  errors?: string[];
}

export class ApiError extends Error {
  /** Status HTTP; 0 quando não houve resposta. */
  readonly status: number;
  /**
   * `code` do corpo `{detail, code}` do servidor (por exemplo `invalid_credentials`),
   * ou um de `CLIENT_CODES`. 402 vira `clinic_blocked` e 429 vira `rate_limited`.
   */
  readonly code: string;
  /** Texto do servidor, só para diagnóstico: nunca mostrar ao paciente. */
  readonly detail?: string;
  /** 409 `clinic_choice_required`: clínicas entre as quais escolher. */
  readonly clinics?: ClinicRef[];
  /** 400/422 de senha: mensagens de validação do servidor (pt-BR). */
  readonly errors?: string[];

  constructor(status: number, code: string, init: ApiErrorInit = {}) {
    // A mensagem não leva corpo, URL nem token.
    super(`ApiError ${status} ${code}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    // `detail` é texto do servidor: não enumerável, para que `JSON.stringify`, spread
    // ou um log descuidado do erro não o levem junto.
    Object.defineProperty(this, "detail", {
      value: init.detail,
      enumerable: false,
    });
    this.clinics = init.clinics;
    this.errors = init.errors;
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** Sem resposta do servidor (rede ou tempo esgotado): a sessão continua valendo. */
export function isOfflineError(value: unknown): boolean {
  return (
    isApiError(value) &&
    (value.code === CLIENT_CODES.network || value.code === CLIENT_CODES.timeout)
  );
}

/** A sessão acabou (renovação recusada, token ausente ou sessão trocada). */
export function isSessionError(value: unknown): boolean {
  return (
    isApiError(value) &&
    (value.code === CLIENT_CODES.sessionLost ||
      value.code === CLIENT_CODES.sessionChanged)
  );
}
