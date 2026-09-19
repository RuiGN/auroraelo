# Language flag toggle implementation plan

**Approved design:** flag only on the closed shared language toggle: Brazil for
pt-br, USA for en, Spain for es. Open list keeps native language names as text.
Flags are visual aliases, not nationality or locale changes. Keep accessible name,
CSRF, persistence, 44px target, keyboard/focus and existing dark-mode contrast.

**Architecture:** replace globe/code in `templates/components/language_selector.html`
with a decorative local image selected by the effective language. Reuse the existing
vendor flag SVG assets under `static/duralux/images/flags/`. Keep a globe fallback
for future unknown languages. Scope flag sizing to the component in product CSS.
No JavaScript behavior or Python models/settings changes. No commit/push/production.

- [x] Add parameterized template tests asserting image selection, flag-only button,
  full accessible name and unchanged textual options; run RED.
- [x] Implement fixed SVG mappings and CSS sizing; copy only the three static SVGs;
  update runtime inventory/hash contract; run GREEN and focused checks.
- [x] Rebuild only local web; verify image loading, flag changes after language POST,
  contrast and accessible names in real login and post-login layouts; record evidence.

Verification commands: `.venv/bin/python -m pytest --no-cov
 tests/test_language_selector_ui.py tests/test_duralux_static_foundation.py -q`
with disposable test settings/database; existing browser scripts
`verify-runtime-languages.cjs` and `verify-language-selector-contrast.cjs` enhanced
to assert the flag-only toggle. Rendered captions/options remain text. Expected:
three flags served locally, no external asset requests, full local matrix passing.
