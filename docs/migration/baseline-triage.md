# Triagem das falhas do baseline — evidência local

## Escopo e autoria

Checkout `/Users/rgnsystems/projects/auroraelo`, branch `hermes`, verificada antes de editar.
Somente cinco módulos de testes foram alterados por esta tarefa, além deste documento.
Nenhum scanner de produção, configuração, PRD, assertion existente ou arquivo visual foi
alterado. Sem commit, push ou deploy. Dados de teste sintéticos; sem leitura de `.env`,
credenciais, bancos, uploads ou prontuários reais.

A árvore está sendo modificada simultaneamente por outros agentes. As contagens abaixo
são fotografias das execuções, **não** uma declaração de suíte global atual verde.
A comparação foi por IDs completos extraídos do XML, não pela diferença de totais.

## Contagens verificadas

- Baseline preservado `aurora-baseline.xml`: **1439 casos = 1393 passed + 45 failed + 1 skipped**, zero errors.
- RED isolado: **1 failed**, com `FileNotFoundError: /bin/true` seguido de bloqueio por `ValidationError`.
- RED dos cinco módulos: **66 casos = 56 passed + 10 failed**.
- GREEN dos mesmos cinco módulos, com migrações normais: **66 passed**, zero failures/errors/skips.
- Reexecução de 43 IDs falhos do baseline, sem os dois drills: **16 passed + 27 failed**.
- Validação complementar: **60 casos = 58 passed + 1 failed + 1 skipped**, incluindo os dois drills PostgreSQL verdes, módulo completo de consentimento, regressões de conteúdo, traduções do scanner e checker estático.
- União das reexecuções dos **45 IDs originais**: **18 passaram e 27 falharam** nas respectivas execuções. Dos 18 verdes, **10** são o fix portátil desta tarefa; **2** são CI do parent; **4** são mudanças visuais/manifests concorrentes; **2** são drills com Docker agora disponível. Não é total de falhas da suíte completa atual.
- Ruff check dos cinco arquivos: **All checks passed!**; Ruff format: **5 files already formatted**; `git diff --check` do escopo: exit 0.

Todos os XML/logs citados ficam em `/Users/rgnsystems/.hermes/cache/scratch/`.
O baseline foi preservado, sem sobrescrita. Execuções focadas posteriores usam `--no-cov`
para evitar relatório global de cobertura sem representatividade; isso não altera assertions.
Não foi usado `--nomigrations`.

## Reprodução

Execute da raiz do checkout, com `.venv/bin/python` e `DJANGO_SETTINGS_MODULE=config.settings.test`.
Cada ID listado adiante pode ser passado entre aspas ao pytest (importante para parâmetros).

```bash
# RED isolado, antes do fix; arquivo de evidência preservado:
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest tests/test_clinic_setup.py::test_clinic_admin_uploads_safe_logo_and_contrasting_brand_colors -q --tb=short --junitxml=/Users/rgnsystems/.hermes/cache/scratch/aurora-upload-red.xml

# Mesmos módulos antes/depois; artefatos red e green separados:
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest tests/test_clinic_setup.py tests/test_content.py tests/test_content_http.py tests/test_learning_experience.py tests/test_professional_management.py -q --no-cov --tb=short --junitxml=/Users/rgnsystems/.hermes/cache/scratch/aurora-upload-modules-green.xml

.venv/bin/python -m ruff check tests/test_clinic_setup.py tests/test_content.py tests/test_content_http.py tests/test_learning_experience.py tests/test_professional_management.py
.venv/bin/python -m ruff format --check tests/test_clinic_setup.py tests/test_content.py tests/test_content_http.py tests/test_learning_experience.py tests/test_professional_management.py

# Segurança complementar e dois casos de restore do baseline:
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest tests/test_incident_readiness.py::test_postgres_drill_measures_objectives_and_binds_persistent_artifacts tests/test_incident_readiness.py::test_postgres_drill_fails_closed_when_rpo_objective_is_exceeded tests/test_duralux_wcag_and_responsive.py::test_s11_04_all_static_references_in_templates_resolve tests/test_consent_access_lifecycle.py tests/test_content_regressions.py tests/test_clinic_service_translations.py -q --no-cov --tb=short --junitxml=/Users/rgnsystems/.hermes/cache/scratch/aurora-triage-extra.xml
```

