/**
 * Modo de operação do app.
 *
 * - `live` (padrão): dados reais. Enquanto o backend não oferecer sessão mobile e os
 *   contratos de API do app Pós-Alta (ver README), nenhuma informação clínica é
 *   exibida e toda ação de gravação é recusada com mensagem explícita.
 * - `preview`: demonstração com dados sintéticos mantidos só na memória, sempre
 *   sinalizada na interface. Precisa ser pedida explicitamente na compilação:
 *   `EXPO_PUBLIC_APP_MODE=preview` (scripts `start:preview`, `web:preview`).
 */
export type AppMode = "live" | "preview";

export function resolveAppMode(raw: string | undefined): AppMode {
  return raw === "preview" ? "preview" : "live";
}

// O Expo só substitui `process.env.EXPO_PUBLIC_*` quando a referência é literal.
export const APP_MODE: AppMode = resolveAppMode(
  process.env.EXPO_PUBLIC_APP_MODE,
);

/** Números de emergência do Brasil (padrão de wellness.CrisisResourceConfig). */
export const EMERGENCY_NUMBERS = {
  medical: "192",
  fire: "193",
  police: "190",
  emotionalSupport: "188",
} as const;
