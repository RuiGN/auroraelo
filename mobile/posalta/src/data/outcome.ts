/** Resultado de uma gravação (`store.run`) e estado de carregamento do store. */

/**
 * - `unavailable`: não há ação registrada para esta gravação no modo live, ou o
 *   servidor não conseguiu concluir (`code: "server_error"`). Nada foi fingido.
 * - `invalid`: a entrada foi recusada antes de enviar (validação local).
 * - `offline`: sem rede ou tempo esgotado; o snapshot continua como estava.
 * - `rejected`: o servidor recusou (4xx); `code` é o `code` do corpo do erro.
 * - `session`: a sessão acabou; o app volta para a entrada.
 * - `blocked`: clínica com cobrança pendente (HTTP 402).
 */
export type ActionFailure =
  | "unavailable"
  | "invalid"
  | "offline"
  | "rejected"
  | "session"
  | "blocked";

export type ActionOutcome =
  | { ok: true }
  | { ok: false; reason: ActionFailure; code?: string };

/** `idle`: nada para carregar (sem sessão/config). `ready`: tudo carregado. */
export type StoreStatus = "idle" | "loading" | "error" | "ready";

/** Por que o último carregamento falhou (para escolher o texto e o botão). */
export type LoadFailure = "offline" | "blocked" | "unexpected";
