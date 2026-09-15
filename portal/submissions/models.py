"""Submissions: drafts, immutable revisions, uploads, field evidence, review cases, questions.

A frozen revision never becomes editable. Repair creates a new revision linked
to the earlier attempt. Uploaded bytes live in object storage under immutable
keys; Git never stores them.
"""

from __future__ import annotations

import hashlib
import json
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from . import state as wf


def canonical_hash(record: dict) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions")
    collaborators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="shared_submissions")
    label = models.CharField(max_length=300, blank=True, default="", help_text="Working title shown in the workspace")
    intended_object_id = models.CharField(max_length=13, blank=True, default="",
                                          help_text="Existing SR-OBJ to revise, or blank for a new object family")
    source_reference = models.CharField(max_length=500, blank=True, default="",
                                        help_text="DOI, archive reference, or source URL supplied instead of / alongside uploads")
    draft = models.JSONField(default=dict, help_text="Editable candidate research-object record")
    proposed_sources = models.JSONField(default=dict, help_text="{placeholder or SRC id: source record}")
    proposed_relations = models.JSONField(default=dict, help_text="{placeholder or REL id: relation record + evidence}")
    draft_version = models.PositiveIntegerField(default=1, help_text="Optimistic concurrency token")
    workflow_state = models.CharField(max_length=40, default=wf.DRAFT, db_index=True)
    processing_notes = models.JSONField(default=list, help_text="Operator-safe processing results and questions")
    publish_files = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.label or f"Submission {str(self.id)[:8]}"

    @property
    def state_label(self) -> str:
        return wf.LABELS.get(self.workflow_state, self.workflow_state)

    @property
    def state_meaning(self) -> str:
        return wf.MEANINGS.get(self.workflow_state, "")

    @property
    def editable(self) -> bool:
        return self.workflow_state in wf.EDITABLE

    @property
    def latest_revision(self):
        return self.revisions.order_by("-number").first()

    @property
    def latest_attempt(self):
        from registry_bridge.models import EvaluationAttempt

        return EvaluationAttempt.objects.filter(revision__submission=self).order_by("-recorded_at").first()

    def can_view(self, account) -> bool:
        if not account or not account.is_authenticated:
            return False
        if account == self.owner or self.collaborators.filter(pk=account.pk).exists():
            return True
        if account.is_administrator:
            return True
        return self.review_assignments.filter(reviewer=account).exists()

    def can_edit(self, account) -> bool:
        return bool(account and account.is_authenticated and
                    (account == self.owner or self.collaborators.filter(pk=account.pk).exists()))


class SubmissionRevision(models.Model):
    """Immutable confirmed record. Content never changes after creation."""

    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    record = models.JSONField()
    proposed_records = models.JSONField(default=dict, help_text="{authors|sources|relations: {id: record}} frozen with the revision")
    content_hash = models.CharField(max_length=80, db_index=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    confirmed_at = models.DateTimeField(default=timezone.now)
    operation_key = models.UUIDField(unique=True, default=uuid.uuid4)
    repairs = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="repaired_by")
    publish_files = models.BooleanField(default=False)
    public_metadata_acknowledged = models.BooleanField(default=False)
    admission_decision = models.CharField(max_length=24, blank=True, default="", help_text="Set only from engine output")
    source_file_hashes = models.JSONField(default=list)

    class Meta:
        unique_together = [("submission", "number")]
        ordering = ["submission", "number"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            allowed = set(kwargs.get("update_fields") or [])
            if not allowed or not allowed <= {"admission_decision"}:
                raise ValueError("confirmed revisions are immutable; create a new revision instead")
        else:
            self.content_hash = canonical_hash(self.record)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.submission_id} r{self.number}"


class Upload(models.Model):
    PENDING, COMPLETE, FAILED = "pending", "complete", "failed"
    STATES = [(s, s) for s in (PENDING, COMPLETE, FAILED)]
    PRIVATE, PUBLIC = "private", "public"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploads")
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="uploads")
    revision = models.ForeignKey(SubmissionRevision, null=True, blank=True, on_delete=models.PROTECT, related_name="uploads")
    storage_key = models.CharField(max_length=300, unique=True)
    filename = models.CharField(max_length=300, help_text="Display metadata only; never a filesystem path")
    media_type = models.CharField(max_length=120, blank=True, default="")
    byte_count = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default="", db_index=True)
    client_sha256 = models.CharField(max_length=64, blank=True, default="")
    visibility = models.CharField(max_length=10, default=PRIVATE)
    state = models.CharField(max_length=10, choices=STATES, default=PENDING)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="members",
                               help_text="Archive this member was extracted from")
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        ordering = ["created_at"]


class FieldEvidence(models.Model):
    SOURCE_EXTRACTION, RESEARCHER_STATEMENT, LIBRARY_CLASSIFICATION = "source-extraction", "researcher-statement", "library-classification"
    ORIGINS = [(SOURCE_EXTRACTION, "Extracted from a source file"), (RESEARCHER_STATEMENT, "Stated by the researcher"),
               (LIBRARY_CLASSIFICATION, "Local library classification")]

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="evidence")
    revision = models.ForeignKey(SubmissionRevision, null=True, blank=True, on_delete=models.PROTECT, related_name="evidence")
    field_path = models.CharField(max_length=120, db_index=True)
    origin = models.CharField(max_length=30, choices=ORIGINS)
    value_preview = models.CharField(max_length=500, blank=True, default="")
    upload = models.ForeignKey(Upload, null=True, blank=True, on_delete=models.PROTECT, related_name="evidence")
    locator = models.CharField(max_length=200, blank=True, default="", help_text="page 3 / paragraph 12 / line 40 / record:title")
    source_version = models.CharField(max_length=200, blank=True, default="")
    processing = models.JSONField(default=dict, help_text="parser, version, ocr flag, model service/version if used")
    uncertain = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["field_path", "created_at"]


class ReviewCase(models.Model):
    """A documented human-review condition. A reviewer resolves inputs; never overrides a gate."""

    OPEN, RESOLVED, RETURNED = "open", "resolved", "returned_to_researcher"
    STATES = [(s, s) for s in (OPEN, RESOLVED, RETURNED)]
    CONDITIONS = [
        ("identity_claim", "Claimed ownership of an existing identity"),
        ("ambiguous_source", "Ambiguous source or version identity"),
        ("edit_ownership", "Conflicting edit ownership"),
        ("attribution", "Disputed or unverified attribution"),
        ("unsupported_relation", "Proposed relation lacks stated evidence"),
        ("taxonomy_or_governing", "Taxonomy or governing change requested"),
        ("publication_exception", "Publication exception"),
    ]

    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="review_cases")
    revision = models.ForeignKey(SubmissionRevision, null=True, blank=True, on_delete=models.PROTECT, related_name="review_cases")
    condition = models.CharField(max_length=40, choices=CONDITIONS)
    detail = models.TextField(help_text="Exact issue and the evidence requested")
    state = models.CharField(max_length=30, choices=STATES, default=OPEN)
    resolution = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]


class Question(models.Model):
    submission = models.ForeignKey(Submission, null=True, blank=True, on_delete=models.PROTECT, related_name="questions")
    revision = models.ForeignKey(SubmissionRevision, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="questions")
    route = models.CharField(max_length=30, default="submission", help_text="submission | source_suggestion | relation_proposal | general")
    text = models.TextField()
    source_pointer = models.CharField(max_length=500, blank=True, default="")
    resolved = models.BooleanField(default=False)
    resolution_evidence = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]


class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="responses")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
