"""GitHub webhook receiver: signed, deduplicated, reconciliation-triggering."""

from __future__ import annotations

import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import record_event

from .models import WebhookDelivery
from .reconciliation import nudge_publication_for_branch


def _valid_signature(body: bytes, header: str | None) -> bool:
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


@csrf_exempt
@require_POST
def github_webhook(request):
    if not _valid_signature(request.body, request.headers.get("X-Hub-Signature-256")):
        return HttpResponseForbidden("invalid signature")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event = request.headers.get("X-GitHub-Event", "")
    if not delivery_id:
        return HttpResponseBadRequest("missing delivery id")
    _, created = WebhookDelivery.objects.get_or_create(delivery_id=delivery_id, defaults={"event": event})
    if not created:
        return JsonResponse({"status": "duplicate", "delivery": delivery_id})
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponseBadRequest("invalid json")
    branches = set()
    if event == "pull_request":
        branches.add(((payload.get("pull_request") or {}).get("head") or {}).get("ref"))
    elif event == "check_run":
        for pull in (payload.get("check_run") or {}).get("pull_requests") or []:
            branches.add((pull.get("head") or {}).get("ref"))
    elif event == "check_suite":
        for pull in (payload.get("check_suite") or {}).get("pull_requests") or []:
            branches.add((pull.get("head") or {}).get("ref"))
    elif event == "push":
        ref = payload.get("ref", "")
        branches.add(ref.split("refs/heads/", 1)[-1] if ref.startswith("refs/heads/") else None)
    nudged = [b for b in branches if b and nudge_publication_for_branch(b)]
    record_event("webhook.received", actor_label="webhook", correlation=delivery_id,
                 payload={"event": event, "branches": sorted(b for b in branches if b), "nudged": nudged})
    return HttpResponse(status=202)
