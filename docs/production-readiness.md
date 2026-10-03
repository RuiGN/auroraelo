# Prontidão para produção — Aurora Elo (web da equipe + app Pós-Alta)

Estado em 2026-10-03. O repositório (`origin/gemini`, `9915b34`) contém apenas esta linha
de trabalho (a outra linha — ativação por PIN, PWA da equipe — ficou no histórico, como
segundo pai do commit de mesclagem) e **a VPS roda esse commit** desde 2026-10-03 02:23 UTC.

## Entrada no web da equipe

- **Login único** (sem abas): **CPF + senha**, para todas as funções da equipe. Depois de
  entrar, o sistema monta menu e início conforme a função (gestor, terapeuta, administrativo).
  O e-mail serve para recuperar a senha. A operação da plataforma entra em `/master/login/`
  com e-mail e senha. O app do paciente continua entrando por e-mail.
- **O gestor cadastra os usuários** em *Usuários e equipe → Cadastrar usuário* (nome, CPF,
  e-mail e função). O sistema gera uma senha aleatória (16 caracteres, ex.:
  `Kp7m-Xw3r-Tn9v-Bc4z`) e a mostra uma única vez, sem cache; o gestor repassa por canal
  seguro. Há "Redefinir senha" por pessoa.
- **Troca obrigatória no primeiro acesso:** enquanto `must_change_password` for verdadeiro,
  todo caminho (exceto trocar senha e sair) redireciona para a tela de troca.
- Matriz de funções e menus: `docs/authorization-matrix.md`.

## Modelo do produto

- **Web (`auroraelo/`) é só da equipe da clínica.** Paciente não entra no web.
- **App Pós-Alta (`mobile/posalta`) é do paciente.** Fala só com `/api/v1/mobile/`.
- A equipe cadastra no web o que o paciente **recebe** (medicação, plano de cuidado,
  hábitos, exercícios, serviços e horários, recursos de crise). O paciente edita no app o
  que é **dele e privado** (meta de recuperação, plano de recaída, plano de apoio urgente,
  ações de pouca energia, diário e check-in). A equipe só vê o que o paciente compartilha.

## O que está pronto e verificado

| Área | Estado | Evidência |
|---|---|---|
| Web só da equipe (paciente barrado, telas de paciente removidas) | pronto | `tests/test_patient_web_boundary.py` |
| Login por CPF, cadastro com senha gerada, troca no primeiro acesso, menus por função | pronto (em produção a partir do deploy do login por CPF) | `tests/test_team_registration.py`, `tests/test_accounts_authentication.py` |
| API do paciente (59 operações, sessão por token, posse por perfil) | pronta | suíte do web: 3137 passam |
| Ativação e recuperação de senha pelo app (código + link) | pronta | `tests/test_mobile_api_accounts.py` |
| Telas da equipe: medicação, plano de cuidado, hábitos | prontas | `tests/test_routines_staff_*.py` |
| Telas da equipe: serviços, horários de atendimento, recursos de crise | prontas | `tests/test_clinic_setup_staff_views.py` |
| Telas da equipe: diário e check-ins compartilhados, pedido de acesso | prontas | `tests/test_journal_staff_views.py` |
| Painel "Aplicativo do paciente" (convite, aparelhos, revogar sessões) | pronto | `tests/test_mobile_api_staff_views.py` |
| App ligado à API (22 fatias do estado, todas as gravações) | pronto em teste | 406 testes Jest, `tsc`, Prettier, `expo export` |
| Contrato app × servidor | conferido por teste | foto do OpenAPI + `tests/contract-live.test.ts` |
| App × servidor em execução (SQLite local) | 13 de 13 | `npm run test:e2e` |
| App × servidor com PostgreSQL, Redis, gunicorn e SMTP | 15 de 15 | `npm run test:e2e:staging` |
| Aceite obrigatório de consentimentos no primeiro acesso | pronto (no cliente) | `tests/consent-gate.test.tsx` |

A única falha da suíte do web é `test_repository_matrix_passes_completeness_gate…`: a data
de revisão da matriz regulatória (`docs/compliance/cfp-crp02-matrix.json`) venceu em
2026-09-30. É revisão humana de conformidade, não código.

## O que NÃO foi verificado (risco real)

