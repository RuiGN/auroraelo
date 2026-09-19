# Remoção de MFA e apresentação dos formulários

## Escopo entregue

- Removidos modelos, rotas, views, serviços, formulários e enforcement de MFA.
- Migração `accounts/0008_remove_mfa` elimina as tabelas antigas. Migrações históricas permanecem para manter o grafo reproduzível.
- `AccountSession`, recuperação de senha e reautenticação por senha continuam ativos. A configuração legada `MFA_ENCRYPTION_KEY` permanece porque também cifra sessões e integrações; não é enforcement de MFA.
- Os 99 templates atuais são varridos pelo teste de cobertura. Foram decorados 68 controles manuais em 22 templates, além dos campos Django compartilhados e especializados.
- Ícones decorativos não substituem labels. Checkboxes, radios, arquivos, cores, ranges e campos ocultos preservam suas funções nativas.
- Campos recebem placeholders traduzidos, quando aplicáveis, e larguras proporcionais; a ordem lógica de preenchimento é preservada. Horários de início/fim usam duas colunas em telas maiores, uma em dispositivos pequenos.
- Telefone, CPF/CNPJ e CEP têm apresentação e envio canônico. CEP se aplica ao endereço brasileiro, não ao código postal internacional. Não há corte silencioso de números longos ou internacionais. Valores monetários respeitam a localização sem máscara destrutiva.

## Evidência executada

- Suíte rápida: **1434 passed, 1 skipped, 3 deselected**. Os quatro casos não executados dependem de PostgreSQL ou migrações reais.
- Suíte PostgreSQL: **6 passed**, cobrindo os quatro casos acima e dois casos sobrepostos. Total agregado: **1438 testes distintos aprovados** (deduplicados por classname/name dos relatórios JUnit).
- Verificação independente de schema: **PASS PostgreSQL 0007 -> 0008: MFA tables removed; user and encrypted session preserved**.
- Navegador Chrome: 11 verificações aprovadas para máscaras, edição no meio do valor, autofill/envio, ausência de truncamento e responsividade em **360, 768 e 1280 px**.
- Gate de traduções ampliado para helpers: **passed, 1395 keys**; catálogo de português, inglês e espanhol compilado.
- `makemigrations --check --dry-run`: **No changes detected**.
- `manage.py check`, Ruff dos arquivos Python deste escopo e `git diff --check`: sem erros.

O teste histórico de migração de idioma agora restaura os leaf nodes em `finally`: sem isso, as tabelas MFA recriadas pelo rollback histórico impediam o flush de teardown no PostgreSQL.

## Reprodução

Suíte rápida:

```sh
.venv/bin/python -m pytest tests/ -o addopts='' --nomigrations -q \
  -k 'not preference_migration and not cross_tenant_content_version_is_rejected_by_database and not tenant_move_of_content_row_is_rejected_by_database'
```

Casos dependentes de PostgreSQL (usar exclusivamente o serviço descartável de `compose.test.yml` e variáveis DB_* desse ambiente):

```sh
.venv/bin/python -m pytest tests/test_content_tenant_invariant.py \
  tests/test_language_preferences.py::test_preference_migration_leaves_existing_users_without_explicit_choice \
  tests/test_consent_access_lifecycle.py::test_access_review_is_race_idempotent_on_postgresql \
  -o addopts='' -q
```

`python scripts/verify_mfa_removal.py` recusa bancos não isolados e exige `mindcare_mfa_verification` vazio em `127.0.0.1:55439`, com `config.settings.test` e `TEST_DATABASE=postgresql`.

O teste de navegador está em `scripts/verify-input-presentation.cjs`. Configure `PLAYWRIGHT_MODULE` para uma instalação local de Playwright e `CHROME_BIN` se o Chrome não estiver em `/usr/bin/google-chrome`. Ele renderiza fixtures Django, sem login ou acesso a dados reais.

## Publicação

Não houve commit, push ou deploy. O banco da aplicação em execução não foi migrado. A implantação deve aplicar `0008_remove_mfa`, publicar templates/catálogos/static e reiniciar os processos; conservar a chave de criptografia existente.
