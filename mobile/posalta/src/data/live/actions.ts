/**
 * Registro das ações de escrita do modo live.
 *
 * Toda gravação das telas é `store.run(mutations.<chave>(input))`. No preview a
 * mutação pura é aplicada na memória; no live o store procura aqui a ação com a mesma
 * `chave`. Sem ação registrada o resultado é `{ ok: false, reason: "unavailable" }`:
 * nunca se finge sucesso.
 *
 * COMO UM DOMÍNIO REGISTRA AS SUAS (sem editar o store nem as telas):
 *   1. em `src/data/live/<dominio>.ts`, ao lado do loader, exporte um registro:
 *        export const careActions: LiveActionRegistry = {
 *          logDose: {
 *            run: (input) => async (api) => {            // input: tipado pela mutação
 *              await api.put(`/mobile/medications/${input.medicationId}/doses/`, {…});
 *              return { ok: true };
 *            },
 *            refresh: ["doseLogs"],      // fatias recarregadas depois do sucesso
 *          },
 *        };
 *   2. importe-o abaixo e acrescente `...careActions` em `LIVE_ACTIONS`.
 *
 * Regras: erros de API sobem (`ApiError`) e o store os traduz em `offline` (rede),
 * `rejected` + `code` (4xx), `blocked` (402), `session` (sessão perdida) ou
 * `unavailable` (5xx); devolva `{ ok: false, reason: "invalid" }` para recusar a
 * entrada sem ir ao servidor; não grave nada localmente (o snapshot só muda quando
 * as fatias de `refresh` forem recarregadas); duas chamadas simultâneas com a mesma
 * chave e a mesma entrada viram uma só (trava no store).
 */
import type { Api } from "../../api/client";
import type { Snapshot } from "../../domain/types";
import type { MutationInput, MutationKey } from "../mutations";
import { agendaActions } from "./agenda";
import { authoringActions } from "./authoring";
import { careActions } from "./care";
import { diaryActions } from "./diary";
import { profileActions } from "./profile";
import { supportActions } from "./support";
import type { SnapshotSlice } from "./registry";

export type RemoteResult =
  | { ok: true }
  | { ok: false; reason: "invalid"; code?: string };

/** O que a ação pode consultar além da entrada (ex.: o id do plano ativo). */
export interface ActionContext {
  /** Último snapshot carregado (`null` antes do primeiro carregamento). */
  readonly snapshot: Snapshot | null;
}

export interface LiveAction<K extends MutationKey = MutationKey> {
  run: (
    input: MutationInput<K>,
    context: ActionContext,
  ) => (api: Api) => Promise<RemoteResult>;
  /** Fatias a recarregar (via loaders) depois do sucesso. */
  refresh: readonly SnapshotSlice[];
}

export type LiveActionRegistry = { [K in MutationKey]?: LiveAction<K> };

/** Ações ativas. Mutação sem ação aqui continua `unavailable`. */
export const LIVE_ACTIONS: LiveActionRegistry = {
  ...careActions,
  ...diaryActions,
  ...agendaActions,
  ...supportActions,
  ...profileActions,
  ...authoringActions,
};
