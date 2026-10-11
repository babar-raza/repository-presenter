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
from typing import Any

import httpx

from repository_presenter.components.readme.extractors.surface.registry import (
    TRANSIENT_STATUSES,
    ResolveUrl,
    match_repository,
)
from repository_presenter.core.package_registry import (
    RegistryObservation,
    register_observer,
)
from repository_presenter.core.retry import RetryableOperationError, run_with_retry

PYPI_PROJECT_URL = "https://pypi.org/pypi/{name}/json"
REQUEST_TIMEOUT_SECONDS = 15.0
USER_AGENT = "repository-presenter (+https://github.com/babar-raza/repository-presenter)"


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
    fetch: Callable[[str], httpx.Response] | None = None,
    sleep: Callable[[float], None] | None = None,
    repository: str | None = None,
    resolve_url: ResolveUrl | None = None,
) -> RegistryObservation:
    """Observe ``name`` on PyPI, retrying transient failures under the package_registry policy.

    ``repository`` (``owner/name``) asks the further question a found name does not answer: does
    the project's own ``project_urls`` / ``home_page`` point back at that repository? Only then is
    the distribution corroborated as the repository's own (``repository_matched``).

    ``fetch`` defaults to None and is resolved to this module's ``fetch_project_json`` at call time,
    never bound as a default argument: a test replaces that module attribute (tests/conftest.py),
    and a default bound at definition would keep the real function and reach the live registry.
    """
    url = PYPI_PROJECT_URL.format(name=name)

    def attempt() -> httpx.Response:
        try:
            response = (fetch or fetch_project_json)(url)
        except httpx.TransportError as exc:
            raise RetryableOperationError(f"{type(exc).__name__}: {exc}") from exc
        if response.status_code in TRANSIENT_STATUSES:
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
        info = payload["info"]
        urls = tuple(
            str(url)
            for url in (*(info.get("project_urls") or {}).values(), info.get("home_page"))
            if url
        )
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return RegistryObservation(
            name,
            url,
            found=False,
            error=f"malformed registry response: {exc}",
            status=200,
            elapsed_ms=elapsed,
        )
    published = None if manifest_version is None else manifest_version in releases
    matched = match_repository(urls, repository, resolve_url) if repository and urls else None
    return RegistryObservation(
        name,
        url,
        found=True,
        latest_version=latest,
        manifest_version_published=published,
        status=200,
        elapsed_ms=elapsed,
        project_urls=urls,
        repository_matched=matched,
    )


# `components/issues/redetect.py` asks for this read by ecosystem name through `core/`,
# never by importing this module (RESEARCH_AND_GUIDELINES.md section 7.4).
register_observer("python", observe_pypi)
