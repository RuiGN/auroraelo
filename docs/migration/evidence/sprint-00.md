# Sprint 0 evidence — 2026-09-08

Source commit: `453eab77867f6c199887946b11996a1a4558f4db`, clean `main` checkout.
Destination base: `f5e6f03709b170d4861bb113b4360c9aa904365f`; work is uncommitted
on `codex/duralux-migration`. Original source remains unchanged.

| Item | Evidence | Result |
| --- | --- | --- |
| S00.01 | `baseline.md`, Git inspection before/after import | Source clean; only destination PRD initially untracked |
| S00.02 | `backend-matrix.md`, `source-manifest.json` | 23 apps, 84 migrations, exhaustive tracked-file inventory |
| S00.03 | `routes-matrix.md`, `runtime-routes.json` | 182 resolver patterns mapped; transitive permissions still need per-flow audit |
| S00.04 | `templates-matrix.md` | 97 templates mapped, lexical context and includes; dynamic/context-processor behavior needs per-flow verification |
| S00.05 | `assets-matrix.md` | 77 reference HTMLs classified; 1059 reference assets inventoried |
| S00.06 | `templates-matrix.md`, routes | Visual references and broad audience mapped; full critical-journey walkthrough still pending |
| S00.07 | `source-pytest.xml`, `source-pytest.log`, `source-failures.json` | 1061 passed, 89 failed, 1 skipped; 426.22 seconds |
| S00.08 | `decisions.md`, dependency manifests | `config/` configuration, preserved app labels, Python 3.14.7/Django 6.1, clean install |

Relative references in this table are under `docs/migration/` or its `evidence/`
directory. S00.03/S00.04/S00.06 remain open for their verification gaps; inventory
coverage alone is not complete behavioral verification.

## Baseline execution

Executed the source `.venv/bin/python -m pytest --no-cov -p no:cacheprovider -q`
against a temporary tracked-file archive, with JUnit capture and a cleared environment:
`DJANGO_SETTINGS_MODULE=config.settings.test`, `SQLITE_NAME=:memory:`,
`PYTHONDONTWRITEBYTECODE=1`. No operational DB, credentials or uploads were imported.

87 failures raise `TemplateSyntaxError`, principally in shared navigation and journal
templates. Another expected HTTP 409 became 500, and one source-text assertion requires
an exact table class string. These are baseline failures, not passing contracts. Preserve
the JSON/XML for exact test IDs; do not replace the source result after fixing Mindcare.

## Independent review

The initial import review confirmed all 727 imported paths exist, deliberate configuration
differences are bounded, and no blocking introduced security/package defect was found.
The reviewer explicitly noted that incomplete matrix/flow evidence prevents declaring
Sprint 0 wholly complete. That limitation remains reflected in the checklist.
