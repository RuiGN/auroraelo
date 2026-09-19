# Flag-only language toggle — 2026-09-09

Superseded by the user: globe + language code; login control inside the card,
upper right. See `language-globe-card.md`. Results below describe the old UI only.

User approved flag-only closed control: Brazil for pt-br, USA for en, Spain for es.
Open list keeps Português (Brasil), English and Español as text. Flags do not change
locale variants or imply nationality. Shared login/header component only.

- Template renders a decorative local flag image and full language name in the
  button's accessible label; unknown future languages retain a globe fallback.
- Product CSS sizes the image at 28×21 px inside the existing 44px minimum target.
  Existing dark-mode select/option contrast remains unchanged.
- Only the three required SVGs were copied from the local reference flags directory.
  Parsed SVGs contained no scripts, foreignObject, images, handlers or href attributes.
- Runtime asset list and hashes updated; no additional dependency or remote CDN.
- RED: three new flag-template cases failed before implementation (`flag-toggle-red.log`).
- GREEN: 169 focused/integration tests passed across two non-overlapping runs
  (`flag-toggle-green.log`, `flag-integration-tests.log`). Includes template compilation,
  static collection/hashes, language/session/CSRF behavior and theme contracts.
- Browser: 54 unique scenarios passed: 18 anonymous login and 36 post-login
  vertical/detached layouts; pt-br/en/es, 320/390/1440 px, light/dark. Real images
  decoded, button has no visible text, accessible labels retain language names;
  login POST swaps flag after redirect; header contrast/focus checks pass.
  Evidence: `flag-auth/results.json` and `flag-header/results.json`.
- Scoped catalog gate unchanged: 1,250 marked keys pass (`flag-catalog-check.json`).
- Ruff, focused mypy, JS syntax and git diff whitespace checks passed.
- Local web image rebuilt/healthy; served SVG/CSS bytes match checkout assets.

No commit, push, production publication, password reset or profile preference change.
Full backend suite not rerun for this presentation-only increment; previous S14
translation and full coverage gaps remain open. Browser screenshots were recorded,
not claimed as independent manual visual review.
