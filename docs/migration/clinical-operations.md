# Operações clínicas — backend integrado, ativação bloqueada

## Estado e integração

Implementação nova em `clinical_operations/`, sem alteração de `accounts.User`,
migrations de outros domínios ou templates. A entrega auxiliar foi isolada;
o principal registrou o app nos settings compartilhados e montou a rota abaixo.
**Não ativar em atendimento real antes de revisão independente clínica e de segurança.**
A ativação, navegação, política de rollout e aprovação pertencem ao integrador.

Integração aplicada pelo principal:

```python
# INSTALLED_APPS
"clinical_operations.apps.ClinicalOperationsConfig"
# config/urls.py
path("api/v1/clinical-operations/", include("clinical_operations.urls")),
```

`CLINICAL_OPERATIONS_ENABLED` é **false por padrão**, inclusive nos settings de
teste gerais. Os settings de desenvolvimento/produção importam explicitamente a
flag da base; não foi alterada nenhuma variável de ambiente de instalação.
Enquanto desabilitada, a view devolve `503 clinical_operations_disabled` antes
de consultas/mutações do domínio. CSRF e os middlewares continuam ativos e podem
rejeitar uma requisição antes da view. Nenhuma ativação/deploy foi executada.
Habilitar a flag não substitui autenticação, clínica, grants ou consentimento.

### Revisão independente pendente

A tentativa local de revisão por `opencode-go / glm-5.3` terminou com código
`124` (timeout), sem parecer JSON. O log
`/Users/rgnsystems/.hermes/cache/scratch/aurora-clinical-review-fallback.log`
registra `REVIEW_TIMEOUT: nenhuma aprovação deve ser inferida`.
Isso não constitui aprovação, reprovação do código ou validação clínica.

A revisão estática foi redistribuída entre dois contextos independentes Astra:
fronteira HTTP/autorização e persistência/transações. Os resultados ainda precisam
de avaliação pelo integrador; essa contingência não substitui a revisão por outra
família prevista em `hermes-model-routing.md`. A ativação e o deploy continuam
bloqueados pelos gates de revisão e validação, sem mudanças na configuração do
Hermes ou nos provedores de IA do produto.

Manter AuthenticationMiddleware, SessionMiddleware, CsrfViewMiddleware e
ClinicTenantMiddleware. Não publicar estas rotas como APIs anônimas nem isentá-las
de CSRF. Nenhum grant é criado por instalação/migração. Um administrador ativo
precisa conceder cada capacidade explicitamente. Não há registro Django Admin que
ofereça edição livre dos dados deste app.

Os settings `clinical_operations.testing_settings` derivam de `config.settings.test`
e mantêm este app sem duplicação, URLconf isolado e flag habilitada para testes.
São exclusivos de testes, nunca de atendimento real. Os testes próprios habilitam
a flag por fixture; os testes de integração verificam separadamente o bloqueio
padrão e as rotas reais em `config.urls`.

## Correções de revogação e listagens — aguardando reavaliação

O parecer estático `release-new-domains-review.json` identificou CO-01 e CO-02.
O principal conferiu os hashes das fontes e reproduziu os defeitos antes da edição:
seis falhas na revogação de grants e oito nas listagens identificadas.

- CO-01: `set_grant(enabled=False)` agora só desabilita um grant já existente na
  clínica. A atividade/papel do alvo não impede a revogação; reativá-lo não restaura
  a permissão. O caminho não cria grants e preserva autorização atual do
  administrador, lock/revalidação da clínica e auditoria técnica. Concessões
  continuam exigindo papel vigente compatível.
- CO-02: atendimentos e inscrições continuam restritos à clínica e ao profissional,
  mas agora também consultam `people.selectors.patient_visible_to` antes de paginar.
  Vínculo encerrado/expirado e paciente ou membership inativos retiram a identidade
  da listagem, sem apagar registros históricos nem produzir escrita no GET.

Novo módulo: `tests/test_clinical_operations_revocation.py`. Também cobre isolamento
da revogação entre clínicas, administrador inativo/sem papel, clínica inativa,
ausência de criação ao revogar e paginação somente de registros autorizados.

Execução local com PostgreSQL 17 descartável, migrations normais e settings reais:

