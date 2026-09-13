"""Tests for the seven admission gates, decision logic, and receipts."""

from __future__ import annotations

import copy

import jsonschema
import pytest

from validators import gates, loader, receipts


def evaluate(record, registry, schemas, taxonomies):
    return gates.evaluate_object(record, registry, schemas, taxonomies)


def test_accepted_object_receipt(base_registry, schemas, taxonomies, synthetic_object):
    evaluation = evaluate(synthetic_object, base_registry, schemas, taxonomies)
    assert evaluation.decision == "ACCEPTED"
    assert all(g.result == "PASS" for g in evaluation.gates.values())

    receipt = receipts.build_receipt(synthetic_object, evaluation,
                                     receipt_id="RCPT-000001",
                                     generated="2026-09-13T00:00:00Z")
    jsonschema.Draft202012Validator(schemas["receipt"]).validate(receipt)
    assert receipt["decision"] == "ACCEPTED"
    assert receipt["object_id"] == "SR-OBJ-000001"
    assert receipt["author_ids"] == ["AUTH-0001"]
    assert receipt["tier2_class_primary"] == "diagnostic"
    assert "organizational conformance only" in receipt["disclaimer"]
    assert "Tier-1" in receipt["disclaimer"]

    markdown = receipts.render_receipt_markdown(receipt)
    for key in "ABCDEFG":
        assert f"Gate {key}: PASS" in markdown
    assert "Decision: ACCEPTED" in markdown
    assert "organizational conformance only" in markdown


def test_repairable_object_receipt(base_registry, schemas, taxonomies, synthetic_object):
    """Missing main question blocks admission but is repairable — not a rejection."""
    record = synthetic_object
    record["main_question"] = ""
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "RETURNED_FOR_REPAIR"
    assert evaluation.gates["D"].result == "BLOCKED"

    receipt = receipts.build_receipt(record, evaluation,
                                     receipt_id="RCPT-000002",
                                     generated="2026-09-13T00:00:00Z")
    jsonschema.Draft202012Validator(schemas["receipt"]).validate(receipt)
    assert receipt["decision"] == "RETURNED_FOR_REPAIR"
    assert receipt["provisional_object_id"] == "SR-OBJ-000001"
    assert any("main_question" in m for m in receipt["missing_structure"])
    assert receipt["exact_repair_required"]
    assert receipt["resubmission_condition"]
    assert receipt["fields_already_accepted"]

    markdown = receipts.render_receipt_markdown(receipt)
    assert "Decision: RETURNED_FOR_REPAIR" in markdown
    assert "Exact repair required" in markdown


def test_rejected_object_receipt(base_registry, schemas, taxonomies, synthetic_object):
    """A non-tier-2 authority claim violates the contract and is rejected."""
    record = synthetic_object
    record["authority"]["tier"] = "tier-1"
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "REJECTED"
    assert evaluation.gates["B"].result == "FAIL"

    receipt = receipts.build_receipt(record, evaluation,
                                     receipt_id="RCPT-000003",
                                     generated="2026-09-13T00:00:00Z")
    jsonschema.Draft202012Validator(schemas["receipt"]).validate(receipt)
    assert receipt["decision"] == "REJECTED"
    assert receipt["failed_gates"]
    assert receipt["established_violation"]
    assert "does not by itself establish that the underlying research claim is false" \
        in receipt["disclaimer"]

    markdown = receipts.render_receipt_markdown(receipt)
    assert "Decision: REJECTED" in markdown
    assert "underlying research claim is false" in markdown


def test_repair_is_not_collapsed_into_rejection(base_registry, schemas, taxonomies,
                                                synthetic_object):
    """Missing structure yields RETURNED_FOR_REPAIR, never REJECTED."""
    record = synthetic_object
    del record["authority_boundary"]
    del record["next_burden"]
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "RETURNED_FOR_REPAIR"


