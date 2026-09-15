"""Cross-cutting infrastructure: append-only events and the transactional job outbox.

Neither model is a research authority. Events record who did what to which
revision; Jobs record background work whose authoritative state is here (in
PostgreSQL), not in the broker, so broker loss never erases submitted work.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Event(models.Model):
    """Append-only audit event. Never updated, never deleted."""

    id = models.BigAutoField(primary_key=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="events")
    actor_label = models.CharField(max_length=120, blank=True, default="", help_text="system | reviewer | researcher | webhook")
    action = models.CharField(max_length=80, db_index=True)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="scoped_events")
    submission_id = models.UUIDField(null=True, blank=True, db_index=True)
    revision_number = models.IntegerField(null=True, blank=True)
    previous_state = models.CharField(max_length=40, blank=True, default="")
    new_state = models.CharField(max_length=40, blank=True, default="")
    operation_key = models.UUIDField(null=True, blank=True, db_index=True)
    correlation = models.CharField(max_length=200, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("events are append-only")
        super().save(*args, **kwargs)


def record_event(action: str, *, actor=None, actor_label: str = "", account=None, submission=None,
                 revision=None, previous_state: str = "", new_state: str = "", operation_key=None,
                 reason: str = "", correlation: str = "", payload: dict = None) -> Event:
    return Event.objects.create(
        action=action, actor=actor, actor_label=actor_label or ("system" if actor is None else "user"),
        account=account, submission_id=getattr(submission, "id", submission),
        revision_number=getattr(revision, "number", revision), previous_state=previous_state,
        new_state=new_state, operation_key=operation_key, reason=reason, correlation=correlation,
        payload=payload or {},
    )


class Job(models.Model):
    """Outbox entry: one unit of background work with an idempotent operation key."""

    QUEUED, LEASED, SUCCEEDED, FAILED, DEAD = "queued", "leased", "succeeded", "failed", "dead"
    STATES = [(s, s) for s in (QUEUED, LEASED, SUCCEEDED, FAILED, DEAD)]

    id = models.BigAutoField(primary_key=True)
    operation_key = models.UUIDField(unique=True, default=uuid.uuid4)
    task_name = models.CharField(max_length=120, db_index=True)
    payload = models.JSONField(default=dict)
    state = models.CharField(max_length=12, choices=STATES, default=QUEUED, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=6)
    lease_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    next_retry_at = models.DateTimeField(default=timezone.now, db_index=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_safe_error = models.TextField(blank=True, default="", help_text="Operator-safe error context; never manuscript text or secrets.")
    submission_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.task_name} {self.operation_key} [{self.state}]"


def enqueue(task_name: str, payload: dict = None, *, operation_key=None, submission=None,
            max_attempts: int = None) -> Job:
    """Create (or recover) the job row and dispatch it *after* the surrounding transaction commits."""
    operation_key = operation_key or uuid.uuid4()
    job, created = Job.objects.get_or_create(
        operation_key=operation_key,
        defaults={"task_name": task_name, "payload": payload or {},
                  "submission_id": getattr(submission, "id", submission),
                  "max_attempts": max_attempts or getattr(settings, "PORTAL_JOB_MAX_ATTEMPTS", 6)},
    )
    if created or job.state in (Job.QUEUED, Job.FAILED):
        transaction.on_commit(lambda: dispatch(job.operation_key))
    elif job.state == Job.DEAD:
        # A deliberate re-request after the blocker was resolved: revive with a fresh attempt budget.
        Job.objects.filter(pk=job.pk).update(state=Job.QUEUED, attempts=0, next_retry_at=timezone.now(),
                                             dispatched_at=None, last_safe_error="", lease_expires_at=None)
        transaction.on_commit(lambda: dispatch(job.operation_key))
    return job


def dispatch(operation_key) -> None:
    from .tasks import run_job

    Job.objects.filter(operation_key=operation_key, dispatched_at__isnull=True).update(dispatched_at=timezone.now())
    run_job.delay(str(operation_key))
