"""Protected publication sequence (§15): branch -> commit -> PR -> required check -> merge -> verify.

Idempotent per operation key. A worker crash at any step is recovered on the
next run from the observable Git state (existing branch, existing PR, merged
PR), never by creating a second object, receipt, or PR. Registered is set only
after the exact expected content is read back from the default branch.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import enqueue, record_event
from core.tasks import DeterministicFailure, RetryableError, handler

from . import allocation as bridge_allocation
from .github_app import GitHubRefused, GitHubUnavailable, client
from .models import Allocation, Publication
from .policy import filter_publishable

log = logging.getLogger("portal.publication")

PUBLISH = "registry_bridge.publish"
REFRESH_PROJECTION = "catalog.refresh_projection"


def publish_job_key(operation_key):
    """The outbox job for a publication has its own key, distinct from the operation that produced it."""
    import uuid

    return uuid.uuid5(uuid.NAMESPACE_URL, f"publish:{operation_key}")


def queue_publication(*, kind: str, operation_key, files: dict, reservations: list, expected: dict, summary: str,
                      account=None, attempt=None) -> Publication:
    files = dict(files)
    if kind == Publication.AUTHOR_REGISTRATION:
        # Author registrations carry their own ledger entries; admissions get theirs from the checkout.
        files.update(bridge_allocation.ledger_files_for(
            reservations, str(operation_key), purpose=summary,
            published_paths={value: f"registry/authors/{value}.json" for value in reservations if value.startswith("AUTH-")}))
    filter_publishable(files)
    publication, created = Publication.objects.get_or_create(
        operation_key=operation_key,
        defaults={"kind": kind, "files": files, "reservations": reservations, "expected": expected,
                  "summary": summary[:200], "account": account, "attempt": attempt},
    )
    if created:
        enqueue(PUBLISH, {"publication": str(publication.operation_key)}, operation_key=publish_job_key(operation_key),
                submission=getattr(getattr(attempt, "revision", None), "submission_id", None))
        record_event("publication.queued", operation_key=operation_key, account=account,
                     submission=getattr(getattr(attempt, "revision", None), "submission_id", None),
                     payload={"kind": kind, "files": sorted(files)})
    return publication


def _set(publication: Publication, **fields) -> None:
    for key, value in fields.items():
        setattr(publication, key, value)
    publication.save(update_fields=[*fields, "updated_at"])


@handler(PUBLISH)
def publish(job) -> None:
    publication = Publication.objects.get(operation_key=job.payload["publication"])
    run_publication(publication)


def run_publication(publication: Publication) -> Publication:
    if publication.status in (Publication.VERIFIED, Publication.ABANDONED):
        return publication
    default_branch = settings.PORTAL_REGISTRY_DEFAULT_BRANCH
    try:
        gh = client()
        branch = publication.branch or f"portal/{publication.kind}/{str(publication.operation_key)[:13]}"
        current_base = gh.default_branch_sha(default_branch)
        head = gh.branch_sha(branch)

        if head is None:
            gh.create_branch(branch, current_base)
            head_sha = gh.commit_files(branch, current_base, publication.files, _commit_message(publication))
            _set(publication, branch=branch, base_sha=current_base, head_sha=head_sha, status=Publication.BRANCHED)
        elif not publication.head_sha or head == publication.base_sha:
            # Crash between branch creation and commit: the branch still points at the base.
            head_sha = gh.commit_files(branch, head, publication.files, _commit_message(publication))
            _set(publication, branch=branch, base_sha=publication.base_sha or head, head_sha=head_sha, status=Publication.BRANCHED)
        else:
            _set(publication, branch=branch, head_sha=head)

        pull = gh.find_pull(branch)
        if pull is None:
            pull = gh.open_pull(branch, default_branch, publication.summary, _pull_body(publication))
        if publication.pr_number != pull["number"] or publication.status == Publication.BRANCHED:
            _set(publication, pr_number=pull["number"], status=Publication.PR_OPEN)

        if pull.get("merged"):
            return _verify(publication, gh, pull.get("merge_commit_sha") or gh.default_branch_sha(default_branch))

        if pull.get("state") == "closed":
            _set(publication, status=Publication.BLOCKED,
                 blocker=f"Pull request #{pull['number']} was closed without merging. Reopen it or re-run the operation.")
            raise DeterministicFailure(publication.blocker)

        latest_base = gh.default_branch_sha(default_branch)
        if latest_base != publication.base_sha:
            return _base_moved(publication, latest_base)

        check = gh.check_state(publication.head_sha, settings.GITHUB_REQUIRED_CHECK)
        if check.status != "completed":
            if publication.status != Publication.CHECKS_PENDING:
                _set(publication, status=Publication.CHECKS_PENDING)
            raise RetryableError(f"required check '{check.name}' is {check.status}")
        if check.conclusion != "success":
            _set(publication, status=Publication.BLOCKED,
                 blocker=(f"Required check '{check.name}' concluded '{check.conclusion}' on PR #{pull['number']} "
                          f"(head {publication.head_sha[:12]}). Inspect the CI log; the submitted work remains saved."))
            raise DeterministicFailure(publication.blocker)

        if not settings.PORTAL_AUTO_MERGE_ROUTINE:
            _set(publication, status=Publication.AWAITING_REVIEW,
                 blocker=f"Automatic merging is disabled. A maintainer must merge PR #{pull['number']} (no bypass).")
            raise RetryableError("awaiting maintainer merge")

        merge_sha = gh.merge_pull(pull["number"], publication.head_sha, settings.GITHUB_MERGE_METHOD, publication.summary)
        _set(publication, merge_sha=merge_sha, status=Publication.MERGED)
        return _verify(publication, gh, merge_sha)
    except GitHubUnavailable as exc:
        _set(publication, retries=publication.retries + 1)
        raise RetryableError(f"GitHub unavailable: {exc}") from exc
    except GitHubRefused as exc:
        message = str(exc)
        if any(marker in message for marker in ("not a fast forward", "was modified", "409")):
            return _base_moved(publication, None)
        _set(publication, status=Publication.BLOCKED, blocker=f"GitHub refused the operation: {message[:300]}")
        raise DeterministicFailure(publication.blocker) from exc


def _base_moved(publication: Publication, latest_base: str | None) -> Publication:
    """Another writer advanced the base: abandon this candidate and re-run the producing job on the new base."""
    _set(publication, status=Publication.ABANDONED,
         blocker=f"Default branch moved past base {publication.base_sha[:12]}; rebuilding against {(latest_base or 'latest')[:12]}.")
    record_event("publication.base_moved", operation_key=publication.operation_key, reason=publication.blocker)
    if publication.kind == Publication.AUTHOR_REGISTRATION:
        from accounts.models import AuthorBinding
        from accounts.services import start_author_registration

        binding = AuthorBinding.objects.filter(publication=publication).first()
        if binding:
            binding.publication = None
            binding.state = AuthorBinding.PENDING
            binding.save(update_fields=["publication", "state", "updated_at"])
            start_author_registration(binding.account)
    else:
        from submissions.services import requeue_evaluation

        # The abandoned attempt's receipt number is withdrawn, never reissued.
        bridge_allocation.withdraw_value(publication.attempt.receipt_id)
        requeue_evaluation(publication.attempt.revision, reason="base moved before merge")
    raise DeterministicFailure(publication.blocker)


def _verify(publication: Publication, gh, merge_sha: str) -> Publication:
    default_branch = settings.PORTAL_REGISTRY_DEFAULT_BRANCH
    mismatches = []
    for path, content in publication.files.items():
        if path.startswith("site/"):
            continue  # regenerated by later publications; the record files are the verified content
        committed = gh.file_content(path, default_branch)
        if committed != content:
            mismatches.append(path)
    if mismatches:
        _set(publication, merge_sha=merge_sha, status=Publication.BLOCKED,
             blocker="Committed content differs from the expected publication for: " + ", ".join(mismatches[:5]))
        raise DeterministicFailure(publication.blocker)
    with transaction.atomic():
        _set(publication, merge_sha=merge_sha, status=Publication.VERIFIED, verified_at=timezone.now(), blocker="")
        bridge_allocation.mark_committed(publication.reservations, merge_sha)
        _after_verified(publication)
        enqueue(REFRESH_PROJECTION, {"sha": merge_sha}, operation_key=_projection_key(merge_sha))
        record_event("publication.verified", operation_key=publication.operation_key,
                     payload={"merge_sha": merge_sha, "pr": publication.pr_number, "files": sorted(publication.files)})
    return publication


def _after_verified(publication: Publication) -> None:
    from submissions import state as wf

    if publication.kind == Publication.AUTHOR_REGISTRATION:
        from accounts.models import AuthorBinding

        binding = AuthorBinding.objects.filter(publication=publication).first()
        if binding:
            binding.state = AuthorBinding.REGISTERED
            binding.linked_at = timezone.now()
            binding.save(update_fields=["state", "linked_at", "updated_at"])
    elif publication.attempt is not None:
        submission = publication.attempt.revision.submission
        if publication.attempt.decision == "ACCEPTED" and submission.workflow_state == wf.ACCEPTED_PENDING:
            wf.transition(submission, wf.REGISTERED, revision=publication.attempt.revision,
                          operation_key=publication.operation_key,
                          reason=f"verified on default branch at {publication.merge_sha[:12]}")


def _projection_key(sha: str):
    import uuid

    return uuid.uuid5(uuid.NAMESPACE_URL, f"projection:{sha}")


def _commit_message(publication: Publication) -> str:
    return (f"{publication.summary}\n\nOperation: {publication.operation_key}\n"
            f"Route: portal\nPaths: {', '.join(sorted(publication.files))[:1500]}")


def _pull_body(publication: Publication) -> str:
    lines = [f"Automated portal publication for operation `{publication.operation_key}`.", "",
             f"Kind: {publication.kind}", "", "Changed paths:"]
    lines += [f"- `{p}`" for p in sorted(publication.files)]
    lines += ["", "Only registry, receipt, reservation, execution-evidence and generated-site paths are touched. "
                  "Schemas, taxonomies, engine code and workflows are never changed by a submission."]
    return "\n".join(lines)
