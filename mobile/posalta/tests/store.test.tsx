import React from "react";
import { act, renderHook } from "@testing-library/react-native";
import { resolveAppMode } from "../src/config";
import { mutations } from "../src/data/mutations";
import { useStore } from "../src/data/store";
import { Options, Providers } from "./helpers";

function setup(options: Options) {
  return renderHook(() => useStore(), {
    wrapper: ({ children }) => (
      <Providers {...options}>{children as React.ReactElement}</Providers>
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

describe("store em modo live sem servidor configurado", () => {
  it("não expõe nenhum dado clínico e fica ocioso", () => {
    const { result } = setup({ mode: "live" });
    expect(result.current.mode).toBe("live");
    expect(result.current.snapshot).toBeNull();
    expect(result.current.status).toBe("idle");
    expect(result.current.failure).toBeNull();
  });

  it("recusa toda gravação em vez de fingir sucesso", async () => {
    const { result } = setup({ mode: "live" });
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: false, reason: "unavailable" });
    expect(result.current.snapshot).toBeNull();
  });

  it("refresh não faz nada (e não rejeita)", async () => {
    const { result } = setup({ mode: "live" });
    await act(async () => {
      await expect(result.current.refresh()).resolves.toBeUndefined();
    });
  });
});

describe("store em modo preview", () => {
  it("carrega dados sintéticos e aplica gravações só na memória", async () => {
    const { result } = setup({ mode: "preview" });
    expect(result.current.snapshot?.patient.displayName).toBe("Alex Exemplo");
    expect(result.current.status).toBe("ready");
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: true });
    expect(result.current.snapshot?.lowEnergy.active).toBe(true);
  });

  it("devolve uma promessa já resolvida: o preview responde na hora", async () => {
    const { result } = setup({ mode: "preview" });
    await act(async () => {
      const outcome = result.current.run(mutations.setLowEnergy(true));
      expect(outcome).toBeInstanceOf(Promise);
      expect(await outcome).toEqual({ ok: true });
    });
  });

  it("devolve 'invalid' sem alterar nada quando a mutação recusa a entrada", async () => {
    const { result } = setup({ mode: "preview" });
    const before = result.current.snapshot;
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.run(
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

  it("encadeia gravações consecutivas sobre o estado mais recente", async () => {
    const { result } = setup({ mode: "preview" });
    await act(async () => {
      await Promise.all([
        result.current.run(mutations.setCounterHidden(true)),
        result.current.run(mutations.restartCounter()),
      ]);
    });
    expect(result.current.snapshot?.sobriety).toMatchObject({
      hideCounter: true,
      restartCount: 1,
    });
  });

  it("não usa sessão nem rede", async () => {
    const transport = jest.fn();
    const { result } = setup({ mode: "preview", transport });
    await act(async () => {
      await result.current.refresh();
    });
    expect(transport).not.toHaveBeenCalled();
  });
});
