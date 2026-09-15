"""Baseline preservation (acceptance row O05).

Every historical artifact hashed in docs/portal-evidence/baseline-810f4222.json
must remain byte-identical. Portal implementation adds infrastructure; it
never rewrites released research records, receipts, schemas, taxonomies, or
manifests. New files are permitted; changed or deleted baseline files are not.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from validators import loader

MANIFEST = Path(__file__).parent.parent / "docs" / "portal-evidence" / "baseline-810f4222.json"


def test_baseline_artifacts_are_byte_identical():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed, missing = [], []
    for rel_path, expected in manifest["files"].items():
        path = loader.REPO_ROOT / rel_path
        if not path.exists():
            missing.append(rel_path)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(rel_path)
    assert not missing, f"baseline artifacts deleted: {missing}"
    assert not changed, f"baseline artifacts rewritten: {changed}"


def test_baseline_counts_match_recorded_history():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    counts = manifest["counts"]
    receipts = loader.load_receipts()
    # The live library may grow; it may never shrink below the baseline.
    assert len(loader.load_registry()["objects"]) >= counts["objects"]
    assert sum(1 for r in receipts.values() if r["decision"] == "ACCEPTED") >= counts["receipts_accepted"]
    assert sum(1 for r in receipts.values() if r["decision"] == "RETURNED_FOR_REPAIR") >= counts["receipts_repair"]
    manifests = loader.load_release_manifests()
    assert manifest["library_release"] in manifests
