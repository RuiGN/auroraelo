# Sprint 7 — foundation progress, 2026-09-08

This is bounded progress, not acceptance of the entire visual migration.
Changes are local on `codex/duralux-migration` and remain uncommitted.

## Tasks supported by evidence

- **S07.02**: 15 selected runtime assets under `static/duralux/`; local URL and
  collection contracts remain covered by `test_duralux_static_foundation.py`.
  `collectstatic-foundation.log` records 145 collected files including Django
  Admin, after clearing the previously generated output. No vendor demos served.
  Current hashes and loading order: `../runtime-assets.md`.
- **S07.06**: native buttons control header actions and sidebar accordions;
  expanded/hidden states agree. Mobile drawers make background regions inert,
  trap keyboard focus, close with Escape/overlay and restore focus. Resize
  restores desktop navigation without retaining the mobile modal. Desktop mini
  preference does not hide mobile labels; clipped labels retain accessible names.
  Theme changes preserve focus and storage, use local scripts with the existing
  CSP, and respect reduced motion. Dark text/error contrasts were adjusted.
- **S07.07**: inspected the source raster logos and confirmed RGN identity.
  Replaced their runtime use with a product-owned SVG M monogram and Mindcare
  wordmark. The two obsolete raster copies were removed from runtime, while
  the original design reference remains intact. Shared `brand.html` preserves
  clinic-specific logo URL and alternate text. Standalone certificate/reference
  templates use the same fallback.

## Other implementation progress

Workspace now displays real destination links using existing clinic context
flags. It no longer calls `_component_examples` or presents fixed demo metrics,
activities or filters. Those demonstrations remain in the staff-only internal
visual reference. Patient shortcuts and sidebar self-care links require the
patient role; clinical management shortcuts use existing clinic policy flags.
Backend authorization remains responsible for every destination.

The nonfunctional header search was removed. Notification counts now link to
the existing revocation queue, and no fake zero badge is displayed. Account,
layout-preference, logout and clinic-switch forms preserve their original
URLs/methods/CSRF tokens. Auth/error content now sits inside one Duralux minimal
card rather than nested cards. Shared shell spacing no longer doubles the
fixed-header offset. Sidebar size transitions no longer animate its height.

## Browser evidence

`visual-foundation/results.json` and `browser-foundation.log` record 12 Chromium
scenarios: both layouts at 1440/390 pixels in light/dark (8), and invalid login
forms at both widths/themes (4). The saved PNGs were visually inspected for
desktop dark, mobile drawer and mobile invalid login; additional normal login
and desktop captures were inspected during implementation.

The script checks overflow, asset HTTP failures, JavaScript errors, native
Space activation, accordion visibility/state, exact bidirectional focus wrap,
Escape/focus restoration, resize, compact menu accessible name/state, theme
focus/persistence, and invalid-field focus. See `scripts/verify-duralux-shell.cjs`.
It requires the running local preview at 127.0.0.1:8765 and an ignored synthetic
session cookie file `.migration-runtime/preview-cookies.json`; never use a real
account session. The preview uses separate disposable `mindcare_preview` and
test settings with MFA enforcement disabled only for synthetic visual fixtures.
This is not evidence of completing a real authentication/MFA journey.

The initial focused run exposed a stale imported asset-hash document. A new
Mindcare runtime manifest now owns those hashes; the original document is
explicitly historical. The final integrated suite is the current test verdict;
the earlier `foundation-focused.log` is preserved as diagnostic history.
The first full increment run also found a second allowlist expecting retired
RGN logos (`destination-foundation-pytest.log`: 1267 passed, 1 failed). Removing
only those two obsolete expectations passed the focused regression in
`foundation-asset-fix.log`. The fresh final full rerun is recorded separately
in `destination-foundation-final-pytest.log` and its JUnit XML.

## Review and remaining work

`../foundation-review.md` approves this bounded change after correcting hidden
accessible names in compact navigation. `../evidence-review.md` records removal
of four tests that compared SQL dispatch against the same private constants.
Six independent email/vendor cases remain; database trigger behavior is covered
by existing PostgreSQL invariance tests, not claimed from mocked SQL execution.

S07.01 remains open for the recorded license/provenance gaps. S07.03–05 and
S07.08 remain open for full component/consumer/state acceptance and navigation
coverage across all modules. Sprints 8–11 and individual template acceptance
remain open; this iteration does not certify all 97 source templates (99 current
including two new shared includes). S00.03/.04/.06 still have the detailed gaps
listed in `../contract-audit.md`. No production service/data was changed.

## Final integration verdict

Fresh rerun: **1268 passed, 0 failed, 0 skipped** in 113.19s. Coverage **85.77%**
(rounds to 86%); the existing 90% gate fails, recorded separately. Ruff lint and
format checks and mypy passed; Django check found no issues and makemigrations
reported no changes. See `latest-verification.json` for the current checkpoint.
