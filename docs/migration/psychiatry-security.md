# Psiquiatria — segurança local e integrações pendentes

## Escopo e decisão

Branch `hermes`. Entrega auxiliar limitada a Python de `psychiatry/`, migration nova
e testes novos. A integração posterior do principal alterou `core/policies.py` e
`clinics/middleware.py`, com testes HTTP em `tests/test_psychiatry_integration.py`.
Nenhum acesso a .env, bancos, uploads ou prontuários reais. Nenhum commit/push/deploy.
IA de produto não foi ativada nem seu provedor substituído. As tarefas legadas deste
módulo, que enviavam dados diretamente a OpenAI ou fabricavam planos, agora retornam
`disabled` antes de consultar dados e não são enfileiradas pelas APIs.

Políticas compartilhadas em `psychiatry/policies.py` e seletores/serviços revalidam
identidade persistida, papel atual, clínica ativa e ownership. Não dependem exclusivamente
do middleware. Todos os aliases resolvem as mesmas funções protegidas.

- **C (clínico):** `ClinicAuthorizationPolicy(patient.clinical.read)` +
  `PatientAuthorizationPolicy` existente: **therapist** vigente com relação de cuidado
  vigente e paciente vigente na mesma clínica. Superuser/clinic_admin/recepção não são
  bypass. Não inventamos papel physician na matriz do domínio people.
- **C por paciente:** exige ainda autorização versionada corrente para
  `clinical_follow_up` via `consents.services.resolve_purpose_access`. Ausente,
  recusada, revogada ou substituída por versão não aceita: perfil excluído antes de
  consulta clínica/agregação. `tcle_signed=True` legado nunca é evidência suficiente.
- **P (paciente):** papel patient vigente, clínica ativa e exatamente um perfil
  com `clinic_id` e `user_id=request.user.pk`. Sem CPF nem “primeiro paciente”.
  Autoacesso e registro próprio não são bloqueados por consentimento de compartilhamento;
  isso não autoriza comunicação/IA. Leitura profissional permanece dependente da finalidade.
- **B (B2C):** somente identidade autenticada e ativa; ownership pela FK `user`.
  Clínica não é requisito do produto B2C. Strings `user_identifier` legadas não são
  convertidas para ownership, mesmo que coincidam com UUID do ator. `user_id` externo
  é rejeitado; não há usuário guest.

## Matriz completa rota → política → consulta

Legenda acima. Todas as mutações usam sessão e CSRF (nenhum `csrf_exempt`).
Leituras HTML são GET. Métodos HTTP de API permanecem declarados na view.

