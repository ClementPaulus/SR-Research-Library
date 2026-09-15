"""Workspace views: submissions list, upload, guided editor, confirm, status, repair, questions, export, downloads."""

from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import AuthorBinding
from core.models import Event
from registry_bridge.models import EvaluationAttempt, Publication

from . import services, state as wf
from .export import build_handoff
from .forms import DraftForm, ProposedRelationForm, ProposedSourceForm, taxonomies
from .models import FieldEvidence, Question, ReviewCase, Submission, SubmissionRevision, Upload


def _owned(request, submission_id, edit: bool = False) -> Submission:
    submission = get_object_or_404(Submission, id=submission_id)
    if edit and not submission.can_edit(request.user):
        raise Http404
    if not edit and not submission.can_view(request.user):
        raise Http404  # do not reveal existence to unauthorized accounts
    return submission


@login_required
def workspace(request):
    binding = AuthorBinding.objects.filter(account=request.user).first()
    mine = Submission.objects.filter(owner=request.user)
    shared = request.user.shared_submissions.all()
    requested = [s for s in mine if s.workflow_state in (wf.NEEDS_REVIEW, wf.NEEDS_REPAIR, wf.NOT_ADMITTED, wf.PROCESSING_UNAVAILABLE)]
    registered = [s for s in mine if s.workflow_state == wf.REGISTERED]
    return render(request, "submissions/workspace.html", {
        "binding": binding, "mine": mine, "shared": shared, "requested": requested, "registered": registered,
        "verified": request.user.verified,
    })


@login_required
def new_submission(request):
    if request.method == "POST":
        label = request.POST.get("label", "")
        reference = request.POST.get("source_reference", "").strip()
        intended = request.POST.get("intended_object_id", "").strip().upper()
        files = request.FILES.getlist("files")
        if not files and not reference:
            messages.error(request, "Upload at least one file or supply a DOI, archive reference, or source URL.")
            return render(request, "submissions/new.html", {"max_file_mib": settings.PORTAL_UPLOAD_MAX_FILE_BYTES // (1024 * 1024)})
        try:
            submission = services.create_submission(request.user, label=label, source_reference=reference, intended_object_id=intended)
            for f in files:
                services.register_upload(submission, request.user, f)
            if not files:
                services.start_preparation_from_reference(submission, request.user)
        except (services.SubmissionError, PermissionError) as exc:
            messages.error(request, str(exc))
            return render(request, "submissions/new.html", {"max_file_mib": settings.PORTAL_UPLOAD_MAX_FILE_BYTES // (1024 * 1024)})
        messages.success(request, "Your files are saved. We’re preparing a draft for your review.")
        return redirect("submissions:detail", submission.id)
    return render(request, "submissions/new.html", {"max_file_mib": settings.PORTAL_UPLOAD_MAX_FILE_BYTES // (1024 * 1024),
                                                    "max_submission_mib": settings.PORTAL_UPLOAD_MAX_SUBMISSION_BYTES // (1024 * 1024)})


JOURNEY = [
    ("uploaded", "Uploaded", {wf.DRAFT, wf.UPLOADING}),
    ("preparing", "Preparing", {wf.PREPARING, wf.PROCESSING_UNAVAILABLE}),
    ("review", "Needs your review", {wf.NEEDS_REVIEW}),
    ("submitted", "Submitted & evaluating", {wf.SUBMITTED, wf.EVALUATING, wf.REVIEW_NEEDED}),
    ("decision", "Decision", {wf.NEEDS_REPAIR, wf.NOT_ADMITTED, wf.ACCEPTED_PENDING}),
    ("registered", "Registered", {wf.REGISTERED}),
]


def _journey(submission: Submission) -> list:
    current_index = next((i for i, (_, _, states) in enumerate(JOURNEY) if submission.workflow_state in states), 0)
    rows = []
    for index, (key, label, states) in enumerate(JOURNEY):
        status = "done" if index < current_index else ("current" if index == current_index else "todo")
        if key == "decision" and index == current_index:
            label = {wf.NEEDS_REPAIR: "Needs repair", wf.NOT_ADMITTED: "Not admitted", wf.ACCEPTED_PENDING: "Accepted — awaiting registration"}.get(
                submission.workflow_state, label)
        rows.append({"key": key, "label": label, "status": status})
    return rows


@login_required
def detail(request, submission_id):
    submission = _owned(request, submission_id)
    revisions = submission.revisions.order_by("number")
    attempts = EvaluationAttempt.objects.filter(revision__submission=submission).order_by("recorded_at")
    publications = Publication.objects.filter(attempt__in=attempts).order_by("created_at")
    events = Event.objects.filter(submission_id=submission.id).order_by("-occurred_at")[:60]
    questions = submission.questions.prefetch_related("responses").order_by("created_at")
    review_cases = submission.review_cases.order_by("created_at")
    uploads = submission.uploads.filter(parent__isnull=True).order_by("created_at")
    preparation_note = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "preparation"), {})
    repair_note = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "repair"), None)
    dependency_note = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "dependency"), None)
    assessment = services.assessment_for(submission) if submission.editable else None
    registered_object = submission.draft.get("object_id") if submission.workflow_state == wf.REGISTERED else None
    accepted_attempt = next((a for a in reversed(list(attempts)) if a.decision == "ACCEPTED"), None)
    return render(request, "submissions/detail.html", {
        "s": submission, "revisions": revisions, "attempts": attempts, "publications": publications, "events": events,
        "questions": questions, "review_cases": review_cases, "uploads": uploads, "notes": preparation_note,
        "repair_note": repair_note, "dependency_note": dependency_note, "assessment": assessment,
        "journey": _journey(submission), "registered_object": registered_object, "accepted_attempt": accepted_attempt,
        "can_edit": submission.can_edit(request.user), "labels": wf.LABELS, "meanings": wf.MEANINGS,
        "owner_author_id": submission.owner.author_id,
    })


