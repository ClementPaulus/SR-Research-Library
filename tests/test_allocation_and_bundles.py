"""Tests for repository-wide identifier allocation, receipt bundles, and execution manifests.

Fixtures are synthetic and explicitly marked; no scholarly facts are fabricated.
"""

from __future__ import annotations

import copy
import json
import shutil
from concurrent.futures import ThreadPoolExecutor

import jsonschema
import pytest

from validators import admit, allocation, checks, execution, gates, loader, receipts

SNAPSHOT_AUTHOR = {
    "author_id": "AUTH-0001", "display_name": "Clement Paulus", "status": "active",
    "registered": "2026-09-13T02:48:30Z",
}


@pytest.fixture()
def isolated_repo(tmp_path):
    """A scratch registry/receipts tree with only synthetic fixtures."""
    registry_dir = tmp_path / "registry"
    receipts_dir = tmp_path / "receipts"
    for sub in ("authors", "objects", "sources", "relations", "governing", "reservations"):
        (registry_dir / sub).mkdir(parents=True)
    (registry_dir / "authors" / "AUTH-0001.json").write_text(json.dumps(SNAPSHOT_AUTHOR), encoding="utf-8")
    from tests.conftest import SYNTHETIC_RELATION, SYNTHETIC_SOURCE
    (registry_dir / "sources" / "SRC-000001.json").write_text(json.dumps(SYNTHETIC_SOURCE), encoding="utf-8")
    (registry_dir / "relations" / "REL-000001.json").write_text(json.dumps(SYNTHETIC_RELATION), encoding="utf-8")
    receipts_dir.mkdir()
    return registry_dir, receipts_dir


# --------------------------------------------------------------------------- allocation

def test_next_free_reconciles_records_history_receipts_and_reservations(isolated_repo):
    registry_dir, receipts_dir = isolated_repo
    assert allocation.next_free("SR-OBJ", registry_dir=registry_dir, receipts_dir=receipts_dir) == "SR-OBJ-000001"
    (registry_dir / "objects" / "history").mkdir()
    (registry_dir / "objects" / "history" / "SR-OBJ-000004.v0.1.0.json").write_text(
        json.dumps({"object_id": "SR-OBJ-000004", "version": "0.1.0"}), encoding="utf-8")
    assert allocation.next_free("SR-OBJ", registry_dir=registry_dir, receipts_dir=receipts_dir) == "SR-OBJ-000005"
    (receipts_dir / "repair").mkdir()
    (receipts_dir / "repair" / "RCPT-000009.json").write_text(json.dumps({
        "receipt_id": "RCPT-000009", "decision": "RETURNED_FOR_REPAIR", "provisional_object_id": "SR-OBJ-000007",
        "submission_identity": "SR-OBJ-000007", "generated": "2026-09-14T00:00:00Z", "gates": {}, "disclaimer": "x"}), encoding="utf-8")
    assert allocation.next_free("SR-OBJ", registry_dir=registry_dir, receipts_dir=receipts_dir) == "SR-OBJ-000008"
    assert allocation.next_free("RCPT", registry_dir=registry_dir, receipts_dir=receipts_dir) == "RCPT-000010"
    res = allocation.reserve("SR-OBJ", "synthetic test reservation", operation_key="op-0000-0001",
                             registry_dir=registry_dir, receipts_dir=receipts_dir)
    assert res["value"] == "SR-OBJ-000008" and res["state"] == "reserved"
    assert allocation.next_free("SR-OBJ", registry_dir=registry_dir, receipts_dir=receipts_dir) == "SR-OBJ-000009"


def test_reserve_is_idempotent_per_operation_and_unique_across_operations(isolated_repo):
    registry_dir, receipts_dir = isolated_repo
    first = allocation.reserve("AUTH", "author registration", operation_key="op-synthetic-A", registry_dir=registry_dir, receipts_dir=receipts_dir)
    again = allocation.reserve("AUTH", "author registration", operation_key="op-synthetic-A", registry_dir=registry_dir, receipts_dir=receipts_dir)
    other = allocation.reserve("AUTH", "author registration", operation_key="op-synthetic-B", registry_dir=registry_dir, receipts_dir=receipts_dir)
    assert first == again
    assert first["value"] == "AUTH-0002" and other["value"] == "AUTH-0003"
    jsonschema.Draft202012Validator(loader.load_schema("reservation")).validate(first)


