"""The typed way in to the vendored publication probe: is this package on its registry?

`RESEARCH_AND_GUIDELINES.md` §29.12 and §29.6 E3. One probe serves every registry the portfolio
uses — PyPI, NuGet, npm, crates.io, the Go proxy, Maven Central — with the URL templates and the
per-registry quirks the legacy learned (Maven through `repo1.maven.org`, never `search.maven.org`;
crates.io needs a named User-Agent; C++ has no registry at all).

Two rules the caller can rely on. The reading is *observed*, never assumed: a probe that could not
reach the registry says so, and the caller writes `UNRESOLVED` rather than `CONTRADICTED` - "we
could not check" is not "we checked and it is false" (§29.6 E5). And the observation is volatile,
so it belongs in a probe record, never in a fact's value (§27.2 RC7).

A transient answer is asked again before it is called unreadable. `observe()` replays the probe
under `RETRY_POLICIES["package_registry"]` for every registry alike (G4-W17 arrival item 57: only
`python_registry.py` retried, and lane F measured 5 of 10 NuGet reads unreadable in one run, each
failing BC-02 at EXTRACTING for a package that is published); a registry that stays down still
yields the inconclusive reading, never an exception.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction import (
    package_registries,
    publication_probe,
)
from repository_presenter.core.retry import RETRY_POLICIES, RetryableOperationError, run_with_retry

Fetch = Callable[..., Any]
Sleep = Callable[[float], None]
# What the vendored probe calls each registry, keyed by this repository's ecosystem name.
REGISTRY_TYPES: dict[str, str] = {
    "python": "pypi",
    "net": "nuget",
    "java": "maven",
    "typescript": "npm",
    "go": "go_modules",
    "rust": "cargo",
}
# The answers that mean "ask again": rate limiting and the 5xx family. One classification for
# both registry paths - python_registry.py reads this set too - so they cannot drift apart. A 404
# is the registry's answer (not published) and a 403 or any other status is the adapter's own
# ambiguous reading; neither is replayed.
TRANSIENT_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_POLICY = RETRY_POLICIES["package_registry"]


@dataclass(frozen=True)
class RegistryObservation:
    """One reading of a registry, with the uncertainty kept rather than rounded away."""

    registry: str
    name: str
    published: bool | None
    ambiguous: bool
    evidence_url: str | None
    method: str | None
    source: str

    @property
    def conclusive(self) -> bool:
        """Whether a fact may take a polarity from this reading at all."""
        return self.published is not None and not self.ambiguous

    @property
    def summary(self) -> str:
        """What an install fact's evidence records about this reading.

        The wording is shared because BC-02 asks an install command to show a manifest reading
        and a package-registry reading, and no plugin should have to remember the phrase.
        Measured 2026-09-06: the .NET install fact said "published on nuget" and BC-02 failed
        Aspose.3D for .NET outright at EXTRACTING. The registry's current version never appears
        here - that is the registry's state, not the repository's (§27.2 RC7), and it belongs in
        the probe record.
        """
        if self.published is None:
            return f"package registry: {self.registry or 'none'} could not be read"
        if self.ambiguous:
            return f"package registry: {self.registry} answered ambiguously"
        found = "found" if self.published else "distribution not found"
        return f"package registry: {found} on {self.registry}"


def registry_type(ecosystem: str) -> str:
    """The probe's name for an ecosystem's registry, or an empty string when it has none."""
    return REGISTRY_TYPES.get(ecosystem, "")


class _RegistryReads:
    """One probe's reads, replayed while a transient answer still has attempts left.

    The vendored adapters never raise: a connection failure is ``None`` and a status they do not
    expect is an ambiguous ``CheckResult``, and both reach ``observe()`` as "could not be read".
    Here a transient answer becomes a :class:`RetryableOperationError` instead, so
    ``run_with_retry`` replays the whole probe under the ``package_registry`` policy. On the
    policy's last attempt the answer goes back to the adapter unchanged, so a registry that
    stays down yields exactly the inconclusive reading a single read always gave (§29.6 E5)
    rather than an exception the facts stage never expected.
    """

    def __init__(self, fetch: Fetch, max_attempts: int) -> None:
        self._fetch = fetch
        self._max_attempts = max_attempts
        self.attempt = 0

    def begin_attempt(self) -> None:
        self.attempt += 1

    def __call__(self, url: str, *args: Any, **kwargs: Any) -> Any:
        response = self._fetch(url, *args, **kwargs)
        if self.attempt >= self._max_attempts:
            return response
        if response is None:
            raise RetryableOperationError(f"no response from {url}")
        status = getattr(response, "status_code", None)
        if status in TRANSIENT_STATUSES:
            raise RetryableOperationError(f"HTTP {status} from {url}")
        return response


def observe(
    ecosystem: str,
    package_name: str,
    *,
    repository_url: str | None = None,
    fetch: Fetch | None = None,
    offline: bool = False,
    sleep: Sleep | None = None,
) -> RegistryObservation:
    """Ask the registry whether ``package_name`` is published, or say plainly that we did not.

    ``offline`` and an unknown registry both return an inconclusive reading rather than a
    negative one, which is the difference between a disposition that is honest and one that is
    wrong.

    A transient answer - no response, 429, or a 5xx - is asked again under
    ``RETRY_POLICIES["package_registry"]``, for every ecosystem alike (G4-W17 arrival item 57);
    a 404 and a non-transient status are the registry's answer and are never asked again.
    ``sleep`` exists so a test measures the replays without waiting on the policy's backoff.
    """
    kind = registry_type(ecosystem)
    # The vendored adapters key their own coordinate differently per registry: the Go adapter
    # reads candidate["module_path"] (package_registries/go.py), and the Maven check reads
    # candidate["group_id"]/["artifact_id"] rather than a single name (publication_probe.py's
    # _maven_check) - name alone, which every other registry takes, leaves both UNRESOLVED
    # rather than probed. Java's package:name fact is already the "group:artifact" coordinate
    # a reader writes, so splitting it costs no plugin a fact of its own.
    candidate: dict[str, Any] = {"name": package_name}
    if kind == "go_modules":
        candidate["module_path"] = package_name
    elif kind == "maven" and ":" in package_name:
        candidate["group_id"], candidate["artifact_id"] = package_name.split(":", 1)
    install_info: dict[str, Any] = {"registry_type": kind, "candidate": candidate}
    result: dict[str, Any]
    if offline or not kind:
        result = publication_probe.probe_publication(
            install_info, repo_url=repository_url, fetch=fetch, offline=True
        )
    else:
        reads = _RegistryReads(fetch or package_registries.default_fetch, _POLICY.max_attempts)

        def attempt() -> dict[str, Any]:
            reads.begin_attempt()
            probed: dict[str, Any] = publication_probe.probe_publication(
                install_info, repo_url=repository_url, fetch=reads
            )
            return probed

        result = run_with_retry("package_registry", attempt, sleep=sleep or time.sleep)
    live = result.get("live") or {}
    return RegistryObservation(
        registry=kind,
        name=package_name,
        published=live.get("published"),
        ambiguous=bool(live.get("ambiguous", True)),
        evidence_url=live.get("evidence_url"),
        method=live.get("method"),
        source=str(result.get("source", "")),
    )
