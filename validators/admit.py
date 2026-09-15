"""Command-line admission evaluator.

Usage:
    python -m validators.admit path/to/submitted-object.json [--write] [--register]
                               [--operation-key KEY] [--source-file PATH ...]

Evaluates a submitted research-object record against the seven admission gates
(A-G), prints the receipt, and with --write stores the complete receipt bundle:
the machine-readable and human-readable receipts, the exact submitted-record
snapshot (RCPT-NNNNNN.submission.json) beside them under receipts/accepted,
receipts/repair, or receipts/rejected according to the decision, and the
companion execution manifest under receipts/executions/.

With --register, an ACCEPTED record is copied into registry/objects/ (the
source of truth). If a previous version of the same object is already
registered, that state is preserved in registry/objects/history/ first.
Records that are RETURNED_FOR_REPAIR or REJECTED are never registered.

--source-file PATH records the SHA-256 of an original manuscript or data file
in the execution manifest; the file itself is never placed in Git.

The evaluation is identical for every author, including AUTH-0001; there are
no founder exceptions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from . import allocation, execution, gates, loader, receipts


def register_object(record: dict, registry_dir: Path = None) -> Path:
    """Write an ACCEPTED record into the registry, preserving any prior version."""
    registry_dir = registry_dir or loader.REGISTRY_DIR
    objects_dir = registry_dir / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    path = objects_dir / f"{record['object_id']}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing == record:
            return path
        if existing.get("version") == record.get("version"):
            raise FileExistsError(
                f"{path.name} is already registered at version {record.get('version')} "
                "with different content; bump the version instead of rewriting a registered state."
            )
        loader.archive_object_version(existing, registry_dir)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _source_file_entries(paths: list) -> list:
    entries = []
    for raw in paths or []:
        path = Path(raw)
        entries.append({
            "display_name": path.name,
            "sha256": execution.file_sha256(path),
            "bytes": path.stat().st_size,
            "media_type": None,
            "version_reference": None,
            "public": False,
        })
    return entries


def evaluate_and_write(record: dict, *, write: bool, register: bool, operation_key: str = None,
                       source_files: list = None, route: str = "cli", registry_base: str = None,
                       registry: dict = None, schemas: dict = None, taxonomies: dict = None,
                       receipts_dir: Path = None, registry_dir: Path = None, out=print) -> dict:
    """Evaluate one record and (optionally) persist its bundle and registration.

    Returns {decision, receipt, execution, paths, registered_path}. Used by both
    the CLI and the portal worker so the two routes share one code path.
    """
    receipts_dir = receipts_dir or loader.RECEIPTS_DIR
    registry_dir = registry_dir or loader.REGISTRY_DIR
    evaluation = gates.evaluate_object(record, registry, schemas, taxonomies)
    receipt_id = receipts.next_receipt_id(receipts_dir, registry_dir) if write else None
    receipt = receipts.build_receipt(record, evaluation, receipt_id=receipt_id)
    out(receipts.render_receipt_markdown(receipt))
    result = {"decision": evaluation.decision, "receipt": receipt, "evaluation": evaluation,
              "execution": None, "paths": {}, "registered_path": None}
    if write:
        snapshot_rel = receipts.bundle_paths(receipt, receipts_dir)["submission"]
        try:
            snapshot_rel = snapshot_rel.relative_to(loader.REPO_ROOT).as_posix()
        except ValueError:
            snapshot_rel = snapshot_rel.as_posix()
        manifest = execution.build_execution_manifest(
            receipt, record, evaluation, route=route, snapshot_path=snapshot_rel,
            registry_base=registry_base, source_files=source_files, operation_key=operation_key)
        paths = receipts.write_receipt_bundle(receipt, record, manifest, receipts_dir)
        result["execution"] = manifest
        result["paths"] = paths
        out(f"Receipt bundle written: {paths['receipt_json']}, {paths['receipt_md']}, "
            f"{paths['submission']}, {paths['execution']}")
    if evaluation.decision == "ACCEPTED":
        if register:
            registered_path = register_object(record, registry_dir)
            result["registered_path"] = registered_path
            out(f"Registered: {registered_path}")
            reservation_path = registry_dir / "reservations" / f"{record['object_id']}.json"
            if reservation_path.exists():
                rel = registered_path.relative_to(loader.REPO_ROOT).as_posix() if registered_path.is_relative_to(loader.REPO_ROOT) else registered_path.as_posix()
                allocation.mark_state(record["object_id"], "published", registry_dir=registry_dir,
                                      published_record_path=rel)
                out(f"Reservation published: {reservation_path}")
    elif register:
        out(f"Not registered: decision is {evaluation.decision}")
    return result


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    parser = argparse.ArgumentParser(prog="python -m validators.admit", add_help=True)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--operation-key")
    parser.add_argument("--source-file", action="append", default=[])
    parser.add_argument("--registry-base", help="commit SHA of the registry state being evaluated (defaults to HEAD)")
    args = parser.parse_args(argv)
    exit_code = 0
    for arg in args.paths:
        path = Path(arg)
        text = path.read_text(encoding="utf-8")
        record = yaml.safe_load(text) if path.suffix in (".yaml", ".yml") else json.loads(text)
        result = evaluate_and_write(record, write=args.write, register=args.register,
                                    operation_key=args.operation_key,
                                    source_files=_source_file_entries(args.source_file),
                                    registry_base=args.registry_base)
        if result["decision"] != "ACCEPTED":
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
