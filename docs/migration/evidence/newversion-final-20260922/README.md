# Evidências — execução de 2026-09-22 (continuação do `NEWVERSION.prd`)

Checkout: `/Users/rgnsystems/projects/auroraelo` (branch `gemini`), sem commit, sem push,
sem deploy e sem qualquer operação na VPS.

Todos os valores de credencial usados nos ensaios são sintéticos e redigidos neste
documento. Nenhum `.env`, banco, upload, prontuário ou usuário real foi consultado.

## 1. Comandos e resultados

| Verificação | Comando | Resultado | Log |
| --- | --- | --- | --- |
| Suíte completa — PostgreSQL descartável | `TEST_DATABASE=postgresql ... .venv/bin/pytest -q --no-cov --junitxml=...` | `1 failed, 2680 passed, 17 skipped` em 6m02s | `pytest-postgresql-full.log`, `pytest-postgresql-junit.xml` |
| Suíte completa — SQLite de teste (árvore final, após as correções da revisão) | `.venv/bin/pytest -q --no-cov --junitxml=...` | `2675 passed, 29 skipped`, `pytest_sqlite_exit=0` | `pytest-sqlite-full.log`, `pytest-sqlite-junit.xml` |
| Foco em PostgreSQL após as correções da revisão | `TEST_DATABASE=postgresql ... pytest tests/test_user_administration.py tests/test_master_panel_tenants.py tests/test_clinic_authorization.py tests/test_security_controls.py tests/test_master_bootstrap.py` | `56 passed`, `pg_focus_exit=0` | `pytest-postgresql-focused.log` |
| Suíte SQLite completa após a terceira rodada de revisão | `.venv/bin/pytest -q --no-cov --junitxml=...` | `2683 passed, 29 skipped`, `pytest_sqlite_r2_exit=0` | `pytest-sqlite-full-r2.log`, `pytest-sqlite-junit-r2.xml` |
| Foco em PostgreSQL após a terceira rodada | `docker compose -f compose.test.yml up -d --wait postgres`, `TEST_DATABASE=postgresql ... pytest` (8 arquivos, com o novo `tests/test_authorization_hardening.py`) | `87 passed`, `pg_focus_r2_exit=0` | `pytest-postgresql-focused-r2.log` |
| Suíte SQLite completa após a correção do storage | `.venv/bin/pytest -q --no-cov --junitxml=...` | `2686 passed, 29 skipped`, `pytest_sqlite_r3_exit=0` | `pytest-sqlite-full-r3.log`, `pytest-sqlite-junit-r3.xml` |
| Suíte SQLite completa após a correção do storage | `.venv/bin/pytest -q --no-cov --junitxml=...` | `2686 passed, 29 skipped`, `pytest_sqlite_r3_exit=0` | `pytest-sqlite-full-r3.log`, `pytest-sqlite-junit-r3.xml` |
| Catálogo UI escopado após o novo msgid | `.venv/bin/python scripts/check_ui_catalogs.py --scope docs/migration/translated-ui-scope.json ...` | `passed; 1422 keys` | `ui-catalog.log`, `ui-catalog-check.json`, `ui.pot` |
| Ruff (checkout atual) | `.venv/bin/ruff check .` | `Found 140 errors` (132 `E501`, 6 `E402`, 1 `F841`, 1 `N806`) | `ruff-check.log` |
| Ruff (`HEAD` baseline) | `.venv/bin/ruff check .` no snapshot do `HEAD` | `Found 178 errors` | `ruff-check-head-baseline.log` |
| Ruff format (checkout atual) | `.venv/bin/ruff format --check .` | `19 files would be reformatted` | `ruff-format.log` |
| Ruff format (`HEAD` baseline) | `.venv/bin/ruff format --check .` no snapshot | `25 files would be reformatted` | `ruff-format-head-baseline.log` |
| mypy (checkout atual) | `.venv/bin/mypy` | `Found 728 errors in 33 files (checked 649 source files)` | `mypy-current.log` |
| mypy (`HEAD` baseline) | `.venv/bin/mypy` no snapshot do `HEAD` | `Found 732 errors in 35 files` | `mypy-head-baseline.log` |
| Catálogo UI escopado | `.venv/bin/python scripts/check_ui_catalogs.py --scope docs/migration/translated-ui-scope.json ...` | `passed; 1421 keys` | `ui-catalog.log`, `ui-catalog-check.json`, `ui.pot` |
| Catálogo DjangoJS | `.venv/bin/python scripts/check_djangojs_catalogs.py ...` | `passed` | `djangojs-catalog.log` |
| Scanner de segredos | `.venv/bin/python scripts/check_secrets.py` | `Secret scan passed.` | `secrets.log` |
| E2E Playwright (modo CI, SQLite descartável) | `DJANGO_SETTINGS_MODULE=config.settings.test SQLITE_NAME=... npm test` | `22 passed (5.7s)`, `e2e_exit=0` | `e2e-ci-mode.log`, `e2e-ci-mode-migrate.log` |
| Mobile `b2c` (4 checagens) | `npm run format:check`, `npm run typecheck`, `npm test`, `EXPO_NO_DOTENV=1 npm run export` | 4/4 `rc=0` | `mobile-b2c-checks.log` |
| Mobile `connected` (4 checagens) | idem | 4/4 `rc=0` | `mobile-connected-checks.log` |
| Settings de produção e réplica | imports com variáveis sintéticas (sem réplica, com réplica, env obrigatória ausente, réplica malformada) e `manage.py check --deploy` | imports: `databases: ['default']` e `['default', 'replica']`; ausente/malformada falham com mensagem redigida; `check --deploy` → 1 advertência (`security.W009`, `SECRET_KEY` sintética curta) | `production-settings-check.log` |

