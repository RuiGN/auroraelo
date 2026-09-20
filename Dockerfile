# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS ui-build

WORKDIR /app/design_system
COPY design_system/package.json design_system/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY design_system/ ./
COPY templates/ /app/templates/
COPY psychiatry/templates/ /app/psychiatry/templates/
COPY static/design_system/css/ /app/static/design_system/css/
COPY static/design_system/js/shell.js /app/static/design_system/js/shell.js
RUN npm run build

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      postgresql-client \
      gettext \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . /app
COPY --from=ui-build /app/static/design_system/css/aurora.css /app/static/design_system/css/aurora.css

# Compile catalogs inside the artifact; runtime must not depend on checkout .mo files.
RUN python manage.py compilemessages --settings=config.settings.test \
 && python scripts/check_ui_catalogs.py \
      --scope docs/migration/translated-ui-scope.json \
      --output /tmp/auroraelo-ui-catalog-check.json \
      --pot-output /tmp/auroraelo-ui.pot \
 && python scripts/check_djangojs_catalogs.py \
      --output /tmp/auroraelo-djangojs-catalog-check.json \
 && test "$(python -c 'import json; print(json.load(open("/tmp/auroraelo-ui-catalog-check.json"))["passed"])')" = "True" \
 && test "$(python -c 'import json; print(json.load(open("/tmp/auroraelo-djangojs-catalog-check.json"))["passed"])')" = "True"

RUN mkdir -p /app/staticfiles /app/media /app/private_media \
 && useradd --create-home --shell /bin/bash --uid 1000 appuser \
 && chown -R appuser:appuser /app \
 && chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/health/live/ >/dev/null || curl -fsS http://127.0.0.1:8000/accounts/login/ >/dev/null || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
