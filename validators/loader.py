"""Registry, schema, and taxonomy loading for the Structura Reditus Research Library.

The registry files under ``registry/`` are the source of truth. All tools
(validators, gates, receipts, profiles, manifests, site generation) read from
the registry; nothing here writes a competing database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_DIR = REPO_ROOT / "schema"
TAXONOMY_DIR = REPO_ROOT / "taxonomy"
REGISTRY_DIR = REPO_ROOT / "registry"
RECEIPTS_DIR = REPO_ROOT / "receipts"
RELEASES_DIR = REPO_ROOT / "releases"
SITE_DIR = REPO_ROOT / "site"

TAXONOMY_FILES = {
    "domains": "domains.yaml",
    "focuses": "focuses.yaml",
    "tier2_classes": "tier2_classes.yaml",
    "evidence_modes": "evidence_modes.yaml",
    "provenance_types": "provenance_types.yaml",
    "maturity_states": "maturity_states.yaml",
    "relation_types": "relation_types.yaml",
    "publication_states": "publication_states.yaml",
    "functional_loci": "functional_loci.yaml",
}

MISSINGNESS_CLASSES = [
    "NON_BLOCKING",
    "EVALUABILITY_BLOCKING",
    "CONTRACT_VIOLATING",
    "AUTHORITY_BOUNDARY",
    "SOURCE_BOUNDARY",
    "PUBLICATION_BOUNDARY",
    "REPAIRABLE",
    "UNRESOLVED_SEAM",
]

DECISIONS = ["ACCEPTED", "RETURNED_FOR_REPAIR", "REJECTED"]


def _load_record(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def load_schemas() -> dict:
    return {name: load_schema(name) for name in ("author", "object", "source", "relation", "receipt")}


def load_taxonomies(taxonomy_dir: Path = TAXONOMY_DIR) -> dict:
    """Return {taxonomy_name: [term ids]} for all controlled taxonomies."""
    taxonomies = {}
    for name, filename in TAXONOMY_FILES.items():
        data = yaml.safe_load((taxonomy_dir / filename).read_text(encoding="utf-8"))
        taxonomies[name] = [term["id"] for term in data.get("terms", [])]
    return taxonomies


def _load_dir(directory: Path) -> dict:
    """Load every JSON/YAML record file in a registry directory.

    Returns {relative filename: record}. Files under history/ are historical
    states and are loaded separately.
    """
    records = {}
    if not directory.is_dir():
        return records
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix in (".json", ".yaml", ".yml"):
            records[path.name] = _load_record(path)
    return records


def load_registry(registry_dir: Path = REGISTRY_DIR) -> dict:
    """Load the full registry (current states only)."""
    return {
        "authors": _load_dir(registry_dir / "authors"),
        "objects": _load_dir(registry_dir / "objects"),
        "sources": _load_dir(registry_dir / "sources"),
        "relations": _load_dir(registry_dir / "relations"),
    }


def load_object_history(registry_dir: Path = REGISTRY_DIR) -> dict:
    """Load preserved historical object versions."""
    return _load_dir(registry_dir / "objects" / "history")


def schema_version() -> str:
    return (SCHEMA_DIR / "VERSION").read_text(encoding="utf-8").strip()


def taxonomy_version() -> str:
    return (TAXONOMY_DIR / "VERSION").read_text(encoding="utf-8").strip()


def archive_object_version(record: dict, registry_dir: Path = REGISTRY_DIR) -> Path:
    """Preserve a historical object version instead of overwriting it.

    Writes the given record state to registry/objects/history/ keyed by
    object_id and version. Raises if that historical state already exists,
    so previous states are never silently rewritten.
    """
    history_dir = registry_dir / "objects" / "history"
    os.makedirs(history_dir, exist_ok=True)
    object_id = record["object_id"]
    version = record["version"]
    path = history_dir / f"{object_id}.v{version}.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != record:
            raise FileExistsError(
                f"Historical state {path.name} already exists and differs; "
                "historical states are never rewritten. Register a new version instead."
            )
        return path
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
