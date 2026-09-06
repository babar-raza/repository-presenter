"""The typed way in to the vendored publication probe: is this package on its registry?

`RESEARCH_AND_GUIDELINES.md` §29.12 and §29.6 E3. One probe serves every registry the portfolio
uses — PyPI, NuGet, npm, crates.io, the Go proxy, Maven Central — with the URL templates and the
per-registry quirks the legacy learned (Maven through `repo1.maven.org`, never `search.maven.org`;
crates.io needs a named User-Agent; C++ has no registry at all).

Two rules the caller can rely on. The reading is *observed*, never assumed: a probe that could not
reach the registry says so, and the caller writes `UNRESOLVED` rather than `CONTRADICTED` - "we
could not check" is not "we checked and it is false" (§29.6 E5). And the observation is volatile,
so it belongs in a probe record, never in a fact's value (§27.2 RC7).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction import (
    publication_probe,
)

Fetch = Callable[..., Any]
# What the vendored probe calls each registry, keyed by this repository's ecosystem name.
REGISTRY_TYPES: dict[str, str] = {
    "python": "pypi",
    "net": "nuget",
    "java": "maven",
    "typescript": "npm",
    "go": "go_modules",
    "rust": "cargo",
}


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


def observe(
    ecosystem: str,
    package_name: str,
    *,
    repository_url: str | None = None,
    fetch: Fetch | None = None,
    offline: bool = False,
) -> RegistryObservation:
    """Ask the registry whether ``package_name`` is published, or say plainly that we did not.

    ``offline`` and an unknown registry both return an inconclusive reading rather than a
    negative one, which is the difference between a disposition that is honest and one that is
    wrong.
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
    result: dict[str, Any] = publication_probe.probe_publication(
        {"registry_type": kind, "candidate": candidate},
        repo_url=repository_url,
        fetch=fetch,
        offline=offline or not kind,
    )
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
