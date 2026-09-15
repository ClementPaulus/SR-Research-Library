"""Health endpoint and shared template context."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone

from .models import Job


def health(request):
    """Web, database, worker heartbeat (oldest queued job age), storage, and Git sync status."""
    status = {"web": "ok"}
    healthy = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["database"] = f"error: {type(exc).__name__}"
        healthy = False
    oldest = Job.objects.filter(state__in=[Job.QUEUED, Job.FAILED]).order_by("created_at").first()
    age = (timezone.now() - oldest.created_at).total_seconds() if oldest else 0
    status["outbox_oldest_pending_seconds"] = int(age)
    status["outbox_dead_jobs"] = Job.objects.filter(state=Job.DEAD).count()
    if age > 4 * settings.PORTAL_RECONCILE_INTERVAL_SECONDS:
        status["worker"] = "stale"
        healthy = False
    else:
        status["worker"] = "ok"
    try:
        from django.core.files.storage import default_storage

        default_storage.exists("healthz-probe")
        status["storage"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["storage"] = f"error: {type(exc).__name__}"
        healthy = False
    try:
        from registry_bridge.checkout import repository_head

        status["registry_head"] = repository_head()[:12]
    except Exception as exc:  # noqa: BLE001
        status["registry_head"] = f"error: {type(exc).__name__}"
        healthy = False
    from registry_bridge.models import Publication

    status["publications_pending"] = Publication.objects.exclude(
        status__in=[Publication.VERIFIED, Publication.ABANDONED]).count()
    recent = timezone.now() - timedelta(hours=24)
    status["publications_verified_24h"] = Publication.objects.filter(status=Publication.VERIFIED, verified_at__gte=recent).count()
    return JsonResponse(status, status=200 if healthy else 503)


