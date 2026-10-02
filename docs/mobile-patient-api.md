# API do app do paciente (pós-alta)

Contrato HTTP usado pelo app `mobile/posalta`. Prefixo: `/api/v1/mobile/`. Documentação
interativa (somente equipe): `/api/v1/docs/`.

Escopo: **só o que o paciente enxerga e faz sobre os próprios dados**. O sistema web é só
da equipe da clínica: paciente não entra no web (login, escolha de clínica e sessão web
recusam o vínculo de paciente) e não há tela web de paciente. A régua de
acompanhamento pós-alta (ligações aos 7 e 15 dias, visita aos 15), o concierge, o contato
com a família e as mensagens com a equipe pertencem ao aplicativo da clínica e **não**
têm rota aqui. Da alta sai apenas a data (`discharge_date`), para contar os dias.

## Autenticação

Somente `Authorization: Bearer <token de acesso>`. Cookie de sessão não vale nestas rotas
(sem CSRF). Os tokens são opacos, com prefixo (`aem_` acesso, `aer_` renovação).

| Passo | Rota | Observações |
|---|---|---|
| Ativar conta | `POST /mobile/auth/activate/` | `code` (do convite), `password`, `first_name`, `last_name`; já abre a sessão. Quem já tem conta informa a senha atual |
| Recuperar senha | `POST /mobile/auth/password-recovery/` | `email`; resposta sempre `202`; só paciente recebe e-mail |
| Redefinir senha | `POST /mobile/auth/password-reset/` | `code` (`uid.token` do e-mail), `new_password`; derruba todas as sessões |
| Entrar | `POST /mobile/auth/login/` | `email`, `password`, `device_label`, `platform` (`ios`/`android`), `app_version`, `clinic_id` (só se houver mais de uma clínica) |
| Renovar | `POST /mobile/auth/refresh/` | troca o par; o token de renovação anterior **deixa de valer** |
| Sair | `POST /mobile/auth/logout/` | encerra este aparelho |
| Aparelhos | `GET /mobile/auth/sessions/`, `DELETE /mobile/auth/sessions/{id}/`, `POST /mobile/auth/sessions/revoke-others/` | só os da própria pessoa; id alheio = 404 |

Regras de segurança (todas testadas em `tests/test_mobile_api_auth.py`):

- **Mesmo orçamento de tentativas do login web.** `verify_credentials` reutiliza as chaves
  de limite de `accounts`: trocar de canal não zera as tentativas (`429`).
- **Falha indistinguível.** Senha errada, e-mail inexistente, usuário inativo e credencial
  correta de quem **não é paciente** respondem o mesmo `401 invalid_credentials`.
- **Só paciente.** Exige vínculo ativo com papel `patient` e perfil de paciente ligado ao
  usuário. Equipe usa o sistema web.
- **Clínica e paciente presos à sessão**, decididos no servidor. `X-Clinic-ID`,
  `?clinic_id=` ou `?patient_id=` são ignorados. Mais de uma clínica → `409
  clinic_choice_required` com a lista, e o app reenvia com `clinic_id`.
- **Token de acesso curto (15 min)**; renovação válida por 30 dias; vida absoluta da sessão
  90 dias. Ajustáveis por `MOBILE_ACCESS_TOKEN_SECONDS`, `MOBILE_REFRESH_TOKEN_DAYS`,
  `MOBILE_SESSION_ABSOLUTE_DAYS` e `MOBILE_MAX_SESSIONS_PER_USER` (padrão 5; o aparelho mais
  antigo é substituído).
- **Renovação rotativa com detecção de reuso.** Apresentar de novo um token já trocado
  revoga a sessão inteira (o par copiado e o legítimo). O app deve **serializar** as
  renovações (uma por vez); duas simultâneas derrubam a sessão.
- **Só o resumo SHA-256 é gravado**, nunca o token. Os tokens têm 256 bits.
- **Revalidação a cada uso**: troca de senha (`credentials_changed_at`), usuário inativo,
  papel/vínculo vencido ou clínica inativa derrubam a sessão na hora (`401`).
- **Cobrança bloqueada** na clínica responde `402`, como no web, **exceto** `/mobile/help/` e
  o logout: o paciente não perde a própria ajuda urgente por pendência da clínica.
- Todas as respostas de `/api/` levam `Cache-Control: private, no-store`.
- Auditoria (`audit`, `resource_type=mobile_session`, nunca com token): `login` e as
  revogações (`update`); recusa de renovação que revoga a sessão (reuso, vínculo perdido)
  fica como `denied`. A renovação de rotina (a cada ~15 min por aparelho) não é auditada.
