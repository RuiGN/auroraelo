# Aurora Elo Pós-Alta — app mobile do paciente

Terceiro projeto Expo ao lado de `b2c` e `connected`. É o aplicativo que o paciente
usa em casa depois da alta, montado a partir das funcionalidades de paciente do
backend Django (`journal`, `goals`, `routines`, `scheduling`, `wellness`,
`support_network`, `content`, `consents`, `privacy`).

- **Marca e design:** logo oficial (`logo.png`, copiada para `assets/`) e tokens do
  `auroraelo_design_system`. `src/theme/tokens.generated.ts` é gerado do CSS do
  design system (`npm run tokens`); claro/escuro e Manrope seguem o design system.
  Um teste valida contraste WCAG AA de 14 pares de cor nos dois temas.
- **Idiomas:** `pt-br` (padrão), `en` e `es`, com paridade de chaves e de
  `{parâmetros}` verificada em teste. No `AsyncStorage` ficam só o idioma e a
  aparência; a sessão (tokens) fica no cofre seguro do aparelho (ver "Modo live").
  Textos de prontuário/equipe não são traduzidos. As mensagens de erro da API são
  escolhidas pelo `code` do erro (`src/i18n/errorCodes.ts`), nunca pelo `detail`.

## Escopo: o que NÃO está neste app

Pertencem ao **aplicativo da clínica** (equipe), não ao paciente, e foram retirados
daqui: régua de acompanhamento pós-alta (ligações aos 7 e 15 dias e visita aos 15),
Concierge/contato com a família e mensagens com a equipe. Os itens correspondentes
do PRD (`ConciergeLog`, `CommunicationRule`) continuam sendo trabalho do backend e
do app da clínica. Um teste (`escopo do app do paciente`) impede a volta desses
termos, telas e rotas.

## Telas

| Aba | Conteúdo | Origem no backend |
|---|---|---|
| **Hoje** | saudação, dias desde a alta, resumo do dia, modo de pouca energia, metas | todos abaixo |
| **Cuidado** | plano de cuidado (e resposta do paciente), medicações e registro de doses, rotina/hábitos, exercícios da equipe, plano de prevenção de recaída, metas | `routines.CarePlan/PrescribedMedication/Habit`, `goals.*`, `wellness.RelapsePreventionPlan` |
| **Diário** | check-in diário (7 perguntas 1–5), registro no diário (humor, emoções, visibilidade), vontade de usar, contador de recuperação (ocultável, recomeço sem culpa) | `journal.*`, `wellness.SobrietyGoal/CravingCheckIn` |
| **Agenda** | consultas, solicitar horário livre, pedir reagendamento, cancelar | `scheduling.*` |
| **Apoio** | rede de apoio (o que cada pessoa vê; o diário nunca é compartilhado), conteúdos indicados | `support_network.*`, `content.*` |
| **Ajuda** (cabeçalho) | números de emergência, pessoas de confiança, respiração guiada, 5-4-3-2-1, plano pessoal | `support_network.UrgentSupportPlan`, `wellness.CrisisResourceConfig` |
| **Perfil** | equipe, idioma, aparência, consentimentos, direitos LGPD, sair deste aparelho e dos outros (só no live) | `consents.*`, `privacy.DataSubjectRequest`, sessões do app |
| **Entrada** (live, sem sessão) | entrar, ativar conta com o código do convite, recuperar e redefinir a senha; Ajuda urgente em todas | `/mobile/auth/…` |

## Dois modos (`EXPO_PUBLIC_APP_MODE`)

- **`live` (padrão):** dados reais da API do paciente (`/api/v1/mobile/`), com entrada
  por e-mail e senha e sessão por token. Sem endereço válido do servidor o app mostra a
  tela "Aplicativo sem configuração" (nada é exibido, salvo ou enviado); sem sessão
  ativa só existe a pilha de entrada. Hoje só o **paciente** (`GET /mobile/me/`) vem da
  API: as demais fatias do `Snapshot` ficam vazias e toda gravação responde
  "ainda não está disponível" até cada domínio registrar o seu loader e as suas ações
  (ver "Modo live" abaixo). A Ajuda urgente funciona sem entrar e sem rede.
- **`preview`:** demonstração com dados 100 % sintéticos mantidos só na memória,
  sinalizada por faixa em toda tela e selo "DEMO" no cabeçalho. Não usa sessão nem
  rede. Só liga se pedida na compilação: `npm run start:preview`,
  `npm run web:preview`, `npm run export:preview`.