A reexecução `aurora-baseline-recheck.xml/.log` foi feita por `subprocess.run` com lista de
argumentos montada do XML original: para cada `testcase` com `failure`,
`classname.replace(".", "/") + ".py::" + name`, excluindo apenas os dois casos de
`test_incident_readiness` executados depois. Foram conferidos 43 IDs selecionados.
Um ID antigo de derivação Duralux foi renomeado por outro agente **depois** dessa execução;
reprodução futura deve distinguir caso removido/renomeado de caso que efetivamente passou.

## Classificação sem dupla contagem

| Causa | Falhas no baseline |
|---|---:|
| Raiz HTTP: contrato 200 versus redirecionamento 302 | 5 |
| Upload: comando simulado não portátil | 10 |
| Catálogo visual: redirect público substituiu contrato Django | 11 |
| Revogação: tenant escolhido implicitamente | 1 |
| Runtime visual: mistura de sistemas e código inline | 5 |
| Assets: pacote fonte Duralux ausente | 2 |
| Idiomas: publicação default e produção | 3 |
| Inventário de templates desatualizado | 1 |
| Assets: hashes documentados divergentes | 1 |
| Restore PostgreSQL: infraestrutura indisponível no baseline | 2 |
| CI: workflow ausente no baseline | 2 |
| CSP: fontes remotas e script inline | 1 |
| Template: tag static sem load | 1 |
| **Total** | **45** |

### Raiz HTTP: contrato 200 versus redirecionamento 302 (5)

**Causa confirmada.** `config.views.home` retorna incondicionalmente `redirect("account_login")`; os testes ainda esperam a antiga frase de fundação com status 200. Os casos en/es falham antes de verificar tradução, portanto não são evidência de catálogo ausente. No reset de senha, a primeira assertion 200 impede alcançar a verificação posterior de invalidação de ambas as sessões e rejeição de reutilização do token.

**Proposta, não aplicada:** decidir explicitamente o contrato da raiz (anônimo → login; autenticado → workspace, se aprovado). Atualizar testes de navegação para destino/status exatos e manter testes de identidade/sessão e token single-use. Testar tradução numa resposta HTML real com `Content-Language` e conteúdo visível. Preservar observabilidade e `X-Request-ID` também em redirects; não usar `status in (200, 302)` nem transformar o reset em teste superficial de status.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_accounts_authentication.py::test_password_reset_is_single_use_and_invalidates_all_existing_sessions` — FAIL.
- `tests/test_observability.py::test_request_id_accepts_safe_value_and_returns_response_header` — FAIL.
- `tests/test_shell_ui_translations.py::test_foundation_response_uses_the_request_language[en-Therapeutic platform available.]` — FAIL.
- `tests/test_shell_ui_translations.py::test_foundation_response_uses_the_request_language[es-Plataforma terap\xe9utica disponible.]` — FAIL.
- `tests/test_smoke.py::test_root_endpoint_uses_brazilian_portuguese` — FAIL.

### Upload: comando simulado não portátil (10)

**Causa confirmada / corrigida nesta tarefa.** Os dez decoradores invocavam `/bin/true`, inexistente neste macOS. `core/uploads.py:222–255` anexa o caminho temporário ao comando e converte `OSError` em bloqueio: comportamento de segurança correto. O RED isolado mostrou `FileNotFoundError` e `ValidationError`; nos fluxos HTTP o efeito era formulário 200 ou ausência de mídia persistida. Somente os decoradores passaram a `(sys.executable, "-c", "pass")`, com `import sys`. O subprocesso ainda é executado; nenhuma assertion, validação de tipo/tamanho, vínculo de clínica, auditoria ou scanner de produção foi alterado. É simulação de resultado limpo, não detecção real de malware.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_clinic_setup.py::test_clinic_admin_uploads_safe_logo_and_contrasting_brand_colors` — PASS.
- `tests/test_clinic_setup.py::test_branding_stage_uploads_logo_and_advances` — PASS.
- `tests/test_clinic_setup.py::test_modules_stage_enforces_prerequisites_and_advances` — PASS.
- `tests/test_clinic_setup.py::test_saved_branding_is_applied_to_the_active_tenant_workspace` — PASS.
- `tests/test_content.py::test_attach_media_validates_type_and_size` — PASS.
- `tests/test_content.py::test_attach_media_accepts_video_and_audio` — PASS.
- `tests/test_content_http.py::test_editorial_http_surface_supports_complete_versioned_workflow` — PASS.
- `tests/test_learning_experience.py::test_media_playback_grant_is_tenant_bound_and_expiring` — PASS.
- `tests/test_learning_experience.py::test_media_playback_grant_denies_draft_content_to_patients` — PASS.
- `tests/test_professional_management.py::test_admin_registers_complete_professional_profile_with_safe_photo_and_audit` — PASS.