```bash
# Variáveis somente do ambiente sintético documentado no README.
TMPDIR=/Users/rgnsystems/.hermes/cache/scratch DJANGO_SETTINGS_MODULE=config.settings.test \
  .venv/bin/python -m pytest tests/test_clinical_operations_revocation.py \
  tests/test_clinical_operations.py tests/test_clinical_operations_integration.py \
  tests/test_domain_architecture.py --reuse-db --no-cov -q --tb=short \
  --junitxml=/Users/rgnsystems/.hermes/cache/scratch/clinical-corrections-postgresql.xml
```

Resultado conferido no JUnit: **127 passed**, zero falhas/erros/skips; 37 avisos de
`staticfiles/` ausente, duração 165,22 s. Ruff check/format dos dois módulos alterados
e do teste novo passaram, assim como `git diff --check`.

O ciclo rápido anterior com SQLite `--nomigrations` teve 78 aprovados, duas falhas
de triggers append-only ausentes e três skips PostgreSQL. Não foi considerado
aceite das migrations: os testes correspondentes passaram na execução PostgreSQL
normal acima. Os dois testes adicionais de paginação entraram nessa execução final.

Limites: a autorização das listagens consulta cada paciente distinto candidato;
paginação da saída não limita esse custo total. Não foi comprovado cancelamento
instantâneo de leituras em andamento nem serialização de todos os escritores
externos. Revisão corretiva independente foi solicitada em relatório separado.
Flags continuam desativadas; não há aprovação clínica ou autorização de deploy.

## Pareceres Astra de fronteira e persistência — triagem do principal

Os relatórios estáticos
`/Users/rgnsystems/.hermes/cache/scratch/clinical-boundary-independent-review.json`
e `.../clinical-persistence-independent-review.json` ambos reprovaram
(`passed: false`). Os dois achados principais eram HTTP-AUTH-01/CO-01 (revogação
de grants e listagens) e já haviam sido corrigidos pelo principal antes dos
pareceres: os hashes atuais de `services.py`/`selectors.py` divergem da árvore
avaliada. A revisão por outra família de modelos permanece pendente; nenhum
parecer aqui substitui essa etapa.

Conferência direta pelo principal contra a árvore atual:

- CP-01/HTTP-AUTH-02 (revogação bloqueada por alvo inelegível): `set_grant` com
  `enabled=False` somente desabilita grant existente; a elegibilidade do alvo é
  exigida apenas na concessão. Coberto por
  `tests/test_clinical_operations_revocation.py` (vinte casos, incluindo alvo
  inativo/suspenso/expirado/papel alterado/removido, reativação sem restaurar
  permissão e ausência de criação ao revogar).
- HTTP-AUTH-01 (listagens identificáveis após perda de vínculo): atendimentos e
  inscrições agora filtram por `patient_visible_to` com
  `patient.clinical.read` antes de paginar, cobrindo vínculo encerrado/expirado,
  paciente inativo e membership suspenso, sem escrita no GET.
- HTTP-JSON-03 (RecursionError do parser): em Python/CPython 3.14.7 o parser
  `json.loads` do projeto suportou profundidades de 2000/4000/8000 dentro do
  limite de bytes sem lançar a exceção; o 500 relatado não reproduziu com
  payload real. Ainda assim, `clinical_operations/views.py` agora converte
  `RecursionError` do parser em `invalid_payload` 400, sem capturar exceções de
  serviços/persistência. Um teste específico injeta a falha só no parser e
  verifica 400 sem escrita; outro garante que `RecursionError` de serviço segue
  propagando (não vira 400).

Novo módulo `tests/test_clinical_operations_json_limits.py` (43 casos): payloads
profundamente aninhados nos dez recursos em forma de array/objeto, profundidade
relatada e próxima ao limite de bytes, sessão gerenciada com
`ACCOUNT_SESSION_ALLOW_UNKNOWN=False`, CSRF real, `X-Clinic-ID`, verificação de
ausência de escrita em `clinical_operations_*`/`audit_*`, `no-store`, controle
positivo que persiste produto e guardas contra rótulo incorreto de erros internos.

