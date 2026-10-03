import React from "react";
import { act, renderHook } from "@testing-library/react-native";
import { AppState } from "react-native";
import { useSession } from "../src/api/session";
import { LiveActionRegistry } from "../src/data/live/actions";
import { mutations } from "../src/data/mutations";
import { useStore } from "../src/data/store";
import {
  createFakeServer,
  deferred,
  FakeServer,
  Handler,
  meBody,
  networkFailure,
  tokensBody,
} from "./fakeApi";
import { Options, Providers } from "./helpers";

const ME = "/mobile/me/";
const REFRESH = "/mobile/auth/refresh/";
const LOGIN = "/mobile/auth/login/";

const settle = () =>
  act(async () => void (await jest.advanceTimersByTimeAsync(0)));

function setup(handler: Handler, options: Options = {}) {
  const server: FakeServer = createFakeServer(handler);
  const hook = renderHook(
    () => ({ store: useStore(), session: useSession() }),
    {
      wrapper: ({ children }) => (
        <Providers
          mode="live"
          signedIn
          transport={server.transport}
          {...options}
        >
          {children as React.ReactElement}
        </Providers>
      ),
    },
  );
  return { ...hook, server };
}

type AppStateListener = (state: string) => void;

function mockAppState() {
  const listeners: AppStateListener[] = [];
  const remove = jest.fn();
  jest.spyOn(AppState, "addEventListener").mockImplementation(((
    _type: string,
    listener: AppStateListener,
  ) => {
    listeners.push(listener);
    return { remove };
  }) as never);
  return {
    emit: (state: string) => listeners.forEach((listener) => listener(state)),
    remove,
  };
}

const okMe: Handler = () => ({ status: 200, body: meBody() });

describe("carregamento ao ficar ativo", () => {
  it("carrega o paciente da API assim que a sessão fica ativa", async () => {
    const gate = deferred();
    const { result, server } = setup(async () => {
      await gate.promise;
      return { status: 200, body: meBody() };
    });
    await settle();
    expect(result.current.session.status).toBe("active");
    expect(result.current.store.status).toBe("loading");
    expect(result.current.store.snapshot).toBeNull(); // nada antes da resposta
    gate.resolve();
    await settle();
    expect(result.current.store.status).toBe("ready");
    expect(result.current.store.snapshot?.patient.displayName).toBe(
      "Alex Paciente",
    );
    expect(result.current.store.snapshot?.medications).toEqual([]);
    expect(server.callsTo(ME)).toHaveLength(1);
    expect(server.callsTo(ME)[0].headers.Authorization).toBe(
      "Bearer aem_access_1",
    );
  });

  it("sem sessão ativa não há nenhuma chamada nem dado", async () => {
    const { result, server } = setup(okMe, { signedIn: false });
    await settle();
    expect(result.current.session.status).toBe("signedOut");
    expect(result.current.store.snapshot).toBeNull();
    expect(result.current.store.status).toBe("idle");
    expect(server.calls).toHaveLength(0);
  });

  it("entrar carrega os dados; sair apaga o snapshot da memória", async () => {
    const { result, server } = setup(
      (call) =>
        call.path === LOGIN
          ? { status: 200, body: tokensBody() }
          : call.path === ME
            ? { status: 200, body: meBody() }
            : { status: 204 },
      { signedIn: false },
    );
    await settle();
    await act(async () => {
      await result.current.session.login({ email: "a@b.c", password: "x" });
    });
    await settle();
    expect(result.current.store.snapshot?.patient.displayName).toBe(
      "Alex Paciente",
    );
    expect(server.callsTo(ME)).toHaveLength(1);

    await act(async () => {
      await result.current.session.logout();
    });
    // Nenhum dado clínico fica visível com a sessão encerrada.
    expect(result.current.store.snapshot).toBeNull();
    expect(result.current.store.status).toBe("idle");
    // E um novo login não mostra o paciente anterior antes de carregar.
    const run = await act(async () =>
      result.current.store.run(mutations.setLowEnergy(true)),
    );
    expect(run).toEqual({ ok: false, reason: "session" });
  });

  it("sessão perdida zera o snapshot na hora", async () => {
    let revoked = false;
    const { result } = setup((call) => {
      if (call.path === REFRESH)
        return { status: 401, body: { detail: "x", code: "invalid_token" } };
      return revoked
        ? { status: 401, body: {} }
        : { status: 200, body: meBody() };
    });
    await settle();
    expect(result.current.store.snapshot).not.toBeNull();
    revoked = true; // o servidor revogou a sessão
    await act(async () => {
      await result.current.store.refresh();
    });
    await settle();
    expect(result.current.session.status).toBe("signedOut");
    expect(result.current.session.notice).toBe("expired");
    expect(result.current.store.snapshot).toBeNull();
    expect(result.current.store.status).toBe("idle");
  });
});

describe("falhas de carregamento", () => {
  it("sem rede no primeiro carregamento: erro 'offline' e tentar de novo funciona", async () => {
    let offline = true;
    const { result } = setup(() =>
      offline ? networkFailure() : { status: 200, body: meBody() },
    );
    await settle();
    expect(result.current.store.status).toBe("error");
    expect(result.current.store.failure).toBe("offline");
    expect(result.current.store.snapshot).toBeNull();
    expect(result.current.session.status).toBe("active"); // rede ≠ sessão perdida
    offline = false;
    await act(async () => {
      await result.current.store.refresh();
    });
    expect(result.current.store.status).toBe("ready");
    expect(result.current.store.failure).toBeNull();
    expect(result.current.store.snapshot).not.toBeNull();
  });

  it("402: erro 'blocked'", async () => {
    const { result } = setup(() => ({ status: 402, body: { detail: "x" } }));
    await settle();
    expect(result.current.store.status).toBe("error");
    expect(result.current.store.failure).toBe("blocked");
  });
});