### Catálogo visual: redirect público substituiu contrato Django (11)

**Causa confirmada, com implicação de segurança.** `config.views.design_system_reference` apenas redireciona para `/static/design_system/index.html`, sem decoração de login/staff e sem processar GET/POST. Por isso desaparecem contexto, paginação, CSRF, validação de formulário e tabela acessível. O middleware de tenant pula usuários anônimos: não torna essa rota privada. A página estática também pode ser servida diretamente, fora da autorização da view Django.

**Proposta, não aplicada:** separar showcase público estático, explicitamente demonstrativo e sem dados/operações clínicas, do catálogo funcional privado (autenticação, staff, tenant, CSRF e validação no servidor). Restaurar o catálogo privado ou aprovar sua retirada com cobertura equivalente de formulários/acessibilidade em rotas reais; não mudar 403/CSRF para aceitar redirect. O HTML público lido ainda tinha Tailwind CDN e `onsubmit` que anuncia “Prontuário salvo com sucesso!” sem persistência: rotular como demonstração e remover essa promessa. Não interpretar esse toast como operação clínica. Os onze casos têm uma causa comum, não onze bugs independentes de widgets.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_component_widget_contracts.py::test_component_catalog_posts_with_real_csrf_validation` — FAIL.
- `tests/test_content_components.py::test_visual_reference_catalogs_all_component_variants` — FAIL.
- `tests/test_content_components.py::test_visual_reference_filter_preserves_the_active_order` — FAIL.
- `tests/test_content_components.py::test_visual_reference_pagination_matches_the_rendered_table` — FAIL.
- `tests/test_design_system.py::test_design_reference_requires_authentication` — FAIL.
- `tests/test_design_system.py::test_design_reference_rejects_authenticated_non_staff` — FAIL.
- `tests/test_design_system.py::test_design_reference_is_pt_br_accessible_and_demo_free` — FAIL.
- `tests/test_form_components.py::test_visual_reference_catalogs_the_accessible_form` — FAIL.
- `tests/test_form_components.py::test_visual_reference_validates_posted_form_on_the_server` — FAIL.
- `tests/test_form_components.py::test_visual_reference_reports_a_valid_server_submission` — FAIL.
- `tests/test_theme_charts.py::test_visual_reference_chart_has_summary_table_and_local_vendor_asset` — FAIL.

### Revogação: tenant escolhido implicitamente (1)

**Causa confirmada; prioridade de segurança.** `clinics.services.selected_clinic_id` usa a primeira associação ativa (`.first()`) quando faltam header e sessão, e grava a seleção automaticamente. O teste cria administrador de duas clínicas, remove `active_clinic_id` e recebe 200 em vez de 400. `ClinicTenantMiddleware` então injeta a clínica; `consents.views._context` e `_require_clinic_admin` veem contexto válido e a fila filtra por essa clínica. Isso viola a seleção explícita; não prova, por si só, acesso a clínica sem associação.

**Proposta, não aplicada:** exigir seleção explícita para fila e acknowledgement de revogação, idealmente no contrato transversal de resolução, e retornar o 400 documentado na ausência dela. Não conceder tenant global, não desativar managers e não mudar o teste para 200. Validar GET e POST sem seleção, UUID inválido, associação expirada, clínica de outro usuário e tentativa cross-tenant; provar ausência de mutação/auditoria de sucesso ao negar. Exige revisão independente do responsável por autorização/consentimento. O módulo completo foi reexecutado; somente este caso falhou e o teste de concorrência PostgreSQL permaneceu skipped em SQLite.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_consent_access_lifecycle.py::test_revocation_work_http_fails_closed_without_explicit_active_tenant` — FAIL.

### Runtime visual: mistura de sistemas e código inline (5)

**Causas confirmadas no baseline.** A allowlist proíbe qualquer `index.html` dentro de `static/`; o checkout contém `static/design_system/index.html`. O layout esperava favicon Duralux, mas o shell usa outro caminho. Os dois testes de legado detectavam `css/tokens.css` como substring de `design_system/css/tokens.css`; a checagem não distingue namespace. O workspace continha `style=` inline.