Execução local com PostgreSQL descritável sintético do README, migrations normais,
`--reuse-db`, `--no-cov`: **170 passed, zero failures/errors/skips**
(`clinical-boundary-corrections-postgresql.xml`; 42 operações + 20 revogação +
43 limites JSON + 23 integração + 42 arquitetura). Ruff check/format de
`clinical_operations/` e dos testes novos: aprovado. `git diff --check`: limpo.
O ciclo SQLite `--nomigrations` dos limites JSON também passou (43 casos). Mypy
do teste novo não acusou diagnóstico no alvo; o gate global permanece reprovado
com dívida preexistente em outros arquivos.

Permanecem abertos, sem correção nesta etapa:

- HTTP-CACHE-04: erros antecipados de middleware (CSRF global, sessão revogada,
  tenant ausente) não recebem `no-store` do `never_cache` da view. Limite
  registrado, não vazamento clínico demonstrado.
- HTTP-TEST-05: matriz de sessões gerenciadas revogadas/expiradas na fronteira
  habilitada ainda não cobre todos os ramos; o limite JSON novo usa sessão
  rastreada, mas não todas as variantes.
- AUDIT-TRACE-06: correlação de `request_id` entre HTTP e auditoria e ação técnica
  distinta para concessão/revogação seguem como proposta.
- Lacunas de concorrência real apontadas pelo parecer de persistência
  (revogação durante espera por lock em grant/membership/consentimento) e limites
  de append-only quanto a TRUNCATE/substituição SQLite.

As sugestões de mesmo request_id e de testes concorrentes adicionais não foram
implementadas nesta etapa. Nenhum dado clínico real foi usado; flags seguem
desativadas; sem commit, push ou deploy.

## Pareceres de aprovação limitada — verificação de hashes pelo principal

Dois pareceres Astra retornaram `passed: true` com escopo delimitado:

1. **Correções CO-01/CO-02** (`clinical-revocation-corrections-review.json`):
   revogação preserva autorização/auditoria, não cria grant e independe do estado
   do alvo; listagens aplicam `patient_visible_to` antes da paginação sem escrita
   no GET. Limitações explícitas mantidas: custo por paciente distinto, janela
   concorrente de leitura em andamento (revogação não cancela GET iniciado) e
   escritores de membership fora do lock de `set_grant`.
2. **Integração recovery montada e DESATIVADA** (`recovery-mounted-disabled-review.json`):
   rotas/exceções exatas, CSRF/sessão na cadeia, ator de `request.user`, resolver
   ausente nega antes de Redis/provedor e os quatro settings preservam
   `False/False/None` sem sobrescrita por ambiente. Não é aprovação para ativar:
   com consentimento e configuração futuros, o provedor recebe mensagem,
   histórico e fontes; `store=False` não comprova retenção zero.

Conferência de hashes pelo principal contra a árvore atual:

- CO-01/CO-02: 16 de 17 coincidem. A divergência é `clinical_operations/views.py`,
  alterado pelo próprio principal **após** o snapshot do revisor com a correção
  HTTP-JSON-03 (tratamento de `RecursionError` no parser). Os três arquivos
  nucleares da revisão (`services.py`, `selectors.py`, teste de revogação)
  coincidem; o parecer permanece válido para eles.
- Recovery: 18 de 20 coincidem. As divergências são `tests/test_recovery_integration.py`
  (ampliado pelo principal com os casos de idioma/sessão/CSRF pós-snapshot) e
  `accounts/middleware.py` (correção `setdefault` de `Content-Language` pelo
  principal). Ambas as mudanças foram feitas pelo próprio principal e são
  objeto de revisões separadas já registradas; nenhuma delas altera as rotas,
  exceções, flags ou contratos avaliados.

As aprovações são estáticas e sequenciais; não cobrem a janela concorrente de
SEC-01/SEC-04 de psiquiatria nem autorizam ativação de IA, atendimento clínico
ou deploy. Revisão por outra família de modelos e suíte global pós-correções
continuam pendentes. Sem commit, push ou deploy.

## Contratos públicos consumidos

- `clinics.services.authorized_active_clinic`, `lock_clinic_for_update`:
  clínica ativa, identidade persistida atual, papel e serialização da clínica.
- `clinics.policies.has_active_clinic_role`: papel vigente e usuário ativo.
- `people.selectors.patient_visible_to(action="patient.clinical.read")`:
  terapeuta ativo, paciente da clínica e vínculo vigente.
