"""Public catalog over the committed projection: search (S01–S05), record pages, receipt chronology (G08), no login required."""

from __future__ import annotations

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.projection import current_projection, refresh_projection
from submissions import services, state as wf

pytestmark = pytest.mark.django_db(transaction=True)


def test_public_routes_need_no_login(client):
    for url in ("/", "/research", "/research/SR-OBJ-000023", "/sources", "/sources/SRC-000052", "/governing", "/authors",
                "/authors/AUTH-0001", "/receipts", "/receipts/RCPT-000036", "/contribute", "/healthz"):
        response = client.get(url)
        assert response.status_code == 200, url
    assert client.get("/objects/SR-OBJ-000023.html").status_code == 302  # legacy static path redirect
    assert client.get("/workspace/").status_code == 302  # private routes require login


def test_s01_physically_constrained_finds_object_23(client):
    response = client.get("/research", {"q": "physically constrained"})
    assert response.status_code == 200
    assert b"SR-OBJ-000023" in response.content and b"main_question" in response.content


def test_s02_author_name_and_relation_id(client):
    response = client.get("/research", {"q": "Clement"})
    assert b"SR-OBJ-000031" in response.content and b"SR-OBJ-000001" in response.content
    response = client.get("/research", {"q": "REL-000006"})
    assert b"SR-OBJ-000031" in response.content and b"SR-OBJ-000023" in response.content
    response = client.get("/", {"q": "REL-000006"})
    assert b"SR-OBJ-000031" in response.content


def test_s03_filters_secondary_domain_evidence_maturity_shareable(client):
    response = client.get("/research", {"domain": ["cognitive-science"], "maturity": ["prospectively-tested"]})
    assert response.status_code == 200
    assert b"SR-OBJ-000031" in response.content
    assert b"domain: cognitive-science" in response.content and b"maturity: prospectively-tested" in response.content
    assert b"Reset" in response.content and b"Shareable link" in response.content
    empty = client.get("/research", {"q": "zzz-no-such-term"})
    assert b"0 research object" in empty.content


def test_s04_suggestions_are_labelled_capped_and_create_no_relation(client):
    response = client.get("/research/SR-OBJ-000023")
    body = response.content.decode()
    assert "Generated retrieval suggestion, not a declared relation" in body
    projection = current_projection()
    rows, total = projection.bridges_for("SR-OBJ-000023", limit=5)
    assert len(rows) <= 5 and total >= len(rows)
    if rows:
        assert "propose a relation" in body or "already" in body
        assert "strength" in body.lower() and "probability" in body  # labelled as detector label, not probability
    if total > 5:
        assert "Show all" in body
        assert len(projection.bridges_for("SR-OBJ-000023", limit=10_000)[0]) == total
    assert len(projection.relations) == len([k for k in projection.relations if k.startswith("REL-")])


def test_s05_profile_counts_current_objects_only(registered_author, synthetic_record):
    from tests.test_submissions import _complete_record, _submit

    record = _complete_record(registered_author.author_id, synthetic_record)
    record["main_question"] = ""
    submission, r1 = _submit(registered_author, record)
    assert submission.workflow_state == wf.NEEDS_REPAIR
    services.start_repair(submission, registered_author)
    submission.refresh_from_db()
    fixed = dict(submission.draft, main_question="Does the repaired record pass all gates?")
    services.save_draft(submission, registered_author, fixed, {}, {}, expected_version=submission.draft_version)
    submission.refresh_from_db()
    services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    submission.refresh_from_db()
    assert submission.workflow_state == wf.REGISTERED
    # Second registered revision of the same object (metadata bump) must not inflate the count.
    services.start_repair(submission, registered_author)
    submission.refresh_from_db()
    services.save_draft(submission, registered_author, dict(submission.draft, notes="bumped"), {}, {}, expected_version=submission.draft_version)
    submission.refresh_from_db()
    services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    submission.refresh_from_db()
    assert submission.workflow_state == wf.REGISTERED
    projection = refresh_projection(None)
    projection = current_projection()
    author_id = registered_author.author_id
    assert projection.profiles[author_id]["total_registered_authored_objects"] == 1
    object_id = submission.draft["object_id"]
    assert projection.objects[object_id]["version"] != r1.record["version"]
    assert any(k.startswith(object_id + ".v") for k in projection.object_history)


def test_g08_current_receipt_is_the_acceptance_for_registered_version_and_history_shows_all(registered_author, synthetic_record, client):
    from tests.test_submissions import _complete_record, _submit

    record = _complete_record(registered_author.author_id, synthetic_record)
    del record["scope"]
    submission, r1 = _submit(registered_author, record)
    services.start_repair(submission, registered_author)
    submission.refresh_from_db()
    services.save_draft(submission, registered_author, dict(submission.draft, scope="Library self-testing only."), {}, {}, expected_version=submission.draft_version)
    submission.refresh_from_db()
    services.confirm_and_submit(submission, registered_author, publish_files=False, acknowledged=True, expected_version=submission.draft_version)
    submission.refresh_from_db()
    assert submission.workflow_state == wf.REGISTERED
    refresh_projection(None)
    object_id = submission.draft["object_id"]
    projection = current_projection()
    obj = projection.objects[object_id]
    current = projection.current_receipt(obj)
    assert current["decision"] == "ACCEPTED" and current["version"] == obj["version"]
    attempts = projection.attempts[object_id]
    assert [a["decision"] for a in attempts] == ["RETURNED_FOR_REPAIR", "ACCEPTED"]
    response = client.get(f"/research/{object_id}")
    body = response.content.decode()
    assert "RETURNED_FOR_REPAIR" in body and "ACCEPTED" in body and "current" in body
    assert body.index("RETURNED_FOR_REPAIR") > body.index("Admission attempts")


def test_g09_g10_live_engine_tests_permit_growth(registered_author, synthetic_record):
    """A seventh declared relation and a later admission are valid growth; snapshot facts remain intact."""
    import os
    import subprocess
    import sys

    from tests.test_submissions import _complete_record, _submit

    record = _complete_record(registered_author.author_id, synthetic_record)
    submission, revision = _submit(registered_author, record)
    assert submission.workflow_state == wf.REGISTERED
    # Run the repository's own census tests against the scratch checkout that now contains the new object.
    from registry_bridge.checkout import isolated_checkout, repository_head

    with isolated_checkout(repository_head(), keep=False) as checkout:
        import shutil

        shutil.copytree(_repo_tests_dir(), checkout / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(_repo_tests_dir().parent / "docs" / "portal-evidence" / "baseline-810f4222.json",
                    checkout / "docs" / "portal-evidence" / "baseline-810f4222.json") if (checkout / "docs" / "portal-evidence").exists() else None
        env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO")}
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:django",
                                 "tests/test_census_2026_09.py", "tests/test_baseline_preservation.py"],
                                cwd=checkout, capture_output=True, text=True, env=env)
        assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]


def _repo_tests_dir():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent.parent / "tests"