**Proposta, não aplicada:** aprovar manifesto de runtime híbrido/novo com lista explícita de assets públicos, CSP, acessibilidade e ausência de operações simuladas enganosas. Comparar caminhos normalizados completos no checker de legado para evitar falso positivo por substring, sem retirar a proibição dos assets efetivamente legados. Levar estilos inline para CSS de produto. Atualizar contrato do favicon somente se o novo asset local estiver validado. Os dois casos de legado e o de inline ficaram verdes durante mudanças de outro agente; não atribuir isso ao fix de upload.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_design_system.py::test_only_allowlisted_application_assets_are_in_static_storage` — FAIL.
- `tests/test_layouts.py::test_workspace_shell_uses_only_the_duralux_runtime` — FAIL.
- `tests/test_duralux_legacy_removal.py::test_runtime_templates_reference_no_legacy_or_demo_source_paths` — PASS.
- `tests/test_duralux_legacy_removal.py::test_base_loads_only_global_duralux_dependencies` — PASS.
- `tests/test_sprint4_duralux_templates.py::test_sprint4_templates_use_product_classes_instead_of_inline_code` — PASS.

### Assets: pacote fonte Duralux ausente (2)

**Causa confirmada.** `design_system_duralux/` não existe. Um teste exige a pasta e outro lê `assets/css/theme.min.css` para comparar derivação sanitizada. Não é problema de finder do runtime.

**Proposta, não aplicada:** esclarecer se a fonte vendorizada deve ser restaurada de origem verificável ou foi deliberadamente retirada. Se retirada, preservar procedência/licença, versão e hash verificável do runtime e validar ausência de imports externos/source maps. Trocar somente o nome da pasta não conserva a garantia de derivação exata. Durante a investigação outro agente mudou `test_design_assets_are_application_owned` e renomeou o segundo caso para `test_legacy_theme_runtime_remains_sanitized`; o resultado abaixo é da reexecução anterior a essas mudanças, não valida os contratos novos.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_design_system.py::test_design_assets_are_application_owned` — FAIL.
- `tests/test_duralux_static_foundation.py::test_duralux_theme_is_exact_sanitized_source_derivation` — FAIL.

### Idiomas: publicação default e produção (3)

**Causa confirmada.** `config/settings/base.py` publica pt-br/en/es; o settings de teste importa essa lista e o teste de produção com variáveis sintéticas também observou os três idiomas. O README lido no início restringia base/produção a pt-br e reservava en/es à aceitação local.

**Proposta, não aplicada:** restaurar a allowlist revisada em base/produção, mantendo os idiomas de aceitação em development, ou obter aprovação e evidência de revisão dos catálogos antes de ampliar publicação. Não alterar os três testes para legitimar publicação não revisada. Manter separadas preferências possíveis do modelo e idiomas efetivamente publicados. Não traduzir conteúdo clínico autoral. Nenhuma configuração de produção foi alterada nesta tarefa.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_language_preferences.py::test_only_reviewed_portuguese_is_published_by_default` — FAIL.
- `tests/test_language_preferences.py::test_runtime_languages_separate_local_acceptance_from_production[config.settings.production-expected_languages1]` — FAIL.
- `tests/test_language_selector_ui.py::test_default_publication_does_not_offer_unreviewed_languages` — FAIL.

### Inventário de templates desatualizado (1)

**Causa confirmada.** A contagem executada encontrou 100 templates sob `templates/`; o relatório de cobertura não contém `Templates atuais no disco: **100**`. O caso mede documentação versus árvore, não um defeito HTTP.

**Proposta, não aplicada:** reconciliar inventário e escopo i18n com a árvore aprovada, explicar templates adicionados/removidos e reexecutar compilação/catálogos. Não excluir arbitrariamente arquivos da contagem para obter verde. Apps com templates próprios merecem inventário explícito adicional.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_duralux_legacy_removal.py::test_template_coverage_reconciles_baseline_and_migration_helpers` — FAIL.

### Assets: hashes documentados divergentes (1)

**Causa confirmada no baseline.** `css/auth.css` tinha SHA-256 observado `9e773f27a0fdfded03fa4586cdf1221d00124e3e249579c77964226ed1a367ca`, contra manifesto `518c5b8552b2cf1a88dce50e8a776cc9233a1276e816838d355c34291954c2ff`. A reexecução passou enquanto outro agente modificava CSS/manifests; esta tarefa não os editou.

