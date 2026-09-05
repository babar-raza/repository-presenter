"""Observe the package registry: is the distribution the manifest names really on PyPI?

The install command a README shows is a claim about the registry, not about the tree, so the
claim is checked against PyPI's JSON API (one bounded read, retried only on transient failures)
and recorded as an observation: found or not, the latest version, and whether the manifest's
version is published. A registry that cannot be reached leaves the claim unresolved.

The latest version is what the registry happens to hold today, so it travels in the probe record
(`core/probes.py`) and never in the fact's evidence, which is hashed: a release published upstream
must not reopen a stage for a repository that did not change (section 27.2 RC7).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from repository_presenter.core.probes import ProbeRecord
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
    status: int | None = None
    elapsed_ms: int | None = None

    @property
    def summary(self) -> str:
        """What the fact's evidence records: stable while the repository is unchanged.

        The latest version is deliberately absent - it is the registry's state, not the
        repository's, and it is hashed into dependencies.json (section 27.2 RC7). ``probe``
        carries it.
        """
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
        return f"package registry: found; {published}"

    @property
    def probe(self) -> ProbeRecord:
        """The same read, with what the evidence does not carry: status, timing, and the
        volatile latest version."""
        outcome = (
            "UNREACHABLE" if self.error is not None else "FOUND" if self.found else "NOT_FOUND"
        )
        observation = f"latest {self.latest_version}" if self.latest_version else self.error or None
        return ProbeRecord(
            "package_registry",
            self.url,
            outcome,
            status=self.status,
            elapsed_ms=self.elapsed_ms,
            observation=observation,
        )


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

    started = time.monotonic()

    def since_start() -> int:
        return int((time.monotonic() - started) * 1000)

    try:
        response = run_with_retry("package_registry", attempt, sleep=sleep or time.sleep)
    except RetryableOperationError as exc:
        return RegistryObservation(name, url, found=False, error=str(exc), elapsed_ms=since_start())
    elapsed = since_start()
    if response.status_code == 404:
        return RegistryObservation(name, url, found=False, status=404, elapsed_ms=elapsed)
    if response.status_code != 200:
        return RegistryObservation(
            name,
            url,
            found=False,
            error=f"HTTP {response.status_code}",
            status=response.status_code,
            elapsed_ms=elapsed,
        )
    try:
        payload: Any = response.json()
        latest = str(payload["info"]["version"])
        releases = payload.get("releases") or {}
    except (ValueError, KeyError, TypeError) as exc:
        return RegistryObservation(
            name,
            url,
            found=False,
            error=f"malformed registry response: {exc}",
            status=200,
            elapsed_ms=elapsed,
        )
    published = None if manifest_version is None else manifest_version in releases
    return RegistryObservation(
        name,
        url,
        found=True,
        latest_version=latest,
        manifest_version_published=published,
        status=200,
        elapsed_ms=elapsed,
    )
