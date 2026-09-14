"""Reconciliation: recover publications whose webhook or worker acknowledgment was lost."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.models import Job, dispatch

from .models import Publication
from .publication import publish_job_key


def reconcile_pending_publications() -> int:
    """Re-dispatch the publish job for every publication still in flight and not touched recently."""
    cutoff = timezone.now() - timedelta(seconds=settings.PORTAL_RECONCILE_INTERVAL_SECONDS)
    pending = Publication.objects.filter(
        status__in=[Publication.QUEUED, Publication.BRANCHED, Publication.PR_OPEN, Publication.CHECKS_PENDING,
                    Publication.AWAITING_REVIEW, Publication.MERGED],
        updated_at__lte=cutoff,
    )
    count = 0
    for publication in pending:
        job = Job.objects.filter(operation_key=publish_job_key(publication.operation_key)).first()
        if job is None or job.state in (Job.SUCCEEDED, Job.DEAD):
            continue
        if job.state == Job.LEASED and job.lease_expires_at and job.lease_expires_at > timezone.now():
            continue
        Job.objects.filter(pk=job.pk).update(state=Job.QUEUED, next_retry_at=timezone.now(), dispatched_at=None)
        dispatch(job.operation_key)
        count += 1
    return count


def nudge_publication_for_branch(branch: str) -> bool:
    """Webhook hint: a PR/check/push event mentioned this branch; run its publication now."""
    publication = Publication.objects.filter(branch=branch).exclude(
        status__in=[Publication.VERIFIED, Publication.ABANDONED]).first()
    if publication is None:
        return False
    job = Job.objects.filter(operation_key=publish_job_key(publication.operation_key)).first()
    if job and job.state not in (Job.SUCCEEDED, Job.DEAD):
        Job.objects.filter(pk=job.pk).update(state=Job.QUEUED, next_retry_at=timezone.now(), dispatched_at=None)
        dispatch(job.operation_key)
        return True
    return False