A ajuda urgente nunca simula nada: abrir a tela não avisa ninguém, os números abrem o
discador **só quando o paciente toca**, e o texto diz que o app não é serviço de
emergência nem monitora em tempo real (alinhado ao `NO_DELIVERY` do backend).

## Modo live

### Variáveis de ambiente

| Variável | Valor | Observações |
|---|---|---|
| `EXPO_PUBLIC_API_BASE_URL` | origem do servidor, ex. `https://api.exemplo.com.br` | só a origem (sem caminho, usuário, consulta ou fragmento); o app acrescenta `/api/v1`. **`https` é obrigatório.** `http` só vale para `localhost`, `127.0.0.1` e `10.0.2.2` (emulador Android) e só em desenvolvimento (`__DEV__`). Ausente ou inválida = tela de configuração ausente. É pública (vai no pacote): nunca coloque segredo nela. |
| `EXPO_PUBLIC_APP_MODE` | `preview` | qualquer outro valor (ou ausente) = `live`. |

Os scripts usam `EXPO_NO_DOTENV=1`: arquivos `.env` **não** são lidos. Passe as variáveis
no comando, por exemplo `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000 npm start` (no
emulador Android use `http://10.0.2.2:8000`). O Expo só troca `process.env.EXPO_PUBLIC_*`
quando a referência é literal; por isso `src/config.ts` não faz acesso dinâmico.

### Fluxo de entrada

`SessionProvider` (`src/api/session.tsx`) mantém a máquina de estados
`disabled` (preview, ou sem endereço do servidor) → `restoring` (lê o cofre, sem rede) →
`signedOut` | `active`. O `RootNavigator` escolhe as telas por esse estado:

- `active` (ou preview): as abas e as telas de dados;
- `signedOut`: **Entrar**, **Ativar conta**, **Recuperar senha** e **Redefinir senha**
  (`src/screens/AuthScreens.tsx`), cada uma com acesso visível à **Ajuda urgente**;
- `disabled` no live: "Aplicativo sem configuração"; `restoring`: "Abrindo sua conta…".

Detalhes que importam:

- **Tokens** (`src/api/tokenStore.ts`): `expo-secure-store` no iOS/Android (só neste
  aparelho, fora de backups); **web: só memória**, recarregar a página encerra a sessão;
  nunca `AsyncStorage`. O estado do React guarda só clínica e nome de exibição.
- **Cliente HTTP** (`src/api/client.ts`): `Authorization: Bearer` só vai para a origem
  configurada (o cliente monta a URL e recusa caminhos fora do formato); tempo limite de
  15 s; `redirect: "error"`, `credentials: "omit"`; a resposta precisa ser JSON.
  **401 → uma renovação por vez** (chamadas simultâneas aguardam a mesma promessa: o
  servidor revoga a sessão inteira se o mesmo token de renovação for reapresentado) e a
  requisição original é repetida **uma** vez. Renovação recusada (401/403) = sessão
  perdida (apaga os tokens, volta para a entrada com aviso); erro de rede ou tempo
  esgotado **não** derruba a sessão. `402` → `clinic_blocked`; `429` → `rate_limited`;
  `409 clinic_choice_required` traz as clínicas; `422` de senha traz `errors[]`. Nenhum
  token, corpo ou URL vai para log, mensagem de erro ou estado.
- **Login com mais de uma clínica:** o `409` abre a escolha na própria tela e reenvia
  com `clinic_id`.
- **Links do e-mail:** `auroraelo-posalta://activate?code=…` e `…://reset?code=…`
  (`scheme` em `app.json`; parser puro em `src/api/deepLinks.tsx`). O código fica só em
  memória até a tela preencher o campo (editável); links desconhecidos são ignorados e
  só valem sem sessão ativa.
- **Sair** (Perfil, com confirmação) chama `POST /mobile/auth/logout/` e **sempre**
  limpa o aparelho, mesmo sem rede; "Sair dos outros aparelhos" usa
  `/mobile/auth/sessions/revoke-others/`. Ao perder a sessão o snapshot em memória é
  descartado: nenhum dado clínico fica visível sem sessão.

### Como o store funciona (`src/data/store.tsx`, `src/data/live/`)

```
Store { mode, snapshot, now, status, failure, run(mutation), refresh(slices?) }
status: "idle" | "loading" | "error" | "ready"      failure: "offline" | "blocked" | "unexpected" | null
run(...) -> Promise<ActionOutcome>   (no preview resolve na hora)
ActionOutcome = { ok: true } | { ok: false, reason, code? }
reason: "unavailable" | "invalid" | "offline" | "rejected" | "session" | "blocked"
```

