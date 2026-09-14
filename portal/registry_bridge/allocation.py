"""Portal-side identifier allocation: a locked transaction over the shared allocator.

The database row lock serializes concurrent portal requests; the value itself
is computed by ``validators.allocation`` against the pinned committed registry
(records, history, receipts, snapshots, ledger) plus every portal allocation
not yet committed. Issued values are then published as ledger files so the
public record is reconstructible from Git alone.
"""

from __future__ import annotations

import json
import re
from datetime import timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from .checkout import isolated_checkout, repository_head
from .models import Allocation, NamespaceLock

_NUMBER = re.compile(r"([0-9]+)$")


def _next_free_in_checkout(namespace: str, base_sha: str) -> str:
    """Compute the next free value from a pinned checkout using the repository engine."""
    with isolated_checkout(base_sha) as checkout:
        from registry_bridge.engine import import_engine

        engine = import_engine(checkout)
        return engine["allocation"].next_free(
            namespace,
            registry_dir=checkout / "registry",
            receipts_dir=checkout / "receipts",
        )


def reserve_identifier(namespace: str, operation_key: str, purpose: str, base_sha: str = None) -> str:
    """Reserve one value for the operation (idempotent) with a namespace row lock."""
    base_sha = base_sha or repository_head()
    with transaction.atomic():
        NamespaceLock.objects.get_or_create(namespace=namespace)
        NamespaceLock.objects.select_for_update().get(namespace=namespace)
        existing = Allocation.objects.filter(namespace=namespace, operation_key=operation_key).first()
        if existing:
            return existing.value
        committed_next = _next_free_in_checkout(namespace, base_sha)
        highest_local = 0
        # Withdrawn values are counted too: an identifier is never recycled after a failed process.
        for value in Allocation.objects.filter(namespace=namespace).values_list("value", flat=True):
            match = _NUMBER.search(value)
            if match:
                highest_local = max(highest_local, int(match.group(1)))
        committed_number = int(_NUMBER.search(committed_next).group(1))
        number = max(committed_number, highest_local + 1)
        prefix = committed_next[: -len(_NUMBER.search(committed_next).group(1))]
        width = len(_NUMBER.search(committed_next).group(1))
        value = f"{prefix}{number:0{width}d}"
        Allocation.objects.create(namespace=namespace, value=value, operation_key=operation_key,
                                  purpose=purpose, state=Allocation.LOCAL)
        return value


def ledger_entry(namespace: str, value: str, operation_key: str, purpose: str, route: str = "portal",
                 reserved_at: str = None, state: str = "reserved", published_record_path: str = None) -> dict:
    return {
        "reservation_version": "SR-RESERVATION.v0.1.0",
        "namespace": namespace,
        "value": value,
        "operation_key": operation_key,
        "purpose": purpose,
        "state": state,
        "reserved_at": reserved_at or timezone.now().astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "route": route,
        "published_record_path": published_record_path,
    }


def ledger_file(value: str) -> str:
    return f"registry/reservations/{value}.json"


def ledger_files_for(values: list, operation_key: str, purpose: str, published_paths: dict = None,
                     states: dict = None, operation_keys: dict = None) -> dict:
    """{ledger path: JSON text} for the given values, marked published when a record path is known."""
    files = {}
    for value in values:
        namespace = value.rsplit("-", 1)[0]
        record_path = (published_paths or {}).get(value)
        state = (states or {}).get(value) or ("published" if record_path else "reserved")
        entry = ledger_entry(namespace, value, (operation_keys or {}).get(value, operation_key), purpose,
                             state=state, published_record_path=record_path)
        files[ledger_file(value)] = json.dumps(entry, indent=2, ensure_ascii=False) + "\n"
    return files


def mark_committed(values: list, sha: str) -> None:
    Allocation.objects.filter(value__in=values).exclude(state=Allocation.WITHDRAWN).update(
        state=Allocation.LEDGER_COMMITTED, committed_sha=sha)


def withdraw(operation_key: str) -> None:
    Allocation.objects.filter(operation_key=operation_key).update(state=Allocation.WITHDRAWN)


def withdraw_value(value: str) -> None:
    if value:
        Allocation.objects.filter(value=value).exclude(state=Allocation.LEDGER_COMMITTED).update(state=Allocation.WITHDRAWN)
