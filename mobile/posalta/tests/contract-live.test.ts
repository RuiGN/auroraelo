/**
 * Contrato do modo live contra o OpenAPI real do backend: cada loader lê dados de
 * exemplo gerados do esquema de resposta e cada ação tem o corpo conferido contra o
 * esquema de entrada (ver tests/contractServer.ts).
 */
import { Api, createApiClient } from "../src/api/client";
import { createMemoryTokenStore } from "../src/api/tokenStore";
import { LIVE_ACTIONS } from "../src/data/live/actions";
import { createLiveEngine, LiveEngine } from "../src/data/live/engine";
import { LOADERS, unwiredSlices } from "../src/data/live/registry";
import { mutations } from "../src/data/mutations";
import { ContractServerOptions, createContractServer } from "./contractServer";
import {
  BASE_URL,
  createFakeServer,
  FakeServer,
  storedSession,
} from "./fakeApi";

async function setup(options: ContractServerOptions = {}) {
  const contract = createContractServer(options);
  const server: FakeServer = createFakeServer(contract.handler);
  const client = createApiClient({
    baseUrl: BASE_URL,
    transport: server.transport,
    tokenStore: createMemoryTokenStore(),
  });
  await client.setSession(storedSession(1));
  const engine: LiveEngine = createLiveEngine({
    api: client as Api,
    loaders: LOADERS,
    actions: LIVE_ACTIONS,
  });
  await engine.refresh();
  return { engine, server, contract };
}

function snapshotOf(engine: LiveEngine) {
  const snapshot = engine.getState().snapshot;
  if (!snapshot) throw new Error("snapshot não carregou");
  return snapshot;
}

describe("contrato: carregamento", () => {
  it("todas as leituras ligadas passam nos parsers com dados do esquema real", async () => {
    const { engine, contract } = await setup();
    expect(contract.violations).toEqual([]);
    expect(engine.getState().failure).toBeNull();
    expect(engine.getState().status).toBe("ready");
  });
});