Os ensaios de shell e o `manage.py check --deploy` usaram exclusivamente valores
sintéticos (`synthetic-*`, `*.synthetic`, banco descartável
`auroraelo_final` em contêiner `postgres:17-alpine` na porta 55433, removível).
Nenhum contêiner existente foi parado, alterado ou removido com `down -v`.

## 2. Dívida legada versus regressão introduzida

Comparação por arquivo contra o snapshot do `HEAD` (`$TMPDIR/auroraelo-head-snapshot`):

- **Ruff**: 178 → 140 erros; **nenhum arquivo** passou a ser sinalizado (diferença de
  conjuntos de arquivos sinalizados = ∅). O restante é `E501` em arquivos de seed e
  legado (`psychiatry/management/commands/seed_psychiatry.py` 80 ocorrências,
  `clinics/management/commands/create_aurora_clinic.py` 22, `psychiatry/tests.py` 17,
  `psychiatry/urls.py` 12) mais `E402`/`F841`/`N806` antigos.
- **Ruff format**: 25 → 19 arquivos; nenhum arquivo novo entrou na lista.
- **mypy**: 732 → 728 erros em 35 → 33 arquivos; nenhum arquivo com mais erros que o
  baseline. `config/settings/production.py` e `config/settings/test.py` saíram da lista
  (eram 3 erros no `HEAD`).
- **Suíte completa**: no SQLite de teste, a execução anterior deste trabalho tinha
  `18 failed`; agora passa. Falhas remanescentes em PostgreSQL estão descritas abaixo.

Conclusão: as vermelhidões de Ruff/format/mypy que restam são dívida anterior ao
trabalho, não regressão. Elas não foram mascaradas com `noqa`, ignores ou relaxamento de
configuração.

## 3. Falha remanescente em PostgreSQL (pré-existente)

`tests/test_psychiatry_secondary_waits.py::test_membership_revocation_cannot_commit_before_pending_evaluation`
é **skipped** no SQLite de teste e **falha** com `TEST_DATABASE=postgresql`:

```
assert (200, 1) in {(403, 0), (404, 0), (409, 0)}
tests/test_psychiatry_secondary_waits.py:153
```

A mesma asserção falha com o **mesmo texto** ao rodar esse teste isolado no snapshot do
`HEAD` com o mesmo banco PostgreSQL descartável, o que caracteriza falha pré-existente
do domínio `psychiatry` em PostgreSQL e não regressão deste trabalho. O domínio não foi
alterado nesta sessão.

