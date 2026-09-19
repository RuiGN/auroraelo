# Account UI translation report

This bounded S14.05 slice marks the fixed interface copy in the six templates under
`templates/accounts/`, the account form metadata, request-time view contexts and
form errors, role display labels, and the unsupported-language response. The accompanying JSON evidence
contains draft English and Spanish catalog values with exact gettext keys.

The implementation uses `gettext_lazy` for form field metadata and `gettext` for
request-time contexts and errors. Templates use `translate` or `blocktranslate`,
including accessible labels and the MFA clipboard status attributes. Stable action
values (`restart`, `revoke`, `revoke_others`), URL names, credential material, UUIDs,
HTTP behavior and authorization controls remain unchanged.

## Validation scope

`tests/test_account_ui_translations.py` exercises English and Spanish login output,
form labels, an application-owned password mismatch, and Django's email validation.
These assertions depend on the root catalog merge and compiled `.mo` files; this
slice intentionally does not edit `.po` or `.mo` files.

## Remaining account-adjacent copy

The invitation email subject and body in `accounts/views.py` remain PT-BR because
outbound communication belongs to S14.09 and requires recipient-language activation.
Domain/service exceptions originate outside this slice;
`GENERIC_LOGIN_ERROR` and `GENERIC_RECOVERY_RESPONSE` are translated at their UI
rendering boundary, while broader service/domain translation requires root triage.
English technical exception messages used only for server failures were not marked
as product UI. Django framework validation depends on the framework catalogs.

This evidence covers only the account UI slice. It does not claim completion of
S14.05, catalog review, language publication, or the full Sprint 14 acceptance.
