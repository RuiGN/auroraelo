import { mutations } from "../src/data/mutations";
import { buildPreviewSnapshot } from "../src/data/previewData";
import { combineDateTime, toISODate } from "../src/domain/logic";
import { CheckInScaleAnswers, Snapshot } from "../src/domain/types";
import { NOW } from "./helpers";

const base = buildPreviewSnapshot(NOW);
const today = toISODate(NOW);
const answers: CheckInScaleAnswers = {
  general_state: 4,
  anxiety: 2,
  sadness: 2,
  irritability: 1,
  energy: 4,
  sleep_quality: 3,
  motivation: 4,
};

function apply(
  snapshot: Snapshot,
  mutation: ReturnType<(typeof mutations)[keyof typeof mutations]>,
) {
  const next = mutation(snapshot, NOW);
  if (next === null) throw new Error("mutação recusada");
  return next;
}

describe("check-in", () => {
  it("guarda um registro por dia: reenviar substitui o de hoje", () => {
    const first = apply(
      base,
      mutations.submitCheckIn({
        answers,
        notes: "  ok ",
        visibility: "private",
      }),
    );
    const second = apply(
      first,
      mutations.submitCheckIn({
        answers: { ...answers, anxiety: 5 },
        notes: "",
        visibility: "shareable",
      }),
    );
    const todays = second.checkIns.filter((item) => item.date === today);
    expect(todays).toHaveLength(1);
    expect(todays[0].answers.anxiety).toBe(5);
    expect(todays[0].visibility).toBe("shareable");
    expect(first.checkIns.find((item) => item.date === today)?.notes).toBe(
      "ok",
    );
    // o registro de ontem permanece
    expect(second.checkIns).toHaveLength(2);
  });

  it("recusa observações acima de 2000 caracteres", () => {
    const result = mutations.submitCheckIn({
      answers,
      notes: "x".repeat(2001),
      visibility: "private",
    })(base, NOW);
    expect(result).toBeNull();
  });
});

describe("diário", () => {
  const entry = {
    mood: 3 as const,
    emotions: ["calm" as const],
    intensity: 2 as const,
    context: "  Dia tranquilo ",
    triggers: "",
    reactions: "",
    strategies: "",
    visibility: "private" as const,
  };

  it("exige o que aconteceu e respeita os limites do backend", () => {
    expect(
      mutations.addJournalEntry({ ...entry, context: "   " })(base, NOW),
    ).toBeNull();
    expect(
      mutations.addJournalEntry({ ...entry, context: "x".repeat(4001) })(
        base,
        NOW,
      ),
    ).toBeNull();
    expect(
      mutations.addJournalEntry({ ...entry, triggers: "x".repeat(2001) })(
        base,
        NOW,
      ),
    ).toBeNull();
    expect(
      mutations.addJournalEntry({ ...entry, context: "x".repeat(4000) })(
        base,
        NOW,
      ),
    ).not.toBeNull();
  });

  it("insere o registro mais novo primeiro, com o texto aparado e privado por padrão", () => {
    const next = apply(base, mutations.addJournalEntry(entry));
    expect(next.journal).toHaveLength(base.journal.length + 1);
    expect(next.journal[0]).toMatchObject({
      context: "Dia tranquilo",
      visibility: "private",
    });
  });
});

describe("medicação", () => {
  const scheduledFor = combineDateTime(today, "08:00");

  it("registra e substitui o registro da mesma dose", () => {
    const taken = apply(
      base,
      mutations.logDose({ medicationId: "m-1", scheduledFor, status: "taken" }),
    );
    const corrected = apply(
      taken,
      mutations.logDose({
        medicationId: "m-1",
        scheduledFor,
        status: "omitted",
      }),
    );
    const logs = corrected.doseLogs.filter(
      (log) => log.medicationId === "m-1" && log.scheduledFor === scheduledFor,
    );
    expect(logs).toHaveLength(1);
    expect(logs[0].status).toBe("omitted");
  });

  it("desfaz um registro e recusa medicação desconhecida", () => {
    const taken = apply(
      base,
      mutations.logDose({ medicationId: "m-1", scheduledFor, status: "late" }),
    );
    const undone = apply(
      taken,
      mutations.undoDose({ medicationId: "m-1", scheduledFor }),
    );
    expect(
      undone.doseLogs.some(
        (log) =>
          log.scheduledFor === scheduledFor && log.medicationId === "m-1",
      ),
    ).toBe(false);
    expect(
      mutations.logDose({
        medicationId: "nope",
        scheduledFor,
        status: "taken",
      })(base, NOW),
    ).toBeNull();
  });
});

