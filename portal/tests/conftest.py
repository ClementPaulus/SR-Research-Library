"""Portal test fixtures.

Every test runs against a *scratch copy* of the research repository, so the
real registry is never touched, and against the in-memory fake GitHub client.
Fixtures are synthetic and explicitly marked; no scholarly facts are invented.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PORTAL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PORTAL_DIR.parent
for path in (str(REPO_ROOT), str(PORTAL_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from tests.conftest import SYNTHETIC_OBJECT, SYNTHETIC_RELATION, SYNTHETIC_SOURCE  # noqa: E402  (repo-level fixtures)


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(scope="session")
def scratch_repo(tmp_path_factory):
    """A committed clone of the current tree (registry, schema, taxonomy, receipts, validators) with synthetic fixtures added."""
    root = tmp_path_factory.mktemp("scratch-repo")
    for folder in ("registry", "schema", "taxonomy", "receipts", "releases", "validators", "docs"):
        shutil.copytree(REPO_ROOT / folder, root / folder,
                        ignore=shutil.ignore_patterns("__pycache__", ".ledger.lock", "browser", "*.png", "*.zip"))
    for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "ENGINE_CONTRACT.md", "LIBRARY_SPECIFICATION.md"):
        shutil.copy(REPO_ROOT / name, root / name)
    (root / "site").mkdir()
    (root / "registry" / "sources" / "SRC-000001.json").write_text(json.dumps(SYNTHETIC_SOURCE, indent=2) + "\n", encoding="utf-8")
    # SRC-000001 exists in the live corpus; keep the live one (synthetic fixture only when absent).
    if (REPO_ROOT / "registry" / "sources" / "SRC-000001.json").exists():
        shutil.copy(REPO_ROOT / "registry" / "sources" / "SRC-000001.json", root / "registry" / "sources" / "SRC-000001.json")
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "tests@example.invalid", cwd=root)
    _git("config", "user.name", "Portal Tests", cwd=root)
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "scratch baseline", cwd=root)
    (root / ".baseline-sha").write_text(_git("rev-parse", "HEAD", cwd=root), encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def portal_settings(settings, scratch_repo, tmp_path):
    settings.PORTAL_REGISTRY_REPO_PATH = scratch_repo
    # Reset the scratch repository to its baseline so fake-GitHub merges from earlier tests do not leak.
    baseline = (scratch_repo / ".baseline-sha").read_text(encoding="utf-8").strip()
    _git("update-ref", "refs/heads/main", baseline, cwd=scratch_repo)
    for ref in _git("for-each-ref", "--format=%(refname)", "refs/heads/", cwd=scratch_repo).splitlines():
        if ref and ref != "refs/heads/main":
            _git("update-ref", "-d", ref, cwd=scratch_repo)
    settings.PORTAL_MEDIA_ROOT = str(tmp_path / "media")
    settings.STORAGES = {**settings.STORAGES, "default": {"BACKEND": "django.core.files.storage.FileSystemStorage",
                                                          "OPTIONS": {"location": str(tmp_path / "media"), "base_url": None}}}
    from django.core.files.storage import storages

    storages._storages = {}
    from registry_bridge.fake_github import REPO

    REPO.reset()
    from catalog import projection

    projection._CACHE.clear()
    yield


@pytest.fixture()
def synthetic_record():
    record = copy.deepcopy(SYNTHETIC_OBJECT)
    record["object_id"] = "SR-OBJ-NEW"
    record["source_ids"] = ["SRC-000001"]
    record["relations"] = []
    record["date"] = "2026-09-14T12:00:00Z"
    return record


@pytest.fixture()
def make_account(db):
    from allauth.account.models import EmailAddress

    from accounts.models import Account

    def factory(email="researcher@example.invalid", display_name="Synthetic Researcher", verified=True, role=Account.RESEARCHER, **extra):
        account = Account.objects.create_user(email=email, password="correct-horse-battery-staple-9", display_name=display_name, role=role, **extra)
        EmailAddress.objects.create(user=account, email=email, verified=verified, primary=True)
        return account

    return factory


@pytest.fixture()
def registered_author(make_account):
    """An account whose author registration has completed end to end through the fake GitHub."""
    from accounts.models import AuthorBinding
    from accounts.services import start_author_registration

    account = make_account()
    start_author_registration(account)
    binding = AuthorBinding.objects.get(account=account)
    assert binding.state == AuthorBinding.REGISTERED, binding.state
    return account


@pytest.fixture()
def client_for(client):
    def login(account):
        client.force_login(account)
        return client

    return login
