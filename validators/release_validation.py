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
    manifests = sorted((ROOT / "releases").glob("*.manifest.yaml"))
    if not manifests:
        return ["no release manifest files found"]

    for manifest in manifests:
        release = load_yaml(manifest)
        if not isinstance(release, dict):
            errors.append(f"{manifest.name}: release manifest must be a YAML object")
            continue

        missing = REQUIRED_RELEASE_FIELDS - set(release.keys())
        if missing:
            errors.append(f"{manifest.name}: missing fields: {sorted(missing)}")

        frozen_at = release.get("frozen_at")
        if frozen_at and not is_iso_datetime(str(frozen_at)):
            errors.append(f"{manifest.name}: frozen_at must be ISO datetime")

    return errors
