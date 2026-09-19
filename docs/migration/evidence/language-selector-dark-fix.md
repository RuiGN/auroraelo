# Post-login language selector dark-mode fix

Date: 2026-09-09. Local branch `codex/duralux-migration`; changes uncommitted.

## Cause and bounded fix

The vendor theme forces `.form-select` to white text and transparent background
using `!important`, overriding the non-important header input background. Chromium
showed the closed control over a dark menu (not white-on-white), but both select and
native options lacked an opaque background. Native popup rendering varies by OS/browser.
The red check caught the transparent dark select. No claim of reproducing the exact
white popup on the user's browser is made.

`static/duralux/css/product-integration.css` now sets an opaque `#111827` background,
`#f8fafc` text and `#94a3b8` border for the shared dark language select and options.
The scoped selector exceeds vendor specificity; necessary `!important` declarations
are confined to this component. Vendor CSS and light-mode rules are unchanged.
`docs/migration/runtime-assets.md` has the new SHA-256 hash.

## Real verification

- Before fix: browser assertion failed because the dark select background was transparent.
  Evidence: `language-selector-contrast-red/results.json`.
- After fix: **36 post-login browser scenarios passed**, all combinations of
  vertical/detached workspace, 320/390/1440 px, pt-br/en/es, dark/light. Normal, focus,
  hover, labels and native option computed colors were checked, plus keyboard focus
  and selection without persisting a different account language.
- Minimum select text contrast: **11.34:1** overall; **16.96:1** in dark mode.
- Evidence: `language-selector-contrast/results.json` and bounded menu screenshots.
- Real login used the existing synthetic patient account; MFA was not disabled or
  bypassed. Session was logged out; no password or profile preference was changed.
- Focused PostgreSQL pytest: **36 passed** in 4.51s (`language-contrast-pytest.log`).
- `git diff --check` and JavaScript syntax check passed.
- Local web image rebuilt and healthy. The served CSS bytes match the source SHA-256
  `2c6cd7b28c264faaec6cefd45793230ad1e891b962900a0ef86385a2cae93920`.

The full backend suite was not rerun for this CSS-only runtime change. This bounded
contrast fix does not close S14.05–S14.12/C11 or claim whole-page WCAG conformance.
No commit, push, production deployment or database migration change was performed.
