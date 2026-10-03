/**
 * Roteiro ponta a ponta: o MESMO código do app (cliente, sessão, loaders, ações) contra o
 * Django em execução, com dados cadastrados pelos serviços de domínio que as telas da
 * equipe usam. Não faz parte de `npm test` (precisa do servidor): ver README.
 *
 * Variáveis: E2E_BASE_URL, E2E_OUT (pasta com seed.json), E2E_PROJECT (raiz do web),
 * E2E_SQLITE (banco do servidor) e E2E_PY (python do web).
 */
import { execFileSync } from "child_process";
import * as fs from "fs";
import * as http from "http";
import { Api, createApiClient, Transport } from "../../src/api/client";
import { isApiError } from "../../src/api/errors";
import { createMemoryTokenStore } from "../../src/api/tokenStore";
import { parseTokens } from "../../src/api/types";
import { LIVE_ACTIONS } from "../../src/data/live/actions";
import { createLiveEngine, LiveEngine } from "../../src/data/live/engine";
import { LOADERS } from "../../src/data/live/registry";
import { mutations } from "../../src/data/mutations";
import { combineDateTime, addDays, toISODate } from "../../src/domain/logic";

const BASE = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8765";
const OUT = process.env.E2E_OUT as string;
const PROJECT = process.env.E2E_PROJECT as string;
const PASSWORD = "E2e-Senha-Sintetica-2026!"; // credencial sintética do banco descartável

const seed = JSON.parse(fs.readFileSync(`${OUT}/seed.json`, "utf8"));

const nodeTransport: Transport = (input, init) =>
  new Promise((resolve, reject) => {
    const { URL } = require("url");
    const url = new URL(input);
    const request = http.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname + url.search,
        method: init.method,
        headers: {
          ...(init.headers as Record<string, string>),
          // O runserver do Django não lê corpo "chunked": o fetch real manda o tamanho.
          ...(typeof init.body === "string"
            ? { "Content-Length": String(Buffer.byteLength(init.body)) }
            : {}),
        },
      },
      (response) => {
        let raw = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => (raw += chunk));
        response.on("end", () =>
          resolve({
            status: response.statusCode ?? 0,
            url: input,
            headers: {
              get: (name) => {
                const value = response.headers[name.toLowerCase()];
                return Array.isArray(value) ? value[0] : (value ?? null);
              },
            },
            json: async () => JSON.parse(raw),
          }),
        );
      },
    );
    request.on("error", reject);
    if (typeof init.body === "string") request.write(init.body);
    request.end();
  });

let client: ReturnType<typeof createApiClient>;
let activated: ReturnType<typeof parseTokens>;
let engine: LiveEngine;

const snapshot = () => {
  const value = engine.getState().snapshot;
  if (!value) throw new Error("sem snapshot");
  return value;
};

const ok = { ok: true };

