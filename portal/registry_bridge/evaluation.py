"""Orchestrates one formal evaluation of a confirmed revision in an isolated pinned checkout."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import transaction

from core.models import record_event
from core.tasks import DeterministicFailure, RetryableError
from submissions import state as wf
from submissions.models import ReviewCase, Submission, SubmissionRevision

from . import allocation as bridge_allocation
from .checkout import changed_files, fetch_default_branch, isolated_checkout
from .models import Allocation, EvaluationAttempt, Publication
from .policy import filter_publishable
from .publication import queue_publication

log = logging.getLogger("portal.evaluation")

WORKER = Path(__file__).with_name("evaluate_worker.py")

DECISION_TO_STATE = {
    "ACCEPTED": wf.ACCEPTED_PENDING,
    "RETURNED_FOR_REPAIR": wf.NEEDS_REPAIR,
    "REJECTED": wf.NOT_ADMITTED,
}


def review_triggers(revision: SubmissionRevision) -> list:
    """Documented conditions requiring human resolution. Never controversy, negative results, or the founder's identity."""
    submission = revision.submission
    owner_author = submission.owner.author_id
    triggers = []
    from accounts.models import IdentityClaim

    if IdentityClaim.objects.filter(account=submission.owner, state=IdentityClaim.REQUESTED).exists():
        triggers.append(("identity_claim", "The submitting account has an open claim on an existing AuthorID; "
                                           "verify the claim before evaluating attribution."))
    authors = revision.record.get("authors") or []
    others = [a for a in authors if a != owner_author]
    if others:
        triggers.append(("attribution", f"The record lists AuthorID(s) {', '.join(others)} not bound to the submitting account. "
                                        "Provide evidence of attributable authorship; the uploader is never substituted for the actual authors."))
    for rid, proposal in (revision.proposed_records.get("relations") or {}).items():
        if not (proposal.get("_evidence") or proposal.get("evidence") or "").strip():
            triggers.append(("unsupported_relation", f"Proposed relation {rid} states no supporting evidence. "
                                                     "State what evidence supports this connection."))
    for sid, source in (revision.proposed_records.get("sources") or {}).items():
        if source.get("_ambiguous_version"):
            triggers.append(("ambiguous_source", f"Source {sid}: {source['_ambiguous_version']}"))
    return triggers