def test_invalid_tier2_class_is_rejected(base_registry, schemas, taxonomies, synthetic_object):
    record = synthetic_object
    record["tier2_class"]["primary"] = "tier-3-metaclass"
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "REJECTED"
    assert evaluation.gates["D"].result == "FAIL"


def test_evaluability_blocking_missingness_blocks_acceptance(base_registry, schemas,
                                                             taxonomies, synthetic_object):
    record = synthetic_object
    record["missingness"].append({
        "item": "Key evaluation dataset unavailable (synthetic scenario)",
        "class": "EVALUABILITY_BLOCKING",
    })
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "RETURNED_FOR_REPAIR"


def test_contract_violating_missingness_is_rejected(base_registry, schemas, taxonomies,
                                                    synthetic_object):
    record = synthetic_object
    record["missingness"].append({
        "item": "Original authorship deliberately withheld (synthetic scenario)",
        "class": "CONTRACT_VIOLATING",
    })
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "REJECTED"


def test_disagreement_is_not_an_admission_failure(base_registry, schemas, taxonomies,
                                                  synthetic_object, synthetic_relation):
    """An object that challenges another work and reports non-return is still ACCEPTED."""
    registry = copy.deepcopy(base_registry)
    other = copy.deepcopy(synthetic_object)
    other["object_id"] = "SR-OBJ-000002"
    other["title"] = "Synthetic second object (synthetic test fixture)"
    registry["objects"]["SR-OBJ-000002.json"] = other

    challenge = copy.deepcopy(synthetic_relation)
    challenge["relation_id"] = "REL-000002"
    challenge["relation_type"] = "challenges"
    challenge["from_id"] = "SR-OBJ-000001"
    challenge["to_id"] = "SR-OBJ-000002"
    registry["relations"]["REL-000002.json"] = challenge

    record = synthetic_object
    record["relations"] = ["REL-000001", "REL-000002"]
    record["main_question"] = ("Does the challenged synthetic structure fail to return "
                               "under the declared test conditions?")
    record["notes"] = ("SYNTHETIC: reports a negative result (non-return) and challenges "
                       "another Tier-2 work; disagreement is not an admission failure.")
    evaluation = evaluate(record, registry, schemas, taxonomies)
    assert evaluation.decision == "ACCEPTED"


def test_founder_neutral_admission(base_registry, schemas, taxonomies, synthetic_object):
    """AUTH-0001 receives identical gate results to any other registered author."""
    registry = copy.deepcopy(base_registry)
    registry["authors"]["AUTH-0002.json"] = {
        "author_id": "AUTH-0002",
        "display_name": "Synthetic Second Author (synthetic test identity)",
        "status": "active",
        "registered": "2026-09-13",
        "notes": "SYNTHETIC: test fixture only.",
    }

    founder_record = copy.deepcopy(synthetic_object)
    other_record = copy.deepcopy(synthetic_object)
    other_record["authors"] = ["AUTH-0002"]

    founder_eval = evaluate(founder_record, registry, schemas, taxonomies)
    other_eval = evaluate(other_record, registry, schemas, taxonomies)
    assert founder_eval.decision == other_eval.decision == "ACCEPTED"
    assert {k: g.result for k, g in founder_eval.gates.items()} == \
           {k: g.result for k, g in other_eval.gates.items()}

    # And a founder-authored record with the same defect gets the same non-acceptance.
    founder_record["main_question"] = ""
    other_record["main_question"] = ""
    founder_eval = evaluate(founder_record, registry, schemas, taxonomies)
    other_eval = evaluate(other_record, registry, schemas, taxonomies)
    assert founder_eval.decision == other_eval.decision == "RETURNED_FOR_REPAIR"


def test_unregistered_author_blocks_admission(base_registry, schemas, taxonomies,
                                              synthetic_object):
    record = synthetic_object
    record["authors"] = ["AUTH-0099"]
    evaluation = evaluate(record, base_registry, schemas, taxonomies)
    assert evaluation.decision == "RETURNED_FOR_REPAIR"
    assert evaluation.gates["A"].result == "BLOCKED"
