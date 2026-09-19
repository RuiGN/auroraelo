# Clinic and onboarding translation review

Scope: the bounded clinic/onboarding translation diff, its five templates, eight Python files, two focused test files, and browser harness. This is not a review of the entire imported working tree. No application source, persisted data, migrations, deployment, or source-project files were modified by this review.

## Specification review

No actionable source findings identified.

- Fixed headings, descriptions, labels, choices, step presentations, domain/TLS status presentations, checklist text, and upload/service errors use translated presentation text. Class/module metadata uses lazy translation; service and selector messages resolve at runtime.
- Authored clinic names, goals, consent titles/purposes, and operational configuration remain data. Template autoescaping remains enabled; interpolation does not introduce `safe` or HTML trust of authored values.
- Module, contact, reminder, weekday, and step codes remain stable. Domain strings, URLs, timezone identifiers, language configuration values, authorization checks, upload checks, and persistence operations retain their contracts. Base `LANGUAGES` remains pt-br only; en/es availability in a synthetic preview is not publication approval.
- Invalid preferences POST retains the bound form and its errors. A recognized submitted step takes precedence over a conflicting query parameter. Valid submitted choices are rendered from the bound data. The invalid branch cannot call the record/completion services, so it cannot advance or write onboarding state. The template includes the existing form behavior script for invalid-field focus and displays non-field errors.
- Catalog evidence records 47 cumulative source files and 486 required keys, no missing keys or placeholder errors, and no stale compiled catalogs. Preservation evidence records 145 added compiled keys per locale and no changes to earlier compiled values.

## Code quality review

No actionable source findings identified. Presentation mappings match the currently defined domain/TLS statuses and keep the original objects/codes. The bound-form change is narrow and leaves successful POST behavior unchanged. The browser harness covers body/query step disagreement, retained valid choices, invalid-field focus, themes/viewports/locales, and denied administrative routes.

## Validation and limits

Source and catalog/preservation evidence were independently inspected. Database tests were intentionally not rerun while the coordinating agent owned PostgreSQL validation. Completed artifacts confirm:

- 77 focused regression tests passed (`clinic-onboarding-focused.log`).
- 249 browser scenarios passed, including six invalid-form cases and 27 permission denials, with no browser/asset errors (`clinic-onboarding-browser.log`, `visual-clinic-onboarding/results.json`).
- Ruff passed, 479 files already formatted, mypy passed for 579 files, Django system check passed, and migration check reported no changes.

The implementer subsequently reported the corrected focused UI suite passing 18 tests in 2.70 seconds after adding the test-only language override and stronger bound-form assertions. Its final completion message was inspected through agent status. The earlier `clinic-onboarding-final-focused.log` still records the superseded fixture failure (2 failed, 22 passed), so it must not be presented as the successful rerun artifact. Those failures came from requesting unpublished locales without the test override; the production pt-br-only allowlist remains intact.

The HTTP regression explicitly checks that invalid input creates no onboarding record; nonmutation of an existing record follows from the reviewed invalid branch, rather than a separate runtime assertion. Full-project runtime tests and deployment were outside this review.

Final verdict: approved for this bounded source slice; no actionable specification, security, business-behavior, or code-quality findings. Evidence housekeeping remains: preserve the corrected test-run output alongside the superseded log before claiming a fully self-contained final validation bundle.
