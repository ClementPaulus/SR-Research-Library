"""GitHub App client: short-lived installation tokens, Git Data API commits, PRs, checks, merges.

Credentials never reach the browser or logs. The private key comes from the
secret manager (PEM text or a file path). Installation tokens are cached until
shortly before expiry and refreshed on demand.
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import jwt
import requests
from django.conf import settings

log = logging.getLogger("portal.github")


class GitHubUnavailable(RuntimeError):
    """Transient (network, 5xx, rate limit): retry with backoff."""


class GitHubRefused(RuntimeError):
    """Deterministic (4xx other than rate limit): needs a specific action."""


@dataclass
class CheckState:
    name: str
    status: str      # queued | in_progress | completed | missing
    conclusion: str  # success | failure | neutral | cancelled | timed_out | action_required | ""


class GitHubAppClient:
    def __init__(self):
        self.api = settings.GITHUB_API_URL.rstrip("/")
        self.owner = settings.GITHUB_REPO_OWNER
        self.repo = settings.GITHUB_REPO_NAME
        self.app_id = settings.GITHUB_APP_ID
        self.installation_id = settings.GITHUB_APP_INSTALLATION_ID
        self._token = None
        self._token_expires = 0
        missing = [name for name, value in (("GITHUB_REPO_OWNER", self.owner), ("GITHUB_REPO_NAME", self.repo),
                                            ("GITHUB_APP_ID", self.app_id), ("GITHUB_APP_INSTALLATION_ID", self.installation_id))
                   if not value]
        if missing:
            raise GitHubRefused("GitHub App is not configured: missing " + ", ".join(missing))

    # ------------------------------------------------------------------ auth
    def _private_key(self) -> str:
        if settings.GITHUB_APP_PRIVATE_KEY:
            return settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
        if settings.GITHUB_APP_PRIVATE_KEY_PATH:
            return Path(settings.GITHUB_APP_PRIVATE_KEY_PATH).read_text(encoding="utf-8")
        raise GitHubRefused("GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_PATH must be configured")

    def _app_jwt(self) -> str:
        now = int(time.time())
        return jwt.encode({"iat": now - 60, "exp": now + 9 * 60, "iss": str(self.app_id)}, self._private_key(), algorithm="RS256")

    def _installation_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        response = requests.post(f"{self.api}/app/installations/{self.installation_id}/access_tokens",
                                 headers={"Authorization": f"Bearer {self._app_jwt()}", "Accept": "application/vnd.github+json"},
                                 timeout=20)
        if response.status_code >= 500:
            raise GitHubUnavailable(f"token endpoint {response.status_code}")
        if response.status_code != 201:
            raise GitHubRefused(f"installation token refused ({response.status_code})")
        payload = response.json()
        self._token = payload["token"]
        self._token_expires = time.time() + 55 * 60
        return self._token

    def _request(self, method: str, path: str, **kwargs):
        headers = {"Authorization": f"Bearer {self._installation_token()}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        url = path if path.startswith("http") else f"{self.api}/repos/{self.owner}/{self.repo}{path}"
        try:
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise GitHubUnavailable(f"network error: {type(exc).__name__}") from exc
        if response.status_code in (401,) and self._token:
            self._token = None  # expired installation token: refresh once
            headers["Authorization"] = f"Bearer {self._installation_token()}"
            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubUnavailable("rate limited")
        if response.status_code >= 500:
            raise GitHubUnavailable(f"{method} {path} -> {response.status_code}")
        if response.status_code >= 400:
            detail = response.json().get("message", "") if response.headers.get("content-type", "").startswith("application/json") else ""
            raise GitHubRefused(f"{method} {path} -> {response.status_code} {detail}"[:300])
        return response.json() if response.content else {}

    # ------------------------------------------------------------------ repository state
    def default_branch_sha(self, branch: str) -> str:
        return self._request("GET", f"/git/ref/heads/{branch}")["object"]["sha"]

    def branch_sha(self, branch: str) -> str | None:
        try:
            return self._request("GET", f"/git/ref/heads/{branch}")["object"]["sha"]
        except GitHubRefused as exc:
            if "404" in str(exc):
                return None
            raise

    def create_branch(self, branch: str, sha: str) -> None:
        self._request("POST", "/git/refs", json={"ref": f"refs/heads/{branch}", "sha": sha})

    def commit_files(self, branch: str, parent_sha: str, files: dict, message: str) -> str:
        """Create one commit on ``branch`` containing ``files`` on top of ``parent_sha``; returns the new SHA."""
        parent = self._request("GET", f"/git/commits/{parent_sha}")
        tree_entries = []
        for path, content in sorted(files.items()):
            blob = self._request("POST", "/git/blobs", json={"content": content, "encoding": "utf-8"})
            tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self._request("POST", "/git/trees", json={"base_tree": parent["tree"]["sha"], "tree": tree_entries})
        commit = self._request("POST", "/git/commits", json={"message": message, "tree": tree["sha"], "parents": [parent_sha]})
        self._request("PATCH", f"/git/refs/heads/{branch}", json={"sha": commit["sha"], "force": False})
        return commit["sha"]

    def find_pull(self, branch: str) -> dict | None:
        pulls = self._request("GET", f"/pulls?head={self.owner}:{branch}&state=all&per_page=5")
        return pulls[0] if pulls else None

    def open_pull(self, branch: str, base: str, title: str, body: str) -> dict:
        return self._request("POST", "/pulls", json={"head": branch, "base": base, "title": title, "body": body})

    def pull(self, number: int) -> dict:
        return self._request("GET", f"/pulls/{number}")

    def check_state(self, sha: str, name: str) -> CheckState:
        runs = self._request("GET", f"/commits/{sha}/check-runs?per_page=100").get("check_runs", [])
        for run in runs:
            if run.get("name") == name:
                return CheckState(name, run.get("status", ""), run.get("conclusion") or "")
        statuses = self._request("GET", f"/commits/{sha}/status").get("statuses", [])
        for status in statuses:
            if status.get("context") == name:
                state = status.get("state")
                return CheckState(name, "completed" if state in ("success", "failure", "error") else "in_progress",
                                  "success" if state == "success" else ("failure" if state else ""))
        return CheckState(name, "missing", "")

    def merge_pull(self, number: int, sha: str, method: str, title: str) -> str:
        result = self._request("PUT", f"/pulls/{number}/merge", json={"sha": sha, "merge_method": method, "commit_title": title})
        if not result.get("merged"):
            raise GitHubRefused(result.get("message", "merge not performed"))
        return result["sha"]

    def file_content(self, path: str, ref: str) -> str | None:
        try:
            payload = self._request("GET", f"/contents/{path}?ref={ref}")
        except GitHubRefused as exc:
            if "404" in str(exc):
                return None
            raise
        if payload.get("encoding") == "base64":
            return base64.b64decode(payload["content"]).decode("utf-8")
        return payload.get("content")

    def compare(self, base: str, head: str) -> dict:
        return self._request("GET", f"/compare/{base}...{head}")


def client():
    from django.utils.module_loading import import_string

    return import_string(settings.PORTAL_GITHUB_ADAPTER)()