describe("plano de cuidado, rotina, exercícios e metas", () => {
  it("registra a resposta do paciente ao plano", () => {
    const next = apply(
      base,
      mutations.respondCarePlan({
        decision: "review_requested",
        notes: " quero revisar ",
      }),
    );
    expect(next.carePlan?.response).toMatchObject({
      decision: "review_requested",
      notes: "quero revisar",
    });
    expect(
      mutations.respondCarePlan({
        decision: "accepted",
        notes: "x".repeat(2001),
      })(base, NOW),
    ).toBeNull();
    expect(
      mutations.respondCarePlan({ decision: "accepted", notes: "" })(
        { ...base, carePlan: null },
        NOW,
      ),
    ).toBeNull();
  });

  it("marca e limpa o status de um hábito", () => {
    const done = apply(
      base,
      mutations.setHabitStatus({
        habitId: "h-1",
        date: today,
        status: "completed",
      }),
    );
    expect(
      done.habitChecks.filter((c) => c.habitId === "h-1" && c.date === today),
    ).toHaveLength(1);
    const changed = apply(
      done,
      mutations.setHabitStatus({
        habitId: "h-1",
        date: today,
        status: "partial",
      }),
    );
    expect(
      changed.habitChecks.find((c) => c.habitId === "h-1" && c.date === today)
        ?.status,
    ).toBe("partial");
    const cleared = apply(
      changed,
      mutations.setHabitStatus({ habitId: "h-1", date: today, status: null }),
    );
    expect(
      cleared.habitChecks.some((c) => c.habitId === "h-1" && c.date === today),
    ).toBe(false);
    expect(
      mutations.setHabitStatus({
        habitId: "x",
        date: today,
        status: "completed",
      })(base, NOW),
    ).toBeNull();
  });

  it("conclui exercício só com resposta", () => {
    expect(
      mutations.completeExercise({
        id: "ex-1",
        response: "  ",
        visibility: "private",
      })(base, NOW),
    ).toBeNull();
    const next = apply(
      base,
      mutations.completeExercise({
        id: "ex-1",
        response: " minha resposta ",
        visibility: "shareable",
      }),
    );
    expect(next.exercises.find((item) => item.id === "ex-1")).toMatchObject({
      status: "completed",
      response: "minha resposta",
      visibility: "shareable",
    });
  });

  it("alterna passos e muda o status de metas", () => {
    const toggled = apply(
      base,
      mutations.toggleGoalStep({ goalId: "g-1", stepId: "gs-2" }),
    );
    expect(toggled.goals[0].steps.find((s) => s.id === "gs-2")?.isDone).toBe(
      true,
    );
    const back = apply(
      toggled,
      mutations.toggleGoalStep({ goalId: "g-1", stepId: "gs-2" }),
    );
    expect(back.goals[0].steps.find((s) => s.id === "gs-2")?.isDone).toBe(
      false,
    );
    expect(
      mutations.toggleGoalStep({ goalId: "g-1", stepId: "gs-4" })(base, NOW),
    ).toBeNull(); // passo de outra meta
    expect(
      apply(base, mutations.setGoalStatus({ goalId: "g-1", status: "paused" }))
        .goals[0].status,
    ).toBe("paused");
  });
});

describe("fissura e contador", () => {
  it("valida intensidade de 0 a 10", () => {
    const entry = { triggersContext: "", copingStrategyUsed: "" };
    expect(
      mutations.addCraving({ ...entry, intensity: -1 })(base, NOW),
    ).toBeNull();
    expect(
      mutations.addCraving({ ...entry, intensity: 11 })(base, NOW),
    ).toBeNull();
    expect(
      mutations.addCraving({ ...entry, intensity: 4.5 })(base, NOW),
    ).toBeNull();
    const next = apply(base, mutations.addCraving({ ...entry, intensity: 0 }));
    expect(next.cravings[0].intensity).toBe(0);
  });

  it("oculta o contador e recomeça sem apagar o histórico de recomeços", () => {
    const hidden = apply(base, mutations.setCounterHidden(true));
    expect(hidden.sobriety?.hideCounter).toBe(true);
    const restarted = apply(hidden, mutations.restartCounter());
    expect(restarted.sobriety).toMatchObject({
      referenceDate: today,
      restartCount: 1,
      hideCounter: true,
    });
    expect(
      apply(restarted, mutations.restartCounter()).sobriety?.restartCount,
    ).toBe(2);
    expect(
      mutations.restartCounter()({ ...base, sobriety: null }, NOW),
    ).toBeNull();
  });

  it("liga e desliga o modo de pouca energia", () => {
    const on = apply(base, mutations.setLowEnergy(true));
    expect(on.lowEnergy.active).toBe(true);
    expect(on.lowEnergy.startedAt).not.toBeNull();
    const off = apply(on, mutations.setLowEnergy(false));
    expect(off.lowEnergy).toMatchObject({ active: false, startedAt: null });
  });
});