@login_required
def status_json(request, submission_id):
    submission = _owned(request, submission_id)
    note = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "preparation"), {})
    return JsonResponse({"state": submission.workflow_state, "label": submission.state_label, "meaning": submission.state_meaning,
                         "draft_version": submission.draft_version, "updated_at": submission.updated_at.isoformat(),
                         "steps": note.get("steps", []), "journey": _journey(submission)})


@login_required
def upload(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    if request.method != "POST":
        return redirect("submissions:detail", submission.id)
    try:
        for f in request.FILES.getlist("files"):
            services.register_upload(submission, request.user, f, client_sha256=request.POST.get("client_sha256", ""))
    except (services.SubmissionError, PermissionError) as exc:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"error": "upload_refused", "message": str(exc)}, status=422)
        messages.error(request, str(exc))
        return redirect("submissions:detail", submission.id)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"status": "saved", "state": submission.workflow_state})
    messages.success(request, "Your files are saved. We’re preparing a draft for your review.")
    return redirect("submissions:detail", submission.id)


@login_required
def edit(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    if not submission.editable:
        messages.info(request, "This revision is frozen. Start a repair or a new revision to edit.")
        return redirect("submissions:detail", submission.id)
    evidence = FieldEvidence.objects.filter(submission=submission, revision__isnull=True).select_related("upload")
    path_to_form = {v: k for k, v in _FORM_TO_PATH.items()}
    evidence_by_field: dict = {}
    for e in evidence:
        evidence_by_field.setdefault(path_to_form.get(e.field_path, e.field_path), []).append(e)
    notes = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "preparation"), {})
    repair_note = next((n for n in reversed(submission.processing_notes or []) if n.get("kind") == "repair"), None)
    if request.method == "POST":
        form = DraftForm(request.POST, taxonomies=taxonomies())
        if form.is_valid():
            try:
                draft, sources, relations = form.to_record(submission)
                before = services.assessment_for(submission)
                services.save_draft(submission, request.user, draft, sources, relations,
                                    expected_version=int(request.POST.get("draft_version", "0")),
                                    confirm_fields=before["needs_confirmation"])
            except services.StaleDraft as exc:
                messages.error(request, f"{exc}. Your changes were not saved; the latest saved version is shown below.")
                return redirect("submissions:edit", submission.id)
            except (services.SubmissionError, PermissionError) as exc:
                messages.error(request, str(exc))
            else:
                if request.POST.get("action") == "preview":
                    return redirect("submissions:confirm", submission.id)
                messages.success(request, "Draft saved. Extracted values you kept are now recorded as confirmed.")
                return redirect("submissions:edit", submission.id)
    else:
        form = DraftForm.from_submission(submission, taxonomies=taxonomies())
    assessment = services.assessment_for(submission)
    status_by_field = {p: "ready" for p in assessment["ready"]}
    status_by_field.update({p: "confirm" for p in assessment["needs_confirmation"]})
    status_by_field.update({p: "missing" for p in assessment["missing"]})
    focus = set((repair_note or {}).get("affected_fields") or [])
    field_status = {}
    for name in form.fields:
        path = _form_field_to_path(name)
        field_status[name] = {"status": status_by_field.get(path, ""), "repair": path in focus or name in focus}
    return render(request, "submissions/edit.html", {
        "s": submission, "form": form, "evidence_by_field": evidence_by_field, "notes": notes, "repair_note": repair_note,
        "assessment": assessment, "field_status": field_status,
        "sources": submission.proposed_sources or {}, "relations": submission.proposed_relations or {},
        "source_form": ProposedSourceForm(prefix="src"), "relation_form": ProposedRelationForm(prefix="rel"), "raw_json": json.dumps(submission.draft, indent=2, ensure_ascii=False),
        "abstract_hint": submission.draft.get("_abstract_hint"), "source_authors_hint": submission.draft.get("_source_authors_hint"),
        "duplicates": submission.draft.get("_duplicate_findings") or [], "version_ambiguity": submission.draft.get("_version_ambiguity"),
        "source_rows": [(k, v, v.get("_ambiguous_version"), v.get("_source_type_unconfirmed")) for k, v in (submission.proposed_sources or {}).items()],
        "relation_rows": [(k, v, v.get("evidence") or v.get("_evidence") or "") for k, v in (submission.proposed_relations or {}).items()],
    })


