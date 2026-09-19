# S14.01–S14.04 bounded independent review

Review date: 2026-09-08. Review scope is the language preference foundation,
shared selector, and their security/context boundaries. This is not acceptance
of S14.05–S14.12 or publication of English/Spanish. The checkout contains the
ongoing untracked migration; this reviewer did not modify implementation,
commit, deploy, or run pytest.

## Final source review and author follow-up

The initial streaming wrapper evaluated the source iterator before activating
the response language and wrapped asynchronous streams in a synchronous
iterator. Authors were notified. The saved fix was reread: separate sync/async wrappers
activate during next/anext, restore in finally, and yield only after restoration.
Both defects are resolved in source. Focused execution evidence is author-owned.

Added tests were reread for two users sharing one browser, revoked-session POST
refusal, preservation of the active clinic key, and effective language on MFA
responses. The refined MFA case establishes a valid clinic and asserts the
exact enrollment redirect plus an unverified MFA session. These assertions now
exercise the intended boundary instead of stopping at a missing-clinic error.

The browser author found a 320px dropdown positioning problem. The corrective
CSS was reread: the selector-specific rule overrides vendor width and disables
its transform animation, preserving Popper positioning. The author rerun now records 38 passing Chromium scenarios and no errors in
`evidence/visual-i18n/results.json`, also confirmed by the browser log. Source
inspection alone did not detect this visual failure.

The root reviewer subsequently found a critical omission missed in the initial
bounded pass: development and production explicitly import base settings but
omitted LANGUAGES. Django would therefore use its global language list there,
despite the base/test allowlist being correct. The earlier blanket publication
conclusion was invalid and required reopening this review.

The author added LANGUAGES to both environment imports and parametrized runtime
configuration checks. Independent rereview instantiated Django Settings for
base, development, production and test using synthetic environment values only;
no database, network or pytest execution was involved. All four now expose
exactly pt-br, default pt-br, USE_I18N=True, the project locale directory, the
intended middleware order, and the language context processor. Entry points were
traced: manage.py defaults to development; WSGI/ASGI default to production;
pytest and normal CI checks use test, with a separate production check. The only
three-language settings override outside tests is the disposable preview.

All publication consumers use settings.LANGUAGES: profile validation, native
locale negotiation, endpoint allowlist and selector context. No alternate
set_language route, i18n URL prefix or JavaScriptCatalog publication route was
found. The similarly named support-network urgent-plan preferred_language is a
separate domain field and is not used to publish UI languages.

No additional actionable source findings remain after this configuration
rereview. This statement applies to the corrected environment imports, not the
initial base/test-only snapshot.

## Reviewed contracts

- Profile values are effective only while present in `settings.LANGUAGES`.
  Native LocaleMiddleware supplies cookie, browser negotiation and default
  fallback. Inferred preferences are not written to the profile.
- The additive user migration starts existing users with an empty preference.
  Candidate model choices include pt-br/en/es; the published default is pt-br
  alone. Partial English/Spanish catalogs are not publicly selectable.
- The endpoint is POST-only, goes through CSRF middleware, validates the
  published allowlist and delegates redirect/cookie handling to native
  `set_language`. Profile persistence uses the authenticated request user and
  requires its managed session. No submitted user/clinic identifier is used.
- The language endpoint exemption is after managed-session validation, and
  only exempts this route from the existing MFA navigation enforcement. It
  does not grant clinic permissions or mark MFA verified.
- The profile language middleware precedes tenant/MFA denial handling and
  sets the effective request and response language. HTML responses vary on
  Cookie and Accept-Language. No translated response/fragment cache was found
  in the bounded reviewed account/config/core/template paths.
- Authentication and workspace bases set document language and direction.
  The shared selector has native option names, current selection, associated
  labels, a 44px toggle, and a viewport-bounded menu.
- Its separate POST form contains CSRF, language and current-path `next`;
  unrelated form values are not collected or copied into the redirect.
- The script confirms before discarding edited POST forms. Cancellation
  preserves dirty state. Acceptance clears the existing beforeunload guard;
  sessionStorage carries only the selector focus target across navigation.

## Verification limits

S14.01 inventory/glossary is technically ready as a discovery artifact. Human
commercial terminology review remains an S14.07 acceptance requirement. The
review compared available pre-change HTML/CSS/JS snapshots and found changes
limited to the language foundation and its existing form-guard integration.

Source inspection is not browser evidence for keyboard operation, focus,
320px layout, or confirmation dialogs. The author-owned Chromium artifact was inspected: 36 combinations of auth/
workspace, pt-br/en/es, 320/390/1440px and light/dark, plus dirty-form and blocked-
storage scenarios. English/Spanish were enabled only in the disposable preview.
Focused/backend results and the full regression/coverage gate must be reported
separately.
This source review does not establish full-suite or multilingual publication
acceptance.

## Final validation refinement

Reviewed `test_consent_center_static_copy_comes_from_translation_catalog` after
LocaleMiddleware integration. The test now publishes pt-br/en only within its
override and sends Accept-Language=en on the actual request, rather than relying
on ambient translation state outside the middleware. It preserves the original
English title/button assertions and Portuguese-title exclusion, and additionally
asserts Content-Language=en. This adapts the request setup to the new language
resolution contract without weakening the translation assertions. The user
fixture has no explicit profile preference that would override that header.

Inspected `evidence/visual-i18n/real-login-result.json`: the author-owned probe
records real credential login, an explicit es preference, a fresh en-US browser,
restoration without a language cookie, and no errors. This supplements the
force-login tests with the real authentication flow; it remains disposable
preview evidence, not production publication evidence. The author reports the
single adapted test passed; the final full-suite rerun was still pending when
this refinement was reviewed.

## Execution closure recorded by the implementing agent

The final PostgreSQL run completed after this review: 1310 passed, 0 failed/skipped,
127.91s. Coverage is 86.01979429458568%; the unchanged 90% gate still fails.
See `evidence/latest-verification.json` and `destination-i18n-final-pytest.xml`.
