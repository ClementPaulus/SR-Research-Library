"""Reviewer/maintainer routes: review queue, case resolution, identity claims, pending registrations."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.views.decorators.http import require_POST

from accounts.models import IdentityClaim, ReviewAssignment
from accounts.services import decide_identity_claim
from core.models import Job
from registry_bridge.models import Publication

from . import services
from .models import ReviewCase, Submission


def _reviewer(user) -> bool:
    return user.is_authenticated and user.is_reviewer


reviewer_required = user_passes_test(_reviewer, login_url="/login")


@login_required
@reviewer_required
def queue(request):
    user = request.user
    if user.is_administrator:
        cases = ReviewCase.objects.filter(state=ReviewCase.OPEN).select_related("submission", "revision")
    else:
        assigned = ReviewAssignment.objects.filter(reviewer=user).values_list("submission_id", flat=True)
        cases = ReviewCase.objects.filter(state=ReviewCase.OPEN, submission_id__in=assigned).select_related("submission", "revision")
    claims = IdentityClaim.objects.filter(state=IdentityClaim.REQUESTED) if user.is_administrator else IdentityClaim.objects.none()
    blocked = Publication.objects.filter(status__in=[Publication.BLOCKED, Publication.AWAITING_REVIEW, Publication.CHECKS_PENDING]).order_by("-updated_at") if user.is_administrator else Publication.objects.none()
    dead_jobs = Job.objects.filter(state=Job.DEAD).order_by("-updated_at")[:50] if user.is_administrator else Job.objects.none()
    return render(request, "review/queue.html", {"cases": cases, "claims": claims, "blocked": blocked, "dead_jobs": dead_jobs})


@login_required
@reviewer_required
def case(request, case_id):
    review_case = get_object_or_404(ReviewCase, pk=case_id)
    submission = review_case.submission
    if not submission.can_view(request.user):
        messages.error(request, "You are not assigned to this submission.")
        return redirect("review:queue")
    if request.method == "POST":
        try:
            services.resolve_review_case(review_case, request.user, request.POST.get("resolution", ""),
                                         return_to_researcher=request.POST.get("action") == "return")
        except PermissionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Review case recorded. There is no 'accept anyway' control; the engine decides on re-evaluation.")
        return redirect("review:queue")
    revision = review_case.revision
    return render(request, "review/case.html", {"case": review_case, "s": submission, "revision": revision})


@login_required
@reviewer_required
@require_POST
def decide_claim(request, claim_id):
    if not request.user.is_administrator:
        messages.error(request, "Only administrators decide identity claims.")
        return redirect("review:queue")
    claim = get_object_or_404(IdentityClaim, pk=claim_id, state=IdentityClaim.REQUESTED)
    verified = request.POST.get("decision") == "verify"
    decide_identity_claim(claim, request.user, verified, request.POST.get("notes", ""))
    messages.success(request, f"Claim {'verified and linked' if verified else 'denied'}.")
    return redirect("review:queue")


@login_required
@reviewer_required
@require_POST
def assign(request, submission_id):
    if not request.user.is_administrator:
        messages.error(request, "Only administrators assign reviewers.")
        return redirect("review:queue")
    submission = get_object_or_404(Submission, id=submission_id)
    from accounts.models import Account

    reviewer = get_object_or_404(Account, email=request.POST.get("email", ""))
    ReviewAssignment.objects.get_or_create(reviewer=reviewer, submission=submission,
                                           defaults={"assigned_by": request.user, "condition": request.POST.get("condition", "review")[:120]})
    messages.success(request, f"{reviewer.display_name} can now inspect this submission.")
    return redirect("review:queue")


@login_required
@reviewer_required
@require_POST
def retry_publication(request, operation_key):
    if not request.user.is_administrator:
        return redirect("review:queue")
    publication = get_object_or_404(Publication, operation_key=operation_key)
    from registry_bridge.publication import publish_job_key

    job = Job.objects.filter(operation_key=publish_job_key(publication.operation_key)).first()
    if job:
        from django.utils import timezone

        from core.models import dispatch

        Job.objects.filter(pk=job.pk).update(state=Job.QUEUED, next_retry_at=timezone.now(), dispatched_at=None, last_safe_error="")
        if publication.status == Publication.BLOCKED:
            Publication.objects.filter(pk=publication.pk).update(status=Publication.PR_OPEN if publication.pr_number else Publication.QUEUED)
        dispatch(job.operation_key)
        messages.info(request, "Publication re-queued; it resumes from the observable Git state.")
    return redirect("review:queue")


app_name = "review"
urlpatterns = [
    path("", queue, name="queue"),
    path("cases/<int:case_id>", case, name="case"),
    path("claims/<int:claim_id>/decide", decide_claim, name="decide_claim"),
    path("submissions/<uuid:submission_id>/assign", assign, name="assign"),
    path("publications/<uuid:operation_key>/retry", retry_publication, name="retry_publication"),
]
