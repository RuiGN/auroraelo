# Sprint 14 language backend foundation

## Scope

This change implements the backend foundation in DURALUX.prd S14.02 and
S14.03. It does not publish incomplete English or Spanish interface
translations. All runtime settings modules explicitly publish only `pt-br`.
The stable user preference candidates remain `pt-br`, `en`, and `es` so a
reviewed locale can be enabled later without changing the persisted contract.

## Runtime contract

- `User.preferred_language` is optional and defaults to an empty string. The
  additive `accounts.0007_user_preferred_language` migration leaves existing
  users without an inferred preference.
- Resolution order is a valid published profile preference, Django's language
  cookie, `Accept-Language`, then `pt-br`. Invalid and removed values fall back
  without rewriting the profile or cookie.
- `LocaleMiddleware` runs after sessions and before `CommonMiddleware`.
  `UserLanguageMiddleware` runs after authentication and before clinic and
  account security middleware. It keeps `request.LANGUAGE_CODE`, translation
  context, and `Content-Language` aligned, including error responses and sync
  or async streaming responses.
- Translated HTML varies on `Cookie` and `Accept-Language`; existing privacy
  and security response headers remain intact.
- `POST /accounts/language/` (`account_set_language`) retains Django's native
  language-cookie and safe local `next` redirect behavior, adds a strict
  published-language allowlist, and remains CSRF protected. Anonymous choices
  set only the cookie. An authenticated profile is updated only when account
  security attached a valid managed session.
- The language action is narrowly exempt from clinic and MFA navigation gates,
  while session validation still runs. It does not select a clinic, satisfy
  MFA, or grant access to another route.
- The template context is `ui_languages` with `code` and `name_local`,
  `current_ui_language`, and `ui_language_next`. The return URL contains only
  the current local path and existing query string.

## Verification

The feature was developed test first. The initial focused run failed during
collection because `accounts.context_processors` did not exist. After the
implementation, the focused PostgreSQL run used the isolated base database
`mindcare_i18n`, which creates/reuses `test_mindcare_i18n` on port 55439:

```text
20 passed in 16.91s
```

The first correct-database schema build took 248.86 seconds; the warm rerun
above confirms it was migration setup rather than a deadlock. Tests cover the
additive migration for an existing user, migration drift, CSRF, GET 405,
invalid languages, safe redirects and query preservation, anonymous and
managed-session persistence, revoked sessions, two users in one browser,
cross-device profile precedence, cookie and browser negotiation, removed
locales, clinic independence, exact MFA enforcement, context data, cache vary
headers, and sync/async streaming context restoration.

Focused verification also completed with:

```text
Ruff format: 11 files already formatted
Ruff check: All checks passed
mypy --strict: Success: no issues found in 11 source files
manage.py makemigrations --check --dry-run: No changes detected
```

No coverage file was written. No commit, push, source import, or production
change was performed.