- `consents.services.require_purpose_access` e
  `consents.policies.ConsentPurpose.CLINICAL_FOLLOW_UP`: documento vigente,
  integridade e última manifestação. Ausência, recusa e revogação bloqueiam
  leitura/escrita do conteúdo; mero aceite histórico não basta.
- `audit.services.record_audit_event`: somente ação técnica, tipo/UUID de recurso,
  ator, clínica, resultado e request UUID. Nenhuma nota, nome, produto, motivo
  clínico ou payload bruto é entregue à auditoria.
- `core.persistence.UUIDTimestampedModel`: identidade UUID e timestamps.

Nenhum import de models privados de outros apps. O teste próprio aplica o mesmo
verificador de `tests/test_domain_architecture.py` incluindo `clinical_operations`.
O principal pode acrescentar o novo domínio à matriz central, preservando os
mesmos edges públicos (core/clinics/people/consents/audit).

## Permissões

| Capacidade | Requisito adicional |
|---|---|
| `pharmacy.read` | grant explícito e papel ativo de administrador, terapeuta ou equipe administrativa |
| `pharmacy.write` | independente de read; mesmos papéis, grant próprio |
| `encounter.manage` | terapeuta ativo + grant; paciente vinculado; profissional do atendimento é o ator |
| `record.read` | grant independente + terapeuta responsável + vínculo + consentimento vigente |
| `record.write` | mesmos requisitos, grant independente; atendimento em andamento |
| `session.manage` | terapeuta responsável + grant; vínculo para inscrição/presença |

`clinic_admin` pode conceder/revogar grants, mas **não** recebe conteúdo clínico
por ser administrador. Não se concedem capacidades clínicas a papéis administrativos.
Não há bypass por `is_superuser`, `is_staff`, ator nulo ou IDs do payload.
Grants são por clínica/usuário/capacidade, sem herança entre clínicas. Membership,
clínica e ator são consultados novamente a cada operação; mutações revalidam após
adquirir o lock da clínica para não usar grant revogado enquanto aguardavam.

Paciente é o UUID de `accounts.User` com membership `patient` vigente na clínica,
não o UUID de `PatientProfile`. Não há criação automática de perfil/vínculo/consentimento.
O profissional é derivado da sessão autenticada, nunca de um campo arbitrário.

## HTTP JSON

Prefixo `/api/v1/clinical-operations/`. Sessão autenticada; seleção de clínica pelo
contrato existente (sessão `active_clinic_id`/header `X-Clinic-ID`). POST exige
`Content-Type: application/json` e token CSRF (`X-CSRFToken` + cookie de mesma origem).
Respostas têm `Cache-Control` privado/no-store via `never_cache`.

Todos os POST retornam `201 {"id":"UUID"}`; replay de movimento/inscrição retorna
o mesmo ID sem nova linha nem auditoria. Não retorna conteúdo clínico na resposta
de escrita. Todos os campos da tabela são obrigatórios salvo indicação.

| URI (POST) | Payload |
|---|---|
| `grants/` | `user_id`, `capability`, `enabled` (boolean JSON, inclusive false explícito) |
| `products/` | `name` (1–160 caracteres), `sku` (1–48) |
| `lots/` | `product_id`, `code` (1–64), `expires_on` (`YYYY-MM-DD`) |
| `movements/` | `lot_id`, `quantity` (inteiro 1–1.000.000), `direction` (`in`/`out`), `key` (1–80); `patient_id` obrigatório em out e ausente/null em in |
| `encounters/` | `patient_id`, `starts_at` (ISO-8601 futuro com fuso) |
| `transitions/` | `encounter_id`, `status` |
| `records/` | `encounter_id`, `content` (1–8.000 caracteres) |
| `sessions/` | `kind` (`individual`/`grupo`), `modality`, `capacity`, `starts_at`, `ends_at` |
| `enrollments/` | `session_id`, `patient_id` |
| `attendance/` | `enrollment_id`, `status` (`presente`/`ausente`) |

Exemplo de entrada de estoque:

```json
{"lot_id":"00000000-0000-0000-0000-000000000001","quantity":10,"direction":"in","key":"recebimento-sintetico-001"}
```

O UUID de exemplo é ilustrativo, não um recurso persistido. Não há campo de
prescrição, dose, diagnóstico, contraindicação ou aconselhamento terapêutico.

