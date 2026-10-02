/**
 * Motor do modo live: carrega o Snapshot pelos loaders e executa as gravações pelas
 * ações registradas. É TypeScript puro (sem React) para ser testado isoladamente; o
 * `StoreProvider` cria um motor por sessão ativa e o descarta ao perder a sessão, o
 * que zera o snapshot em memória.
 *
 * Garantias:
 * - cada loader roda no máximo uma vez por vez (chamadas simultâneas aguardam a
 *   mesma promessa) e um resultado mais antigo nunca sobrescreve um mais novo;
 * - o recarregamento depois de uma gravação ignora requisições anteriores à
 *   gravação (`force`), para não mostrar o estado de antes;
 * - falha de um loader não impede os outros; a fatia fica com o último valor bom
 *   (ou vazio);
 * - duas gravações simultâneas da mesma ação com a mesma entrada viram uma só
 *   (trava por chave + entrada), evitando registro duplicado por toque duplo;
 * - nunca se finge sucesso: sem ação registrada o resultado é `unavailable`.
 */
import { Api } from "../../api/client";
import {
  CLIENT_CODES,
  isApiError,
  isOfflineError,
  isSessionError,
} from "../../api/errors";
import { Snapshot } from "../../domain/types";
import { Mutation, MutationKey } from "../mutations";
import { ActionOutcome, LoadFailure, StoreStatus } from "../outcome";
import { LiveActionRegistry, RemoteResult } from "./actions";
import { emptySnapshotFor } from "./empty";
import { LoaderEntry, SnapshotSlice } from "./registry";

export interface LiveState {
  snapshot: Snapshot | null;
  status: StoreStatus;
  failure: LoadFailure | null;
}

export interface LiveEngineOptions {
  api: Api;
  loaders: readonly LoaderEntry[];
  actions: LiveActionRegistry;
  /** Relógio injetável (ms). */
  now?: () => number;
  /** Intervalo mínimo entre recarregamentos automáticos (primeiro plano). */
  minRefreshIntervalMs?: number;
}

export interface LiveEngine {
  getState(): LiveState;
  subscribe(listener: () => void): () => void;
  /**
   * Recarrega as fatias pedidas (todas, se omitido). Nunca rejeita: o resultado fica
   * em `status`/`failure`. `force` ignora requisições já em andamento.
   */
  refresh(
    slices?: readonly SnapshotSlice[],
    options?: { force?: boolean },
  ): Promise<void>;
  /** Recarrega tudo, a menos que já esteja carregando ou tenha carregado há pouco. */
  refreshIfStale(): Promise<void>;
  run(mutation: Mutation): Promise<ActionOutcome>;
  /** Encerra o motor: resultados em voo são descartados e o estado é abandonado. */
  dispose(): void;
}

export const MIN_REFRESH_INTERVAL_MS = 30_000;

type EntryResult =
  | { ok: true; entry: LoaderEntry; seq: number; partial: Partial<Snapshot> }
  | { ok: false; entry: LoaderEntry; seq: number; error: unknown };

interface EntryRun {
  seq: number;
  applied: number;
  inflight?: Promise<EntryResult>;
}

