# Independent review of the shared UI translation slice

Date: 2026-09-08. Scope: partial DURALUX S14.05/S14.06 only.

Reviewed current files against `.migration-runtime/shared-i18n-before`: account forms and views, language response, core reference forms, config view contexts, clinic navigation context, the six shared template directories and both affected JavaScript files. Review was read-only apart from this report; no database access, pytest run, commit or deployment was performed.

## Findings and disposition

- Synthetic `ACTIVITY_ROWS` labels were initially translated via variables without extraction markers. The issue was reported to the parent and the declarations now use `gettext_noop`. `GENERIC_LOGIN_ERROR` and `GENERIC_RECOVERY_RESPONSE` also now use extraction markers while retaining their plain-string service values and request-time translation.
- The shell draft JSON used Django template placeholders (`{{ name }}`, `{{ clinic_name }}`, `{{ count }}`). The merged compiled catalogs now correctly contain gettext placeholders; no raw template placeholder remains in any compiled value.
- Invitation role labels now use a UI-local lazy translation map. Independent rendering under pt-BR, English and Spanish verified the four translated labels while retaining exactly the service-provided role codes and ordering. The original eager-label limitation is resolved.

No newly introduced authorization, tenant selection, secret exposure, escaping, stable-code or URL regression was found in the reviewed diff. CSRF, MFA protection, status codes, recovery neutrality and redirect validation retain their previous behavior. No new `safe` rendering or `innerHTML` interpolation was introduced. The chart's three category attributes match its sole current consumer and fixed three-point synthetic dataset. UTC date interpretation remains unchanged.

## Completed checks

- Django loaded all 27 templates in the scoped directories without template syntax errors.
- An isolated template render verified hostile interpolated text remains escaped inside a `blocktranslate` HTML attribute under pt-BR, English and Spanish overrides.
- All 344 handoff JSON entries have nonempty English and Spanish values and matching named placeholders after template-placeholder normalization. Duplicate messages do not conflict between handoffs.
- Default settings still contain `LANGUAGE_CODE = "pt-br"` and only pt-BR in `LANGUAGES`.

## Final catalog follow-up

The independent rerun of `scripts/check_ui_catalogs.py` passed for 341 required compiled lookup keys from 34 declared sources, with no missing translation, placeholder mismatch or stale MO artifact. The checker uses real Django extraction plus GNU gettext compilation, validates source paths and stages extraction outside the repository; it does not mutate application catalogs or language settings.

Every pre-slice compiled non-header key and value is retained exactly: 24 pt-BR and four each English/Spanish. Current catalogs contain 360 pt-BR keys and 341 each English/Spanish. No existing catalog message was lost or changed. All compiled values preserve source HTML tags and contain no raw template placeholders. Focused direct lookups verified greeting/context placeholders, neutral login rejection, sortable labels and singular/plural notification sentences in all three languages.

The parent owns the full regression suite and browser matrix. This report does not assert full language coverage, native-speaker editorial approval, launch-language publication, full Sprint 14 completion or production deployment. Existing domain and outbound-message translation limitations remain documented scope limits.

## Execution closure and chart correction

The final browser run caught a defect missed in the initial source review: `data-category-1` is not available as `dataset.category1`. The three chart category reads now use `getAttribute("data-category-1")`, `getAttribute("data-category-2")` and `getAttribute("data-category-3")`, matching the three literal attribute names in the reference template. This bounded correction restores the translated chart categories without changing values, ordering or escaping. The earlier broad chart statement should be read together with this correction; the initial review did not detect the DOM mapping defect.

Read the completed execution evidence: `shared-ui-browser.log` reports 96 passing scenarios; `destination-shared-ui-final-pytest.log` reports 1,331 passing tests in 163.09 seconds; `shared-ui-lint.log` reports all checks passed; `shared-ui-mypy.log` reports no issues in 583 source files. The final catalog evidence again reports 341 required keys with empty missing, placeholder and stale-artifact lists. These results were executed by the parent and inspected here, not independently rerun by this reviewer. Adding PO source references leaves catalog lookup behavior unchanged; the final stale-artifact check confirms checked PO compilation matches the workspace MO bytes. No further scoped defect remains identified.
