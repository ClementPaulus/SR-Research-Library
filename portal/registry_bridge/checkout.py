"""Pinned, isolated checkouts of the research repository.

Every evaluation and publication works in its own temporary checkout created
with ``git archive`` at an explicit base commit. Nothing mutates the shared
clone's working tree, and no two jobs share a writable directory.
"""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings


class GitError(RuntimeError):
    pass


def _git(*args, cwd: Path = None, check: bool = True) -> str:
    cwd = cwd or settings.PORTAL_REGISTRY_REPO_PATH
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()[:400]}")
    return result.stdout.strip()


def repository_head(ref: str = None) -> str:
    """Commit SHA of the pinned base: the fetched default branch when a remote is configured, else HEAD."""
    repo = settings.PORTAL_REGISTRY_REPO_PATH
    if ref:
        return _git("rev-parse", ref, cwd=repo)
    if getattr(settings, "PORTAL_REGISTRY_USE_LOCAL_HEAD", False):
        return _git("rev-parse", "HEAD", cwd=repo)
    remote_ref = f"{settings.PORTAL_REGISTRY_REMOTE}/{settings.PORTAL_REGISTRY_DEFAULT_BRANCH}"
    out = _git("rev-parse", "--verify", "--quiet", remote_ref, cwd=repo, check=False)
    return out or _git("rev-parse", "HEAD", cwd=repo)


def fetch_default_branch() -> str:
    """Fetch the latest default branch (no-op if the remote is unavailable) and return its SHA."""
    repo = settings.PORTAL_REGISTRY_REPO_PATH
    remotes = _git("remote", cwd=repo, check=False).split()
    if settings.PORTAL_REGISTRY_REMOTE in remotes and not getattr(settings, "PORTAL_REGISTRY_USE_LOCAL_HEAD", False):
        subprocess.run(["git", "fetch", "--quiet", settings.PORTAL_REGISTRY_REMOTE, settings.PORTAL_REGISTRY_DEFAULT_BRANCH],
                       cwd=repo, text=True, capture_output=True, timeout=120)
    return repository_head()


def commit_exists(sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=settings.PORTAL_REGISTRY_REPO_PATH,
                          capture_output=True).returncode == 0


@contextmanager
def isolated_checkout(base_sha: str, keep: bool = False):
    """Yield a Path to a fresh, isolated copy of the repository at ``base_sha``."""
    workdir = Path(tempfile.mkdtemp(prefix="sr-eval-"))
    try:
        archive = workdir / "base.tar"
        with archive.open("wb") as handle:
            proc = subprocess.run(["git", "archive", "--format=tar", base_sha], cwd=settings.PORTAL_REGISTRY_REPO_PATH,
                                  stdout=handle, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise GitError(f"git archive {base_sha} failed: {proc.stderr.decode(errors='replace')[:400]}")
        checkout = workdir / "repo"
        checkout.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(checkout, filter="data")
        archive.unlink()
        (checkout / ".sr-base-sha").write_text(base_sha + "\n", encoding="utf-8")
        yield checkout
    finally:
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)


def changed_files(checkout: Path, base_sha: str) -> dict:
    """{repo-relative path: content} for files that differ from the base commit (text files only)."""
    changed = {}
    base_tree = _git("ls-tree", "-r", "--name-only", base_sha)
    base_paths = set(base_tree.splitlines())
    for path in sorted(p for p in checkout.rglob("*") if p.is_file()):
        rel = path.relative_to(checkout).as_posix()
        if rel == ".sr-base-sha" or rel.startswith(".git/"):
            continue
        content = path.read_bytes()
        if rel in base_paths:
            original = subprocess.run(["git", "show", f"{base_sha}:{rel}"], cwd=settings.PORTAL_REGISTRY_REPO_PATH,
                                      capture_output=True).stdout
            if original == content:
                continue
        try:
            changed[rel] = content.decode("utf-8")
        except UnicodeDecodeError:
            raise GitError(f"refusing to publish non-text file {rel}")
    return changed
