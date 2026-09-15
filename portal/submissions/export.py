"""Downloadable handoff bundles built from the recorded revision (never from 'whatever is latest')."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

from django.conf import settings
from django.core.files.storage import default_storage

from core.models import Event
from registry_bridge.models import EvaluationAttempt, Publication

from .models import FieldEvidence, SubmissionRevision, Upload


def _json(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def build_handoff(revision: SubmissionRevision, *, include_private: bool, requested_by) -> bytes:
    submission = revision.submission
    attempt = EvaluationAttempt.objects.filter(revision=revision).exclude(receipt_id="").order_by("-recorded_at").first()
    publication = Publication.objects.filter(attempt=attempt).order_by("-created_at").first() if attempt else None
    uploads = list(Upload.objects.filter(revision=revision, parent__isnull=True, state=Upload.COMPLETE))
    members: dict = {}

    state = attempt.decision if attempt else "PENDING (no formal decision; this is a labelled pending record)"
    remaining = {
        "ACCEPTED": "Registration is pending until the exact accepted revision is verified on the default branch." if not (
            publication and publication.status == Publication.VERIFIED) else "None: the record is registered.",
        "RETURNED_FOR_REPAIR": "Supply the exact repair listed in receipt.json and confirm a new revision.",
        "REJECTED": "Remove the established contract violation and resubmit as a new revision or new object.",
    }.get(attempt.decision if attempt else "", "Confirm and submit this revision for formal evaluation.")
    members["README.md"] = "\n".join([
        f"# Handoff for submission {submission.id} revision {revision.number}",
        "",
        f"Object identity: {revision.record.get('object_id')}",
        f"Purpose: reconstruct the exact evaluated (or explicitly pending) record and its evidence.",
        f"State: {state}",
        f"Exact remaining action: {remaining}",
        f"Package scope: {'owner export (includes private files authorized for this export)' if include_private else 'public-safe export (private files, login data and credentials excluded)'}",
        "",
        "## Reconstruction",
        "1. Check out the research repository at the `registry_base` commit in execution-manifest.json.",
        "2. Install the pinned engine dependencies: `pip install -r requirements-dev.txt` at that commit "
        "(lock hash in execution-manifest.json → dependency_lock).",
        "3. Verify `sha256sum -c SHA256SUMS` and that submission.json hashes to `submission_hash`.",
        "4. Reproduce: `python -m validators.admit submission.json` and compare the seven gate results with receipt.json "
        "(timestamps may differ; gate results and decision must not).",
        "",
        "Library admission confirms that the record meets the organizational requirements. It does not certify the scientific claims.",
        "",
    ])
    members["submission.json"] = _json(revision.record)
    members["sources.json"] = _json({
        "proposed_sources": revision.proposed_records.get("sources", {}),
        "registered_source_ids": revision.record.get("source_ids", []),
        "files": [{"display_name": u.filename, "sha256": u.sha256, "bytes": u.byte_count, "media_type": u.media_type,
                   "visibility": u.visibility, "included": include_private or u.visibility == Upload.PUBLIC} for u in uploads],
        "source_reference": submission.source_reference,
    })
    members["evidence-map.json"] = _json([
        {"field": e.field_path, "origin": e.origin, "locator": e.locator, "upload_sha256": e.upload.sha256 if e.upload else None,
         "upload_display_name": e.upload.filename if e.upload else None, "uncertain": e.uncertain, "processing": e.processing,
         "value_preview": e.value_preview}
        for e in FieldEvidence.objects.filter(revision=revision).select_related("upload")
    ])
    missing = revision.record.get("missingness") or []
    members["missingness.json"] = _json({
        "declared": missing,
        "blocking": [m for m in missing if m.get("class") in ("EVALUABILITY_BLOCKING", "REPAIRABLE", "CONTRACT_VIOLATING")],
        "affected_burden": revision.record.get("next_burden"),
        "repair_required": attempt.receipt.get("exact_repair_required", []) if attempt and attempt.decision == "RETURNED_FOR_REPAIR" else [],
    })
    if attempt:
        members["receipt.json"] = _json(attempt.receipt)
        from registry_bridge.engine import import_engine

        members["receipt.md"] = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)["receipts"].render_receipt_markdown(attempt.receipt)
        manifest = dict(attempt.execution_manifest)
        manifest["dependency_lock"] = _lock_locator()
        manifest["reproduce_command"] = (f"git checkout {attempt.registry_base} && python -m validators.admit submission.json")
        members["execution-manifest.json"] = _json(manifest)
    else:
        members["execution-manifest.json"] = _json({"status": "no formal evaluation has been run for this revision",
                                                    "dependency_lock": _lock_locator()})
    members["publication.json"] = _json(
        {"status": publication.status, "pull_request": publication.pr_number, "branch": publication.branch,
         "base_sha": publication.base_sha, "head_sha": publication.head_sha, "merge_sha": publication.merge_sha,
         "verified_at": publication.verified_at.isoformat() if publication.verified_at else None, "blocker": publication.blocker}
        if publication else {"status": "unpublished", "note": "no publication has been queued for this revision"})
    events = Event.objects.filter(submission_id=submission.id).order_by("occurred_at")
    members["history.json"] = _json({
        "revisions": [{"number": r.number, "content_hash": r.content_hash, "confirmed_at": r.confirmed_at.isoformat(),
                       "repairs": r.repairs.number if r.repairs else None, "admission_decision": r.admission_decision}
                      for r in submission.revisions.order_by("number")],
        "attempts": [{"receipt_id": a.receipt_id, "decision": a.decision, "registry_base": a.registry_base,
                      "recorded_at": a.recorded_at.isoformat(), "supersedes": a.supersedes.receipt_id if a.supersedes else None}
                     for a in EvaluationAttempt.objects.filter(revision__submission=submission).order_by("recorded_at")],
        "transitions": [{"at": e.occurred_at.isoformat(), "action": e.action, "from": e.previous_state, "to": e.new_state,
                         "actor": e.actor_label, "reason": e.reason} for e in events],
    })
    unavailable = []
    for upload in uploads:
        if include_private or upload.visibility == Upload.PUBLIC:
            with default_storage.open(upload.storage_key, "rb") as handle:
                members[f"files/{upload.sha256[:12]}-{_safe_name(upload.filename)}"] = handle.read()
        else:
            unavailable.append({"display_name": upload.filename, "sha256": upload.sha256, "reason": "private file excluded from public-safe export"})
    members["files/UNAVAILABLE.json"] = _json(unavailable)

    sums = []
    for name in sorted(members):
        data = members[name] if isinstance(members[name], bytes) else members[name].encode("utf-8")
        sums.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    members["SHA256SUMS"] = "\n".join(sums) + "\n"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(members):
            data = members[name] if isinstance(members[name], bytes) else members[name].encode("utf-8")
            archive.writestr(name, data)
    return buffer.getvalue()


def _safe_name(filename: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:80] or "file"


def _lock_locator() -> dict:
    lock = settings.PORTAL_REGISTRY_REPO_PATH / "portal" / "requirements.txt"
    engine_lock = settings.PORTAL_REGISTRY_REPO_PATH / "requirements-dev.txt"
    result = {}
    for label, path in (("portal_lock", lock), ("engine_requirements", engine_lock)):
        if path.exists():
            result[label] = {"path": str(path.relative_to(settings.PORTAL_REGISTRY_REPO_PATH)),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return result
