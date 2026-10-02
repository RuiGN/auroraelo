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
  `{parâmetros}` verificada em teste. Só o idioma e a aparência são gravados no
  aparelho; textos de prontuário/equipe não são traduzidos.

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
| **Perfil** | equipe, idioma, aparência, consentimentos, direitos LGPD | `consents.*`, `privacy.DataSubjectRequest` |

## Dois modos (`EXPO_PUBLIC_APP_MODE`)

- **`live` (padrão):** dados reais. Como o backend ainda não tem sessão mobile nem
  contratos de API para o paciente (ver abaixo), **nenhum dado clínico é exibido** e
  toda gravação é recusada com mensagem explícita ("nada foi salvo ou enviado").
  A Ajuda urgente, idioma e aparência funcionam sem conexão.
- **`preview`:** demonstração com dados 100 % sintéticos mantidos só na memória,
  sinalizada por faixa em toda tela e selo "DEMO" no cabeçalho. Só liga se pedida na
  compilação: `npm run start:preview`, `npm run web:preview`, `npm run export:preview`.

A ajuda urgente nunca simula nada: abrir a tela não avisa ninguém, os números abrem o
discador **só quando o paciente toca**, e o texto diz que o app não é serviço de
emergência nem monitora em tempo real (alinhado ao `NO_DELIVERY` do backend).

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

## Mapa de contratos: o que existe e o que falta (Sprint 6, "APIs seguras")

Inspeção estática do backend (`api/*.py`, `psychiatry/api.py`, `config/urls.py`).
Nenhuma chamada foi feita e nenhum dado real foi lido.

| Funcionalidade do app | Endpoint hoje | Situação |
|---|---|---|
| Check-in diário | `GET/POST /api/v1/journal/checkins/` | existe |
| Diário | `GET/POST /api/v1/journal/entries/` | existe |
| Metas e passos | `/api/v1/goals/`, `/{id}/steps/`, `/steps/{id}/toggle/`, `/{id}/status/` | existe |
| Consultas | `/api/v1/scheduling/appointments/` (+ `reschedule`, `cancel`), `/services/`, `/appointments/free-slots/` | existe (`confirm`/`complete` são da clínica) |
| Medicação / adesão | só `psychiatry/api/v1/patient/summary` e `medications/log` (modelo `PrescriptionItem`, **não** `routines.PrescribedMedication`) | decidir qual modelo é a fonte do paciente |
| Plano de cuidado, hábitos, exercícios, prevenção de recaída, contador, vontade de usar, pouca energia, plano de apoio urgente, rede de apoio | modelos existem; **sem API** | criar |
| Conteúdo, consentimentos, direitos LGPD | só views HTML (`/conteudos/`, `/consents/`) | criar API JSON |
| Autenticação mobile | `SessionOrBearerAuth.authenticate` devolve `None` (TODO `ApiAccessToken`); middleware de clínica exige contexto | **bloqueio**: login/refresh/revogação, escopo paciente-clínica no servidor, tokens em SecureStore, testes cross-tenant |

Antes de trocar `live` por dados reais, seguir os bloqueios de
[`docs/migration/mobile-readiness.md`](../../docs/migration/mobile-readiness.md)
(sessão, tenant, consentimento, auditoria, persistência real). Os números de
emergência e o plano de apoio urgente (`CrisisResourceConfig`, `UrgentSupportPlan`)
também precisam chegar por API para alimentar a tela de Ajuda.

## Verificado e não verificado

- **Verificado (execução local):** `tsc`, Prettier, 129 testes Jest sem warnings
  (tokens, i18n, regras de domínio, mutações, fluxos pela navegação real, modo `live`
  sem dado clínico, escopo), `expo install --check`, `expo-doctor` 18/18,
  `npm run export` (web + Hermes iOS/Android) e conferência visual no navegador em
  390×844 (claro e escuro).
- **Pendência herdada:** `npm audit --omit=dev` aponta 24 vulnerabilidades (11
  moderadas, 12 altas, 1 crítica), as mesmas dos apps `b2c`/`connected` (ferramental
  transitivo do Expo/RN). Não foi feito `audit fix` forçado; segue o bloqueio nº 1 de
  `docs/migration/mobile-readiness.md`.
- **Não verificado:** build nativo iOS/Android, aparelho real, VoiceOver/TalkBack,
  texto ampliado no aparelho, integração com backend. Lembretes por notificação
  **não existem** (o app não pede permissão de notificações; `blockedPermissions`
  mantido).