**Proposta:** só recalcular manifesto depois de revisar bytes pretendidos e procedência; preservar checagem criptográfica. Um novo hash não demonstra por si só ausência de regressão visual ou segurança.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_duralux_static_foundation.py::test_documented_runtime_hashes_match_the_published_assets` — PASS.

### Restore PostgreSQL: infraestrutura indisponível no baseline (2)

**Causa de baseline delimitada.** O primeiro teste falhou em `docker network create --internal`; o segundo tentou ler um relatório nunca produzido. O stderr disponível no baseline não identifica a causa completa do daemon/rede. Na investigação atual, `docker info --format '{{.ServerVersion}}'` retornou `29.7.2` e ambos os testes passaram sem edição. Os scripts usam nomes UUID, rede interna, bancos sintéticos e limpeza dos próprios recursos.

**Proposta:** executar esses gates com daemon disponível e preservar artefatos de RTO/RPO; melhorar diagnóstico/preflight em tarefa separada, não simular relatório nem marcar skip silencioso. Verde local é ensaio sintético, não teste de recuperação de produção. Não houve leitura de backup ou banco real.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_incident_readiness.py::test_postgres_drill_measures_objectives_and_binds_persistent_artifacts` — PASS.
- `tests/test_incident_readiness.py::test_postgres_drill_fails_closed_when_rpo_objective_is_exceeded` — PASS.

### CI: workflow ausente no baseline (2)

**Causa confirmada / resolvida por outro responsável.** `.github/workflows/quality.yml` não existia no baseline; o parent o criou antes desta etapa. Os dois casos agora passam. O arquivo foi somente lido; esta tarefa não reivindica sua autoria nem execução remota do GitHub Actions. Passar assertions sobre YAML não equivale a uma execução aprovada de todos os jobs.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_regulatory_governance.py::test_ci_executes_regulatory_matrix_gate` — PASS.
- `tests/test_security_controls.py::test_ci_blocks_committed_secrets_with_repository_owned_scanner` — PASS.

### CSP: fontes remotas e script inline (1)

**Causa confirmada; prioridade de segurança.** O header observado inclui `script-src 'self' 'unsafe-inline'` e domínios externos Tailwind/Cloudflare, além de Google Fonts/Unsplash em outras diretivas. O contrato esperava scripts locais sem inline. Não é falha causada por upload.

**Proposta, não aplicada:** compilar Tailwind localmente, mover scripts para arquivos próprios e remover dependências remotas não aprovadas antes de restringir a CSP. Preservar `object-src 'none'`, `frame-ancestors 'none'` e demais diretivas. Revisar headers também em arquivos estáticos servidos pelo proxy, pois middleware Django pode não cobri-los. Não alargar o teste de segurança para aceitar a política relaxada.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_security_controls.py::test_application_responses_have_restrictive_security_headers` — FAIL.

### Template: tag static sem load (1)

**Causa confirmada.** `templates/workspace/home-aurora-elo.html` usa `{% static %}` sem carregar a biblioteca naquele template; Django lança `TemplateSyntaxError` na linha 53. Bibliotecas carregadas no template pai não ficam automaticamente disponíveis ao parser do filho.

**Proposta, não aplicada:** adicionar `{% load static %}` no template proprietário após aprovação do responsável visual, ou retirar o template se for artefato descartado e reconciliar inventário/escopo. Não retirar o caso de compilação apenas para esconder sintaxe inválida.

**IDs completos e resultado da reexecução registrada:**

- `tests/test_template_compilation.py::test_application_template_compiles[workspace/home-aurora-elo.html]` — FAIL.

## Checker estático: limite do verde

O checker relevante é
`tests/test_duralux_wcag_and_responsive.py::test_s11_04_all_static_references_in_templates_resolve`,
não um script independente em `scripts/`. **Passou** tanto no baseline quanto na execução
complementar. Logo, não é uma 46ª falha: é uma limitação de cobertura a considerar na migração.

Ele lê apenas `templates/**/*.html` e reconhece tags literais `{% static "..." %}`
com uma regex. Não compila o template, não cobre templates internos de apps como
`psychiatry/templates`, URLs literais em href/src, `url()` em CSS, tags com atribuição
`as`, expressões dinâmicas ou arquivos HTML públicos de `static/`.
Isso explica por que pode passar ao mesmo tempo que o template sem `{% load static %}` falha.

O probe sem banco `aurora_triage_probe.py` ampliou somente a inspeção de tags literais:
**19 referências únicas** no escopo `templates` e **11** em `psychiatry/templates`,
sem caminho ausente em ambos no instante da execução. Não soma esses números como
referências globalmente distintas. O probe não modifica templates e não substitui
`collectstatic`, resolução pelo manifesto ou validação renderizada/rede do navegador.

