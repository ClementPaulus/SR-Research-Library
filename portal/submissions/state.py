"""Workflow state machine for submissions.

Operational workflow state is stored separately from the nullable research
admission decision (which only the engine sets) and from the nullable
publication identity (which only a verified Git commit sets).
"""

from __future__ import annotations

from core.models import record_event

DRAFT = "draft"
UPLOADING = "uploading"
PREPARING = "preparing"
NEEDS_REVIEW = "needs_your_review"
SUBMITTED = "submitted"
EVALUATING = "evaluating"
REVIEW_NEEDED = "review_needed"
NEEDS_REPAIR = "needs_repair"
NOT_ADMITTED = "not_admitted"
ACCEPTED_PENDING = "accepted_registration_pending"
REGISTERED = "registered"
PROCESSING_UNAVAILABLE = "processing_unavailable"

LABELS = {
    DRAFT: "Draft",
    UPLOADING: "Uploading",
    PREPARING: "Preparing",
    NEEDS_REVIEW: "Needs your review",
    SUBMITTED: "Submitted",
    EVALUATING: "Evaluating",
    REVIEW_NEEDED: "Review needed",
    NEEDS_REPAIR: "Needs repair",
    NOT_ADMITTED: "Not admitted",
    ACCEPTED_PENDING: "Accepted — registration pending",
    REGISTERED: "Registered",
    PROCESSING_UNAVAILABLE: "Processing unavailable",
}

MEANINGS = {
    DRAFT: "Editable saved work; no formal decision.",
    UPLOADING: "Files are being saved; no formal decision.",
    PREPARING: "Background preparation is underway; no formal decision.",
    NEEDS_REVIEW: "Extracted or proposed fields need your confirmation before formal submission.",
    SUBMITTED: "An immutable confirmed revision has been received.",
    EVALUATING: "The pinned admission engine is running against your confirmed revision.",
    REVIEW_NEEDED: "A stated source, identity, relation, or policy question requires human resolution. Controversy or disagreement is never a trigger.",
    NEEDS_REPAIR: "Formal decision RETURNED_FOR_REPAIR; the receipt explains the exact repair. Your files and earlier version are preserved.",
    NOT_ADMITTED: "Formal decision REJECTED; the receipt identifies the contract violation and the resubmission route.",
    ACCEPTED_PENDING: "Your submission passed the admission checks. Registration in the public library is in progress.",
    REGISTERED: "Your work is registered. The exact accepted revision and receipt are verified on the default branch.",
    PROCESSING_UNAVAILABLE: "A service, parser, or storage problem occurred. Any earlier decision remains unchanged.",
}

EDITABLE = {DRAFT, NEEDS_REVIEW}
TERMINAL_DECISIONS = {NEEDS_REPAIR, NOT_ADMITTED, ACCEPTED_PENDING, REGISTERED}

TRANSITIONS = {
    DRAFT: {UPLOADING, PREPARING, NEEDS_REVIEW, SUBMITTED},
    UPLOADING: {PREPARING, DRAFT, PROCESSING_UNAVAILABLE},
    PREPARING: {NEEDS_REVIEW, DRAFT, PROCESSING_UNAVAILABLE},
    NEEDS_REVIEW: {DRAFT, SUBMITTED, PREPARING},
    SUBMITTED: {EVALUATING, REVIEW_NEEDED, PROCESSING_UNAVAILABLE},
    EVALUATING: {REVIEW_NEEDED, NEEDS_REPAIR, NOT_ADMITTED, ACCEPTED_PENDING, NEEDS_REVIEW, PROCESSING_UNAVAILABLE},
    REVIEW_NEEDED: {EVALUATING, DRAFT, PROCESSING_UNAVAILABLE},
    NEEDS_REPAIR: {DRAFT, EVALUATING},
    NOT_ADMITTED: {DRAFT, EVALUATING},
    ACCEPTED_PENDING: {REGISTERED, PROCESSING_UNAVAILABLE, EVALUATING},
    PROCESSING_UNAVAILABLE: {DRAFT, PREPARING, SUBMITTED, EVALUATING, ACCEPTED_PENDING, NEEDS_REVIEW},
    REGISTERED: {DRAFT},  # a new revision of a registered object starts a new draft
}


class IllegalTransition(RuntimeError):
    pass


def transition(submission, new_state: str, *, actor=None, actor_label: str = "system", reason: str = "",
               revision=None, operation_key=None, payload: dict = None, save: bool = True):
    previous = submission.workflow_state
    if new_state == previous:
        return submission
    if new_state not in TRANSITIONS.get(previous, set()):
        raise IllegalTransition(f"{previous} -> {new_state} is not a permitted transition")
    submission.workflow_state = new_state
    if save:
        submission.save(update_fields=["workflow_state", "updated_at"])
    record_event("submission.transition", actor=actor, actor_label=actor_label, submission=submission,
                 revision=revision, previous_state=previous, new_state=new_state, operation_key=operation_key,
                 reason=reason, payload=payload or {}, account=submission.owner)
    return submission
