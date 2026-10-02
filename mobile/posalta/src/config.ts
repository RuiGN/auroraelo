/**
 * Modo de operação do app.
 *
 * - `live` (padrão): dados reais, vindos da API do paciente (`/api/v1/mobile/`) com
 *   sessão por token. Exige `EXPO_PUBLIC_API_BASE_URL`; sem um endereço válido o app
 *   mostra a tela de configuração ausente e nenhum dado clínico é exibido.
 * - `preview`: demonstração com dados sintéticos mantidos só na memória, sempre
 *   sinalizada na interface. Precisa ser pedida explicitamente na compilação:
 *   `EXPO_PUBLIC_APP_MODE=preview` (scripts `start:preview`, `web:preview`). Não usa
 *   sessão nem rede.
 */
export type AppMode = "live" | "preview";

export function resolveAppMode(raw: string | undefined): AppMode {
  return raw === "preview" ? "preview" : "live";
}

// O Expo só substitui `process.env.EXPO_PUBLIC_*` quando a referência é literal.
export const APP_MODE: AppMode = resolveAppMode(
  process.env.EXPO_PUBLIC_APP_MODE,
);

/** Hosts em que HTTP simples é aceito, e só em desenvolvimento (`__DEV__`). */
const DEV_HTTP_HOSTS = ["localhost", "127.0.0.1", "10.0.2.2"];

// Gramática deliberadamente restrita (como em ../shared/http.ts): esquema, host ASCII
// e porta opcional, sem usuário, caminho, consulta ou fragmento. A URL global do
// React Native 0.76 não implementa `protocol`/`origin`, então não usamos `new URL`.
const DNS_LABEL = "[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?";
const BASE_URL = new RegExp(
  `^(https?)://(${DNS_LABEL}(?:\\.${DNS_LABEL})*)(?::(\\d{1,5}))?/?$`,
  "i",
);

/**
 * Valida o endereço do servidor e o devolve normalizado (origem, sem barra final),
 * ou `null` quando ausente ou inválido.
 *
 * - `https` é obrigatório;
 * - `http` só vale para `localhost`, `127.0.0.1` e `10.0.2.2` (emulador Android) e
 *   somente com `dev = true`;
 * - só a origem: o app acrescenta `/api/v1` aos caminhos do contrato.
 *
 * É o único lugar onde o endereço do servidor é decidido: o cliente HTTP só envia
 * o token de acesso para a origem devolvida aqui.
 */
export function resolveApiBaseUrl(
  raw: string | undefined | null,
  dev: boolean,
): string | null {
  if (typeof raw !== "string") return null;
  const match = BASE_URL.exec(raw.trim());
  if (!match) return null;
  const scheme = match[1].toLowerCase();
  const host = match[2].toLowerCase();
  const port = match[3];
  if (port !== undefined && (Number(port) < 1 || Number(port) > 65535)) {
    return null;
  }
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) {
    // Endereço IP só nos hosts de desenvolvimento listados (nunca um IP qualquer).
    if (!DEV_HTTP_HOSTS.includes(host)) return null;
  }
  if (scheme === "http") {
    if (!dev || !DEV_HTTP_HOSTS.includes(host)) return null;
  } else if (!host.includes(".") && host !== "localhost") {
    return null;
  }
  // Porta padrão do esquema é omitida: é assim que o sistema devolve a URL da resposta
  // (o cliente compara a URL da resposta com a da requisição para detectar redirects).
  const portNumber = port === undefined ? null : Number(port);
  const isDefaultPort =
    portNumber === (scheme === "https" ? 443 : 80) || portNumber === null;
  return `${scheme}://${host}${isDefaultPort ? "" : `:${portNumber}`}`;
}

/** `__DEV__` existe no Metro e no Jest; em outro ambiente assume produção. */
export const IS_DEV: boolean =
  typeof __DEV__ !== "undefined" ? __DEV__ === true : false;

/**
 * Origem do servidor (`https://…`) ou `null` quando faltar/for inválida. A variável é
 * pública (vai no pacote do app): nunca coloque segredo nela.
 */
export const API_BASE_URL: string | null = resolveApiBaseUrl(
  process.env.EXPO_PUBLIC_API_BASE_URL,
  IS_DEV,
);

/** Números de emergência do Brasil (padrão de wellness.CrisisResourceConfig). */
export const EMERGENCY_NUMBERS = {
  medical: "192",
  fire: "193",
  police: "190",
  emotionalSupport: "188",
} as const;
