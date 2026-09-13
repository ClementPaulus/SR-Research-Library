"""Release-manifest generation for the Structura Reditus Research Library.

The library is versioned independently (SR-LIBRARY.vX.Y.Z). Each release
manifest records the schema version, taxonomy version, entity counts, the
full manifest of IDs, date and timezone, open seams, migration notes, and
content hashes. Previous releases are never silently rewritten: writing a
manifest that already exists with different content raises an error.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import checks, loader

RECEIPT_FILE_RE = re.compile(r"^RCPT-[0-9]{6}\.json$")


def load_open_seams(releases_dir: Path = None) -> list:
    """Return the descriptions of seams still marked open in releases/open-seams.yaml."""
    path = (releases_dir or loader.RELEASES_DIR) / "open-seams.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [f"{s['id']}: {s['description']}" for s in data.get("seams", [])
            if s.get("status") == "open"]


def _hash_directory(directory: Path) -> dict:
    """Return {relative path: sha256} for every record file in a directory tree."""
    hashes = {}
    if not directory.is_dir():
        return hashes
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix in (".json", ".yaml", ".yml", ".md"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[str(path.relative_to(directory.parent))] = digest
    return hashes


def _count_receipts(receipts_dir: Path) -> int:
    count = 0
    for subdir in ("accepted", "repair", "rejected"):
        directory = receipts_dir / subdir
        if directory.is_dir():
            # Archived submissions (RCPT-NNNNNN.submission.json) sit beside receipts and are not receipts.
            count += sum(1 for p in directory.iterdir() if RECEIPT_FILE_RE.match(p.name))
    return count


def build_release_manifest(library_version: str, open_seams: list = None,
                           migration_notes: list = None, prerelease: bool = True) -> dict:
    """Build a release manifest from the current registry state.

    When ``open_seams`` is None, the seams marked open in
    ``releases/open-seams.yaml`` are used.
    """
    registry = loader.load_registry()
    now = datetime.now(timezone.utc)
    if open_seams is None:
        open_seams = load_open_seams()

    ids = {
        "authors": sorted(r["author_id"] for r in registry["authors"].values() if r.get("author_id")),
        "objects": sorted(r["object_id"] for r in registry["objects"].values() if r.get("object_id")),
        "sources": sorted(r["source_id"] for r in registry["sources"].values() if r.get("source_id")),
        "relations": sorted(r["relation_id"] for r in registry["relations"].values() if r.get("relation_id")),
        "governing": sorted(r["governing_id"] for r in registry.get("governing", {}).values() if r.get("governing_id")),
    }
    # Released governing records become immutable; their content hash is what the validator enforces.
    governing_hashes = {
        r["governing_id"]: checks.governing_immutable_hash(r)
        for r in registry.get("governing", {}).values() if r.get("governing_id")
    }
    # Records already released keep the hash of the release that froze them.
    governing_hashes.update(loader.released_governing_hashes())

    hashes = {}
    hashes.update(_hash_directory(loader.SCHEMA_DIR))
    hashes.update(_hash_directory(loader.TAXONOMY_DIR))
    hashes.update(_hash_directory(loader.REGISTRY_DIR))

    return {
        "library_version": library_version,
        "prerelease": prerelease,
        "schema_version": loader.schema_version(),
        "taxonomy_version": loader.taxonomy_version(),
        "author_count": len(ids["authors"]),
        "object_count": len(ids["objects"]),
        "source_count": len(ids["sources"]),
        "relation_count": len(ids["relations"]),
        "governing_count": len(ids["governing"]),
        "receipt_count": _count_receipts(loader.RECEIPTS_DIR),
        "id_manifest": ids,
        "governing_immutable_hashes": dict(sorted(governing_hashes.items())),
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timezone": "UTC",
        "open_seams": list(open_seams),
        "migration_notes": migration_notes or [],
        "hashes": hashes,
    }


def write_release_manifest(manifest: dict, manifests_dir: Path = None) -> Path:
    """Write a release manifest without rewriting previous releases."""
    manifests_dir = manifests_dir or (loader.RELEASES_DIR / "manifests")
    manifests_dir.mkdir(parents=True, exist_ok=True)
    path = manifests_dir / f"{manifest['library_version']}.json"
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != manifest:
            raise FileExistsError(
                f"Release manifest {path.name} already exists and differs; previous "
                "releases are never silently rewritten. Publish a new version instead."
            )
        return path
    path.write_text(payload, encoding="utf-8")
    return path