GET disponíveis: `products/`, `lots/`, `movements/`, `encounters/`, `sessions/`,
`enrollments/`, `records/?encounter_id=UUID`. Listagens retornam
`{"results":[...],"offset":0,"limit":100}`. Offset inteiro 0–10.000, páginas de
no máximo 100, ordenação estável por created_at/UUID. Não há total ou has_more
presumido. Atendimentos/sessões/inscrições ficam limitados ao profissional responsável;
as listagens operacionais nunca incluem conteúdo de notas. Movimentos listados
omitem paciente e chave idempotente. Para notas, cada GET revalida grant, vínculo,
consentimento e profissional. Métodos de listagem não criam grants, recursos,
movimentos, notas, auditoria ou notificações. A seleção de clínica feita pelo
middleware existente permanece sob responsabilidade de `clinics`.

Payload limitado a 16 KiB; objeto JSON obrigatório; rejeita campos desconhecidos,
chaves duplicadas, tipos incompatíveis (inclusive boolean como quantidade), strings
excessivas, datas sem timezone e IDs malformados. GET rejeita parâmetros desconhecidos
ou repetidos. Conteúdo bruto não aparece em erros.

Erros JSON do app: `authentication_required` 401; `access_denied`/`clinic_required`
403; `invalid_payload` 400; `json_required` 415; `payload_too_large` 413;
`method_not_allowed` 405; `integrity_conflict` 409 (unicidade); conflitos de domínio
409: `idempotency_conflict`, `insufficient_stock`, `expired_lot`,
`invalid_transition`, `invalid_record_state`, `capacity_reached`,
`schedule_overlap`, `patient_schedule_overlap`, `session_started`.
Falhas antecipadas do middleware tenant/CSRF conservam seu contrato existente
(por exemplo, CSRF 403 padrão Django pode ser HTML), sem exceção de segurança.

## Persistência e invariantes

- Oito modelos novos: OperationGrant, Product, StockLot, StockMovement, Encounter,
  ClinicalRecord, TherapySession e Enrollment.
- Default managers recusam consultas sem `.for_clinic(clinic_id)`. O manager de
  infraestrutura serve ao Django; não é usado por HTTP/serviços para contornar tenant.
- FKs próprias são resolvidas na clínica antes da escrita e novamente em `save/clean`.
  Paciente/usuário/autor passam pelos contratos de papel e vínculo, não por simples
  existência de UUID. Serviços são a fronteira de escrita suportada; bulk writes,
  alteração manual de saldos e SQL de aplicação fora dos serviços não são suportados.
- `0001_initial` adiciona tabelas e constraints; `0002_append_only` instala triggers
  PostgreSQL e SQLite que rejeitam UPDATE/DELETE de movimento e registro clínico.
  Instâncias e querysets também bloqueiam alteração/exclusão dessas linhas.
  Administrador do banco pode remover triggers: isto não é armazenamento WORM certificado.
- Estoque inicial zero; cada entrada/saída e auditoria pertencem à mesma transação.
  Lock da clínica antes dos recursos evita inversão com a cadeia de auditoria.
  Unicidade `(clinic,key)` serializa replay mesmo entre lotes diferentes.
  Payload idempotente inclui lote, quantidade, direção, paciente e ator. Chave é
  preservada literalmente (espaços não são removidos); uma chave não vazia tem
  significado exato e não deve ser reutilizada para outra intenção.
- Saída nova de lote com validade anterior ao dia local é bloqueada; validade hoje
  ainda permite saída. Entrada de lote vencido é admitida para inventário, mas não
  o torna dispensável. Replay previamente concluído não produz nova dispensação.
- Saldo nunca negativo (checagem de serviço e constraint do banco); teto de saldo
  2.147.483.647 unidades, sem frações. Sem ajuste/descarte/correção de inventário
  nesta fatia — não apagar movimentos para corrigir erros.
- Atendimento: `agendado → em_atendimento → concluido`; cancelamento permitido a
  partir de agendado/em_atendimento. Estados finais não reabrem. Tokens de API sem
  acentos; rótulos em português ficam a cargo da futura UI. Notas somente append-only
  durante atendimento; não equivalem a assinatura clínica/digital ou prontuário certificado.
