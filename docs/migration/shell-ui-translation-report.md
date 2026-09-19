# Shell UI translation report

Date: 2026-09-08
Scope: bounded S14.05 slice for the shared Duralux shell and workspace.

## Implemented

- Marked fixed visible text and accessibility attributes in `templates/layouts/**/*.html`
  and `templates/workspace/*.html` with Django `translate` or `blocktranslate`.
- Used `blocktranslate count` for the pending operational-revocation notification.
- Bound clinic and user display values as escaped template variables; no user-authored or
  persisted content is translated.
- Kept route names, URL paths, role values, layout values, activity identifiers, query
  keys and sort keys unchanged.
- Marked the synthetic activity constants with `gettext_noop`, preserving their
  `str` API and canonical source values. Translation occurs within the active request
  before display filtering and sorting.
- Translated request-time workspace, component-example, plain-text health, bad-layout
  and safe error-handler copy in `config/views.py`.
- Added translated `data-theme-dark` and `data-theme-light` labels consumed by the
  shell theme-status script.
- Inspected `clinics/context_processors.py`; it exposes authorization booleans,
  clinic objects and branding data, and contains no fixed UI label to mark.
- Drafted 126 English and Spanish catalog entries in
  `docs/migration/evidence/shell-ui-translations.json`, including one plural entry.

## Verification completed

- All eight owned templates compile with Django's template loader.
- Focused Ruff passed for `config/views.py`, `clinics/context_processors.py` and
  `tests/test_shell_ui_translations.py`.
- Focused mypy passed for the same Python files.
- The translation mapping is valid JSON.
- A source-to-mapping check found no marked shell/config msgid missing from the draft.
- `git diff --check` passed for the owned implementation and evidence files.

## Deferred integration checks

The English and Spanish entries are a merge input only. This slice does not edit or
compile PO/MO catalogs, publish languages, change `LANGUAGES`, or claim S14.05 is
complete. The focused HTTP tests intentionally require the root catalog merge before
they can pass.

Run after merging the catalog entries and compiling catalogs:

```shell
.venv/bin/pytest -q tests/test_shell_ui_translations.py tests/test_smoke.py tests/test_layouts.py tests/test_content_components.py tests/test_observability.py
```

The remaining S14.05 templates and Python modules, full catalog review, browser matrix,
and S14.06-S14.12 acceptance remain pending.
