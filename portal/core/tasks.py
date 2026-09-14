"""Job runner with leases, bounded retries, and periodic reconciliation.

``run_job`` is the only Celery task that touches the outbox. Every concrete
operation is a plain Python callable registered in ``HANDLERS`` and must be
idempotent for its operation key: retried or duplicate deliveries never
create a second decision, identity, or publication.
"""

from __future__ import annotations

import logging
import traceback
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Job, dispatch, record_event

log = logging.getLogger("portal.jobs")

HANDLERS: dict = {}


def handler(name: str):
    def register(fn):
        HANDLERS[name] = fn
        return fn
    return register


class RetryableError(Exception):
    """Transient failure: the job is retried with backoff."""


class DeterministicFailure(Exception):
    """The job cannot succeed without a specific human action; it stops with that action recorded."""


def _lease(operation_key) -> Job | None:
    now = timezone.now()
    with transaction.atomic():
        job = Job.objects.select_for_update().filter(operation_key=operation_key).first()
        if job is None:
            return None
        if job.state in (Job.SUCCEEDED, Job.DEAD):
            return None
        if job.state == Job.LEASED and job.lease_expires_at and job.lease_expires_at > now:
            return None  # another worker holds a live lease
        if job.next_retry_at and job.next_retry_at > now and job.state == Job.FAILED:
            return None
        job.state = Job.LEASED
        job.attempts += 1
        job.lease_expires_at = now + timedelta(seconds=settings.PORTAL_JOB_LEASE_SECONDS)
        job.save(update_fields=["state", "attempts", "lease_expires_at", "updated_at"])
        return job


@shared_task(name="core.tasks.run_job", bind=True, ignore_result=True)
def run_job(self, operation_key: str) -> None:
    job = _lease(operation_key)
    if job is None:
        return
    fn = HANDLERS.get(job.task_name)
    if fn is None:
        _finish(job, Job.DEAD, f"no handler registered for {job.task_name}")
        return
    try:
        fn(job)
    except DeterministicFailure as exc:
        _finish(job, Job.DEAD, str(exc))
        record_event("job.stopped", operation_key=job.operation_key, submission=job.submission_id,
                     reason=str(exc), actor_label="system")
    except Exception as exc:  # noqa: BLE001 - every failure must land in the outbox, never vanish
        safe = f"{type(exc).__name__}: {str(exc)[:500]}"
        log.warning("job %s attempt %s failed: %s", job.operation_key, job.attempts, safe)
        log.debug(traceback.format_exc())
        if job.attempts >= job.max_attempts:
            _finish(job, Job.DEAD, safe)
            record_event("job.exhausted", operation_key=job.operation_key, submission=job.submission_id,
                         reason=safe, actor_label="system")
        else:
            delay = min(3600, 15 * (2 ** (job.attempts - 1)))
            Job.objects.filter(pk=job.pk).update(state=Job.FAILED, last_safe_error=safe, lease_expires_at=None,
                                                 next_retry_at=timezone.now() + timedelta(seconds=delay),
                                                 dispatched_at=None, updated_at=timezone.now())
    else:
        _finish(job, Job.SUCCEEDED, "")


def _finish(job: Job, state: str, error: str) -> None:
    Job.objects.filter(pk=job.pk).update(state=state, last_safe_error=error, lease_expires_at=None,
                                         updated_at=timezone.now())


@shared_task(name="core.tasks.reconcile", ignore_result=True)
def reconcile() -> dict:
    """Recover queued work the broker may have lost and reconcile pending publications with Git."""
    now = timezone.now()
    redispatched = 0
    candidates = Job.objects.filter(state__in=[Job.QUEUED, Job.FAILED], next_retry_at__lte=now)
    for job in candidates:
        if job.dispatched_at and job.dispatched_at > now - timedelta(seconds=settings.PORTAL_RECONCILE_INTERVAL_SECONDS):
            continue  # recently dispatched; give the broker a chance
        dispatch(job.operation_key)
        redispatched += 1
    expired = Job.objects.filter(state=Job.LEASED, lease_expires_at__lt=now)
    for job in expired:
        Job.objects.filter(pk=job.pk).update(state=Job.FAILED, lease_expires_at=None, dispatched_at=None,
                                             last_safe_error="lease expired (worker restart?)", updated_at=now)
        dispatch(job.operation_key)
        redispatched += 1
    from registry_bridge import reconciliation

    publications = reconciliation.reconcile_pending_publications()
    return {"redispatched": redispatched, "publications_checked": publications}
