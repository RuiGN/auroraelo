# People UI translation checkpoint — 2026-09-08

Continuation of S14.05–S14.07 alongside S08.04 on the existing local
`codex/duralux-migration` worktree. This does not complete the migration or
publish English and Spanish.

Four templates cover patient listing, registration, authorized detail and the
professional directory. Fixed UI, form metadata and presentation/service messages
use Django internationalization; authored names, accessibility preferences,
addresses and emergency contacts stay unchanged and escaped. Submitted role,
gender, language and timezone codes retain their original semantics.

## Corrections during resumption

- A denied-access test switched users with `force_login`, which correctly clears
  the old session. It now selects the clinic for the therapist before asserting
  the actual patient-policy 403; the access rule was not changed.
- Independent review identified `Nome` translated as `First name` in full-name
  table columns. The three full-name labels now use the gettext context
  `person full name` and English `Name`, preserving account-registration copy.
  HTTP regressions assert the distinction.
- The browser harness resets scrolling after testing table keyboard focus,
  preventing the fixed header from obscuring headings in full-page captures.

## Verified evidence

- `evidence/resume-focused.xml`: 51 PostgreSQL UI tests passed, including all 11
  people cases. They retain authored/escaped data, translated errors, stable
  filters/domain values, and denial of unlinked therapist access.
- `evidence/resume-people-browser.log` and `evidence/visual-people/results.json`:
  90 Chromium scenarios passed across pt-br/en/es, 320/390/1440px and both
  themes; includes invalid forms, focus, empty filters and access boundaries.
- Screenshots inspected: Spanish mobile dark registration and English desktop
  professional listing. The latter was recaptured with its heading visible.
- Catalogs integrated and compiled; `evidence/resume-catalog-final.json` checks
  the cumulative 42-template scope. No prior compiled translation was changed
  or removed (`evidence/resume-catalog-preservation.json`).

The initial independent reviewer reported the terminology finding but its session
ended before a final verdict. A subsequent independent rereview inspected the
current contextual labels, compiled catalogs, permissions and stable domain codes:
specification and code quality approved, with no actionable code findings. See
`people-ui-translation-review.md`. The cumulative extraction is authoritative;
earlier scoped POT files predate the context correction. Full-suite results are
recorded in `continuation-report.md`.

Full visual accessibility acceptance, native-language market review and the
remaining domain families are still open. Production LANGUAGES remains pt-br.