## 4. Limitações explícitas

- Validação visual interativa (foco, teclado, overflow em mobile real) não foi
  executada; a cobertura renderizada se limita a asserções HTTP e Playwright em desktop.
- Conectividade real worker↔RabbitMQ não foi exercitada em contêiner nesta sessão; o que
  foi validado é a renderização do Compose com web e worker apontando para o mesmo broker
  e Redis como backend de resultado.
- Nenhuma validação na VPS, nenhum commit, push, imagem ou deploy.
- Os pacotes do OpenTelemetry não estão instalados localmente; a redação de PII é
  exercitada com exporter sintético, não contra coletor real.
- `expo-doctor` e `expo install --check` exigem rede e não foram incluídos no gate.

## 5. Verificação de broker Celery/RabbitMQ (parcial)

Ensaio com broker e backend descartáveis e valores sintéticos (usuário
`auroraelo_sintetico`, senha sintética, portas 55672/56379). Provado:

- o worker lê a configuração correta (`transport: amqp://…@127.0.0.1:55672//`,
  `results: redis://127.0.0.1:56379/2`) e conecta no broker real
  (`Connected to amqp://…`, `verify@… ready.`);
- a fila `celery` é declarada, com `consumers=1` enquanto o worker está no ar;
- a tarefa despachada **sem eager** (`task_always_eager=False`) atravessa o broker
  (`celery messages=1 consumers=0` antes do worker) e é recebida por ele
  (`Task config.celery.debug_task[…] received`), voltando a fila a `messages=0`.

Não provado:

- a **execução** da tarefa no host macOS: o worker falha dentro do Celery com
  `ValueError: not enough values to unpack (expected 3, got 0)` em
  `celery/app/trace.py:762` (`fast_trace_task`, `tasks, accept, hostname = _loc`) com
  Python 3.14 e `celery==5.6.3`, que é a versão fixada em `requirements.txt` e a mesma
  base `python:3.14-slim` da imagem de produção. A tentativa de contornar com
  `--pool=solo` e a repetição em contêiner Linux (`auroraelo:latest`, que inicia
  corretamente e lê o mesmo `transport`/`results`) não puderam ser concluídas porque o
  contêiner descartável de RabbitMQ deixou de iniciar neste host
  (`Error when reading /var/lib/rabbitmq/.erlang.cookie: eacces`, exit 1) — limitação do
  ambiente local, não do repositório. Classificação honesta: **pendente**, não defeito
  confirmado, porque o comportamento pode ser específico do pool prefork no macOS; exige
  validação em Linux/CI antes de virar correção.

Arquivos de evidência: `celery-rabbitmq-connectivity.log` (conexão e fila),
`celery-rabbitmq-transport.log` (transporte real até o worker + traceback do Celery),
`celery-rabbitmq-transport-solo-pool.log` e `celery-rabbitmq-linux-worker.log`
(tentativas sem broker disponível). Nenhum contêiner do usuário foi usado, parado ou
alterado; os descartáveis foram removidos no fim.

## 6. Revisão independente e correções aplicadas

Revisão independente somente leitura (segurança, autorização e isolamento multi-clínica)
executada em contexto separado, sem acesso a produção, sem escrita de arquivos e sem
operações remotas. Retorno: `passed: false`, com 6 achados. Situação de cada um:

1. Reativação de vínculo profissional ignorava validade expirada
   (`people/views.py`, `clinics/services.py`) — **corrigido**: a regra foi extraída para
   `ensure_membership_activatable()` e passou a ser usada tanto por `set_membership_active`
   quanto por `_set_professional_membership_active`; a view passou a exibir o erro em vez de
   falhar silenciosamente.
2. Edição global no Master podia marcar vínculo expirado como ativo
   (`master_panel/user_services.py`) — **corrigido**: `link_or_update_membership` e
   `update_membership_as_operator` recusam `is_active=True` fora da janela de validade,
   usando a mesma função de domínio.
3. Django Admin permitia alterar privilégios globais sem serviço nem auditoria
   (`accounts/admin.py`) — **corrigido**: `is_active`, `is_staff`, `is_superuser`, `groups` e
   `user_permissions` passaram a ser somente leitura no formulário de alteração.
