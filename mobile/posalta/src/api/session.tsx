/**
 * Sessão do paciente no modo `live`.
 *
 * Máquina de estados:
 *
 *   disabled ── (preview, ou sem endereço válido do servidor: não usa sessão)
 *   restoring ─► signedOut | active      (lê o cofre seguro, sem rede)
 *   signedOut ─► active                  (entrar / ativar conta)
 *   active    ─► signedOut               (sair, ou sessão perdida)
 *
 * O estado guarda só dados não sensíveis (clínica e nome de exibição). Os tokens
 * ficam no cliente HTTP e no cofre; senhas e códigos passam pelas funções abaixo e
 * não são guardados nem registrados em lugar nenhum.
 */
import React, {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { APP_MODE, API_BASE_URL, AppMode } from "../config";
import { Api, ApiClient, createApiClient, Transport } from "./client";
import { describeDevice, DeviceInfo } from "./deviceInfo";
import { ApiError, ClinicRef, CLIENT_CODES, isApiError } from "./errors";
import { int, record } from "./parse";
import { createDefaultTokenStore, TokenStore } from "./tokenStore";
import {
  DeviceSession,
  parseDeviceSessions,
  parseTokens,
  SessionInfo,
  sessionInfo,
} from "./types";

export type SessionStatus = "disabled" | "restoring" | "signedOut" | "active";

/** Aviso mostrado na tela de entrada depois de uma mudança de estado. */
export type SessionNotice = "expired" | "password_reset";

export type AuthFailureReason =
  | "invalid_credentials"
  | "rate_limited"
  | "offline"
  | "invalid_code"
  | "weak_password"
  | "clinic_choice"
  | "blocked"
  | "unexpected";

export type AuthResult =
  | { ok: true }
  | {
      ok: false;
      reason: AuthFailureReason;
      /** `weak_password`: mensagens de validação do servidor. */
      errors?: string[];
      /** `clinic_choice`: clínicas entre as quais o paciente escolhe. */
      clinics?: ClinicRef[];
    };

export type LogoutOthersResult =
  | { ok: true; revoked: number }
  | { ok: false; reason: AuthFailureReason };

export interface LoginInput {
  email: string;
  password: string;
  /** Só depois de um `clinic_choice`. */
  clinicId?: string;
}

export interface ActivateInput {
  code: string;
  password: string;
  firstName: string;
  lastName: string;
}

export interface ResetInput {
  code: string;
  newPassword: string;
}

/** Traduz um erro da API em motivo de falha de entrada (a UI escolhe o texto). */
export function toAuthFailure(error: unknown): AuthResult & { ok: false } {
  if (!isApiError(error)) return { ok: false, reason: "unexpected" };
  if (
    error.code === CLIENT_CODES.network ||
    error.code === CLIENT_CODES.timeout
  ) {
    return { ok: false, reason: "offline" };
  }
  switch (error.code) {
    case "invalid_credentials":
      return { ok: false, reason: "invalid_credentials" };
    case CLIENT_CODES.rateLimited:
      return { ok: false, reason: "rate_limited" };
    case CLIENT_CODES.clinicBlocked:
      return { ok: false, reason: "blocked" };
    case "invalid_code":
      return { ok: false, reason: "invalid_code" };
    case "weak_password":
      return { ok: false, reason: "weak_password", errors: error.errors ?? [] };
    case "clinic_choice_required":
      return error.clinics && error.clinics.length > 0
        ? { ok: false, reason: "clinic_choice", clinics: error.clinics }
        : { ok: false, reason: "unexpected" };
    default:
      return { ok: false, reason: "unexpected" };
  }
}

export interface Session {
  status: SessionStatus;
  /** Clínica e nome de exibição da sessão ativa (nunca tokens). */
  info: SessionInfo | null;
  notice: SessionNotice | null;
  clearNotice: () => void;
  /** Cliente para loaders e ações; `null` quando `status = "disabled"`. */
  api: Api | null;
  login: (input: LoginInput) => Promise<AuthResult>;
  activate: (input: ActivateInput) => Promise<AuthResult>;
  /** Resposta neutra: o servidor sempre responde 202, exista ou não o e-mail. */
  requestRecovery: (email: string) => Promise<AuthResult>;
  resetPassword: (input: ResetInput) => Promise<AuthResult>;
  /** Sempre encerra a sessão neste aparelho, mesmo que a rede falhe. */
  logout: () => Promise<void>;
  logoutOthers: () => Promise<LogoutOthersResult>;
  listSessions: () => Promise<DeviceSession[] | null>;
  revokeSession: (sessionId: string) => Promise<AuthResult>;
}

const SessionContext = createContext<Session | null>(null);

interface SessionState {
  status: SessionStatus;
  info: SessionInfo | null;
  notice: SessionNotice | null;
}

/** Tempo máximo esperando o servidor ao sair (a limpeza local não depende dele). */
const LOGOUT_TIMEOUT_MS = 5_000;

interface SessionProviderProps {
  children: ReactNode;
  mode?: AppMode;
  /** Origem do servidor; padrão `EXPO_PUBLIC_API_BASE_URL` validada em `config.ts`. */
  baseUrl?: string | null;
  /** Injetáveis para teste. Lidos só na primeira montagem. */
  transport?: Transport;
  tokenStore?: TokenStore;
  timeoutMs?: number;
  device?: () => DeviceInfo;
  /** Permite `http` em localhost (padrão: `__DEV__`). */
  dev?: boolean;
}

export function SessionProvider({
  children,
  mode = APP_MODE,
  baseUrl = API_BASE_URL,
  transport,
  tokenStore,
  timeoutMs,
  device = describeDevice,
  dev,
}: SessionProviderProps) {
  const [client] = useState<ApiClient>(() =>
    createApiClient({
      baseUrl,
      transport,
      tokenStore: tokenStore ?? createDefaultTokenStore(),
      timeoutMs,
      dev,
    }),
  );
  const enabled = mode === "live" && client.configured;
  // Loaders e ações recebem só as chamadas HTTP: nunca `setSession`, `restore` etc.
  const api = useMemo<Api>(
    () => ({
      get: (path, opts) => client.get(path, opts),
      post: (path, body, opts) => client.post(path, body, opts),
      put: (path, body, opts) => client.put(path, body, opts),
      delete: (path, opts) => client.delete(path, opts),
    }),
    [client],
  );
  const [state, setState] = useState<SessionState>({
    status: enabled ? "restoring" : "disabled",
    info: null,
    notice: null,
  });
  const statusRef = useRef(state.status);
  statusRef.current = state.status;
  const deviceRef = useRef(device);
  deviceRef.current = device;
  const flights = useRef(new Map<string, Promise<unknown>>());

  useEffect(() => {
    if (!enabled) return undefined;
    let alive = true;
    client
      .restore()
      .then((info) => {
        if (!alive) return;
        setState((prev) =>
          prev.status !== "restoring"
            ? prev
            : info
              ? { status: "active", info, notice: null }
              : { status: "signedOut", info: null, notice: null },
        );
      })
      .catch(() => {
        if (alive) {
          setState((prev) =>
            prev.status === "restoring"
              ? { status: "signedOut", info: null, notice: null }
              : prev,
          );
        }
      });
    const stop = client.onSessionLost(() => {
      setState((prev) =>
        prev.status === "disabled" || prev.status === "signedOut"
          ? prev
          : { status: "signedOut", info: null, notice: "expired" },
      );
    });
    return () => {
      alive = false;
      stop();
    };
  }, [client, enabled]);

  /** Uma chamada por nome de cada vez: toque duplo não repete a requisição. */
  const once = useCallback(
    <T,>(name: string, run: () => Promise<T>): Promise<T> => {
      const running = flights.current.get(name);
      if (running) return running as Promise<T>;
      const promise = run().finally(() => {
        flights.current.delete(name);
      });
      flights.current.set(name, promise);
      return promise;
    },
    [],
  );

  const enter = useCallback(
    async (
      path: string,
      body: Record<string, unknown>,
    ): Promise<AuthResult> => {
      try {
        const tokens = await client.post(path, body, {
          auth: false,
          parse: parseTokens,
        });
        await client.setSession(tokens);
        setState({ status: "active", info: sessionInfo(tokens), notice: null });
        return { ok: true };
      } catch (error) {
        return toAuthFailure(error);
      }
    },
    [client],
  );

  const login = useCallback(
    (input: LoginInput) =>
      once("login", () => {
        const info = deviceRef.current();
        return enter("/mobile/auth/login/", {
          email: input.email.trim(),
          password: input.password,
          ...(input.clinicId ? { clinic_id: input.clinicId } : {}),
          device_label: info.deviceLabel,
          platform: info.platform,
          app_version: info.appVersion,
        });
      }),
    [enter, once],
  );

  const activate = useCallback(
    (input: ActivateInput) =>
      once("activate", () => {
        const info = deviceRef.current();
        return enter("/mobile/auth/activate/", {
          code: input.code.trim(),
          password: input.password,
          first_name: input.firstName.trim(),
          last_name: input.lastName.trim(),
          device_label: info.deviceLabel,
          platform: info.platform,
          app_version: info.appVersion,
        });
      }),
    [enter, once],
  );

  const requestRecovery = useCallback(
    (email: string) =>
      once("recovery", async (): Promise<AuthResult> => {
        try {
          await client.post(
            "/mobile/auth/password-recovery/",
            { email: email.trim() },
            { auth: false },
          );
          return { ok: true };
        } catch (error) {
          return toAuthFailure(error);
        }
      }),
    [client, once],
  );

  const resetPassword = useCallback(
    (input: ResetInput) =>
      once("reset", async (): Promise<AuthResult> => {
        try {
          await client.post(
            "/mobile/auth/password-reset/",
            { code: input.code.trim(), new_password: input.newPassword },
            { auth: false },
          );
          setState((prev) =>
            prev.status === "signedOut"
              ? { ...prev, notice: "password_reset" }
              : prev,
          );
          return { ok: true };
        } catch (error) {
          return toAuthFailure(error);
        }
      }),
    [client, once],
  );

  const logout = useCallback(
    () =>
      once("logout", async () => {
        if (statusRef.current !== "active") return;
        // O servidor é avisado quando possível, mas a saída local nunca espera mais
        // que `LOGOUT_TIMEOUT_MS` (a renovação do token também entra nessa conta).
        const notified = client
          .post("/mobile/auth/logout/", undefined, {
            timeoutMs: LOGOUT_TIMEOUT_MS,
          })
          .catch(() => undefined); // sem rede, sessão já encerrada ou clínica bloqueada
        let timer: ReturnType<typeof setTimeout> | undefined;
        const expired = new Promise<void>((resolve) => {
          timer = setTimeout(resolve, LOGOUT_TIMEOUT_MS);
        });
        await Promise.race([notified, expired]);
        clearTimeout(timer);
        await client.clearSession();
        setState({ status: "signedOut", info: null, notice: null });
      }),
    [client, once],
  );

  const logoutOthers = useCallback(
    (): Promise<LogoutOthersResult> =>
      once("logoutOthers", async (): Promise<LogoutOthersResult> => {
        try {
          const revoked = await client.post(
            "/mobile/auth/sessions/revoke-others/",
            undefined,
            { parse: (value) => int(record(value).revoked) },
          );
          return { ok: true, revoked };
        } catch (error) {
          const failure = toAuthFailure(error);
          return {
            ok: false,
            reason: failure.ok ? "unexpected" : failure.reason,
          };
        }
      }),
    [client, once],
  );

  const listSessions = useCallback(async (): Promise<
    DeviceSession[] | null
  > => {
    try {
      return await client.get("/mobile/auth/sessions/", {
        parse: parseDeviceSessions,
      });
    } catch {
      return null;
    }
  }, [client]);

  const revokeSession = useCallback(
    async (sessionId: string): Promise<AuthResult> => {
      try {
        await client.delete(`/mobile/auth/sessions/${sessionId}/`);
        return { ok: true };
      } catch (error) {
        if (error instanceof ApiError && error.code === "not_found") {
          return { ok: true }; // já encerrado: o efeito desejado
        }
        return toAuthFailure(error);
      }
    },
    [client],
  );

  const clearNotice = useCallback(() => {
    setState((prev) => (prev.notice ? { ...prev, notice: null } : prev));
  }, []);

  const value = useMemo<Session>(
    () => ({
      status: state.status,
      info: state.info,
      notice: state.notice,
      clearNotice,
      api: state.status === "disabled" ? null : api,
      login,
      activate,
      requestRecovery,
      resetPassword,
      logout,
      logoutOthers,
      listSessions,
      revokeSession,
    }),
    [
      state,
      api,
      clearNotice,
      login,
      activate,
      requestRecovery,
      resetPassword,
      logout,
      logoutOthers,
      listSessions,
      revokeSession,
    ],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

/** Sessão, ou `null` fora de `SessionProvider` (telas que funcionam sem ela). */
export function useOptionalSession(): Session | null {
  return useContext(SessionContext);
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession precisa estar dentro de SessionProvider.");
  }
  return session;
}
