"""Execution manifests: bind a formal receipt to the exact inputs that produced it.

A receipt says what was decided. An execution manifest says *from what*: the
canonical hash of the evaluated revision, the hashes of the original source
files, the engine revision, the schema and taxonomy versions, and the
registry base commit. Publication (the commit/PR that later carries the
record) is recorded separately so no file contains the SHA of the commit that
contains it.

Manifests live under receipts/executions/ (SR-EXECUTION.v0.1.0) and are never
loaded as receipts. The legacy receipt schema is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from . import loader
from .gates import GateEvaluation

MANIFEST_VERSION = "SR-EXECUTION.v0.1.0"
EXECUTIONS_DIR = loader.RECEIPTS_DIR / "executions"


def canonical_json(record: dict) -> str:
    """Deterministic serialization used for submission hashes."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def submission_hash(record: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(record).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(repo_root: Path = None, allow_dirty: bool = True) -> str:
    """Current commit of the checkout, marked dirty when the working tree differs."""
    repo_root = repo_root or loader.REPO_ROOT
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True,
                                      stderr=subprocess.DEVNULL).strip()
        status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                         cwd=repo_root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if status and allow_dirty:
        return f"working-tree:{sha}-dirty"
    return sha


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_execution_manifest(receipt: dict, record: dict, evaluation: GateEvaluation, *,
                             route: str, snapshot_path: str, engine_revision: str = None,
                             registry_base: str = None, source_files: list = None,
                             operation_key: str = None, review_decision: dict = None,
                             supersedes_attempt: str = None, evaluated_at: str = None,
                             schema_version: str = None, taxonomy_version: str = None,
                             notes: str = None) -> dict:
    revision = engine_revision or git_revision()
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "receipt_id": receipt["receipt_id"],
        "decision": receipt["decision"],
        "submission_identity": receipt["submission_identity"],
        "submission_hash": submission_hash(record),
        "submission_snapshot_path": snapshot_path,
        "engine_revision": revision,
        "schema_version": schema_version or loader.schema_version(),
        "taxonomy_version": taxonomy_version or loader.taxonomy_version(),
        "registry_base": registry_base or revision,
        "evaluated_at": evaluated_at or receipt.get("generated") or _now_iso(),
        "gate_results": {key: gate.result for key, gate in evaluation.gates.items()},
        "route": route,
        "operation_key": operation_key,
        "source_files": list(source_files or []),
        "review_decision": review_decision,
    }
    if supersedes_attempt:
        manifest["supersedes_attempt"] = supersedes_attempt
    if notes:
        manifest["notes"] = notes
    jsonschema.Draft202012Validator(loader.load_schema("execution")).validate(manifest)
    return manifest


def load_execution_manifests(executions_dir: Path = None) -> dict:
    """{receipt_id: manifest} for every companion execution manifest."""
    executions_dir = executions_dir or EXECUTIONS_DIR
    manifests = {}
    if executions_dir.is_dir():
        for path in sorted(executions_dir.glob("RCPT-*.execution.json")):
            manifests[path.name.split(".")[0]] = json.loads(path.read_text(encoding="utf-8"))
    return manifests


def load_publication_records(executions_dir: Path = None) -> dict:
    """{receipt_id: publication record} written after the carrying commit exists."""
    executions_dir = executions_dir or EXECUTIONS_DIR
    records = {}
    if executions_dir.is_dir():
        for path in sorted(executions_dir.glob("RCPT-*.publication.json")):
            records[path.name.split(".")[0]] = json.loads(path.read_text(encoding="utf-8"))
    return records


def verify_manifest_against_snapshot(manifest: dict, receipts_dir: Path = None, repo_root: Path = None) -> list:
    """Return a list of discrepancies between a manifest and its preserved snapshot (empty when consistent)."""
    repo_root = repo_root or loader.REPO_ROOT
    problems = []
    snapshot_path = repo_root / manifest["submission_snapshot_path"]
    if not snapshot_path.exists():
        return [f"snapshot {manifest['submission_snapshot_path']} is missing"]
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if submission_hash(snapshot) != manifest["submission_hash"]:
        problems.append("submission_hash does not match the preserved snapshot")
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    receipts = loader.load_receipts(receipts_dir)
    receipt = receipts.get(manifest["receipt_id"])
    if receipt is None:
        problems.append(f"receipt {manifest['receipt_id']} not found")
    else:
        if receipt["decision"] != manifest["decision"]:
            problems.append("decision differs between receipt and manifest")
        for key in "ABCDEFG":
            if receipt["gates"][key]["result"] != manifest["gate_results"][key]:
                problems.append(f"gate {key} result differs between receipt and manifest")
    return problems