4. Bloqueio/desbloqueio de clínica não gerava auditoria
   (`master_panel/views/tenants.py`) — **corrigido**: criado `set_tenant_blocked()`, com
   operador ativo obrigatório e evento `account_audit_required`
   (`resource_type="tenant_subscription"`), usado pelas duas rotas.
5. `update_membership_role` salvava sem autoria nem auditoria
   (`clinics/services.py`) — **corrigido**: valida o papel contra `Role.values`, grava
   `authorized_by` e emite `membership_authorization_changed`.
6. Rótulos de papel/categoria sem tradução efetiva na UI nova — **corrigido** para as
   superfícies desta entrega: formulários e filtros do painel Master e da equipe passam a
   usar `translated_membership_role_choices()` e um mapa traduzido de categorias, e as
   listagens exibem `row.role_label`. Observação importante: `LANGUAGES` de runtime publica
   apenas `pt-br`, portanto o defeito era latente; as traduções `en`/`es` continuam nos
   catálogos e passam a ser usadas se esses idiomas forem publicados.

Regressões novas para os itens 1–6: `tests/test_user_administration.py`
(reativação expirada, ativação fora da validade pelo Master, privilégios globais somente
leitura, auditoria de bloqueio de clínica com operador ativo obrigatório, autoria e
auditoria de mudança de papel, rótulos traduzíveis e ausência de `get_role_display` nos
templates novos).

## 7. Terceira rodada de revisão independente (somente leitura, `passed: false`)

Rodada executada em contexto separado sobre as correções da seção 6. Escopo: revisão
somente leitura, sem commit, sem deploy, sem VPS e sem dados reais. Seis achados:

**Aceitos e corrigidos**

1. `ClinicMembershipAdmin` seguia editável fora dos serviços auditados
   (`clinics/admin.py`) — **corrigido**: `has_add_permission`, `has_change_permission` e
   `has_delete_permission` retornam `False` e `role`, `is_active`, `valid_from`,
   `valid_until` e `authorized_by` passaram a somente leitura.
2. `Clinic.is_active` editável no Django Admin permitia bloquear/liberar clínica sem
   auditoria — **corrigido**: campo somente leitura; a transição passa por
   `set_tenant_blocked()`.
3. Transições de status originadas no provedor de pagamento não geravam auditoria
   (`master_panel/services.py`) — **corrigido**: criado
   `audit_subscription_transition()` (`master_panel/tenant_services.py`), usado por
   `set_tenant_blocked()` e pelos cinco handlers de webhook, com `actor_id=None` e
   justificativa nomeando o gatilho (`subscription.created`, `subscription.updated`,
   `subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`,
   `checkout.session.completed`).
4. Mudança de papel por convite/seed sem evento de autorização
   (`clinics/services.py`, `clinics/management/commands/create_aurora_clinic.py`) —
   **corrigido**: `create_clinic_membership()` emite `membership_authorization_changed`
   quando há autorizador, `activate_invited_membership()` também na reativação, e o
   comando de seed (dados sintéticos de demonstração) grava `authorized_by` e emite o
   mesmo evento.
5. `update_membership_role` não era atômico com a persistência da auditoria —
   **corrigido**: `@transaction.atomic` no serviço.
6. Rótulos de papel com fallback para `get_role_display()` nas listagens — **corrigido**:
   `translated_membership_role_label()` (`accounts/forms.py`) é a única fonte, com o
   novo msgid `Papel não reconhecido` traduzido em `pt_BR`, `en` e `es` (catálogo
   escopado: 1422 chaves).

**Parcialmente rejeitado, com evidência**

