"""The read-only listing of one GitHub organization's repositories (registry discovery's input).

``discovery.py`` reconciles the registry allow-list against what an authorized organization
actually holds; this module is the single read it needs: ``GET /orgs/{organization}/repos``,
paged, with the same bounded retry the other GitHub reads use (``core/github/read_client.py``).
It is a listing and nothing else: no repository found here receives a second request, and nothing
here can mutate GitHub. The caller passes the read-only token; ``fetch`` is injectable so tests
reach no network.

The listing is built from page numbers the code chooses, never from a ``Link`` URL the server
sends, so the bearer token can only ever reach ``api.github.com/orgs/<organization>/repos``. A
malformed record, a failed page, or the page cap makes the whole listing *incomplete* (``error``
or ``truncated``) rather than silently shorter: a count that quietly under-reports is exactly the
defect this exists to remove. It lives here, beside its only consumer, and moves to
``core/github/`` when a second one needs it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import quote

from repository_presenter.core.github.read_client import (
    GITHUB_API_ROOT,
    Fetch,
    _get_with_retry,
    fetch_get,
)
from repository_presenter.core.retry import RetryableOperationError
from repository_presenter.core.secrets import redact

PAGE_SIZE = 100
# 3,000 repositories per organization: far beyond any authorized organization, and a bound so a
# misbehaving server can never keep the monitor paging.
MAX_PAGES = 30
_FULL_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ORGANIZATION = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class UpstreamRepository:
    """One repository GitHub reported for the organization.

    Only what classification and the owner's admission decision need: identity, the flags a
    policy rule matches on, and the two facts that say whether it is alive and what it is.
    """

    full_name: str
    repository_id: int
    archived: bool = False
    private: bool = False
    fork: bool = False
    default_branch: str | None = None
    pushed_at: str | None = None
    language: str | None = None

    @property
    def owner(self) -> str:
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/", 1)[1]


@dataclass(frozen=True)
class OrganizationListing:
    """Every repository one organization listed, or why the listing is not trustworthy.

    ``error`` set means nothing may be concluded from ``repositories`` (not even absence);
    ``truncated`` means the list is a true prefix only, so the names it holds are real but a
    name missing from it proves nothing.
    """

    organization: str
    repositories: tuple[UpstreamRepository, ...] = ()
    error: str | None = None
    truncated: bool = False

    @property
    def complete(self) -> bool:
        return self.error is None and not self.truncated


OrganizationLister = Callable[..., OrganizationListing]


def list_organization_repositories(
    organization: str,
    *,
    token: str | None = None,
    fetch: Fetch = fetch_get,
    sleep: Callable[[float], None] | None = None,
) -> OrganizationListing:
    """List ``organization``'s repositories, ``PAGE_SIZE`` at a time, until a short page."""
    if not _ORGANIZATION.fullmatch(organization):
        return OrganizationListing(organization, error="not a valid organization name")
    base = f"{GITHUB_API_ROOT}/orgs/{quote(organization, safe='')}/repos"
    found: list[UpstreamRepository] = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{base}?type=all&per_page={PAGE_SIZE}&page={page}"
        try:
            response = _get_with_retry(url, token=token, fetch=fetch, sleep=sleep)
        except RetryableOperationError as exc:
            return OrganizationListing(organization, error=_scrub(str(exc), token))
        except Exception as exc:  # one organization's failure never aborts the others
            return OrganizationListing(
                organization, error=_scrub(f"{type(exc).__name__}: {exc}", token)
            )
        if response.status_code != 200:
            return OrganizationListing(organization, error=f"HTTP {response.status_code}")
        try:
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("the response is not a list of repositories")
            records = [_repository(item, organization) for item in payload]
        except (ValueError, TypeError, KeyError) as exc:
            return OrganizationListing(
                organization, error=_scrub(f"malformed listing response: {exc}", token)
            )
        found.extend(record for record in records if record is not None)
        if len(payload) < PAGE_SIZE:
            return OrganizationListing(organization, tuple(found))
    return OrganizationListing(organization, tuple(found), truncated=True)


def _repository(item: object, organization: str) -> UpstreamRepository | None:
    """One listed record, or ``None`` for a repository that is not this organization's.

    Anything that cannot be read as a repository record raises ``ValueError``: a half-understood
    record is never skipped, because skipping it would hide a repository from the count.
    """
    if not isinstance(item, Mapping):
        raise ValueError("a listed item is not a repository record")
    full_name = item.get("full_name")
    identity = item.get("id")
    if not isinstance(full_name, str) or not _FULL_NAME.fullmatch(full_name):
        raise ValueError("a repository record has no usable full_name")
    if isinstance(identity, bool) or not isinstance(identity, int) or identity <= 0:
        raise ValueError(f"{full_name} has no usable repository id")
    if full_name.split("/", 1)[0].casefold() != organization.casefold():
        return None
    return UpstreamRepository(
        full_name=full_name,
        repository_id=identity,
        archived=item.get("archived") is True,
        private=item.get("private") is True,
        fork=item.get("fork") is True,
        default_branch=_text(item.get("default_branch")),
        pushed_at=_text(item.get("pushed_at")),
        language=_text(item.get("language")),
    )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _scrub(message: str, token: str | None) -> str:
    return redact(message, [token] if token else [])