describe("contrato: cuidado", () => {
  it("lê medicação, plano, rotina, exercícios e pouca energia", async () => {
    const { engine } = await setup({
      overrides: {
        "GET /mobile/medications/": {
          medications: [
            {
              id: "55555555-5555-4555-8555-555555555555",
              name: "Sertralina",
              presentation: "50 mg",
              dose: "1 comprimido",
              route: "oral",
              schedule_times: ["08:00", "20:00"],
              start_date: "2026-09-01",
              end_date: null,
              is_continuous: true,
              prescriber_name: "Dra. Helena",
              instructions: "Após o café.",
            },
          ],
          dose_logs: [
            {
              id: "66666666-6666-4666-8666-666666666666",
              medication_id: "55555555-5555-4555-8555-555555555555",
              scheduled_for: "2026-10-02T11:00:00+00:00",
              status: "taken",
              recorded_at: "2026-10-02T11:05:00Z",
            },
          ],
        },
      },
    });
    const snapshot = snapshotOf(engine);
    expect(snapshot.medications[0].scheduleTimes).toEqual(["08:00", "20:00"]);
    // "+00:00" e "Z" viram o mesmo texto: a conferência de doses é por igualdade
    expect(snapshot.doseLogs[0].scheduledFor).toBe("2026-10-02T11:00:00.000Z");
    expect(snapshot.carePlan?.actions.length).toBeGreaterThan(0);
    expect(snapshot.habits.length).toBeGreaterThan(0);
    expect(snapshot.exercises.length).toBeGreaterThan(0);
  });

  it("ações de cuidado respeitam o esquema de entrada e recarregam as fatias", async () => {
    const { engine, server, contract } = await setup();
    const snapshot = snapshotOf(engine);
    const med = snapshot.medications[0];
    const when = "2026-10-02T11:00:00.000Z";
    expect(
      await engine.run(
        mutations.logDose({
          medicationId: med.id,
          scheduledFor: when,
          status: "late",
        }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.undoDose({ medicationId: med.id, scheduledFor: when }),
      ),
    ).toEqual({ ok: true });
    const doseCalls = server.calls.filter((c) => c.method === "PUT");
    expect(doseCalls.map((c) => c.body.status)).toEqual([
      "late",
      "not_reported",
    ]);
    expect(
      await engine.run(
        mutations.respondCarePlan({ decision: "accepted", notes: " ok " }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.setHabitStatus({
          habitId: snapshot.habits[0].id,
          date: "2026-10-02",
          status: "completed",
        }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.setHabitStatus({
          habitId: snapshot.habits[0].id,
          date: "2026-10-02",
          status: null,
        }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.completeExercise({
          id: snapshot.exercises[0].id,
          response: "Fiz o exercício",
          visibility: "private",
        }),
      ),
    ).toEqual({ ok: true });
    expect(await engine.run(mutations.setLowEnergy(true))).toEqual({
      ok: true,
    });
    expect(contract.violations).toEqual([]);
    expect(server.calls.some((c) => c.method === "DELETE")).toBe(true);
  });

  it("responder o plano sem plano carregado é recusado sem ir ao servidor", async () => {
    const { engine, server } = await setup({
      overrides: { "GET /mobile/care-plan/": { care_plan: null } },
    });
    const before = server.calls.length;
    expect(
      await engine.run(
        mutations.respondCarePlan({ decision: "accepted", notes: "" }),
      ),
    ).toEqual({ ok: false, reason: "invalid" });
    expect(server.calls.length).toBe(before);
  });
});

describe("contrato: diário, recuperação e metas", () => {
  it("lê check-ins, registros, pedidos de acesso, recuperação e metas", async () => {
    const { engine, contract } = await setup();
    expect(contract.violations).toEqual([]);
    const snapshot = snapshotOf(engine);
    expect(snapshot.checkIns[0].answers.sleep_quality).toBe(3);
    expect(snapshot.journal.length).toBeGreaterThan(0);
    expect(snapshot.accessRequests.length).toBeGreaterThan(0);
    expect(snapshot.sobriety).not.toBeNull();
    expect(snapshot.goals[0].steps.length).toBeGreaterThan(0);
  });

  it("um check-in sem as sete respostas não é mostrado", async () => {
    const answers = {
      general_state: 3,
      anxiety: null,
      sadness: 2,
      irritability: 1,
      energy: 3,
      sleep_quality: 3,
      motivation: 3,
    };
    const { engine } = await setup({
      overrides: {
        "GET /mobile/diary/": {
          checkins: [
            {
              id: "55555555-5555-4555-8555-555555555555",
              date: "2026-10-02",
              answers,
              notes: "",
              visibility: "private",
              submitted_at: "2026-10-02T12:00:00Z",
            },
          ],
          entries: [],
        },
      },
    });
    expect(snapshotOf(engine).checkIns).toEqual([]);
  });

  it("ações do diário respeitam o esquema de entrada", async () => {
    const { engine, server, contract } = await setup();
    const snapshot = snapshotOf(engine);
    const goal = snapshot.goals[0];
    const outcomes = [
      await engine.run(
        mutations.submitCheckIn({
          answers: snapshot.checkIns[0].answers,
          notes: " tudo bem ",
          visibility: "shareable",
        }),
      ),
      await engine.run(
        mutations.addJournalEntry({
          mood: 4,
          emotions: ["calm", "hope"],
          intensity: 2,
          context: "Um bom dia",
          triggers: "",
          reactions: "",
          strategies: "",
          visibility: "private",
        }),
      ),
      await engine.run(
        mutations.addCraving({
          intensity: 7,
          triggersContext: "Fim do dia",
          copingStrategyUsed: "Caminhei",
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
        mutations.respondAccessRequest({
          id: snapshot.accessRequests[0].id,
          approve: false,
        }),
      ),
    ];
    expect(outcomes).toEqual(outcomes.map(() => ({ ok: true })));
    expect(contract.violations).toEqual([]);
    // alternar etapa envia o contrário do estado atual
    const stepCall = server.calls.find((c) => c.path.includes("/goals/steps/"));
    expect(stepCall?.body).toEqual({ is_done: !goal.steps[0].isDone });
  });

  it("arquivar meta é da equipe: o app recusa sem ir ao servidor", async () => {
    const { engine, server } = await setup();
    const goal = snapshotOf(engine).goals[0];
    const before = server.calls.length;
    expect(
      await engine.run(
        mutations.setGoalStatus({ goalId: goal.id, status: "archived" }),
      ),
    ).toEqual({ ok: false, reason: "invalid" });
    expect(server.calls.length).toBe(before);
  });
});

describe("contrato: agenda", () => {
  it("lê consultas e opções de agendamento (id composto serviço_profissional_unidade)", async () => {
    const { engine } = await setup();
    const snapshot = snapshotOf(engine);
    expect(snapshot.appointments.length).toBeGreaterThan(0);
    const option = snapshot.services[0];
    expect(option.id.split("_")).toHaveLength(3);
    expect(option.freeSlots[0]).toBe("2026-10-02T12:00:00.000Z");
  });

  it("pedir, remarcar e cancelar respeitam o esquema; remarcar exige horário", async () => {
    const { engine, server, contract } = await setup();
    const snapshot = snapshotOf(engine);
    const option = snapshot.services[0];
    const appointment = snapshot.appointments[0];
    expect(
      await engine.run(
        mutations.requestAppointment({
          serviceId: option.id,
          slot: option.freeSlots[0],
        }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.requestReschedule({
          id: appointment.id,
          slot: option.freeSlots[0],
        }),
      ),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.cancelAppointment({ id: appointment.id, reason: " viagem " }),
      ),
    ).toEqual({ ok: true });
    expect(contract.violations).toEqual([]);
    const request = server.calls.find(
      (c) => c.method === "POST" && c.path === "/mobile/appointments/",
    );
    expect(request?.body.idempotency_key).toMatch(/^app-[a-z0-9-]{8,}$/);
    const before = server.calls.length;
    expect(
      await engine.run(mutations.requestReschedule({ id: appointment.id })),
    ).toEqual({ ok: false, reason: "invalid" });
    expect(server.calls.length).toBe(before);
    expect(
      await engine.run(
        mutations.requestAppointment({ serviceId: "sem-partes", slot: "x" }),
      ),
    ).toEqual({ ok: false, reason: "invalid" });
  });
});

describe("contrato: apoio e perfil", () => {
  it("lê rede de apoio, plano urgente, plano de recaída, conteúdos, consentimentos e pedidos", async () => {
    const { engine, contract } = await setup({
      overrides: {
        "GET /mobile/support-network/": {
          supporters: [
            {
              id: "55555555-5555-4555-8555-555555555555",
              name: "Marta",
              relationship_type: "Mãe",
              scopes: ["view_wellness_summary", "view_diary"],
              established_at: "2026-09-01T12:00:00Z",
            },
          ],
          pending_invitations: [],
          available_scopes: ["view_wellness_summary"],
        },
        "GET /mobile/consents/": [
          {
            document_id: "66666666-6666-4666-8666-666666666666",
            purpose: "clinical_follow_up",
            kind: "consent",
            title: "Acompanhamento clínico",
            version: "2025.1",
            mandatory: true,
            status: "pending",
            decided_at: null,
            can_revoke: false,
          },
        ],
      },
    });
    expect(contract.violations).toEqual([]);
    const snapshot = snapshotOf(engine);
    // só os escopos do domínio entram; um escopo desconhecido é descartado
    expect(snapshot.supportNetwork[0].scopes).toEqual([
      "view_wellness_summary",
    ]);
    expect(snapshot.urgentPlan?.contacts.length).toBeGreaterThan(0);
    expect(snapshot.relapsePlan?.sections.length).toBeGreaterThan(0);
    expect(snapshot.content[0].favorite).toBe(false);
    expect(snapshot.content[0].estimatedMinutes).toBeGreaterThanOrEqual(1);
    expect(snapshot.consents[0]).toMatchObject({
      purpose: "clinical_follow_up",
      status: "pending",
      mandatory: true,
      decidedAt: null,
    });
    expect(snapshot.consents[0].content).toEqual(expect.any(String));
    expect(snapshot.privacyRequests.length).toBeGreaterThan(0);
  });

  it("escopos de apoio exigem a senha e enviam a lista completa; revogar apaga a pessoa", async () => {
    const { engine, server, contract } = await setup({
      overrides: {
        "GET /mobile/support-network/": {
          supporters: [
            {
              id: "55555555-5555-4555-8555-555555555555",
              name: "Marta",
              relationship_type: "Mãe",
              scopes: ["view_wellness_summary"],
              established_at: "2026-09-01T12:00:00Z",
            },
          ],
          pending_invitations: [],
          available_scopes: [],
        },
      },
    });
    const person = snapshotOf(engine).supportNetwork[0];
    const before = server.calls.length;
    expect(
      await engine.run(
        mutations.toggleSupportScope({
          id: person.id,
          scope: "receive_urgent_alerts",
        }),
      ),
    ).toEqual({ ok: false, reason: "invalid" });
    expect(server.calls.length).toBe(before);
    expect(
      await engine.run(
        mutations.toggleSupportScope({
          id: person.id,
          scope: "receive_urgent_alerts",
          password: "senha-do-teste",
        }),
      ),
    ).toEqual({ ok: true });
    const put = server.calls.find((c) => c.method === "PUT");
    expect(put?.body).toEqual({
      scopes: ["view_wellness_summary", "receive_urgent_alerts"],
      password: "senha-do-teste",
    });
    expect(await engine.run(mutations.revokeSupport(person.id))).toEqual({
      ok: true,
    });
    expect(contract.violations).toEqual([]);
  });

  it("consentimento: aceitar usa a decisão; revogar manda um motivo; pedido LGPD duplicado vira 'invalid'", async () => {
    const { engine, server, contract } = await setup({
      overrides: {
        "POST /mobile/privacy-requests/": {
          status: 409,
          body: { detail: "x", code: "already_open" },
        },
      },
    });
    const consent = snapshotOf(engine).consents[0];
    expect(
      await engine.run(mutations.setConsent({ id: consent.id, granted: true })),
    ).toEqual({ ok: true });
    expect(
      await engine.run(
        mutations.setConsent({ id: consent.id, granted: false }),
      ),
    ).toEqual({ ok: true });
    const bodies = server.calls
      .filter((c) => c.method === "POST" && c.path.includes("/consents/"))
      .map((c) => c.body);
    expect(bodies[0].decision).toBe("accepted");
    expect(bodies[1].reason.length).toBeGreaterThanOrEqual(3);
    expect(bodies[0].request_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(await engine.run(mutations.createPrivacyRequest("access"))).toEqual({
      ok: false,
      reason: "invalid",
      code: "already_open",
    });
    expect(contract.violations).toEqual([]);
  });
});

describe("contrato: conteúdo pessoal editado no app", () => {
  it("meta, plano de recaída, plano urgente, contatos e ações de pouca energia respeitam o esquema", async () => {
    const { engine, server, contract } = await setup();
    const snapshot = snapshotOf(engine);
    const contactId = snapshot.urgentPlan!.contacts[0].id;
    const outcomes = [
      await engine.run(
        mutations.setupSobriety({
          goalType: "reduction",
          focus: "  Álcool ",
          referenceDate: "2026-10-02",
          motivations: "Estar presente",
          hideCounter: false,
        }),
      ),
      await engine.run(
        mutations.saveRelapsePlan({
          title: "Meu plano",
          sections: [
            { type: "triggers", title: "Gatilhos", content: " Fim do dia " },
            { type: "protective_factors", title: "O que protege", content: "" },
          ],
        }),
      ),
      await engine.run(
        mutations.saveUrgentPlan({
          personalInstructions: "Respirar fundo",
          calmingStrategies: ["Caminhar", " ", "Ligar para alguém"],
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
      await engine.run(
        mutations.saveUrgentContact({
          id: contactId,
          name: "Marta",
          relationship: "Mãe",
          phone: "+55 11 99999-0000",
          messageTemplate: "Pode me ligar?",
        }),
      ),
      await engine.run(mutations.removeUrgentContact(contactId)),
      await engine.run(mutations.setLowEnergyActions(["Beber água", " "])),
    ];
    expect(outcomes).toEqual(outcomes.map(() => ({ ok: true })));
    expect(contract.violations).toEqual([]);
    const plan = server.calls.find(
      (c) => c.method === "PUT" && c.path === "/mobile/relapse-plan/",
    );
    // seção vazia não é enviada; o texto é aparado
    expect(plan?.body.sections).toEqual([
      { section_type: "triggers", title: "Gatilhos", content: "Fim do dia" },
    ]);
    const energy = server.calls.find(
      (c) => c.path === "/mobile/low-energy/actions/",
    );
    expect(energy?.body).toEqual({ actions: ["Beber água"] });
    const goal = server.calls.find((c) => c.path === "/mobile/recovery/goal/");
    expect(goal?.body.focus).toBe("Álcool");
  });
});

describe("contrato: cobertura", () => {
  it("toda fatia do Snapshot tem loader", () => {
    expect(unwiredSlices(LOADERS)).toEqual([]);
  });
});
