"""Repository-wide identifier allocation and the reservation ledger.

Neither a browser nor an isolated checkout may compute "the next free number"
on its own. Every namespace is reconciled against everything that already
uses a value:

  * committed current records          (registry/<kind>/)
  * preserved historical object states  (registry/objects/history/)
  * receipts and the identities they name (receipts/*/RCPT-*.json)
  * the additive reservation ledger     (registry/reservations/<value>.json)

A reserved value is never reused for different work and never recycled after
withdrawal or a failed process. When a namespace approaches its schema limit
the allocator refuses and a versioned migration is required; it never wraps
or silently changes the identifier format.

Reservations are infrastructure records governed by
``schema/reservation.schema.json`` (SR-RESERVATION.v0.1.0). They are not one
of the three registry surfaces and are excluded from ``loader.load_registry``.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from . import loader

RESERVATION_VERSION = "SR-RESERVATION.v0.1.0"
RESERVATIONS_DIR = loader.REGISTRY_DIR / "reservations"


@dataclass(frozen=True)
class Namespace:
    prefix: str
    width: int
    registry_kind: str | None
    id_field: str | None

    @property
    def pattern(self) -> re.Pattern:
        return re.compile(rf"^{re.escape(self.prefix)}-([0-9]{{{self.width}}})$")

    @property
    def limit(self) -> int:
        return 10 ** self.width - 1

    def format(self, number: int) -> str:
        return f"{self.prefix}-{number:0{self.width}d}"


NAMESPACES = {
    "AUTH": Namespace("AUTH", 4, "authors", "author_id"),
    "SR-OBJ": Namespace("SR-OBJ", 6, "objects", "object_id"),
    "SRC": Namespace("SRC", 6, "sources", "source_id"),
    "REL": Namespace("REL", 6, "relations", "relation_id"),
    "SR-GOV": Namespace("SR-GOV", 6, "governing", "governing_id"),
    "RCPT": Namespace("RCPT", 6, None, None),
}

# Refuse allocation once fewer than this many values remain, so a migration is planned in time.
EXHAUSTION_MARGIN = 100


class NamespaceExhausted(RuntimeError):
    """The namespace is at (or within the margin of) its schema limit; a versioned migration is required."""


class ReservationConflict(RuntimeError):
    """The requested value is already held by a different operation."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def reservation_schema() -> dict:
    return loader.load_schema("reservation")


