"""Tests for the governing-reference registry (SR-GOV-*), its validators, and its relation to Tier-2 objects."""

from __future__ import annotations

import copy

import jsonschema
import pytest

from validators import checks, gates, loader, manifest, sitegen

GOVERNING = {
    "governing_id": "SR-GOV-000001",
    "title": "Synthetic governing reference used only for library self-tests",
    "source_id": "SRC-000001",
    "version": "Synthetic v1.0",
    "status": "active",
    "governing_role": ["specification"],
    "authority_scope": {"tier_1": [], "tier_0": ["Synthetic Tier-0 burden: fixture only."]},
    "source_role": "Synthetic fixture; carries no real authority.",
    "immutable_record": True,
    "active_from": "2026-09-13T00:00:00Z",
    "supersedes": None,
    "superseded_by": None,
    "doi": None,
    "canonical_link": None,
    "scope": "Library self-testing only.",
    "non_goal": "Establishes nothing about the corpus.",
    "missingness": [],
    "notes": "SYNTHETIC: test fixture only.",
}


@pytest.fixture()
def governing_record():
    return copy.deepcopy(GOVERNING)


@pytest.fixture()
def base_registry(base_registry, synthetic_object):
    """Synthetic registry including the synthetic object so REL-000001 resolves."""
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = copy.deepcopy(synthetic_object)
    return registry


def _validate(registry, schemas, taxonomies, released=None):
    return checks.validate_registry(registry, schemas, taxonomies, released_hashes=released or {})


def test_valid_governing_record(base_registry, schemas, taxonomies, governing_record):
    jsonschema.Draft202012Validator(schemas["governing"]).validate(governing_record)
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-0/SR-GOV-000001.json"] = governing_record
    assert _validate(registry, schemas, taxonomies).ok


def test_invalid_governing_id(schemas, governing_record):
    governing_record["governing_id"] = "GOV-1"
    errors = list(jsonschema.Draft202012Validator(schemas["governing"]).iter_errors(governing_record))
    assert any(e.validator == "pattern" for e in errors)


def test_missing_source_reference(base_registry, schemas, taxonomies, governing_record):
    governing_record["source_id"] = "SRC-000999"
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-0/SR-GOV-000001.json"] = governing_record
    report = _validate(registry, schemas, taxonomies)
    assert [i.record for i in report.for_check("source-references")] == ["governing/tier-0/SR-GOV-000001.json"]


def test_invalid_authority_scope(base_registry, schemas, taxonomies, governing_record):
    del governing_record["authority_scope"]["tier_1"]
    errors = list(jsonschema.Draft202012Validator(schemas["governing"]).iter_errors(governing_record))
    assert any(e.validator == "required" for e in errors)
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-0/SR-GOV-000001.json"] = governing_record
    assert _validate(registry, schemas, taxonomies).for_check("governing-authority-scope")
    # A record whose scope does not match its view directory is flagged.
    fixed = copy.deepcopy(GOVERNING)
    registry["governing"] = {"tier-1/SR-GOV-000001.json": fixed}
    assert _validate(registry, schemas, taxonomies).for_check("governing-view")


def test_mixed_tier1_tier0_record(base_registry, schemas, taxonomies, governing_record):
    governing_record["authority_scope"] = {"tier_1": ["Synthetic Tier-1 burden."], "tier_0": ["Synthetic Tier-0 burden."]}
    jsonschema.Draft202012Validator(schemas["governing"]).validate(governing_record)
    registry = copy.deepcopy(base_registry)
    registry["governing"]["mixed/SR-GOV-000001.json"] = governing_record
    assert _validate(registry, schemas, taxonomies).ok
    assert set(sitegen._gov_tags(governing_record)) >= {"Tier-1-bearing", "Tier-0-bearing", "mixed"}


def test_immutable_released_record(base_registry, schemas, taxonomies, governing_record):
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-0/SR-GOV-000001.json"] = governing_record
    released = {"SR-GOV-000001": checks.governing_immutable_hash(governing_record)}
    assert _validate(registry, schemas, taxonomies, released).ok
    # Status may change after release; historical meaning may not.
    governing_record["status"] = "historical"
    assert _validate(registry, schemas, taxonomies, released).ok
    governing_record["scope"] = "Silently rewritten scope (synthetic)."
    assert _validate(registry, schemas, taxonomies, released).for_check("governing-immutability")
    # A released record may not disappear.
    registry["governing"] = {}
    assert _validate(registry, schemas, taxonomies, released).for_check("governing-immutability")


