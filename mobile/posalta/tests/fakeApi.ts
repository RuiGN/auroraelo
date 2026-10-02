/**
 * Servidor falso para os testes do cliente HTTP, da sessão, do store live e das telas
 * de entrada: um transporte (`Transport`) que registra cada chamada e responde pelo
 * `handler` do teste. Nada aqui abre rede.
 */
import { Transport, TransportResponse } from "../src/api/client";
import { StoredSession } from "../src/api/types";

export const BASE_URL = "https://api.clinica.test";
export const API = `${BASE_URL}/api/v1`;

export interface FakeCall {
  url: string;
  /** Caminho depois de `/api/v1`, sem a consulta. */
  path: string;
  method: string;
  headers: Record<string, string>;
  /** Corpo JSON já decodificado (`undefined` sem corpo). */
  body: any;
  init: RequestInit;
}

export interface FakeReply {
  status: number;
  body?: unknown;
  /** Padrão `application/json`; `null` omite o cabeçalho. */
  contentType?: string | null;
  /** URL da resposta (simula redirecionamento). Padrão: a da requisição. */
  url?: string;
  /** `json()` rejeita (corpo ilegível). */
  unreadable?: boolean;
}

export type Handler = (call: FakeCall) => FakeReply | Promise<FakeReply>;

export interface FakeServer {
  transport: Transport;
  calls: FakeCall[];
  /** Quantas vezes `json()` foi chamado (para provar que o corpo não foi lido). */
  jsonReads: () => number;
  callsTo: (path: string) => FakeCall[];
}

export function createFakeServer(handler: Handler): FakeServer {
  const calls: FakeCall[] = [];
  let reads = 0;
  const transport: Transport = async (input, init) => {
    const headers: Record<string, string> = {};
    for (const [key, value] of Object.entries(init.headers ?? {})) {
      headers[key] = String(value);
    }
    const url = new URL(input);
    const call: FakeCall = {
      url: input,
      path: url.pathname.replace(/^\/api\/v1/, ""),
      method: String(init.method),
      headers,
      body: typeof init.body === "string" ? JSON.parse(init.body) : undefined,
      init,
    };
    calls.push(call);
    const reply = await handler(call);
    const contentType =
      reply.contentType === undefined ? "application/json" : reply.contentType;
    const response: TransportResponse = {
      status: reply.status,
      url: reply.url ?? input,
      headers: {
        get: (name) =>
          name.toLowerCase() === "content-type" ? contentType : null,
      },
      json: async () => {
        reads += 1;
        if (reply.unreadable) throw new SyntaxError("Unexpected token");
        return reply.body;
      },
    };
    return response;
  };
  return {
    transport,
    calls,
    jsonReads: () => reads,
    callsTo: (path) => calls.filter((call) => call.path === path),
  };
}

/** Falha de rede como o `fetch` a reporta. */
export function networkFailure(): never {
  throw new TypeError("Network request failed");
}

/** Resposta que nunca chega; rejeita quando o cliente aborta (tempo esgotado). */
export function hang(call: FakeCall): Promise<never> {
  return new Promise((_, reject) => {
    call.init.signal?.addEventListener("abort", () =>
      reject(new Error("aborted")),
    );
  });
}

/** Promessa resolvida de fora: para ordenar respostas concorrentes. */
export function deferred<T = void>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/** Corpo `TokensOut` do servidor; `n` distingue pares de tokens sucessivos. */
export function tokensBody(n = 1, overrides: Record<string, unknown> = {}) {
  return {
    session_id: "11111111-1111-4111-8111-111111111111",
    access_token: `aem_access_${n}`,
    access_expires_at: "2099-01-01T00:15:00Z",
    refresh_token: `aer_refresh_${n}`,
    refresh_expires_at: "2099-02-01T00:00:00Z",
    clinic: {
      id: "22222222-2222-4222-8222-222222222222",
      name: "Clínica Aurora",
    },
    patient: {
      id: "33333333-3333-4333-8333-333333333333",
      display_name: "Alex Paciente",
    },
    ...overrides,
  };
}

/** A mesma sessão como o app a guarda no cofre. */
export function storedSession(n = 1): StoredSession {
  return {
    sessionId: "11111111-1111-4111-8111-111111111111",
    accessToken: `aem_access_${n}`,
    accessExpiresAt: "2099-01-01T00:15:00Z",
    refreshToken: `aer_refresh_${n}`,
    refreshExpiresAt: "2099-02-01T00:00:00Z",
    clinic: {
      id: "22222222-2222-4222-8222-222222222222",
      name: "Clínica Aurora",
    },
    patient: {
      id: "33333333-3333-4333-8333-333333333333",
      displayName: "Alex Paciente",
    },
  };
}

/** `GET /mobile/me/` mínimo e válido. */
export function meBody(overrides: Record<string, unknown> = {}) {
  return {
    id: "33333333-3333-4333-8333-333333333333",
    display_name: "Alex Paciente",
    language: "pt-br",
    timezone: "America/Sao_Paulo",
    clinic: {
      id: "22222222-2222-4222-8222-222222222222",
      name: "Clínica Aurora",
    },
    discharge_date: "2026-09-23",
    care_team: [
      {
        id: "44444444-4444-4444-8444-444444444444",
        name: "Dra. Helena",
        role: "psychiatrist",
      },
    ],
    ...overrides,
  };
}