_FORM_TO_PATH = {"tier2_class_primary": "tier2_class.primary", "domain_primary": "domain.primary",
                 "structural_focus_primary": "structural_focus.primary", "evidence_mode_primary": "evidence_mode.primary"}


def _form_field_to_path(name: str) -> str:
    return _FORM_TO_PATH.get(name, name)


@login_required
@require_POST
def autosave(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    try:
        payload = json.loads(request.body or b"{}")
        if "form" in payload:
            form = DraftForm(payload["form"], taxonomies=taxonomies())
            if not form.is_valid():
                return JsonResponse({"error": "invalid", "message": "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items())}, status=422)
            draft, sources, relations = form.to_record(submission)
        else:
            draft, sources, relations = payload.get("draft") or {}, payload.get("proposed_sources") or submission.proposed_sources, \
                payload.get("proposed_relations") or submission.proposed_relations
        services.save_draft(submission, request.user, draft, sources, relations, expected_version=int(payload.get("draft_version", 0)))
    except services.StaleDraft as exc:
        submission.refresh_from_db()
        return JsonResponse({"error": "stale_draft", "message": str(exc), "draft_version": submission.draft_version}, status=409)
    except (services.SubmissionError, PermissionError, ValueError) as exc:
        return JsonResponse({"error": "invalid", "message": str(exc)}, status=422)
    submission.refresh_from_db()
    return JsonResponse({"status": "saved", "draft_version": submission.draft_version})


@login_required
@require_POST
def add_source(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    form = ProposedSourceForm(request.POST, prefix="src")
    if not form.is_valid():
        messages.error(request, "Source could not be added: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items()))
        return redirect("submissions:edit", submission.id)
    placeholder, record = form.to_record(submission)
    sources = dict(submission.proposed_sources or {})
    sources[placeholder] = record
    draft = dict(submission.draft)
    draft.setdefault("source_ids", [])
    if placeholder not in draft["source_ids"]:
        draft["source_ids"] = list(draft["source_ids"]) + [placeholder]
    try:
        services.save_draft(submission, request.user, draft, sources, submission.proposed_relations,
                            expected_version=int(request.POST.get("draft_version", "0")))
    except services.StaleDraft as exc:
        messages.error(request, str(exc))
    return redirect("submissions:edit", submission.id)


@login_required
@require_POST
def add_relation(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    form = ProposedRelationForm(request.POST, prefix="rel")
    if not form.is_valid():
        messages.error(request, "Relation could not be added: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items()))
        return redirect("submissions:edit", submission.id)
    placeholder, record = form.to_record(submission)
    relations = dict(submission.proposed_relations or {})
    relations[placeholder] = record
    draft = dict(submission.draft)
    draft["relations"] = list(draft.get("relations") or []) + [placeholder]
    try:
        services.save_draft(submission, request.user, draft, submission.proposed_sources, relations,
                            expected_version=int(request.POST.get("draft_version", "0")))
    except services.StaleDraft as exc:
        messages.error(request, str(exc))
    return redirect("submissions:edit", submission.id)


@login_required
def confirm(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    if not submission.editable:
        return redirect("submissions:detail", submission.id)
    if request.method == "POST":
        hints = {}
        if request.POST.get("duplicate_resolution"):
            value = request.POST["duplicate_resolution"]
            hints["_duplicate_resolution"] = value if value == "distinct" else f"revision_of:{request.POST.get('revision_target', '').strip().upper()}"
        if request.POST.get("version_resolution"):
            hints["_version_resolution"] = request.POST["version_resolution"].strip()[:500]
        source_type = request.POST.get("source_type_confirmation")
        try:
            expected = int(request.POST.get("draft_version", "0"))
            if hints or source_type:
                sources = dict(submission.proposed_sources or {})
                if source_type in ("corpus-native", "external", "historical", "dataset"):
                    for record in sources.values():
                        if record.pop("_source_type_unconfirmed", None):
                            record["source_type"] = source_type
                draft = {k: v for k, v in submission.draft.items()}
                draft.update(hints)
                services.save_draft(submission, request.user, draft, sources, submission.proposed_relations, expected_version=expected)
                submission.refresh_from_db()
                expected = submission.draft_version
            revision = services.confirm_and_submit(
                submission, request.user, publish_files=request.POST.get("publish_files") == "on",
                acknowledged=request.POST.get("acknowledge") == "on" and request.POST.get("acknowledge_claims") == "on",
                expected_version=expected)
        except (services.SubmissionError, services.StaleDraft, PermissionError) as exc:
            messages.error(request, str(exc))
            return redirect("submissions:confirm", submission.id)
        messages.success(request, f"Revision {revision.number} submitted to the public research library. Evaluation is running.")
        return redirect("submissions:detail", submission.id)
    preview = None
    try:
        preview = services.preflight(submission)
    except Exception as exc:  # noqa: BLE001 - preview must never block the page
        preview = {"error": f"Preview unavailable ({type(exc).__name__}); the authoritative evaluation still runs on submission."}
    assessment = services.assessment_for(submission)
    public_fields = ["title", "authors", "source_ids", "tier2_class", "domain", "structural_focus", "main_question", "claim_layers",
                     "evidence_mode", "provenance", "maturity", "version", "publication_state", "boundaries", "missingness", "next_burden"]
    uploads = submission.uploads.filter(parent__isnull=True, state=Upload.COMPLETE)
    claims_by_layer: dict = {}
    for claim in submission.draft.get("claim_layers") or []:
        if isinstance(claim, dict):
            claims_by_layer.setdefault(claim.get("layer", "?"), []).append(claim.get("claim", ""))
    duplicates = [f for f in (submission.draft.get("_duplicate_findings") or []) if f["kind"] == "possible_duplicate_object"]
    other_authors = [a for a in (submission.draft.get("authors") or []) if a != submission.owner.author_id]
    unconfirmed_source_types = [k for k, v in (submission.proposed_sources or {}).items() if v.get("_source_type_unconfirmed")]
    return render(request, "submissions/confirm.html", {
        "s": submission, "preview": preview, "public_fields": public_fields, "uploads": uploads, "assessment": assessment,
        "record_json": json.dumps({k: v for k, v in submission.draft.items() if not k.startswith("_")}, indent=2, ensure_ascii=False),
        "claims_by_layer": claims_by_layer, "duplicates": duplicates, "version_ambiguity": submission.draft.get("_version_ambiguity"),
        "duplicate_resolution": submission.draft.get("_duplicate_resolution"), "version_resolution": submission.draft.get("_version_resolution"),
        "other_authors": other_authors, "unconfirmed_source_types": unconfirmed_source_types,
    })


@login_required
@require_POST
def repair(request, submission_id):
    submission = _owned(request, submission_id, edit=True)
    try:
        services.start_repair(submission, request.user)
    except services.SubmissionError as exc:
        messages.error(request, str(exc))
        return redirect("submissions:detail", submission.id)
    messages.info(request, "A new editable draft was created from the frozen revision. Your files and earlier version are preserved.")
    return redirect("submissions:edit", submission.id)


@login_required
@require_POST
def ask(request, submission_id):
    submission = _owned(request, submission_id)
    text = request.POST.get("text", "").strip()
    if text:
        services.ask_question(request.user, text, submission=submission, source_pointer=request.POST.get("source_pointer", ""))
        messages.success(request, "Your question is recorded with the current revision attached.")
    return redirect("submissions:detail", submission.id)


@login_required
@require_POST
def respond(request, submission_id, question_id):
    submission = _owned(request, submission_id)
    question = get_object_or_404(Question, pk=question_id, submission=submission)
    text = request.POST.get("text", "").strip()
    if text:
        services.respond(question, request.user, text, resolve=request.POST.get("resolve") == "on",
                         resolution_evidence=request.POST.get("resolution_evidence", ""))
    return redirect("submissions:detail", submission.id)


@login_required
def export(request, submission_id, number):
    submission = _owned(request, submission_id)
    revision = get_object_or_404(SubmissionRevision, submission=submission, number=number)
    include_private = request.GET.get("scope") != "public" and submission.can_edit(request.user) or request.user.is_administrator
    if request.GET.get("scope") == "public":
        include_private = False
    payload = build_handoff(revision, include_private=include_private, requested_by=request.user)
    response = HttpResponse(payload, content_type="application/zip")
    scope = "owner" if include_private else "public"
    response["Content-Disposition"] = f'attachment; filename="handoff-{submission.id}-r{number}-{scope}.zip"'
    return response


@login_required
def download(request, submission_id, upload_id):
    submission = _owned(request, submission_id)
    upload = get_object_or_404(Upload, id=upload_id, submission=submission, state=Upload.COMPLETE)
    handle = default_storage.open(upload.storage_key, "rb")
    response = FileResponse(handle, content_type=upload.media_type or "application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{upload.filename.replace(chr(34), "")}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def contribute_question(request):
    """Ask a contribution question not tied to a submission (persistent private thread)."""
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        route = request.POST.get("route", "general")
        if text:
            services.ask_question(request.user, text, route=route if route in ("general", "source_suggestion", "relation_proposal") else "general",
                                  source_pointer=request.POST.get("source_pointer", ""))
            messages.success(request, "Recorded. Source-only suggestions and questions are never counted as your authored research.")
        return redirect("submissions:questions")
    threads = Question.objects.filter(author=request.user, submission__isnull=True).prefetch_related("responses").order_by("-created_at")
    return render(request, "submissions/questions.html", {"threads": threads})
