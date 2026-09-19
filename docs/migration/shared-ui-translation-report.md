# Shared interface translation checkpoint — 2026-09-08

This delivers a bounded part of S14.05–S14.07, plus a local validation tool related
to S14.10. It does not complete those tasks or publish English/Spanish.

## Scope and behavior

`shared-ui-scope.json` declares 27 templates and 7 Python files for extraction:
account pages, layouts/navigation, workspace, shared components, error pages and
visual reference, plus their labels, validations and view contexts. The remaining
73 templates and domain Python/JS/outbound text still require work.

- 336 unique shared-message drafts were added to each language. The actual
  extraction requires 341 catalog keys including the existing selector and plural
  forms; every required key is compiled and nonempty in pt_BR/en/es.
- Labels defined at import use lazy translation; request-time text uses gettext.
  Stable generic login/recovery constants and example rows use gettext_noop for
  extraction while retaining their original values before presentation.
- Greeting/clinic/sorting/page-number interpolations use named placeholders;
  user content is escaped. Revocation notices have singular/plural forms. Role
  choices translate their labels without changing codes, ordering or permissions.
- Clipboard success/failure and theme announcements arrive through translated
  HTML data attributes and are inserted with textContent. Reference chart labels
  and categories are escaped separately, avoiding interpolation into raw JSON.
  Reference date formatting follows the document language while retaining UTC.
- Source locations are retained in PO files. Previously compiled translations
  were compared with the snapshot: all existing keys and values remain intact.
- The original 84 migrations are preserved. No schema, authorization, clinical
  content, routes, currency or production changes are part of this checkpoint.

## Verification and fixes

- 85 focused tests passed. New tests exercise localized form errors/labels,
  invitation role codes, request language, plural notices, escaping, pagination
  accessible names and preservation of original record text.
- 96 Chromium scenarios passed, zero page errors: 72 combinations of login,
  workspace, reference and 404 × three languages × 320/390/1440 px × light/dark;
  21 additional account states at 320px; three real MFA submissions rendering
  recovery codes. Clipboard success and denial fallbacks were exercised in each
  language. Recovery-code values are masked in screenshots.
- Workspace screenshots intentionally show the theme after a toggle. Their
  result records distinguish the initial `theme` from `screenshotTheme`.
  Representative Spanish login and English workspace screenshots were inspected.
- A browser check exposed the reference chart's data-category-1 access mismatch;
  explicit getAttribute reads fixed the rendered SVG categories. One in-progress
  full suite was interrupted after 444 passing tests for this correction; it is
  not the final acceptance result.
- Catalog checker: real Django extraction + GNU gettext compilation across the
  declared scope, with no missing keys, placeholder mismatches or stale MO files.
  A disposable negative probe removed one English translation and left its MO
  stale; the checker correctly rejected both conditions without touching runtime.
- Final full-suite, coverage, Ruff, mypy, Django and static results are recorded
  in `evidence/latest-verification.json` and `shared-ui-*` logs.
- Independent review: `shared-ui-translation-review.md`. Translation handoff
  mappings remain in `evidence/{account,shell,component,reference}-ui-translations.json`.

## Local maintenance

Use the project virtualenv with GNU gettext installed, from the repository root:

```sh
.venv/bin/python scripts/check_ui_catalogs.py
```

The checker extracts only declared source files into a temporary directory and
writes a scoped POT/report. It reads existing PO/MO files without modifying or
publishing them. It rejects missing compiled translations, placeholder divergence
and stale binaries. Keep `shared-ui-scope.json` explicit as later domains are added.
Edit/review catalog translations, compile with `msgfmt --check` or Django's
`compilemessages`, and rerun the check and relevant HTTP/browser tests.

The checker is not yet a complete-project CI/build gate. Remaining work includes
all domain copy, dashboard/plugin/JS catalogs, outbound recipient language,
localized parsing/formatting and human terminology review. The default allowlist
still contains pt-br only in every runtime settings module; three languages are
available exclusively in test overrides and the disposable browser preview.
