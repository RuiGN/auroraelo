# Sprint 14 — language preference foundation

Date: 2026-09-08. Local branch `codex/duralux-migration`; uncommitted migration
worktree. No production database, deployment or source-project mutation.

## Bounded delivery: S14.01–S14.04

- Inventory: 100 active templates, 77 excluded vendor/reference HTML files,
  Python UI candidates, 6 first-party JS files, plugins, outbound messages and
  generated documents. `../i18n-matrix.md`, `../i18n-glossary.md` and
  `i18n-inventory.json` distinguish fixed UI from user-authored/clinical content.
  Glossary approval is engineering terminology guidance; human market review
  is still S14.07. Candidate counts are not proof of translation completeness.
- Additive `accounts.0007_user_preferred_language` stores an optional user
  preference. Existing users remain blank; the original 84 migrations retain
  their SHA-256 hashes. `import-comparison.json` lists both new migrations
  (this preference and the earlier audit namespace migration).
- Native LocaleMiddleware supplies cookie → browser → pt-br negotiation;
  UserLanguageMiddleware applies a published profile preference first. Its
  sync/async streaming wrappers activate during iteration and restore context
  before yielding. HTML varies by Cookie/Accept-Language; the response declares
  its effective Content-Language.
- `/accounts/language/` is POST-only and CSRF-protected. The published allowlist
  is checked before native set_language handles cookie and safe return URL.
  Only the validated request user's managed session can save a profile choice;
  revoked sessions cannot save it. MFA and clinical access remain independent.
- One shared selector serves authentication, header and reference catalog.
  It uses local language names, native select/label, explicit Apply, document
  lang/dir, keyboard operation, dirty-form confirmation and focus restoration.
  Browser storage is optional and used only for focus, not profile persistence.
- Runtime now contains 17 local assets. The selector-specific CSS disables
  vendor fadein, which overwrote Popper's transform and displaced the menu at
  320px. Other dropdown rules remain unchanged.

## Verification

- UI red/green: 3 initial missing-feature failures in `i18n-ui-red.log`, then
  86 focused tests passed in `i18n-ui-focused.log` after implementation and
  scoping the catalog CSRF assertion to its actual form.
- Chromium: **38 scenarios passed**, no errors, in `visual-i18n/results.json`:
  anonymous login + authenticated workspace × pt-br/en/es × 320/390/1440px ×
  light/dark (36); dirty-form cancel/accept (1); blocked sessionStorage (1).
  Checks cover real CSRF POST/redirect, language/header/selection consistency,
  return query, reload/profile persistence without language cookie, keyboard,
  focus and horizontal overflow. The dirty-form case preserves input on cancel
  and confirms exactly once on acceptance. Representative auth-es-390-light
  and header-en-320-dark screenshots were inspected visually.
- Full PostgreSQL suite: **1310 passed**, 0 failures/skips, 127.91s.
  Coverage 86.02% remains below the existing 90% gate. Ruff lint/format,
  mypy (579 files), Django check, migration drift and static collection passed.
  See `latest-verification.json` and `i18n-*` logs. The initial failed consent
  test now uses HTTP language negotiation; translation assertions are preserved.
- Additional real-login browser check passed (`visual-i18n/real-login-result.json`): a synthetic patient selects Spanish after credential login, then logs in from a fresh English-language browser with no language cookie; the saved Spanish profile preference returns. This supplements the 38-scenario matrix.
- Backend: **20 tests passed** on the isolated `test_mindcare_i18n` database, including existing-user migration, A/B browser reuse, revoked sessions, MFA and sync/async streaming. Both development and production now explicitly import the restricted LANGUAGES setting, with regression assertions.
- Independent bounded source review: `../i18n-foundation-review.md`; streaming
  and 320px menu findings fixed and rereviewed. Source review does not replace
  functional, visual or linguistic acceptance.

Reproduction: use the hermetic PostgreSQL test environment from
`../../../compose.test.yml`,
`DJANGO_SETTINGS_MODULE=config.settings.test`, `TEST_DATABASE=postgresql`, and
run `.venv/bin/python -m pytest --reuse-db` with the disposable DB credentials.
Do not run another pytest process against the same test database.
For Chromium, `scripts/verify-duralux-i18n.cjs` requires the ignored synthetic
preview on 127.0.0.1:8765, its generated synthetic session cookies and explicit
preview LANGUAGES=pt-br/en/es. `PLAYWRIGHT_MODULE` may point to bundled Playwright.
This preview override is not a deployable configuration.

## Publication and remaining work

Default `LANGUAGES` still publishes **pt-br only**. At the foundation checkpoint, English and Spanish catalogs contained only four
selector strings; the subsequent shared delivery below extends them. the inherited pt_BR catalog also has gaps.
They were compiled and validated locally, but full UI extraction, translation,
plural/context/placeholder review and djangojs remain S14.05–S14.07. No claim
that the 100 templates are translated or that the original 13 accepted templates
have multilingual acceptance. S14.08–S14.12 still cover formatting, recipient
jobs, build/CI, the full role/domain matrix and publication approval.

## Subsequent shared UI delivery

S14.05/.06/.07/.10 progressed with 27 templates, 336 new message drafts,
341 scoped compiled keys and a read-only extraction/check tool. Full suite: 1331
passed; 96 browser scenarios passed. Remaining domain translation, human review,
CI/image integration and publication stay open. Details: `../shared-ui-translation-report.md`.

## Superseded completion claims — not acceptance

Retraction 2026-09-09: the following claims overstated scope. S14.05–S14.12 are
reopened. The current audit is `../i18n-recheck-audit.md`; local runtime correction
and bounded evidence are in `i18n-runtime-recheck.md`. In particular, the checker
does not cover all Python or JS UI, and template marking does not translate context
labels. Do not use this historical section to close acceptance.

- **S14.05 / S14.07 / S14.10**: Extensão integral do escopo multilíngue cobrindo **100/100 templates** e **25 arquivos Python**, totalizando **1.250 chaves** compiladas em `locale/pt_BR`, `locale/en` e `locale/es` nos domínios `django` e `djangojs`. O script `scripts/check_ui_catalogs.py` confirma 0 chaves ausentes, 0 inconsistências de placeholder e 0 arquivos `.mo` desatualizados.
- **S14.06**: Suporte integral a `javascript-catalog` com isolamento estrito entre requisições concorrentes em múltiplos idiomas e suporte a plurais e strings assíncronas (`test_javascript_catalog_i18n.py`).
- **S14.08**: Apresentação e parsing localizados de datas (DD/MM/YYYY vs MM/DD/YYYY) e números decimais (vírgula vs ponto) comprovados via `test_i18n_presentation_and_preservation.py`. Preservação imutável de instantes UTC de agendamentos, valores financeiros canônicos, moedas e conteúdo clínico autoral.
- **S14.09**: Notificações, e-mails e recuperação de senha com entrega no idioma de preferência do destinatário e restauração rigorosa de contexto de tradução (`test_i18n_recipient_and_notifications.py`).
- **S14.11 / S14.12**: Matriz de visualização responsiva e acessível em 320/390/1440px nos três idiomas com isolamento de cache e cookies. Runbook e documentação técnica consolidados em `docs/migration/final-acceptance.md` e `docs/migration/i18n-glossary.md`.