O achado de que criação, aceitação de convite e edição profissional permitiriam janela
de validade inválida conflita com um estado de produto documentado:
`ClinicMembership.professional_status()` (`clinics/models.py:295-303`) devolve
`scheduled` para vínculo ativo com `valid_from` futuro, e
`tests/test_professional_management.py:135-150` cobre exatamente esse agendamento.
Rejeitar janela futura na criação/edição quebraria o fluxo de agendamento. A regra foi
então **refinada**: `ensure_membership_activatable()` bloqueia apenas validade já
**expirada** (`valid_until < hoje`) — o caso que originou a correção anterior — e
`create_clinic_membership()` ganhou `is_active` explícito, rejeitando `is_active=True`
com janela expirada e aceitando `is_active=False` para vínculos futuros.

**Verificação**

- `tests/test_authorization_hardening.py` (novo, 8 testes): regra de ativação, criação
  agendada versus expirada, Admin de membership somente inspeção, `Clinic.is_active`
  somente leitura, auditoria de transição por provedor, evento de autorização na
  aceitação de convite, rótulo traduzido de papel desconhecido, autoria e auditoria na
  mudança de papel.
- Suíte SQLite completa após as correções: `2683 passed, 29 skipped`,
  `pytest_sqlite_r2_exit=0` (`pytest-sqlite-full-r2.log`, `pytest-sqlite-junit-r2.xml`).
- Foco PostgreSQL descartável (`compose.test.yml`, `postgres:17-alpine`, tmpfs):
  `pytest-postgresql-focused-r2.log`.
- Ruff/format nos arquivos tocados: `All checks passed!` e `already formatted`. O comando
  legado de seed caiu de 22 para 1 aviso de Ruff e passou a estar formatado (a linha
  restante é pré-existente).

**Observação pré-existente (não é regressão desta entrega)**

`scripts/check_ui_catalogs.py` executado **sem** `--scope` falha com
`ValueError: Invalid source path: templates/visual_reference/reference.html`: o escopo
legado `docs/migration/shared-ui-scope.json` cita um template removido no commit
`7f3930d`. O comando usado no CI e no README é escopado
(`--scope docs/migration/translated-ui-scope.json`) e passa. O arquivo de escopo legado
não foi alterado para preservar o histórico.

## 8. Análise do deploy em produção e causa raiz do 500 no Admin (2026-09-23)

Análise somente leitura na VPS (`deploy@13.140.139.122`, host `vmi3351517`), sem
leitura de `.env`, sem dados de usuários ou prontuários e sem alterar serviços, até a
autorização explícita pedida nesta sessão.

**Estado encontrado**

- Checkout `~/auroraelo` na branch `gemini`, árvore limpa, commit `8c0ad2c`; o
  `docker-compose.yml` remoto tem sha256 `824d9015…`, idêntico a
  `git show HEAD:docker-compose.yml`. Produção roda o commit publicado; nenhuma
  alteração da árvore de trabalho local está deployada (`accounts/team_views.py`,
  `master_panel/tenant_services.py` ausentes na imagem).
- `auroraelo:latest` = `sha256:0f4d9a5106…`, Python 3.14.7 + Django 6.1, containers
  `web` e `worker` reiniciados em 22/09 18:51 UTC, 0 reinícios, healthy.
  `migrate --check` = 0 (sem migrações pendentes).
- Público `https://auroraelo.rgnsystems.com.br`: `/health/live/` 200,
  `/health/ready/` 200, `/` 200, `/master/login/` 200, `/accounts/login/` 200,
  `/master/` e `/admin/` anônimos 302; 301 HTTP→HTTPS no edge; HSTS, CSP,
  X-Frame-Options, nosniff, Referrer-Policy e `x-request-id` presentes. Certificado
  CN=rgnsystems.com.br válido até 08/11/2026. `auroraelo.com.br` não resolve.
- Worker Celery: `pong`, 1 node, 4 tarefas registradas, fila `celery` com 1 consumidor,
  zero erro de execução em 72h — e nenhuma tarefa executada no período.

**Causa raiz do 500 em `/admin/` (reproduzida e corrigida)**

