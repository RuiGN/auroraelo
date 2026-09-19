# Globe selector inside the login card — 2026-09-09

The user superseded the flag-only choice and requested the login selector at the
upper right inside the card. Changes remain local and uncommitted.

## Delivered scope

- Shared selector: decorative Feather globe + visible PT-BR/EN/ES code, including
  mobile. Accessible name retains the full local language name; dropdown retains
  textual options. No locale, CSRF, persistence, permissions or session changes.
- Authentication base: selector moved into a right-aligned toolbar in card-body,
  before the brand and outside the login form. Bootstrap padding/layout reused;
  no absolute positioning or overlaps. Shared reset/MFA shells inherit the move.
- Flag-only CSS removed; prior opaque dark select/option correction retained.
  Three old SVGs remain archived in static but have no selector consumer.
- Browser probes updated for globe/code instead of flags; old evidence retained.

## Verification (current code, not historical migration acceptance)

- RED→GREEN: three globe/code cases fail against flags, then pass.
  `globe-toggle-red.log`, `globe-toggle-green.log`.
- Browser RED: actual served page rejects the selector outside the login card
  (`globe-card-red/results.json`).
- Browser GREEN: **18 unique cases**, pt-br/en/es × 320/390/1440 × light/dark;
  `globe-card/results.json`. Tests actual local Compose, DOM containment and
  upper-right placement, brand/emblem non-overlap, 44px target, keyboard,
  safe POST/CSRF, focus restoration, cookie/reload, route preservation, menu bounds,
  zero page errors/failed responses and localized JavaScriptCatalog.
- At mobile widths the control has 25px top/right inset, with its right edge
  exactly aligned to the email input. Dark text is white on #0f172a. Closed desktop
  and mobile screenshots inspected; geometry resolves any ambiguous image inference.
- Focused suite: **156 passed**, 9.59s (`globe-card-focused.log`).
- Full PostgreSQL suite: **1435 passed**, 0 failures/errors/skips, 366.96s
  (`globe-card-suite.xml`, `globe-card-suite.log`). Coverage remains **86.10%**;
  unchanged 90% gate fails with exit 2 (`globe-card-coverage-gate.log`).
- Ruff check/format on changed test file, JS syntax, mypy (591 files), Django check
  and migration drift checks passed. Scoped catalogs: 1,250 marked keys pass
  (`globe-card/catalogs.json`); not complete translation or editorial approval.
- Local web image rebuilt, healthy, no pending migrations. Served CSS SHA-256
  matches source: 2c6cd7b28c264faaec6cefd45793230ad1e891b962900a0ef86385a2cae93920.
  Fingerprints: `globe-card/hashes.json`; build output: `globe-card-build.log`.

A first browser attempt preceded Gunicorn readiness and failed with connection
reset (`globe-card/startup-not-ready.json`); the later run passed after health was
confirmed. A premature process notification returned no exit code while pytest
was still running; no duplicate suite was started. Acceptance uses the completed
JUnit/log, not that notification. Early coverage attempt had no data and is retained
as `globe-card-coverage-before-suite-end.log`.

No production deployment, commit, push, data transfer or account changes.
The full post-login contrast browser script was updated but not rerun in this
increment. Previous translation/coverage release gaps remain open.