def load_reservations(reservations_dir: Path = None) -> dict:
    """Return {value: reservation} for every ledger entry."""
    reservations_dir = reservations_dir or RESERVATIONS_DIR
    ledger = {}
    if not reservations_dir.is_dir():
        return ledger
    for path in sorted(reservations_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        ledger[record.get("value", path.stem)] = record
    return ledger


def _numbers(values, namespace: Namespace) -> set:
    numbers = set()
    for value in values:
        if isinstance(value, str):
            match = namespace.pattern.match(value)
            if match:
                numbers.add(int(match.group(1)))
    return numbers


def used_values(namespace_key: str, registry: dict = None, history: dict = None,
                receipts: dict = None, reservations: dict = None,
                registry_dir: Path = None, receipts_dir: Path = None) -> set:
    """Every value of the namespace already used anywhere in the repository."""
    namespace = NAMESPACES[namespace_key]
    registry_dir = registry_dir or loader.REGISTRY_DIR
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    if registry is None:
        registry = loader.load_registry(registry_dir)
    if history is None:
        history = loader.load_object_history(registry_dir)
    if receipts is None:
        receipts = loader.load_receipts(receipts_dir)
    if reservations is None:
        reservations = load_reservations(registry_dir / "reservations")

    values: set = set()
    if namespace.registry_kind:
        for record in (registry.get(namespace.registry_kind) or {}).values():
            values.add(record.get(namespace.id_field))
    if namespace_key == "SR-OBJ":
        for record in history.values():
            values.add(record.get("object_id"))
        # Snapshots beside receipts preserve provisional identities of non-accepted work.
        for subdir in ("accepted", "repair", "rejected"):
            directory = receipts_dir / subdir
            if directory.is_dir():
                for path in directory.glob("RCPT-*.submission.json"):
                    try:
                        values.add(json.loads(path.read_text(encoding="utf-8")).get("object_id"))
                    except (OSError, ValueError):
                        continue
    for receipt in receipts.values():
        if namespace_key == "RCPT":
            values.add(receipt.get("receipt_id"))
        elif namespace_key == "SR-OBJ":
            values.add(receipt.get("object_id"))
            values.add(receipt.get("provisional_object_id"))
            values.add(receipt.get("submission_identity"))
        elif namespace_key == "AUTH":
            values.update(receipt.get("author_ids") or [])
        elif namespace_key == "SRC":
            values.update(receipt.get("source_ids") or [])
        elif namespace_key == "REL":
            values.update(receipt.get("relation_ids") or [])
    if namespace_key == "RCPT":
        # Receipt files that failed to load still occupy their number.
        for subdir in ("accepted", "repair", "rejected"):
            directory = receipts_dir / subdir
            if directory.is_dir():
                for path in directory.iterdir():
                    match = re.match(r"(RCPT-[0-9]{6})", path.name)
                    if match:
                        values.add(match.group(1))
    for value, reservation in reservations.items():
        if reservation.get("namespace") == namespace_key:
            values.add(value)
    return {v for v in values if isinstance(v, str) and namespace.pattern.match(v)}


def next_free(namespace_key: str, **kwargs) -> str:
    """Lowest unused value above every used value in the namespace."""
    namespace = NAMESPACES[namespace_key]
    used = _numbers(used_values(namespace_key, **kwargs), namespace)
    candidate = (max(used) + 1) if used else 1
    if candidate > namespace.limit - EXHAUSTION_MARGIN:
        raise NamespaceExhausted(
            f"namespace {namespace_key} is within {EXHAUSTION_MARGIN} values of its schema limit "
            f"({namespace.limit}); a versioned identifier migration is required before further allocation")
    return namespace.format(candidate)


def find_reservation(namespace_key: str, operation_key: str, reservations: dict) -> dict | None:
    for reservation in reservations.values():
        if reservation.get("namespace") == namespace_key and reservation.get("operation_key") == operation_key:
            return reservation
    return None


def _write_exclusive(path: Path, payload: dict) -> None:
    """Create the ledger file atomically; fail if another writer created it first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


@contextlib.contextmanager
def _ledger_lock(reservations_dir: Path):
    """Serialize scan-and-create within one host; O_EXCL remains the cross-host backstop."""
    reservations_dir.mkdir(parents=True, exist_ok=True)
    lock_path = reservations_dir / ".ledger.lock"
    with open(lock_path, "a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def reserve(namespace_key: str, purpose: str, operation_key: str = None, route: str = "cli",
            registry_dir: Path = None, receipts_dir: Path = None, notes: str = None,
            reserved_at: str = None) -> dict:
    """Reserve the next free value for one operation (idempotent per operation key).

    Repeating the call with the same operation key returns the existing
    reservation instead of allocating a second value.
    """
    if namespace_key not in NAMESPACES:
        raise KeyError(f"unknown namespace '{namespace_key}'")
    registry_dir = registry_dir or loader.REGISTRY_DIR
    reservations_dir = registry_dir / "reservations"
    operation_key = operation_key or str(uuid.uuid4())
    schema = reservation_schema()
    with _ledger_lock(reservations_dir):
        reservations = load_reservations(reservations_dir)
        existing = find_reservation(namespace_key, operation_key, reservations)
        if existing:
            return existing
        for _attempt in range(20):
            value = next_free(namespace_key, registry_dir=registry_dir, receipts_dir=receipts_dir,
                              reservations=load_reservations(reservations_dir))
            record = {
                "reservation_version": RESERVATION_VERSION,
                "namespace": namespace_key,
                "value": value,
                "operation_key": operation_key,
                "purpose": purpose,
                "state": "reserved",
                "reserved_at": reserved_at or _now_iso(),
                "route": route,
                "published_record_path": None,
            }
            if notes:
                record["notes"] = notes
            jsonschema.Draft202012Validator(schema).validate(record)
            try:
                _write_exclusive(reservations_dir / f"{value}.json", record)
            except FileExistsError:
                continue  # another host took this value between scan and create; rescan
            return record
    raise ReservationConflict(f"could not reserve a {namespace_key} value after repeated conflicts")


def mark_state(value: str, state: str, registry_dir: Path = None, published_record_path: str = None) -> dict:
    """Advance a reservation to published or withdrawn. Ledger entries are never deleted."""
    if state not in ("published", "withdrawn"):
        raise ValueError("state must be 'published' or 'withdrawn'")
    registry_dir = registry_dir or loader.REGISTRY_DIR
    path = registry_dir / "reservations" / f"{value}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["state"] == "published" and state != "published":
        raise ReservationConflict(f"{value} is already published and cannot be withdrawn")
    record["state"] = state
    if published_record_path is not None:
        record["published_record_path"] = published_record_path
    jsonschema.Draft202012Validator(reservation_schema()).validate(record)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return record


def check_reservations(registry: dict, receipts: dict, reservations: dict, report,
                       history: dict = None) -> None:
    """Validator check: the ledger and the committed records must agree.

    * every ledger file validates against the reservation schema;
    * a reservation must not be in state ``reserved`` while a committed record already
      carries its value (publish the reservation), and a ``published`` reservation must
      name an existing record;
    * one value is never held by two operations.
    """
    schema = reservation_schema()
    validator = jsonschema.Draft202012Validator(schema)
    committed: dict = {}
    for key, namespace in NAMESPACES.items():
        if namespace.registry_kind:
            for filename, record in (registry.get(namespace.registry_kind) or {}).items():
                value = record.get(namespace.id_field)
                if isinstance(value, str):
                    committed[value] = f"{namespace.registry_kind}/{filename}"
    for receipt_id in receipts:
        committed[receipt_id] = f"receipts/{receipt_id}"
    seen_operations: dict = {}
    for value, reservation in reservations.items():
        rec = f"reservations/{value}.json"
        for error in validator.iter_errors(reservation):
            path = "/".join(str(p) for p in error.absolute_path) or "<root>"
            report.add("reservation-schema", rec, f"{path}: {error.message}")
        if reservation.get("value") != value:
            report.add("reservation-ledger", rec, f"file name does not match reserved value '{reservation.get('value')}'")
        op = (reservation.get("namespace"), reservation.get("operation_key"))
        if op in seen_operations:
            report.add("reservation-ledger", rec,
                       f"operation {op[1]} already holds {seen_operations[op]} in namespace {op[0]}; one identity per operation")
        seen_operations[op] = value
        state = reservation.get("state")
        if state == "reserved" and value in committed:
            report.add("reservation-ledger", rec,
                       f"'{value}' is still 'reserved' but {committed[value]} is committed; mark the reservation published")
        if state == "published":
            record_path = reservation.get("published_record_path")
            if not record_path or not (loader.REPO_ROOT / record_path).exists():
                if value not in committed:
                    report.add("reservation-ledger", rec,
                               f"'{value}' is 'published' but no committed record carries it")