| Rota (incluindo aliases) | Política | Consulta/efeito |
|---|---|---|
| `/psiquiatria/` | C | visible_patients → contagem de perfis autorizados |
| `/psiquiatria/anamnese/` | C | visible_patients + catálogo diagnóstico limitado |
| `/psiquiatria/pacientes/` | C | visible_patients (50) |
| `/psiquiatria/telepsiquiatria/` | C | sem sala ou paciente fictício; serviço indisponível |
| `/psiquiatria/crise-sos/` | C | sem consulta; monitoring_active=False |
| `/psiquiatria/leitos/` | C | sem consulta/ocupação inventada; integração indisponível |
| `/psiquiatria/login/` | Público GET | redirect account_login |
| `/psiquiatria/mobile/conectado/` | P | own_patient; vínculo inequívoco |
| `/psiquiatria/mobile/b2c/` | B | shell autenticado, sem consultas pessoais |
| `/psiquiatria/adictologia/` | C | AddictionProfile / CravingTrackingLog / TwelveStepsAnamnesis por patient__in=visible_patients |
| `/psiquiatria/adictologia/12-passos/` | C | visible_patients (50); session_id somente após persistência |
| `/psiquiatria/api/v1/clinic/dashboard/` | C | visible_patients → contagens; tele/sos por patient__in |
| `/psiquiatria/api/v1/clinic/patients/` | C | visible_patients → filtros → order/slice |
| `/psiquiatria/api/v1/clinic/anamnese/` | C | clinical_patient(UUID) → avaliação com author=request.user |
| `/psiquiatria/api/v1/dashboard/` | C | visible_patients → contagens; tele/sos por patient__in |
| `/psiquiatria/api/v1/patients/` | C | visible_patients → filtros → order/slice |
| `/psiquiatria/api/v1/anamnesis/save/` | C | clinical_patient(UUID) → avaliação com author=request.user |
| `/psiquiatria/api/v1/adictologia/12-passos/step/` | C | clinical_patient(UUID) + rascunho autor/paciente; transação SQL |
| `/psiquiatria/api/v1/adictologia/12-passos/draft/` | C | UUID + author=request.user + patient__in=visible_patients |
| `/psiquiatria/api/v1/adictologia/12-passos/consolidate/` | C | mesmo rascunho autorizado + select_for_update; sem IA |
| `/psiquiatria/api/v1/adictologia/craving/` | P | own_patient → log SQL; sem inferir recuperação/entrega |
| `/psiquiatria/api/v1/adictologia/dashboard/` | C | perfis/logs por patient__in=visible_patients antes de count |
| `/psiquiatria/api/v1/patient/summary/` | P | own_patient → itens da prescrição vigente própria |
| `/psiquiatria/api/v1/patient/medications/log/` | P | own_patient → item de prescrição vigente própria → log SQL |
| `/psiquiatria/api/v1/patient/sos/` | P | own_patient → alerta SQL; nenhuma notificação |
| `/psiquiatria/api/v1/mobile/connected/summary/` | P | own_patient → itens da prescrição vigente própria |
| `/psiquiatria/api/v1/mobile/connected/adherence/` | P | own_patient → item de prescrição vigente própria → log SQL |
| `/psiquiatria/api/v1/mobile/connected/sos/` | P | own_patient → alerta SQL; nenhuma notificação |
| `/psiquiatria/api/v1/mind/mood/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |
| `/psiquiatria/api/v1/mind/cbt-diary/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |
| `/psiquiatria/api/v1/mind/breathing/` | Público GET | catálogo estático, sem dados pessoais |
| `/psiquiatria/api/v1/mind/subscription/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |
| `/psiquiatria/api/v1/mobile/b2c/mood/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |
| `/psiquiatria/api/v1/mobile/b2c/cbt-diary/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |
| `/psiquiatria/api/v1/mobile/b2c/breathing/` | Público GET | catálogo estático, sem dados pessoais |
| `/psiquiatria/api/v1/mobile/b2c/subscription/` | B | user=request.user; nenhuma busca por user_identifier; POST assinatura indisponível |

## Persistência, legado e migration

`0003_verified_ownership_and_opt_in` é nova; nenhuma migration histórica foi renomeada.
Adiciona FKs nullable PROTECT: perfil→clinic/user, leito→clinic, B2C→user,
avaliação→author e 12 passos→author. Adiciona `draft_steps` JSON em 12 passos.
Defaults de novos perfis: `tcle_signed=False`; novos escores de risco não avaliados
são `NULL`, não “50” nem risco zero. Nenhum backfill, associação por CPF/e-mail,
exclusão de dados ou reconfirmação silenciosa. True/escores legados permanecem intactos.
Sem ownership verificado: consultas HTTP negam/excluem registros.

O vínculo deve ser verificado por processo administrativo auditado futuro, fora destas
rotas; não há API para atribuir clinic/user livremente. Rascunhos sem autor não são
retomáveis. Os antigos métodos Redis sem tenant/autor lançam PermissionDenied;
nenhuma chave antiga é lida, migrada, limpa ou promovida como rascunho autorizado.

Rascunhos novos usam SQL: primeira escrita recebe `patient_id` UUID e retorna
`session_id` UUID gerado pelo servidor. Atualizações exigem mesmo autor/paciente,
revalidam papel, relação e consentimento. Consolidação copia somente respostas reais,
deixa passos ausentes vazios, status `IN_PROGRESS`, `ai_processed=False`.
Não equivale a assinatura/revisão clínica final.

## Contratos HTTP para mobile/UI

Payload UTF-8 application/json, objeto no topo, até **65536 bytes**. Chaves duplicadas,
NaN/Infinity, objetos errados e campos desconhecidos são rejeitados. IDs de paciente/
sessão são UUID canônico com hífens; IDs de medicação são int positivo (bool rejeitado).
Listagens privadas: `limit=1..100` (default 50), `offset=0..10000`, ordenação estável.
Textos até 4000 caracteres, tags até 20 strings de 100 caracteres; campos menores
respeitam seus comprimentos. Não são aceitos nomes/CPF/doctor_name para criar paciente.

- Anamnese: patient_id, chief_complaint, hda, anxiety_scale int 0..10,
  risk_level enum do modelo, diagnostic_impression, therapeutic_plan. Autor da sessão;
  CRM não inventado; não preenche MSE automaticamente. Exige paciente já vinculado.
- Adesão: medication_id int, is_taken bool explícito, scheduled_time ISO com timezone,
  notes opcional até 255. Valida prescrição própria ativa e vigente; grava log antes de
  `persisted=True`. Não afirma sincronização externa nem administração verificada.
- SOS: latitude/longitude opcionais **em par**, números finitos -90..90 / -180..180.
  Grava somente alerta próprio. `notification_delivered=False`, `monitoring_active=False`,
  `protocol_active=False`, `urgent_intervention_dispatched=False`; texto explícito
  “Ninguém foi notificado”. Não há telefone/plantão inventado nem entrega implementada.
- Craving: intensity int 0..10, target_urge obrigatório (até 80), trigger opcional,
  halt_factors lista HUNGRY/ANGRY/LONELY/TIRED, coping até 150,
  urge_surfed_successfully bool **declarado pelo paciente**, jamais derivado da intensidade.
  Mesmo disclaimer de não entrega/monitoramento. Álcool, substâncias e jogo são aceitos
  como relato; não há diagnóstico automático.
- Humor B2C: mood enum, anxiety_score int 0..10, energy_score int 1..5,
  sleep_hours número 0..24, tags e gratitude opcionais. Zero não vira default.
- TCC B2C: trigger e thought obrigatórios, distortion até 150, rational opcional,
  before/after int 0..100; todos os retornos vêm de linhas próprias persistidas.
- Assinatura: GET somente registro próprio vigente; POST **503** porque não há
  verificação de compra. Não ativa assinatura/benefícios via valor enviado pelo cliente.

KPIs indisponíveis são `null` em vez de números inventados. Sem resultados, lista vazia;
nenhum paciente/medicação/agendamento demonstrativo é retornado pela API.
Leitos/teleconsulta não passam a ser serviços funcionais só porque o shell existe.

## Integração de tenant pelo principal

O principal reproduziu `400` em B2C com usuário ativo sem clínica: o middleware
impedia alcançar a política local. Foram aplicadas **nove exceções exatas**, em
`core.policies.is_tenant_independent_path`, consumidas por `clinics.middleware`.
Não há prefixo genérico `/api/`, `/psiquiatria/` ou `/mobile/b2c/`, nem dispensa de
sessão/CSRF. Headers/seleções de clínica antigos não definem ownership B2C.

**Públicos já restritos a GET pelo domínio:**
- `/psiquiatria/login/`
- `/psiquiatria/api/v1/mind/breathing/`
- `/psiquiatria/api/v1/mobile/b2c/breathing/`

**B2C privado (isentar resolução de tenant, NÃO autenticação):**
- `/psiquiatria/api/v1/mind/mood/`
- `/psiquiatria/api/v1/mind/cbt-diary/`
- `/psiquiatria/api/v1/mind/subscription/`
- `/psiquiatria/api/v1/mobile/b2c/mood/`
- `/psiquiatria/api/v1/mobile/b2c/cbt-diary/`
- `/psiquiatria/api/v1/mobile/b2c/subscription/`

**Décima exceção proposta, não aplicada:** `/psiquiatria/mobile/b2c/`.
O template ainda exibe dias fixos, ofertas não integradas, alegação de alívio
instantâneo e toasts de gravação sem chamada persistente. Não se ampliou o acesso
a esse HTML. Isso não bloqueia a página para usuários que já possuam clínica;
sua sanitização e validação renderizada continuam sendo bloqueios de release.

Preservar também as exceções públicas canônicas de recuperação autorizadas pelo
principal (`/apoio/recuperacao/`, `/api/v1/recovery/catalog/`) se integradas nesta branch.
As rotas de connected/adictologia NÃO recebem exceção de tenant.
CSRF global pode retornar a página de erro HTML do projeto antes da view; se o mobile
precisar JSON uniforme nesse erro, configurar CSRF_FAILURE_VIEW no principal sem
isentar as rotas. Clientes devem enviar cookie da sessão e token CSRF válido.

**UI é outro proprietário:** templates ainda podem conter dados/declarações estáticas
legadas; este agente não os alterou. Os contextos Python estão sem demo, mas isso não
certifica HTML final. Remover fallback visual, nomes/CRMs/pacientes, falsas salas e
promessas de SOS; consumir novos contratos e estados vazios/indisponíveis. Atualizar
scripts dos 12 passos (sem session_id inventado, sem patient_cpf), exibir não entrega
sempre e preservar i18n. Principal deve exigir validação renderizada independente.

## Evidência de execução e limites

TDD local em fatias: autorização (39 falhas → 42 verdes), ownership (3 falhas → 45),
B2C/JSON/CSRF (27 falhas → 73), connected/SOS/craving (14 falhas → 87),
rascunhos/helpers/HTML (7 falhas → 94), consentimento (1 falha → 95),
ID/autor/filtros/risco (3 falhas → 98). Acrescentada matriz de regressão por rota,
ator inativo, tenant ausente/inativo/estrangeiro, staff e papel expirado; CSRF válido
com persistência real e rejeição de CSRF em todas as nove mutações.

Comandos confirmados sob `config.settings.test`:
- Ruff check/format dos nove módulos alterados + dois testes novos: aprovado.
- `manage.py check`: nenhum problema.
- `manage.py makemigrations --check --dry-run`: nenhuma mudança pendente.
- Regressão rápida: `.venv/bin/python -m pytest tests/test_psychiatry_security.py tests/test_patient_authorization.py tests/test_clinic_authorization.py tests/test_versioned_consents.py --nomigrations --no-cov -q --tb=short`: **330 passed**, 7 avisos de `staticfiles/` ausente. Um teste adicional RED→GREEN de `actor=None` no serviço: **1 passed**; não há bypass de tarefa de sistema.
- Evolução **com migrations reais e dependências**, SQLite `:memory:`:
  `PYTHONPATH=/Users/rgnsystems/projects/auroraelo .venv/bin/python /Users/rgnsystems/.hermes/cache/scratch/verify_psychiatry_migration.py`: **PASS**. Exercita o próprio teste novo de evolução 0002→0003, comprovando True legado preservado, ownership NULL e default novo False.
- Execução ampliada **com migrations normais**:
  `.venv/bin/python -m pytest tests/test_psychiatry_security.py tests/test_psychiatry_security_migration.py tests/test_patient_authorization.py tests/test_clinic_authorization.py tests/test_versioned_consents.py --no-cov -q --tb=short --junitxml=/Users/rgnsystems/.hermes/cache/scratch/psychiatry-security-tests.xml`:
  **331 passed, 7 warnings**, 766,82 s. JUnit conferido programaticamente: 276 casos
  de segurança, 1 de migration, 9 de autorização paciente, 16 de autorização clínica,
  29 de consentimentos; zero failures/errors.
- Após o último ajuste `actor=None`, execução focada final:
  `.venv/bin/python -m pytest tests/test_psychiatry_security.py --nomigrations --no-cov -q --tb=short`:
  **277 passed**, 33,04 s. O teste adicional não fazia parte da coleta anterior do
  processo com migrations; foi comprovado separado. Ruff, Django check e
  makemigrations-check foram repetidos depois e permaneceram aprovados.

A primeira tentativa de regressão sem `--nomigrations` excedeu timeout da ferramenta;
isso não foi tratado como aprovação. O teste de evolução aditiva verifica dados
sintéticos da 0002 para 0003. PostgreSQL/Redis/RabbitMQ, serviços de emergência,
notificação, cobrança real, assinatura clínica e deploy não foram exercitados.
A suíte global pode estar em mutação por agentes de UI/mobile; não marcar PRD nem
aprovar produção com estes testes focados. Revisão independente e aprovação final
permanecem com o principal.

## Verificação posterior do principal — integração real

- JUnit da entrega auxiliar relido: 331 casos, sem failures/errors/skips; os
  277 casos atuais de segurança foram incluídos na nova execução abaixo.
- TDD do middleware: usuário B2C ativo sem clínica recebia `400`; após aplicar
  somente as nove exceções exatas, recebeu `200` com histórico vazio real.
- `tests/test_psychiatry_integration.py`: **70 passed** em SQLite com
  `--nomigrations` (ciclo rápido, não prova migrations). Verifica a matriz das
  **36 rotas**, nove exceções, caminhos semelhantes, seleção/header antigo,
  anonimato/inatividade, sessão desconhecida/revogada, CSRF real, ownership em
  SQL, legado sem dono e rejeição de autoativação de assinatura. O HTML B2C
  permanece fora da exceção. JUnit: `psychiatry-parent-integration-fast.xml`.
- PostgreSQL 17 descartável, settings e rotas reais, migrations normais:
  **473 passed, zero skips/failures/errors**, 89 avisos de `staticfiles/` ausente.
  Contagens conferidas pelo XML: segurança 277, integração 70, middleware 18,
  autorização paciente 9, autorização clínica 16, consentimentos 29,
  sessão/MFA 11, evolução de migration 1 e arquitetura 42.
- O teste de evolução `0002 → 0003` passou também em PostgreSQL: valores legados
  preservados, ausência de backfill e default novo False. Não foi executado em
  banco real nem foram lidos dados de pacientes.
- Ruff check/format: **14 arquivos aprovados**. Django check e
  `makemigrations --check --dry-run`: aprovados. `git diff --check` sem erros.
- Varredura estática focada em 15 arquivos Python: nenhum padrão de segredo ou
  chamada perigosa detectado pelo scanner; não substitui revisão independente.
- Mypy dos três alvos de integração **falhou**: 195 erros em nove arquivos de
  dependências, sem diagnóstico nos alvos diretos. Tipagem do domínio continua
  bloqueio de qualidade; isso não equivale a aprovação da suíte global.

Reprodução (usar exclusivamente as variáveis dos serviços sintéticos documentadas
no README; não executar outra suíte no mesmo banco simultaneamente):

```bash
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest \
  tests/test_psychiatry_security.py tests/test_psychiatry_security_migration.py \
  tests/test_psychiatry_integration.py tests/test_tenant_middleware.py \
  tests/test_patient_authorization.py tests/test_clinic_authorization.py \
  tests/test_versioned_consents.py tests/test_account_session_mfa.py \
  tests/test_domain_architecture.py --no-cov --reuse-db -q --tb=short \
  --junitxml=/Users/rgnsystems/.hermes/cache/scratch/psychiatry-parent-postgresql.xml
