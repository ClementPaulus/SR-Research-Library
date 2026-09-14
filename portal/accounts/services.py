"""Identity resolution and automatic author registration.

After email verification a background job (a) checks for an open claim on an
existing identity, (b) otherwise reserves a new AuthorID through the shared
allocator, (c) builds the schema-conformant public author record from the
supplied identity fields only, and (d) publishes it through the same protected
Git workflow as research records. Repeated jobs return the same identity.
"""

from __future__ import annotations

import json
import logging
from datetime import timezone as dt_timezone

import jsonschema
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import enqueue, record_event
from core.tasks import DeterministicFailure, handler

from .models import Account, AuthorBinding, IdentityClaim

log = logging.getLogger("portal.accounts")

REGISTER_AUTHOR = "accounts.register_author"


def start_author_registration(account: Account) -> AuthorBinding:
    """Idempotently create the binding and queue registration. Safe to call on every verification."""
    with transaction.atomic():
        binding, _ = AuthorBinding.objects.select_for_update().get_or_create(account=account)
        if binding.state in (AuthorBinding.REGISTERED, AuthorBinding.LINKED):
            return binding
        enqueue(REGISTER_AUTHOR, {"account_uuid": str(account.uuid)}, operation_key=binding.operation_key)
        record_event("author.registration_queued", account=account, operation_key=binding.operation_key,
                     actor=account, actor_label="researcher")
    return binding


def build_author_record(account: Account, author_id: str, registered: str) -> dict:
    record = {
        "author_id": author_id,
        "display_name": account.display_name.strip(),
        "status": "active",
        "registered": registered,
        "notes": ("Registered through the researcher portal. Only the supplied identity fields "
                  "(display name and, if supplied, ORCID) are recorded; no credentials, affiliations, "
                  "roles, or research metadata are added. Same admission requirements as every author."),
    }
    if account.orcid:
        record["orcid"] = account.orcid
    schema = json.loads((settings.PORTAL_REGISTRY_REPO_PATH / "schema" / "author.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(record)
    return record


@handler(REGISTER_AUTHOR)
def register_author(job) -> None:
    from registry_bridge import allocation as bridge_allocation
    from registry_bridge.models import Publication
    from registry_bridge.publication import queue_publication

    account = Account.objects.get(uuid=job.payload["account_uuid"])
    with transaction.atomic():
        binding = AuthorBinding.objects.select_for_update().get(account=account)
        if binding.state in (AuthorBinding.REGISTERED, AuthorBinding.LINKED):
            return
        if IdentityClaim.objects.filter(account=account, state=IdentityClaim.REQUESTED).exists():
            if binding.state != AuthorBinding.CLAIM_REQUESTED:
                binding.state = AuthorBinding.CLAIM_REQUESTED
                binding.save(update_fields=["state", "updated_at"])
                record_event("author.claim_pending", account=account, operation_key=binding.operation_key,
                             reason="An identity claim on an existing AuthorID is awaiting verification.")
            raise DeterministicFailure("identity claim awaiting reviewer verification")
        if binding.publication_id and binding.state == AuthorBinding.RESERVED:
            return  # publication already queued; reconciliation will finish it
        if not account.display_name.strip():
            raise DeterministicFailure("display name is empty; the researcher must supply one")
        value = bridge_allocation.reserve_identifier("AUTH", str(binding.operation_key), purpose="author registration")
        registered = timezone.now().astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = build_author_record(account, value, registered)
        publication = queue_publication(
            kind=Publication.AUTHOR_REGISTRATION,
            operation_key=binding.operation_key,
            files={f"registry/authors/{value}.json": json.dumps(record, indent=2, ensure_ascii=False) + "\n"},
            reservations=[value],
            expected={"author_id": value},
            summary=f"Register author {value} ({account.display_name})",
            account=account,
        )
        binding.author_id = value
        binding.state = AuthorBinding.RESERVED
        binding.publication = publication
        binding.evidence = "Verified email; new identity allocated through the shared reservation ledger."
        binding.save(update_fields=["author_id", "state", "publication", "evidence", "updated_at"])
        record_event("author.reserved", account=account, operation_key=binding.operation_key,
                     payload={"author_id": value})


def request_identity_claim(account: Account, author_id: str, evidence: str) -> IdentityClaim:
    """Claim an existing identity. Never auto-granted; a reviewer verifies evidence."""
    claim = IdentityClaim.objects.create(account=account, author_id=author_id, evidence=evidence)
    binding, _ = AuthorBinding.objects.get_or_create(account=account)
    if binding.state == AuthorBinding.PENDING:
        binding.state = AuthorBinding.CLAIM_REQUESTED
        binding.save(update_fields=["state", "updated_at"])
    record_event("author.claim_requested", account=account, actor=account, actor_label="researcher",
                 payload={"author_id": author_id})
    return claim


def decide_identity_claim(claim: IdentityClaim, reviewer: Account, verified: bool, notes: str) -> IdentityClaim:
    if not reviewer.is_reviewer:
        raise PermissionError("only reviewers or administrators decide identity claims")
    with transaction.atomic():
        claim.state = IdentityClaim.VERIFIED if verified else IdentityClaim.DENIED
        claim.decided_by = reviewer
        claim.decided_at = timezone.now()
        claim.decision_notes = notes
        claim.save()
        binding = AuthorBinding.objects.select_for_update().get(account=claim.account)
        if verified:
            if AuthorBinding.objects.filter(author_id=claim.author_id).exclude(pk=binding.pk).exists():
                raise DeterministicFailure(f"{claim.author_id} is already bound to another account")
            binding.author_id = claim.author_id
            binding.state = AuthorBinding.LINKED
            binding.linked_by = reviewer
            binding.linked_at = timezone.now()
            binding.evidence = f"Identity claim verified by reviewer: {notes[:200]}"
            binding.save()
        else:
            binding.state = AuthorBinding.PENDING
            binding.save(update_fields=["state", "updated_at"])
            start_author_registration(claim.account)
        record_event("author.claim_decided", account=claim.account, actor=reviewer, actor_label="reviewer",
                     payload={"author_id": claim.author_id, "verified": verified})
    return claim


def revoke_other_sessions(account: Account, current_session_key: str | None) -> int:
    from django.contrib.sessions.models import Session
    from importlib import import_module

    engine = import_module(settings.SESSION_ENGINE)
    removed = 0
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.session_key == current_session_key:
            continue
        data = engine.SessionStore().decode(session.session_data)
        if str(data.get("_auth_user_id")) == str(account.pk):
            session.delete()
            removed += 1
    record_event("account.sessions_revoked", account=account, actor=account, actor_label="researcher",
                 payload={"removed": removed})
    return removed
