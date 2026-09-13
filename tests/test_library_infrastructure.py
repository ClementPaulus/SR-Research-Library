"""Tests for external-source discipline, history preservation, profiles,
manifests, and site generation."""

from __future__ import annotations

import copy
import json

import jsonschema
import pytest
import yaml

from validators import admit, loader, manifest, profiles, sitegen


def test_external_source_attribution_preservation(base_registry, schemas):
    """External work remains an external source object with preserved
    authorship, source-native claims, source identity, and missingness."""
    source = base_registry["sources"]["SRC-000001.json"]
    jsonschema.Draft202012Validator(schemas["source"]).validate(source)
    assert source["source_type"] == "external"
    # Original authorship is preserved as names, never replaced by a library AuthorID.
    assert source["source_authors"]
    assert not any(a.startswith("AUTH-") for a in source["source_authors"])
    # Source-native claims stay on the source; local interpretation lives on the object.
    assert source["source_native_claims"]
    # Missingness is preserved, not silently filled.
    assert source["missingness"]
    assert source["publication_year"] is None


def test_object_keeps_source_observation_distinct(synthetic_object):
    """Claim layers keep source observation distinct from local interpretation,
    so a local interpretation is never attributed to the external author."""
    layers = {entry["layer"] for entry in synthetic_object["claim_layers"]}
    assert "source-observation" in layers
    assert "local-interpretation" in layers


def test_historical_version_preservation(tmp_path, synthetic_object):
    """Object revisions preserve prior states; history is never rewritten."""
    registry_dir = tmp_path / "registry"
    (registry_dir / "objects").mkdir(parents=True)

    v1 = copy.deepcopy(synthetic_object)
    path_v1 = loader.archive_object_version(v1, registry_dir)
    assert path_v1.exists()
    assert "SR-OBJ-000001.v0.1.0" in path_v1.name

    v2 = copy.deepcopy(synthetic_object)
    v2["version"] = "0.2.0"
    v2["notes"] = "SYNTHETIC: revised test fixture."
    path_v2 = loader.archive_object_version(v2, registry_dir)
    assert path_v2 != path_v1

    # Both historical states remain readable and distinct.
    history = loader.load_object_history(registry_dir)
    assert len(history) == 2

    # Attempting to rewrite an existing historical state with different content fails.
    conflicting = copy.deepcopy(v1)
    conflicting["title"] = "Silently rewritten title (synthetic)"
    with pytest.raises(FileExistsError):
        loader.archive_object_version(conflicting, registry_dir)

    # Re-archiving identical content is a no-op, not a rewrite.
    assert loader.archive_object_version(copy.deepcopy(v1), registry_dir) == path_v1


def test_register_object_preserves_previous_version(tmp_path, synthetic_object):
    """Registering a new version archives the prior state; same-version rewrites fail."""
    registry_dir = tmp_path / "registry"

    v1 = copy.deepcopy(synthetic_object)
    path = admit.register_object(v1, registry_dir)
    assert path == registry_dir / "objects" / "SR-OBJ-000001.json"
    assert json.loads(path.read_text(encoding="utf-8")) == v1
    assert loader.load_object_history(registry_dir) == {}

    # Identical re-registration is a no-op.
    assert admit.register_object(copy.deepcopy(v1), registry_dir) == path

    # Same version, different content: never silently rewritten.
    conflicting = copy.deepcopy(v1)
    conflicting["title"] = "Silently rewritten title (synthetic)"
    with pytest.raises(FileExistsError):
        admit.register_object(conflicting, registry_dir)

    v2 = copy.deepcopy(v1)
    v2["version"] = "0.2.0"
    admit.register_object(v2, registry_dir)
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == "0.2.0"
    history = loader.load_object_history(registry_dir)
    assert list(history) == ["SR-OBJ-000001.v0.1.0.json"]
    assert history["SR-OBJ-000001.v0.1.0.json"] == v1


def test_admit_cli_registers_only_accepted(tmp_path, monkeypatch, synthetic_object, capsys):
    registry_dir = tmp_path / "registry"
    monkeypatch.setattr(loader, "REGISTRY_DIR", registry_dir)
    real_registry = loader.load_registry(loader.REPO_ROOT / "registry")
    monkeypatch.setattr(loader, "load_registry", lambda registry_dir=None: real_registry)

    accepted = copy.deepcopy(synthetic_object)
    accepted["source_ids"], accepted["relations"] = [], []
    accepted_path = tmp_path / "accepted.json"
    accepted_path.write_text(json.dumps(accepted), encoding="utf-8")
    assert admit.main([str(accepted_path), "--register"]) == 0
    assert (registry_dir / "objects" / "SR-OBJ-000001.json").exists()

    repair = copy.deepcopy(accepted)
    repair["object_id"] = "SR-OBJ-000002"
    del repair["main_question"]
    repair_path = tmp_path / "repair.json"
    repair_path.write_text(json.dumps(repair), encoding="utf-8")
    assert admit.main([str(repair_path), "--register"]) == 1
    assert not (registry_dir / "objects" / "SR-OBJ-000002.json").exists()
    assert "Not registered: decision is RETURNED_FOR_REPAIR" in capsys.readouterr().out