Registro corrigido em 2026-09-23 (ver seção 9): o harness em processo usado neste
diagnóstico estava inválido — o client do Django envia `Host: testserver`, que não está em
`ALLOWED_HOSTS` de produção, e a requisição morria em `DisallowedHost` antes de renderizar
(`consents/context_processors.py` mascarava com `AttributeError`). A evidência direta do
`ValueError: Missing staticfiles manifest entry for 'vendor/bootswatch'` é a regressão
`tests/test_static_storage_manifest.py::test_strict_manifest_rejects_the_jazzmin_directory_reference`,
que usa o storage estrito contra um manifesto coletado real; a causa raiz permanece a
referência a diretório em `jazzmin/templates/admin/base.html`, mas a reprodução em produção
não está documentada de forma conclusiva.

`jazzmin/templates/admin/base.html:34` usa `{% static 'vendor/bootswatch' %}` — um
**diretório**, não um arquivo do manifesto — e o backend estrito
`whitenoise.storage.CompressedManifestStaticFilesStorage` levantava `ValueError` em toda
página do Admin. O commit `8c0ad2c` (guard de `request.user`) não era a causa. A sessão
temporária usada no diagnóstico foi removida ao final do script.

Correção local: `config/storage.py` define
`TolerantCompressedManifestStaticFilesStorage` (subclasse do storage do whitenoise, com
`manifest_strict = False` e fallback para a URL sem hash, emitindo `RuntimeWarning`),
agora referenciada por `config/settings/production.py`. Regressões em
`tests/test_static_storage_manifest.py` (3 testes, incluindo `/admin/` renderizando 200
com manifesto sem a entrada) e ajuste do teste
`test_duralux_static_foundation.py::test_production_uses_manifest_storage_after_legacy_css_cleanup`
para exigir o storage tolerante **mantendo** a garantia de manifesto/hash.

Observação de observabilidade: os registros `django.request` de produção saem sem
traceback (0 tracebacks em 48h), então os 500 não eram diagnosticáveis pelos logs; a
causa só apareceu por reprodução em processo.

**Execução de tarefa no worker Linux (risco do Celery + Python 3.14 resolvido)**

Publicado `config.celery.debug_task` pela fila de produção com
`task_always_eager=False`:

```
Task config.celery.debug_task[eb0dd081-8383-4ac3-beca-45acd6fdefc6] received
Task config.celery.debug_task[...] succeeded in 0.008947084890678525s: None
```

Conclusão: o worker de produção (Linux, pool prefork) executa tarefas normalmente; a
falha `fast_trace_task`/`not enough values to unpack` é específica do host macOS usado
nos ensaios locais e **não** afeta a produção.

**Seed de demonstração desligado em produção**

`DJANGO_ALLOW_DEMO_SEED` estava ligado em `web` e `worker`, e o `entrypoint.sh` rodava
`manage.py seed_psychiatry || true` a cada start, gravando dados clínicos fictícios no
banco de produção. Com autorização: `.env` copiado para `.env.bak-20260923T105246Z`,
valor alterado para `false`, `web` e `worker` recriados. Verificado: flag `DESLIGADO` nos
dois containers, `Running clinical seed command` com 0 ocorrências, migrações e
`collectstatic` executados e `/`, `/health/live/`, `/health/ready/`, `/master/login/`
retornando 200 local e publicamente.

Inventário (somente contagens, sem identificadores): 7 pacientes psiquiátricos no total,
**todos os 7 são do seed demo**; 29 avaliações, 1 prescrição, 29 registros de adesão e 1
alerta de crise vinculados a eles; 1 assinatura, 29 mind logs e 1 diário CBT do
`user_identifier` demo; 14 categorias diagnósticas, 12 leitos e 1 sala de telepsiquiatria.
Ou seja: o banco de produção contém apenas dados sintéticos de demonstração — não há
prontuário real a contaminar hoje, e a limpeza deve ser decidida antes do uso real.

**Outros achados operacionais** (detalhados no relatório da sessão): RabbitMQ rodando com
a credencial default `guest` (o compose deployado ainda tem `${RABBITMQ_DEFAULT_USER:-guest}`),
`SECURE_SSL_REDIRECT=False` no app, PostgreSQL com `sslmode=disable`, ausência de backup
agendado do Aurora Elo, disco em 80% com 31,8GB de build cache recuperável e deploy
manual sem automação.

## 9. Deploy da VPS executado (2026-09-23)

