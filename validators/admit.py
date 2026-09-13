"""Command-line admission evaluator.

Usage:
    python -m validators.admit path/to/submitted-object.json [--write] [--register]

Evaluates a submitted research-object record against the seven admission gates
(A-G), prints the receipt, and with --write stores the machine-readable and
human-readable receipts under receipts/accepted, receipts/repair, or
receipts/rejected according to the decision.

With --register, an ACCEPTED record is copied into registry/objects/ (the
source of truth). If a previous version of the same object is already
registered, that state is preserved in registry/objects/history/ first.
Records that are RETURNED_FOR_REPAIR or REJECTED are never registered.

The evaluation is identical for every author, including AUTH-0001; there are
no founder exceptions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from . import gates, loader, receipts


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


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    write = "--write" in argv
    register = "--register" in argv
    paths = [a for a in argv if not a.startswith("--")]
    exit_code = 0
    for arg in paths:
        path = Path(arg)
        text = path.read_text(encoding="utf-8")
        record = yaml.safe_load(text) if path.suffix in (".yaml", ".yml") else json.loads(text)
        evaluation = gates.evaluate_object(record)
        receipt = receipts.build_receipt(record, evaluation)
        print(receipts.render_receipt_markdown(receipt))
        if write:
            json_path, md_path = receipts.write_receipt(receipt)
            print(f"Receipt written: {json_path} and {md_path}")
        if evaluation.decision == "ACCEPTED":
            if register:
                registered_path = register_object(record)
                print(f"Registered: {registered_path}")
        else:
            if register:
                print(f"Not registered: decision is {evaluation.decision}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
