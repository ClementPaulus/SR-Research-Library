"""Calibration and contract tests for generated bridge candidates."""

from __future__ import annotations

import copy
import json

from validators import bridges, loader, sitegen


def _live_candidates():
    registry = loader.load_registry()
    return registry, bridges.generate_bridge_candidates(registry["objects"], registry["relations"])


def _pair(candidates, first, second):
    return next(candidate for candidate in candidates
                if {candidate["object_a"], candidate["object_b"]} == {first, second})


def test_declared_sequences_are_detected_and_marked():
    _, candidates = _live_candidates()
    for first, second in (("SR-OBJ-000001", "SR-OBJ-000002"),
                          ("SR-OBJ-000002", "SR-OBJ-000003"),
                          ("SR-OBJ-000005", "SR-OBJ-000006")):
        candidate = _pair(candidates, first, second)
        assert candidate["already_declared"] is True
        assert candidate["strength"] in {bridges.LOW, bridges.MEDIUM, bridges.HIGH}


def test_burden_chain_is_directional_and_recovered():
    _, candidates = _live_candidates()
    first = _pair(candidates, "SR-OBJ-000007", "SR-OBJ-000008")
    second = _pair(candidates, "SR-OBJ-000008", "SR-OBJ-000009")
    assert first["direction"] == "SR-OBJ-000007 -> SR-OBJ-000008"
    assert second["direction"] == "SR-OBJ-000008 -> SR-OBJ-000009"
    assert "handoff_to" in first["candidate_relation_types"]
    assert "handoff_to" in second["candidate_relation_types"]


def test_broad_classification_overlap_does_not_make_high_candidate():
    _, candidates = _live_candidates()
    broad = [candidate for candidate in candidates if candidate["strength"] == bridges.HIGH]
    assert all(any(signal["type"] in {"burden_handoff", "explicit_lineage", "shared_question"}
                   for signal in candidate["signals"]) for candidate in broad)


def test_generation_is_deterministic_and_does_not_mutate_registry():
    registry = loader.load_registry()
    before = json.dumps(registry, sort_keys=True)
    first = bridges.build_bridge_projection(registry)
    second = bridges.build_bridge_projection(registry)
    assert first == second
    assert json.dumps(registry, sort_keys=True) == before


def test_historical_or_source_text_is_not_a_detector_input():
    registry = loader.load_registry()
    baseline = bridges.build_bridge_projection(registry)
    changed = copy.deepcopy(registry)
    changed["sources"]["SRC-000012.json"]["source_native_claims"].append("return physics diagnostic boundary")
    changed["objects"]["SR-OBJ-000007.json"]["source_ids"] = ["SRC-000012"]
    assert bridges.build_bridge_projection(changed) == baseline


def test_object_page_separates_visible_generated_bridges(tmp_path):
    registry = loader.load_registry()
    sitegen.generate_site(tmp_path, registry, receipts={})
    page = (tmp_path / "objects" / "SR-OBJ-000008.html").read_text(encoding="utf-8")
    assert "Possible structural connections" in page
    assert "Generated retrieval suggestion." in page
    assert "Relations</h2>" in page
    projection = json.loads((tmp_path / "data" / "bridge_candidates.json").read_text(encoding="utf-8"))
    assert projection["generated"] is True
    assert projection["source"] == "registry"