Proposta futura: manter compilação Django, ampliar raízes explicitamente pelos loaders,
validar URLs locais CSS/JS/HTML e assets de `collectstatic`/manifesto em diretório descartável;
incluir teste de página renderizada sem 404. Não trocar falhas por bypass geral de paths.

## Segurança do scanner preservada e limitação adicional

O mesmo probe exercitou `core.uploads.require_clean_malware_scan` sem DB, com bytes sintéticos:

- `(sys.executable, "-c", "pass")`: aprovado, posição do upload restaurada para 0.
- `(sys.executable, "-c", "raise SystemExit(1)")`: bloqueado por
  “O arquivo não foi aprovado na varredura de segurança.”, posição 0.
- `("/bin/true",)`: bloqueado por scanner indisponível, posição 0.

Há ainda `("/bin/false",)` em
`tests/test_clinic_setup.py::test_branding_rejects_logo_when_malware_scan_does_not_clear`.
`/bin/false` também não existe neste macOS. O caso fica verde por indisponibilidade, não
por um scanner realmente executado retornar código não zero. **Não foi alterado**, pois a
autorização limita o fix a `/bin/true`. Recomenda-se tarefa separada para portátil retorno
não zero e para distinguir explicitamente indisponibilidade de reprovação. O probe acima
confirma ambos os ramos reais, mas não corrige essa lacuna do teste persistente.

## Arquivos desta tarefa e limites

- `tests/test_clinic_setup.py`: import sys e quatro comandos simulados.
- `tests/test_content.py`: import sys e dois comandos simulados.
- `tests/test_content_http.py`: import sys e um comando simulado.
- `tests/test_learning_experience.py`: import sys e dois comandos simulados.
- `tests/test_professional_management.py`: import sys e um comando simulado.
- `docs/migration/baseline-triage.md`: esta classificação e evidências.

Diff de código: **15 linhas adicionadas / 10 removidas**, exclusivamente cinco imports e
dez substituições. O estado inicial dos cinco arquivos não tinha alterações Git.
Outras mudanças observadas no checkout não foram feitas por esta tarefa.

Não foi reexecutada a suíte completa nesta etapa; não há afirmação de ausência global de
regressões simultâneas. O teste de concorrência de consentimento requer PostgreSQL e
permaneceu skipped no módulo sob SQLite; os dois drills PostgreSQL são processos separados
e não tornam esse teste de concorrência aprovado. Não houve validação visual/browser,
CI remota ou operação em produção. Consentimento, CSP e exposição do catálogo público
seguem pendências de decisão/revisão; não devem ser eliminadas alterando assertions.

## Execução global posterior — notificação tardia e rechecagem

O processo `proc_1e5abceabd55` terminou com exit 1. Seu XML
`aurora-release-global.xml` registra a execução iniciada às 15:24:52 e concluída
às 15:44:06 de 2026-09-20, no fuso -03. A notificação foi recebida depois de novas
correções; não representa a árvore corrente. Não confundir esse arquivo com o
baseline anterior `aurora-baseline.xml` de 1439 casos.

Contagem conferida pelo principal nos casos e nos totais declarados do XML:

- **2440 casos: 2393 passed, 30 failed, 17 skipped, zero errors**.
- O log confirma 597 warnings e duração de 1154,64 s.
- Todos os 17 skips indicam ausência de `RECOVERY_TEST_REDIS_URL` apontando para
  o Redis descartável permitido. Os mesmos 17 IDs passaram na execução posterior
  `recovery-language-postgresql.xml`, com Redis local DB13. Isso não reescreve os
  skips históricos nem transforma uma suíte focada em aprovação global.

Os **30 IDs falhos exatos** foram extraídos programaticamente e reexecutados com
PostgreSQL descartável, migrations normais, `--reuse-db`, `--no-cov` e sem alterar
assertions: **5 passed, 25 failed**, sem errors/skips. Conferência por conjuntos:
30 solicitados, 30 observados, nenhum ID ausente ou adicional. Evidências separadas:
`aurora-release-failures-recheck.xml` e `aurora-release-failures-recheck.log` no scratch.

Passaram nessa seleção focada:

- contrato de idiomas de `config.settings.development`;
- escopo cumulativo de superfícies e chaves gettext;
- rejeição de produção sem segredo;
- checker de catálogos nos parâmetros `valid` e `stale`.

