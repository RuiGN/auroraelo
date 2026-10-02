/** Loader da fatia `patient`: GET /mobile/me/ (api/mobile_patient_api.py). */
import {
  id,
  list,
  maybeIsoDate,
  maybeText,
  nonEmptyText,
  oneOf,
  Parser,
  record,
  text,
} from "../../api/parse";
import { PatientSummary, TeamRole } from "../../domain/types";
import type { LoaderEntry } from "./registry";

const TEAM_ROLES: readonly TeamRole[] = [
  "psychiatrist",
  "psychologist",
  "nurse",
  "pharmacist",
  "other",
];

/** Mesmo padrão do servidor quando o cadastro não tem um fuso válido. */
const DEFAULT_TIMEZONE = "America/Sao_Paulo";

/** `PatientSummaryOut` → `PatientSummary`. A alta pode vir sem data (`null`). */
export const parsePatientSummary: Parser<PatientSummary> = (value) => {
  const source = record(value);
  const clinic = record(source.clinic);
  return {
    id: id(source.id),
    displayName: nonEmptyText(source.display_name, 300),
    clinicName: text(clinic.name, 300),
    dischargeDate: maybeIsoDate(source.discharge_date),
    timezone: maybeText(source.timezone, 64) || DEFAULT_TIMEZONE,
    careTeam: list(source.care_team, (entry) => {
      const member = record(entry);
      return {
        id: id(member.id),
        name: nonEmptyText(member.name, 300),
        role: oneOf(member.role, TEAM_ROLES, "other"),
      };
    }),
  };
};

export const patientLoader: LoaderEntry = {
  slices: ["patient"],
  load: async (api) => ({
    patient: await api.get("/mobile/me/", { parse: parsePatientSummary }),
  }),
};
