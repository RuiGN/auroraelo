# Authenticated customizer — login isolation

Date: 2026-09-09 19:46 UTC
Scope: confirm the Duralux theme customizer stays out of the login shell.
Worktree: `/mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/mindcare/.git/worktrees/duralux-fidelity-index`

## What was changed

Cut 2 of the Duralux fidelity migration added:

- `templates/components/theme_customizer.html` — partial mirroring the original Duralux
  panel with three option groups (Navigation / Header / Skin), reset and content actions,
  and triggers that never use inline `javascript:` URLs.
- `static/duralux/js/theme-customizer.js` — vanilla JS controller, no jQuery, no CDN.
  Persists under the dedicated `mindcare:duralux-theme` key and never writes to the
  product theme attribute `data-bs-theme` (managed by `product-shell.js`).
- `templates/layouts/base.html` — includes the partial inside authenticated shells
  only. `auth_base.html` does not include it, so the login form keeps its focus.
- `templates/layouts/partials/header.html` — added the `feather-settings` trigger
  wired to `data-customizer-trigger`.
- `static/duralux/css/product-integration.css` — customizer layout, sidebar animation,
  open/close transitions, per-target fidelity overrides (only active when the user
  or `localStorage` flips a `data-duralux-*` attribute).

## Verification

`./scripts/verify-customizer-login-isolation.cjs` confirms the customizer triggers and
container never appear in the login page (CSP-compatible marker check). The captured
screenshot in this folder shows the login shell without any customizer UI.

```text
Customizer absent from login shell (correctly).
```

Browser matrix:

| Viewport | Theme | Customizer visible? | Expected |
|----------|-------|--------------------|----------|
| 1440 × 900 | light | false (login uses `auth_base.html`) | pass |

## Pytest contract

`tests/test_duralux_customizer_presentation.py` enforces:

- The partial exposes three `theme-options-set` groups with light/dark radios.
- Triggers use class names (`customizer-open-trigger` / `customizer-close-trigger`)
  and never `javascript:` URLs.
- No `onclick=` attributes anywhere.
- The vanilla JS source uses the dedicated `mindcare:duralux-theme` key.
- It does not write or read `data-bs-theme` on `document.documentElement`.
- Escape closes the panel and focus is restored to the trigger.
- The partial is rendered from `layouts/base.html` (not from `auth_base.html`).
- The workspace header exposes the open trigger.

## What still needs a human

- Authenticated browser session across the 18-scenario matrix requires MFA
  enrollment, which is intentionally not exposed by product automation. Use the
  application UI to verify the customizer visually after logging in.
- Coverage minimum remains open per `docs/migration/coverage-report.md`.