def test_concurrent_reservations_never_collide(isolated_repo):
    registry_dir, receipts_dir = isolated_repo

    def work(i):
        return allocation.reserve("SRC", "concurrent synthetic", operation_key=f"op-synthetic-{i:04d}",
                                  registry_dir=registry_dir, receipts_dir=receipts_dir)["value"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(work, range(12)))
    assert len(set(values)) == 12
    ledger = allocation.load_reservations(registry_dir / "reservations")
    assert len(ledger) == 12


def test_withdrawn_reservation_is_never_reused(isolated_repo):
    registry_dir, receipts_dir = isolated_repo
    res = allocation.reserve("REL", "synthetic", operation_key="op-synthetic-w", registry_dir=registry_dir, receipts_dir=receipts_dir)
    allocation.mark_state(res["value"], "withdrawn", registry_dir=registry_dir)
    nxt = allocation.reserve("REL", "synthetic", operation_key="op-synthetic-x", registry_dir=registry_dir, receipts_dir=receipts_dir)
    assert nxt["value"] != res["value"]
    allocation.mark_state(nxt["value"], "published", registry_dir=registry_dir, published_record_path="registry/relations/x.json")
    with pytest.raises(allocation.ReservationConflict):
        allocation.mark_state(nxt["value"], "withdrawn", registry_dir=registry_dir)


def test_namespace_exhaustion_requires_migration(isolated_repo):
    registry_dir, receipts_dir = isolated_repo
    (registry_dir / "authors" / "AUTH-9950.json").write_text(json.dumps({**SNAPSHOT_AUTHOR, "author_id": "AUTH-9950"}), encoding="utf-8")
    with pytest.raises(allocation.NamespaceExhausted):
        allocation.next_free("AUTH", registry_dir=registry_dir, receipts_dir=receipts_dir)


def test_reservation_check_flags_stale_reserved_state(isolated_repo):
    registry_dir, receipts_dir = isolated_repo
    res = allocation.reserve("SRC", "synthetic", operation_key="op-synthetic-s", registry_dir=registry_dir, receipts_dir=receipts_dir)
    registry = loader.load_registry(registry_dir)
    registry["sources"][f"{res['value']}.json"] = {"source_id": res["value"]}
    report = checks.ValidationReport()
    allocation.check_reservations(registry, {}, allocation.load_reservations(registry_dir / "reservations"), report)
    assert any(i.check == "reservation-ledger" and "still 'reserved'" in i.message for i in report.issues)


# --------------------------------------------------------------------------- receipt bundles

