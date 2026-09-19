# Focused migration test report

## Scope

`tests/test_migration_domain_invariants.py` exercises observable decisions in
two executable migration helpers:

- unsupported database vendors fail closed before any SQL is executed, for
  both applying and dropping the content invariant;
- existing e-mail identifiers are canonicalized in one batch;
- an already-canonical data set does not issue an empty bulk update; and
- blank or case-insensitively duplicated identifiers stop the migration before
  any bulk update.

Four former tests were removed because they compared executed SQL with the same
private SQL constants consumed by the implementation. Those assertions measured
statement forwarding but could remain green with invalid or ineffective SQL.

The database behavior of the content triggers is covered separately by
`tests/test_content_tenant_invariant.py`. That suite tests valid same-tenant
writes and database rejection of cross-tenant content versions, cross-tenant
content media, and content tenant changes. It was not duplicated in this focused
helper test file.

## Focused test result

Command:

```text
env -i PATH=/usr/bin:/bin DJANGO_SETTINGS_MODULE=config.settings.test TEST_DATABASE=postgresql DB_NAME=mindcare_coverage DB_USER=mindcare DB_PASSWORD=mindcare-test-only DB_HOST=127.0.0.1 DB_PORT=55439 COVERAGE_FILE=.coverage.coverage-agent .venv/bin/python -m pytest --reuse-db --no-cov tests/test_migration_domain_invariants.py -q
```

Output:

```text
......                                                                   [100%]
6 passed in 0.33s
```

The `[100%]` progress indicator above means all six collected tests completed;
it is not a code-coverage measurement.

## Static checks

Commands and outputs:

```text
.venv/bin/python -m ruff check tests/test_migration_domain_invariants.py
All checks passed!

.venv/bin/python -m ruff format --check tests/test_migration_domain_invariants.py
1 file already formatted
```

## Evidence boundary

No coverage run was performed for this correction, so this report makes no
module or repository coverage-percentage claim. The isolated
`.coverage.coverage-agent` path remained configured in the focused test command,
and the shared `.coverage` file was not used by that command.

The full suite, the separate database-trigger suite, and the repository-wide
90% coverage gate were not run in this bounded task. Their status must come from
the root integration run.