describe("agenda", () => {
  const service = base.services[0];
  const slot = service.freeSlots[0];

  it("solicita um horário livre como 'requested' e o retira dos livres", () => {
    const next = apply(
      base,
      mutations.requestAppointment({ serviceId: service.id, slot }),
    );
    const created = next.appointments[next.appointments.length - 1];
    expect(created.status).toBe("requested");
    expect(created.startAt).toBe(new Date(slot).toISOString());
    expect(
      new Date(created.endAt).getTime() - new Date(created.startAt).getTime(),
    ).toBe(service.durationMinutes * 60_000);
    expect(next.services[0].freeSlots).not.toContain(slot);
    // o mesmo horário não pode ser pedido duas vezes
    expect(
      mutations.requestAppointment({ serviceId: service.id, slot })(next, NOW),
    ).toBeNull();
  });

  it("recusa horários que não foram oferecidos", () => {
    expect(
      mutations.requestAppointment({
        serviceId: service.id,
        slot: new Date(2030, 0, 1).toISOString(),
      })(base, NOW),
    ).toBeNull();
    expect(
      mutations.requestAppointment({ serviceId: "nope", slot })(base, NOW),
    ).toBeNull();
  });

  it("pede reagendamento sem trocar o horário e cancela com motivo", () => {
    const resched = apply(base, mutations.requestReschedule({ id: "a-2" }));
    expect(resched.appointments.find((a) => a.id === "a-2")).toMatchObject({
      status: "reschedule_requested",
      startAt: base.appointments.find((a) => a.id === "a-2")!.startAt,
    });
    const canceled = apply(
      base,
      mutations.cancelAppointment({ id: "a-2", reason: " viagem " }),
    );
    expect(canceled.appointments.find((a) => a.id === "a-2")).toMatchObject({
      status: "canceled",
      cancelReason: "viagem",
    });
    // já realizada ou cancelada não muda mais
    expect(
      mutations.cancelAppointment({ id: "a-1", reason: "" })(base, NOW),
    ).toBeNull();
    expect(
      mutations.cancelAppointment({ id: "a-2", reason: "" })(canceled, NOW),
    ).toBeNull();
    expect(mutations.requestReschedule({ id: "a-1" })(base, NOW)).toBeNull();
    expect(
      mutations.cancelAppointment({ id: "a-2", reason: "x".repeat(256) })(
        base,
        NOW,
      ),
    ).toBeNull();
  });
});

describe("rede de apoio", () => {
  it("altera permissões e encerra o acompanhamento de uma pessoa da rede", () => {
    const toggled = apply(
      base,
      mutations.toggleSupportScope({ id: "sn-1", scope: "view_routine" }),
    );
    expect(toggled.supportNetwork[0].scopes).toContain("view_routine");
    const revoked = apply(toggled, mutations.revokeSupport("sn-1"));
    expect(revoked.supportNetwork[0]).toMatchObject({
      active: false,
      scopes: [],
    });
    // o diário nunca é um escopo possível de compartilhamento com a rede de apoio
    const allScopes = new Set(
      base.supportNetwork.flatMap((person) => person.scopes),
    );
    expect([...allScopes].some((scope) => /journal|diary/.test(scope))).toBe(
      false,
    );
  });
});

describe("conteúdo, consentimentos e LGPD", () => {
  it("alterna favorito e lido", () => {
    const next = apply(
      apply(base, mutations.toggleContent({ id: "c-1", flag: "favorite" })),
      mutations.toggleContent({ id: "c-1", flag: "read" }),
    );
    expect(next.content.find((item) => item.id === "c-1")).toMatchObject({
      favorite: true,
      read: true,
    });
  });

  it("não deixa revogar consentimento obrigatório; opcionais podem ser revogados e reconcedidos", () => {
    expect(
      mutations.setConsent({ purpose: "terms_of_use", granted: false })(
        base,
        NOW,
      ),
    ).toBeNull();
    expect(
      mutations.setConsent({ purpose: "clinical_limits", granted: false })(
        base,
        NOW,
      ),
    ).toBeNull();
    const revoked = apply(
      base,
      mutations.setConsent({ purpose: "communication", granted: false }),
    );
    expect(
      revoked.consents.find((item) => item.purpose === "communication")?.status,
    ).toBe("revoked");
    const granted = apply(
      revoked,
      mutations.setConsent({ purpose: "communication", granted: true }),
    );
    expect(
      granted.consents.find((item) => item.purpose === "communication")?.status,
    ).toBe("granted");
  });

  it("registra pedido do titular aguardando identidade e impede duplicidade aberta", () => {
    const next = apply(base, mutations.createPrivacyRequest("access"));
    expect(next.privacyRequests[0]).toMatchObject({
      type: "access",
      status: "identity_pending",
    });
    expect(mutations.createPrivacyRequest("access")(next, NOW)).toBeNull();
    expect(
      apply(next, mutations.createPrivacyRequest("erasure")).privacyRequests,
    ).toHaveLength(2);
  });
});

describe("imutabilidade", () => {
  it("nenhuma mutação altera o instantâneo original", () => {
    const frozen = JSON.stringify(base);
    apply(
      base,
      mutations.submitCheckIn({ answers, notes: "", visibility: "private" }),
    );
    apply(base, mutations.toggleGoalStep({ goalId: "g-1", stepId: "gs-2" }));
    apply(base, mutations.createPrivacyRequest("access"));
    expect(JSON.stringify(base)).toBe(frozen);
  });
});