Não se atribui automaticamente esse resultado a um fix específico: mudanças
concorrentes e dependência da ordem/importação de settings precisam ser consideradas.
Esses cinco verdes isolados não encerram os casos antes de uma nova execução global.

As 25 falhas restantes incluem seleção implícita de tenant na fila de revogação,
CSP permissiva, catálogo funcional substituído por redirect estático, contratos
da raiz HTTP, publicação de idiomas, inventário e compilação de templates. As
causas históricas acima são pontos de partida, não autorização para enfraquecer
testes, recuperar `design_system_duralux/` ou publicar uma suíte reprovada.

A reprodução posterior de SEC-01 em `tests/test_psychiatry_secondary_waits.py`
não estava nessa coleta global e permanece um bloqueio adicional de segurança.
Não houve alteração de runtime nesta rechecagem, nem commit, push ou deploy.

## Tipagem estrita dos sete módulos de testes — verificação do principal

Dois auxiliares corrigiram tipagem mypy estrita em sete módulos de testes, sem
alterar runtime. O principal reexecutou os gates com ambiente sanitizado
(`config.settings.test`, SQLite `:memory:`, `--nomigrations`, `--no-cov`):

- Seis módulos de UI/entrada: **zero diagnóstico mypy no alvo**; ruff
  check/format aprovados; os mesmos 100 IDs passaram antes e depois.
- `tests/test_clinical_operations.py`: **144 → 79 diagnósticos no alvo**, todos
  `no-untyped-call` de backend não tipado (`create_product`, `move_stock`,
  `set_grant`, `read_records`, `for_clinic`, `save`, etc.). A tipagem de
  `set_grant`/`list_resources` isoladamente não resolve; exige o pacote
  `clinical_operations` completo. Registrado como dívida de backend, sem cast,
  `type: ignore` ou Any para contornar.
- Ruff/format dos sete alvos: aprovados. `git diff --check`: limpo.

Reexecução conjunta pelo principal: **137 passed, 2 failed, 3 skipped**
(`typing-seven-modules-verify.xml`). As duas falhas são
`test_immutable_rows_resist_raw_sql[movement/record]`, esperadas sob
`--nomigrations` (a migration `0002_append_only` instala triggers via RunSQL,
que o modo não aplica); esses casos passaram na execução PostgreSQL com
migrations normais registrada em `clinical-boundary-corrections-postgresql.xml`
(170 passed). Os três skips são PostgreSQL-only sob SQLite.

Mypy global permanece reprovado: 205 erros em 8 arquivos na execução do
principal, incluindo os 79 `no-untyped-call` do teste clínico (dívida de backend)
e erros preexistentes em `clinical_operations/models.py`,
`psychiatry/models.py`, `config/celery.py` e `clinics/services.py`. Nenhum foi
silenciado; não se declara mypy global verde. Sem commit/push/deploy.

## Fechamento pré-publicação — suíte SQLite `--nomigrations` vs HEAD limpo

A execução global em SQLite (`config.settings.test`, `SQLITE_NAME=:memory:`,
`--nomigrations`, `--no-cov`) totalizou **2634 casos: 2574 passed, 31 failed,
29 skipped**. Os 31 IDs falhos foram reexecutados um a um contra o HEAD limpo
(`a12ca59`, extraído em `/tmp/aurora-baseline`) sob os mesmos flags, via JUnit
comparado programaticamente (`baseline-failures.xml`): **27 falham igualmente
no HEAD limpo** e são dívida preexistente de `main`, não deste trabalho.
Nenhuma das 27 foi enfraquecida ou removida para publicação; permanecem
registradas como falhas conhecidas (design system trocado por redirect
estático sem atualizar testes, catálogo visual, publicação de idiomas,
CSP/root HTTP, inventário/compilação de templates).

As **4 falhas novas** eram introduzidas por este trabalho e foram tratadas
sem enfraquecer contratos:

- `test_auth_duralux_acceptance::test_public_auth_forms_use_the_minimal_shell_...`:
  o seletor do wrapper foi atualizado de `minimal-card-wrapper product-auth-inner`
  para `aurora-auth-card`, o design vigente exigido por
  `tests/test_aurora_design_system.py`. Todos os contratos funcionais (CSRF,
  `name=email`, autocomplete, `name=password`, link de recuperação, `pt-br`)
  permanecem exigidos. 5 passed.
