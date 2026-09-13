"""Pytest configuration and shared fixtures.

All example records built here are synthetic test objects and are explicitly
marked as synthetic. No scholarly facts are fabricated: titles, questions,
and claims describe the library's own test machinery.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from validators import loader  # noqa: E402


SYNTHETIC_SOURCE = {
    "source_id": "SRC-000001",
    "source_type": "external",
    "title": "Synthetic external source used only for library self-tests",
    "source_authors": ["Synthetic External Author (synthetic test identity)"],
    "source_native_claims": [
        "This synthetic source claims only that it exists as a test fixture."
    ],
    "identifier": {"other": "synthetic-test-fixture"},
    "publication_year": None,
    "venue": None,
    "missingness": [
        "No publication year: this is a synthetic fixture with no real publication event."
    ],
    "notes": "SYNTHETIC: test fixture only; not a real scholarly source.",
}

SYNTHETIC_RELATION = {
    "relation_id": "REL-000001",
    "relation_type": "derived_from",
    "from_id": "SR-OBJ-000001",
    "to_id": "SRC-000001",
    "declared": "2026-09-13",
    "notes": "SYNTHETIC: test fixture relation.",
}

SYNTHETIC_OBJECT = {
    "object_id": "SR-OBJ-000001",
    "title": "Synthetic self-test object for library admission machinery",
    "authors": ["AUTH-0001"],
    "authority": {"tier": "tier-2"},
    "tier2_class": {"primary": "diagnostic", "secondary": []},
    "functional_locus": "none",
    "source_ids": ["SRC-000001"],
    "lens": "Library self-test lens: the object examines the admission machinery itself.",
    "domain": {"primary": "structura-reditus-core", "secondary": []},
    "object_of_study": "The admission-gate machinery of the Research Library.",
    "structural_focus": {"primary": "return", "secondary": ["boundary"]},
    "main_question": "Does a structurally complete record pass all seven admission gates?",
    "secondary_questions": [],
    "claim_layers": [
        {"layer": "source-observation",
         "claim": "The synthetic source states only that it exists as a test fixture."},
        {"layer": "local-interpretation",
         "claim": "A structurally complete record should be ACCEPTED by the gates."}
    ],
    "evidence_mode": {"primary": "no-empirical-validation", "secondary": []},
    "provenance": "synthetic-test-object",
    "maturity": "exploratory",
    "relations": ["REL-000001"],
    "version": "0.1.0",
    "date": "2026-09-13",
    "publication_state": "registered-only",
    "source_boundary": "The synthetic source establishes nothing beyond its own existence "
                       "as a fixture; no scholarly claim is drawn from it.",
    "authority_boundary": "This object claims no Tier-0 or Tier-1 authority, no scientific "
                          "truth, and no endorsement of any external source.",
    "scope": "Library self-testing only.",
    "exclusions": ["Any real scholarly claim."],
    "preserved_meaning": "The synthetic source's own statement is preserved verbatim in its "
                         "source-native claims.",
    "missingness": [
        {"item": "No empirical validation performed",
         "class": "NON_BLOCKING",
         "notes": "The object is a synthetic test fixture."}
    ],
    "distortion_or_substitution_risk": "None beyond the declared synthetic framing; the source "
                                       "is quoted, not interpreted.",
    "next_burden": "None beyond continued test maintenance.",
    "repair_route": "Amend this record and resubmit through the same seven gates.",
    "notes": "SYNTHETIC: test fixture only; explicitly marked as synthetic.",
    "synthetic": True,
}


@pytest.fixture()
def schemas():
    return loader.load_schemas()


@pytest.fixture()
def taxonomies():
    return loader.load_taxonomies()


@pytest.fixture()
def base_registry():
    """Registry with the real AUTH-0001 plus synthetic fixtures."""
    registry = loader.load_registry()
    registry = copy.deepcopy(registry)
    registry["sources"]["SRC-000001.json"] = copy.deepcopy(SYNTHETIC_SOURCE)
    registry["relations"]["REL-000001.json"] = copy.deepcopy(SYNTHETIC_RELATION)
    return registry


@pytest.fixture()
def synthetic_object():
    return copy.deepcopy(SYNTHETIC_OBJECT)


@pytest.fixture()
def synthetic_source():
    return copy.deepcopy(SYNTHETIC_SOURCE)


@pytest.fixture()
def synthetic_relation():
    return copy.deepcopy(SYNTHETIC_RELATION)
