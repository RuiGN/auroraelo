/**
 * Registro dos carregadores (loaders) do modo live.
 *
 * Cada fatia do `Snapshot` (`patient`, `medications`, `goals`…) é preenchida por um
 * loader: `(api) => Promise<Partial<Snapshot>>`. Enquanto uma fatia não tem loader
 * ela fica com o valor vazio seguro de `empty.ts` (listas vazias, `null`, pouca
 * energia inativa); nunca com dado inventado.
 *
 * COMO UM DOMÍNIO REGISTRA O SEU (sem editar o store nem as telas):
 *   1. crie `src/data/live/<dominio>.ts` exportando um `LoaderEntry`:
 *        export const medicationsLoader: LoaderEntry = {
 *          slices: ["medications", "doseLogs"],      // fatias que este loader preenche
 *          load: async (api) => {
 *            const data = await api.get("/mobile/medications/", { parse });
 *            return { medications: …, doseLogs: … };
 *          },
 *        };
 *   2. importe-o abaixo e acrescente UMA linha em `LOADERS`.
 *
 * Regras: uma fatia pertence a um único loader (teste confere); o loader só altera as
 * fatias que declarou em `slices` (o resto do que devolver é descartado); erros de API
 * podem subir (`ApiError`): o store os traduz em `status`/`failure`; sempre valide o
 * corpo com `parse` (ver `src/api/parse.ts`).
 */
import type { Api } from "../../api/client";
import type { Snapshot } from "../../domain/types";
import { patientLoader } from "./patient";

/** Nome de uma fatia do Snapshot. */
export type SnapshotSlice = keyof Snapshot;

export type Loader = (api: Api) => Promise<Partial<Snapshot>>;

export interface LoaderEntry {
  /** Fatias que o loader preenche (e que `refresh([...])`/ações podem pedir). */
  readonly slices: readonly SnapshotSlice[];
  readonly load: Loader;
}

const ALL_SLICES: Record<SnapshotSlice, true> = {
  patient: true,
  checkIns: true,
  journal: true,
  sobriety: true,
  cravings: true,
  medications: true,
  doseLogs: true,
  carePlan: true,
  habits: true,
  habitChecks: true,
  exercises: true,
  relapsePlan: true,
  goals: true,
  lowEnergy: true,
  appointments: true,
  services: true,
  supportNetwork: true,
  urgentPlan: true,
  content: true,
  consents: true,
  privacyRequests: true,
};

/** Todas as fatias do Snapshot; o tipo acima obriga a atualizar esta lista junto. */
export const SNAPSHOT_SLICES = Object.keys(ALL_SLICES) as SnapshotSlice[];

/** Loaders ativos. Um domínio novo acrescenta uma linha aqui. */
export const LOADERS: readonly LoaderEntry[] = [
  patientLoader,
  // medicationsLoader,   // exemplo: domínio de cuidado
];

/** Fatias que ainda não têm loader (continuam vazias no modo live). */
export function unwiredSlices(
  loaders: readonly LoaderEntry[] = LOADERS,
): SnapshotSlice[] {
  const wired = new Set(loaders.flatMap((entry) => entry.slices));
  return SNAPSHOT_SLICES.filter((slice) => !wired.has(slice));
}
