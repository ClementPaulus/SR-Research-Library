"""Command-line admission evaluator.

Usage:
    python -m validators.admit path/to/submitted-object.json [--write]

Evaluates a submitted research-object record against the seven admission gates
(A-G), prints the receipt, and with --write stores the machine-readable and
human-readable receipts under receipts/accepted, receipts/repair, or
receipts/rejected according to the decision.

The evaluation is identical for every author, including AUTH-0001; there are
no founder exceptions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from . import gates, receipts


def main(argv: list = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    write = "--write" in argv
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
        if evaluation.decision != "ACCEPTED":
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
