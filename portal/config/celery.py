"""Celery application. Authoritative job state lives in PostgreSQL (core.Job); Redis only delivers."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("portal")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["core", "accounts", "submissions", "registry_bridge"])
app.conf.beat_schedule = {
    "reconcile-outbox-and-publications": {
        "task": "core.tasks.reconcile",
        "schedule": float(os.environ.get("PORTAL_RECONCILE_INTERVAL_SECONDS", "120")),
    },
}
