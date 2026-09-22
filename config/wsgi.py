"""WSGI entry point for production servers."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

from core.telemetry import configure_telemetry  # noqa: E402

configure_telemetry()

application = get_wsgi_application()
