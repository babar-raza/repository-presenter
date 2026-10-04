"""GitHub REST client: read (``GET /repos/{owner}/{repo}``, always available) and three gated write
halves (``PATCH /repos/{owner}/{repo}`` + ``PUT /repos/{owner}/{repo}/topics``,
``POST /repos/{owner}/{repo}/issues``, and the branch/contents/pull-request primitives
``components/propose/effect.py`` composes into one proposal effect).

The read half is the one GitHub-metadata read this project's production code makes outside cloning
(``core/git_safety/clone.py`` already reads with the same ``GH_TOKEN`` to pin and push-disable a
clone). It exists to observe a repository's current ``description``, ``homepage``, and ``topics``
(workstream 2 Phase 0, docs/investigations/02-repo-metadata-community-files.md section 5).

The metadata write half (``update_repository``, ``replace_topics``) exists so
``components/metadata/apply.py`` (workstream 2 Phase 1, the gated write path) has a real function to
call - but this module itself performs no authorization check and never decides whether a write
*should* happen. ``apply.py`` is the only production caller, and it refuses to reach either function
unless an explicit, owner-controlled authorization signal is present (never inferred from a
credential's mere presence or scope, per ``AGENTS.md`` "Security and Effects"); no other code in
this project calls either write function. Both still need a write-scoped token distinct from the
read-only ``GH_TOKEN`` this module's read half uses (``GH_METADATA_WRITE_TOKEN`` -
``core/secrets.py``) - the ``Administration: write`` scope this project's own ``GH_TOKEN`` does not
have (``OWNER-04``, ``project/state.yaml``).

The issue-filing write half (``create_issue``) exists so ``components/issues/file.py`` (workstream 3
Phase 3, the gated issue-filing path) has a real function to call - the same split: this module
performs no authorization check of its own, and no other code calls it. It needs its own
write-scoped token, also distinct from ``GH_TOKEN`` (``GH_ISSUES_WRITE_TOKEN`` -
``core/secrets.py``) - the ``Issues: write`` scope this project's own ``GH_TOKEN`` does not have.

The proposal-effect write half (``get_ref``/``create_ref``/``get_contents``/``put_contents``/
``find_open_pull_request``/``create_pull_request``/``update_pull_request``) exists so
``components/propose/effect.py`` (G6-W02, the gated README-proposal PR effect) has real functions to
compose one idempotent "create or update a presenter branch and its PR" effect from. Same split
again: no authorization check here, no other caller. Its own write-scoped token is
``GH_PROPOSAL_WRITE_TOKEN`` (``core/secrets.py``) - a fresh, repository-scoped App installation
token minted only inside ``propose.yml``'s effect job, never ``GH_TOKEN`` and never reused from the
``GH_METADATA_WRITE_TOKEN``/``GH_ISSUES_WRITE_TOKEN`` halves above, even though all three are
GitHub App installation tokens in principle - each effect mints and uses its own.

``fetch``/``write`` are injected the same way ``tools/discovery/portfolio_discovery.py`` and
``components/readme/evidence/facts/links.py`` already inject their HTTP calls: a plain
``(status_code, body)`` callable, so every test here runs with a fake and makes no live network
call.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from repository_presenter.core.errors import RepositoryMetadataError

API_ROOT = "https://api.github.com"
USER_AGENT = "repository-presenter (+https://github.com/babar-raza/repository-presenter)"
REQUEST_TIMEOUT_SECONDS = 30.0
SCHEMA_VERSION = 1

FetchFn = Callable[[str, "str | None"], "tuple[int, Any]"]
WriteFn = Callable[[str, str, "dict[str, Any]"], "tuple[int, Any]"]
ClockFn = Callable[[], str]


def default_fetch(url: str, token: str | None) -> tuple[int, Any]:
    """GET ``url`` from the GitHub REST API. Returns ``(status_code, parsed_json_or_none)``.

    Never raises for an HTTP-level failure (404, 403, 5xx) or a transport failure (DNS, timeout,
    connection refused) - the caller decides what a given outcome means, mirroring
    ``tools/discovery/portfolio_discovery.py::default_fetch``. Status ``-1`` means unreachable,
    with the exception recorded as the (unparsed) body.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ObservedRepository:
    """GitHub's own current view of one repository's description, homepage, and topics.

    An observation, not a fact bound to a source revision: these three fields are repository
    settings, not commit content, and can change independently of any revision this project has
    ever cloned (docs/investigations/02-repo-metadata-community-files.md section 2.1).
    """

    repository: str
    description: str | None
    homepage: str | None
    topics: tuple[str, ...]
    observed_at: str
    schema_version: int = SCHEMA_VERSION


