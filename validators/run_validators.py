from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validators.relation_validation import validate_relations
from validators.release_validation import validate_release_manifest
from validators.schema_validation import validate_schema_files
from validators.taxonomy_validation import validate_taxonomies
from validators.unique_id_validation import validate_unique_ids

VALIDATORS = [
    ("schema", validate_schema_files),
    ("unique-id", validate_unique_ids),
    ("taxonomy", validate_taxonomies),
    ("relation", validate_relations),
    ("release", validate_release_manifest),
]


def main() -> int:
    any_errors = False
    for name, fn in VALIDATORS:
        errors = fn()
        if errors:
            any_errors = True
            print(f"[{name}] FAIL")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"[{name}] PASS")

    return 1 if any_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