- Retenção: `python manage.py purge_mobile_sessions [--days 30]` remove sessões vencidas ou
  revogadas há mais de N dias.

**O token do app só vale em `/api/v1/mobile/`.** As rotas genéricas (`/api/v1/journal/`,
`/goals/`, `/scheduling/`) seguem por sessão e recusam o token (testado). Convite e
recuperação: o e-mail do paciente leva o código e um link `auroraelo-posalta://activate?code=…`
(ou `reset?code=…`) que abre o app (`MOBILE_APP_SCHEME`). A equipe vê o código **uma vez** ao
convidar e ele também segue por e-mail; a clínica não consegue consultá-lo depois.

## Erros

Corpo estável `{"detail": "...", "code": "..."}`. O app escolhe o texto pelo `code`; `detail`
é só diagnóstico (pt-BR). Códigos usados: `invalid_credentials`, `rate_limited`,
`clinic_choice_required`, `invalid_token`, `not_found`, `invalid_dose_time`,
`timezone_required`, `plan_closed`, `invalid_date`, `not_scheduled`, `already_completed`,
`invalid_response`, `unsupported`, `no_actions_configured`, `invalid_intensity`,
`invalid_scope`, `reauthentication_failed`, `consent_rejected`, `revocation_rejected`,
`already_open`, `rejected`. `422` também cobre validação de formato (pydantic).

**Posse.** Os serviços de rotina, medicação e bem-estar autorizam só por clínica. Cada rota
resolve o objeto **restrito ao perfil do paciente da sessão** antes de gravar; id de outra
pessoa (mesma clínica ou outra) responde `404` e nada é gravado. Há teste por rota.

## Rotas

| Tela do app | Rota | Domínio |
|---|---|---|
| Hoje / Perfil | `GET /mobile/me/` | `people`, `concierge` (só a data da alta) |
| Check-in e diário | `GET /mobile/diary/`, `POST /mobile/checkins/`, `POST /mobile/journal/`, `PUT /mobile/journal/{id}/visibility/` | `journal` |
| Pedidos de acesso ao diário | `GET /mobile/journal/access-requests/`, `POST /mobile/journal/access-requests/{id}/respond/` | `journal` |
| Metas | `GET /mobile/goals/`, `PUT /mobile/goals/steps/{id}/`, `PUT /mobile/goals/{id}/status/` | `goals` |
| Agenda | `GET /mobile/appointments/`, `GET /mobile/booking/options/`, `POST /mobile/appointments/`, `POST /mobile/appointments/{id}/cancel/`, `POST /mobile/appointments/{id}/reschedule/` | `scheduling` |
| Cuidado: medicação | `GET /mobile/medications/`, `PUT /mobile/medications/{id}/doses/` | `routines` |
| Cuidado: plano | `GET /mobile/care-plan/`, `POST /mobile/care-plan/{id}/response/` | `routines` |
| Cuidado: rotina | `GET /mobile/routine/?days=7`, `PUT`/`DELETE /mobile/habits/{id}/checks/{AAAA-MM-DD}/` | `routines` |
| Cuidado: exercícios | `GET /mobile/exercises/`, `POST /mobile/exercises/{id}/complete/` | `goals` |
| Pouca energia | `GET`/`PUT /mobile/low-energy/` | `goals` |
| Diário: recuperação | `GET /mobile/recovery/`, `PUT /mobile/recovery/counter/`, `POST /mobile/recovery/restart/`, `POST /mobile/recovery/cravings/` | `wellness` |
| Cuidado: recaída | `GET /mobile/relapse-plan/` | `wellness` |
| Ajuda | `GET /mobile/help/` | `wellness`, `support_network` |
| Apoio | `GET /mobile/support-network/`, `PUT /mobile/support-network/{id}/scopes/` (exige senha), `DELETE /mobile/support-network/{id}/` | `support_network`, `accounts` |
| Apoio: conteúdos | `GET /mobile/content/` | `content` |
| Perfil: consentimentos | `GET /mobile/consents/`, `GET /mobile/consents/{doc}/`, `POST /mobile/consents/{doc}/decision/`, `POST /mobile/consents/{doc}/revoke/` | `consents` |
| Perfil: LGPD | `GET`/`POST /mobile/privacy-requests/` | `privacy` |

Regras que o app precisa respeitar:

- **Doses** (`PUT …/doses/`): `scheduled_for` com fuso, exatamente um horário programado do
  medicamento (`HH:MM` no fuso do paciente), dentro do curso, até 7 dias atrás e até 30
  minutos à frente. `status`: `taken`, `late`, `omitted`; `not_reported` desfaz. Não há
  campo de observação nem "compensação" de dose.
