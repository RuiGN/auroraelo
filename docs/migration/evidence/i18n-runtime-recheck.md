# Local i18n runtime correction — 2026-09-09

Branch `codex/duralux-migration`, base HEAD `fe3e5e9`, uncommitted correction.
No production change, commit/push, password reset, authored-data translation or
operational data transfer was performed. This is **not final migration acceptance**.

## Reproduction and root cause

The actual Compose web container used `config.settings.development` importing the
base allowlist containing only pt-br. A GET to `/accounts/login/` with
`Accept-Language: en` returned pt-br and offered only the pt-br option. The earlier
reports confused catalog presence and overridden test/preview settings with actual
runtime availability. The earlier conclusion that S14 was complete is withdrawn.

`check_ui_catalogs.py --scope docs/migration/translated-ui-scope.json` returned
1,250 keys and `publication_acceptance: false`. Its allowlist covers marked messages
in 100 templates and 26 Python files. Counterexamples in `../i18n-recheck-audit.md`
prove omitted labels/errors/choices, notifications and actual localization gaps.

## Changes

- `config/settings/development.py`: offer pt-br/en/es only for local acceptance.
  Base/test/production remain restricted to pt-br until release criteria are met.
- `tests/test_runtime_language_publication.py`: isolated subprocess using the real
  development settings, not a LANGUAGES override. Exercises login rendering,
  negotiation, options, CSRF POST, safe next, cookie/reload and rejected French.
- `tests/test_language_preferences.py`: explicit environment-specific expectations;
  production restriction and existing authorization/persistence tests retained.
- `.dockerignore`: exclude `.env`, `.venv`, `.git`, local uploads, evidence and
  preview data before rebuilding. The prior image contained `/app/.env`; the new
  image does not. Old local images/cache were not pruned; do not redistribute them.
- `scripts/verify-runtime-languages.cjs`: real local Compose login/browser matrix.
- PRD, README, scope description and acceptance metadata corrected to separate
  local availability from whole-UI translation and human publication acceptance.

## Verification

| Check | Actual result | Evidence |
| --- | --- | --- |
| New regression before fix | 3 failures: only pt-br offered | `recheck-runtime-red.log` |
| New regression after fix | 3 passed; final formatting/helper adjustment rerun: 3 passed | `recheck-runtime-green.log` and terminal output |
| Complete PostgreSQL suite | 1,432 passed, 0 failures/errors/skips, 220.21s | `recheck-pytest.log`, `recheck-pytest.xml` |
| Coverage | 86.10134116646698%; unchanged 90% gate fails, exit 2 | `recheck-coverage.json`, `recheck-coverage-gate.log` |
| Ruff check / format | pass / 491 files | terminal output |
| Mypy | pass, 591 files | terminal output |
| Django check / migration drift | no issues / no changes detected | terminal output |
| Scoped catalogs | 1,250 marked keys, no missing/placeholder/stale Django MO entries in declared scope | `recheck-i18n-catalogs.json` |
| Local image rebuild | built, web recreated and healthy; database/cache volumes retained | `recheck-build.log` |
| Served artifact | languages pt-br/en/es, real EN/ES login translations, excluded paths absent; live/ready HTTP 200 | `recheck-runtime.json` |
| Chromium matrix | 18 passed, zero page/network errors | `recheck-browser.log`, `runtime-languages/results.json` |

Full-suite command (credentials below belong only to disposable localhost tests):

```bash
env -i PATH=/usr/bin:/bin DJANGO_SETTINGS_MODULE=config.settings.test \
  TEST_DATABASE=postgresql DB_NAME=mindcare DB_USER=mindcare \
  DB_PASSWORD=mindcare-test-only DB_HOST=127.0.0.1 DB_PORT=55439 \
  COVERAGE_FILE=.coverage.i18n-recheck .venv/bin/python -m pytest --reuse-db -q \
  --cov-report=json:docs/migration/evidence/recheck-coverage.json --cov-report= \
  --junitxml=docs/migration/evidence/recheck-pytest.xml
COVERAGE_FILE=.coverage.i18n-recheck .venv/bin/python -m coverage report \
  --fail-under=90 --format=total
```

Browser: `PLAYWRIGHT_MODULE` points to an installed Playwright package and optional
`CHROMIUM_PATH` to an installed Chromium executable; run
`node scripts/verify-runtime-languages.cjs`. It asserts pt-br/en/es ×
320/390/1440 × light/dark, POST/CSRF, cookies, path, focus, overflow and JS catalog.
Screenshots are recorded artifacts, not a claim of manual visual review. The
standard browser tool failed because the selected real-profile browser was not a
supported Chromium default; independent headless Chromium ran the actual checks.

Runtime fingerprints are in `recheck-file-hashes.json`. The suite completed before
minor test-only helper/format adjustments; the adjusted test was rerun successfully.
The production code did not change after the full suite or image build.

## Independent review

`../i18n-local-fix-review.md` approves the bounded local-availability correction
with no actionable findings. The reviewer inspected code and existing artifacts;
it did not rerun tests or certify full-domain translation, manual visual quality
or commercial publication. This approval does not close S14.05–S14.12 or C11.

## Remaining acceptance

S14.05–S14.12 are reopened, along with C11 and final homologation dependencies.
The targeted audit is not an exhaustive translation inventory. Complete the real
UI labels/messages, domain choices, formatting, recipient notifications, extraction
and dynamic consumers; run the full role/domain matrix and human terminology
review. Resolve coverage through behavioral tests, not a lowered threshold.

Local use: open http://localhost:8000/accounts/login/, select the globe, choose
English or Español and apply. Existing profile preference still wins over browser
negotiation; the language POST updates an authenticated profile using existing
session controls. MFA, permissions, clinical data and currency/time-zone contracts
were not changed by this availability correction.
