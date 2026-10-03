import { Api, createApiClient } from "../src/api/client";
import { ApiError } from "../src/api/errors";
import { createMemoryTokenStore } from "../src/api/tokenStore";
import { LiveActionRegistry } from "../src/data/live/actions";
import { emptySnapshotFor } from "../src/data/live/empty";
import { createLiveEngine, LiveEngine } from "../src/data/live/engine";
import { parsePatientSummary, patientLoader } from "../src/data/live/patient";
import {
  LoaderEntry,
  LOADERS,
  SNAPSHOT_SLICES,
  unwiredSlices,
} from "../src/data/live/registry";
import { mutations } from "../src/data/mutations";
import {
  BASE_URL,
  createFakeServer,
  deferred,
  FakeServer,
  Handler,
  meBody,
  networkFailure,
  storedSession,
} from "./fakeApi";

async function liveApi(handler: Handler) {
  const server = createFakeServer(handler);
  const client = createApiClient({
    baseUrl: BASE_URL,
    transport: server.transport,
    tokenStore: createMemoryTokenStore(),
  });
  await client.setSession(storedSession(1));
  return { api: client as Api, server };
}

const ME = "/mobile/me/";
const okMe: Handler = () => ({ status: 200, body: meBody() });

async function engineWith(
  handler: Handler,
  options: {
    loaders?: readonly LoaderEntry[];
    actions?: LiveActionRegistry;
    now?: () => number;
  } = {},
): Promise<{ engine: LiveEngine; server: FakeServer; api: Api }> {
  const { api, server } = await liveApi(handler);
  const engine = createLiveEngine({
    api,
    loaders: options.loaders ?? [patientLoader],
    actions: options.actions ?? {},
    now: options.now,
  });
  return { engine, server, api };
}

