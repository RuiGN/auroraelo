# Migration decisions

## 2026-09-08 — Import boundary

Source: `453eab77867f6c199887946b11996a1a4558f4db`; destination base:
`f5e6f03709b170d4861bb113b4360c9aa904365f`.
Work occurs in the user's destination checkout on `codex/duralux-migration`.
The source is unchanged. A tracked-file snapshot in a temporary directory supplies
the baseline tests; no source `.env`, database, upload, cache or virtualenv was copied.
The source interpreter is used read-only for that snapshot, with a cleared environment.

## Package collision

Keep source `config/` for settings, URLs, ASGI and WSGI; replace the initial destination
configuration package `core/` with the source shared app. The original scaffold remains
recoverable in the destination base commit. Preserve labels, migration files and
`accounts.User`. No schema rewriting or migration squashing is authorized by this choice.

## Dependency baseline

Use Python 3.14.7 and source-pinned Django 6.1 initially. The destination had Django
6.1.1 declared; its adoption is deferred until baseline equivalence is established.
Install dependencies in the destination `.venv`, rather than copying environments.
Coverage now includes goals and all six additional domain apps absent from the
source coverage list. This can change aggregate coverage without changing behavior.

## Templates and historical evidence

Import the 97 source templates and their 17 runtime assets as a transitional runnable
baseline. They already use Duralux conventions but require fresh reconstruction/review
against the local reference and Mindcare identity. No visual acceptance checkbox is
completed by copying files. Historical source specs and documentation retain provenance;
they are not evidence for Mindcare. Old screenshots/log directories were excluded.
Backend regulatory traceability still references the historical product PRD identifiers.

## Deployment isolation

Remove source production domains from default CSRF trust. Only the deployment's explicit
environment may grant cross-origin trust. Use independent example hosts and service
names; cache namespace is `mindcare`. `compose.test.yml` has localhost-only ports
55439/56389 and disposable tmpfs storage. No production service is touched.

## Data and external services

Deliver a clean installation. No operational record, secret, encryption key, e-mail,
WhatsApp message or payment is transferred/dispatched. Integration verification uses
existing test adapters. Real-provider activation and any production data transfer require
separate configuration and authorization.

## Documentation consulted

- Django 6.1 application labels and migrations: https://docs.djangoproject.com/en/6.1/ref/applications/
- Custom user model: https://docs.djangoproject.com/en/6.1/topics/auth/customizing/
- Docker Compose service configuration: https://docs.docker.com/reference/compose-file/services/

Documentation retrieved through Context7 on 2026-09-08.

## Corrective changes exposed by baseline tests

The source SQLite suite finished with 1061 passed, 89 failed and 1 skipped. Repaired
multiline Django tags and missing comparison whitespace in six destination templates;
all original conditions and variables remain unchanged. Added compiler/render regressions.

PostgreSQL then exposed 38 failures caused by existing audit action names exceeding
the original 32-character column (observed literals up to 47). Added migration
`audit.0005_expand_action_namespace` to expand capacity to 128 without shortening
actions or altering audit hashes. All original 84 migrations remain unchanged.

Converted theme links to keyboard-native buttons with the accessible toggle label;
the chart test now requires semantic class tokens rather than exact class ordering.
Independent review approved these bounded changes.

Final full PostgreSQL suite: 1253 passed and 86% coverage. Keep the existing 90% CI
coverage gate; do not lower it to declare completion. The 39 inherited Python formatting
differences were normalized and verified to preserve the AST exactly.

## 2026-09-08 — Mindcare visual foundation

Use the approved local Duralux minimal authentication and shared dashboard
structure, preserving Django context/CSRF behavior. The RGN raster logos were
visually inspected and removed from runtime; use a small product-owned M SVG
and Mindcare wordmark as fallback while retaining configured clinic logos.
`docs/migration/runtime-assets.md` now owns current asset hashes.

Operational workspace must not present synthetic component metrics as facts.
Keep examples in the staff-only reference and present role-scoped destination
cards using existing context processor flags. Do not introduce a second
authorization policy in the UI; destination views retain their existing checks.

Use native button controls, synchronized ARIA/hidden states, inert background
regions and focus restoration for the drawer. Desktop mini state must not
collapse labels on mobile or remove accessible names. Preserve both theme
preferences and existing layout preference endpoints.

Context7 references consulted for this increment: Django 6.1 template inclusion/
authentication context and static collection/finder behavior:
https://docs.djangoproject.com/en/6.1/ref/templates/builtins/
https://docs.djangoproject.com/en/6.1/topics/auth/default/
https://docs.djangoproject.com/en/6.1/ref/contrib/staticfiles/

## 2026-09-08 — Shared components and account presentation

Keep configured Django widget subclasses and explicit formats. Only stock widgets
receive structural Duralux adaptation; hidden fields retain hidden semantics.
The `include ... only` catalog form receives `csrf_token` explicitly, verified by
an enforced-CSRF POST. Restore initial disabled state after browser history and
focus a native invalid field or the general-error summary as appropriate.

Mobile table cards present each datum once and retain active/current/next ordering.
Use label hit areas for checkbox/radio accessibility rather than stretching the
control. Account entry/MFA templates follow the local minimal references, retaining
local QR, manual enrollment, recovery codes, no-store responses and existing routes.
Session errors use the same accessible renderer; generic messages use a neutral icon.

Identity evidence adds an unused expired TOTP followed by a valid current TOTP,
and a technical superuser without clinical membership. Existing policies remain
unchanged. Test randomness is scoped to enrollment only, preserving unique recovery
codes. Context7 documentation consulted for widget rendering and restricted includes:
https://docs.djangoproject.com/en/6.1/topics/forms/
https://docs.djangoproject.com/en/6.1/ref/forms/api/
https://docs.djangoproject.com/en/6.1/ref/templates/builtins/

## 2026-09-08 — Planned multilingual UI scope

User requested persistent language choice and international UI in DURALUX.prd.
Version 1.1 adds S14.01–S14.12 (all pending), initial pt-br/en/es, and proposed
pt/fr/de expansion. Execute the foundation before remaining template work and
complete it before Sprints 11–13; keep existing task IDs and accepted Portuguese
visual evidence intact. Use reviewed Django catalogs, profile/cookie preference,
and a mobile/auth selector. Clinical content, currency, timezone and authorization
remain independent. This increment changes planning only, not runtime or test results.
