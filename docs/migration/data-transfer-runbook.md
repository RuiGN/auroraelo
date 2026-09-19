# Data boundary and transfer runbook

Status: clean-install procedure started; operational data transfer is not authorized
or executed. A production transfer requires a deployment-specific reviewed plan.

## Clean installation

1. Install the pinned dependencies into the Mindcare environment.
2. Configure a database and cache dedicated to Mindcare. For disposable testing use
   `compose.test.yml`; its tmpfs data is not durable and must never hold real records.
3. Set `DJANGO_SETTINGS_MODULE`, `DB_*`, and independent security keys as required by
   the chosen environment. Use the custom `accounts.User` from the first migration.
4. Run `manage.py migrate --plan`; check application labels and migration dependencies.
5. Run `manage.py migrate --noinput` on the dedicated database, then
   `manage.py makemigrations --check --dry-run` and `manage.py check`.
6. Verify an empty operational database has no imported patients, messages or charges.
   Create test identities only through controlled fixtures in a disposable environment.
7. Configure private uploads separately; do not publish `private_media/` via static
   files. Test authorization before enabling real uploads or download endpoints.

## If operational transfer is requested later

Record the exact source/destination release and database versions, authorization,
maintenance window, acceptable downtime, rollback owner and consistency checkpoint.
Take an encrypted database backup and a matching private-media snapshot, outside Git.
Record SHA-256 hashes and restrict access; never embed credentials in documentation.

Restore first into an isolated staging environment. Preserve primary keys, tenant
relationships, content types, permissions and migration history. Reconcile counts per
table and clinic, foreign-key relationships, financial totals and attachment hashes.
Reconcile or explicitly invalidate active sessions/tokens according to an approved policy.

Encrypted MFA, audit integrity and protected exports may depend on source key material.
Choose secure key transfer or an explicit rotation/re-enrollment strategy before import;
never assume newly generated keys can decrypt source records. Verify decryptability
without logging secrets or clinical content.

Disable outbound adapters during rehearsal so webhooks, messages and charges are not
replayed. Establish cursor/idempotency checkpoints before activating workers/providers.
Validate representative authorized/denied access for at least two clinics.

## Restore rehearsal evidence

A completed rehearsal must record backup creation, hash verification, restore exit status,
table/relationship reconciliation, application readback, private-file verification,
elapsed times and cleanup. Running migrations or restoring an empty schema is not proof
that operational data can be recovered. No completed rehearsal is claimed in this file.

## Rollback

Before cutover, retain the last verified source release, database and matching media
snapshot. If validation fails, stop destination writes and external dispatches, revert
routing to the intact source, and reconcile any destination-only writes before retrying.
Never overwrite the only copy of a database to test restoration.