- Sessão individual tem capacidade 1; grupo 1–100; intervalo futuro, fim posterior
  ao início e duração até oito horas. Bloqueia sobreposição de sessões do profissional
  e inscrição simultânea do paciente em sessões sobrepostas. Capacidade serializada
  pela clínica. Reinscrição da mesma pessoa é idempotente. Presença é um registro
  operacional manual, não comprovação biométrica ou serviço de monitoramento.
- Modalidades fechadas: `psicoterapia`, `exercicio`, `yoga`, `arteterapia`.
  Modalidade não implica indicação terapêutica, habilitação regulatória ou ausência
  de contraindicações; a avaliação clínica permanece humana.

## Limites deliberados

Não é SNGPC, escrituração sanitária homologada, prescrição/dispensação de medicamentos
controlados, verificação de habilitação profissional regulatória, recomendador de
exercício nem motor de contraindicações. Não há integração com farmácia externa,
agenda histórica de `scheduling`, notificações, SOS, teleconsulta, pagamento ou mobile.
A agenda do novo app não detecta sobreposições com outros domínios; atendimento tem
apenas horário inicial, não reserva global de duração/sala. Sem cancelamento de sessão,
lista de espera, estorno de estoque, reconciliação entre saldo e SQL externo ou lote
fracionado. Auditoria de leitura persistente não foi adicionada a GET para preservar
leitura sem efeitos; avaliar trilha de acesso institucional antes da ativação.

Notas ficam no banco do produto; não há criptografia de campo nova, assinatura,
certificação clínica, política de retenção/descarte nem fluxo de correção certificado
nesta fatia. Backup, criptografia em repouso, privilégio mínimo do usuário do banco,
retention/LGPD e revisão clínica são gates do rollout, não resultados destes testes.

## Validação reproduzível

Dados exclusivamente sintéticos. RED/GREEN foi exercitado por fatias (grant/produto,
lote/movimento, atendimento/registro, sessões, HTTP, triggers, revogação durante espera
do lock e chave literal). Rodadas TDD rápidas usaram `--nomigrations`; as rodadas finais
aplicam migrations reais. Não tratar `--nomigrations` como prova de triggers.

```bash
DJANGO_SETTINGS_MODULE=clinical_operations.testing_settings .venv/bin/python -m pytest \
  tests/test_clinical_operations.py tests/test_domain_architecture.py -q --no-cov
.venv/bin/python -m ruff check clinical_operations tests/test_clinical_operations.py
.venv/bin/python -m ruff format --check clinical_operations tests/test_clinical_operations.py
.venv/bin/python manage.py check --settings=clinical_operations.testing_settings
.venv/bin/python manage.py makemigrations clinical_operations --check --dry-run \
  --settings=clinical_operations.testing_settings
.venv/bin/python manage.py migrate clinical_operations --noinput \
  --settings=clinical_operations.testing_settings
```

PostgreSQL descartável já disponibilizado pelo principal, porta 55439 somente:

```bash
TEST_DATABASE=postgresql DB_HOST=127.0.0.1 DB_PORT=55439 \
DB_NAME=auroraelo DB_USER=auroraelo DB_PASSWORD=auroraelo-test-only \
DJANGO_SETTINGS_MODULE=clinical_operations.testing_settings \
.venv/bin/python -m pytest tests/test_clinical_operations.py -q --no-cov --reuse-db
```

Credenciais acima são públicas e sintéticas do Compose de teste. Não usar porta 5432,
.env, banco real, uploads, VPS ou execução concorrente de suites no mesmo test DB.
Os três casos concorrentes exigem PostgreSQL e têm skip explícito no SQLite.
### Evidência executada na entrega isolada

- SQLite com migrations reais: **81 passed, 3 skipped**, 18 warnings de staticfiles.
  Os skips são exclusivamente os três casos concorrentes que exigem PostgreSQL.
  Foram coletados 42 testes próprios e 42 de arquitetura; no SQLite, 39 próprios
  executaram e três foram pulados. JUnit:
  `/Users/rgnsystems/.hermes/cache/scratch/clinical-operations-sqlite.xml`.
- PostgreSQL 17 descartável, migrations reais: **84 passed**, sem skips, incluindo
  três testes de concorrência real (última unidade, replay da mesma saída e última
  vaga da sessão), mais a matriz de arquitetura. `--reuse-db` reutilizou somente o
  banco sintético `test_auroraelo` após a primeira criação/migração.