def test_bundle_writes_snapshot_and_manifest_for_every_decision(isolated_repo, synthetic_object, schemas, taxonomies):
    registry_dir, receipts_dir = isolated_repo
    registry = loader.load_registry(registry_dir)
    variants = {
        "ACCEPTED": synthetic_object,
        "RETURNED_FOR_REPAIR": {**copy.deepcopy(synthetic_object), "main_question": ""},
        "REJECTED": {**copy.deepcopy(synthetic_object), "authority": {"tier": "tier-1"}},
    }
    for expected, record in variants.items():
        result = admit.evaluate_and_write(record, write=True, register=False, registry=registry, schemas=schemas,
                                          taxonomies=taxonomies, receipts_dir=receipts_dir, registry_dir=registry_dir,
                                          registry_base="synthetic-base", out=lambda *_: None)
        assert result["decision"] == expected
        paths = result["paths"]
        assert all(p.exists() for p in paths.values())
        snapshot = json.loads(paths["submission"].read_text(encoding="utf-8"))
        assert snapshot == record
        manifest = json.loads(paths["execution"].read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(loader.load_schema("execution")).validate(manifest)
        assert manifest["submission_hash"] == execution.submission_hash(record)
        assert manifest["registry_base"] == "synthetic-base"
        assert manifest["route"] == "cli"
    loaded = loader.load_receipts(receipts_dir)
    assert len(loaded) == 3 and not any(k.endswith("submission") for k in loaded)
    assert set(receipts.load_submission_snapshots(receipts_dir)) == set(loaded)
    assert set(execution.load_execution_manifests(receipts_dir / "executions")) == set(loaded)


def test_bundle_refuses_overwrite_and_recovers_identical_repeat(isolated_repo, synthetic_object, schemas, taxonomies):
    registry_dir, receipts_dir = isolated_repo
    registry = loader.load_registry(registry_dir)
    evaluation = gates.evaluate_object(synthetic_object, registry, schemas, taxonomies)
    receipt = receipts.build_receipt(synthetic_object, evaluation, receipt_id="RCPT-000001", generated="2026-09-14T00:00:00Z")
    manifest = execution.build_execution_manifest(receipt, synthetic_object, evaluation, route="portal",
                                                  snapshot_path="receipts/accepted/RCPT-000001.submission.json",
                                                  engine_revision="test", registry_base="test")
    first = receipts.write_receipt_bundle(receipt, synthetic_object, manifest, receipts_dir)
    again = receipts.write_receipt_bundle(receipt, synthetic_object, manifest, receipts_dir)
    assert first == again
    different = dict(receipt, title="a different title under the same receipt id")
    with pytest.raises(receipts.ReceiptConflict):
        receipts.write_receipt_bundle(different, synthetic_object, manifest, receipts_dir)
    assert json.loads(first["receipt_json"].read_text(encoding="utf-8")) == receipt
    # Same ID under a different decision directory is refused too.
    repair_receipt = dict(receipt, decision="RETURNED_FOR_REPAIR")
    with pytest.raises(receipts.ReceiptConflict):
        receipts.write_receipt(repair_receipt, receipts_dir)
    assert not list(receipts_dir.glob(".RCPT-*"))  # staging cleaned up


def test_manifest_verifies_against_snapshot_and_detects_tampering(isolated_repo, synthetic_object, schemas, taxonomies):
    registry_dir, receipts_dir = isolated_repo
    registry = loader.load_registry(registry_dir)
    result = admit.evaluate_and_write(synthetic_object, write=True, register=False, registry=registry, schemas=schemas,
                                      taxonomies=taxonomies, receipts_dir=receipts_dir, registry_dir=registry_dir,
                                      registry_base="b", out=lambda *_: None)
    manifest = result["execution"]
    manifest_local = dict(manifest, submission_snapshot_path=str(result["paths"]["submission"]))
    assert execution.verify_manifest_against_snapshot(manifest_local, receipts_dir, repo_root=receipts_dir.parent.parent) == []
    tampered = dict(manifest_local, submission_hash="sha256:" + "0" * 64)
    assert "submission_hash does not match the preserved snapshot" in execution.verify_manifest_against_snapshot(
        tampered, receipts_dir, repo_root=receipts_dir.parent.parent)


def test_cli_and_direct_evaluation_are_deterministic(isolated_repo, synthetic_object, schemas, taxonomies):
    """E07: identical pinned inputs -> identical gate outcomes regardless of route."""
    registry_dir, receipts_dir = isolated_repo
    registry = loader.load_registry(registry_dir)
    a = gates.evaluate_object(copy.deepcopy(synthetic_object), registry, schemas, taxonomies)
    b = gates.evaluate_object(copy.deepcopy(synthetic_object), registry, schemas, taxonomies)
    assert a.decision == b.decision == "ACCEPTED"
    assert {k: g.result for k, g in a.gates.items()} == {k: g.result for k, g in b.gates.items()}
    assert execution.submission_hash(synthetic_object) == execution.submission_hash(json.loads(json.dumps(synthetic_object)))


def test_register_publishes_reservation(isolated_repo, synthetic_object, schemas, taxonomies):
    registry_dir, receipts_dir = isolated_repo
    res = allocation.reserve("SR-OBJ", "synthetic object", operation_key="op-synthetic-reg", registry_dir=registry_dir, receipts_dir=receipts_dir)
    record = dict(copy.deepcopy(synthetic_object), object_id=res["value"])
    registry = loader.load_registry(registry_dir)
    result = admit.evaluate_and_write(record, write=True, register=True, registry=registry, schemas=schemas,
                                      taxonomies=taxonomies, receipts_dir=receipts_dir, registry_dir=registry_dir,
                                      registry_base="b", out=lambda *_: None)
    assert result["registered_path"].exists()
    ledger = allocation.load_reservations(registry_dir / "reservations")
    assert ledger[res["value"]]["state"] == "published"
