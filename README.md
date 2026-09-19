# Mindcare

Django application being migrated from the source snapshot `453eab7`.
The authoritative migration checklist is [DURALUX.prd](DURALUX.prd).
Imported templates are transitional: their presence does not imply visual acceptance.

## Runtime

Python 3.14 and Django 6.1 are pinned to the source baseline during migration.
The original destination declaration of Django 6.1.1 is deferred until parity is verified.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip check
```

Configuration lives in `config/settings/`; `core/` is the shared application.
Do not recreate migrations or substitute the custom `accounts.User` model.

## Isolated tests

SQLite tests need no `.env` or external service:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
```

Use the disposable local PostgreSQL/Redis services for database-specific checks:

```bash
docker compose -f compose.test.yml up -d --wait
export DJANGO_SETTINGS_MODULE=config.settings.test
export DB_NAME=mindcare DB_USER=mindcare DB_PASSWORD=mindcare-test-only
export DB_HOST=127.0.0.1 DB_PORT=55439 TEST_DATABASE=postgresql
.venv/bin/python -m pytest
docker compose -f compose.test.yml down
```

These fixed credentials are exclusively for disposable localhost tests. The services
store data in tmpfs; stopping/recreating them discards the test data. Never point them
at real uploads or patient data. Do not run competing suites against the same test DB.

## Local development

The application does not automatically load `.env`. Use `.env.example` to configure
and explicitly export development variables, with newly generated keys and an
independent database. `manage.py` defaults to `config.settings.development`.
The example is for local development, not production. Run migrations before starting
the server. Do not copy credentials, databases, uploads or private encryption keys
from the source project.

Production requires `config.settings.production`, explicit hosts, database TLS,
shared cache and independent security keys. Cross-origin CSRF trust is empty unless
explicitly configured. Production publication is outside the current execution.

## Translation catalogs

Local development (`config.settings.development`, including local Compose) offers
`pt-br`, `en`, and `es` via the globe selector on login and in the header. English
and Spanish are draft catalogs for acceptance testing; domain translation gaps
remain documented in `docs/migration/i18n-recheck-audit.md`. Production and the
base configuration remain restricted to `pt-br` pending complete UI/terminology
acceptance. UI language never translates user-authored clinical content.

Install GNU gettext alongside the Python environment (`sudo apt-get install gettext`
on Debian/Ubuntu). After editing a catalog, compile that locale explicitly, for example:

```bash
msgfmt --check locale/en/LC_MESSAGES/django.po -o locale/en/LC_MESSAGES/django.mo
.venv/bin/python scripts/check_ui_catalogs.py \
  --scope docs/migration/translated-ui-scope.json \
  --output /tmp/mindcare-ui-catalog-check.json \
  --pot-output /tmp/mindcare-ui.pot
```

CI runs the same check. It extracts the delivered scope, compiles each catalog in
a temporary directory, and rejects missing required translations, mismatched
placeholders, or stale checked-in `.mo` files. Required fuzzy entries are excluded
by gettext and therefore fail as missing translations. Add each delivered domain
to the cumulative scope; this gate does not certify the remaining untranslated UI
or replace human review and runtime/browser validation.

## Historical documents

`PRD.md`, `MUDANCALAYOUT.prd`, and imported `docs/` describe the source snapshot and
support existing traceability tests. Their completion markers do not describe
Mindcare. Fresh evidence and decisions belong to `docs/migration/`.