- Leitura direta de `django_migrations` confirmou `0001_initial` e `0002_append_only`;
  catálogo PostgreSQL confirmou ambos os triggers de imutabilidade.
- `manage.py check`: nenhum problema; `makemigrations --check --dry-run`: nenhuma
  alteração pendente; `migrate clinical_operations` em SQLite `:memory:`: ambas as
  migrations e dependências aplicadas com sucesso.
- Ruff check e format check dos arquivos próprios aprovados.
- O warning observado é o diretório `staticfiles/` ausente no checkout de teste;
  os testes HTTP JSON não usam arquivos estáticos. Não foi ocultado nem corrigido
  fora do escopo. Não houve certificação clínica, mypy ou suíte global nesta entrega.

A evidência JUnit foi gravada em
`/Users/rgnsystems/.hermes/cache/scratch/clinical-operations-postgresql.xml`.
O integrador ainda precisa rodar a suíte global com settings/rotas reais e obter
revisão independente antes de ativar as operações clínicas.

### Verificação do principal após integração

- Os JUnits da entrega isolada foram lidos e suas contagens conferidas: 84 casos
  em cada backend, três skips no SQLite e nenhum no PostgreSQL.
- TDD do registro/ativação: primeiro falhou o registro ausente; depois falharam
  flag ausente e rota 404. Os testes passaram após registro, montagem e bloqueio.
- PostgreSQL 17 sintético, `config.settings.test` e `config.urls` reais:
  **107 passed, zero skips/failures/errors**, migrations normais e `--reuse-db`.
  Inclui os três casos de concorrência real e 23 testes da integração/ativação.
  JUnit: `/Users/rgnsystems/.hermes/cache/scratch/clinical-parent-integrated-postgresql.xml`.
- Os 23 testes da ativação foram reexecutados após tipagem e uso de CSRF válido
  nos probes diretos: **23 passed**; chamadas desativadas não podem consultar o
  banco. JUnit: `/Users/rgnsystems/.hermes/cache/scratch/clinical-parent-gate.xml`.
- Django check e `makemigrations --check --dry-run` nos settings gerais aprovados.
- Ruff check/format do app, testes e arquivos de integração aprovados, exceto
  `config/settings/base.py`: E501 na CSP e formatação de configuração Celery já
  existentes em HEAD. Não foram alteradas essas configurações fora do escopo.
- Mypy global foi executado e **falhou**, incluindo código/testes novos sem
  tipagem; não é um baseline verde nem aprovação desta entrega. Logs ficam em
  `/Users/rgnsystems/.hermes/cache/scratch/clinical-parent-mypy*.log`.
  A última execução reportou **649 erros em 26 arquivos**, sem diagnóstico no
  novo teste de integração após a correção de tipagem. Esta contagem inclui outras
  entregas concorrentes; não foi atribuída integralmente à integração clínica.
- Varredura estática focada de 23 arquivos Python: nenhum padrão de segredo ou
  chamada perigosa detectado. As quatro interpolações SQL das migrations foram
  conferidas: usam somente tabelas/operações constantes, não dados de requisição.
  Essa varredura limitada não substitui a revisão independente.
- O warning de `staticfiles/` ausente permanece. Uma reexecução SQLite completa
  do principal foi interrompida; não se contabiliza como aprovação. A evidência
  SQLite completa acima é a da entrega isolada, não uma nova suíte global.

Comando da suíte integrada focada (variáveis PostgreSQL sintéticas conforme seção
anterior, nunca um banco real):

```bash
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest \
  tests/test_clinical_operations.py tests/test_clinical_operations_integration.py \
  tests/test_domain_architecture.py -q --no-cov --reuse-db
```

Revisão independente ainda não aprovada: a tentativa com Sonnet foi encerrada
sem relatório após exceder o orçamento; uma tentativa alternativa foi iniciada.
Não equivale a revisão clínica humana. Permanecem pendentes tratamento dos achados,
tipagem, suíte global pós-integração, UI/i18n operacional e integração com scheduling.
Os checkboxes dos sprints funcionais completos não devem ser encerrados por este
backend isoladamente. Sem commit, push, alteração de banco real ou deploy.
