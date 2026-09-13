"""Regression tests for the 2026-09 Tier-2 census, repair, and ingress pass.

These tests read the live registry and receipts; they encode the structural
rules of the pass, not the scientific content of any work.
"""

from __future__ import annotations

import hashlib
import json

from validators import bridges, loader, sitegen

LOURETTE_DOI = "10.1103/z2sl-6gcc"
HE_DOI = "10.1038/s41467-026-69958-0"
NEW_OBJECTS = [f"SR-OBJ-0000{n}" for n in range(20, 31)]
REPAIRED = ["SR-OBJ-000017", "SR-OBJ-000019"]
PEDAGOGICAL = ["SR-OBJ-000027", "SR-OBJ-000028", "SR-OBJ-000029", "SR-OBJ-000030"]


def _objects():
    return {o["object_id"]: o for o in loader.load_registry()["objects"].values()}


def _sources():
    return {s["source_id"]: s for s in loader.load_registry()["sources"].values()}


def _receipts():
    return loader.load_receipts()


def test_repaired_objects_keep_reserved_ids_and_preserve_repair_receipts():
    objects, receipts = _objects(), _receipts()
    for oid, repair_id in (("SR-OBJ-000017", "RCPT-000017"), ("SR-OBJ-000019", "RCPT-000019")):
        assert oid in objects
        assert receipts[repair_id]["decision"] == "RETURNED_FOR_REPAIR"
        assert receipts[repair_id]["provisional_object_id"] == oid
        later = [r for r in receipts.values() if r["decision"] == "ACCEPTED" and r.get("object_id") == oid]
        assert later and all(r["receipt_id"] > repair_id for r in later)
        # The blocking REPAIRABLE missingness was discharged, not deleted into silence.
        assert not any(m["class"] in ("REPAIRABLE", "EVALUABILITY_BLOCKING") for m in objects[oid]["missingness"])
        assert any(m["class"] == "UNRESOLVED_SEAM" for m in objects[oid]["missingness"])
        assert objects[oid]["maturity"] == "historical"
        assert not objects[oid]["next_burden"].startswith("Unresolved")


def test_collapse_formalism_stays_blocked_without_source_identity():
    objects, receipts = _objects(), _receipts()
    assert "SR-OBJ-000016" not in objects
    assert not any(r.get("object_id") == "SR-OBJ-000016" for r in receipts.values() if r["decision"] == "ACCEPTED")
    assert receipts["RCPT-000016"]["decision"] == "RETURNED_FOR_REPAIR"
    src = _sources()["SRC-000033"]
    assert any("mismatch" in m for m in src["missingness"])


def test_external_dois_are_not_assigned_to_local_derivative_papers():
    sources = _sources()
    assert sources["SRC-000048"]["source_type"] == "external"
    assert sources["SRC-000048"]["identifier"]["doi"] == LOURETTE_DOI
    assert sources["SRC-000051"]["source_type"] == "external"
    assert sources["SRC-000051"]["identifier"]["doi"] == HE_DOI
    for sid, external_doi in (("SRC-000049", LOURETTE_DOI), ("SRC-000052", HE_DOI)):
        local = sources[sid]
        assert local["source_type"] == "corpus-native"
        assert local["identifier"].get("doi") != external_doi
        assert local.get("concept_doi") != external_doi and local.get("version_doi") != external_doi
        assert local["source_authors"] == ["Clement Paulus"]
    # External authorship is preserved as names, never replaced by a library AuthorID.
    assert sources["SRC-000048"]["source_authors"][0] == "Sean Lourette"
    assert sources["SRC-000051"]["source_authors"][0] == "Chengping He"
    # The local memristive manuscript carries its own verified Zenodo deposit and publication state,
    # never the external article's DOI.
    assert sources["SRC-000052"]["identifier"]["doi"] == "10.5281/zenodo.22695434"
    assert sources["SRC-000052"]["concept_doi"] == "10.5281/zenodo.22695433"
    assert _objects()["SR-OBJ-000023"]["publication_state"] == "archived"


def test_new_objects_resolve_sources_and_taxonomies_and_stay_tier_2():
    registry = loader.load_registry()
    taxonomies = loader.load_taxonomies()
    sources = {s["source_id"] for s in registry["sources"].values()}
    objects = _objects()
    for oid in NEW_OBJECTS + REPAIRED:
        o = objects[oid]
        assert o["authority"]["tier"] == "tier-2"
        assert o["source_ids"] and set(o["source_ids"]) <= sources
        assert o["tier2_class"]["primary"] in taxonomies["tier2_classes"]
        assert set(o["tier2_class"]["secondary"]) <= set(taxonomies["tier2_classes"])
        assert o["domain"]["primary"] in taxonomies["domains"]
        assert set(o["domain"]["secondary"]) <= set(taxonomies["domains"])
        assert o["structural_focus"]["primary"] in taxonomies["focuses"]
        assert set(o["structural_focus"]["secondary"]) <= set(taxonomies["focuses"])
        assert o["evidence_mode"]["primary"] in taxonomies["evidence_modes"]
        assert set(o["evidence_mode"]["secondary"]) <= set(taxonomies["evidence_modes"])
        assert o["provenance"] in taxonomies["provenance_types"]
        assert o["maturity"] in taxonomies["maturity_states"]
        assert o["functional_locus"] in taxonomies["functional_loci"]
        assert o["publication_state"] in taxonomies["publication_states"]
        for gid in o.get("governing_refs", []):
            assert any(g["governing_id"] == gid for g in registry["governing"].values())


def test_every_new_object_has_an_accepted_receipt():
    accepted = {r["object_id"] for r in _receipts().values() if r["decision"] == "ACCEPTED"}
    assert set(NEW_OBJECTS + REPAIRED) <= accepted