describe("roteiro ponta a ponta contra o servidor real", () => {
  it("1. ativa a conta com o código do convite e abre a sessão", async () => {
    client = createApiClient({
      baseUrl: BASE,
      transport: nodeTransport,
      tokenStore: createMemoryTokenStore(),
      dev: true,
    });
    const session = await client.post(
      "/mobile/auth/activate/",
      {
        code: seed.code,
        password: PASSWORD,
        first_name: "Alex",
        last_name: "Exemplo",
        device_label: "Roteiro E2E",
        platform: "ios",
        app_version: "1.0.0",
      },
      { auth: false, parse: parseTokens },
    );
    activated = session;
    await client.setSession(session);
    expect(session.patient.displayName).toContain("Alex");
    engine = createLiveEngine({
      api: client as Api,
      loaders: LOADERS,
      actions: LIVE_ACTIONS,
    });
  });

  it("2. cada loader lê e valida a resposta real do servidor", async () => {
    const problems: string[] = [];
    for (const entry of LOADERS) {
      try {
        await entry.load(client as Api);
      } catch (error) {
        problems.push(
          `${entry.slices.join(",")}: ${
            isApiError(error) ? `${error.status} ${error.code}` : String(error)
          }`,
        );
      }
    }
    expect(problems).toEqual([]);
  });

  it("3. o snapshot traz o que a equipe cadastrou", async () => {
    await engine.refresh(undefined, { force: true });
    expect(engine.getState().failure).toBeNull();
    const s = snapshot();
    expect(s.patient.displayName).toContain("Alex");
    expect(s.medications.map((m) => m.name)).toContain("Sertralina");
    expect(s.carePlan?.title).toBe("Plano de cuidado pós-alta");
    expect(s.carePlan?.actions.length).toBe(2);
    expect(s.habits.map((h) => h.title)).toContain("Beber água");
    expect(s.exercises.length).toBeGreaterThan(0);
    expect(s.services.length).toBeGreaterThan(0);
    expect(s.services[0].freeSlots.length).toBeGreaterThan(0);
    expect(s.content.length).toBe(2);
    const mandatory = s.consents.filter((c) => c.mandatory);
    expect(mandatory.length).toBe(1);
    expect(mandatory[0]).toMatchObject({ status: "pending" });
    expect(mandatory[0].content).toContain("termos de uso");
  });

  it("4. aceite obrigatório: decide os documentos pendentes", async () => {
    for (const consent of snapshot().consents.filter(
      (c) => c.status === "pending",
    )) {
      expect(
        await engine.run(
          mutations.setConsent({ id: consent.id, granted: true }),
        ),
      ).toEqual(ok);
    }
    expect(
      snapshot().consents.filter((c) => c.mandatory && c.status === "pending"),
    ).toEqual([]);
  });

  it("5. depois da ativação: meta, registro compartilhável e pedido de acesso", async () => {
    execFileSync(process.env.E2E_PY as string, [`${OUT}/seed2.py`], {
      cwd: PROJECT,
      env: {
        ...process.env,
        DJANGO_SETTINGS_MODULE: "config.settings.test",
        SQLITE_NAME: process.env.E2E_SQLITE,
        E2E_OUT: OUT,
      },
      stdio: "pipe",
    });
    await engine.refresh(undefined, { force: true });
    const s = snapshot();
    expect(s.goals.map((g) => g.title)).toContain("Caminhar três vezes");
    expect(s.accessRequests.length).toBe(1);
    expect(s.accessRequests[0].purpose).toContain("sessão");
    // a indicação da equipe vem primeiro
    expect(s.content[0].recommendedByName).not.toBeNull();
  });

  it("6. cuidado: dose, plano, hábito, exercício e pouca energia", async () => {
    const s = snapshot();
    const now = new Date();
    const yesterday = addDays(toISODate(now), -1);
    const outcomes = {
      dose: await engine.run(
        mutations.logDose({
          medicationId: s.medications[0].id,
          scheduledFor: combineDateTime(yesterday, "08:00"),
          status: "taken",
        }),
      ),
      plan: await engine.run(
        mutations.respondCarePlan({
          decision: "accepted",
          notes: "Combinado.",
        }),
      ),
      habit: await engine.run(
        mutations.setHabitStatus({
          habitId: s.habits[0].id,
          date: toISODate(now),
          status: "completed",
        }),
      ),
      exercise: await engine.run(
        mutations.completeExercise({
          id: s.exercises[0].id,
          response: "Fiz o registro.",
          visibility: "private",
        }),
      ),
      actions: await engine.run(
        mutations.setLowEnergyActions(["Beber água", "Respirar fundo"]),
      ),
      lowEnergy: await engine.run(mutations.setLowEnergy(true)),
    };
    expect(outcomes).toEqual({
      dose: ok,
      plan: ok,
      habit: ok,
      exercise: ok,
      actions: ok,
      lowEnergy: ok,
    });
    const after = snapshot();
    expect(after.doseLogs.length).toBe(1);
    expect(after.carePlan?.response?.decision).toBe("accepted");
    expect(after.habitChecks.length).toBe(1);
    expect(after.exercises[0].status).toBe("completed");
    expect(after.lowEnergy).toMatchObject({ active: true });
    expect(after.lowEnergy.actions).toEqual(["Beber água", "Respirar fundo"]);
    // desfazer a dose
    expect(
      await engine.run(
        mutations.undoDose({
          medicationId: s.medications[0].id,
          scheduledFor: combineDateTime(yesterday, "08:00"),
        }),
      ),
    ).toEqual(ok);
    expect(snapshot().doseLogs.length).toBe(0);
  });

  it("7. diário, recuperação e metas", async () => {
    const answers = {
      general_state: 3,
      anxiety: 2,
      sadness: 2,
      irritability: 1,
      energy: 3,
      sleep_quality: 3,
      motivation: 4,
    } as const;
    const goal = snapshot().goals[0];
    const access = snapshot().accessRequests[0];
    const outcomes = [
      await engine.run(
        mutations.submitCheckIn({
          answers: answers as never,
          notes: "Dia calmo.",
          visibility: "shareable",
        }),
      ),
      await engine.run(
        mutations.addJournalEntry({
          mood: 4,
          emotions: ["calm", "hope"],
          intensity: 2,
          context: "Um bom dia.",
          triggers: "",
          reactions: "",
          strategies: "",
          visibility: "private",
        }),
      ),
      await engine.run(
        mutations.setupSobriety({
          goalType: "reduction",
          focus: "Álcool",
          referenceDate: addDays(toISODate(new Date()), -5),
          motivations: "Estar presente.",
          hideCounter: false,
        }),
      ),
      await engine.run(
        mutations.addCraving({
          intensity: 6,
          triggersContext: "Fim do dia.",
          copingStrategyUsed: "Caminhei.",
        }),
      ),
      await engine.run(mutations.setCounterHidden(true)),
      await engine.run(mutations.restartCounter()),
      await engine.run(
        mutations.toggleGoalStep({ goalId: goal.id, stepId: goal.steps[0].id }),
      ),
      await engine.run(
        mutations.setGoalStatus({ goalId: goal.id, status: "paused" }),
      ),
      await engine.run(
        mutations.respondAccessRequest({ id: access.id, approve: true }),
      ),
    ];
    expect(outcomes).toEqual(outcomes.map(() => ok));
    const s = snapshot();
    expect(s.checkIns.length).toBe(1);
    expect(s.journal.length).toBeGreaterThanOrEqual(1);
    expect(s.sobriety).toMatchObject({ focus: "Álcool", hideCounter: true });
    expect(s.sobriety?.restartCount).toBe(1);
    expect(s.cravings.length).toBe(1);
    expect(s.goals[0].status).toBe("paused");
    expect(s.goals[0].steps[0].isDone).toBe(true);
    expect(s.accessRequests).toEqual([]);
  });

  it("8. agenda: pedir, cancelar, pedir de novo e remarcar", async () => {
    const option = snapshot().services[0];
    expect(
      await engine.run(
        mutations.requestAppointment({
          serviceId: option.id,
          slot: option.freeSlots[0],
        }),
      ),
    ).toEqual(ok);
    let appointment = snapshot().appointments[0];
    expect(appointment.status).toBe("requested");
    expect(appointment.professionalName).not.toBe("");
    expect(
      await engine.run(
        mutations.cancelAppointment({ id: appointment.id, reason: "Viagem" }),
      ),
    ).toEqual(ok);
    expect(snapshot().appointments[0].status).toBe("canceled");
    // o mesmo horário volta a ficar livre e pode ser pedido de novo
    const again = snapshot().services[0];
    expect(again.freeSlots).toContain(option.freeSlots[0]);
    expect(
      await engine.run(
        mutations.requestAppointment({
          serviceId: again.id,
          slot: again.freeSlots[0],
        }),
      ),
    ).toEqual(ok);
    appointment = snapshot().appointments.find(
      (a) => a.status === "requested",
    )!;
    const other = snapshot().services[0].freeSlots[3];
    expect(
      await engine.run(
        mutations.requestReschedule({ id: appointment.id, slot: other }),
      ),
    ).toEqual(ok);
    const moved = snapshot().appointments.find((a) => a.id === appointment.id)!;
    expect(moved.status).toBe("reschedule_requested");
    expect(moved.startAt).toBe(new Date(other).toISOString());
  });

  it("9. conteúdo pessoal: plano de recaída, plano urgente e contatos", async () => {
    const outcomes = [
      await engine.run(
        mutations.saveRelapsePlan({
          title: "Meu plano",
          sections: [
            {
              type: "triggers",
              title: "Gatilhos",
              content: "Fim do expediente",
            },
            {
              type: "protective_factors",
              title: "O que me protege",
              content: "Caminhar",
            },
          ],
        }),
      ),
      await engine.run(
        mutations.saveUrgentPlan({
          personalInstructions: "Respirar e ligar para alguém.",
          calmingStrategies: ["Caminhar", "Água gelada"],
        }),
      ),
      await engine.run(
        mutations.saveUrgentContact({
          name: "Marta",
          relationship: "Mãe",
          phone: "+55 11 99999-0000",
          messageTemplate: "",
        }),
      ),
    ];
    expect(outcomes).toEqual(outcomes.map(() => ok));
    let s = snapshot();
    expect(s.relapsePlan?.sections.map((x) => x.type).sort()).toEqual([
      "protective_factors",
      "triggers",
    ]);
    expect(s.urgentPlan?.contacts.map((c) => c.name)).toEqual(["Marta"]);
    // esvaziar uma parte remove a seção no servidor
    expect(
      await engine.run(
        mutations.saveRelapsePlan({
          title: "Meu plano",
          sections: [
            {
              type: "triggers",
              title: "Gatilhos",
              content: "Fim do expediente",
            },
            {
              type: "protective_factors",
              title: "O que me protege",
              content: "",
            },
          ],
        }),
      ),
    ).toEqual(ok);
    s = snapshot();
    expect(s.relapsePlan?.sections.map((x) => x.type)).toEqual(["triggers"]);
    const contact = s.urgentPlan!.contacts[0];
    expect(
      await engine.run(
        mutations.saveUrgentContact({
          id: contact.id,
          name: "Marta Dias",
          relationship: "Mãe",
          phone: "+55 11 99999-0000",
          messageTemplate: "Pode me ligar?",
        }),
      ),
    ).toEqual(ok);
    expect(snapshot().urgentPlan?.contacts[0].name).toBe("Marta Dias");
    expect(await engine.run(mutations.removeUrgentContact(contact.id))).toEqual(
      ok,
    );
    expect(snapshot().urgentPlan?.contacts).toEqual([]);
  });

  it("10. perfil: revogar consentimento opcional e pedir direito do titular", async () => {
    const optional = snapshot().consents.find((c) => !c.mandatory)!;
    expect(optional.canRevoke).toBe(true);
    expect(
      await engine.run(
        mutations.setConsent({ id: optional.id, granted: false }),
      ),
    ).toEqual(ok);
    expect(snapshot().consents.find((c) => c.id === optional.id)?.status).toBe(
      "revoked",
    );
    expect(await engine.run(mutations.createPrivacyRequest("access"))).toEqual(
      ok,
    );
    expect(snapshot().privacyRequests[0]).toMatchObject({
      type: "access",
      status: "identity_pending",
    });
    // pedido aberto do mesmo tipo: o app explica em vez de falhar
    expect(await engine.run(mutations.createPrivacyRequest("access"))).toEqual({
      ok: false,
      reason: "invalid",
      code: "already_open",
    });
  });

  it("11. token de acesso inválido: renova uma vez, repete a chamada e mantém a sessão", async () => {
    await client.setSession({ ...activated, accessToken: "aem_invalido" });
    await engine.refresh(["patient"], { force: true });
    expect(engine.getState().failure).toBeNull();
    const devices = await client.get("/mobile/auth/sessions/", {
      parse: (raw) => raw as { id: string; is_current: boolean }[],
    });
    expect(devices.filter((d) => d.is_current)).toHaveLength(1);
    expect(client.currentSession()?.sessionId).toBe(activated.sessionId);
  });

  it("12. reuso do token de renovação derruba a sessão inteira", async () => {
    const anonymous = createApiClient({
      baseUrl: BASE,
      transport: nodeTransport,
      tokenStore: createMemoryTokenStore(),
      dev: true,
    });
    const login = await anonymous.post(
      "/mobile/auth/login/",
      {
        email: seed.email,
        password: PASSWORD,
        device_label: "Segundo aparelho",
        platform: "android",
        app_version: "1.0.0",
      },
      { auth: false, parse: parseTokens },
    );
    const rotated = await anonymous.post(
      "/mobile/auth/refresh/",
      { refresh_token: login.refreshToken },
      { auth: false, parse: parseTokens },
    );
    expect(rotated.accessToken).not.toBe(login.accessToken);
    // quem reapresenta o token já trocado é tratado como cópia: 401 e sessão revogada
    await expect(
      anonymous.post(
        "/mobile/auth/refresh/",
        { refresh_token: login.refreshToken },
        { auth: false, parse: parseTokens },
      ),
    ).rejects.toMatchObject({ status: 401 });
    await anonymous.setSession(rotated);
    await expect(anonymous.get("/mobile/me/")).rejects.toMatchObject({
      status: 401,
    });
  });

  it("13. sair encerra a sessão no servidor", async () => {
    await client.post("/mobile/auth/logout/", undefined);
    await expect(client.get("/mobile/me/")).rejects.toMatchObject({
      status: 401,
    });
  });
});
