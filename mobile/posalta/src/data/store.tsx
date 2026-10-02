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
import { AppMode, APP_MODE } from "../config";
import { Snapshot } from "../domain/types";
import { Mutation } from "./mutations";
import { buildPreviewSnapshot } from "./previewData";

export type ActionOutcome =
  | { ok: true }
  | { ok: false; reason: "unavailable" | "invalid" };

export interface Store {
  mode: AppMode;
  /** `null` no modo live enquanto não houver API autenticada. */
  snapshot: Snapshot | null;
  now: Date;
  /**
   * Aplica uma gravação. No modo live recusa (`unavailable`): não existe sessão
   * mobile nem contrato de API homologado, então nada pode ser salvo de verdade.
   */
  run: (mutation: Mutation) => ActionOutcome;
}

const StoreContext = createContext<Store | null>(null);

interface StoreProviderProps {
  children: ReactNode;
  mode?: AppMode;
  /** Relógio injetável para testes; quando informado, não há atualização periódica. */
  clock?: () => Date;
  initialSnapshot?: Snapshot;
}

export function StoreProvider({
  children,
  mode = APP_MODE,
  clock,
  initialSnapshot,
}: StoreProviderProps) {
  const [now, setNow] = useState<Date>(() => (clock ? clock() : new Date()));
  const [snapshot, setSnapshot] = useState<Snapshot | null>(() =>
    mode === "preview" ? (initialSnapshot ?? buildPreviewSnapshot(now)) : null,
  );
  const snapshotRef = useRef<Snapshot | null>(snapshot);
  const nowRef = useRef<Date>(now);
  nowRef.current = now;

  useEffect(() => {
    if (clock) return undefined;
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, [clock]);

  const run = useCallback(
    (mutation: Mutation): ActionOutcome => {
      if (mode !== "preview" || snapshotRef.current === null) {
        return { ok: false, reason: "unavailable" };
      }
      const moment = clock ? clock() : new Date();
      const next = mutation(snapshotRef.current, moment);
      if (next === null) return { ok: false, reason: "invalid" };
      snapshotRef.current = next;
      setSnapshot(next);
      return { ok: true };
    },
    [mode, clock],
  );

  const value = useMemo<Store>(
    () => ({ mode, snapshot, now, run }),
    [mode, snapshot, now, run],
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