- **Plano de cuidado**: rascunho e "aguardando assinatura" nunca aparecem. **Recusar encerra
  o plano; pausar o pausa** (regra do domínio) e plano encerrado não aceita nova resposta
  (`409 plan_closed`). O app deve dizer isso antes de confirmar.
- **Hábitos**: de hoje até 7 dias atrás; o hábito precisa estar previsto para o dia
  (`422 not_scheduled`). `DELETE` desfaz o registro e deixa auditoria na clínica.
- **Exercícios**: formatos `text` e `scale_1_5` (resposta `"1"`–`"5"`); outros formatos
  respondem `422 unsupported`. Uma única conclusão (`409 already_completed`).
- **Vontade de usar**: intensidade **1 a 10** (o domínio não aceita 0). Registro privado e
  protegido na tela travada.
- **Ajuda**: leitura **sem efeito colateral** (não registra acesso nem avisa ninguém). Os
  números abrem o discador só quando o paciente toca.
- **Rede de apoio**: escopos são os do domínio — `view_wellness_summary`,
  `receive_urgent_alerts`, `view_relapse_plan_safe`, `receive_checkin_summary`. O diário e
  registros clínicos não são compartilháveis. Mudar escopo exige `password` (reautenticação,
  com limite de tentativas). O e-mail e o telefone da pessoa de apoio não saem pela API.
- **Conteúdos**: só texto simples (o HTML saneado do servidor vira parágrafos e `•`).
  Indicações da equipe vêm primeiro, com o nome do profissional (credencial verificada).
  Favorito e "lido" **não existem no servidor**.
- **Consentimentos**: decisão é aceite ou recusa da versão **vigente**; aceite só sai pela
  revogação (documento opcional); obrigatório não é revogável por aqui. Reenviar com o
  mesmo `request_id` é idempotente. A origem fica gravada como `mobile_app`.
- **LGPD**: o pedido nasce `identity_pending` e só avança depois que um administrador da
  clínica verifica a identidade e decide. Um pedido aberto por tipo (`409 already_open`).
  Status devolvido é o do domínio: `identity_pending`, `in_review`, `approved`, `rejected`,
  `processing`, `completed`.

Agenda e diário (`tests/test_mobile_api_diary_agenda.py`):

- **Check-in**: as sete perguntas 1–5 (`general_state`, `anxiety`, `sadness`,
  `irritability`, `energy`, `sleep_quality`, `motivation`) e `notes`; reenviar no dia
  atualiza. O questionário padrão é criado na primeira vez se a clínica não tiver um.
  `visibility` padrão `private`.
- **Diário**: privado por padrão; compartilhar é escolha do paciente; voltar a privado
  revoga acessos já concedidos. Pedido de acesso da equipe (registro "confirmar antes")
  aparece em `access-requests/`; só o dono responde, uma vez.
- **Consultas**: profissional tem de ser da equipe **vinculada ao paciente**; unidade e
  serviço, ativos na clínica; o horário precisa estar livre naquele instante
  (`422 slot_unavailable`). `idempotency_key` é prefixada pelo paciente no servidor (a chave
  é única por clínica; sem o prefixo, duas pessoas poderiam colidir). A clínica confirma.
  Remarcar pede um **horário livre** (o domínio exige o novo horário) e fica
  `reschedule_requested`.

## Diferenças em relação ao protótipo do app

O protótipo foi desenhado antes da API. Para ligar o modo `live`, o app precisa ajustar:

| Protótipo | API |
|---|---|
| Escopos de apoio `view_goals`, `view_routine`, `view_appointments`, `receive_alerts` | os quatro escopos do domínio acima |
| Intensidade de vontade de usar 0–10 | 1–10 |
| Favorito / lido nos conteúdos | não persistem no servidor |
| Papéis de equipe `nurse`, `pharmacist` | `psychiatrist`, `psychologist`, `other` |
| Status de LGPD `identity_pending`/`in_review`/`completed` | acrescenta `approved`, `rejected`, `processing` |
| Troca de escopo sem senha | exige senha (reautenticação) |
| Consentimentos como 4 chaves fixas | lista de documentos vigentes da clínica, por `document_id` |

## Fora do escopo desta API (decisões em aberto)

- Notificações/lembretes: o servidor não envia nada ao app; a API não promete isso.
- Criar convites de apoio e editar o plano de recaída pelo app.
- Edição de medicação ou do plano de cuidado: é da equipe.
