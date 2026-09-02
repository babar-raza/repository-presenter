"""Observe the package registry: is the distribution the manifest names really on PyPI?

The install command a README shows is a claim about the registry, not about the tree, so the
claim is checked against PyPI's JSON API (one bounded read, retried only on transient failures)
and recorded as an observation: found or not, the latest version, and whether the manifest's
version is published. A registry that cannot be reached leaves the claim unresolved.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from repository_presenter.core.retry import RetryableOperationError, run_with_retry

PYPI_PROJECT_URL = "https://pypi.org/pypi/{name}/json"
REQUEST_TIMEOUT_SECONDS = 15.0
USER_AGENT = "repository-presenter (+https://github.com/babar-raza/repository-presenter)"
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RegistryObservation:
    """What the registry said about one distribution name."""

    name: str
    url: str
    found: bool
    latest_version: str | None = None
    manifest_version_published: bool | None = None
    error: str | None = None

    @property
    def summary(self) -> str:
        if self.error is not None:
            return f"package registry unreachable: {self.error}"
        if not self.found:
            return "package registry: distribution not found"
        published = (
            "manifest version published"
            if self.manifest_version_published
            else "manifest version not published"
            if self.manifest_version_published is False
            else "manifest version unknown"
        )
        return f"package registry: found; latest {self.latest_version}; {published}"


def fetch_project_json(url: str, transport: httpx.BaseTransport | None = None) -> httpx.Response:
    """One bounded GET against the registry; a transport override exists for tests only."""
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        transport=transport,
        follow_redirects=True,
    ) as client:
        return client.get(url)


def observe_pypi(
    name: str,
    manifest_version: str | None,
    *,
    fetch: Callable[[str], httpx.Response] = fetch_project_json,
    sleep: Callable[[float], None] | None = None,
) -> RegistryObservation:
    """Observe ``name`` on PyPI, retrying transient failures under the package_registry policy."""
    url = PYPI_PROJECT_URL.format(name=name)

    def attempt() -> httpx.Response:
        try:
            response = fetch(url)
        except httpx.TransportError as exc:
            raise RetryableOperationError(f"{type(exc).__name__}: {exc}") from exc
        if response.status_code in _TRANSIENT_STATUSES:
            retry_after = response.headers.get("Retry-After")
            raise RetryableOperationError(
                f"HTTP {response.status_code}",
                retry_after_seconds=float(retry_after) if retry_after else None,
            )
        return response

    try:
        response = run_with_retry("package_registry", attempt, sleep=sleep or time.sleep)
    except RetryableOperationError as exc:
        return RegistryObservation(name, url, found=False, error=str(exc))
    if response.status_code == 404:
        return RegistryObservation(name, url, found=False)
    if response.status_code != 200:
        return RegistryObservation(name, url, found=False, error=f"HTTP {response.status_code}")
    try:
        payload: Any = response.json()
        latest = str(payload["info"]["version"])
        releases = payload.get("releases") or {}
    except (ValueError, KeyError, TypeError) as exc:
        return RegistryObservation(
            name, url, found=False, error=f"malformed registry response: {exc}"
        )
    published = None if manifest_version is None else manifest_version in releases
    return RegistryObservation(
        name, url, found=True, latest_version=latest, manifest_version_published=published
    )
