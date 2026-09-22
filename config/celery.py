"""Celery initialization for Aurora Elo Health Systems."""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("auroraelo")
app.config_from_object("django.conf:settings", namespace="CELERY")

from core.telemetry import configure_telemetry  # noqa: E402

configure_telemetry()

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