def test_taxonomy_extension_record_matches_taxonomies(taxonomies):
    """Every accepted extension is present in its taxonomy; no proposal is applied early."""
    data = yaml.safe_load((loader.TAXONOMY_DIR / "extensions.yaml").read_text(encoding="utf-8"))
    ids = [e["id"] for e in data["extensions"]]
    assert len(ids) == len(set(ids))
    for ext in data["extensions"]:
        assert ext["decision"] in ("proposed", "accepted", "rejected", "deprecated")
        present = ext["term"] in taxonomies[ext["taxonomy"]]
        if ext["decision"] == "accepted":
            assert present, f"{ext['id']} accepted but {ext['term']} missing from {ext['taxonomy']}"
            assert ext["version_introduced"]
        elif ext["decision"] in ("proposed", "rejected"):
            assert not present, f"{ext['id']} is {ext['decision']} but already in taxonomy"


def test_open_seams_are_well_formed():
    data = yaml.safe_load((loader.RELEASES_DIR / "open-seams.yaml").read_text(encoding="utf-8"))
    ids = [s["id"] for s in data["seams"]]
    assert len(ids) == len(set(ids))
    for seam in data["seams"]:
        assert seam["status"] in ("open", "closed")
        assert seam["area"] and seam["description"]


def test_author_profile_reconstructible_quantities(base_registry, synthetic_object):
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    profile = profiles.build_author_profile("AUTH-0001", registry)
    assert profile["author_id"] == "AUTH-0001"
    assert profile["display_name"] == "Clement Paulus"
    assert profile["total_registered_authored_objects"] == 1
    assert profile["primary_domain_distribution"] == {"structura-reditus-core": 1.0}
    assert profile["tier2_class_distribution"] == {"diagnostic": 1.0}
    assert profile["structural_focus_distribution"] == {"return": 1.0}
    assert profile["evidence_mode_distribution"] == {"no-empirical-validation": 1.0}
    assert profile["provenance_distribution"] == {"synthetic-test-object": 1.0}
    assert profile["maturity_distribution"] == {"exploratory": 1.0}
    # No universal author score and no prestige weighting exists anywhere in the profile.
    for forbidden in ("score", "rank", "prestige", "citations", "importance"):
        assert forbidden not in profile


def test_author_identity_stable_while_history_changes(base_registry, synthetic_object):
    """Author identity fields are unchanged as contribution history grows."""
    empty_profile = profiles.build_author_profile("AUTH-0001", base_registry)
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    grown_profile = profiles.build_author_profile("AUTH-0001", registry)
    for identity_field in ("author_id", "display_name", "orcid", "status"):
        assert empty_profile[identity_field] == grown_profile[identity_field]
    assert empty_profile["total_registered_authored_objects"] == 0
    assert grown_profile["total_registered_authored_objects"] == 1


def test_release_manifest_generation(tmp_path):
    data = manifest.build_release_manifest(
        "SR-LIBRARY.v0.0.0-test",
        open_seams=["synthetic test seam"],
        migration_notes=["synthetic test note"],
    )
    assert data["schema_version"] == loader.schema_version()
    assert data["taxonomy_version"] == loader.taxonomy_version()
    assert data["author_count"] >= 1
    assert "AUTH-0001" in data["id_manifest"]["authors"]
    assert data["timezone"] == "UTC"
    assert data["hashes"]

    path = manifest.write_release_manifest(data, tmp_path)
    assert path.exists()
    # Identical rewrite is a no-op; differing rewrite is refused.
    assert manifest.write_release_manifest(data, tmp_path) == path
    altered = copy.deepcopy(data)
    altered["migration_notes"] = ["silently changed"]
    with pytest.raises(FileExistsError):
        manifest.write_release_manifest(altered, tmp_path)


def test_site_generated_from_registry(tmp_path, base_registry, synthetic_object):
    """The site is generated from the registry, not a second database, with three distinct surfaces."""
    registry = copy.deepcopy(base_registry)
    registry["objects"]["SR-OBJ-000001.json"] = synthetic_object
    index_path = sitegen.generate_site(tmp_path, registry, receipts={})
    html = index_path.read_text(encoding="utf-8")
    for surface in ("GOVERNING REFERENCES", "TIER-2 RESEARCH", "SOURCES &amp; ARCHIVES"):
        assert surface in html
    assert "organizational conformance only" in html
    objects_html = (tmp_path / "objects" / "index.html").read_text(encoding="utf-8")
    assert "SR-OBJ-000001" in objects_html
    object_page = (tmp_path / "objects" / "SR-OBJ-000001.html").read_text(encoding="utf-8")
    assert "TIER-2 RESEARCH OBJECT" in object_page
    source_page = (tmp_path / "sources" / "SRC-000001.html").read_text(encoding="utf-8")
    assert "Registry kind: SOURCE" in source_page
    assert "Tier-2 research object(s) built on it" in source_page
    assert "Clement Paulus" in (tmp_path / "authors" / "AUTH-0001.html").read_text(encoding="utf-8")
    objects_data = json.loads((tmp_path / "data" / "objects.json").read_text(encoding="utf-8"))
    assert objects_data[0]["object_id"] == "SR-OBJ-000001"
    profiles_data = json.loads((tmp_path / "data" / "profiles.json").read_text(encoding="utf-8"))
    assert "AUTH-0001" in profiles_data
