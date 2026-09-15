"""Submission services: uploads, preparation, drafts, confirmation, evaluation dispatch, repair, questions, review."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
import uuid
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from core.models import enqueue, record_event
from core.tasks import DeterministicFailure, RetryableError, handler

from . import extraction, preparation, state as wf
from .models import FieldEvidence, Question, Response, ReviewCase, Submission, SubmissionRevision, Upload

log = logging.getLogger("portal.submissions")

PREPARE = "submissions.prepare"
EVALUATE = "submissions.evaluate"

PLACEHOLDER_OBJECT = "SR-OBJ-NEW"
PLACEHOLDER_RE = re.compile(r"^(SRC|REL)-NEW-[A-Za-z0-9_-]{1,40}$")

OBJECT_ID_RE = re.compile(r"^SR-OBJ-[0-9]{6}$")


class StaleDraft(RuntimeError):
    """Another edit saved a newer draft version; the caller must reload."""


class SubmissionError(RuntimeError):
    pass


# --------------------------------------------------------------------------- creation & uploads

def create_submission(owner, label: str = "", source_reference: str = "", intended_object_id: str = "") -> Submission:
    if intended_object_id and not OBJECT_ID_RE.match(intended_object_id):
        raise SubmissionError("intended_object_id must look like SR-OBJ-000001")
    submission = Submission.objects.create(owner=owner, label=label.strip()[:300], source_reference=source_reference.strip()[:500],
                                           intended_object_id=intended_object_id)
    record_event("submission.created", actor=owner, actor_label="researcher", submission=submission, account=owner)
    return submission


def _storage_key(submission: Submission, upload_id) -> str:
    return f"uploads/{submission.owner.uuid}/{submission.id}/{upload_id}"


def register_upload(submission: Submission, owner, uploaded_file, client_sha256: str = "", visibility: str = Upload.PRIVATE) -> Upload:
    """Stream bytes to immutable storage, hash server-side, and record the upload. Never trusts a client hash alone."""
    if not submission.can_edit(owner):
        raise PermissionError("only the owner or a collaborator may upload to this submission")
    if not submission.editable and submission.workflow_state not in (wf.PREPARING, wf.UPLOADING):
        raise SubmissionError("this submission is frozen; start a repair or new revision to add files")
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > settings.PORTAL_UPLOAD_MAX_FILE_BYTES:
        raise SubmissionError(f"file exceeds the {settings.PORTAL_UPLOAD_MAX_FILE_BYTES // (1024 * 1024)} MiB per-file limit; "
                              "supply an external source link for larger packages")
    existing_total = sum(u.byte_count for u in submission.uploads.filter(state=Upload.COMPLETE, parent__isnull=True))
    if size is not None and existing_total + size > settings.PORTAL_UPLOAD_MAX_SUBMISSION_BYTES:
        raise SubmissionError("this submission would exceed its total upload limit")
    filename = (getattr(uploaded_file, "name", "") or "upload").replace("\\", "/").split("/")[-1][:300]
    digest = hashlib.sha256()
    head = b""
    total = 0
    chunks = []
    for chunk in uploaded_file.chunks():
        if not head:
            head = chunk[:16]
        digest.update(chunk)
        total += len(chunk)
        if total > settings.PORTAL_UPLOAD_MAX_FILE_BYTES:
            raise SubmissionError("file exceeds the per-file limit")
        chunks.append(chunk)
    sha = digest.hexdigest()
    duplicate = submission.uploads.filter(sha256=sha, state=Upload.COMPLETE, parent__isnull=True).first()
    if duplicate:
        return duplicate  # retried upload of an already completed file: no second copy
    if client_sha256 and client_sha256.lower() != sha:
        raise SubmissionError("the file did not arrive intact (client hash mismatch); please retry the upload")
    upload = Upload(owner=owner, submission=submission, filename=filename, byte_count=total, sha256=sha,
                    client_sha256=client_sha256, visibility=visibility,
                    media_type=extraction.detect_media_type(filename, head))
    upload.storage_key = _storage_key(submission, upload.id)
    with transaction.atomic():
        upload.save()
        default_storage.save(upload.storage_key, ContentFile(b"".join(chunks)))
        upload.state = Upload.COMPLETE
        upload.completed_at = timezone.now()
        upload.save(update_fields=["state", "completed_at"])
        record_event("upload.completed", actor=owner, actor_label="researcher", submission=submission, account=owner,
                     payload={"upload": str(upload.id), "bytes": total, "sha256": sha, "media_type": upload.media_type})
        if submission.workflow_state in (wf.DRAFT, wf.NEEDS_REVIEW, wf.UPLOADING):
            if submission.workflow_state != wf.PREPARING:
                wf.transition(submission, wf.PREPARING, actor=owner, actor_label="researcher", reason="upload completed; preparing draft")
        enqueue(PREPARE, {"submission": str(submission.id)}, operation_key=uuid.uuid5(uuid.NAMESPACE_URL, f"prepare:{submission.id}:{sha}"),
                submission=submission)
    return upload


def start_preparation_from_reference(submission: Submission, owner) -> None:
    """No file: prepare from the supplied DOI/URL/archive reference only (bounded acquisition of URLs)."""
    if submission.workflow_state in (wf.DRAFT, wf.NEEDS_REVIEW):
        wf.transition(submission, wf.PREPARING, actor=owner, actor_label="researcher", reason="preparing from source reference")
    enqueue(PREPARE, {"submission": str(submission.id)},
            operation_key=uuid.uuid5(uuid.NAMESPACE_URL, f"prepare:{submission.id}:{submission.source_reference}"), submission=submission)


def read_upload(upload: Upload) -> bytes:
    with default_storage.open(upload.storage_key, "rb") as handle:
        return handle.read()


# --------------------------------------------------------------------------- preparation job

PREPARATION_STEPS = [
    ("preserve", "Preserve original files"),
    ("identify", "Identify source and version information"),
    ("duplicates", "Check for possible duplicates"),
    ("extract", "Extract supported metadata"),
    ("classify", "Propose library classifications"),
    ("assemble", "Prepare the editable submission"),
]


def _progress(submission: Submission, steps: list, problems: list, extra: dict = None) -> None:
    """Persist step-by-step progress so the workspace shows what is actually happening."""
    note = {"kind": "preparation", "steps": steps, "problems": list(problems), "at": timezone.now().isoformat()}
    note.update(extra or {})
    Submission.objects.filter(id=submission.id).update(processing_notes=[note], updated_at=timezone.now())
    submission.processing_notes = [note]


def _step(steps: list, key: str, status: str, detail: str = "") -> None:
    for step in steps:
        if step["key"] == key:
            step["status"] = status
            step["detail"] = detail
            return


@handler(PREPARE)
def prepare(job) -> None:
    submission = Submission.objects.select_related("owner").get(id=job.payload["submission"])
    if submission.workflow_state not in (wf.PREPARING, wf.UPLOADING, wf.PROCESSING_UNAVAILABLE, wf.DRAFT, wf.NEEDS_REVIEW):
        return  # frozen or already evaluated; preparation of a stale job is a no-op
    steps = [{"key": key, "label": label, "status": "pending", "detail": ""} for key, label in PREPARATION_STEPS]
    problems: list = []
    extractions: list = []
    uploads = list(submission.uploads.filter(state=Upload.COMPLETE, parent__isnull=True))
    try:
        _step(steps, "preserve", "done", f"{len(uploads)} file(s) stored with server-side SHA-256; originals are never modified")
        _progress(submission, steps, problems)

        _step(steps, "extract", "running")
        _progress(submission, steps, problems)
        for upload in uploads:
            data = read_upload(upload)
            if extraction.suffix_of(upload.filename) == ".zip":
                try:
                    members = extraction.expand_zip(
                        data, max_members=settings.PORTAL_ARCHIVE_MAX_MEMBERS,
                        max_expanded_bytes=settings.PORTAL_ARCHIVE_MAX_EXPANDED_BYTES, max_depth=settings.PORTAL_ARCHIVE_MAX_DEPTH,
                        per_file_bytes=settings.PORTAL_UPLOAD_MAX_FILE_BYTES, time_budget=settings.PORTAL_EXTRACTION_TIME_BUDGET_SECONDS)
                except (extraction.ArchiveLimit, Exception) as exc:  # noqa: BLE001 - zipfile errors are intake problems
                    problems.append(f"{upload.filename}: archive could not be processed ({str(exc)[:160]}). "
                                    "This is an intake limit, not a research decision; the file is saved.")
                    continue
                for member in members:
                    child = _record_member(upload, member)
                    if extraction.suffix_of(member["name"]):
                        extractions.append((str(child.id), member["name"], extraction.extract(member["data"], member["name"])))
                continue
            extractions.append((str(upload.id), upload.filename, extraction.extract(data, upload.filename)))
        if not extractions and submission.source_reference and re.match(r"^https?://", submission.source_reference):
            from . import acquisition

            try:
                final_url, content_type, payload = acquisition.fetch(submission.source_reference)
                name = final_url.split("/")[-1] or "source"
                if "pdf" in content_type:
                    name = name if name.lower().endswith(".pdf") else name + ".pdf"
                elif "html" in content_type:
                    name = name + ".txt"
                extractions.append(("", name, extraction.extract(payload, name)))
                problems.append(f"Acquired {final_url} ({len(payload)} bytes). The library does not mirror it; the URL stays a source link.")
            except acquisition.AcquisitionRefused as exc:
                problems.append(f"Source URL was not acquired: {exc}. The source gap is preserved; supply the source identity manually.")
        parsed = sum(1 for _, _, e in extractions if e.fields or e.record)
        _step(steps, "extract", "done", f"{parsed} of {len(extractions)} file(s) yielded fields; parsers: "
              + ", ".join(sorted({str(e.processing.get('parser')) for _, _, e in extractions if e.processing.get('parser')})) or "no parseable files")
        _progress(submission, steps, problems)

        # ---- identify sources and versions
        _step(steps, "identify", "running")
        _progress(submission, steps, problems)
        per_file = [(name, preparation.identify_sources(e.full_text, name)) for _, name, e in extractions if e.full_text]
        if submission.source_reference:
            per_file.append(("source reference", preparation.identify_sources(submission.source_reference, "source reference")))
        identification = preparation.merge_identifications(per_file)
        ident_summary = []
        if identification["dois"]:
            ident_summary.append(f"DOI {', '.join(d['value'] for d in identification['dois'][:3])}")
        if identification["arxiv"]:
            ident_summary.append(f"arXiv {', '.join(a['value'] for a in identification['arxiv'][:2])}")
        if identification["versions"]:
            ident_summary.append(f"version statement(s) {', '.join(sorted({v['value'] for v in identification['versions']}))}")
        if identification["publication_hints"]:
            ident_summary.append("publication hint: " + ", ".join(h["value"] for h in identification["publication_hints"]))
        _step(steps, "identify", "done", "; ".join(ident_summary) or "no DOI, arXiv, or version statement found in the text")
        if identification["version_ambiguity"]:
            problems.append(identification["version_ambiguity"] + " Confirm which version governs before submitting.")
        _progress(submission, steps, problems)

        # ---- duplicates against the committed registry
        _step(steps, "duplicates", "running")
        _progress(submission, steps, problems)
        from catalog.projection import current_projection
        from registry_bridge.engine import import_engine

        projection = current_projection()
        engine = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)
        manifests = engine["execution"].load_execution_manifests(settings.PORTAL_REGISTRY_REPO_PATH / "receipts" / "executions") if engine["execution"] else {}
        candidate_title = next((e.fields["title"]["value"] for _, _, e in extractions if e.fields.get("title")), None) or \
            next((e.record.get("title") for _, _, e in extractions if e.record), None) or submission.draft.get("title") or ""
        findings = preparation.check_duplicates(candidate_title, [d["value"] for d in identification["dois"]],
                                                [u.sha256 for u in uploads], projection, manifests)
        dup_detail = "; ".join(f"{f['id']} ({f['basis']})" for f in findings[:4]) or "no matching DOI, similar title, or identical file in the registry"
        _step(steps, "duplicates", "done", dup_detail)
        _progress(submission, steps, problems)

        # ---- classification suggestions (library classification, always uncertain)
        _step(steps, "classify", "running")
        _progress(submission, steps, problems)
        text = "\n".join(e.full_text for _, _, e in extractions if e.full_text)
        taxonomies = engine["loader"].load_taxonomies(settings.PORTAL_REGISTRY_REPO_PATH / "taxonomy")
        suggestions = preparation.suggest_classifications(text, taxonomies, identification["publication_hints"]) if text else {}
        _step(steps, "classify", "done", ", ".join(f"{k} → {v['term']}" for k, v in suggestions.items() if v.get("term")) or "no classification could be suggested from the text")
        _progress(submission, steps, problems)
    except Exception as exc:  # noqa: BLE001
        log.warning("preparation failed for %s: %s", submission.id, type(exc).__name__)
        for step in steps:
            if step["status"] == "running":
                step["status"] = "failed"
                step["detail"] = f"{type(exc).__name__}; your files are preserved and this step will be retried"
        _progress(submission, steps, problems)
        if submission.workflow_state != wf.PROCESSING_UNAVAILABLE:
            wf.transition(submission, wf.PROCESSING_UNAVAILABLE, reason=f"preparation error: {type(exc).__name__}")
        raise RetryableError(f"preparation error {type(exc).__name__}") from exc

    # ---- assemble the editable submission
    _step(steps, "assemble", "running")
    _progress(submission, steps, problems)
    owner_author = submission.owner.author_id
    candidate, evidence, _legacy_questions, more_problems = extraction.assemble_candidate(
        extractions, submission.draft, owner_author, submission.source_reference)
    problems += more_problems
    evidence = list(evidence)
    for path, suggestion in suggestions.items():
        if not suggestion.get("term"):
            evidence.append((path, "library-classification", "keyword match: tie", "", "no single suggestion: " + ", ".join(suggestion.get("alternatives", [])), True, {"method": "keyword"}))
            continue
        head, _, tail = path.partition(".")
        current = candidate.get(head)
        if tail:
            block = current if isinstance(current, dict) else {"primary": "", "secondary": []}
            if not block.get("primary"):
                block["primary"] = suggestion["term"]
                if suggestion.get("secondary") and not block.get("secondary"):
                    block["secondary"] = suggestion["secondary"]
                candidate[head] = block
        elif not current:
            candidate[head] = suggestion["term"]
        evidence.append((path, "library-classification", "keyword match: " + ", ".join(suggestion["matched"][:4]), "",
                         f"suggested {suggestion['term']}" + (f"; alternatives: {', '.join(suggestion['alternatives'])}" if suggestion["alternatives"] else ""),
                         True, {"method": "keyword", "alternatives": suggestion["alternatives"]}))
    proposed_sources = dict(submission.proposed_sources or {})
    source_type_unconfirmed = False
    existing_sources = [f for f in findings if f["kind"] == "existing_source"]
    if existing_sources:
        for finding in existing_sources:
            if finding["id"] not in candidate.get("source_ids", []):
                candidate.setdefault("source_ids", []).append(finding["id"])
        evidence.append(("source_ids", "source-extraction", existing_sources[0]["basis"], "", ", ".join(f["id"] for f in existing_sources), False, {"method": "doi-match"}))
    elif not proposed_sources and not candidate.get("source_ids") and (candidate.get("title") or identification["dois"]):
        placeholder, record, unconfirmed = _auto_source(candidate, identification, extractions, submission)
        proposed_sources[placeholder] = record
        candidate.setdefault("source_ids", []).append(placeholder)
        source_type_unconfirmed = unconfirmed
        evidence.append(("source_ids", "source-extraction", "proposed from extracted title/authors/identifiers", "",
                         f"{placeholder}: {record['title'][:80]}", True, {"method": "auto-source"}))
    if findings:
        candidate["_duplicate_findings"] = findings[:6]
    if identification["version_ambiguity"]:
        candidate["_version_ambiguity"] = identification["version_ambiguity"]
        for record in proposed_sources.values():
            record.setdefault("_ambiguous_version", identification["version_ambiguity"])
    if not settings.PORTAL_EXTRACTION_MODEL_SERVICE_URL:
        problems.append("Automated preparation used deterministic parsers and keyword matching only (no model-assisted extraction is configured). "
                        "Every suggestion is marked uncertain until you confirm it.")
    evidence_dicts = [{"field_path": e[0], "origin": e[1], "uncertain": e[5]} for e in evidence]
    assessment = preparation.assess(candidate, evidence_dicts, findings, identification["version_ambiguity"], source_type_unconfirmed)
    _step(steps, "assemble", "done", f"{len(assessment['ready'])} field(s) ready, {len(assessment['needs_confirmation'])} to confirm, "
          f"{len(assessment['missing'])} missing; {assessment['blocking_open']} blocking question(s)")
    with transaction.atomic():
        submission.refresh_from_db()
        submission.draft = candidate
        submission.proposed_sources = proposed_sources
        submission.draft_version += 1
        submission.processing_notes = [{"kind": "preparation", "steps": steps, "problems": problems, "questions": assessment["questions"],
                                        "assessment": {k: assessment[k] for k in ("ready", "needs_confirmation", "missing", "blocking_open", "submittable")},
                                        "identification": {k: identification[k] for k in ("dois", "arxiv", "zenodo", "versions", "publication_hints", "version_ambiguity")},
                                        "duplicates": findings[:6], "suggestions": suggestions, "at": timezone.now().isoformat()}]
        submission.save(update_fields=["draft", "proposed_sources", "draft_version", "processing_notes", "updated_at"])
        FieldEvidence.objects.filter(submission=submission, revision__isnull=True).delete()
        rows = []
        for field_path, origin, locator, upload_id, preview, uncertain, processing in evidence:
            rows.append(FieldEvidence(submission=submission, field_path=field_path, origin=origin, locator=locator,
                                      upload_id=upload_id or None, value_preview=str(preview)[:500], uncertain=uncertain, processing=processing))
        FieldEvidence.objects.bulk_create(rows)
        if submission.workflow_state in (wf.PREPARING, wf.UPLOADING, wf.PROCESSING_UNAVAILABLE, wf.DRAFT):
            wf.transition(submission, wf.NEEDS_REVIEW, reason="draft prepared; researcher review required",
                          payload={"questions": len(assessment["questions"]), "problems": len(problems), "duplicates": len(findings)})
        record_event("submission.prepared", submission=submission, account=submission.owner,
                     payload={"fields": len(evidence), "questions": len(assessment["questions"]), "duplicates": len(findings),
                              "suggestions": sorted(suggestions)})


def _auto_source(candidate: dict, identification: dict, extractions: list, submission: Submission) -> tuple:
    """Propose a source record from what the files themselves state. Nothing is invented; gaps become missingness."""
    owner_name = _fold(submission.owner.display_name)
    authors = list(candidate.get("_source_authors_hint") or [])
    own_work = bool(authors) and any(_fold(a) == owner_name or owner_name in _fold(a) for a in authors)
    source_type = "corpus-native" if own_work else "external"
    unconfirmed = not authors or not own_work
    identifier, links, missing = {}, [], []
    if identification["dois"]:
        doi = identification["dois"][0]["value"]
        identifier["doi"] = doi
        identifier["url"] = f"https://doi.org/{doi}"
        links.append({"label": "Canonical DOI", "type": "canonical", "url": f"https://doi.org/{doi}", "preferred": True})
    elif identification["urls"]:
        identifier["url"] = identification["urls"][0]["value"]
        links.append({"label": "Source page", "type": "canonical", "url": identification["urls"][0]["value"], "preferred": True})
    if identification["arxiv"]:
        identifier["archive_reference"] = f"arXiv:{identification['arxiv'][0]['value']}"
    if identification["zenodo"]:
        identifier["archive_reference"] = f"zenodo:{identification['zenodo'][0]['value']}"
    if not identifier:
        missing.append("No DOI, URL, or archive reference is stated in the uploaded files; source identity rests on the uploaded manuscript.")
    if not authors:
        authors = [submission.owner.display_name]
        missing.append("No author statement could be extracted; the uploading researcher is listed provisionally and must confirm authorship.")
    missing.append("Publication year not stated in the files.")
    record = {
        "source_id": "SRC-NEW-1", "source_type": source_type, "title": candidate.get("title") or "(title to be confirmed)",
        "source_authors": authors, "source_native_claims": [], "identifier": identifier, "publication_year": None, "venue": None,
        "links": links, "missingness": missing, "status": "active",
        "notes": "Proposed automatically from the uploaded files' own statements; confirm before submitting.",
    }
    versions = sorted({v["value"] for v in identification["versions"]})
    if len(versions) == 1:
        record["version"] = versions[0]
    if unconfirmed:
        record["_source_type_unconfirmed"] = True
    return "SRC-NEW-1", record, unconfirmed


def _fold(text: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower().strip()


def _record_member(parent: Upload, member: dict) -> Upload:
    sha = hashlib.sha256(member["data"]).hexdigest()
    existing = Upload.objects.filter(parent=parent, sha256=sha, filename=member["name"][:300]).first()
    if existing:
        return existing
    child = Upload(owner=parent.owner, submission=parent.submission, parent=parent, filename=member["name"][:300],
                   byte_count=member["bytes"], sha256=sha, media_type=extraction.detect_media_type(member["name"], member["data"][:16]),
                   visibility=parent.visibility)
    child.storage_key = _storage_key(parent.submission, child.id)
    child.save()
    default_storage.save(child.storage_key, ContentFile(member["data"]))
    child.state = Upload.COMPLETE
    child.completed_at = timezone.now()
    child.save(update_fields=["state", "completed_at"])
    return child


# --------------------------------------------------------------------------- drafts

EDITABLE_TOP_LEVEL = {
    "object_id", "title", "authors", "authority", "tier2_class", "functional_locus", "source_ids", "lens", "domain", "object_of_study",
    "structural_focus", "main_question", "secondary_questions", "claim_layers", "evidence_mode", "provenance", "maturity", "relations",
    "governing_refs", "version", "date", "publication_state", "source_boundary", "authority_boundary", "scope", "exclusions",
    "preserved_meaning", "missingness", "distortion_or_substitution_risk", "next_burden", "repair_route", "notes", "supersedes",
    "synthetic",
}


def save_draft(submission: Submission, actor, draft: dict, proposed_sources: dict, proposed_relations: dict,
               expected_version: int, label: str = None, confirm_fields: list = None) -> Submission:
    """Save an editable draft with an optimistic version token.

    Preparation hints (underscore keys) survive saves; callers may update them (e.g. ``_duplicate_resolution``).
    ``confirm_fields`` records that the researcher reviewed uncertain extracted values and kept them, so they
    need not be retyped and stop being asked about.
    """
    if not submission.can_edit(actor):
        raise PermissionError("not permitted to edit this submission")
    if not submission.editable:
        raise SubmissionError("this revision is frozen; start a repair to edit")
    unknown = set(draft) - EDITABLE_TOP_LEVEL - {k for k in draft if k.startswith("_")}
    if unknown:
        raise SubmissionError("draft contains fields outside the object schema: " + ", ".join(sorted(unknown)))
    hint_updates = {k: v for k, v in draft.items() if k.startswith("_")}
    draft = {k: v for k, v in draft.items() if not k.startswith("_")}
    draft["authority"] = {"tier": "tier-2"}  # the library registers Tier-2 records only
    with transaction.atomic():
        current = Submission.objects.select_for_update().get(id=submission.id)
        if current.draft_version != expected_version:
            raise StaleDraft(f"draft changed from version {expected_version} to {current.draft_version} in another tab")
        hints = {k: v for k, v in (current.draft or {}).items() if k.startswith("_")}
        hints.update(hint_updates)
        current.draft = {**draft, **hints}
        current.proposed_sources = proposed_sources or {}
        current.proposed_relations = proposed_relations or {}
        current.draft_version += 1
        if label is not None:
            current.label = label.strip()[:300]
        elif draft.get("title"):
            current.label = str(draft["title"])[:300]
        current.save(update_fields=["draft", "proposed_sources", "proposed_relations", "draft_version", "label", "updated_at"])
        confirmed = []
        for path in confirm_fields or []:
            value = preparation._value_at(current.draft, path)
            if value in (None, "", [], {}):
                continue
            if FieldEvidence.objects.filter(submission=current, revision__isnull=True, field_path=path, uncertain=True).exists() and \
                    not FieldEvidence.objects.filter(submission=current, revision__isnull=True, field_path=path, origin="researcher-statement").exists():
                FieldEvidence.objects.create(submission=current, field_path=path, origin="researcher-statement",
                                             locator="confirmed in the editor", value_preview=str(value)[:500], uncertain=False,
                                             processing={"confirmed_by": str(actor.uuid)})
                confirmed.append(path)
        record_event("draft.saved", actor=actor, actor_label="researcher", submission=current, account=current.owner,
                     payload={"draft_version": current.draft_version, "confirmed_fields": confirmed})
    return current


def assessment_for(submission: Submission) -> dict:
    """Live readiness of the current draft (recomputed from the draft and its evidence rows)."""
    rows = FieldEvidence.objects.filter(submission=submission, revision__isnull=True).values("field_path", "origin", "uncertain")
    draft = submission.draft or {}
    proposed_unconfirmed = any(rec.get("_source_type_unconfirmed") for rec in (submission.proposed_sources or {}).values())
    return preparation.assess(draft, list(rows), draft.get("_duplicate_findings"), draft.get("_version_ambiguity"), proposed_unconfirmed)


def preflight(submission: Submission) -> dict:
    """Non-authoritative form feedback using the live engine in-process. Allocates nothing, writes nothing."""
    from registry_bridge.engine import import_engine

    engine = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)
    loader, gates = engine["loader"], engine["gates"]
    registry = loader.load_registry()
    registry = {k: dict(v) for k, v in registry.items()}
    for sid, source in (submission.proposed_sources or {}).items():
        registry["sources"][f"{sid}.json"] = {k: v for k, v in source.items() if not k.startswith("_")}
    for rid, relation in (submission.proposed_relations or {}).items():
        registry["relations"][f"{rid}.json"] = {k: v for k, v in relation.items() if not k.startswith("_") and k != "evidence"}
    record = _resolved_record(submission, allocate=False)
    evaluation = gates.evaluate_object(record, registry, loader.load_schemas(), loader.load_taxonomies())
    return {"decision_preview": evaluation.decision,
            "gates": {k: {"result": g.result, "details": g.details} for k, g in evaluation.gates.items()},
            "note": "Preview only. The authoritative decision is issued by the isolated engine against the pinned registry."}


def _resolved_record(submission: Submission, allocate: bool) -> dict:
    """Return the draft with placeholders resolved to reserved identifiers (or left as placeholders for preview)."""
    from registry_bridge import allocation as bridge_allocation

    record = copy.deepcopy(submission.draft)
    record.pop("_abstract_hint", None)
    for key in list(record):
        if key.startswith("_"):
            record.pop(key)
    record["authority"] = {"tier": "tier-2"}
    if submission.intended_object_id:
        record["object_id"] = submission.intended_object_id
    elif not record.get("object_id") or record.get("object_id") == PLACEHOLDER_OBJECT:
        if allocate:
            record["object_id"] = bridge_allocation.reserve_identifier("SR-OBJ", str(submission.id), purpose="new research object family")
        else:
            record["object_id"] = record.get("object_id") or "SR-OBJ-000000"
    mapping = {}
    for placeholder in list(submission.proposed_sources or {}):
        if PLACEHOLDER_RE.match(placeholder):
            mapping[placeholder] = (bridge_allocation.reserve_identifier("SRC", f"{submission.id}:{placeholder}", purpose="new source record")
                                    if allocate else placeholder)
    for placeholder in list(submission.proposed_relations or {}):
        if PLACEHOLDER_RE.match(placeholder):
            mapping[placeholder] = (bridge_allocation.reserve_identifier("REL", f"{submission.id}:{placeholder}", purpose="new relation record")
                                    if allocate else placeholder)
    record["source_ids"] = [mapping.get(s, s) for s in record.get("source_ids") or []]
    record["relations"] = [mapping.get(r, r) for r in record.get("relations") or []]
    record["_mapping"] = mapping
    return record


def _apply_version_resolution(submission: Submission, resolution: str, actor) -> None:
    """The researcher's statement of the governing version resolves automatic ambiguity (a researcher statement, recorded as such).

    Ambiguity the researcher declares unresolvable in the source form (``ambiguous_version``) is left in place and still triggers review.
    """
    sources = dict(submission.proposed_sources or {})
    stated = sorted({m.group(1) for m in preparation.VERSION_RE.finditer(resolution)})
    changed = False
    for record in sources.values():
        auto = record.get("_ambiguous_version")
        if auto and auto == (submission.draft or {}).get("_version_ambiguity"):
            record.pop("_ambiguous_version", None)
            if len(stated) == 1:
                record["version"] = stated[0]
            record["notes"] = (record.get("notes", "").strip() + " " if record.get("notes") else "") + \
                f"Governing version stated by the submitting researcher: {resolution.strip()}"
            changed = True
    if changed:
        submission.proposed_sources = sources
        submission.save(update_fields=["proposed_sources", "updated_at"])
        FieldEvidence.objects.create(submission=submission, field_path="source_ids", origin="researcher-statement",
                                     locator="governing version stated on the submit page", value_preview=resolution[:500], uncertain=False,
                                     processing={"confirmed_by": str(actor.uuid)})


def _frozen_proposals(submission: Submission, mapping: dict, object_id: str) -> dict:
    sources, relations = {}, {}
    for placeholder, source in (submission.proposed_sources or {}).items():
        sid = mapping.get(placeholder, placeholder)
        rec = copy.deepcopy(source)
        rec["source_id"] = sid
        sources[sid] = rec
    for placeholder, relation in (submission.proposed_relations or {}).items():
        rid = mapping.get(placeholder, placeholder)
        rec = copy.deepcopy(relation)
        rec["relation_id"] = rid
        evidence = (rec.pop("evidence", "") or rec.get("_evidence") or "").strip()
        if evidence:
            rec["_evidence"] = evidence
            rec["notes"] = (f"{rec.get('notes', '').strip()} " if rec.get("notes") else "") + f"Evidence stated by the submitter: {evidence}"
        for endpoint in ("from_id", "to_id"):
            value = rec.get(endpoint)
            if value in (PLACEHOLDER_OBJECT, "SR-OBJ-000000"):
                rec[endpoint] = object_id
            rec[endpoint] = mapping.get(rec.get(endpoint), rec.get(endpoint))
        rec.setdefault("declared", timezone.now().astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        relations[rid] = rec
    return {"authors": {}, "sources": sources, "relations": relations}


def confirm_and_submit(submission: Submission, actor, *, publish_files: bool, acknowledged: bool,
                       expected_version: int) -> SubmissionRevision:
    """Freeze the confirmed record as an immutable revision, reserve identifiers, and queue evaluation."""
    if not submission.can_edit(actor):
        raise PermissionError("not permitted")
    if not acknowledged:
        raise SubmissionError("confirm which metadata and receipts become public before submitting")
    if not actor.author_id:
        raise SubmissionError("your public author identity is still being registered; submit once your AuthorID is assigned")
    from accounts.models import AuthorBinding

    binding_state = AuthorBinding.objects.filter(account=actor).values_list("state", flat=True).first()
    if binding_state not in (AuthorBinding.REGISTERED, AuthorBinding.LINKED):
        raise SubmissionError(f"your AuthorID {actor.author_id} is reserved and is being published to the public registry; "
                              "you can keep editing this draft and submit once registration completes (see your profile for status)")
    if not submission.editable:
        raise SubmissionError("this submission is not in an editable state")
    with transaction.atomic():
        current = Submission.objects.select_for_update().get(id=submission.id)
        if current.draft_version != expected_version:
            raise StaleDraft("the draft changed in another tab; reload and review before submitting")
        hints = {k: v for k, v in (current.draft or {}).items() if k.startswith("_")}
        findings = hints.get("_duplicate_findings") or []
        if any(f["kind"] == "possible_duplicate_object" for f in findings) and not hints.get("_duplicate_resolution"):
            raise SubmissionError("a possible duplicate object was found; state whether this is a revision of it or a distinct study before submitting")
        if hints.get("_version_ambiguity") and not hints.get("_version_resolution"):
            raise SubmissionError("more than one manuscript version was found; state which version governs before submitting")
        if hints.get("_version_resolution"):
            _apply_version_resolution(current, hints["_version_resolution"], actor)
        resolution = hints.get("_duplicate_resolution") or ""
        if resolution.startswith("revision_of:"):
            target = resolution.split(":", 1)[1]
            if not OBJECT_ID_RE.match(target):
                raise SubmissionError("the revision target must be an existing SR-OBJ identifier")
            current.intended_object_id = target
        record = _resolved_record(current, allocate=True)
        mapping = record.pop("_mapping")
        if not record.get("authors"):
            record["authors"] = [actor.author_id]
        record.setdefault("date", timezone.now().astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        previous = current.latest_revision
        number = (previous.number + 1) if previous else 1
        revision = SubmissionRevision(submission=current, number=number, record=record,
                                      proposed_records=_frozen_proposals(current, mapping, record["object_id"]),
                                      confirmed_by=actor, repairs=previous, publish_files=publish_files,
                                      public_metadata_acknowledged=True,
                                      source_file_hashes=[{"display_name": u.filename, "sha256": u.sha256, "bytes": u.byte_count,
                                                           "media_type": u.media_type or None, "version_reference": None,
                                                           "public": publish_files and u.visibility == Upload.PUBLIC}
                                                          for u in current.uploads.filter(state=Upload.COMPLETE, parent__isnull=True)])
        revision.save()
        current.uploads.filter(revision__isnull=True).update(revision=revision)
        FieldEvidence.objects.filter(submission=current, revision__isnull=True).update(revision=revision)
        current.publish_files = publish_files
        current.draft = {**record, **hints}
        current.draft_version += 1
        current.save(update_fields=["publish_files", "draft", "draft_version", "intended_object_id", "updated_at"])
        wf.transition(current, wf.SUBMITTED, actor=actor, actor_label="researcher", revision=revision,
                      operation_key=revision.operation_key, reason=f"revision {number} confirmed ({revision.content_hash[:19]})")
        enqueue(EVALUATE, {"revision": revision.pk}, operation_key=revision.operation_key, submission=current)
    return revision


@handler(EVALUATE)
def evaluate(job) -> None:
    from registry_bridge.evaluation import evaluate_revision

    revision = SubmissionRevision.objects.select_related("submission__owner").get(pk=job.payload["revision"])
    review_id = job.payload.get("review")
    review = ReviewCase.objects.filter(pk=review_id).first() if review_id else None
    attempt_key = job.payload.get("attempt_key")
    evaluate_revision(revision, review=review, attempt_key=uuid.UUID(attempt_key) if attempt_key else None)


def requeue_evaluation(revision: SubmissionRevision, reason: str, review: ReviewCase = None) -> None:
    """Queue a distinct evaluation attempt; the earlier attempt and its receipt stay in history."""
    attempt_key = uuid.uuid4()
    submission = revision.submission
    enqueue(EVALUATE, {"revision": revision.pk, "attempt_key": str(attempt_key), "review": review.pk if review else None},
            operation_key=attempt_key, submission=submission)
    record_event("evaluation.requeued", submission=submission, revision=revision, operation_key=attempt_key, reason=reason)


# --------------------------------------------------------------------------- repair & revision

def start_repair(submission: Submission, actor) -> Submission:
    """Open a new editable draft from the frozen revision, reusing its evidence and naming the fields the receipt flagged."""
    if not submission.can_edit(actor):
        raise PermissionError("not permitted")
    if submission.workflow_state not in (wf.NEEDS_REPAIR, wf.NOT_ADMITTED, wf.REGISTERED):
        raise SubmissionError("repair or revision can start only after a formal decision or registration")
    latest = submission.latest_revision
    from registry_bridge.models import EvaluationAttempt

    attempt = EvaluationAttempt.objects.filter(revision=latest).exclude(receipt_id="").order_by("-recorded_at").first() if latest else None
    focus = preparation.repair_focus(attempt.receipt) if attempt and attempt.decision != "ACCEPTED" else []
    with transaction.atomic():
        current = Submission.objects.select_for_update().get(id=submission.id)
        hints = {k: v for k, v in (current.draft or {}).items() if k.startswith("_")}
        draft = copy.deepcopy(latest.record) if latest else copy.deepcopy({k: v for k, v in current.draft.items() if not k.startswith("_")})
        if current.workflow_state == wf.REGISTERED and draft.get("version"):
            major, minor, patch = (int(x) for x in draft["version"].split("."))
            draft["version"] = f"{major}.{minor}.{patch + 1}"
            draft.pop("date", None)
        current.draft = {**draft, **hints}
        current.draft_version += 1
        note = {"kind": "repair", "at": timezone.now().isoformat(), "from_revision": latest.number if latest else None,
                "receipt_id": attempt.receipt_id if attempt else None, "decision": attempt.decision if attempt else None,
                "affected_fields": focus,
                "exact_repair": (attempt.receipt.get("exact_repair_required") or [attempt.receipt.get("established_violation")]) if attempt else []}
        current.processing_notes = list(current.processing_notes or []) + [note]
        current.save(update_fields=["draft", "draft_version", "processing_notes", "updated_at"])
        # Reuse the frozen revision's evidence so nothing already extracted or confirmed is asked again.
        FieldEvidence.objects.filter(submission=current, revision__isnull=True).delete()
        if latest:
            for row in FieldEvidence.objects.filter(revision=latest):
                FieldEvidence.objects.create(submission=current, field_path=row.field_path, origin=row.origin, locator=row.locator,
                                             upload=row.upload, value_preview=row.value_preview, uncertain=row.uncertain,
                                             processing=dict(row.processing, reused_from_revision=latest.number))
        wf.transition(current, wf.DRAFT, actor=actor, actor_label="researcher", revision=latest,
                      reason="researcher started a repair / new revision; the earlier revision remains frozen",
                      payload={"affected_fields": focus})
    return current


# --------------------------------------------------------------------------- questions & review

def ask_question(author, text: str, *, submission: Submission = None, route: str = "submission", source_pointer: str = "") -> Question:
    if submission is not None and not submission.can_view(author):
        raise PermissionError("not permitted")
    question = Question.objects.create(author=author, submission=submission, revision=submission.latest_revision if submission else None,
                                       route=route, text=text.strip()[:5000], source_pointer=source_pointer.strip()[:500])
    record_event("question.asked", actor=author, actor_label="researcher", submission=submission, account=author,
                 payload={"route": route})
    return question


def respond(question: Question, author, text: str, resolve: bool = False, resolution_evidence: str = "") -> Response:
    if question.submission is not None and not question.submission.can_view(author):
        raise PermissionError("not permitted")
    response = Response.objects.create(question=question, author=author, text=text.strip()[:5000])
    if resolve:
        question.resolved = True
        question.resolution_evidence = resolution_evidence.strip()[:2000]
        question.save(update_fields=["resolved", "resolution_evidence"])
    return response


def resolve_review_case(case: ReviewCase, reviewer, resolution: str, return_to_researcher: bool = False) -> ReviewCase:
    """A reviewer resolves a documented question or repairs documented inputs; there is no 'accept anyway'."""
    if not reviewer.is_reviewer:
        raise PermissionError("only reviewers resolve review cases")
    submission = case.submission
    if not submission.can_view(reviewer):
        raise PermissionError("reviewer is not assigned to this submission")
    with transaction.atomic():
        case.state = ReviewCase.RETURNED if return_to_researcher else ReviewCase.RESOLVED
        case.resolution = resolution.strip()[:5000]
        case.resolved_by = reviewer
        case.resolved_at = timezone.now()
        case.save()
        record_event("review.resolved", actor=reviewer, actor_label="reviewer", submission=submission, revision=case.revision,
                     payload={"condition": case.condition, "returned": return_to_researcher})
        if return_to_researcher:
            wf.transition(submission, wf.DRAFT, actor=reviewer, actor_label="reviewer", revision=case.revision,
                          reason=f"returned to researcher: {case.condition}")
        elif not submission.review_cases.filter(revision=case.revision, state=ReviewCase.OPEN).exists():
            requeue_evaluation(case.revision, reason=f"review resolved: {case.condition}", review=case)
    return case
