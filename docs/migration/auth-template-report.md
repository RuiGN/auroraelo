# Relatório de migração dos templates de autenticação

## Escopo

Implementação de `DURALUX.prd` S08.01 e S08.02 nos templates server-rendered de autenticação, MFA e sessões. As alterações preservam rotas, métodos HTTP, nomes de campos, CSRF, redirecionamentos e políticas de autenticação existentes.

## Referências locais

- `design_system_duralux/auth-login-minimal.html`
- `design_system_duralux/auth-register-minimal.html`
- `design_system_duralux/auth-reset-minimal.html`
- `design_system_duralux/auth-resetting-minimal.html`
- `design_system_duralux/auth-verify-minimal.html`

Foram reutilizadas a estrutura `auth-minimal-wrapper > auth-minimal-inner > minimal-card-wrapper`, a marca flutuante, o cartão único, a hierarquia tipográfica compacta, ações primárias de largura total e a composição centralizada das confirmações. Não foram copiados login social, customizador de tema, JavaScript de OTP segmentado nem links sem destino, pois esses elementos não existem nos contratos do produto.

## Arquivos

- `templates/accounts/auth_base.html`: shell minimal, marca do produto, ativos locais e cartão único.
- `templates/accounts/auth_form.html`: formulário compartilhado para login, convite, recuperação, redefinição, reautenticação e desafio MFA.
- `templates/accounts/auth_message.html`: confirmações e estados de recuperação.
- `templates/accounts/mfa_enroll.html`: QR local, chave manual, reinício e confirmação TOTP.
- `templates/accounts/mfa_recovery_codes.html`: aviso e lista dos oito códigos de uso único.
- `templates/accounts/sessions.html`: dispositivos, estado, data semântica e ações explícitas de revogação.
- `static/duralux/css/auth.css`: ajustes limitados ao shell de autenticação, QR e grade responsiva dos códigos.
- `tests/test_auth_duralux_acceptance.py`: aceitação de respostas renderizadas e preservação dos contratos de entrada/segurança.

## Validação executada

Banco descartável PostgreSQL em `127.0.0.1:55439`, banco base `mindcare_auth` e banco pytest `test_mindcare_auth`. Redis de teste em `127.0.0.1:56389`. Todas as execuções usaram `--reuse-db --no-cov`.

```text
pytest tests/test_auth_duralux_acceptance.py --reuse-db --no-cov -q
9 passed in 2.58s
```

```text
pytest \
  tests/test_accounts_authentication.py::test_authentication_templates_are_accessible_and_pt_br \
  tests/test_accounts_authentication.py::test_password_recovery_response_is_generic_for_known_and_unknown_email \
  tests/test_accounts_authentication.py::test_password_reset_is_single_use_and_invalidates_all_existing_sessions \
  tests/test_account_session_mfa.py::test_mfa_enroll_get_renders_local_qr_and_manual_key_without_cache \
  tests/test_account_session_mfa.py::test_mfa_enroll_post_confirms_factor_once_and_keeps_local_continue_url \
  tests/test_account_session_mfa.py::test_mfa_enroll_invalid_code_preserves_pending_secret \
  tests/test_account_session_mfa.py::test_confirmed_mfa_challenge_hides_provisioning_material_and_disables_cache \
  tests/test_account_session_mfa.py::test_recovery_codes_response_is_not_cacheable \
  tests/test_account_session_mfa.py::test_revoking_all_other_sessions_requires_current_password \
  --reuse-db --no-cov -q
9 passed in 5.04s
```

`python manage.py check --settings=config.settings.test` também concluiu sem problemas.

O script reproduzível `scripts/verify-duralux-auth.cjs` foi executado contra o servidor Django isolado em `127.0.0.1:8766` e o banco sintético `mindcare_auth`:

```text
PLAYWRIGHT_MODULE=/home/rui/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright \
  node scripts/verify-duralux-auth.cjs
36 visual auth cases passed
```

