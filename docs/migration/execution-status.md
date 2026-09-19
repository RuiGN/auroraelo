# Execution checkpoint — 2026-09-09

Branch: `codex/duralux-migration`. Changes remain local and uncommitted.
Authoritative checklist: `../../DURALUX.prd`. No production action was performed.

## Latest presentation adjustment — globe and login card

The user superseded flag-only selection with a globe + visible language code.
Login selection is now inside the card at the upper right. Eighteen current-runtime
Chromium scenarios verify placement, no branding overlap, keyboard/POST/CSRF,
focus restoration, three languages and both themes at 320/390/1440px.
Evidence: `evidence/language-globe-card.md`. No multilingual release gates closed.

## Current correction — local language availability, not final acceptance

- Development now offers pt-br/en/es; base/test/production retain pt-br by default.
- Actual-runtime login selector: 18 Chromium scenarios passed (three languages,
  320/390/1440 px, light/dark), including real POST/CSRF, cookie persistence,
  return URL, focus, overflow and JavaScriptCatalog. This is not a four-role,
  all-domain visual acceptance matrix.
- Full PostgreSQL suite: 1,432 passed, 0 failures/skips, 220.21s.
- Branch-aware coverage: 86.10134116646698%; the unchanged 90% gate fails.
- Ruff lint/format (491 files), mypy (591 files), Django check and migration drift pass.
- Declared catalog scope: 100 templates + 26 Python files, 1,250 marked keys pass.
  Omitted/unmarked domain text remains untranslated; see `i18n-recheck-audit.md`.
- `.dockerignore` prevents `.env`, virtualenv and local data from entering the new
  image. Existing volumes were retained; production was not changed.
- S14.05–S14.12 and final multilingual acceptance are reopened in `DURALUX.prd`.
- Evidence: `evidence/i18n-runtime-recheck.md`, `evidence/recheck-pytest.xml`,
  `evidence/recheck-coverage-gate.log`, `evidence/runtime-languages/results.json`.
- This correction remains uncommitted. Earlier migration commits are preserved.

The following checkpoints are historical, not current completion or language
publication claims. Their numerical/template claims require their bounded evidence.

## Previous clinical journey & scheduling delivery (Sprint 4 & Sprint 9)

- 31 domain templates and their Python presentation layers reconstructed and validated with the Duralux design system:
  - Therapist Dashboard (S09.01): `templates/therapist_dashboard/home.html` + `static/duralux/js/dashboard-charts.js`
  - Journal & Check-ins (S09.02): 7 templates (`list.html`, `detail.html`, `form.html`, `checkin_list.html`, `checkin_today.html`, `checkin_unavailable.html`, `partials/calendar.html`)
  - Goals & Exercises (S09.03): 10 templates (`list.html`, `detail.html`, `form.html`, `low_energy.html`, `exercise_catalog.html`, `exercise_form.html`, `exercise_assign.html`, `exercise_execute.html`, `exercise_execution_detail.html`, `patient_exercises.html`)
  - Scheduling & Messaging (S09.04, S09.05, S09.06): 13 templates (`appointment_calendar.html`, `appointment_list.html`, `appointment_request.html`, `appointment_reschedule.html`, `unit_list.html`, `unit_form.html`, `room_form.html`, `reminder_preferences.html`, `waitlist_list.html`, `waitlist_form.html`, `conversation_list.html`, `conversation_create.html`, `conversation_detail.html`)
- All 31 templates use semantic Bootstrap 5/Duralux markup, zero inline styles, no legacy CSS tokens, and complete `{% load i18n %}` translations.
- Duralux regression contracts verified: `test_template_compilation.py` (107/107 templates compile) and `test_duralux_domain_templates.py` pass cleanly.
- Full clinical domain test suite verified: 106 tests passed across `test_goals.py`, `test_low_energy.py`, `test_exercises.py`, `test_journal.py`, `test_checkin.py`, `test_scheduling.py`, `test_waitlist.py`, `test_availability.py`, and `test_therapist_dashboard.py`.
- Zero migration drift (`makemigrations --check` passed: no changes detected).
- Ruff check and mypy pass with 0 errors across `scheduling`, `journal`, `goals`, `therapist_dashboard`.
- **51/112 top-level task IDs checked**. **74/100 templates reconstructed and verified**.
- Next focus: Sprint 10 (Content, Learning, Reports, and Finance - 23 templates).

## Previous continuation delivery (Clinics, Onboarding, People, Consents)

- 15 domain templates and their Python services/forms/selectors delivered and translated across pt-br/en/es:
  - Clinics & Onboarding (S08.03): 5 templates
  - People & Directory (S08.04): 4 templates
  - Consents & Revocations (S08.05): 6 templates
- Fixed navigation pending revocation badge pluralization in `layouts/partials/navigation.html`.
- Cumulative scope: **42 templates and 25 Python files**, with **639 required catalog keys**; 0 missing, 0 placeholder errors, 0 stale `.mo` files (`evidence/continuation-catalog-check.json`).
- Browser scenarios: 249 clinic/onboarding + 90 people + 37 consents scenarios passed across viewports, themes and roles.
- Full suite: **1397 passed**, 1 skipped, 0 failed in 254.89s. Coverage **86.12%** (`evidence/continuation-pytest.log`).
- Evidence: `continuation-report.md`, `evidence/latest-verification.json`.
- **39/112 top-level task IDs checked**. **29/100 templates have verified visual & functional acceptance**.
- Next focus: Sprint 9 (Therapist dashboard, Scheduling, Journal, and Goals).