def get_repository(
    owner: str,
    name: str,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
    clock: ClockFn = _utc_now,
) -> ObservedRepository:
    """Read ``description``, ``homepage``, and ``topics`` as GitHub currently reports them.

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 200 - a denied,
    rate-limited, missing, or unreachable repository never yields a partial or guessed
    observation.
    """
    url = f"{API_ROOT}/repos/{owner}/{name}"
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    raw_topics = body.get("topics")
    topics = tuple(str(t) for t in raw_topics) if isinstance(raw_topics, list) else ()
    description = body.get("description") or None
    homepage = body.get("homepage") or None
    return ObservedRepository(
        repository=f"{owner}/{name}",
        description=description if isinstance(description, str) else None,
        homepage=homepage if isinstance(homepage, str) else None,
        topics=topics,
        observed_at=clock(),
    )


def _write_headers(token: str) -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }


def default_patch(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``PATCH url`` with ``payload`` as JSON. Never called except by ``update_repository``, which
    is itself never called except by ``components/metadata/apply.py`` after that module's own
    authorization check passes - see this module's docstring."""
    try:
        response = httpx.patch(
            url, headers=_write_headers(token), json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def default_put(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``PUT url`` with ``payload`` as JSON. Never called except by ``replace_topics``, which is
    itself never called except by ``components/metadata/apply.py`` after that module's own
    authorization check passes - see this module's docstring."""
    try:
        response = httpx.put(
            url, headers=_write_headers(token), json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def update_repository(
    owner: str,
    name: str,
    *,
    description: str | None = None,
    homepage: str | None = None,
    token: str,
    write: WriteFn = default_patch,
) -> None:
    """``PATCH /repos/{owner}/{repo}`` with only the fields given - a field left ``None`` is never
    included in the request body, so it is left untouched on GitHub, never cleared.

    Raises :class:`ValueError` if both fields are ``None`` (nothing to change - the caller should
    not have reached here) and :class:`RepositoryMetadataError` on anything but a well-formed
    HTTP 200, mirroring :func:`get_repository`'s own fail-closed shape.
    """
    payload: dict[str, Any] = {}
    if description is not None:
        payload["description"] = description
    if homepage is not None:
        payload["homepage"] = homepage
    if not payload:
        raise ValueError("update_repository called with nothing to change")
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}"
    status_code, body = write(url, token, payload)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH {url} returned HTTP {status_code}")


def replace_topics(
    owner: str,
    name: str,
    *,
    topics: tuple[str, ...],
    token: str,
    write: WriteFn = default_put,
) -> None:
    """``PUT /repos/{owner}/{repo}/topics`` - replaces the full topic set (GitHub's own endpoint
    shape has no partial-update mode; the caller passes the complete proposed set).

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 200.
    """
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PUT refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/topics"
    status_code, body = write(url, token, {"names": list(topics)})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200:
        raise RepositoryMetadataError(f"{owner}/{name}: PUT {url} returned HTTP {status_code}")


@dataclass(frozen=True)
class CreatedIssue:
    """What GitHub returns for a successfully created issue - only what a caller needs to record
    it as a handoff's own ``issue_ref`` (``components/issues/model.py::IssueRef``)."""

    number: int
    url: str


def default_post(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
    """``POST url`` with ``payload`` as JSON. Never called except by ``create_issue``, which is
    itself never called except by ``components/issues/file.py`` after that module's own
    authorization check passes - see this module's docstring."""
    try:
        response = httpx.post(
            url, headers=_write_headers(token), json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        return -1, f"{type(exc).__name__}: {exc}"
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def create_issue(
    owner: str,
    name: str,
    *,
    title: str,
    body: str,
    token: str,
    write: WriteFn = default_post,
) -> CreatedIssue:
    """``POST /repos/{owner}/{repo}/issues``.

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 201 (GitHub's own
    success status for issue creation), or a response missing the ``number``/``html_url`` fields a
    caller needs to record what was filed - never a guessed or partial result.
    """
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/issues"
    status_code, response_body = write(url, token, {"title": title, "body": body})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code != 201:
        raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")
    if (
        not isinstance(response_body, dict)
        or "number" not in response_body
        or "html_url" not in response_body
    ):
        raise RepositoryMetadataError(
            f"{owner}/{name}: POST {url} returned HTTP 201 with no usable issue body"
        )
    return CreatedIssue(number=int(response_body["number"]), url=str(response_body["html_url"]))


ISSUE_LIST_PAGE_SIZE = 100
ISSUE_LIST_MAX_PAGES = 10


def find_issue_with_marker(
    owner: str,
    name: str,
    marker: str,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
) -> CreatedIssue | None:
    """The issue (open or closed, never a pull request) whose body contains ``marker``, or ``None``.

    This is the remote half of the filer's dedup: a scheduled run starts from a fresh checkout whose
    handoff may still read ``HANDOFF_PENDING``, so the upstream issue body itself must prove the
    defect was already filed. ``None`` is returned only after every page was read and none matched.
    Raises :class:`RepositoryMetadataError` when the scan is incomplete (an error, or more than
    ``ISSUE_LIST_MAX_PAGES`` full pages) - absence is never inferred from a partial read.
    """
    for page in range(1, ISSUE_LIST_MAX_PAGES + 1):
        url = (
            f"{API_ROOT}/repos/{owner}/{name}/issues"
            f"?state=all&per_page={ISSUE_LIST_PAGE_SIZE}&page={page}"
        )
        status_code, body = fetch(url, token)
        if status_code == -1:
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
        if status_code != 200 or not isinstance(body, list):
            raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
        for item in body:
            if not isinstance(item, dict) or "pull_request" in item:
                continue
            text = item.get("body")
            if isinstance(text, str) and marker in text:
                number = item.get("number")
                html_url = item.get("html_url")
                if not isinstance(number, int) or not isinstance(html_url, str):
                    raise RepositoryMetadataError(
                        f"{owner}/{name}: matching issue has no usable number/html_url"
                    )
                return CreatedIssue(number=number, url=html_url)
        if len(body) < ISSUE_LIST_PAGE_SIZE:
            return None
    raise RepositoryMetadataError(
        f"{owner}/{name}: more than {ISSUE_LIST_MAX_PAGES} pages of issues - cannot prove absence"
    )


def close_issue(
    owner: str,
    name: str,
    number: int,
    *,
    state_reason: str,
    token: str,
    write: WriteFn = default_patch,
) -> None:
    """``PATCH /repos/{owner}/{repo}/issues/{number}`` with ``state: closed`` and GitHub's own
    ``state_reason`` (``completed`` or ``not_planned``).

    Raises :class:`RepositoryMetadataError` on anything but a well-formed HTTP 200. Closing an
    already-closed issue is GitHub-idempotent, so a re-run never fails on it.
    """
    if state_reason not in ("completed", "not_planned"):
        raise ValueError(f"unsupported state_reason {state_reason!r}")
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/issues/{number}"
    status_code, body = write(url, token, {"state": "closed", "state_reason": state_reason})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH {url} returned HTTP {status_code}")


# ---------------------------------------------------------------------------
# Proposal effect: branch, contents, and pull-request primitives
# (components/propose/effect.py's own gated caller, not this module).
# ---------------------------------------------------------------------------


def get_ref(
    owner: str,
    name: str,
    branch: str,
    *,
    token: str,
    fetch: FetchFn = default_fetch,
) -> str | None:
    """``GET /repos/{owner}/{repo}/git/ref/heads/{branch}`` - the branch's current tip commit SHA,
    or ``None`` if the branch does not exist yet (HTTP 404, the only case this treats as a normal
    outcome rather than a failure - the presenter branch legitimately does not exist on a target's
    first-ever proposal)."""
    url = f"{API_ROOT}/repos/{owner}/{name}/git/ref/heads/{branch}"
    status_code, body = fetch(url, token)
    if status_code == 404:
        return None
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    sha = body.get("object", {}).get("sha")
    if not isinstance(sha, str) or not sha:
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned no usable commit sha")
    return sha


def create_ref(
    owner: str,
    name: str,
    branch: str,
    sha: str,
    *,
    token: str,
    write: WriteFn = default_post,
) -> None:
    """``POST /repos/{owner}/{repo}/git/refs`` - creates ``branch`` pointing at ``sha``. Only ever
    called when :func:`get_ref` has already confirmed the branch does not exist - this project's
    one stable presenter branch per target is created once and reused, never recreated."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/git/refs"
    status_code, body = write(url, token, {"ref": f"refs/heads/{branch}", "sha": sha})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 201:
        raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")


@dataclass(frozen=True)
class FileContents:
    """One file's current content on one branch, as GitHub's Contents API reports it."""

    path: str
    sha: str
    text: str


def get_contents(
    owner: str,
    name: str,
    path: str,
    *,
    ref: str,
    token: str,
    fetch: FetchFn = default_fetch,
) -> FileContents | None:
    """``GET /repos/{owner}/{repo}/contents/{path}?ref={ref}`` - the file's current text and blob
    ``sha`` on ``ref``, or ``None`` if the file does not exist on that branch yet (HTTP 404)."""
    url = f"{API_ROOT}/repos/{owner}/{name}/contents/{path}?ref={ref}"
    status_code, body = fetch(url, token)
    if status_code == 404:
        return None
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    sha = body.get("sha")
    encoded = body.get("content")
    if not isinstance(sha, str) or not isinstance(encoded, str):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned no usable content")
    text = base64.b64decode(encoded.encode("ascii").replace(b"\n", b"")).decode("utf-8")
    return FileContents(path=path, sha=sha, text=text)


@dataclass(frozen=True)
class CommitOutcome:
    """The result of one ``put_contents`` call - the new blob/commit SHAs GitHub assigned."""

    content_sha: str
    commit_sha: str


def put_contents(
    owner: str,
    name: str,
    path: str,
    *,
    branch: str,
    message: str,
    text: str,
    sha: str | None,
    token: str,
    write: WriteFn = default_put,
) -> CommitOutcome:
    """``PUT /repos/{owner}/{repo}/contents/{path}`` - creates or updates ``path`` on ``branch``
    with one commit. ``sha`` is the file's current blob sha (from :func:`get_contents`) when
    updating an existing file, or ``None`` when creating it for the first time on this branch -
    GitHub's own endpoint distinguishes create/update by this field's presence, not a different
    verb. Raises :class:`RepositoryMetadataError` with the word "unreachable" in its message for a
    transport-level failure specifically (status ``-1``) - ``components/propose/effect.py`` pattern-
    matches that wording to tell a genuinely lost response (eligible for reconciliation) apart from
    a hard rejection (422 validation error, 409 conflicting sha, etc.), which is never retried
    blindly."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PUT refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/contents/{path}"
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha is not None:
        payload["sha"] = sha
    status_code, body = write(url, token, payload)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code not in (200, 201) or not isinstance(body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: PUT {url} returned HTTP {status_code}")
    content_sha = body.get("content", {}).get("sha")
    commit_sha = body.get("commit", {}).get("sha")
    if not isinstance(content_sha, str) or not isinstance(commit_sha, str):
        raise RepositoryMetadataError(f"{owner}/{name}: PUT {url} returned no usable commit")
    return CommitOutcome(content_sha=content_sha, commit_sha=commit_sha)


@dataclass(frozen=True)
class PullRequestRef:
    """One pull request's identity and current title/body, as GitHub reports it."""

    number: int
    url: str
    title: str
    body: str


def find_open_pull_request(
    owner: str,
    name: str,
    *,
    head_branch: str,
    token: str,
    fetch: FetchFn = default_fetch,
) -> PullRequestRef | None:
    """``GET /repos/{owner}/{repo}/pulls?head={owner}:{head_branch}&state=open`` - the one open
    presenter PR for this target, if any. This project keeps exactly one open PR per target, so the
    first match is authoritative; an empty result means none exists yet."""
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls?head={owner}:{head_branch}&state=open"
    status_code, body = fetch(url, token)
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({body})")
    if status_code != 200 or not isinstance(body, list):
        raise RepositoryMetadataError(f"{owner}/{name}: GET {url} returned HTTP {status_code}")
    if not body:
        return None
    first = body[0]
    return PullRequestRef(
        number=int(first["number"]),
        url=str(first["html_url"]),
        title=str(first.get("title", "")),
        body=str(first.get("body") or ""),
    )


def create_pull_request(
    owner: str,
    name: str,
    *,
    title: str,
    body: str,
    head: str,
    base: str,
    token: str,
    write: WriteFn = default_post,
) -> PullRequestRef:
    """``POST /repos/{owner}/{repo}/pulls`` - opens the one presenter PR from ``head`` into
    ``base``. Only ever called after :func:`find_open_pull_request` has confirmed none is open."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: POST refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls"
    status_code, response_body = write(
        url, token, {"title": title, "body": body, "head": head, "base": base}
    )
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code != 201 or not isinstance(response_body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: POST {url} returned HTTP {status_code}")
    return PullRequestRef(
        number=int(response_body["number"]),
        url=str(response_body["html_url"]),
        title=str(response_body.get("title", title)),
        body=str(response_body.get("body") or body),
    )


def update_pull_request(
    owner: str,
    name: str,
    number: int,
    *,
    title: str,
    body: str,
    token: str,
    write: WriteFn = default_patch,
) -> PullRequestRef:
    """``PATCH /repos/{owner}/{repo}/pulls/{number}`` - refreshes an existing presenter PR's title
    and body in place. Only ever called when the live title/body already differ from what this
    proposal would write - a no-op invocation makes no call at all (``components/propose/effect.py``
    checks before calling this), so a repeated, unchanged proposal never produces a spurious PR
    edit."""
    if not token:
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH refused - no write-scoped token")
    url = f"{API_ROOT}/repos/{owner}/{name}/pulls/{number}"
    status_code, response_body = write(url, token, {"title": title, "body": body})
    if status_code == -1:
        raise RepositoryMetadataError(f"{owner}/{name}: unreachable ({response_body})")
    if status_code != 200 or not isinstance(response_body, dict):
        raise RepositoryMetadataError(f"{owner}/{name}: PATCH {url} returned HTTP {status_code}")
    return PullRequestRef(
        number=number,
        url=str(response_body.get("html_url", f"{API_ROOT}/{owner}/{name}/pull/{number}")),
        title=str(response_body.get("title", title)),
        body=str(response_body.get("body") or body),
    )