describe("carregamento (loaders)", () => {
  it("carrega o paciente de GET /mobile/me/ e deixa o resto vazio e seguro", async () => {
    const { engine, server } = await engineWith(okMe);
    expect(engine.getState()).toEqual({
      snapshot: null,
      status: "idle",
      failure: null,
    });
    await engine.refresh();
    const state = engine.getState();
    expect(state.status).toBe("ready");
    expect(state.failure).toBeNull();
    expect(server.callsTo(ME)).toHaveLength(1);
    expect(server.callsTo(ME)[0].method).toBe("GET");
    expect(state.snapshot?.patient).toEqual({
      id: "33333333-3333-4333-8333-333333333333",
      displayName: "Alex Paciente",
      clinicName: "Clínica Aurora",
      dischargeDate: "2026-09-23",
      timezone: "America/Sao_Paulo",
      careTeam: [
        {
          id: "44444444-4444-4444-8444-444444444444",
          name: "Dra. Helena",
          role: "psychiatrist",
        },
      ],
    });
    // Fatias sem loader: vazias, nunca inventadas.
    expect(state.snapshot).toEqual(emptySnapshotFor(state.snapshot!.patient));
    expect(state.snapshot?.medications).toEqual([]);
    expect(state.snapshot?.lowEnergy).toEqual({
      actions: [],
      active: false,
      startedAt: null,
    });
    expect(state.snapshot?.sobriety).toBeNull();
  });

  it("tolera alta sem data, fuso ausente e papel desconhecido da equipe", () => {
    const patient = parsePatientSummary(
      meBody({
        discharge_date: null,
        timezone: "",
        care_team: [
          { id: "t1", name: "Fulano", role: "enfermeiro-chefe" },
          { id: "t2", name: "Sicrana", role: "psychologist" },
        ],
      }),
    );
    expect(patient.dischargeDate).toBeNull();
    expect(patient.timezone).toBe("America/Sao_Paulo");
    expect(patient.careTeam.map((member) => member.role)).toEqual([
      "other",
      "psychologist",
    ]);
  });

  it.each([
    { name: "sem id", body: meBody({ id: undefined }) },
    { name: "nome vazio", body: meBody({ display_name: "  " }) },
    { name: "data inválida", body: meBody({ discharge_date: "23/09/2026" }) },
    { name: "equipe fora do formato", body: meBody({ care_team: "x" }) },
    { name: "não é objeto", body: [] },
  ])(
    "resposta malformada ($name) vira erro, sem snapshot",
    async ({ body }) => {
      const { engine } = await engineWith(() => ({ status: 200, body }));
      await engine.refresh();
      expect(engine.getState()).toMatchObject({
        snapshot: null,
        status: "error",
        failure: "unexpected",
      });
    },
  );

  it("sem rede: erro 'offline'; depois de carregar, a falha mantém os dados antigos", async () => {
    let offline = true;
    const { engine } = await engineWith(() =>
      offline ? networkFailure() : { status: 200, body: meBody() },
    );
    await engine.refresh();
    expect(engine.getState()).toMatchObject({
      snapshot: null,
      status: "error",
      failure: "offline",
    });
    offline = false;
    await engine.refresh();
    expect(engine.getState().status).toBe("ready");
    const before = engine.getState().snapshot;
    offline = true;
    await engine.refresh();
    expect(engine.getState()).toMatchObject({
      status: "error",
      failure: "offline",
    });
    expect(engine.getState().snapshot).toBe(before); // dados antigos continuam
  });

  it("402 vira falha 'blocked'", async () => {
    const { engine } = await engineWith(() => ({
      status: 402,
      body: { detail: "x" },
    }));
    await engine.refresh();
    expect(engine.getState()).toMatchObject({
      status: "error",
      failure: "blocked",
    });
  });

  it("chamadas simultâneas de refresh compartilham a mesma requisição", async () => {
    const gate = deferred();
    const { engine, server } = await engineWith(async () => {
      await gate.promise;
      return { status: 200, body: meBody() };
    });
    const all = Promise.all([
      engine.refresh(),
      engine.refresh(),
      engine.refresh(),
    ]);
    expect(engine.getState().status).toBe("loading");
    gate.resolve();
    await all;
    expect(server.callsTo(ME)).toHaveLength(1);
    expect(engine.getState().status).toBe("ready");
  });

  it("refreshIfStale: no máximo uma vez por intervalo e nunca com carga em andamento", async () => {
    let clock = 1_000_000;
    const { engine, server } = await engineWith(okMe, { now: () => clock });
    await engine.refreshIfStale(); // primeira vez
    await engine.refreshIfStale(); // logo em seguida: ignorada
    clock += 10_000;
    await engine.refreshIfStale(); // ainda dentro dos 30 s
    expect(server.callsTo(ME)).toHaveLength(1);
    clock += 25_000;
    const first = engine.refreshIfStale();
    const second = engine.refreshIfStale(); // com a primeira em andamento
    await Promise.all([first, second]);
    expect(server.callsTo(ME)).toHaveLength(2);
  });

  it("um resultado mais antigo nunca sobrescreve um mais novo", async () => {
    const slow = deferred<{ displayName: string }>();
    let calls = 0;
    const loader: LoaderEntry = {
      slices: ["patient"],
      load: async () => {
        calls += 1;
        const result =
          calls === 1 ? await slow.promise : { displayName: "Novo" };
        return {
          patient: { ...emptyPatient(), displayName: result.displayName },
        };
      },
    };
    const { engine } = await engineWith(okMe, { loaders: [loader] });
    const stale = engine.refresh();
    await engine.refresh(undefined, { force: true }); // mais nova, termina antes
    slow.resolve({ displayName: "Antigo" });
    await stale;
    expect(engine.getState().snapshot?.patient.displayName).toBe("Novo");
  });

  it("falha de um loader não impede os outros; cada um só altera as suas fatias", async () => {
    const meds: LoaderEntry = {
      slices: ["medications"],
      load: async () => {
        throw new ApiError(0, "network");
      },
    };
    const goals: LoaderEntry = {
      slices: ["goals"],
      // `journal` não foi declarada: é descartada.
      load: async () => ({ goals: [], journal: [{ id: "x" } as never] }),
    };
    const { engine } = await engineWith(okMe, {
      loaders: [patientLoader, meds, goals],
    });
    await engine.refresh();
    const state = engine.getState();
    expect(state.status).toBe("error");
    expect(state.failure).toBe("offline");
    expect(state.snapshot?.patient.displayName).toBe("Alex Paciente");
    expect(state.snapshot?.journal).toEqual([]);
    expect(state.snapshot?.medications).toEqual([]);
  });

  it("refresh(['fatia']) recarrega só os loaders dessa fatia", async () => {
    const goalsLoad = jest.fn(async () => ({ goals: [] }));
    const goals: LoaderEntry = { slices: ["goals"], load: goalsLoad };
    const { engine, server } = await engineWith(okMe, {
      loaders: [patientLoader, goals],
    });
    await engine.refresh();
    await engine.refresh(["goals"]);
    expect(goalsLoad).toHaveBeenCalledTimes(2);
    expect(server.callsTo(ME)).toHaveLength(1);
  });

  it("notifica quem assinou e não publica mais depois de dispose()", async () => {
    const { engine } = await engineWith(okMe);
    const listener = jest.fn();
    engine.subscribe(listener);
    await engine.refresh();
    expect(listener).toHaveBeenCalled();
    listener.mockClear();
    engine.dispose();
    await engine.refresh();
    expect(listener).not.toHaveBeenCalled();
    expect(await engine.run(mutations.setLowEnergy(true))).toEqual({
      ok: false,
      reason: "unavailable",
    });
  });
});