- **Leitura:** ao ficar ativo (e ao voltar ao primeiro plano, no máximo a cada 30 s e
  nunca com outro carregamento em andamento) o motor recarrega **todas** as fatias pelos
  loaders. Cada loader roda uma vez por vez, um resultado antigo nunca sobrescreve um
  novo e a falha de um loader não impede os outros. Falha com dados na tela mantém os
  dados e mostra um aviso com "Tentar de novo"; sem dados mostra o erro por motivo.
- **Escrita:** toda gravação das telas é `run(mutations.x(input), "chave.sucesso")` pelo
  hook `useRunAction` (`src/components/Feedback.tsx`). No preview aplica-se a mutação
  pura na memória. No live o store lê `mutation.meta = { key, input }` e procura a ação
  remota registrada para essa `key`: **sem ação registrada o resultado é `unavailable`
  (nunca se finge sucesso)**; com ação ok, recarrega as fatias indicadas; rede/tempo
  esgotado → `offline` (snapshot intacto); 4xx → `rejected` + `code`; sessão perdida →
  `session`; `402` → `blocked`. Duas gravações simultâneas da **mesma** ação com a mesma
  entrada viram uma só (trava por `key` + entrada), contra registro duplicado por toque
  duplo. As telas só dizem "salvo" com `ok: true`; as falhas têm texto acolhedor por
  motivo (`failureFeedback`).

### Como um domínio liga a sua API (um arquivo novo + uma linha em cada registro)

Nenhuma tela nem o store precisam mudar. Exemplo para o cuidado (`medications`,
`doseLogs`, `logDose`, `undoDose`):

1. **Loader.** Crie `src/data/live/care.ts` e valide sempre o corpo com os parsers de
   `src/api/parse.ts` (erro de formato vira `malformed_response`):

   ```ts
   import { LoaderEntry } from "./registry";

   export const careLoader: LoaderEntry = {
     slices: ["medications", "doseLogs"],   // fatias que ESTE loader preenche
     load: async (api) => {
       const data = await api.get("/mobile/medications/", { parse: parseMedications });
       return { medications: data.medications, doseLogs: data.doseLogs };
     },
   };
   ```

   Registre em `src/data/live/registry.ts`: `import { careLoader } from "./care";` e uma
   linha em `LOADERS`. Regras: uma fatia pertence a um único loader (teste confere); o
   loader só altera as fatias que declarou; erros de API podem subir (`ApiError`).
2. **Ações.** No mesmo arquivo, exporte um `LiveActionRegistry` cujas chaves são os
   nomes das mutações de `src/data/mutations.ts` (a entrada é tipada pela mutação):

   ```ts
   export const careActions: LiveActionRegistry = {
     logDose: {
       run: (input) => async (api) => {
         await api.put(`/mobile/medications/${input.medicationId}/doses/`, { /* ... */ });
         return { ok: true };
       },
       refresh: ["doseLogs"],               // fatias recarregadas depois do sucesso
     },
   };
   ```

   Registre em `src/data/live/actions.ts`: importe e acrescente `...careActions` em
   `LIVE_ACTIONS`. Devolva `{ ok: false, reason: "invalid", code? }` para recusar a
   entrada sem ir ao servidor; não grave nada localmente (o snapshot só muda quando as
   fatias de `refresh` forem recarregadas); deixe os erros de API subirem.
3. **Textos e testes.** Códigos de erro novos entram em `src/i18n/errorCodes.ts` e nos
   três catálogos. Os testes usam o servidor falso de `tests/fakeApi.ts`
   (`createFakeServer`) e `tests/helpers.tsx` (`renderApp({ mode: "live", transport,
   signedIn: true })`); `tests/live-engine.test.ts` mostra loaders e ações de ponta a
   ponta.

## Execução

```sh
cd mobile/posalta
npm ci
npm run format:check && npm run typecheck && npm test
npm run start:preview        # Expo com dados de demonstração
npm run export:preview       # web estático em dist-preview/
python3 scripts/serve-spa.py dist-preview 8790   # servir o export (fallback SPA)
EXPO_NO_DOTENV=1 npx expo install --check
EXPO_NO_DOTENV=1 npx expo-doctor
npm run export               # JS web + bytecode Hermes iOS/Android (não gera IPA/APK)
```

