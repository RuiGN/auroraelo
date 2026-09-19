# Sprint 2 evidence — 2026-09-08

## Services and schema

`compose.test.yml` starts a distinct `mindcare-test` project with PostgreSQL 17 and
Redis 8, bound to `127.0.0.1:55439` and `127.0.0.1:56389`. Both services passed
health checks (`test-services.log`). Storage is disposable tmpfs; no production
database, volume, credentials or records were used.

`postgres-migrate.log` records successful application to an empty database of
102 migrations: 84 original application migrations and 18 Django migrations.
All original migration files remain byte-identical to the source. Later,
`postgres-corrective-migrate.log` records additive `audit.0005_expand_action_namespace`.
Current schema therefore contains 103 migrations, including 85 application migrations.

## PostgreSQL-specific correction

The first complete PostgreSQL suite after repairing template syntax recorded
1212 passed / 40 failed (`destination-postgres-pytest.xml`). 38 failures were the
same storage defect: `audit_auditevent.action` was `varchar(32)`, while existing
domain action names reach 47 characters. SQLite baseline did not enforce that limit.
The other two failures concerned theme-button labeling and a brittle exact-class test.

A new regression first failed on PostgreSQL (`audit-action-red.log`). The corrective
migration expands the field to 128 without truncating values, changing enum choices,
rewriting earlier migrations or modifying audit hash computation. The regression
checks full action readback and chain verification. Theme controls use native buttons;
the chart-table test still requires both contract classes on an actual table while
allowing additional styling classes.

`corrections-focused.log`: 124 passed. Independent review approved scope and code
quality. The final complete PostgreSQL suite passed **1253 tests**, with coverage
**86%**, still below the unchanged 90% CI threshold. `destination-final-pytest.log`
and XML capture the complete result; `coverage-gate.log` records the remaining gap.

## Backup and restore rehearsal

Created two synthetic clinics and two users with unusable passwords, linked by two
memberships, in `mindcare_rehearsal`, cloned from the clean migrated database.
A scoped membership query for one clinic did not expose the other's membership.
No operational record or attachment was used.

Created a custom-format PostgreSQL dump under ignored `.migration-runtime/` with
mode 0600, calculated SHA-256, and restored to `mindcare_restored` with
`pg_restore --exit-on-error`. `restore-result.json` records matching counts and
application readback of identical membership, clinic and user IDs. The fixture
identifiers are in `restore-fixture.json`. This dump exercises the 102-migration
original schema; it is not a backup of production or proof of transferring real
encrypted records/private files.

The restored database was subsequently upgraded with the additive audit migration
(`restored-upgrade.log`), demonstrating restoration of the original schema followed
by the current forward migration.

The operational transfer boundary and required reconciliation/key strategy are
documented in `../data-transfer-runbook.md`. No production cutover is authorized
or implied by this rehearsal.
