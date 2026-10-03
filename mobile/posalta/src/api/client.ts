/**
 * Cliente HTTP JSON da API do paciente (`/api/v1/mobile/`).
 *
 * Garantias (todas cobertas em tests/api-client.test.ts):
 * - `Authorization: Bearer` só vai para a origem configurada: o cliente monta a URL
 *   sozinho (origem validada + `/api/v1` + caminho restrito) e recusa qualquer outro
 *   formato de caminho antes de abrir a rede.
 * - Tempo limite de 15 s (AbortController), `redirect: "error"`, `credentials:
 *   "omit"`, `Accept: application/json`; a resposta precisa ser `application/json`.
 * - 401 em rota autenticada → UMA renovação por vez (as chamadas simultâneas
 *   aguardam a mesma promessa: o servidor revoga a sessão inteira se o mesmo token
 *   de renovação for reapresentado) e a requisição original é repetida UMA vez.
 *   Renovação recusada (401/403) ou token ausente → sessão perdida: apaga os tokens
 *   e avisa os ouvintes. Rede/tempo esgotado NÃO derrubam a sessão.
 * - 402 → `clinic_blocked`; 429 → `rate_limited`; 409 `clinic_choice_required` traz
 *   `clinics`; 400/422 trazem `errors`.
 * - Nenhum token, corpo ou URL vai para log, mensagem de erro ou estado: este módulo
 *   não escreve em console.
 */
import { IS_DEV, resolveApiBaseUrl } from "../config";
import { ApiError, ClinicRef, CLIENT_CODES } from "./errors";
import { isRecord, malformed, Parser } from "./parse";
import { createMemoryTokenStore, TokenStore } from "./tokenStore";
import {
  parseClinicRef,
  parseTokens,
  SessionInfo,
  sessionInfo,
  StoredSession,
} from "./types";

export const API_PREFIX = "/api/v1";
export const DEFAULT_TIMEOUT_MS = 15_000;

/** Transporte injetável (padrão: `fetch` global); mesma assinatura do `fetch`. */
export type Transport = (
  input: string,
  init: RequestInit,
) => Promise<TransportResponse>;

/** Parte da `Response` que o cliente usa (facilita fakes nos testes). */
export interface TransportResponse {
  status: number;
  url?: string;
  headers: { get(name: string): string | null };
  json(): Promise<unknown>;
}

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions<T = unknown> {
  /** Parâmetros de consulta; `undefined`/`null` são omitidos. */
  query?: Record<string, QueryValue>;
  /** Valida o corpo; erros viram `malformed_response`. Passe sempre que tipar o retorno. */
  parse?: Parser<T>;
  /** `false` em rotas públicas (entrar, ativar, recuperar): sem token e sem renovação. */
  auth?: boolean;
  timeoutMs?: number;
}

/** O que loaders e ações de domínio enxergam: só chamadas HTTP, nunca os tokens. */
export interface Api {
  get<T = unknown>(path: string, options?: RequestOptions<T>): Promise<T>;
  post<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions<T>,
  ): Promise<T>;
  put<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions<T>,
  ): Promise<T>;
  delete<T = unknown>(path: string, options?: RequestOptions<T>): Promise<T>;
}

export interface ApiClient extends Api {
  /** Há um endereço de servidor válido. */
  readonly configured: boolean;
  /** Lê a sessão do cofre (sem rede) e a adota. `null` se não houver. */
  restore(): Promise<SessionInfo | null>;
  /** Adota uma sessão nova (login/ativação) e a grava no cofre. */
  setSession(session: StoredSession): Promise<void>;
  /** Apaga a sessão da memória e do cofre. Idempotente. */
  clearSession(): Promise<void>;
  /** Dados não sensíveis da sessão atual. */
  currentSession(): SessionInfo | null;
  /** Ouve a perda de sessão (renovação recusada ou token ausente). */
  onSessionLost(listener: () => void): () => void;
}

export interface ApiClientOptions {
  /** Origem do servidor já validada por `resolveApiBaseUrl`; `null` = sem configuração. */
  baseUrl: string | null;
  tokenStore?: TokenStore;
  transport?: Transport;
  timeoutMs?: number;
  /** Permite `http` em localhost/emulador (padrão: `__DEV__`). */
  dev?: boolean;
}

// Cada segmento: letras, dígitos, "_" e "-" (UUID, datas, nomes de rota). Começa e
// termina com "/" (o Django exige a barra final e perderia o corpo num redirect).
const PATH = /^\/(?:[A-Za-z0-9_-]+\/)+$/;