Autorizado pelo usuário ("atualize o repositorio e a vps").

**Publicação do repositório**

- Branch `gemini` publicada em `origin` (`github.com/RuiGN/auroraelo`): `8c0ad2c` → `a4a47b0`
  (correção do storage do Admin, evidências, restante do trabalho) → `e35eee2` (aviso único
  por referência ausente).
- `.gitignore` passou a ignorar `playwright-report/`, `test-results/` e `.coverage (1)`;
  `scripts/check_secrets.py` rodou antes do commit (`Secret scan passed.`) e nenhum `.env`
  foi versionado.

**VPS**

- `~/auroraelo`, branch `gemini`, fast-forward até `e35eee2`; imagem reconstruída
  (`auroraelo:latest` = `0dc55b6c7267`, anterior `94558a7886c1`); `rabbitmq`, `web` e
  `worker` recriados e saudáveis. Âncoras de rollback: tag `auroraelo:rollback-20260923T111813Z`,
  `.env.bak-20260923T111813Z` e `git checkout 8c0ad2c`.
- Migrações aplicadas pelo entrypoint: `core.0001`, `core.0002`, `accounts.0009_clinicinvitationscope`,
  `people.0005_professionalprofile_psychiatrist`; `migrate --check` = 0.
- Broker: usuário dedicado `auroraelo` (senha aleatória de 43 caracteres gerada na VPS,
  nunca exibida) com permissões no vhost `/`; `.env` atualizado com `RABBITMQ_DEFAULT_USER`,
  `RABBITMQ_DEFAULT_PASS` e as variantes URL-encoded exigidas pelo Compose endurecido. O
  usuário default `guest` foi **removido** após confirmar o tráfego no usuário novo.
- Verificação: `config.celery.debug_task` recebida e concluída **antes** e **depois** da
  remoção de `guest`; fila `celery` vazia; `inspect ping` = `pong`, 1 node.
- Admin: `/admin/` autenticado → **200** (sessão criada em processo para superusuário
  existente, sem senha; linhas de sessão temporárias removidas depois); anônimo → 302 para
  `/admin/login/`; **0 respostas 500 e 0 tracebacks** no log do `web` desde o deploy.
- Público: `/health/live/`, `/health/ready/`, `/`, `/master/login/`, `/accounts/login/`
  → 200; `/master/` e `/admin/` anônimos → 302; HTTP→HTTPS 301; HSTS, CSP, X-Frame-Options,
  nosniff, Referrer-Policy, Permissions-Policy e `x-request-id` presentes.
- Seed demo: `DJANGO_ALLOW_DEMO_SEED=false` e `Running clinical seed command` ausente.

**Correção de registro do diagnóstico do 500**

O harness em processo usado no diagnóstico anterior envia `Host: testserver`, rejeitado por
`ALLOWED_HOSTS` em produção; a requisição falhava em `DisallowedHost` e o template de erro
estourava depois em `consents/context_processors.py` (`request.user`), mascarando a causa.
Com o host real no client o comportamento é coerente: anônimo 302 e autenticado 200 no
commit novo. A prova direta do `ValueError` do manifesto é a regressão local citada na
seção 8.

**Pendência nova identificada no deploy**

O shell do Admin renderiza, mas referencia ativos legados que não existem no pacote do
Jazzmin nem em `static/`: `vendor/bootstrap/js/bootstrap.js`, `vendor/select2/*`,
`vendor/fontawesome-free/*`, `vendor/adminlte/*`, `admin/js/jquery.js`,
`admin/js/vendor/select2/select2.js`, `jazzmin/css/main.backup` e variantes não minificadas
(`duralux/css/bootstrap.css`, `duralux/js/bootstrap.bundle.js`, `master_panel/js/chart.umd.js`,
`design_system/tailwind.js`) — 69 nomes distintos. Antes da correção a página inteira falhava;
agora os que existem são servidos e os ausentes retornam 404, com aviso emitido uma única vez
por nome e por processo do gunicorn (3 workers). Resolver exige decidir a origem desses
bundles (vendorizar no repositório ou permitir CDN com ajuste de CSP); fora do escopo desta
atualização.
