from __future__ import annotations

from pathlib import Path

from .common import ROOT, is_iso_datetime, load_yaml

REQUIRED_RELEASE_FIELDS = {
    "library_version",
    "schema_version",
    "taxonomy_version",
    "frozen_at",
    "registry_counts",
    "id_manifest",
    "receipt_manifest",
    "status",
}


def _registry_files() -> dict[str, list[Path]]:
    return {
        "authors": sorted((ROOT / "registry" / "authors").glob("*.yaml")),
        "objects": sorted((ROOT / "registry" / "objects").glob("*.yaml")),
        "sources": sorted((ROOT / "registry" / "sources").glob("*.yaml")),
        "relations": sorted((ROOT / "registry" / "relations").glob("*.yaml")),
    }


def _id_values(paths: list[Path], field: str) -> list[str]:
    values: list[str] = []
    for path in paths:
        data = load_yaml(path)
        if isinstance(data, dict) and field in data:
            values.append(str(data[field]))
    return sorted(values)


def validate_release_manifest() -> list[str]:
    errors: list[str] = []
    manifests = sorted((ROOT / "releases").glob("*.manifest.yaml"))
    if not manifests:
        return ["no release manifest files found"]

    registry_files = _registry_files()
    receipt_files = {
        "accepted": sorted((ROOT / "receipts" / "accepted").glob("*.yaml")),
        "repair": sorted((ROOT / "receipts" / "repair").glob("*.yaml")),
        "rejected": sorted((ROOT / "receipts" / "rejected").glob("*.yaml")),
    }

    for manifest in manifests:
        release = load_yaml(manifest)
        if not isinstance(release, dict):
            errors.append(f"{manifest.name}: release manifest must be a YAML object")
            continue

        missing = REQUIRED_RELEASE_FIELDS - set(release.keys())
        if missing:
            errors.append(f"{manifest.name}: missing fields: {sorted(missing)}")
            continue

        frozen_at = release.get("frozen_at")
        if frozen_at and not is_iso_datetime(str(frozen_at)):
            errors.append(f"{manifest.name}: frozen_at must be ISO datetime")

        manifest_counts = release.get("registry_counts")
        if not isinstance(manifest_counts, dict):
            errors.append(f"{manifest.name}: registry_counts must be a mapping")
            continue

        expected_counts = {
            "authors": len(registry_files["authors"]),
            "objects": len(registry_files["objects"]),
            "sources": len(registry_files["sources"]),
            "relations": len(registry_files["relations"]),
        }

        for key, expected in expected_counts.items():
            if manifest_counts.get(key) != expected:
                errors.append(f"{manifest.name}: registry_counts.{key} expected {expected} got {manifest_counts.get(key)}")

        receipt_counts = manifest_counts.get("receipts")
        if not isinstance(receipt_counts, dict):
            errors.append(f"{manifest.name}: registry_counts.receipts must be a mapping")
            continue

        for key, expected in ((k, len(v)) for k, v in receipt_files.items()):
            if receipt_counts.get(key) != expected:
                errors.append(
                    f"{manifest.name}: registry_counts.receipts.{key} expected {expected} got {receipt_counts.get(key)}"
                )

        id_manifest = release.get("id_manifest")
        if not isinstance(id_manifest, dict):
            errors.append(f"{manifest.name}: id_manifest must be a mapping")
            continue

        expected_ids = {
            "authors": _id_values(registry_files["authors"], "author_id"),
            "objects": _id_values(registry_files["objects"], "object_id"),
            "sources": _id_values(registry_files["sources"], "source_id"),
            "relations": _id_values(registry_files["relations"], "relation_id"),
        }
        for key, expected in expected_ids.items():
            if sorted(id_manifest.get(key, [])) != expected:
                errors.append(f"{manifest.name}: id_manifest.{key} does not match registry IDs")

        receipt_manifest = release.get("receipt_manifest")
        if not isinstance(receipt_manifest, dict):
            errors.append(f"{manifest.name}: receipt_manifest must be a mapping")
            continue

        for key, files in receipt_files.items():
            expected_paths = sorted(str(path.relative_to(ROOT)) for path in files)
            if sorted(receipt_manifest.get(key, [])) != expected_paths:
                errors.append(f"{manifest.name}: receipt_manifest.{key} does not match receipt files")

        seams_file = release.get("open_seams_file")
        if seams_file and not (ROOT / seams_file).exists():
            errors.append(f"{manifest.name}: open_seams_file does not resolve: {seams_file}")

    return errors