A matriz cobriu nove estados em 320 × 800 e 1440 × 1000, nos temas claro e escuro: login inválido, recuperação com mensagem genérica, redefinição válida, redefinição inválida, aceite de convite, matrícula MFA inválida, desafio MFA confirmado, códigos de recuperação e sessões com senha de reautenticação inválida. Cada caso verificou status HTTP esperado, tema aplicado, ausência de overflow horizontal e erros JavaScript. Os estados específicos também verificaram foco no primeiro campo inválido, vínculos de erro, QR carregado sobre fundo branco computado, ausência de material de matrícula no desafio e oito códigos de recuperação.

O resultado estruturado e as 36 capturas estão em `docs/migration/evidence/visual-auth/`; `results.json` foi gerado em `2026-09-08T20:32:20.287Z` com 36 casos aprovados. As fixtures que contêm cookies, tokens e segredos exclusivamente sintéticos ficam em `.migration-runtime/auth-preview-fixtures.json`, diretório ignorado pelo Git.

## Receitas para aceitação visual sintética

As receitas abaixo devem ser criadas somente no banco de preview e não exigem provedores ou contas reais.

- Login: `GET /accounts/login/`. O POST inválido com `email=endereco-invalido` e senha vazia mostra erros associados aos dois campos.
- Recuperação: `GET /accounts/password-recovery/`. Um POST com qualquer e-mail sintético válido mostra a confirmação genérica. Para visualizar redefinição, crie um `UserFactory`, gere `uid` com `urlsafe_base64_encode(force_bytes(user.pk))` e `token` com `default_token_generator.make_token(user)`, então abra `/accounts/password-reset/<uid>/<token>/`.
- Convite/cadastro: autentique um usuário sintético com papel `CLINIC_ADMIN`, mantenha `active_clinic_id` na sessão e abra `GET /accounts/invitations/new/`. Após emitir convite para `convidada@example.test`, extraia da caixa de e-mail locmem a rota `/accounts/invitations/<token>/accept/` e abra-a anonimamente.
- Matrícula MFA: autentique `UserFactory.create()` e abra `GET /accounts/mfa/enroll/`. A view cria o segredo pendente e entrega QR/chave manual com cabeçalhos `no-store`.
- Erro de matrícula: no mesmo cliente, poste um valor não numérico como `not-a-code` em `/accounts/mfa/enroll/` para manter o QR e mostrar o resumo de erro sem risco de colisão com um TOTP vigente.
- Códigos de recuperação: leia `response.context["manual_secret"]`, gere `current_totp_code(secret=secret)` e poste o código em `/accounts/mfa/enroll/`. A resposta mostra os oito códigos uma vez.
- Desafio MFA: confirme previamente `start_totp_enrollment` com `confirm_totp_enrollment` e abra `GET /accounts/mfa/verify/`. Esse estado deve conter somente o campo de código, sem QR, URI ou segredo.
- Sessões: autentique um `UserFactory`, crie `Session` e `AccountSession.objects.create_for_session(..., client_label="Firefox em computador")`, então abra `GET /accounts/sessions/`.

## Estados visuais ainda pendentes

A matriz automatizada cobre as larguras de 320 px e desktop, temas claro/escuro, foco após erros, QR, lista de oito códigos, formulário de convite, link de redefinição válido/inválido, sessão atual, sessão remota ativa, sessão encerrada e erro de reautenticação. A revisão visual por amostragem das capturas confirmou a composição da matrícula MFA, da redefinição inválida e das sessões; a matriz automatizada verificou os nove estados. O fluxo de copiar a chave também foi validado em Chromium tanto com permissão concedida quanto com permissão negada; o resultado sintético está em `docs/migration/evidence/visual-auth/clipboard-result.json` e não registra o segredo. A validação visual cruzada dos demais consumidores de componentes e o escopo posterior de `DURALUX.prd` S08.08 permanecem separados desta entrega.
