# Sprint 1 evidence — 2026-09-08

Work branch: `codex/duralux-migration`, uncommitted changes against `f5e6f03`.
Source snapshot: `453eab7`. This is backend import evidence, not visual acceptance.

- S01.01: `manage.py` uses `config.settings.development`; `config/` contains settings,
  URLconf and entry points. Source shared `core/` replaces the original scaffold;
  original files remain recoverable from the destination base commit.
- S01.02: `import-manifest.json` records 727 imported files. All 84 migration hashes
  match the source. All 23 own applications load. No source `.env`, DB, upload,
  `.git` or `.venv` was copied.
- S01.03: fresh destination dependency installation completed; `pip check` reports
  no broken requirements. Python 3.14.7 / Django 6.1 match the source baseline.
- S01.04: `destination-check.log` reports no Django issues. The resolver loads
  182 URL patterns (`runtime-routes.json`); `migration-drift.log` says no changes detected.
- S01.05: example variables and CI database names use Mindcare, local-only services
  have distinct ports, cache namespace is independent, `.gitignore` excludes generated
  state and environment secrets. Production trusts no source CSRF domains implicitly.
- S01.06: all source tests, factories, scripts, localization and configuration imported.
  Coverage includes all domain apps; historical source docs are explicitly labeled.
- S01.07: initial collection found 1153 tests (1151 source plus 2 new isolation cases).
  Subsequent template regression cases add 99 tests. Full suite results are tracked
  separately and are not implied by successful collection.

## Configuration regression

`configuration-red.log`: one failure and one pass before removing inherited CSRF origins.
`configuration-isolation-green.log`: 2 passed after the fix. `configuration-green.log`:
23 passed, 2 warnings for configuration, smoke and security tests (287.35 seconds).

## Static gates

- `ruff-check.log`: passed.
- `mypy.log`: no issues in 561 source files at initial import check; final check
  covers 563 files (`mypy-final.log`).
- `ruff-format.log`: initially found 39 inherited formatting differences. These were
  formatted after the complete PostgreSQL suite; `formatting-verification.json`
  confirms unchanged Python AST in every file. `ruff-format-final.log` records
  the final formatting gate; source-level contracts are rechecked separately.
- `secrets-scan.log`: secret scan passed at the recorded check.
- `regulatory-matrix.log`: matrix complete, regulated release blocked. This historical
  governance status does not authorize a production release.

## Corrective template work

Source baseline exposed broken multi-line Django tags. A focused parser/render test
first recorded 4 failures and 95 passes (`templates-red.log`). Correcting tag whitespace
and comparison token spacing in six templates produced 99 passes (`templates-green.log`).
No business condition or permission was removed. Independent review found no accidental
changes. This repairs the transitional baseline; it does not close visual sprints.

The initial destination full SQLite run was interrupted deliberately before template
edits and is not a passing result (`destination-interrupted.md`). A complete PostgreSQL
run follows the correction and has its own log/XML.

Final complete PostgreSQL result: **1253 passed**, 213 warnings, coverage **86%**
(`destination-final-pytest.log`/XML). This is below the unchanged CI gate of 90%.
The gate remains open; no full-release acceptance is claimed.
