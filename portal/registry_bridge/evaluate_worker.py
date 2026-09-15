"""Isolated evaluation worker.

Runs as a separate process with the pinned checkout as its working directory
and *that checkout's* ``validators`` package on the import path, so the engine
revision is exactly the one recorded in the execution manifest.

    python evaluate_worker.py SPEC.json RESULT.json

The spec names the record, proposed dependency records, reservation ledger
entries, and evaluation options. The worker validates the complete candidate
registry, evaluates the record through the unchanged seven gates, writes the
receipt bundle, registers ACCEPTED records, regenerates the public projection,
and reports every changed file. It never decides anything the engine does not.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path


def _write_records(checkout: Path, kind: str, records: dict) -> list:
    """Write proposed dependency records; refuse to overwrite a committed record with different content."""
    conflicts = []
    directory = checkout / "registry" / kind
    directory.mkdir(parents=True, exist_ok=True)
    for record_id, record in (records or {}).items():
        path = directory / f"{record_id}.json"
        text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != text:
            conflicts.append(f"registry/{kind}/{record_id}.json already exists with different content")
            continue
        path.write_text(text, encoding="utf-8")
    return conflicts


def _publish_ledger_states(checkout: Path, ledger_files: dict, outcome: dict) -> None:
    """Mark reservations published when their committed record now exists in the candidate checkout."""
    kinds = {"AUTH": "registry/authors", "SR-OBJ": "registry/objects", "SRC": "registry/sources", "REL": "registry/relations"}
    receipt_id = (outcome.get("receipt") or {}).get("receipt_id")
    receipt_path = None
    if receipt_id and outcome.get("paths"):
        try:
            receipt_path = Path(outcome["paths"]["receipt_json"]).relative_to(checkout).as_posix()
        except ValueError:
            receipt_path = None
    for rel_path in ledger_files:
        target = checkout / rel_path
        if not target.exists():
            continue
        entry = json.loads(target.read_text(encoding="utf-8"))
        if entry.get("state") != "reserved":
            continue
        value, namespace = entry.get("value"), entry.get("namespace")
        record_path = None
        if namespace == "RCPT" and value == receipt_id and receipt_path:
            record_path = receipt_path
        elif namespace in kinds and (checkout / kinds[namespace] / f"{value}.json").exists():
            record_path = f"{kinds[namespace]}/{value}.json"
        if record_path:
            entry["state"] = "published"
            entry["published_record_path"] = record_path
            target.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(spec_path: str, result_path: str) -> int:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    checkout = Path(spec["checkout"]).resolve()
    os.chdir(checkout)
    sys.path.insert(0, str(checkout))
    result: dict = {"status": "error", "engine_checkout": str(checkout)}
    try:
        from validators import admit, checks, loader, sitegen  # the pinned engine, not the web process's copy

        conflicts = []
        for kind in ("authors", "sources", "relations"):
            conflicts += _write_records(checkout, kind, spec.get("proposed", {}).get(kind))
        for rel_path, content in (spec.get("ledger_files") or {}).items():
            target = checkout / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(content, encoding="utf-8")
        if conflicts:
            result.update(status="dependency_conflict", issues=conflicts)
            Path(result_path).write_text(json.dumps(result), encoding="utf-8")
            return 0

        report = checks.validate_registry()
        issues = [{"check": i.check, "record": i.record, "message": i.message} for i in report.issues]
        proposed_paths = {f"{kind}/{rid}.json" for kind in ("authors", "sources", "relations")
                          for rid in (spec.get("proposed", {}).get(kind) or {})}
        dependency_issues = [i for i in issues if i["record"] in proposed_paths or i["check"].startswith("reservation")]
        if dependency_issues:
            result.update(status="dependency_invalid", issues=dependency_issues)
            Path(result_path).write_text(json.dumps(result), encoding="utf-8")
            return 0
        if issues:
            result.update(status="base_invalid", issues=issues)
            Path(result_path).write_text(json.dumps(result), encoding="utf-8")
            return 0

        record = spec["record"]
        outcome = admit.evaluate_and_write(
            record, write=bool(spec.get("write", True)), register=bool(spec.get("register", True)),
            operation_key=spec.get("operation_key"), source_files=spec.get("source_files") or [],
            route=spec.get("route", "portal"), registry_base=spec["registry_base"], receipt_id=spec.get("receipt_id"),
            out=lambda *_: None)
        if outcome["execution"] is not None and (spec.get("supersedes_attempt") or spec.get("review_decision")):
            # Re-emit the manifest with linkage fields the CLI path does not know about.
            from validators import execution as execution_mod, receipts as receipts_mod
            manifest = dict(outcome["execution"])
            if spec.get("supersedes_attempt"):
                manifest["supersedes_attempt"] = spec["supersedes_attempt"]
            if spec.get("review_decision"):
                manifest["review_decision"] = spec["review_decision"]
            import jsonschema
            jsonschema.Draft202012Validator(loader.load_schema("execution")).validate(manifest)
            paths = receipts_mod.bundle_paths(outcome["receipt"], loader.RECEIPTS_DIR)
            paths["execution"].write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            outcome["execution"] = manifest

        _publish_ledger_states(checkout, spec.get("ledger_files") or {}, outcome)
        post = checks.validate_registry()
        post_issues = [{"check": i.check, "record": i.record, "message": i.message} for i in post.issues]
        sitegen.generate_site()
        result.update(
            status="evaluated",
            decision=outcome["decision"],
            receipt=outcome["receipt"],
            execution=outcome["execution"],
            registered_path=str(outcome["registered_path"].relative_to(checkout)) if outcome["registered_path"] else None,
            post_validation_issues=post_issues,
            schema_version=loader.schema_version(),
            taxonomy_version=loader.taxonomy_version(),
        )
    except Exception as exc:  # noqa: BLE001 - reported to the parent as a processing error, never a decision
        result.update(status="error", error=f"{type(exc).__name__}: {str(exc)[:600]}", trace=traceback.format_exc()[-4000:])
    Path(result_path).write_text(json.dumps(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