function buildQuery(query: RequestOptions["query"]): string {
  if (!query) return "";
  const parts: string[] = [];
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    parts.push(
      `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
    );
  }
  return parts.length > 0 ? `?${parts.join("&")}` : "";
}

const defaultTransport: Transport = (input, init) =>
  globalThis.fetch(input, init) as Promise<TransportResponse>;

interface RawResponse {
  status: number;
  /** Corpo JSON lido, quando houver. */
  body: unknown;
  /** O corpo veio como JSON válido. */
  json: boolean;
}

function readErrors(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const lines = value
    .filter((item): item is string => typeof item === "string")
    .slice(0, 10)
    .map((item) => item.slice(0, 300));
  return lines.length > 0 ? lines : undefined;
}

function readClinics(value: unknown): ClinicRef[] | undefined {
  if (!Array.isArray(value) || value.length > 50) return undefined;
  try {
    return value.map((item) => parseClinicRef(item));
  } catch {
    return undefined;
  }
}

/** Converte uma resposta de erro HTTP em `ApiError`, sem copiar o corpo. */
function toApiError(raw: RawResponse): ApiError {
  const body = raw.json && isRecord(raw.body) ? raw.body : {};
  const bodyCode =
    typeof body.code === "string" && /^[a-z0-9_]{1,64}$/.test(body.code)
      ? body.code
      : undefined;
  const detail =
    typeof body.detail === "string" ? body.detail.slice(0, 200) : undefined;
  const { status } = raw;
  let code: string;
  if (status === 402) code = CLIENT_CODES.clinicBlocked;
  else if (status === 429) code = CLIENT_CODES.rateLimited;
  else if (status >= 500) code = CLIENT_CODES.serverError;
  else code = bodyCode ?? `http_${status}`;
  return new ApiError(status, code, {
    detail,
    clinics:
      status === 409 && code === "clinic_choice_required"
        ? readClinics(body.clinics)
        : undefined,
    errors:
      status === 400 || status === 422 ? readErrors(body.errors) : undefined,
  });
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const base = resolveApiBaseUrl(options.baseUrl, options.dev ?? IS_DEV);
  const transport = options.transport ?? defaultTransport;
  const tokenStore = options.tokenStore ?? createMemoryTokenStore();
  const defaultTimeout = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  let current: StoredSession | null = null;
  /** Muda a cada troca de sessão (login/saída), nunca na rotação de tokens. */
  let epoch = 0;
  let refreshing: { epoch: number; promise: Promise<void> } | null = null;
  const lostListeners = new Set<() => void>();

  function urlFor(path: string, query?: RequestOptions["query"]): string {
    if (base === null) throw new ApiError(0, CLIENT_CODES.configuration);
    if (!PATH.test(path)) throw new ApiError(0, CLIENT_CODES.invalidRequest);
    return `${base}${API_PREFIX}${path}${buildQuery(query)}`;
  }

  /** Uma ida ao servidor, já com o corpo JSON lido dentro do tempo limite. */
  async function exchange(
    method: string,
    url: string,
    body: unknown,
    accessToken: string | null,
    timeoutMs: number,
  ): Promise<RawResponse> {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    try {
      const headers: Record<string, string> = { Accept: "application/json" };
      if (body !== undefined) headers["Content-Type"] = "application/json";
      if (accessToken !== null) headers.Authorization = `Bearer ${accessToken}`;
      const response = await transport(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "omit",
        redirect: "error",
        signal: controller.signal,
      });
      // O React Native pode seguir redirecionamentos mesmo com `redirect: "error"`:
      // uma resposta de outra URL é descartada sem ler o corpo. A consulta fica de
      // fora da comparação (o sistema pode reescrever a codificação dela).
      if (response.url && response.url.split("?")[0] !== url.split("?")[0]) {
        malformed();
      }
      const { status } = response;
      if (status === 204) return { status, body: undefined, json: false };
      const isJson = (response.headers.get("content-type") ?? "")
        .toLowerCase()
        .includes("application/json");
      if (!isJson) return { status, body: undefined, json: false };
      try {
        return { status, body: await response.json(), json: true };
      } catch (error) {
        if (timedOut) throw error;
        return { status, body: undefined, json: false };
      }
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(
        0,
        timedOut ? CLIENT_CODES.timeout : CLIENT_CODES.network,
      );
    } finally {
      clearTimeout(timer);
    }
  }

  async function persist(session: StoredSession): Promise<void> {
    try {
      await tokenStore.save(session);
    } catch {
      // Sem cofre a sessão vale só até o app fechar; nada é logado.
    }
  }

  /** Apaga a sessão e, se for o caso, avisa que ela foi perdida. */
  async function dropSession(atEpoch: number, notify: boolean): Promise<void> {
    if (epoch !== atEpoch) return; // outra troca de sessão já aconteceu
    current = null;
    epoch += 1;
    await tokenStore.clear();
    if (notify) for (const listener of [...lostListeners]) listener();
  }

  async function renew(atEpoch: number): Promise<void> {
    const session = current;
    if (session === null) {
      await dropSession(atEpoch, true);
      throw new ApiError(401, CLIENT_CODES.sessionLost);
    }
    const raw = await exchange(
      "POST",
      urlFor("/mobile/auth/refresh/"),
      { refresh_token: session.refreshToken },
      null,
      defaultTimeout,
    );
    if (raw.status === 401 || raw.status === 403) {
      await dropSession(atEpoch, true);
      throw new ApiError(401, CLIENT_CODES.sessionLost);
    }
    if (raw.status < 200 || raw.status >= 300) throw toApiError(raw);
    if (!raw.json) malformed();
    let next: StoredSession;
    try {
      next = parseTokens(raw.body);
    } catch {
      malformed();
    }
    // Saiu ou entrou outra pessoa durante a renovação: não ressuscita a sessão.
    if (epoch !== atEpoch) throw new ApiError(0, CLIENT_CODES.sessionChanged);
    current = next;
    await persist(next);
  }

  /**
   * Renovação única: quem chega durante uma renovação da mesma sessão aguarda a mesma
   * promessa. Uma renovação de sessão anterior (saiu e entrou de novo) não é reaproveitada.
   */
  function renewOnce(atEpoch: number): Promise<void> {
    if (refreshing === null || refreshing.epoch !== atEpoch) {
      const entry: { epoch: number; promise: Promise<void> } = {
        epoch: atEpoch,
        promise: renew(atEpoch).finally(() => {
          if (refreshing === entry) refreshing = null;
        }),
      };
      refreshing = entry;
    }
    return refreshing.promise;
  }

  async function request<T>(
    method: string,
    path: string,
    body: unknown,
    opts: RequestOptions<T> = {},
  ): Promise<T> {
    const url = urlFor(path, opts.query);
    const authenticated = opts.auth !== false;
    const timeoutMs = opts.timeoutMs ?? defaultTimeout;
    const startedAt = epoch;
    let retried = false;
    for (;;) {
      let accessToken: string | null = null;
      if (authenticated) {
        if (epoch !== startedAt)
          throw new ApiError(0, CLIENT_CODES.sessionChanged);
        if (current === null) {
          await dropSession(startedAt, true);
          throw new ApiError(401, CLIENT_CODES.sessionLost);
        }
        accessToken = current.accessToken;
      }
      const raw = await exchange(method, url, body, accessToken, timeoutMs);
      if (authenticated && epoch !== startedAt) {
        throw new ApiError(0, CLIENT_CODES.sessionChanged);
      }
      if (authenticated && raw.status === 401) {
        if (retried) {
          // Já com par novo e ainda 401: a sessão foi revogada no servidor.
          await dropSession(startedAt, true);
          throw new ApiError(401, CLIENT_CODES.sessionLost);
        }
        retried = true;
        // Outra chamada já renovou enquanto esta estava em voo: só repete.
        if (current !== null && current.accessToken !== accessToken) continue;
        await renewOnce(startedAt);
        continue;
      }
      if (raw.status >= 200 && raw.status < 300) {
        if (raw.status === 204) return undefined as T;
        if (!raw.json) malformed();
        if (!opts.parse) return raw.body as T;
        try {
          return opts.parse(raw.body);
        } catch (error) {
          if (error instanceof ApiError) throw error;
          return malformed();
        }
      }
      throw toApiError(raw);
    }
  }

  return {
    configured: base !== null,
    get: (path, opts) => request("GET", path, undefined, opts),
    post: (path, body, opts) => request("POST", path, body ?? undefined, opts),
    put: (path, body, opts) => request("PUT", path, body ?? undefined, opts),
    delete: (path, opts) => request("DELETE", path, undefined, opts),
    async restore() {
      const stored = await tokenStore.load();
      if (stored === null) return null;
      if (Date.parse(stored.refreshExpiresAt) <= Date.now()) {
        // Renovação vencida: nem vale tentar; o paciente entra de novo.
        await tokenStore.clear();
        return null;
      }
      current = stored;
      epoch += 1;
      return sessionInfo(stored);
    },
    async setSession(session) {
      current = session;
      epoch += 1;
      await persist(session);
    },
    async clearSession() {
      current = null;
      epoch += 1;
      await tokenStore.clear();
    },
    currentSession() {
      return current === null ? null : sessionInfo(current);
    },
    onSessionLost(listener) {
      lostListeners.add(listener);
      return () => {
        lostListeners.delete(listener);
      };
    },
  };
}
