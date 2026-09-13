from __future__ import annotations

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


def validate_release_manifest() -> list[str]:
    errors: list[str] = []
    release = load_yaml(ROOT / "releases" / "SR-LIBRARY.v0.1.0-pre.manifest.yaml")

    if not isinstance(release, dict):
        return ["release manifest must be a YAML object"]

    missing = REQUIRED_RELEASE_FIELDS - set(release.keys())
    if missing:
        errors.append(f"release manifest missing fields: {sorted(missing)}")

    frozen_at = release.get("frozen_at")
    if frozen_at and not is_iso_datetime(str(frozen_at)):
        errors.append("release manifest frozen_at must be ISO datetime")

    return errors