function emptyPatient() {
  return parsePatientSummary(meBody());
}

describe("registro de loaders", () => {
  it("todas as fatias do Snapshot têm loader (nenhum domínio ficou sem ligar)", () => {
    expect(LOADERS).toContain(patientLoader);
    expect(unwiredSlices()).toEqual([]);
  });

  it("cada fatia pertence a um único loader e só a fatias que existem", () => {
    const seen = new Map<string, number>();
    for (const entry of LOADERS) {
      for (const slice of entry.slices) {
        seen.set(slice, (seen.get(slice) ?? 0) + 1);
        expect(SNAPSHOT_SLICES).toContain(slice);
      }
    }
    for (const count of seen.values()) expect(count).toBe(1);
  });

  it("a lista de fatias acompanha o Snapshot e o valor vazio cobre todas", () => {
    const empty = emptySnapshotFor(parsePatientSummary(meBody()));
    expect(Object.keys(empty).sort()).toEqual([...SNAPSHOT_SLICES].sort());
  });
});

describe("gravações (ações)", () => {
  const lowEnergyAction = (
    run: jest.Mock,
    refresh: LiveActionRegistry["setLowEnergy"] extends infer A
      ? A extends { refresh: infer R }
        ? R
        : never
      : never = ["patient"],
  ): LiveActionRegistry => ({
    setLowEnergy: { run: (input) => (api) => run(input, api), refresh },
  });

  it("sem ação registrada nunca finge sucesso: 'unavailable', sem tocar a rede", async () => {
    const { engine, server } = await engineWith(okMe);
    await engine.refresh();
    server.calls.length = 0;
    const outcome = await engine.run(mutations.setLowEnergy(true));
    expect(outcome).toEqual({ ok: false, reason: "unavailable" });
    expect(server.calls).toHaveLength(0);
    // Mutação sem metadados (função solta) também é recusada.
    expect(await engine.run(() => null)).toEqual({
      ok: false,
      reason: "unavailable",
    });
  });

  it("ação ok: recebe a entrada tipada, recarrega as fatias indicadas e atualiza o snapshot", async () => {
    let name = "Antes";
    const { engine, server } = await engineWith(
      (call) =>
        call.path === ME
          ? { status: 200, body: meBody({ display_name: name }) }
          : { status: 204 },
      {
        actions: {
          setLowEnergy: {
            run: (active) => async (api) => {
              await api.put("/mobile/low-energy/", { active });
              name = "Depois";
              return { ok: true };
            },
            refresh: ["patient"],
          },
        },
      },
    );
    await engine.refresh();
    expect(engine.getState().snapshot?.patient.displayName).toBe("Antes");
    const outcome = await engine.run(mutations.setLowEnergy(true));
    expect(outcome).toEqual({ ok: true });
    expect(server.callsTo("/mobile/low-energy/")[0].body).toEqual({
      active: true,
    });
    expect(server.callsTo(ME)).toHaveLength(2);
    expect(engine.getState().snapshot?.patient.displayName).toBe("Depois");
  });

  it("falha de rede: 'offline', snapshot intacto e sem recarregar", async () => {
    const run = jest.fn(async () => {
      throw new ApiError(0, "network");
    });
    const { engine, server } = await engineWith(okMe, {
      actions: lowEnergyAction(run),
    });
    await engine.refresh();
    const before = engine.getState().snapshot;
    const outcome = await engine.run(mutations.setLowEnergy(true));
    expect(outcome).toEqual({ ok: false, reason: "offline" });
    expect(engine.getState().snapshot).toBe(before);
    expect(server.callsTo(ME)).toHaveLength(1);
  });

  it.each([
    {
      name: "4xx com code",
      error: new ApiError(422, "invalid_intensity"),
      outcome: { ok: false, reason: "rejected", code: "invalid_intensity" },
    },
    {
      name: "404",
      error: new ApiError(404, "not_found"),
      outcome: { ok: false, reason: "rejected", code: "not_found" },
    },
    {
      name: "402",
      error: new ApiError(402, "clinic_blocked"),
      outcome: { ok: false, reason: "blocked", code: "clinic_blocked" },
    },
    {
      name: "sessão perdida",
      error: new ApiError(401, "session_lost"),
      outcome: { ok: false, reason: "session" },
    },
    {
      name: "sessão trocada",
      error: new ApiError(0, "session_changed"),
      outcome: { ok: false, reason: "session" },
    },
    {
      name: "tempo esgotado",
      error: new ApiError(0, "timeout"),
      outcome: { ok: false, reason: "offline" },
    },
    {
      name: "5xx",
      error: new ApiError(503, "server_error"),
      outcome: { ok: false, reason: "unavailable", code: "server_error" },
    },
    {
      name: "erro inesperado",
      error: new TypeError("bug"),
      outcome: { ok: false, reason: "unavailable", code: "unexpected" },
    },
  ])(
    "erro de ação ($name) vira o resultado certo",
    async ({ error, outcome }) => {
      const run = jest.fn(async () => {
        throw error;
      });
      const { engine } = await engineWith(okMe, {
        actions: lowEnergyAction(run),
      });
      expect(await engine.run(mutations.setLowEnergy(true))).toEqual(outcome);
    },
  );

  it("a ação pode recusar a entrada sem ir ao servidor ('invalid')", async () => {
    const run = jest.fn(async () => ({
      ok: false as const,
      reason: "invalid" as const,
      code: "invalid_intensity",
    }));
    const { engine, server } = await engineWith(okMe, {
      actions: lowEnergyAction(run),
    });
    expect(await engine.run(mutations.setLowEnergy(true))).toEqual({
      ok: false,
      reason: "invalid",
      code: "invalid_intensity",
    });
    expect(server.calls).toHaveLength(0);
  });

  it("recarregar depois do sucesso falhar não desfaz a gravação", async () => {
    let offline = false;
    const run = jest.fn(async () => ({ ok: true as const }));
    const { engine } = await engineWith(
      () => (offline ? networkFailure() : { status: 200, body: meBody() }),
      { actions: lowEnergyAction(run) },
    );
    await engine.refresh();
    offline = true;
    expect(await engine.run(mutations.setLowEnergy(true))).toEqual({
      ok: true,
    });
    expect(engine.getState().status).toBe("error");
  });

  it("trava de duplicidade: mesma ação + mesma entrada em voo vira uma só", async () => {
    const gate = deferred();
    const run = jest.fn(async (_input: unknown, _api: Api) => {
      await gate.promise;
      return { ok: true as const };
    });
    const { engine } = await engineWith(okMe, {
      actions: lowEnergyAction(run),
    });
    const first = engine.run(mutations.setLowEnergy(true));
    const second = engine.run(mutations.setLowEnergy(true)); // toque duplo
    const other = engine.run(mutations.setLowEnergy(false)); // entrada diferente
    gate.resolve();
    expect(await Promise.all([first, second, other])).toEqual([
      { ok: true },
      { ok: true },
      { ok: true },
    ]);
    expect(run).toHaveBeenCalledTimes(2);
    // Terminada a primeira, a mesma gravação pode ser feita de novo.
    await engine.run(mutations.setLowEnergy(true));
    expect(run).toHaveBeenCalledTimes(3);
  });

  it("a trava ignora a ordem das chaves do objeto de entrada", async () => {
    const gate = deferred();
    const run = jest.fn(async () => {
      await gate.promise;
      return { ok: true as const };
    });
    const { engine } = await engineWith(okMe, {
      actions: {
        logDose: { run: () => run, refresh: [] },
      },
    });
    const first = engine.run(
      mutations.logDose({
        medicationId: "m1",
        scheduledFor: "2026-10-02T08:00:00-03:00",
        status: "taken",
      }),
    );
    const second = engine.run(
      mutations.logDose({
        status: "taken",
        scheduledFor: "2026-10-02T08:00:00-03:00",
        medicationId: "m1",
      }),
    );
    gate.resolve();
    await Promise.all([first, second]);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("a trava é liberada mesmo quando a ação falha", async () => {
    const run = jest.fn(async () => {
      throw new ApiError(0, "network");
    });
    const { engine } = await engineWith(okMe, {
      actions: lowEnergyAction(run),
    });
    await engine.run(mutations.setLowEnergy(true));
    await engine.run(mutations.setLowEnergy(true));
    expect(run).toHaveBeenCalledTimes(2);
  });
});