- `test_immutable_rows_resist_raw_sql[movement/record]` e
  `test_ownership_migration_preserves_legacy_values_and_does_not_backfill`:
  receberam guarda explícita que pula com motivo quando o nó de migration
  (`clinical_operations.0002_append_only` /
  `psychiatry.0003_verified_ownership_and_opt_in`) está ausente do grafo —
  exatamente o efeito de `pytest --nomigrations`, que não aplica RunSQL nem
  executa migrations. Com migrations reais ambos rodam: o teste de migration
  passou isolado (1 passed) e os triggers append-only passam com migrations
  normais (registrado em `clinical-boundary-corrections-postgresql.xml`).

O workflow `.github/workflows/quality.yml` foi elaborado, mas **não foi
publicado neste commit**: rodaria vermelho de saída (mypy global com dívida
conhecida, ruff com 141 erros preexistentes em comandos de seed não
modificados e a suíte PostgreSQL com as 27 falhas acima). Publicar um gate
nascente-vermelho não agrega proteção; o arquivo permanece no checkout como
pendência para quando o baseline estiver saneado. As 27 falhas preexistentes
não bloqueiam a publicação deste trabalho porque já existem em produção no
HEAD de `main`; este commit não as introduz e a suíte focada de segurança
(psiquiatria/operações clínicas/recuperação) permanece verde.

# Fechamento do alinhamento visual (design system Aurora Elo, 2026-09-21)

Demanda do usuário: o design system publicado e a tela de login não estavam
conformes a `design_system/index.html` e `design_system/login.html`, e ainda
havia itens do `design_system_duralux`. Ações e verificação:

- Showcase `static/design_system/` sincronizado com o pacote (páginas,
  componentes, JS e assets; `css/tokens.css`/`custom.css` agora são as cópias
  do pacote, com `@theme` v4 e import de fontes Google — a CSP já libera).
  Paridade é garantida por teste byte-a-byte (`test_static_showcase_matches_...`).
- Insumos do build movidos para `design_system/src/tokens.local.css` e
  `src/custom.local.css` (sem `@theme`, sem fontes remotas); `src/aurora.css`
  compila para `static/design_system/css/aurora.css` (25,8 KB; sem
  `@theme`/`@tailwind`/`fonts.googleapis.com` no artefato — contrato de teste).
- Login reescrito conforme `design_system/login.html` (fundo escuro aurora,
  card de vidro, abas de perfil, rodapé de crise 192/188 com msgids já
  traduzidos). O login não carrega mais nenhum CSS/JS Duralux — só
  `aurora.css` + `shell.js` + feather + `form-behaviors.js`.
- Chrome do workspace (base/vertical/detached/header/navigation) sem classes
  `nxl-*`/`product-auth`, sem `product-shell.js`/`language-selector.js`;
  sidebar escura aurora, header claro, breadcrumb, `<main id="main-content">`.
  Bootstrap/feather/`theme.min.css`/`product-integration.css` permanecem como
  camada de compatibilidade de conteúdo (per INTEGRATION.md).
- Seletor de idioma virou `<select>` nativo com POST (padrão da referência);
  `shell.js` ganhou drawer/mini, envio com confirmação de alterações não
  salvas, toggle de senha, abas de perfil e pin de tema claro.
- Página staff antiga `templates/visual_reference/reference.html` (morta desde
  o redirect do showcase) removida; 99 templates no disco (doc reconciliado).
  Testes obsoletos da página removidos/reescritos para o contrato novo.
- i18n: 8 msgids novos em pt_BR/en/es; check escopado passou (1357 chaves,
  0 faltando). `ui-strings.json` regenerado para os 13 templates alterados;
  `runtime-assets.json` com os novos hashes.
- Testes de guardas obsoletos modernizados: test_design_system (allowlist e
  showcase), test_theme_charts, test_auth_duralux_acceptance, test_layouts,
  test_language_selector_ui, test_aurora_ui_translations,
  test_consent_navigation_translations, test_runtime_language_publication,
  test_duralux_legacy_removal, test_duralux_wcag_and_responsive,
  test_content_components, test_form_components,
  test_component_widget_contracts, test_duralux_domain_templates.

Suíte completa final (SQLite, `--nomigrations`): **2581 passed, 13 failed,
32 skipped**. Comparação JUnit contra o baseline: **14 falhas resolvidas,
0 novas**. As 13 restantes são exatamente as preexistentes (SEC-01/psiquiatria,
home-aurora-elo, publicação de idiomas e afins) e permanecem registradas como
pendências, sem regressão introduzida por este trabalho.
