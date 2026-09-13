from __future__ import annotations

import re
from pathlib import Path

from .common import ROOT, list_yaml_files, load_yaml

PATTERNS = {
    "authors": re.compile(r"^AUTH-\d{4}$"),
    "objects": re.compile(r"^SR-OBJ-\d{6}$"),
    "sources": re.compile(r"^SRC-\d{6}$"),
    "relations": re.compile(r"^REL-\d{6}$"),
}

FIELD_NAMES = {
    "authors": "author_id",
    "objects": "object_id",
    "sources": "source_id",
    "relations": "relation_id",
}


def _collect_ids(folder: Path, field: str) -> list[str]:
    values: list[str] = []
    for path in list_yaml_files(folder):
        data = load_yaml(path)
        if isinstance(data, dict) and field in data:
            values.append(str(data[field]))
    return values


def validate_unique_ids() -> list[str]:
    errors: list[str] = []
    registry = ROOT / "registry"

    for category, pattern in PATTERNS.items():
        folder = registry / category
        ids = _collect_ids(folder, FIELD_NAMES[category])
        bad = [value for value in ids if not pattern.fullmatch(value)]
        if bad:
            errors.append(f"{category}: invalid ID format(s): {bad}")

        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            errors.append(f"{category}: duplicate IDs found: {duplicates}")

    return errors
