// Contratos clínicos ainda não homologados. Não chamar os endpoints históricos.
async function unavailable(): Promise<never> {
  throw Object.assign(new Error("unavailable"), {
    code: "unavailable" as const,
  });
}
export const AuroraApiService = Object.freeze({
  getPatientSummary: unavailable,
  logMedication: unavailable,
  triggerSOS: unavailable,
});
