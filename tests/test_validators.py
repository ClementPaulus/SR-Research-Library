from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from validators.relation_validation import validate_relations
from validators.release_validation import validate_release_manifest
from validators.schema_validation import validate_schema_files
from validators.taxonomy_validation import validate_taxonomies
from validators.unique_id_validation import validate_unique_ids

ROOT = Path(__file__).resolve().parents[1]


class ValidatorBaselineTests(unittest.TestCase):
    def test_repository_validators_pass_on_baseline(self):
        self.assertEqual(validate_schema_files(), [])
        self.assertEqual(validate_unique_ids(), [])
        self.assertEqual(validate_taxonomies(), [])
        self.assertEqual(validate_relations(), [])
        self.assertEqual(validate_release_manifest(), [])


class ValidatorFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="sr-library-tests-"))
        shutil.copytree(ROOT / "schema", self.tmpdir / "schema")
        shutil.copytree(ROOT / "taxonomy", self.tmpdir / "taxonomy")
        shutil.copytree(ROOT / "releases", self.tmpdir / "releases")
        (self.tmpdir / "registry" / "authors").mkdir(parents=True)
        (self.tmpdir / "registry" / "objects").mkdir(parents=True)
        (self.tmpdir / "registry" / "sources").mkdir(parents=True)
        (self.tmpdir / "registry" / "relations").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_taxonomy_validator_flags_missing_primary_domain(self):
        obj = self.tmpdir / "registry" / "objects" / "SR-OBJ-000001.yaml"
        obj.write_text(
            """
object_id: SR-OBJ-000001
title: Example
authors:
  - author_id: AUTH-0001
    contribution_role: author
authority:
  tier: 2
tier2_class:
  primary: candidate-material
  secondary: []
functional_locus:
  primary: none-declared
  secondary: []
source_ids: []
lens:
  primary: none
  secondary: []
object_of_study: test
structural_focus:
  primary: return
  secondary: []
main_question: Under what declared conditions can a test object be recovered?
secondary_questions: []
claim_layers: []
evidence_mode:
  primary: conceptual-argument
  secondary: []
provenance: corpus-native
maturity: exploratory
relations: []
version: v0.1.0
date: '2026-09-13'
publication_state: draft
source_boundary: none
authority_boundary: Tier-2 only
scope: bounded
exclusions: none
preserved_meaning: test
missingness: []
distortion_or_substitution_risk: low
next_burden: provide source-backed expansion
repair_route: add missing domain
notes: test
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with patch("validators.taxonomy_validation.ROOT", self.tmpdir):
            errors = validate_taxonomies()
        self.assertTrue(any("domain.primary" in e for e in errors), errors)

    def test_taxonomy_validator_flags_unsupported_secondary_value(self):
        obj = self.tmpdir / "registry" / "objects" / "SR-OBJ-000002.yaml"
        obj.write_text(
            """
object_id: SR-OBJ-000002
title: Example
authors:
  - author_id: AUTH-0001
    contribution_role: author
authority:
  tier: 2
tier2_class:
  primary: candidate-material
  secondary: []
functional_locus:
  primary: none-declared
  secondary:
    - invalid-locus
source_ids: []
lens:
  primary: none
  secondary: []
domain:
  primary: cross-domain
  secondary: []
object_of_study: test
structural_focus:
  primary: return
  secondary: []
main_question: Under what declared conditions can a test object be recovered?
secondary_questions: []
claim_layers: []
evidence_mode:
  primary: conceptual-argument
  secondary: []
provenance: corpus-native
maturity: exploratory
relations: []
version: v0.1.0
date: '2026-09-13'
publication_state: draft
source_boundary: none
authority_boundary: Tier-2 only
scope: bounded
exclusions: none
preserved_meaning: test
missingness: []
distortion_or_substitution_risk: low
next_burden: provide source-backed expansion
repair_route: add missing domain
notes: test
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with patch("validators.taxonomy_validation.ROOT", self.tmpdir):
            errors = validate_taxonomies()
        self.assertTrue(any("functional_locus.secondary" in e for e in errors), errors)

    def test_relation_validator_flags_missing_next_burden(self):
        obj = self.tmpdir / "registry" / "objects" / "SR-OBJ-000001.yaml"
        obj.write_text(
            """
object_id: SR-OBJ-000001
title: Example
source_ids: []
relations: []
authority_boundary: Tier-2 only
provenance: corpus-native
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with patch("validators.relation_validation.ROOT", self.tmpdir):
            errors = validate_relations()
        self.assertTrue(any("missing next_burden" in e for e in errors), errors)


    def test_relation_validator_flags_non_list_reference_fields(self):
        obj = self.tmpdir / "registry" / "objects" / "SR-OBJ-000004.yaml"
        obj.write_text(
            """
object_id: SR-OBJ-000004
source_ids: SRC-123456
relations: REL-123456
authority_boundary: Tier-2 only
next_burden: normalize references
provenance: corpus-native
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with patch("validators.relation_validation.ROOT", self.tmpdir):
            errors = validate_relations()
        self.assertTrue(any("source_ids must be a list" in e for e in errors), errors)
        self.assertTrue(any("relations must be a list" in e for e in errors), errors)

    def test_relation_validator_flags_unresolved_source_and_relation(self):
        obj = self.tmpdir / "registry" / "objects" / "SR-OBJ-000003.yaml"
        obj.write_text(
            """
object_id: SR-OBJ-000003
source_ids:
  - SRC-999999
relations:
  - REL-999999
authority_boundary: Tier-2 only
next_burden: add admissible source and relation
provenance: corpus-native
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with patch("validators.relation_validation.ROOT", self.tmpdir):
            errors = validate_relations()
        self.assertTrue(any("unknown source reference SRC-999999" in e for e in errors), errors)
        self.assertTrue(any("unknown relation reference REL-999999" in e for e in errors), errors)


class ValidatorRunnerTests(unittest.TestCase):
    def test_runner_returns_zero_when_all_validators_pass(self):
        from validators import run_validators

        with patch.object(run_validators, "VALIDATORS", [("ok", lambda: [])]):
            self.assertEqual(run_validators.main(), 0)

    def test_runner_returns_one_when_any_validator_fails(self):
        from validators import run_validators

        with patch.object(run_validators, "VALIDATORS", [("bad", lambda: ["err"]) ]):
            self.assertEqual(run_validators.main(), 1)


if __name__ == "__main__":
    unittest.main()