def test_supersession_preserves_old_record(base_registry, schemas, taxonomies, governing_record):
    old = governing_record
    new = copy.deepcopy(governing_record)
    new.update({"governing_id": "SR-GOV-000002", "version": "Synthetic v2.0", "supersedes": "SR-GOV-000001"})
    registry = copy.deepcopy(base_registry)
    registry["governing"] = {"tier-0/SR-GOV-000001.json": old, "tier-0/SR-GOV-000002.json": new}
    # Old record must acknowledge the supersession and leave active status.
    assert _validate(registry, schemas, taxonomies).for_check("governing-supersession")
    old["superseded_by"] = "SR-GOV-000002"
    old["status"] = "superseded"
    released = {"SR-GOV-000001": checks.governing_immutable_hash(GOVERNING)}
    assert _validate(registry, schemas, taxonomies, released).ok
    # Removing the old record instead of preserving it is a violation.
    del registry["governing"]["tier-0/SR-GOV-000001.json"]
    assert _validate(registry, schemas, taxonomies, released).for_check("governing-supersession")


def test_object_with_valid_governing_ref(base_registry, schemas, taxonomies, governing_record, synthetic_object):
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-0/SR-GOV-000001.json"] = governing_record
    synthetic_object["governing_refs"] = ["SR-GOV-000001"]
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    assert _validate(registry, schemas, taxonomies).ok
    evaluation = gates.evaluate_object(synthetic_object, registry, schemas, taxonomies)
    assert evaluation.decision == "ACCEPTED"


def test_object_with_nonexistent_governing_ref(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["governing_refs"] = ["SR-GOV-000999"]
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    assert _validate(registry, schemas, taxonomies).for_check("governing-references")
    evaluation = gates.evaluate_object(synthetic_object, registry, schemas, taxonomies)
    assert evaluation.decision == "RETURNED_FOR_REPAIR"
    assert evaluation.gates["F"].result == "BLOCKED"


def test_no_authority_inheritance(base_registry, schemas, taxonomies, governing_record, synthetic_object):
    """A Tier-2 object that lists a Tier-1-bearing governing reference stays Tier-2."""
    governing_record["authority_scope"] = {"tier_1": ["Synthetic Tier-1 burden."], "tier_0": []}
    registry = copy.deepcopy(base_registry)
    registry["governing"]["tier-1/SR-GOV-000001.json"] = governing_record
    synthetic_object["governing_refs"] = ["SR-GOV-000001"]
    evaluation = gates.evaluate_object(synthetic_object, registry, schemas, taxonomies)
    assert evaluation.decision == "ACCEPTED"
    assert synthetic_object["authority"]["tier"] == "tier-2"
    # Any attempt to claim the referenced authority is rejected by Gate B / the schema.
    promoted = copy.deepcopy(synthetic_object)
    promoted["authority"]["tier"] = "tier-1"
    assert gates.evaluate_object(promoted, registry, schemas, taxonomies).decision == "REJECTED"
    assert list(jsonschema.Draft202012Validator(schemas["object"]).iter_errors(promoted))


def test_release_manifest_records_governing_hashes(tmp_path):
    data = manifest.build_release_manifest("SR-LIBRARY.v9.9.9-test", open_seams=[], migration_notes=[])
    registry = loader.load_registry()
    for record in registry["governing"].values():
        assert data["governing_immutable_hashes"][record["governing_id"]] == checks.governing_immutable_hash(record)
    assert data["governing_count"] == len(registry["governing"])


def test_live_governing_registry_is_consistent(schemas, taxonomies):
    """Every live governing record validates, resolves its source, and sits in the view matching its scope."""
    registry = loader.load_registry()
    assert registry["governing"], "governing registry should be populated"
    report = checks.validate_registry(registry, schemas, taxonomies,
                                      released_hashes=loader.released_governing_hashes())
    assert report.ok, [str(i) for i in report.issues]
    for record in registry["governing"].values():
        assert record["status"] in ("active", "superseded", "historical", "candidate", "unresolved")
        if record["status"] == "candidate":
            assert record["missingness"] or "candidate" in record["source_role"].lower()
