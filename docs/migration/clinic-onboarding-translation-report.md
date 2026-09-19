# Clinic and onboarding translation checkpoint — 2026-09-08

Continuation of S14.05–S14.07 alongside S08.03. This bounded delivery does not
complete the full internationalization sprint or publish English/Spanish.

## Scope

Five templates: clinic setup (five stages), clinic-switch confirmation, custom
domains, clinic readiness checklist and patient onboarding (four steps).
Translation covers their form metadata, presentation labels and validations,
plus clinic/onboarding service errors and shared upload checks used for logos.

The UI language remains separate from the clinic's operational language and time
zone. Domain names, clinic names, patient goals, consent document content, enum
codes, submitted values and authorization boundaries retain their original
meaning. Fixed labels are translated at presentation time.

## Verification

The integrated focused regression passed 51 cases (`evidence/resume-focused.xml`),
including these UI flows alongside people and consents. The final browser rerun
passed 249 scenarios (`evidence/resume-clinic-browser-final.log` and
`evidence/visual-clinic-onboarding/results.json`), including language/viewport/theme
combinations, invalid forms and permission denials. These are historical completed
runs, not reruns in the latest reconciliation.

The current source matches the recorded 78-file checkpoint fingerprint. Fresh
cumulative extraction validates 639 required keys across 42 templates and their
Python consumers (`evidence/continuation-catalog-check.json`). Independent bounded
source review approved specification and quality (`clinic-onboarding-translation-review.md`).
Full-suite results and evidence limits are consolidated in `continuation-report.md`.

Manual reinspection of the stored 320px Spanish dark clinic-review capture found
the header avatar partly clipped when the clinic-switch control is present. A
document-level no-overflow assertion did not detect this control clipping. Track
the correction and control-bounds browser assertion in S07.06/S11.02 before full
mobile acceptance; these browser pass counts do not close that visual gap.

## Remaining scope

Other domain templates, outbound recipient language, full project extraction,
JavaScript plugin locales, localized parsing, human terminology review and
image/CI proof remain pending. The production language allowlist remains pt-br.
