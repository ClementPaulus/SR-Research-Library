"""Git-backed GitHub double for tests. Same interface as GitHubAppClient.

Branches, commits, pull requests, checks and merges are performed on the real
scratch repository (settings.PORTAL_REGISTRY_REPO_PATH) with plumbing commands,
so every publication is visible to the next pinned checkout exactly as a real
fetch would make it. Fault injection: check policy (success/pending/failure),
transient unavailability, and another writer advancing the default branch.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

from .github_app import CheckState, GitHubRefused, GitHubUnavailable


def _env():
    env = dict(os.environ)
    for key, value in (("GIT_AUTHOR_NAME", "Portal Fake GitHub"), ("GIT_AUTHOR_EMAIL", "fake-github@example.invalid"),
                       ("GIT_COMMITTER_NAME", "Portal Fake GitHub"), ("GIT_COMMITTER_EMAIL", "fake-github@example.invalid")):
        env.setdefault(key, value)
    return env


def _git(*args, cwd=None, input=None, check=True, env=None):
    cwd = cwd or settings.PORTAL_REGISTRY_REPO_PATH
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, input=input, env={**_env(), **(env or {})})
    if check and result.returncode != 0:
        raise GitHubRefused(f"git {' '.join(args)}: {result.stderr.strip()[:300]}")
    return result.stdout.strip()


class _State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pulls = {}
        self.checks = {}
        self.check_policy = "success"
        self.unavailable_calls = 0
        self.counter = itertools.count(1)
        self.merges = []

    def advance_default_branch(self, files: dict, message: str = "another writer") -> str:
        client = FakeGitHubClient()
        branch = settings.PORTAL_REGISTRY_DEFAULT_BRANCH
        return client.commit_files(branch, client.default_branch_sha(branch), files, message)

    _advance = advance_default_branch

    @property
    def branches(self):
        out = _git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads/")
        return dict(line.split(" ", 1) for line in out.splitlines() if line)

    def files_at(self, ref: str) -> dict:
        paths = _git("ls-tree", "-r", "--name-only", ref).splitlines()
        files = {}
        for path in paths:
            out = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=settings.PORTAL_REGISTRY_REPO_PATH, capture_output=True)
            try:
                files[path] = out.stdout.decode("utf-8")
            except UnicodeDecodeError:
                files[path] = out.stdout  # binary evidence files stay bytes
        return files

    @property
    def commits(self):
        state = self

        class _Commits:
            def __getitem__(self, sha):
                return {"files": state.files_at(sha)}

        return _Commits()


REPO = _State()


class FakeGitHubClient:
    repo = REPO

    def _maybe_unavailable(self):
        if self.repo.unavailable_calls > 0:
            self.repo.unavailable_calls -= 1
            raise GitHubUnavailable("injected outage")
        # Acceptance runs inject an outage across processes by creating this file.
        outage_file = getattr(settings, "PORTAL_FAKE_GITHUB_OUTAGE_FILE", "")
        if outage_file and Path(outage_file).exists():
            raise GitHubUnavailable("injected outage (file flag)")

    def default_branch_sha(self, branch):
        self._maybe_unavailable()
        return _git("rev-parse", f"refs/heads/{branch}")

    def branch_sha(self, branch):
        self._maybe_unavailable()
        out = _git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        return out or None

    def create_branch(self, branch, sha):
        self._maybe_unavailable()
        if self.branch_sha(branch):
            raise GitHubRefused("422 Reference already exists")
        _git("update-ref", f"refs/heads/{branch}", sha)

    def commit_files(self, branch, parent_sha, files, message):
        self._maybe_unavailable()
        if self.branch_sha(branch) != parent_sha:
            raise GitHubRefused("422 Update is not a fast forward")
        with tempfile.TemporaryDirectory(prefix="fake-gh-index-") as tmp:
            env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
            _git("read-tree", parent_sha, env=env)
            for path, content in sorted(files.items()):
                blob = _git("hash-object", "-w", "--stdin", input=content)
                _git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = _git("write-tree", env=env)
        sha = _git("commit-tree", tree, "-p", parent_sha, "-m", message)
        _git("update-ref", f"refs/heads/{branch}", sha, parent_sha)
        name = settings.GITHUB_REQUIRED_CHECK
        policy = self.repo.check_policy
        self.repo.checks[sha] = (CheckState(name, "completed", "success") if policy == "success"
                                 else CheckState(name, "in_progress", "") if policy == "pending"
                                 else CheckState(name, "completed", "failure"))
        return sha

    def find_pull(self, branch):
        self._maybe_unavailable()
        for pull in self.repo.pulls.values():
            if pull["head"]["ref"] == branch:
                return pull
        return None

    def open_pull(self, branch, base, title, body):
        self._maybe_unavailable()
        number = next(self.repo.counter)
        pull = {"number": number, "state": "open", "merged": False, "merged_at": None, "merge_commit_sha": None,
                "head": {"ref": branch, "sha": self.branch_sha(branch)}, "base": {"ref": base}, "title": title, "body": body}
        self.repo.pulls[number] = pull
        return pull

    def pull(self, number):
        self._maybe_unavailable()
        pull = self.repo.pulls[number]
        pull["head"]["sha"] = self.branch_sha(pull["head"]["ref"]) or pull["head"]["sha"]
        return pull

    def check_state(self, sha, name):
        self._maybe_unavailable()
        return self.repo.checks.get(sha, CheckState(name, "missing", ""))

    def merge_pull(self, number, sha, method, title):
        self._maybe_unavailable()
        pull = self.repo.pulls[number]
        if pull["merged"]:
            raise GitHubRefused("405 Pull Request is not mergeable: already merged")
        if self.branch_sha(pull["head"]["ref"]) != sha:
            raise GitHubRefused("409 Head branch was modified")
        check = self.repo.checks.get(sha)
        if not check or check.conclusion != "success":
            raise GitHubRefused("405 Required status check is not successful")
        base = pull["base"]["ref"]
        base_sha = self.default_branch_sha(base)
        if _git("merge-base", base_sha, sha) != base_sha:
            raise GitHubRefused("405 Base branch was modified. Review and try the merge again.")  # strict up-to-date rule
        tree = _git("rev-parse", f"{sha}^{{tree}}")
        merge_sha = _git("commit-tree", tree, "-p", base_sha, "-m", f"{title} (#{number})") if method == "squash" else sha
        _git("update-ref", f"refs/heads/{base}", merge_sha, base_sha)
        pull.update(merged=True, state="closed", merge_commit_sha=merge_sha, merged_at="now")
        self.repo.merges.append((number, merge_sha))
        return merge_sha

    def file_content(self, path, ref):
        self._maybe_unavailable()
        out = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=settings.PORTAL_REGISTRY_REPO_PATH, text=True, capture_output=True)
        return out.stdout if out.returncode == 0 else None

    def compare(self, base, head):
        return {"status": "ahead", "files": []}