`npm test` fixa `TZ=America/Sao_Paulo` e usa relógio injetado (2026-10-02 09:00).

## Mapa de contratos: API do paciente (backend)

O backend tem a API do app em `/api/v1/mobile/` (sessão por token, todas as rotas
restritas ao paciente da sessão). Contrato completo, regras de segurança e códigos de
erro: [`docs/mobile-patient-api.md`](../../docs/mobile-patient-api.md). O token do app só
vale nessas rotas.

| Tela / funcionalidade | Rota | No app |
|---|---|---|
| Entrar, ativar, recuperar e redefinir senha, renovar, sair, aparelhos | `/mobile/auth/…` (token de acesso 15 min, renovação rotativa) | **ligado** |
| Hoje, perfil, equipe, data da alta | `GET /mobile/me/` | **ligado** (loader `patient`) |
| Check-in diário, diário, pedidos de acesso | `/mobile/diary/`, `/mobile/checkins/`, `/mobile/journal/…` | loader/ações a registrar |
| Metas | `/mobile/goals/…` | loader/ações a registrar |
| Agenda | `/mobile/appointments/…`, `/mobile/booking/options/` | loader/ações a registrar |
| Medicação e doses | `/mobile/medications/…` | loader/ações a registrar |
| Plano de cuidado e resposta | `/mobile/care-plan/…` | loader/ações a registrar |
| Rotina e hábitos | `/mobile/routine/`, `/mobile/habits/{id}/checks/{data}/` | loader/ações a registrar |
| Exercícios da equipe | `/mobile/exercises/…` | loader/ações a registrar |
| Pouca energia | `/mobile/low-energy/` | loader/ações a registrar |
| Recuperação, contador, vontade de usar | `/mobile/recovery/…` | loader/ações a registrar |
| Prevenção de recaída | `/mobile/relapse-plan/` | loader a registrar |
| Ajuda urgente | `/mobile/help/` (sem efeito colateral; funciona mesmo com cobrança bloqueada) | tela local hoje; loader do plano pessoal a registrar |
| Rede de apoio | `/mobile/support-network/…` | loader/ações a registrar |
| Conteúdos | `/mobile/content/` | loader a registrar |
| Consentimentos | `/mobile/consents/…` | loader/ações a registrar |
| Direitos LGPD | `/mobile/privacy-requests/` | loader/ações a registrar |

Ao ligar cada domínio, respeite os ajustes de contrato de "Diferenças em relação ao
protótipo" no documento da API (escopos de apoio, intensidade 1–10, favorito/lido, papéis
da equipe, status de LGPD, senha para trocar escopo e consentimentos por documento).

## Verificado e não verificado

- **Verificado (execução local):** `tsc`, Prettier, 384 testes Jest em 16 arquivos, sem
  warnings (tokens, i18n e mensagens por código de erro, regras de domínio, mutações e
  seus metadados, cliente HTTP com renovação em voo único, cofre de tokens, sessão,
  links do app, motor do store live, telas de entrada e saída pela navegação real,
  fluxos do preview, modo `live` sem dado clínico, escopo), `expo install --check`,
  `expo-doctor` 18/18 e `expo export --platform all` (web + Hermes iOS/Android, com
  `EXPO_PUBLIC_API_BASE_URL` incorporada ao pacote).
- **Como os testes falam com o "servidor":** transporte falso (`tests/fakeApi.ts`) e
  cofre seguro simulado (`tests/setup.js`). Nenhuma chamada real ao backend foi feita.
- **Pendência herdada:** `npm audit --omit=dev` aponta vulnerabilidades no ferramental
  transitivo do Expo/RN, as mesmas dos apps `b2c`/`connected`. Não foi feito
  `audit fix` forçado; segue o bloqueio nº 1 de `docs/migration/mobile-readiness.md`.
- **Não verificado:** build nativo iOS/Android, aparelho real, `expo-secure-store` de
  verdade (Keychain/Keystore), links `auroraelo-posalta://` abrindo o app pelo sistema,
  VoiceOver/TalkBack, texto ampliado no aparelho e a integração com o backend em
  execução (o contrato foi seguido pela leitura de `docs/mobile-patient-api.md` e de
  `api/mobile_*_api.py`). No iOS o Keychain pode sobreviver à reinstalação do app: a
  sessão guardada seria restaurada até a renovação vencer (30 dias); decidir se vale
  apagá-la na primeira abertura depois de instalar. Lembretes por notificação **não
  existem** (o app não pede permissão de notificações; `blockedPermissions` mantido).
