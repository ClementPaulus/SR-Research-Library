"""Tests for author records, registry validation, and reference integrity."""

from __future__ import annotations

import copy

import jsonschema
import pytest

from validators import checks, loader


def test_valid_author_record(schemas):
    """AUTH-0001 is registered correctly and validates against the schema."""
    registry = loader.load_registry()
    record = registry["authors"]["AUTH-0001.json"]
    jsonschema.Draft202012Validator(schemas["author"]).validate(record)
    assert record["author_id"] == "AUTH-0001"
    assert record["display_name"] == "Clement Paulus"
    assert record["orcid"] == "0009-0000-6069-8234"
    assert record["status"] == "active"


def test_invalid_author_record(schemas):
    """An author record with a malformed ID and unknown status fails validation."""
    bad = {
        "author_id": "AUTHOR-1",
        "display_name": "",
        "status": "unknown-status",
        "registered": "13-09-2026",
    }
    validator = jsonschema.Draft202012Validator(schemas["author"])
    errors = list(validator.iter_errors(bad))
    assert errors, "invalid author record must produce schema errors"


def test_duplicate_author_id(base_registry, schemas, taxonomies):
    """Two files declaring the same AuthorID are reported as duplicates."""
    registry = copy.deepcopy(base_registry)
    duplicate = copy.deepcopy(registry["authors"]["AUTH-0001.json"])
    duplicate["display_name"] = "Duplicate Identity (synthetic)"
    registry["authors"]["AUTH-0001-copy.json"] = duplicate
    report = checks.ValidationReport()
    checks.check_unique_ids(registry, report)
    assert any("duplicate identifier 'AUTH-0001'" in i.message
               for i in report.for_check("unique-ids"))


def test_valid_research_object(base_registry, schemas, taxonomies, synthetic_object):
    """A structurally complete synthetic object passes every validation check."""
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert report.ok, [str(i) for i in report.issues]


def test_missing_main_question(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["main_question"] = ""
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert report.for_check("missing-main-question")


def test_missing_source_boundary(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    del synthetic_object["source_boundary"]
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert report.for_check("missing-source-boundary")


def test_invalid_tier2_class(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["tier2_class"]["primary"] = "tier-3-metaclass"
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert any("tier2_class.primary" in i.message
               for i in report.for_check("taxonomy-references"))


def test_unknown_taxonomy_term(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["evidence_mode"]["primary"] = "vibes-based"
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert any("'vibes-based'" in i.message
               for i in report.for_check("taxonomy-references"))


def test_broken_source_id(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["source_ids"] = ["SRC-999999"]
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert any("SRC-999999" in i.message for i in report.for_check("source-references"))


def test_broken_relation_id(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["relations"] = ["REL-999999"]
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert any("REL-999999" in i.message for i in report.for_check("relation-references"))


def test_broken_relation_endpoint(base_registry, schemas, taxonomies, synthetic_object,
                                  synthetic_relation):
    """A registered relation pointing at an unregistered entity is broken."""
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    synthetic_relation["relation_id"] = "REL-000002"
    synthetic_relation["to_id"] = "SR-OBJ-777777"
    registry["relations"]["REL-000002.json"] = synthetic_relation
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert any("SR-OBJ-777777" in i.message for i in report.for_check("broken-relations"))


def test_duplicate_object_collision(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    clone = copy.deepcopy(synthetic_object)
    clone["object_id"] = "SR-OBJ-000002"
    registry["objects"]["SR-OBJ-000002.json"] = clone
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert report.for_check("duplicate-object-collisions")


def test_date_and_version_format_checks(base_registry, schemas, taxonomies, synthetic_object):
    registry = copy.deepcopy(base_registry)
    synthetic_object["date"] = "13/09/2026"
    synthetic_object["version"] = "v1"
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    report = checks.validate_registry(registry, schemas, taxonomies)
    assert report.for_check("date-formats")
    assert report.for_check("version-formats")


def test_current_registry_is_clean():
    """The committed registry (the source of truth) validates with no issues."""
    report = checks.validate_registry()
    assert report.ok, [str(i) for i in report.issues]