def test_memristive_publication_update_preserves_prior_state_and_receipt():
    objects, receipts = _objects(), _receipts()
    obj = objects["SR-OBJ-000023"]
    assert obj["version"] == "1.0.1"
    history = json.loads((loader.REGISTRY_DIR / "objects" / "history" / "SR-OBJ-000023.v1.0.0.json").read_text(encoding="utf-8"))
    assert history["publication_state"] == "registered-only"
    # Metadata-only update: the scientific record is unchanged between 1.0.0 and 1.0.1.
    for key in ("claim_layers", "scope", "exclusions", "next_burden", "maturity", "authority", "evidence_mode", "source_ids"):
        assert history[key] == obj[key]
    assert receipts["RCPT-000028"]["publication_state"] == "registered-only"
    assert receipts["RCPT-000036"]["object_id"] == "SR-OBJ-000023" and receipts["RCPT-000036"]["version"] == "1.0.1"


def test_historical_works_remain_historical():
    objects, sources = _objects(), _sources()
    for oid in ("SR-OBJ-000017", "SR-OBJ-000019", "SR-OBJ-000026"):
        o = objects[oid]
        assert o["maturity"] == "historical"
        assert "Historical terminology" in o["authority_boundary"]
        assert any(m["class"] == "UNRESOLVED_SEAM" for m in o["missingness"])
        assert "Tier-1" in o["next_burden"] or "current" in o["next_burden"].lower()
    assert sources["SRC-000054"]["source_type"] == "historical" and sources["SRC-000054"]["status"] == "historical"
    assert objects["SR-OBJ-000026"]["provenance"] == "historical-source-anchored"


def test_pedagogical_records_separate_architecture_from_efficacy():
    objects = _objects()
    for oid in PEDAGOGICAL:
        o = objects[oid]
        assert o["tier2_class"]["primary"] == "pedagogical"
        efficacy = [m for m in o["missingness"] if m["item"] == "classroom efficacy"]
        assert efficacy and efficacy[0]["class"] == "NON_BLOCKING" and "NON_EVALUABLE" in efficacy[0]["notes"]
        assert any("efficacy" in c["claim"] for c in o["claim_layers"] if c["layer"] == "source-observation")
    # Four distinct witnesses share one archive DOI but keep separate SourceIDs and objects.
    sources = _sources()
    members = ["SRC-000055", "SRC-000056", "SRC-000057", "SRC-000058"]
    assert len({sources[s]["identifier"]["doi"] for s in members}) == 1
    assert len({sources[s]["title"] for s in members}) == 4
    assert len({objects[o]["source_ids"][0] for o in PEDAGOGICAL}) == 4


def test_relations_are_deliberate_and_source_explicit():
    registry = loader.load_registry()
    relations = {r["relation_id"]: r for r in registry["relations"].values()}
    assert relations["REL-000004"] == {**relations["REL-000004"], "relation_type": "extends",
                                       "from_id": "SR-OBJ-000020", "to_id": "SR-OBJ-000009"}
    assert relations["REL-000005"] == {**relations["REL-000005"], "relation_type": "extends",
                                       "from_id": "SR-OBJ-000029", "to_id": "SR-OBJ-000028"}
    assert len(relations) == 5
    assert "REL-000004" in _objects()["SR-OBJ-000020"]["relations"]
    assert "REL-000005" in _objects()["SR-OBJ-000029"]["relations"]


def test_released_governing_records_and_manifests_unchanged():
    manifests = loader.load_release_manifests()
    released = loader.released_governing_hashes(manifests)
    assert released
    from validators import checks
    report = checks.validate_registry(loader.load_registry(), loader.load_schemas(), loader.load_taxonomies(),
                                      released_hashes=released, receipts=_receipts())
    assert report.ok
    # v1.0.0 manifest counts are historical and untouched by this pass.
    v100 = manifests["SR-LIBRARY.v1.0.0"]
    text = json.dumps(v100, sort_keys=True)
    assert "SR-OBJ-000020" not in text and "SRC-000047" not in text


def test_saturn_and_dmt_are_source_lineage_only():
    objects, sources = _objects(), _sources()
    assert "SRC-000059" in sources
    assert not any("SRC-000059" in o["source_ids"] for o in objects.values())
    dmt = [o for o in objects.values() if "SRC-000019" in o["source_ids"]]
    assert [o["object_id"] for o in dmt] == ["SR-OBJ-000011"]
    assert any(r["relation"] == "earlier_version" for r in sources["SRC-000019"]["related_dois"])


def test_site_rebuild_is_deterministic_and_bridges_include_new_objects(tmp_path):
    registry = loader.load_registry()
    receipts = _receipts()
    digests = []
    for name in ("a", "b"):
        out = tmp_path / name
        sitegen.generate_site(out, registry, receipts)
        digests.append(sorted((p.relative_to(out).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
                              for p in out.rglob("*") if p.is_file()))
    assert digests[0] == digests[1]
    projection = json.loads((tmp_path / "a" / "data" / "bridge_candidates.json").read_text(encoding="utf-8"))
    involved = {c["object_a"] for c in projection["candidates"]} | {c["object_b"] for c in projection["candidates"]}
    assert set(NEW_OBJECTS) <= involved
    chain = next(c for c in projection["candidates"] if {c["object_a"], c["object_b"]} == {"SR-OBJ-000009", "SR-OBJ-000020"})
    assert chain["already_declared"] is True
    # Generated adjacency created no REL-* records.
    assert len(registry["relations"]) == 5
    assert bridges.build_bridge_projection(registry) == projection