```

Evidências em `/Users/rgnsystems/.hermes/cache/scratch/`:
`psychiatry-parent-postgresql.xml`, `psychiatry-parent-postgresql.log`,
`psychiatry-parent-integration-fast.xml` e `psychiatry-parent-types.log`.

Revisão independente em andamento, ainda sem aprovação. A revisão deve examinar
também revogação durante espera de locks e cache de respostas privadas, além da
matriz de acesso. A UI legada continua contendo simulações e promessas que precisam
ser removidas e validadas renderizadas. Nenhum teste aqui certifica notificação,
serviço de emergência, IA clínica, cobrança ou assinatura. Sem commit/push/deploy.

## Revisão recebida e primeiro ciclo corretivo

A revisão independente reprovou o pacote. O relatório preservado no scratch,
`psychiatry-independent-review.json`, separa três achados Python (autorização após
locks, cache privado ausente e overflow numérico) das pendências do HTML legado.
O usuário escolheu corrigir e revisar antes de publicar a nova versão na VPS;
não houve commit, push nem deploy deste pacote.

Primeiro ciclo do principal, ainda sem aprovação independente:

- Reproduzida uma consolidação que persistia após revogação simulada na espera
  pelo rascunho. O serviço agora revalida o paciente depois do lock do recurso.
- Quatro testes PostgreSQL reais demonstraram ausência de serialização das novas
  escritas com a raiz da clínica. A correção usa a raiz antes dos recursos,
  revalida acesso depois da espera e mantém a gravação na mesma transação.
  A anamnese passou a delegar a escrita a `record_evaluation`.
- `tests/test_psychiatry_transaction_authorization.py` ampliou a evidência para
  19 casos: 12 simulações determinísticas após row lock e sete cenários com
  conexões PostgreSQL distintas. Estes últimos verificam bloqueio efetivo por
  `pg_blocking_pids`, commit da revogação/desativação e ausência de nova escrita.
- Regressão com migrations normais: **408 passed**, zero skips/failures/errors,
  incluindo os 19 casos novos, segurança, integração e arquitetura. Há 60 avisos
  de diretório `staticfiles` ausente no ambiente de teste.
- Ruff check/format dos três arquivos editados pelo principal passaram.

Evidências: `psychiatry-locks-red.xml`, `psychiatry-locks-green.xml` e
`psychiatry-locks-regression.xml` em `/Users/rgnsystems/.hermes/cache/scratch/`.
Uma nova revisão independente deve avaliar explicitamente os escritores de
usuários, vínculos e prescrições que não compartilham o lock da clínica; este
primeiro ciclo não certifica a serialização de todos os caminhos do produto.
Cache, limites numéricos e sanitização de templates seguem em correção separada.

## Conferência posterior das correções — nova revisão pendente

O parecer original acima permanece preservado e reprovado. Sua entrega assíncrona
foi recebida novamente depois das correções; ele não descreve integralmente a
versão atual, nem foi convertido em aprovação pelo integrador.

Conferência direta no código atual:

- `services._lock_domain` serializa mutações pela clínica e revalida depois da
  espera; `authorized_draft(lock=True)` revalida o paciente depois do row lock.
  Ainda é necessária revisão dos escritores externos que não compartilham essa
  fronteira, especialmente desativação, memberships, vínculos e prescrições.
- `domain_access` aplica `never_cache` por fora do tratamento local de erros.
  Respostas antecipadas dos middlewares globais não são cobertas pelo decorator;
  os testes registram esse limite, sem alegar proteção global ou apagar caches.
- `validation.number` compara o intervalo antes de `math.isfinite`, rejeitando
  inteiros extremos sem conversão para float. Os testes HTTP usam payload completo,
  CSRF real e controles válidos que persistem; os inválidos não gravam no domínio.
- Os templates filhos não integrados exibem indisponibilidade e não coletam nem
  simulam gravação, atendimento ou notificação. As listas somente leitura usam
  identidades autorizadas, escape HTML e estados vazios. A tradução das mensagens
  novas é um gate separado em andamento, não coberto só pelo atributo `lang`.

Execução local novamente realizada pelo principal:

```bash
TEST_DATABASE=sqlite SQLITE_NAME=:memory: DJANGO_SETTINGS_MODULE=config.settings.test \
  .venv/bin/python -m pytest tests/test_psychiatry_http_hardening.py \
  tests/test_psychiatry_rendered_safety.py \
  tests/test_psychiatry_transaction_authorization.py --nomigrations --no-cov \
  -q --tb=short -o faulthandler_timeout=60 \
  --junitxml=/Users/rgnsystems/.hermes/cache/scratch/psychiatry-parent-corrections-fast.xml
