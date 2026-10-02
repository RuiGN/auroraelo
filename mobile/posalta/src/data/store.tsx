import React, {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { AppState } from "react-native";
import { useOptionalSession } from "../api/session";
import { AppMode, APP_MODE } from "../config";
import { Snapshot } from "../domain/types";
import { LIVE_ACTIONS, LiveActionRegistry } from "./live/actions";
import { createLiveEngine, LiveEngine, LiveState } from "./live/engine";
import { LoaderEntry, LOADERS, SnapshotSlice } from "./live/registry";
import { Mutation } from "./mutations";
import {
  ActionFailure,
  ActionOutcome,
  LoadFailure,
  StoreStatus,
} from "./outcome";
import { buildPreviewSnapshot } from "./previewData";

export type { ActionFailure, ActionOutcome, LoadFailure, StoreStatus };

export interface Store {
  mode: AppMode;
  /**
   * Preview: dados sintéticos em memória. Live: dados da API da sessão ativa
   * (`null` até o paciente carregar e sempre `null` sem sessão ativa).
   */
  snapshot: Snapshot | null;
  now: Date;
  /** `idle` sem sessão/config; `loading`; `error` (veja `failure`); `ready`. */
  status: StoreStatus;
  /** Motivo do último carregamento que falhou (`null` se não houver falha). */
  failure: LoadFailure | null;
  /**
   * Aplica uma gravação. Preview: aplica a mutação pura na memória (resolve na hora).
   * Live: executa a ação remota registrada para a mutação (ver `live/actions.ts`),
   * recarrega as fatias afetadas e resolve com o resultado; sem ação registrada
   * resolve `unavailable`. Nunca finge sucesso.
   */
  run: (mutation: Mutation) => Promise<ActionOutcome>;
  /** Recarrega fatias do snapshot (todas se omitido). Sem efeito no preview. */
  refresh: (slices?: readonly SnapshotSlice[]) => Promise<void>;
}

const StoreContext = createContext<Store | null>(null);

interface StoreProviderProps {
  children: ReactNode;
  mode?: AppMode;
  /** Relógio injetável para testes; quando informado, não há atualização periódica. */
  clock?: () => Date;
  initialSnapshot?: Snapshot;
  /** Registros injetáveis para teste; o padrão são os de `src/data/live/`. */
  loaders?: readonly LoaderEntry[];
  actions?: LiveActionRegistry;
  /** Intervalo mínimo entre recarregamentos ao voltar ao primeiro plano. */
  minRefreshIntervalMs?: number;
}

const IDLE: LiveState = { snapshot: null, status: "idle", failure: null };
const noopSubscribe = () => () => undefined;
const idleState = () => IDLE;

export function StoreProvider({
  children,
  mode = APP_MODE,
  clock,
  initialSnapshot,
  loaders = LOADERS,
  actions = LIVE_ACTIONS,
  minRefreshIntervalMs,
}: StoreProviderProps) {
  const [now, setNow] = useState<Date>(() => (clock ? clock() : new Date()));
  const nowRef = useRef<Date>(now);
  nowRef.current = now;

  useEffect(() => {
    if (clock) return undefined;
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, [clock]);

  // ── Preview: estado só na memória, mutações puras síncronas ───────────────
  const [previewSnapshot, setPreviewSnapshot] = useState<Snapshot | null>(() =>
    mode === "preview" ? (initialSnapshot ?? buildPreviewSnapshot(now)) : null,
  );
  const previewRef = useRef<Snapshot | null>(previewSnapshot);

  // ── Live: um motor por sessão ativa ───────────────────────────────────────
  const session = useOptionalSession();
  const api =
    mode === "live" && session?.status === "active" ? session.api : null;
  const [engine, setEngine] = useState<LiveEngine | null>(null);

  useEffect(() => {
    if (!api) return undefined;
    const created = createLiveEngine({
      api,
      loaders,
      actions,
      minRefreshIntervalMs,
    });
    setEngine(created);
    void created.refresh();
    // Ao voltar ao primeiro plano recarrega tudo, no máximo uma vez por intervalo e
    // nunca com outro carregamento em andamento (sem tempestade de requisições).
    let previous = AppState.currentState;
    const subscription = AppState.addEventListener("change", (next) => {
      if (next === "active" && previous !== "active") {
        void created.refreshIfStale();
      }
      previous = next;
    });
    return () => {
      subscription.remove();
      created.dispose();
      setEngine(null);
    };
  }, [api, loaders, actions, minRefreshIntervalMs]);

  const liveState = useSyncExternalStore(
    engine ? engine.subscribe : noopSubscribe,
    engine ? engine.getState : idleState,
    idleState,
  );
  // Sem sessão ativa nada clínico fica visível, mesmo por um instante.
  const live: LiveState = api && engine ? liveState : IDLE;

  const run = useCallback(
    (mutation: Mutation): Promise<ActionOutcome> => {
      if (mode === "preview") {
        if (previewRef.current === null) {
          return Promise.resolve({ ok: false, reason: "unavailable" });
        }
        const moment = clock ? clock() : new Date();
        const next = mutation(previewRef.current, moment);
        if (next === null)
          return Promise.resolve({ ok: false, reason: "invalid" });
        previewRef.current = next;
        setPreviewSnapshot(next);
        return Promise.resolve({ ok: true });
      }
      if (!engine) {
        // Sem motor: ou a sessão acabou/ainda não existe (`session`), ou não há com
        // quem falar (sem configuração) e a gravação simplesmente não existe.
        const noSession =
          session?.status === "signedOut" || session?.status === "restoring";
        return Promise.resolve(
          noSession
            ? { ok: false, reason: "session" }
            : { ok: false, reason: "unavailable" },
        );
      }
      return engine.run(mutation);
    },
    [mode, clock, engine, session?.status],
  );

  const refresh = useCallback(
    (slices?: readonly SnapshotSlice[]): Promise<void> =>
      engine ? engine.refresh(slices) : Promise.resolve(),
    [engine],
  );

  const value = useMemo<Store>(
    () =>
      mode === "preview"
        ? {
            mode,
            snapshot: previewSnapshot,
            now,
            status: previewSnapshot ? "ready" : "idle",
            failure: null,
            run,
            refresh,
          }
        : {
            mode,
            snapshot: live.snapshot,
            now,
            status: live.status,
            failure: live.failure,
            run,
            refresh,
          },
    [mode, previewSnapshot, live, now, run, refresh],
  );
  return (
    <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
  );
}

export function useStore(): Store {
  const store = useContext(StoreContext);
  if (!store)
    throw new Error("useStore precisa estar dentro de StoreProvider.");
  return store;
}
