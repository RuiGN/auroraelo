# Mindcare migration baseline — 2026-09-08

## Source and destination

Source checkout: `../projetomnunes`, clean at
`453eab77867f6c199887946b11996a1a4558f4db`.
Destination initial commit: `f5e6f03709b170d4861bb113b4360c9aa904365f`, branch `main`;
only `DURALUX.prd` was untracked before execution. Current work branch:
`codex/duralux-migration`. No commit or push has been performed during execution.

The original source configuration uses `config/` and registers 23 own applications.
The destination's initial `core/` configuration has been replaced by that structure.

## Static inventory

- 23 own registered apps, 84 migration files excluding package initializers.
- 114 source test modules; test-case counts are measured separately.
- 97 source application templates and 77 local Duralux reference HTML files.
- 17 source runtime assets; the complete reference bundle remains separate.
- Source Python 3.14.7 / Django 6.1. Destination started with Python 3.14.7 / Django
  6.1.1 and now follows the source dependency baseline.
- 727 tracked source files imported initially; SHA-256 recorded in
  `evidence/import-manifest.json`. Later intentional differences are reported separately.

## Validation boundary

The baseline suite runs on a temporary `git archive` of the source commit with test
settings and in-memory SQLite. `env -i` prevents inheriting database/provider credentials;
bytecode/cache/coverage writes to the original checkout are disabled. The source virtualenv
is only used as the executable, never copied. Logs are captured under `evidence/`.

`config.settings.test` selects SQLite by default. A distinct `mindcare-test` Compose
project supplies PostgreSQL for schema and database-specific tests.

Results are recorded in `evidence/sprint-00.md` and `evidence/sprint-01.md` only after
process completion. An ongoing process, old source documentation or collection alone
does not establish a passing suite.
