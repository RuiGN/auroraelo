# Login: language selector now exposes per-locale flags

Date: 2026-09-09 19:43 UTC
Scope: anonymous login surface only; not a full-domain acceptance.
Worktree: `/mnt/2c8d19a3-3bbb-4f90-b09f-9e17c780ce6a/Projects/mindcare/.git/worktrees/duralux-fidelity-index`
Brand state: build `mindcare:fidelity` (derived from `mindcare:latest` + this worktree).

## Decision

The closed language toggle inside the login card now renders the SVG flag of the
current locale (Brazil / United States / Spain) plus the uppercase language code,
replacing the previous `feather-globe` glyph. The menu keeps the same native
`<select>` form so CSRF, focus restoration, and the relative `next` round-trip
remain verified.

## Browser matrix (Playwright headless Chromium)

Path: `/accounts/login/?next=%2Fworkspace/`
Languages: `pt-br`, `en`, `es`
Widths: 320, 390, 1440
Themes: light, dark
Scenarios: 18 (3 × 3 × 2)

Geometry of every scenario:

```
{ insideCard: true, topGap: 25, rightGap: 25, contained: true,
  aboveBrand: true, overlapsEmblem: false, width: 74.7, height: 44 }
```

Errors collected: 0

## Screenshots

`login-{language}-{width}-{theme}.png` next to this log.
Representative pixels verified with vision analysis:
- PT-BR 320 dark: Brazil flag rectangle ~ (260, 256), no overflow.
- EN 1440 light: United States flag rectangle ~ (1090, 213).
- ES 390 light: Spain flag rectangle inside the open dropdown header.
