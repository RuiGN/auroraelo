import React from "react";
import { renderHook, act } from "@testing-library/react-native";
import { resolveAppMode } from "../src/config";
import { mutations } from "../src/data/mutations";
import { StoreProvider, useStore } from "../src/data/store";
import { NOW } from "./helpers";

function setup(mode: "live" | "preview") {
  return renderHook(() => useStore(), {
    wrapper: ({ children }) => (
      <StoreProvider mode={mode} clock={() => NOW}>
        {children}
      </StoreProvider>
    ),
  });
}

describe("modo de operação", () => {
  it("o padrão é 'live': demonstração só quando pedida explicitamente", () => {
    expect(resolveAppMode(undefined)).toBe("live");
    expect(resolveAppMode("")).toBe("live");
    expect(resolveAppMode("production")).toBe("live");
    expect(resolveAppMode("PREVIEW")).toBe("live");
    expect(resolveAppMode("preview")).toBe("preview");
  });
});

describe("store em modo live (sem API autenticada)", () => {
  it("não expõe nenhum dado clínico", () => {
    const { result } = setup("live");
    expect(result.current.mode).toBe("live");
    expect(result.current.snapshot).toBeNull();
  });

  it("recusa toda gravação em vez de fingir sucesso", () => {
    const { result } = setup("live");
    let outcome: ReturnType<typeof result.current.run> | undefined;
    act(() => {
      outcome = result.current.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: false, reason: "unavailable" });
    expect(result.current.snapshot).toBeNull();
  });
});

describe("store em modo preview", () => {
  it("carrega dados sintéticos e aplica gravações só na memória", () => {
    const { result } = setup("preview");
    expect(result.current.snapshot?.patient.displayName).toBe("Alex Exemplo");
    let outcome: ReturnType<typeof result.current.run> | undefined;
    act(() => {
      outcome = result.current.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: true });
    expect(result.current.snapshot?.lowEnergy.active).toBe(true);
  });

  it("devolve 'invalid' sem alterar nada quando a mutação recusa a entrada", () => {
    const { result } = setup("preview");
    const before = result.current.snapshot;
    let outcome: ReturnType<typeof result.current.run> | undefined;
    act(() => {
      outcome = result.current.run(
        mutations.addJournalEntry({
          mood: 3,
          emotions: [],
          intensity: 3,
          context: "   ",
          triggers: "",
          reactions: "",
          strategies: "",
          visibility: "private",
        }),
      );
    });
    expect(outcome).toEqual({ ok: false, reason: "invalid" });
    expect(result.current.snapshot).toBe(before);
  });

  it("encadeia gravações consecutivas sobre o estado mais recente", () => {
    const { result } = setup("preview");
    act(() => {
      result.current.run(mutations.setCounterHidden(true));
      result.current.run(mutations.restartCounter());
    });
    expect(result.current.snapshot?.sobriety).toMatchObject({
      hideCounter: true,
      restartCount: 1,
    });
  });
});
