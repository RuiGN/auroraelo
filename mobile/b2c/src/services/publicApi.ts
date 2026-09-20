import { createPublicClient } from "../../../shared/http";

// Origem pública, sem segredo. Não dispara requisições ao importar.
// Nenhum endpoint ligado à UI antes de homologar o contrato backend.
export const publicApi = createPublicClient(
  process.env.EXPO_PUBLIC_API_BASE_URL,
);
