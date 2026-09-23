"""Read-only GitHub REST client: ``GET /repos/{owner}/{repo}`` only.

This is the one GitHub-metadata read this project's production code makes outside cloning
(``core/git_safety/clone.py`` already reads with the same ``GH_TOKEN`` to pin and push-disable a
clone). It exists to observe a repository's current ``description``, ``homepage``, and ``topics``
(workstream 2 Phase 0, docs/investigations/02-repo-metadata-community-files.md section 5) - never to
change them. There is no write function in this module and none should be added here without a
separate, explicitly authorized work item: ``PATCH /repos/{owner}/{repo}`` and
``PUT /repos/{owner}/{repo}/topics`` both need the ``Administration: write`` scope this project's
credential does not have (``OWNER-04``, ``project/state.yaml``).

``fetch`` is injected the same way ``tools/discovery/portfolio_discovery.py`` and
``components/readme/evidence/facts/links.py`` already inject their HTTP calls: a plain
``(status_code, body)`` callable, so every test here runs with a fake and makes no live network
call.
"""

from __future__ import annotations

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