def evaluate_revision(revision: SubmissionRevision, *, base_sha: str = None, review: ReviewCase = None,
                      attempt_key=None) -> EvaluationAttempt | None:
    submission = revision.submission
    attempt_key = attempt_key or revision.operation_key
    existing = EvaluationAttempt.objects.filter(operation_key=attempt_key).first()
    if existing and existing.decision:
        return existing  # idempotent: one formal receipt per evaluation attempt

    if review is None:
        open_cases = list(submission.review_cases.filter(revision=revision, state=ReviewCase.OPEN))
        if open_cases:
            raise DeterministicFailure("review case(s) still open")
        resolved_for_revision = submission.review_cases.filter(revision=revision, state=ReviewCase.RESOLVED).exists()
        triggers = [] if resolved_for_revision else review_triggers(revision)
        if triggers:
            with transaction.atomic():
                for condition, detail in triggers:
                    ReviewCase.objects.get_or_create(submission=submission, revision=revision, condition=condition,
                                                     defaults={"detail": detail})
                wf.transition(submission, wf.REVIEW_NEEDED, reason="; ".join(d for _, d in triggers), revision=revision,
                              operation_key=revision.operation_key)
            raise DeterministicFailure("human review required: " + "; ".join(c for c, _ in triggers))

    base_sha = base_sha or fetch_default_branch()
    if submission.workflow_state in (wf.SUBMITTED, wf.REVIEW_NEEDED, wf.PROCESSING_UNAVAILABLE, wf.ACCEPTED_PENDING,
                                     wf.NEEDS_REPAIR, wf.NOT_ADMITTED):
        wf.transition(submission, wf.EVALUATING, revision=revision, operation_key=attempt_key,
                      reason=f"evaluating against base {base_sha[:12]}")

    allocations = list(Allocation.objects.filter(operation_key__startswith=str(submission.id)))
    receipt_id = bridge_allocation.reserve_identifier("RCPT", f"{submission.id}:rcpt:{attempt_key}",
                                                      purpose=f"admission receipt for revision {revision.number}", base_sha=base_sha)
    allocations = list(Allocation.objects.filter(operation_key__startswith=str(submission.id)))
    ledger_files = bridge_allocation.ledger_files_for(
        [a.value for a in allocations], str(submission.id), purpose=f"submission {submission.id} revision {revision.number}",
        states={a.value: ("withdrawn" if a.state == Allocation.WITHDRAWN else "reserved") for a in allocations},
        operation_keys={a.value: a.operation_key for a in allocations})
    proposed = {kind: {rid: {k: v for k, v in rec.items() if not k.startswith("_")}
                       for rid, rec in (revision.proposed_records.get(kind) or {}).items()}
                for kind in ("authors", "sources", "relations")}
    review_decision = None
    if review is not None:
        review_decision = {"condition": review.condition, "resolution": review.resolution[:1000],
                           "resolved_at": review.resolved_at.strftime("%Y-%m-%dT%H:%M:%SZ")}
    supersedes = None
    if revision.repairs_id:
        prior = EvaluationAttempt.objects.filter(revision=revision.repairs).exclude(receipt_id="").order_by("-recorded_at").first()
        supersedes = prior.receipt_id if prior else None

    with isolated_checkout(base_sha) as checkout:
        spec = {
            "checkout": str(checkout),
            "record": revision.record,
            "proposed": proposed,
            "ledger_files": ledger_files,
            "operation_key": str(attempt_key),
            "receipt_id": receipt_id,
            "registry_base": base_sha,
            "source_files": revision.source_file_hashes,
            "route": "portal",
            "write": True,
            "register": True,
            "supersedes_attempt": supersedes,
            "review_decision": review_decision,
        }
        with tempfile.TemporaryDirectory(prefix="sr-spec-") as tmp:
            spec_path, result_path = Path(tmp) / "spec.json", Path(tmp) / "result.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            python = settings.PORTAL_EVALUATION_PYTHON or sys.executable
            try:
                proc = subprocess.run([python, str(WORKER), str(spec_path), str(result_path)],
                                      cwd=checkout, capture_output=True, text=True,
                                      timeout=settings.CELERY_TASK_TIME_LIMIT - 30, env={"PATH": "/usr/bin:/bin:/usr/local/bin",
                                                                                        "PYTHONDONTWRITEBYTECODE": "1",
                                                                                        "PYTHONNOUSERSITE": "1",
                                                                                        "HOME": tmp})
            except subprocess.TimeoutExpired:
                _unavailable(submission, revision, "evaluation worker exceeded its time budget")
                raise RetryableError("evaluation worker timed out")
            if not result_path.exists():
                _unavailable(submission, revision, f"evaluation worker produced no result (exit {proc.returncode})")
                raise RetryableError(f"worker exit {proc.returncode}: {proc.stderr[-400:]}")
            result = json.loads(result_path.read_text(encoding="utf-8"))

        status = result.get("status")
        if status == "error":
            _unavailable(submission, revision, result.get("error", "unknown worker error"))
            raise RetryableError(result.get("error", "worker error"))
        if status in ("dependency_invalid", "dependency_conflict"):
            issues = result.get("issues", [])
            with transaction.atomic():
                submission.processing_notes = [{"kind": "dependency", "issues": issues}]
                submission.save(update_fields=["processing_notes", "updated_at"])
                wf.transition(submission, wf.NEEDS_REVIEW, revision=revision, operation_key=revision.operation_key,
                              reason="proposed source/author/relation records did not validate; no receipt issued",
                              payload={"issues": issues[:20]})
            raise DeterministicFailure("proposed dependency records invalid; researcher must repair the draft")
        if status == "base_invalid":
            _unavailable(submission, revision, "the registry base itself failed validation; maintainer action required")
            raise DeterministicFailure("registry base invalid at " + base_sha)

        files = filter_publishable(changed_files(checkout, base_sha))

    receipt = result["receipt"]
    manifest = result["execution"]
    with transaction.atomic():
        attempt = EvaluationAttempt.objects.create(
            revision=revision, operation_key=attempt_key,
            submission_hash=manifest["submission_hash"], engine_revision=manifest["engine_revision"],
            registry_base=base_sha, schema_version=manifest["schema_version"], taxonomy_version=manifest["taxonomy_version"],
            decision=result["decision"], gate_results=manifest["gate_results"], receipt_id=receipt["receipt_id"],
            receipt=receipt, execution_manifest=manifest, candidate_validation=result.get("post_validation_issues", []),
            review=review, files=files,
            supersedes=EvaluationAttempt.objects.filter(receipt_id=supersedes).first() if supersedes else None,
        )
        SubmissionRevision.objects.filter(pk=revision.pk).update(admission_decision=result["decision"])
        expected = {"receipt_id": receipt["receipt_id"], "decision": result["decision"],
                    "submission_hash": manifest["submission_hash"], "snapshot_path": manifest["submission_snapshot_path"]}
        if result["decision"] == "ACCEPTED":
            expected.update(object_id=revision.record["object_id"], version=revision.record["version"],
                            registered_path=result.get("registered_path"))
        publication = queue_publication(
            kind=Publication.ADMISSION, operation_key=attempt_key, files=files,
            reservations=[a.value for a in allocations], expected=expected,
            summary=f"{result['decision']}: {receipt['submission_identity']} ({receipt['receipt_id']})",
            account=submission.owner, attempt=attempt,
        )
        Allocation.objects.filter(pk__in=[a.pk for a in allocations]).update(state=Allocation.LEDGER_QUEUED)
        wf.transition(submission, DECISION_TO_STATE[result["decision"]], revision=revision,
                      operation_key=attempt_key, reason=f"engine decision {result['decision']} ({receipt['receipt_id']})",
                      payload={"receipt_id": receipt["receipt_id"], "publication": str(publication.operation_key)})
        record_event("evaluation.recorded", submission=submission, revision=revision, operation_key=attempt_key,
                     payload={"decision": result["decision"], "receipt_id": receipt["receipt_id"], "base": base_sha})
    return attempt


def _unavailable(submission: Submission, revision: SubmissionRevision, reason: str) -> None:
    if submission.workflow_state != wf.PROCESSING_UNAVAILABLE:
        wf.transition(submission, wf.PROCESSING_UNAVAILABLE, revision=revision, operation_key=revision.operation_key,
                      reason=reason[:500])
