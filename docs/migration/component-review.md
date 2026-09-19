# Bounded component review — S07.05 / S07.08

Date: 2026-09-08

Scope: read-only review of the shared form, field, table, pagination, card and
content-state changes identified for S07.05 and S07.08. The source checkout was
used only as a behavioral baseline where useful.

## Resolved component findings

The follow-up changes resolve all three findings from the initial component
review:

- `core/templatetags/accessible_forms.py:59-76` now adapts only exact stock
  choice widgets and exact stock, format-less `DateInput` instances. It uses a
  deep copy and leaves subclasses/custom date formats untouched. The new tests
  exercise custom choice `create_option()` and custom date `get_context()` hooks.
- `templates/components/responsive_table.html:40-47` now renders the first
  mobile field once, with its label included as visually hidden heading text,
  and begins the definition-list output with the second column.
- `templates/components/responsive_table.html:34-36` now exposes the active
  mobile ordering and current direction, while the producer supplies the next
  direction label. The browser script now asserts both pieces of state.

The corrected checkbox/radio CSS also restores native-size controls inside a
44-pixel label target and the browser script measures both dimensions.

## Resolved authentication findings

The follow-up authentication changes resolve both review findings:

- `templates/accounts/sessions.html:40-43` now renders the reauthentication
  password through `accessible_widget`. The wrong-password response therefore
  puts `aria-invalid` and the error paragraph ID in `aria-describedby`; the new
  acceptance test asserts that linkage and the 400 response.
- `templates/accounts/auth_message.html:6-8` now uses a neutral information icon
  for every generic message. It no longer communicates success on the 400
  invalid/expired password-reset response.

The identity expiry test also limits deterministic `secrets.token_bytes` to the
enrollment call. Recovery-code generation keeps production randomness, while
the fixed TOTP secret removes the rare cross-step code-collision source from the
clock-boundary assertion. No correctness issue remains in the reviewed patch.

## Review limits

No implementation files were changed. Per coordination constraints, this review
did not run pytest because another process owns the shared PostgreSQL test
database. The parent task reported 53 focused component tests and 9 browser
scenarios passing, with mypy passing after a one-line ignore correction. The
full suite is still running, so this review does not pre-claim full acceptance.
Review covered the listed component sources, their current consumers and focused
tests, the relevant
S07.05/S07.08 PRD contract, the two identity-boundary tests, and the six account
templates plus authentication CSS and acceptance tests. It does not establish
completion of Sprint 3 or 7, migration-wide template acceptance, full identity
journeys, or production behavior.
