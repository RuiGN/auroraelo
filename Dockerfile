# syntax=docker/dockerfile:1.7
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

# Compile catalogs inside the artifact; runtime must not depend on checkout .mo files.
RUN python manage.py compilemessages --settings=config.settings.test \
 && python scripts/check_ui_catalogs.py \
      --scope docs/migration/translated-ui-scope.json \
      --output /tmp/mindcare-ui-catalog-check.json \
      --pot-output /tmp/mindcare-ui.pot \
 && python scripts/check_djangojs_catalogs.py \
      --output /tmp/mindcare-djangojs-catalog-check.json \
 && test "$(python -c 'import json; print(json.load(open("/tmp/mindcare-ui-catalog-check.json"))["passed"])')" = "True" \
 && test "$(python -c 'import json; print(json.load(open("/tmp/mindcare-djangojs-catalog-check.json"))["passed"])')" = "True"

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
