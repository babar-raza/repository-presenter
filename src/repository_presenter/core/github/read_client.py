"""Read-only observations of a public GitHub repository's current state.

Every function here is one bounded GET against `api.github.com`, retried only on a transient
status under the ``github_api`` policy (`core/retry.py`) — the exact discipline
`extractors/platforms/python_registry.py::observe_pypi` already established for the package
registry boundary. Nothing in this module ever mutates a repository or holds a write-scoped
token: an optional bearer token (the same ``GH_TOKEN`` `core/secrets.py` already recognizes) only
raises the anonymous rate limit, never grants a write capability the read-only clone token
(`core/git_safety/clone.py`) does not already carry.

First consumer: `components/issues/redetect.py`, which re-observes the exact
file or tree a handoff artifact's evidence already cites, at the repository's *current* revision
(which may have moved since the handoff was recorded) rather than the frozen one the artifact
carries — the mechanical form of `docs/investigations/03-issue-tracking.md` section 6's "a fresh
... run at the current pinned revision."
"""

from __future__ import annotations

import base64
import binascii
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from repository_presenter.core.retry import RetryableOperationError, run_with_retry

GITHUB_API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 15.0
USER_AGENT = "repository-presenter (+https://github.com/babar-raza/repository-presenter)"
TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})

Fetch = Callable[[str, str | None], httpx.Response]


@dataclass(frozen=True)
class FileRead:
    """One file's content at one revision, or why it could not be read."""

    repository: str
    revision: str
    path: str
    found: bool
    content: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class TreeRead:
    """Every blob path under a revision's tree, or why the listing could not be read."""

    repository: str
    revision: str
    paths: tuple[str, ...] = ()
    truncated: bool = False
    error: str | None = None


@dataclass(frozen=True)
class DefaultBranchRead:
    """The repository's current default-branch head, or why it could not be read."""

    repository: str
    sha: str | None = None
    branch: str | None = None
    error: str | None = None


def fetch_get(url: str, token: str | None) -> httpx.Response:
    """One bounded GET; the default ``fetch`` every function below accepts an override for."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS, headers=headers, follow_redirects=True
    ) as client:
        return client.get(url)


def _get_with_retry(
    url: str,
    *,
    token: str | None,
    fetch: Fetch,
    sleep: Callable[[float], None] | None,
) -> httpx.Response:
    def attempt() -> httpx.Response:
        try:
            response = fetch(url, token)
        except httpx.TransportError as exc:
            raise RetryableOperationError(f"{type(exc).__name__}: {exc}") from exc
        if response.status_code in TRANSIENT_STATUSES:
            retry_after = response.headers.get("Retry-After")
            raise RetryableOperationError(
                f"HTTP {response.status_code}",
                retry_after_seconds=float(retry_after) if retry_after else None,
            )
        return response

    return run_with_retry("github_api", attempt, sleep=sleep or time.sleep)


def fetch_file(
    repository: str,
    revision: str,
    path: str,
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
) -> FileRead:
    """Read one file's content at ``revision`` via the Contents API (never the working tree)."""
    url = f"{GITHUB_API_ROOT}/repos/{repository}/contents/{path}?ref={revision}"
    try:
        response = _get_with_retry(url, token=token, fetch=fetch, sleep=sleep)
    except RetryableOperationError as exc:
        return FileRead(repository, revision, path, found=False, error=str(exc))
    if response.status_code == 404:
        return FileRead(repository, revision, path, found=False)
    if response.status_code != 200:
        return FileRead(
            repository, revision, path, found=False, error=f"HTTP {response.status_code}"
        )
    try:
        payload = response.json()
        encoded = payload["content"]
        encoding = payload.get("encoding", "base64")
    except (ValueError, KeyError, TypeError) as exc:
        return FileRead(
            repository, revision, path, found=False, error=f"malformed contents response: {exc}"
        )
    if encoding != "base64":
        return FileRead(
            repository, revision, path, found=False, error=f"unsupported encoding {encoding!r}"
        )
    try:
        content = base64.b64decode(encoded).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        return FileRead(repository, revision, path, found=False, error=f"cannot decode: {exc}")
    return FileRead(repository, revision, path, found=True, content=content)


def fetch_tree(
    repository: str,
    revision: str,
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
) -> TreeRead:
    """List every blob path under ``revision``'s tree, recursively."""
    url = f"{GITHUB_API_ROOT}/repos/{repository}/git/trees/{revision}?recursive=1"
    try:
        response = _get_with_retry(url, token=token, fetch=fetch, sleep=sleep)
    except RetryableOperationError as exc:
        return TreeRead(repository, revision, error=str(exc))
    if response.status_code != 200:
        return TreeRead(repository, revision, error=f"HTTP {response.status_code}")
    try:
        payload = response.json()
        entries = payload["tree"]
        truncated = bool(payload.get("truncated", False))
    except (ValueError, KeyError, TypeError) as exc:
        return TreeRead(repository, revision, error=f"malformed tree response: {exc}")
    paths = tuple(sorted(e["path"] for e in entries if e.get("type") == "blob"))
    return TreeRead(repository, revision, paths=paths, truncated=truncated)


def fetch_default_branch_sha(
    repository: str,
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
) -> DefaultBranchRead:
    """The repository's current default branch name and head commit sha."""
    repo_url = f"{GITHUB_API_ROOT}/repos/{repository}"
    try:
        repo_response = _get_with_retry(repo_url, token=token, fetch=fetch, sleep=sleep)
    except RetryableOperationError as exc:
        return DefaultBranchRead(repository, error=str(exc))
    if repo_response.status_code != 200:
        return DefaultBranchRead(repository, error=f"HTTP {repo_response.status_code}")
    try:
        branch = repo_response.json()["default_branch"]
    except (ValueError, KeyError, TypeError) as exc:
        return DefaultBranchRead(repository, error=f"malformed repository response: {exc}")
    commit_url = f"{GITHUB_API_ROOT}/repos/{repository}/commits/{branch}"
    try:
        commit_response = _get_with_retry(commit_url, token=token, fetch=fetch, sleep=sleep)
    except RetryableOperationError as exc:
        return DefaultBranchRead(repository, branch=branch, error=str(exc))
    if commit_response.status_code != 200:
        return DefaultBranchRead(
            repository, branch=branch, error=f"HTTP {commit_response.status_code}"
        )
    try:
        sha = commit_response.json()["sha"]
    except (ValueError, KeyError, TypeError) as exc:
        return DefaultBranchRead(
            repository, branch=branch, error=f"malformed commit response: {exc}"
        )
    return DefaultBranchRead(repository, sha=sha, branch=branch)
