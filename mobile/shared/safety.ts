import { ApiError } from "./http";

// Decisão de produto: sem flag remota/EXPO_PUBLIC capaz de ativar IA.
// Requer implementação da API própria, revisão clínica e novo contrato de consentimento.
export const DIGITAL_SUPPORT = Object.freeze({
  enabled: false,
  consent: false,
} as const);
export async function startDigitalSupport(): Promise<never> {
  throw new ApiError("unavailable");
}
