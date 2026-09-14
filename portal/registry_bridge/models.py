"""Registry bridge: evaluation attempts, publications, allocations, projections, webhook deliveries.

These are application bookkeeping entities. Research authority remains in the
committed Git registry; a record is *Registered* only after its exact accepted
revision is verified on the default branch.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Allocation(models.Model):
    """Portal-side record of an identifier reservation; the committed ledger file is the public authority."""

    LOCAL, LEDGER_QUEUED, LEDGER_COMMITTED, WITHDRAWN = "local", "ledger_queued", "ledger_committed", "withdrawn"
    STATES = [(s, s) for s in (LOCAL, LEDGER_QUEUED, LEDGER_COMMITTED, WITHDRAWN)]

    namespace = models.CharField(max_length=8)
    value = models.CharField(max_length=16)
    operation_key = models.CharField(max_length=64, db_index=True)
    purpose = models.CharField(max_length=200)
    state = models.CharField(max_length=20, choices=STATES, default=LOCAL)
    ledger_path = models.CharField(max_length=200, blank=True, default="")
    committed_sha = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["namespace", "value"], name="unique_namespace_value"),
            models.UniqueConstraint(fields=["namespace", "operation_key"], name="one_value_per_operation_per_namespace"),
        ]


class NamespaceLock(models.Model):
    """One row per namespace, locked with SELECT ... FOR UPDATE to serialize allocation."""

    namespace = models.CharField(max_length=8, primary_key=True)


class EvaluationAttempt(models.Model):
    """One run of the exact admission engine against one immutable revision."""

    revision = models.ForeignKey("submissions.SubmissionRevision", on_delete=models.PROTECT, related_name="attempts")
    operation_key = models.UUIDField(unique=True, default=uuid.uuid4)
    submission_hash = models.CharField(max_length=80)
    engine_revision = models.CharField(max_length=80)
    registry_base = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=40)
    taxonomy_version = models.CharField(max_length=40)
    decision = models.CharField(max_length=24, blank=True, default="")
    gate_results = models.JSONField(default=dict)
    receipt_id = models.CharField(max_length=12, blank=True, default="")
    receipt = models.JSONField(default=dict)
    execution_manifest = models.JSONField(default=dict)
    candidate_validation = models.JSONField(default=list, help_text="Issues from validating the complete candidate registry")
    review = models.ForeignKey("submissions.ReviewCase", null=True, blank=True, on_delete=models.PROTECT, related_name="attempts")
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by")
    files = models.JSONField(default=dict, help_text="{repo path: content} produced in the candidate checkout")
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["recorded_at"]

    def __str__(self) -> str:
        return f"{self.receipt_id or '(no receipt)'} {self.decision} for revision {self.revision_id}"


class Publication(models.Model):
    """The Git write for one operation: branch, PR, check, merge, verification."""

    AUTHOR_REGISTRATION, ADMISSION = "author_registration", "admission"
    KINDS = [(AUTHOR_REGISTRATION, "Author registration"), (ADMISSION, "Admission bundle")]
    QUEUED, BRANCHED, PR_OPEN, CHECKS_PENDING, AWAITING_REVIEW, MERGED, VERIFIED, BLOCKED, ABANDONED = (
        "queued", "branched", "pr_open", "checks_pending", "awaiting_review", "merged", "verified", "blocked", "abandoned")
    STATUSES = [(s, s) for s in (QUEUED, BRANCHED, PR_OPEN, CHECKS_PENDING, AWAITING_REVIEW, MERGED, VERIFIED, BLOCKED, ABANDONED)]

    operation_key = models.UUIDField(unique=True)
    kind = models.CharField(max_length=30, choices=KINDS)
    attempt = models.ForeignKey(EvaluationAttempt, null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    account = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    summary = models.CharField(max_length=200)
    files = models.JSONField(default=dict, help_text="{repo path: content} — reviewed paths only")
    reservations = models.JSONField(default=list, help_text="identifier values whose ledger entries this publication carries")
    expected = models.JSONField(default=dict, help_text="what must be verifiable on the default branch afterwards")
    base_sha = models.CharField(max_length=64, blank=True, default="")
    branch = models.CharField(max_length=120, blank=True, default="")
    head_sha = models.CharField(max_length=64, blank=True, default="")
    pr_number = models.IntegerField(null=True, blank=True)
    merge_sha = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUSES, default=QUEUED, db_index=True)
    blocker = models.TextField(blank=True, default="", help_text="Exact required action when blocked")
    retries = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.operation_key} [{self.status}]"


class RegistryProjection(models.Model):
    """Rebuildable public view of one committed record at an identified revision."""

    kind = models.CharField(max_length=12, db_index=True)  # author | object | source | relation | governing | receipt
    record_id = models.CharField(max_length=24, db_index=True)
    committed_sha = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=80)
    refreshed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("kind", "record_id", "committed_sha")]


class ProjectionSnapshot(models.Model):
    """Whole-registry derived views (search index, profiles, bridge candidates, history) at one revision."""

    committed_sha = models.CharField(max_length=64, unique=True)
    search_index = models.JSONField()
    profiles = models.JSONField()
    bridge_candidates = models.JSONField()
    object_history = models.JSONField(default=dict)
    receipts = models.JSONField(default=dict)
    taxonomies = models.JSONField(default=dict)
    schema_version = models.CharField(max_length=40)
    taxonomy_version = models.CharField(max_length=40)
    is_current = models.BooleanField(default=False, db_index=True)
    refreshed_at = models.DateTimeField(default=timezone.now)


class WebhookDelivery(models.Model):
    """Deduplicates GitHub deliveries by their delivery ID."""

    delivery_id = models.CharField(max_length=80, unique=True)
    event = models.CharField(max_length=40)
    received_at = models.DateTimeField(default=timezone.now)
    summary = models.CharField(max_length=200, blank=True, default="")