/** JSON com as chaves ordenadas: a mesma entrada gera sempre a mesma trava. */
function stable(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value) ?? "undefined";
  }
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  const source = value as Record<string, unknown>;
  const body = Object.keys(source)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${stable(source[key])}`);
  return `{${body.join(",")}}`;
}

/** Falha de carregamento para exibir; `null` quando é perda de sessão (outro fluxo). */
function classifyLoad(error: unknown): LoadFailure | null {
  if (isSessionError(error)) return null;
  if (isOfflineError(error)) return "offline";
  if (isApiError(error) && error.code === CLIENT_CODES.clinicBlocked) {
    return "blocked";
  }
  return "unexpected";
}

/** Resultado de uma gravação que falhou (erro vindo da ação ou do cliente HTTP). */
export function outcomeFromError(error: unknown): ActionOutcome {
  if (!isApiError(error)) {
    return { ok: false, reason: "unavailable", code: "unexpected" };
  }
  if (isOfflineError(error)) return { ok: false, reason: "offline" };
  if (isSessionError(error)) return { ok: false, reason: "session" };
  if (error.code === CLIENT_CODES.clinicBlocked) {
    return { ok: false, reason: "blocked", code: error.code };
  }
  if (error.status >= 400 && error.status < 500) {
    return { ok: false, reason: "rejected", code: error.code };
  }
  return { ok: false, reason: "unavailable", code: error.code };
}

const FAILURE_ORDER: LoadFailure[] = ["blocked", "offline", "unexpected"];

export function createLiveEngine(options: LiveEngineOptions): LiveEngine {
  const { api, loaders, actions } = options;
  const now = options.now ?? Date.now;
  const minInterval = options.minRefreshIntervalMs ?? MIN_REFRESH_INTERVAL_MS;

  let state: LiveState = { snapshot: null, status: "idle", failure: null };
  let loaded: Partial<Snapshot> = {};
  /** Algum resultado novo entrou em `loaded`: o snapshot precisa ser remontado. */
  let dirty = false;
  let disposed = false;
  let activeRefreshes = 0;
  let lastStart = Number.NEGATIVE_INFINITY;
  const listeners = new Set<() => void>();
  const runs = new Map<LoaderEntry, EntryRun>();
  const failures = new Map<LoaderEntry, LoadFailure>();
  const locks = new Map<string, Promise<ActionOutcome>>();

  function publish(next: Partial<LiveState>) {
    if (disposed) return;
    const merged = { ...state, ...next };
    if (
      merged.snapshot === state.snapshot &&
      merged.status === state.status &&
      merged.failure === state.failure
    ) {
      return;
    }
    state = merged;
    for (const listener of [...listeners]) listener();
  }

  function runFor(entry: LoaderEntry): EntryRun {
    let run = runs.get(entry);
    if (!run) {
      run = { seq: 0, applied: 0 };
      runs.set(entry, run);
    }
    return run;
  }

  function load(entry: LoaderEntry, force: boolean): Promise<EntryResult> {
    const run = runFor(entry);
    if (!force && run.inflight) return run.inflight;
    run.seq += 1;
    const seq = run.seq;
    const promise: Promise<EntryResult> = Promise.resolve()
      .then(() => entry.load(api))
      .then(
        (partial): EntryResult => ({ ok: true, entry, seq, partial }),
        (error: unknown): EntryResult => ({ ok: false, entry, seq, error }),
      );
    run.inflight = promise;
    void promise.then(() => {
      if (run.inflight === promise) run.inflight = undefined;
    });
    return promise;
  }

  /** Aplica um resultado (ignora os que já foram superados por outro mais novo). */
  function apply(result: EntryResult): void {
    const run = runFor(result.entry);
    if (result.seq <= run.applied) return; // resultado mais antigo que o já aplicado
    run.applied = result.seq;
    if (!result.ok) {
      const failure = classifyLoad(result.error);
      if (failure) failures.set(result.entry, failure);
      else failures.delete(result.entry);
      return;
    }
    failures.delete(result.entry);
    const partial = result.partial;
    if (typeof partial !== "object" || partial === null) {
      failures.set(result.entry, "unexpected");
      return;
    }
    // Só as fatias declaradas pelo loader entram: um domínio não sobrescreve outro.
    const next: Record<string, unknown> = { ...loaded };
    for (const slice of result.entry.slices) {
      const value = partial[slice];
      if (value !== undefined) next[slice] = value;
    }
    loaded = next as Partial<Snapshot>;
    dirty = true;
  }

  function rebuild(): Snapshot | null {
    const patient = loaded.patient;
    if (!patient) return null;
    return { ...emptySnapshotFor(patient), ...loaded } as Snapshot;
  }

  /**
   * O snapshot só é remontado quando algum resultado novo entrou; uma falha de
   * recarregamento mantém o mesmo objeto (as telas não redesenham à toa).
   */
  function currentSnapshot(): Snapshot | null {
    if (!dirty) return state.snapshot;
    dirty = false;
    return rebuild();
  }

  /** Publica o snapshot e, quando nenhum carregamento está em voo, o estado final. */
  function settle() {
    const snapshot = currentSnapshot();
    if (activeRefreshes > 0) {
      publish({ snapshot });
      return;
    }
    const kinds = new Set(failures.values());
    const failure = FAILURE_ORDER.find((kind) => kinds.has(kind)) ?? null;
    publish({ snapshot, status: failure ? "error" : "ready", failure });
  }

  async function refresh(
    slices?: readonly SnapshotSlice[],
    refreshOptions: { force?: boolean } = {},
  ): Promise<void> {
    if (disposed) return;
    const entries =
      slices === undefined
        ? loaders
        : loaders.filter((entry) =>
            entry.slices.some((slice) => slices.includes(slice)),
          );
    if (entries.length === 0) return;
    lastStart = now();
    activeRefreshes += 1;
    publish({ status: "loading" });
    let results: EntryResult[] = [];
    try {
      results = await Promise.all(
        entries.map((entry) => load(entry, refreshOptions.force === true)),
      );
    } finally {
      activeRefreshes -= 1;
    }
    if (disposed) return;
    for (const result of results) apply(result);
    settle();
  }

  async function execute(
    key: MutationKey,
    input: unknown,
  ): Promise<ActionOutcome> {
    const action = actions[key];
    if (!action) return { ok: false, reason: "unavailable" };
    let result: RemoteResult;
    try {
      const run = action.run as (
        value: unknown,
      ) => (client: Api) => Promise<RemoteResult>;
      result = await run(input)(api);
    } catch (error) {
      return outcomeFromError(error);
    }
    if (!result.ok) {
      return result.code
        ? { ok: false, reason: "invalid", code: result.code }
        : { ok: false, reason: "invalid" };
    }
    // O servidor aceitou: recarrega as fatias afetadas (ignorando requisições em voo
    // anteriores à gravação). Se o recarregamento falhar, a gravação continua válida.
    if (action.refresh.length > 0) {
      await refresh(action.refresh, { force: true });
    }
    return { ok: true };
  }

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    refresh,
    refreshIfStale() {
      if (disposed || activeRefreshes > 0) return Promise.resolve();
      if (now() - lastStart < minInterval) return Promise.resolve();
      return refresh();
    },
    run(mutation) {
      const meta = mutation.meta;
      if (!meta || !actions[meta.key as MutationKey]) {
        return Promise.resolve({ ok: false, reason: "unavailable" });
      }
      const lockKey = `${meta.key}:${stable(meta.input)}`;
      const running = locks.get(lockKey);
      if (running) return running;
      const promise = execute(meta.key as MutationKey, meta.input).finally(
        () => {
          locks.delete(lockKey);
        },
      );
      locks.set(lockKey, promise);
      return promise;
    },
    dispose() {
      disposed = true;
      listeners.clear();
      locks.clear();
    },
  };
}
