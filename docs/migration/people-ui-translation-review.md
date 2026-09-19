# Independent review — People UI translation

Date: 2026-09-08  
Scope: only the files declared in `people-ui-scope.json`, the four People templates,
`tests/test_people_ui_translations.py`, the current gettext catalogs and the supplied
checkpoint/diff artifacts.

## Verdict

- **Specification: approved.** Fixed interface copy and display labels are localized,
  while authored patient/professional/contact data remains rendered as data. The
  implementation keeps tenant and patient authorization checks, filter parameters,
  persisted enum values, language/timezone codes and service normalization unchanged.
- **Code quality: approved.** No actionable finding remains in the reviewed slice.
  Presentation dictionaries isolate translated labels from stable domain codes, and
  the templates do not translate user-authored values.

## Full-name terminology rereview

The reported English ambiguity is corrected in the current state. All three column or
field labels that mean a person's complete name use gettext context
`person full name`:

- `templates/people/patient_list.html:40`
- `templates/people/professional_list.html:48`
- `templates/people/patient_detail.html:52`

The English catalog maps contextual `Nome` to `Name`, while the existing uncontextual
account-registration `Nome` remains `First name`. Spanish and pt-BR resolve both forms
appropriately. The compiled `.mo` catalogs contain the same distinction. The focused
HTTP regression asserts `Name` and rejects `First name` on the patient listing, and
also asserts `Name` on the professional listing.

## Preservation checks

Static comparison with the source represented by
`.migration-runtime/people-continuation-review.diff` found no permission or data-model
relaxation. Views retain their action-specific authorization calls and the patient
detail policy denial. Form choice values, directory filter values, stored gender,
language and timezone values, and service validation branches remain stable; only
their user-facing labels/messages are localized. Existing tests explicitly cover
escaped authored names, unchanged submitted values/codes, unchanged filters and denial
of an unlinked therapist.

## Evidence limits

Per the review instruction, no test suite was executed. The verdict combines current
source/catalog inspection with recorded evidence: `resume-focused.xml` reports 51
tests passed (11 People cases), the People browser result records 90 scenarios with no
errors, and the catalog evidence reports no missing keys, placeholder errors or stale
compiled catalogs. Those artifacts are prior execution evidence rather than a fresh
run by this reviewer.

`docs/migration/evidence/continuation-people-ui.pot` predates the full-name correction
and lacks the message context. Later cumulative extraction artifacts
(`continuation-ui.pot`, `resume-ui.pot`, and `resume-ui-final.pot`) include the correct
context, as do the current source and catalogs. The scoped POT should be regenerated
if it is intended to serve as the final standalone extraction artifact; this does not
block the code or catalog verdict.

English and Spanish remain unpublished, and native-market terminology acceptance plus
full visual accessibility acceptance remain outside this bounded engineering review.
