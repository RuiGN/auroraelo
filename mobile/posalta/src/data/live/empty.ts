import { PatientSummary, Snapshot } from "../../domain/types";

/**
 * Snapshot do modo live antes de os loaders de cada domínio existirem (ou
 * responderem): só o paciente é real; todo o resto é vazio e seguro. O tipo de
 * retorno obriga a listar qualquer fatia nova do `Snapshot`.
 */
export function emptySnapshotFor(patient: PatientSummary): Snapshot {
  return {
    patient,
    checkIns: [],
    journal: [],
    sobriety: null,
    cravings: [],
    medications: [],
    doseLogs: [],
    carePlan: null,
    habits: [],
    habitChecks: [],
    exercises: [],
    relapsePlan: null,
    goals: [],
    lowEnergy: { actions: [], active: false, startedAt: null },
    appointments: [],
    services: [],
    supportNetwork: [],
    urgentPlan: null,
    content: [],
    consents: [],
    privacyRequests: [],
  };
}
