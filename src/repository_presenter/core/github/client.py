"""GitHub REST client: read (``GET /repos/{owner}/{repo}``, always available) and a gated write
half (``PATCH /repos/{owner}/{repo}`` and ``PUT /repos/{owner}/{repo}/topics``).

The read half is the one GitHub-metadata read this project's production code makes outside cloning
(``core/git_safety/clone.py`` already reads with the same ``GH_TOKEN`` to pin and push-disable a
clone). It exists to observe a repository's current ``description``, ``homepage``, and ``topics``
(workstream 2 Phase 0, docs/investigations/02-repo-metadata-community-files.md section 5).

The write half (``update_repository``, ``replace_topics``) exists so
``components/metadata/apply.py`` (workstream 2 Phase 1, the gated write path) has a real function to
call - but this module itself performs no authorization check and never decides whether a write
*should* happen. ``apply.py`` is the only production caller, and it refuses to reach either function
unless an explicit, owner-controlled authorization signal is present (never inferred from a
credential's mere presence or scope, per ``AGENTS.md`` "Security and Effects"); no other code in
this project calls either write function. Both still need a write-scoped token distinct from the
read-only ``GH_TOKEN`` this module's read half uses (``GH_METADATA_WRITE_TOKEN`` -
``core/secrets.py``) - the ``Administration: write`` scope this project's own ``GH_TOKEN`` does not
have (``OWNER-04``, ``project/state.yaml``).

``fetch``/``write`` are injected the same way ``tools/discovery/portfolio_discovery.py`` and
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