1. **Contra o servidor de verdade (feito, em ambiente local).** O roteiro
   `mobile/posalta/tests/e2e` (`npm run test:e2e`) roda o código real do app contra o
   Django em execução, com banco descartável: ativação, 18 loaders, aceite, cuidado,
   diário, agenda, conteúdo pessoal, perfil, renovação e reuso de token, saída — 13 de 13
   passam. Há também a versão em ambiente fiel ao de produção
   (`npm run test:e2e:staging`: PostgreSQL 17, Redis 8, settings de produção, gunicorn
   com 3 processos e SMTP real de captura), com recuperação de senha por e-mail e limite de
   tentativas compartilhado: 15 de 15 passam, sem nenhum erro no log do servidor. Falta
   rodá-lo contra um ambiente remoto de teste (rede, TLS, SMTP do provedor).
2. **Nada rodou em aparelho real:** Keychain/Keystore (`expo-secure-store`), links
   `auroraelo-posalta://`, VoiceOver/TalkBack, texto ampliado, teclado, modo escuro.
3. **E-mail:** convite do paciente e recuperação de senha dependem de SMTP. **O `.env` da
   VPS não define `MAILER_*`** (conferido em 2026-10-03): o cadastro de usuários da equipe
   funciona sem e-mail (a senha aparece na tela), mas "esqueci a senha" e o convite do app
   não chegam enquanto o SMTP não for configurado.
4. **Revisão clínica** das telas de prescrição, plano de cuidado e textos do app
   (linguagem, avisos, limites do serviço) por profissional habilitado.
5. **Traduções en/es** foram feitas sem revisão humana.

## Decisões suas (bloqueiam ou mudam escopo)

- **Rede de apoio (família/pessoas de confiança):** o app mostra e revoga, mas **não há
  como criar convite** nem tela para a pessoa aceitar. Recomendação: esconder no v1 e
  entregar na v1.1 junto da superfície da pessoa de apoio. O "plano de apoio urgente"
  (telefones de confiança) já funciona sem isso.
- **Aceite de documentos:** hoje é só no cliente. Recomendação: o servidor recusar rotas
  de dados enquanto houver documento obrigatório pendente (exceto consentimentos, ajuda e
  sair).
- **Notificações/lembretes:** não existem (o app não pede permissão). Se forem requisito
  do v1 é trabalho novo (servidor + app).
- **`/api/v1/recovery/` (IA B2C) e protótipos `mobile/b2c` e `mobile/connected`:** manter
  ou remover.
- **Revisão da matriz regulatória** (data vencida).

## Falta para colocar em produção (estimativa por pessoa, faixas)

| Etapa | Itens | Estimativa |
|---|---|---|
| **A. Piloto interno** (TestFlight / APK interno, 1 clínica) | roteiro de fumaça em ambiente com PostgreSQL/Redis/SMTP; SMTP; `EXPO_PUBLIC_API_BASE_URL` e `eas.json`; conta Apple/Google; build iOS/Android; correções do que aparecer em aparelho | 1–2 semanas |
| **B. Endurecimento** | teste de invasão da API e do app; `npm audit`; servidor recusando dados sem aceite; revisão de privacidade (RIPD/LGPD, política, exclusão de conta no app para a Apple); backup e monitoramento | 2–3 semanas |
| **C. Conformidade e conteúdo** | revisão clínica; revisão humana en/es; matriz regulatória; textos legais por clínica | 2–4 semanas (depende de terceiros) |
| **D. Lojas** | fichas de privacidade, capturas, revisão da Apple/Google | 1–2 semanas |
| **E. Opcional v1** | rede de apoio com convites; notificações; resumo de adesão para a equipe | 3–6 semanas |

Caminho mais curto para um **piloto controlado**: A, com B em paralelo. **Produção
aberta**: A+B+C+D, na ordem de 6–10 semanas se não houver bloqueio externo.

## Publicação (quando for a hora)

1. Reconstruir a imagem e subir; o `entrypoint.sh` já aplica `migrate` (inclui
   `concierge.0001`, `mobile_api.0001–0002`) e `collectstatic`.
2. Conferir no `.env` de produção: `MAILER_*`, `DEFAULT_FROM_EMAIL`, `MOBILE_APP_SCHEME`,
   `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.
3. Agendar `python manage.py purge_mobile_sessions` (retenção das sessões do app).
4. Cadastrar na clínica, pelo web: serviços e horários, recursos de crise, documentos de
   consentimento vigentes; convidar o primeiro paciente pelo painel do aplicativo.