## Previous shared UI delivery

- 27 templates and their Python presentation copy translated in pt-br/en/es: navigation, workspace, accounts/MFA/sessions, shared components, errors and reference.
- 336 new message drafts; 341 extracted keys including selector/plural forms validated, with no missing entries, mismatched parameters or stale compiled files in this scope.
- 96 browser scenarios passed across the three languages, responsive widths, themes, account flows, dynamic messages and real MFA recovery-code generation.
- Full suite: **1331 passed**, 0 failed/skipped, 163.097s. Coverage **86.03%**; the 90% gate still fails. Ruff477, mypy583, Django check, migration drift and static collection passed.
- Evidence: `shared-ui-translation-report.md`, `evidence/destination-shared-ui-final-pytest.xml`, `evidence/shared-ui-catalog-check.json`, `evidence/visual-shared-translations/`. Current metadata: `evidence/latest-verification.json`.
- **36/112 top-level task IDs remain checked**; newly completed subitems under S14.05/.06/.10 do not imply complete domain translation. Remaining 73 templates/domain Python/JS, outbound messages, native-language review and image/CI integration remain pending. Only pt-br is published.

## Previous delivered foundation

- 23 source applications and 727 imported paths reconciled. The original 84 app
  migrations remain byte-identical; additive migrations are audit.0005 and
  accounts.0007. No operational data transferred or source-project mutation.
- Previous foundation includes Mindcare branding, clinic logos, role-aware
  navigation, shared components, authentication/MFA and Sprint 3 backend checks.
- S14.01–S14.04 now add an inventory of 100 templates and other UI text sources,
  an engineering glossary, optional profile preference, safe HTTP language
  selection and a shared accessible selector. Login, header and catalog use it.
- Profile → cookie → browser → pt-br selection preserves clinical access/MFA.
  All four settings modules publish pt-br only. At that checkpoint, English/Spanish contained four selector strings each; the newer shared delivery above extends the catalogs. They remain test/preview-only.
- Runtime has 17 local assets; static collection has 147 files including Admin.
- **36/112 task IDs checked**. **14/100 templates have bounded visual acceptance**:
  the previous 13 plus the language selector. This is not full multilingual
  acceptance; original 13 require the later three-language domain matrix.

## Previous foundation verification (historical)

- **1310 passed, 0 failed, 0 skipped**, 127.91s, PostgreSQL:
  `evidence/destination-i18n-final-pytest.log` and matching JUnit XML.
- **39 browser scenarios passed**: 38 language-selector matrix/behavior scenarios
  plus actual credential login and profile restoration on a new English browser
  without language cookie. Evidence: `evidence/visual-i18n/`.
- 86 focused UI/static tests and 20 isolated backend tests passed. The backend
  report is `language-backend-report.md`; the full suite includes their cases.
- Ruff lint/format (473 files), mypy (579 source files), Django database check,
  migration drift, secret scan and regulatory matrix structural check passed.
  The regulatory checker still reports regulated release blocked.
- Coverage **86.02%**; the existing **90% gate remains unmet**. No gate was
  relaxed. See `evidence/i18n-coverage-gate.log` and `i18n-coverage.json`.
- Local compiled catalogs match checked PO sources, but are partial; this is
  not image/build or publication proof. `evidence/i18n-catalog-check.json`.
- Independent review: `i18n-foundation-review.md`. Full details and limitations:
  `evidence/sprint-14.md`; runtime fingerprints: `evidence/i18n-file-hashes.json`.

An early full run terminated with exit 143 before completion and is not acceptance
proof. The next run had 1309 passes and one legacy consent-test failure: ambient
translation.override no longer selected a request language after LocaleMiddleware.
The test now uses allowlisted HTTP negotiation and retains all translation
assertions; its focused rerun and the final complete suite passed. Earlier
1286-test / 57-browser results remain historical component/authentication evidence.

## Resume here

1. Complete domain UI translation using the concrete gaps in `i18n-recheck-audit.md`:
   Python labels/errors/choices, actual form localization and recipient notifications.
2. Expand extraction/gates beyond the declared allowlist and cover real dynamic UI.
3. Run the four-role/domain multilingual matrix and human terminology review;
   keep production EN/ES unpublished until those criteria are met.
4. Reach the unchanged 90% coverage gate with meaningful behavioral tests.
5. Reconcile the remaining acceptance items before claiming migration complete.
   Do not commit, push, deploy or transfer operational data without authorization.

Local Compose is already running at http://localhost:8000 with draft pt-br/en/es.
Use the globe selector → English / Español → Apply language. The older synthetic
preview described below is a separate environment and is not required for this UI.

## Local environments

`compose.test.yml` PostgreSQL/Redis are loopback-only with tmpfs storage.
`mindcare`/`test_mindcare` is the root integration pair; never run concurrent pytest
against that pair. Language backend validation used `mindcare_i18n`/
`test_mindcare_i18n`. Synthetic browser preview uses `mindcare_preview` on
127.0.0.1:8765; ignored launcher/settings/cookies live in `.migration-runtime/`.
The preview alone enables three languages and disables MFA; backend tests enforce
actual MFA separately. Browser scripts accept `PLAYWRIGHT_MODULE`. Fixtures,
passwords and sessions are synthetic and disposable, never operational backups.

The synthetic browser server was stopped after validation; its ignored launcher
and disposable fixtures remain available for a later review session.
