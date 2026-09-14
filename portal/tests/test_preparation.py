"""Automatic preparation: source/version identification, duplicate checks, classification suggestions,
structured questions, confirmation without retyping, repair reuse, and interruption recovery (W-rows)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.projection import current_projection
from registry_bridge.fake_github import REPO
from registry_bridge.models import EvaluationAttempt, Publication
from submissions import preparation, services, state as wf
from submissions.models import FieldEvidence

pytestmark = pytest.mark.django_db(transaction=True)

MANUSCRIPT = b"""# Bounded Archive Expansion in the Structura Reditus Intake Pipeline

Synthetic Researcher and Portal Fixture

Version 2 (2026-09-14). Preprint; not peer reviewed. This manuscript is a synthetic acceptance fixture: it describes
only the research library's own intake machinery and makes no scholarly claim beyond that.

Abstract
We test whether the intake pipeline's bounded ZIP expansion returns the same member set under repeated runs. In a
simulation of two hundred synthetic archives the simulated pipeline returned identical member sets in every run; one archive with
a nested depth of four failed as designed. The failure is reported as a result, not as missing information.

Introduction
The pipeline is a diagnostic of the library's own robustness. We argue that a bounded expansion contract is a
prerequisite for reproducible intake.
"""


def test_identify_sources_finds_doi_arxiv_versions_and_hints():
    text = ("Title\nDOI: 10.5281/zenodo.22739943 and arXiv:2401.01234v2\nVersion 1.2 of this manuscript; see also version 1.3.\n"
            "Deposited at https://zenodo.org/records/22739943 as a preprint.")
    found = preparation.identify_sources(text, "paper.md")
    assert found["dois"][0]["value"] == "10.5281/zenodo.22739943" and "line 2" in found["dois"][0]["locator"]
    assert found["arxiv"][0]["value"] == "2401.01234v2"
    assert {v["value"] for v in found["versions"]} == {"1.2", "1.3"}
    assert found["zenodo"][0]["value"] == "22739943"
    assert {h["value"] for h in found["publication_hints"]} >= {"preprint", "archived"}
    merged = preparation.merge_identifications([("a.md", found)])
    assert "1.2, 1.3" in merged["version_ambiguity"]


def test_duplicate_check_matches_doi_title_and_identical_file():
    projection = current_projection()
    findings = preparation.check_duplicates("Prospective Identifiable Return in Associative Memory: A Completed Prospective Computational Test",
                                            ["10.5281/zenodo.22739943"], [], projection)
    kinds = {(f["kind"], f["id"]) for f in findings}
    assert ("existing_source", "SRC-000060") in kinds
    assert any(k == "possible_duplicate_object" and i == "SR-OBJ-000031" for k, i in kinds)
    manifests = {"RCPT-000999": {"submission_identity": "SR-OBJ-000999", "source_files": [{"sha256": "ab" * 32, "display_name": "x.pdf"}]}}
    findings = preparation.check_duplicates("", [], ["ab" * 32], projection, manifests)
    assert findings and findings[0]["kind"] == "identical_file"
    assert preparation.check_duplicates("Completely unrelated synthetic title zzz", [], [], projection) == []


def test_classification_suggestions_are_explainable_and_taxonomy_bound():
    from django.conf import settings
    from registry_bridge.engine import import_engine

    taxonomies = import_engine(settings.PORTAL_REGISTRY_REPO_PATH)["loader"].load_taxonomies(settings.PORTAL_REGISTRY_REPO_PATH / "taxonomy")
    suggestions = preparation.suggest_classifications(MANUSCRIPT.decode(), taxonomies, [{"value": "preprint", "matched": ["preprint"]}])
    assert suggestions["evidence_mode.primary"]["term"] == "simulation"
    assert any("simulation" in m for m in suggestions["evidence_mode.primary"]["matched"])
    assert suggestions["tier2_class.primary"]["term"] == "diagnostic"
    assert suggestions["domain.primary"]["term"] == "structura-reditus-core"
    assert suggestions["publication_state"]["term"] == "preprint"
    for path, suggestion in suggestions.items():
        axis = path.split(".")[0]
        allowed = {"evidence_mode": "evidence_modes", "tier2_class": "tier2_classes", "domain": "domains",
                   "structural_focus": "focuses", "functional_locus": "functional_loci", "publication_state": "publication_states"}[axis]
        assert suggestion["term"] is None or suggestion["term"] in taxonomies[allowed]
    # A genuine tie is reported as 'no single suggestion' rather than picking arbitrarily.
    tied = preparation.suggest_classifications("We argue a point. We also ran a simulation.", taxonomies)
    assert tied["evidence_mode.primary"]["term"] is None and tied["evidence_mode.primary"]["note"] == "tied terms; choose one"


def test_upload_runs_full_preparation_with_steps_suggestions_and_auto_source(registered_author):
    submission = services.create_submission(registered_author, label="W-prep")
    services.register_upload(submission, registered_author, SimpleUploadedFile("manuscript-v2.md", MANUSCRIPT))
    submission.refresh_from_db()
    note = submission.processing_notes[-1]
    assert [s["status"] for s in note["steps"]] == ["done"] * 6
    assert {s["key"] for s in note["steps"]} == {"preserve", "identify", "duplicates", "extract", "classify", "assemble"}
    assert "version statement(s) 2" in next(s for s in note["steps"] if s["key"] == "identify")["detail"]
    draft = submission.draft
    assert draft["title"] == "Bounded Archive Expansion in the Structura Reditus Intake Pipeline"
    assert draft["evidence_mode"]["primary"] == "simulation" and draft["tier2_class"]["primary"] == "diagnostic"
    assert draft["publication_state"] == "preprint"
    # Suggestions are labelled library classification and uncertain; the Markdown heading title is a reliable extraction.
    ev = {(e.field_path, e.origin, e.uncertain) for e in FieldEvidence.objects.filter(submission=submission)}
    assert ("evidence_mode.primary", "library-classification", True) in ev
    assert ("title", "source-extraction", False) in ev
    # An automatic source proposal was built from the file's own statements, never from invention.
    assert "SRC-NEW-1" in submission.proposed_sources and draft["source_ids"] == ["SRC-NEW-1"]
    source = submission.proposed_sources["SRC-NEW-1"]
    assert source["version"] == "2" and source["identifier"] == {}
    assert any("No DOI" in m for m in source["missingness"])
    # Structured questions: each says why, whether it blocks, and what resolves it; reliably extracted fields are not re-asked.
    questions = note["questions"]
    assert all({"why", "blocks", "resolves", "status"} <= set(q) for q in questions)
    asked = {q["field"] for q in questions}
    assert "object_of_study" in asked and "next_burden" in asked
    assert "title" not in asked and "title" in note["assessment"]["ready"]
    assert next(q for q in questions if q["field"] == "evidence_mode.primary")["status"] == "needs_confirmation"
    assert note["assessment"]["blocking_open"] > 0


def test_saving_confirms_kept_uncertain_values_without_retyping(registered_author):
    submission = services.create_submission(registered_author, label="W-confirm")
    services.register_upload(submission, registered_author, SimpleUploadedFile("manuscript-v2.md", MANUSCRIPT))
    submission.refresh_from_db()
    before = services.assessment_for(submission)
    assert "evidence_mode.primary" in before["needs_confirmation"] and "publication_state" in before["needs_confirmation"]
    draft = {k: v for k, v in submission.draft.items() if not k.startswith("_")}
    services.save_draft(submission, registered_author, draft, submission.proposed_sources, {}, expected_version=submission.draft_version,
                        confirm_fields=before["needs_confirmation"])
    submission.refresh_from_db()
    after = services.assessment_for(submission)
    assert "publication_state" in after["ready"] and "evidence_mode.primary" in after["ready"]
    assert FieldEvidence.objects.filter(submission=submission, field_path="evidence_mode.primary", origin="researcher-statement",
                                        locator="confirmed in the editor").exists()
    # The original uncertain suggestion row is preserved alongside the confirmation.
    assert FieldEvidence.objects.filter(submission=submission, field_path="evidence_mode.primary", origin="library-classification", uncertain=True).exists()
    assert submission.draft.get("_abstract_hint")  # preparation hints survive saves


def test_two_versions_uploaded_require_a_governing_version_before_submit(registered_author, synthetic_record):
    submission = services.create_submission(registered_author, label="W-ambiguous")
    v1 = MANUSCRIPT.replace(b"Version 2 (2026-09-14)", b"Version 1 (2026-08-01)")
    services.register_upload(submission, registered_author, SimpleUploadedFile("manuscript-v1.md", v1))
    services.register_upload(submission, registered_author, SimpleUploadedFile("manuscript-v2.md", MANUSCRIPT))
    submission.refresh_from_db()
    assert "_version_ambiguity" in submission.draft
    assessment = services.assessment_for(submission)
    assert assessment["questions"][0]["field"] == "_version" and assessment["questions"][0]["blocks"]
    record = dict({k: v for k, v in synthetic_record.items()}, authors=[registered_author.author_id], source_ids=["SRC-000001"], relations=[])
    services.save_draft(submission, registered_author, record, {}, {}, expected_version=submission.draft_version)
    submission.refresh_from_db()
    with pytest.raises(services.SubmissionError, match="which version governs"):
        services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    services.save_draft(submission, registered_author, dict(record, _version_resolution="Version 2 in manuscript-v2.md governs; v1 is an earlier version"),
                        {}, {}, expected_version=submission.draft_version)
    submission.refresh_from_db()
    revision = services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    assert revision.number == 1
    # The researcher's statement resolved the automatic ambiguity: no review case, routine evaluation proceeds.
    submission.refresh_from_db()
    assert not submission.review_cases.filter(condition="ambiguous_source").exists()
    assert submission.workflow_state in (wf.REGISTERED, wf.NEEDS_REPAIR, wf.ACCEPTED_PENDING)


def test_duplicate_object_requires_resolution_and_revision_sets_target(registered_author, synthetic_record):
    from tests.test_submissions import _complete_record, _submit

    first, _ = _submit(registered_author, _complete_record(registered_author.author_id, synthetic_record))
    assert first.workflow_state == wf.REGISTERED
    from catalog.projection import refresh_projection

    refresh_projection(None)
    registered_id = first.draft["object_id"]
    # Uploading the same fixture again is flagged as a possible duplicate of the registered object.
    again = services.create_submission(registered_author, label="W-dup")
    services.register_upload(again, registered_author, SimpleUploadedFile("record.json", json.dumps(synthetic_record).encode()))
    again.refresh_from_db()
    dup = [f for f in again.draft["_duplicate_findings"] if f["kind"] == "possible_duplicate_object"]
    assert dup and dup[0]["id"] == registered_id
    record = _complete_record(registered_author.author_id, synthetic_record)
    services.save_draft(again, registered_author, record, {}, {}, expected_version=again.draft_version)
    again.refresh_from_db()
    with pytest.raises(services.SubmissionError, match="possible duplicate"):
        services.confirm_and_submit(again, registered_author, publish_files=False, acknowledged=True, expected_version=again.draft_version)
    services.save_draft(again, registered_author, dict(record, version="1.0.1", _duplicate_resolution=f"revision_of:{registered_id}"), {}, {},
                        expected_version=again.draft_version)
    again.refresh_from_db()
    revision = services.confirm_and_submit(again, registered_author, publish_files=False, acknowledged=True, expected_version=again.draft_version)
    assert revision.record["object_id"] == registered_id
    again.refresh_from_db()
    assert again.workflow_state == wf.REGISTERED
    assert f"registry/objects/history/{registered_id}.v{synthetic_record['version']}.json" in REPO.files_at("main")


def test_repair_reuses_evidence_and_names_flagged_fields(registered_author, synthetic_record):
    from tests.test_submissions import _complete_record, _submit

    record = _complete_record(registered_author.author_id, synthetic_record)
    del record["next_burden"]
    record["scope"] = ""
    submission, revision = _submit(registered_author, record)
    assert submission.workflow_state == wf.NEEDS_REPAIR
    evidence_before = FieldEvidence.objects.filter(revision=revision).count()
    services.start_repair(submission, registered_author)
    submission.refresh_from_db()
    note = submission.processing_notes[-1]
    assert note["kind"] == "repair" and set(note["affected_fields"]) >= {"next_burden", "scope"}
    assert "authority_boundary" not in note["affected_fields"]
    reused = FieldEvidence.objects.filter(submission=submission, revision__isnull=True)
    assert reused.count() == evidence_before and all(e.processing.get("reused_from_revision") == 1 for e in reused)
    assessment = services.assessment_for(submission)
    missing = set(assessment["missing"])
    assert {"next_burden", "scope"} <= missing and "title" not in missing


def test_manuscript_with_auto_proposed_source_registers_end_to_end(registered_author):
    """The default journey: upload → prepared draft → answer only the missing fields → submit → Registered, new SRC-* published."""
    submission = services.create_submission(registered_author, label="W-e2e")
    services.register_upload(submission, registered_author, SimpleUploadedFile("manuscript-v2.md", MANUSCRIPT))
    submission.refresh_from_db()
    assessment = services.assessment_for(submission)
    draft = {k: v for k, v in submission.draft.items() if not k.startswith("_")}
    answers = {
        "object_of_study": "The intake pipeline's bounded ZIP expansion routine.",
        "main_question": "Does bounded archive expansion return identical member sets under repeated runs?",
        "lens": "Diagnostic of the library's own intake machinery.",
        "claim_layers": [{"layer": "source-observation", "claim": "Identical member sets were returned in every run; the deeply nested archive failed as designed."},
                         {"layer": "local-interpretation", "claim": "A bounded expansion contract is a prerequisite for reproducible intake."}],
        "source_boundary": "Establishes simulated behaviour; not real-world archives.",
        "authority_boundary": "Claims no Tier-0 or Tier-1 authority.",
        "scope": "The library's own intake pipeline under synthetic archives.",
        "preserved_meaning": "The nested-archive failure is a designed refusal, not missing information.",
        "distortion_or_substitution_risk": "Could be mistaken for a claim about external archives; none is made.",
        "missingness": [{"item": "Behaviour on real-world archives", "class": "NON_BLOCKING", "notes": "Only synthetic archives were used."}],
        "next_burden": "Run the same contract on real-world archive samples.",
        "repair_route": "Amend this record and resubmit through the same seven gates.",
        "provenance": "corpus-native", "maturity": "prospectively-tested", "functional_locus": "none",
    }
    answered_fields = set(answers)
    assert answered_fields <= set(assessment["missing"]) | {"missingness"}, set(assessment["missing"]) - answered_fields
    draft.update(answers)
    draft["structural_focus"] = {"primary": "robustness", "secondary": []}
    sources = dict(submission.proposed_sources)
    for record in sources.values():
        record.pop("_source_type_unconfirmed", None)
        record["source_type"] = "corpus-native"
    services.save_draft(submission, registered_author, draft, sources, {}, expected_version=submission.draft_version,
                        confirm_fields=assessment["needs_confirmation"])
    submission.refresh_from_db()
    final = services.assessment_for(submission)
    assert final["submittable"], final["questions"]
    revision = services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    submission.refresh_from_db()
    assert submission.workflow_state == wf.REGISTERED, submission.processing_notes[-1]
    source_id = revision.record["source_ids"][0]
    assert source_id.startswith("SRC-0") and source_id != "SRC-NEW-1"
    files = REPO.files_at("main")
    assert f"registry/sources/{source_id}.json" in files
    assert json.loads(files[f"registry/reservations/{source_id}.json"])["state"] == "published"
    attempt = EvaluationAttempt.objects.get(revision=revision)
    assert attempt.decision == "ACCEPTED" and attempt.execution_manifest["source_files"][0]["display_name"] == "manuscript-v2.md"


def test_outage_file_blocks_publication_then_reconcile_recovers(registered_author, synthetic_record, settings, tmp_path):
    from tests.test_submissions import _complete_record, _submit

    flag = tmp_path / "outage"
    flag.write_text("down")
    settings.PORTAL_FAKE_GITHUB_OUTAGE_FILE = str(flag)
    submission, revision = _submit(registered_author, _complete_record(registered_author.author_id, synthetic_record))
    assert submission.workflow_state == wf.ACCEPTED_PENDING
    publication = Publication.objects.get(attempt__revision=revision)
    assert publication.status != Publication.VERIFIED
    flag.unlink()
    from django.core.management import call_command

    for _ in range(3):
        call_command("reconcile", "--due")
        publication.refresh_from_db()
        if publication.status == Publication.VERIFIED:
            break
    submission.refresh_from_db()
    assert publication.status == Publication.VERIFIED and submission.workflow_state == wf.REGISTERED
    assert EvaluationAttempt.objects.filter(revision=revision).count() == 1  # recovery never re-decides