```

Resultado: **412 passed, 7 skipped, 232 warnings**, 84,76 s. Os sete skips exigem
locks PostgreSQL; este ciclo SQLite sem migrations não os certifica. Os warnings
são de `staticfiles/` ausente e incompatibilidade de `record_property` com JUnit
`xunit2`; não foram ocultados. Os testes de HTML usam Client/renderização Django,
não constituem inspeção de navegador ou aprovação clínica.

Os XMLs históricos também foram recontados, sem tratá-los como nova execução:
`psychiatry-locks-regression.xml` contém 408 casos, incluindo 19 transacionais;
`psychiatry-http-hardening-final.xml` contém 729 casos, incluindo 382 de HTTP.
Ambos têm zero failures/errors/skips. Não se somam essas contagens como casos
únicos, pois suas suítes se sobrepõem.

Nova revisão independente somente leitura foi solicitada contra as correções e
os achados originais, com relatório separado e hashes das fontes. Enquanto não
avaliada, não há encerramento dos achados nem autorização de publicação.

## Revisão focada de locks — SEC-01 permanece aberto

O relatório `psychiatry-locks-independent-review.json`, no scratch do principal,
reprovou o protocolo transacional atual (`passed: false`). Os hashes dos cinco
arquivos de implementação/teste registrados no relatório foram conferidos contra
a árvore atual e coincidem. A revisão é estática: não executou testes ou banco.

O lock da clínica e a revalidação pós-row do rascunho estão presentes, mas não
estabilizam todos os fatos de autorização até o efeito final. Foram apontados:

- `update_membership_role` não toma a raiz da clínica; usuários e ownership também
  podem mudar por caminhos não coordenados por essa raiz.
- A escrita de adesão não trava item/prescrição. Leituras, incluindo o GET do
  rascunho, consomem identificadores previamente autorizados sem a mesma proteção.
- Há potencial inversão `Clinic → FK User` versus `reset_password → User →
  auditoria → Clinic`; o deadlock ainda não foi reproduzido pelo principal.

Correção importante da análise: o encerramento de `CareRelationship` dispara
auditoria síncrona, que toma `Clinic` dentro da transação. Não é um exemplo de
revogação que consegue confirmar independentemente enquanto essa raiz está presa.
Isso não prova uma ordem segura para futuros locks secundários de vínculo.

### Reprodução local adicional do principal

`tests/test_psychiatry_secondary_waits.py` usa três conexões PostgreSQL reais e
somente dados sintéticos. A primeira segura a tabela de avaliações em `SHARE`,
a segunda passa pela política e espera no INSERT, e a terceira troca o papel do
profissional pelo serviço público `update_membership_role`. `pg_blocking_pids`
comprova a espera posterior à autorização. O novo papel é confirmado e relido
antes de liberar a escrita pendente.

Resultado observado: **HTTP 200 e uma avaliação persistida** depois do commit da
revogação. A regressão exige rejeição sem gravação nesse interleaving. Também
aceita a alternativa segura de serializar a revogação depois da escrita, desde
que o bloqueio efetivo seja comprovado; não exige que uma implementação segura
permita a revogação ultrapassar a operação.

Execução com `config.settings.test`, PostgreSQL local descartável do README,
migrations normais e `--reuse-db`: **1 failed**, sem skips/errors, em 5,99 s.
É um RED deliberado, não uma correção entregue nem aprovação. Evidência:
`/Users/rgnsystems/.hermes/cache/scratch/psychiatry-secondary-waits-red.xml`.
Nenhum código de runtime foi alterado nesta reprodução.

O protocolo de estabilização de locks secundários e a fronteira transacional das
leituras estão sob análise independente antes da próxima alteração. Acrescentar
apenas outra checagem imediatamente antes de `create` não elimina esperas depois
dela. SEC-01 segue bloqueando publicação; nenhum commit, push ou deploy realizado.

## Revisão corretiva Astra — SEC-01 parcial e SEC-04 aberto

O parecer `/Users/rgnsystems/.hermes/cache/scratch/psychiatry-corrections-independent-review.json`
permanece `passed: false`. Os hashes dos 18 arquivos centrais foram conferidos
pelo principal contra a árvore atual: **17 de 18 coincidem**. A única
divergência é `accounts/middleware.py`, alterado depois pelo próprio principal
na correção de idioma HTTP (`setdefault` de `Content-Language`), sem relação com
os achados de psiquiatria. O relatório original reprovado foi preservado
(SHA-256 `05d81392…1895`).

Estado por achado original:

- **LOG-01, LOG-02, LOG-03, LOG-04 e SEC-02: corrigidos.** Validação numérica
  compara intervalo antes de `isfinite`; templates sanitizados sem gravação/SOS
  fictícios, sem monitoramento/notificações prometidos e com indisponibilidade
  explícita; listas consomem contexto autorizado com escape padrão.
- **SEC-03: parcial.** `never_cache` cobre o conteúdo privado e os erros
  produzidos na fronteira da view; respostas antecipadas de CSRF global, tenant
  ausente e sessão revogada continuam sem garantia equivalente de `no-store`.
  Defesa em profundidade pendente, sem vazamento clínico demonstrado.
- **SEC-01: parcial.** A espera pela raiz da clínica e a revalidação pós-lock do
  rascunho estão presentes, mas `update_membership_role` e os admins de
  usuário/membership não aderem ao protocolo; leituras com QuerySet de PKs
  previamente autorizadas continuam materializando autorização. A reprovação
  já era esperada e confirmada pela reprodução PostgreSQL do principal em
  `tests/test_psychiatry_secondary_waits.py` (RED deliberado mantido).
- **SEC-04: aberto (novo achado).** Sessão revogada durante a espera pelo lock
  não é revalidada antes da escrita: `_lock_domain` revalida ator/papel, mas
  não `AccountSession`. Cenário estático: revogar a sessão de quem espera a
  raiz não impede a persistência quando a raiz é liberada.

Próximos passos registrados, sem implementação nesta etapa:

1. Estabilizar autorização até o efeito final com locks secundários dos
   escritores de membership/ator e revalidar sessão (`AccountSession`) dentro da
   transação — o desenho aguarda o resultado do protocolo de locks.
2. Envolver as leituras identificadas em fronteira transacional para não
   consumir PKs autorizados antes da revogação.
3. Testes PostgreSQL adicionais: revogação durante espera por escritores reais
   de membership/ator/sessão e leitura de QuerySet construído antes da revogação.
4. Política externa de `no-store` para os ramos antecipados (CSRF global, tenant,
   sessão), sem alterar catálogos públicos.

Sugestões de performance (limitar varredura de pacientes e campos carregados)
foram registradas sem alteração de consulta nesta etapa. Revisão por outra
família de modelos permanece pendente. Nenhum dado clínico real, nenhum commit,
push ou deploy; IA segue desativada.

## Parecer de desenho do protocolo de locks — direção aprovada com bloqueios

O parecer `psychiatry-lock-protocol-design-review.json` avaliou a proposta
delimitada do principal (Clinic como raiz + `SELECT FOR UPDATE NOWAIT` nos
secundários, catch de SQLSTATE 55P03 somente após rollback integral, leituras
dentro de fronteira transacional). Veredito: `proposal_safe: false` — viável
condicionalmente, **não aprovada como fechamento de SEC-01** sem os requisitos
abaixo. O parecer confirma que a abordagem corta as inversões demonstradas
(Clinic→User vs User→auditoria→Clinic; Clinic→vínculo vs vínculo→auditoria→Clinic)
sem exigir refatoração integral de accounts/audit/people.

Requisitos que a implementação precisa cumprir (resumo do protocolo recomendado):

1. **Conjunto de locks completo, não só User/membership**: perfil psiquiátrico,
   rascunho (`TwelveStepsAnamnesis`), `PrescriptionItem` e
   `PsychopharmacologyPrescription` também são alvos FK escritos. A ordem é
   Clinic primeiro, secundários NOWAIT em sequência documentada, revalidação
   das arestas (owner do perfil, autor/paciente/status do rascunho,
   `item.prescription_id`/`prescription.patient_id`) e reautorização sob os
   locks, mantendo tudo até o commit.
2. **Fronteira proprietária da transação**: o catch de 55P03 no nível HTTP
   precisa estar por fora do bloco que adquiriu a raiz; catch após atomic
   interno não basta se um atomic externo conserva a Clinic. Tradução para
   resposta genérica (preferência do parecer: 409) sem conteúdo clínico,
   sem retry parcial, sem engolir 40P01/40001/IntegrityError.
3. **Leituras sem escape lazy**: `visible_patients` hoje devolve QuerySet de
   PKs pré-aprovadas; a fronteira deve materializar DTOs ou executar callbacks
   dentro do contexto. Render HTML é síncrono (`django.shortcuts.render`),
   favorável: a transação deve abranger context processors, avaliação de
   QuerySets e render real. Proibir TemplateResponse pendente e streaming
   fora da fronteira.
4. **Tempo e predicados**: definir o instante de linearização da autorização
   após os locks; revalidar relógio/vigência (membership, vínculo, receita,
   versão de consentimento) após esperas. `PsychiatricPatientProfile` não tem
   unicidade (clinic,user): SELECT FOR UPDATE sem linhas não é lock de
   predicado; ausência/duplicidade nega.
5. **NOWAIT não cobre tudo**: não se propaga a INSERT/UPDATE, checks de FK,
   locks de tabela, índices únicos ou triggers. Não vender como "zero
   deadlocks"; classificar riscos operacionais separadamente.
6. **Backend**: PostgreSQL é a plataforma da garantia concorrente; SQLite fica
   para testes funcionais sem contabilizar como prova de locks.

O parecer traz inventário atual dos 20 consumidores (5 API, 6 HTML, 7 serviços,
2 seletores internos + shells protegidos), helpers públicos propostos com
assinaturas (`lock_users_for_authorization`, `lock_memberships_for_authorization`,
`lock_care_relationships_for_authorization`, `authorization_scope`, DTOs de
leitura), a matriz de locks por operação (avaliação, passo/consolidação de
rascunho, adesão, SOS/craving, resumo conectado), tradeoffs de contenção de
GETs na raiz e paginação pós-autorização, e 14 cenários de teste RED
determinísticos (RED-01..RED-14), incluindo reset_password e fechamento de
vínculo reais em ambas as ordens de chegada, espera posterior à autorização em
INSERT/FK com retenção até commit, e prova de que o revogador NÃO confirma
enquanto os locks são mantidos.

Decisão do principal: a direção Clinic+NOWAIT é a base de implementação;
a alternativa User→Clinic global fica registrada como superfície maior
(accounts/audit/people/convites/receivers), sem adoção neste ciclo. A
implementação seguirá o protocolo P1–P8 e os testes RED-01..RED-14 antes de
qualquer alegação de fechamento de SEC-01. SEC-04 (sessão revogada durante
espera) entra no mesmo protocolo: o inventário de `AccountSession` será
estabilizado junto com os secundários.

Fontes intactas; somente o parecer foi criado. Sem commit, push ou deploy; IA
permanece desativada e SEC-01/SEC-04 seguem bloqueando publicação.