describe("primeiro plano (AppState)", () => {
  it("ao voltar ao primeiro plano recarrega, uma vez por intervalo e sem tempestade", async () => {
    const appState = mockAppState();
    const { result, server } = setup(okMe, {});
    await settle();
    expect(server.callsTo(ME)).toHaveLength(1);

    // Vai e volta várias vezes logo depois: nada de novo (intervalo de 30 s).
    for (let i = 0; i < 5; i += 1) {
      act(() => appState.emit("background"));
      act(() => appState.emit("active"));
    }
    await settle();
    expect(server.callsTo(ME)).toHaveLength(1);

    await act(async () => void (await jest.advanceTimersByTimeAsync(31_000)));
    act(() => appState.emit("background"));
    act(() => appState.emit("active"));
    act(() => appState.emit("active")); // repetido: ignorado
    await settle();
    expect(server.callsTo(ME)).toHaveLength(2);
    expect(result.current.store.status).toBe("ready");
  });

  it("remove o ouvinte ao desmontar", async () => {
    const appState = mockAppState();
    const { unmount } = setup(okMe);
    await settle();
    unmount();
    expect(appState.remove).toHaveBeenCalled();
  });
});

describe("gravações", () => {
  const actions = (calls: unknown[]): LiveActionRegistry => ({
    setLowEnergy: {
      run: (active) => async (api) => {
        calls.push(active);
        await api.put("/mobile/low-energy/", { active });
        return { ok: true };
      },
      refresh: ["patient"],
    },
  });

  it("sem ação registrada: 'unavailable' e nada vai ao servidor", async () => {
    const { result, server } = setup(okMe);
    await settle();
    server.calls.length = 0;
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: false, reason: "unavailable" });
    expect(server.calls).toHaveLength(0);
  });

  it("ação registrada: grava, recarrega a fatia e atualiza o snapshot", async () => {
    let name = "Antes";
    const calls: unknown[] = [];
    const { result, server } = setup(
      (call) =>
        call.path === ME
          ? { status: 200, body: meBody({ display_name: name }) }
          : (name = "Depois") && { status: 204 },
      { actions: actions(calls) },
    );
    await settle();
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: true });
    expect(calls).toEqual([true]);
    expect(server.callsTo(ME)).toHaveLength(2);
    expect(result.current.store.snapshot?.patient.displayName).toBe("Depois");
  });

  it("sem rede: 'offline' e o snapshot continua como estava", async () => {
    let offline = false;
    const { result } = setup(
      (call) => {
        if (offline && call.path !== ME) return networkFailure();
        return call.path === ME
          ? { status: 200, body: meBody() }
          : { status: 204 };
      },
      { actions: actions([]) },
    );
    await settle();
    const before = result.current.store.snapshot;
    offline = true;
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: false, reason: "offline" });
    expect(result.current.store.snapshot).toBe(before);
  });

  it("rejeitado (4xx) traz o code; 402 vira 'blocked'", async () => {
    let status = 422;
    const { result } = setup(
      (call) =>
        call.path === ME
          ? { status: 200, body: meBody() }
          : {
              status,
              body: {
                detail: "x",
                code: status === 422 ? "invalid_intensity" : "",
              },
            },
      { actions: actions([]) },
    );
    await settle();
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({
      ok: false,
      reason: "rejected",
      code: "invalid_intensity",
    });
    status = 402;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toMatchObject({ ok: false, reason: "blocked" });
  });

  it("toque duplo: a mesma gravação em voo vira uma só", async () => {
    const gate = deferred();
    const calls: unknown[] = [];
    const { result, server } = setup(
      async (call) => {
        if (call.path === "/mobile/low-energy/") {
          await gate.promise;
          return { status: 204 };
        }
        return { status: 200, body: meBody() };
      },
      { actions: actions(calls) },
    );
    await settle();
    let both: unknown;
    await act(async () => {
      const first = result.current.store.run(mutations.setLowEnergy(true));
      const second = result.current.store.run(mutations.setLowEnergy(true));
      gate.resolve();
      both = await Promise.all([first, second]);
    });
    expect(both).toEqual([{ ok: true }, { ok: true }]);
    expect(server.callsTo("/mobile/low-energy/")).toHaveLength(1);
  });

  it("sessão perdida durante a gravação: 'session' (e o app volta para a entrada)", async () => {
    let lost = false;
    const { result } = setup(
      (call) => {
        if (call.path === REFRESH) return { status: 401, body: {} };
        if (lost) return { status: 401, body: {} };
        return { status: 200, body: meBody() };
      },
      { actions: actions([]) },
    );
    await settle();
    lost = true;
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.store.run(mutations.setLowEnergy(true));
    });
    expect(outcome).toEqual({ ok: false, reason: "session" });
    await settle();
    expect(result.current.session.status).toBe("signedOut");
    expect(result.current.store.snapshot).toBeNull();
  });
});
