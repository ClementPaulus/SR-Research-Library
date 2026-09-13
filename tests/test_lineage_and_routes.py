"""Tests for typed source lineage, reserved ObjectIDs, and the /questions route."""

from __future__ import annotations

import copy

import jsonschema

from validators import checks, loader, sitegen


def _registry(base_registry, synthetic_object):
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = copy.deepcopy(synthetic_object)
    return registry


def _validate(registry, schemas, taxonomies, receipts=None):
    return checks.validate_registry(registry, schemas, taxonomies, released_hashes={}, receipts=receipts or {})


def test_source_lineage_fields_validate(base_registry, schemas, taxonomies, synthetic_object):
    registry = _registry(base_registry, synthetic_object)
    src = registry["sources"]["SRC-000001.json"]
    src.update({
        "version": "1.0", "status": "active", "identifier": {"doi": "10.5281/zenodo.1000001"},
        "concept_doi": "10.5281/zenodo.1000000", "version_doi": "10.5281/zenodo.1000001",
        "related_dois": [{"doi": "10.5281/zenodo.0999999", "relation": "earlier_version", "notes": "synthetic"}],
        "supersedes": [], "superseded_by": None,
    })
    jsonschema.Draft202012Validator(schemas["source"]).validate(src)
    assert _validate(registry, schemas, taxonomies).ok


def test_source_lineage_doi_consistency(base_registry, schemas, taxonomies, synthetic_object):
    registry = _registry(base_registry, synthetic_object)
    src = registry["sources"]["SRC-000001.json"]
    src.update({"identifier": {"doi": "10.5281/zenodo.1"}, "concept_doi": "10.5281/zenodo.2", "version_doi": "10.5281/zenodo.3"})
    report = _validate(registry, schemas, taxonomies)
    assert any("neither concept_doi nor version_doi" in i.message for i in report.for_check("source-lineage"))
    src.update({"concept_doi": "10.5281/zenodo.1", "version_doi": "10.5281/zenodo.1"})
    report = _validate(registry, schemas, taxonomies)
    assert any("identical" in i.message for i in report.for_check("source-lineage"))
    src.update({"version_doi": "10.5281/zenodo.9", "related_dois": [{"doi": "10.5281/zenodo.1", "relation": "other"}]})
    assert any("repeats" in i.message for i in _validate(registry, schemas, taxonomies).for_check("source-lineage"))


def test_source_supersession_is_append_preserving(base_registry, schemas, taxonomies, synthetic_object):
    registry = _registry(base_registry, synthetic_object)
    old = registry["sources"]["SRC-000001.json"]
    new = copy.deepcopy(old)
    new.update({"source_id": "SRC-000002", "version": "2.0", "supersedes": ["SRC-000001"]})
    registry["sources"]["SRC-000002.json"] = new
    report = _validate(registry, schemas, taxonomies)
    assert report.for_check("source-lineage")  # old record still active and lacks superseded_by
    old.update({"status": "superseded", "superseded_by": "SRC-000002"})
    assert _validate(registry, schemas, taxonomies).ok
    del registry["sources"]["SRC-000001.json"]
    report = _validate(registry, schemas, taxonomies)
    assert any("not preserved" in i.message for i in report.for_check("source-lineage"))


def test_reserved_object_ids_are_not_reused(base_registry, schemas, taxonomies, synthetic_object):
    registry = _registry(base_registry, synthetic_object)
    repair_receipt = {"receipt_id": "RCPT-000900", "decision": "RETURNED_FOR_REPAIR",
                      "provisional_object_id": "SR-OBJ-000001", "submission_identity": "SR-OBJ-000001"}
    report = _validate(registry, schemas, taxonomies, receipts={"RCPT-000900": repair_receipt})
    assert report.for_check("reserved-identities")
    accepted = {"receipt_id": "RCPT-000901", "decision": "ACCEPTED", "object_id": "SR-OBJ-000001", "submission_identity": "SR-OBJ-000001"}
    assert _validate(registry, schemas, taxonomies, receipts={"RCPT-000900": repair_receipt, "RCPT-000901": accepted}).ok


def test_live_registry_reserves_returned_ids():
    """IDs on non-accepted receipts stay reserved for those submissions."""
    receipts = loader.load_receipts()
    returned = {r["provisional_object_id"] for r in receipts.values() if r["decision"] == "RETURNED_FOR_REPAIR"}
    assert {"SR-OBJ-000016", "SR-OBJ-000017", "SR-OBJ-000019"} <= returned
    registered = {o["object_id"] for o in loader.load_registry()["objects"].values()}
    assert not (returned & registered)


def test_question_slug_policy():
    q = "Why does the contract-first measurement framework require its bounded trace, frozen contract, typed return, kernel, seam, authority, and stance architecture?"
    slug = sitegen.question_slug(q)
    assert len(slug) <= 80 and not slug.endswith("-") and slug.startswith("why-does-the-contract-first")
    assert sitegen.question_slug("Réditus — what returns?") == "reditus-what-returns"
    assert sitegen.question_slug("A b") == sitegen.question_slug("a   B?")


def test_questions_route_generated(tmp_path, base_registry, synthetic_object):
    registry = _registry(base_registry, synthetic_object)
    sitegen.generate_site(tmp_path, registry, receipts={})
    slug = sitegen.question_slug(synthetic_object["main_question"])
    page = tmp_path / "questions" / f"{slug}.html"
    assert page.exists() and "SR-OBJ-000001" in page.read_text(encoding="utf-8")
    assert slug in (tmp_path / "questions" / "index.html").read_text(encoding="utf-8")
