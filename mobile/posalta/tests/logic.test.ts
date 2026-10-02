import { buildPreviewSnapshot } from "../src/data/previewData";
import {
  addDays,
  checkInDoneOn,
  combineDateTime,
  daysBetween,
  daysSince,
  doseSlotsForDay,
  doseSummary,
  firstName,
  goalProgress,
  habitSummary,
  isMedicationActiveOn,
  nextAppointment,
  parseISODate,
  partOfDay,
  recoveryDays,
  suggestsExtraSupport,
  toISODate,
} from "../src/domain/logic";
import { CheckInScaleAnswers } from "../src/domain/types";
import { NOW } from "./helpers";

const snapshot = buildPreviewSnapshot(NOW);
const today = toISODate(NOW);

describe("datas", () => {
  it("formatam e interpretam datas locais sem saltar de dia", () => {
    expect(today).toBe("2026-10-02");
    expect(toISODate(parseISODate("2026-03-01"))).toBe("2026-03-01");
    expect(addDays("2026-10-02", -9)).toBe("2026-09-23");
    expect(addDays("2026-02-27", 3)).toBe("2026-03-02");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });

  it("contam dias de calendário (inclusive na virada de horário de verão)", () => {
    expect(daysBetween("2026-09-23", "2026-10-02")).toBe(9);
    expect(daysBetween("2026-10-02", "2026-09-23")).toBe(-9);
    expect(daysBetween("2018-11-03", "2018-11-05")).toBe(2);
    expect(daysSince("2026-09-23", NOW)).toBe(9);
  });

  it("combinam data e horário locais", () => {
    const iso = combineDateTime("2026-10-02", "08:30");
    const date = new Date(iso);
    expect([
      date.getFullYear(),
      date.getMonth(),
      date.getDate(),
      date.getHours(),
      date.getMinutes(),
    ]).toEqual([2026, 9, 2, 8, 30]);
  });

  it("calculam período do dia e primeiro nome", () => {
    expect(partOfDay(new Date(2026, 9, 2, 6))).toBe("morning");
    expect(partOfDay(new Date(2026, 9, 2, 12))).toBe("afternoon");
    expect(partOfDay(new Date(2026, 9, 2, 18))).toBe("evening");
    expect(firstName("  Alex   Exemplo ")).toBe("Alex");
  });
});

describe("medicações", () => {
  it("monta as doses do dia ordenadas por horário", () => {
    const slots = doseSlotsForDay(snapshot, today);
    expect(slots.map((slot) => slot.time)).toEqual(["08:00", "08:00", "20:00"]);
    expect(slots.every((slot) => slot.log === null)).toBe(true);
    expect(doseSummary(slots)).toEqual({ done: 0, total: 3 });
  });

  it("encontra os registros do dia anterior", () => {
    const yesterday = doseSlotsForDay(snapshot, addDays(today, -1));
    expect(doseSummary(yesterday)).toEqual({ done: 3, total: 3 });
    expect(yesterday.find((slot) => slot.time === "20:00")?.log?.status).toBe(
      "late",
    );
  });

  it("respeita início e fim de cada prescrição", () => {
    const naltrexone = snapshot.medications.find((item) => item.id === "m-2")!;
    expect(isMedicationActiveOn(naltrexone, addDays(today, -31))).toBe(false);
    expect(isMedicationActiveOn(naltrexone, today)).toBe(true);
    expect(isMedicationActiveOn(naltrexone, addDays(today, 61))).toBe(false);
    const continuous = snapshot.medications.find((item) => item.id === "m-1")!;
    expect(isMedicationActiveOn(continuous, addDays(today, 500))).toBe(true);
  });
});

describe("rotina, metas e check-in", () => {
  it("resume hábitos concluídos no dia", () => {
    expect(habitSummary(snapshot.habits, snapshot.habitChecks, today)).toEqual({
      done: 0,
      total: 4,
    });
    expect(
      habitSummary(snapshot.habits, snapshot.habitChecks, addDays(today, -1)),
    ).toEqual({ done: 2, total: 4 });
  });

  it("calcula o progresso das metas", () => {
    expect(goalProgress(snapshot.goals[0])).toEqual({
      done: 1,
      total: 3,
      percent: 33,
    });
    expect(goalProgress({ ...snapshot.goals[0], steps: [] })).toEqual({
      done: 0,
      total: 0,
      percent: 0,
    });
  });

  it("sabe se o check-in do dia foi feito", () => {
    expect(checkInDoneOn(snapshot, today)).toBe(false);
    expect(checkInDoneOn(snapshot, addDays(today, -1))).toBe(true);
  });

  it("oferece apoio extra de forma conservadora", () => {
    const calm: CheckInScaleAnswers = {
      general_state: 4,
      anxiety: 2,
      sadness: 2,
      irritability: 2,
      energy: 4,
      sleep_quality: 4,
      motivation: 4,
    };
    expect(suggestsExtraSupport(calm)).toBe(false);
    expect(suggestsExtraSupport({ ...calm, general_state: 2 })).toBe(true);
    expect(suggestsExtraSupport({ ...calm, anxiety: 4 })).toBe(true);
    expect(suggestsExtraSupport({ ...calm, sadness: 5 })).toBe(true);
    expect(suggestsExtraSupport({ ...calm, anxiety: 3, sadness: 3 })).toBe(
      false,
    );
  });
});

describe("agenda e contador", () => {
  it("devolve a próxima consulta ativa", () => {
    const next = nextAppointment(snapshot, NOW);
    expect(next?.id).toBe("a-2");
    expect(nextAppointment({ ...snapshot, appointments: [] }, NOW)).toBeNull();
  });

  it("nunca mostra contador negativo", () => {
    expect(recoveryDays("2026-09-23", NOW)).toBe(9);
    expect(recoveryDays("2026-12-01", NOW)).toBe(0);
  });
});
