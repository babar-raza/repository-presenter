"""What a package registry said about one distribution, and the lookup that asks for it.

Re-checking an upstream defect (`components/issues/redetect.py`) must replay a registry read, but a
stage after facts never imports an extractor (`RESEARCH_AND_GUIDELINES.md` section 7.4,
`docs/REPOSITORY_LAYOUT.md` section 2.1). So the observation type and the lookup live here in
`core/`, the same shape as `core/ecosystems.py`: an ecosystem's own platform module registers its
observer as a side effect of being imported, and a caller asks by ecosystem name without knowing
which module answers. An ecosystem that registered none fails closed with `ConfigError`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Fact, Polarity
from repository_presenter.core.probes import ProbeRecord

# The fact that carries the registry's current stable release (evidence/facts/published_version.py
# emits it; validation/claims.py holds a README's version statements to it). Named here, in `core/`,
# because the validator that reads it must not import the extractor that emits it.
PUBLISHED_VERSION_FACT_ID = "package:published_version"

# A package fact id starting with this names a distribution a reader installs that is not the
# manifest's own `package:name` (a C++ library's NuGet package, whose manifest names only a CMake
# project). Emitted by a platform plugin, SUPPORTED only once a registry confirmed it is this
# repository's; validation/claims.py accepts an install command naming one.
DISTRIBUTION_FACT_PREFIX = "package:distribution"

# `owner/name` out of any GitHub spelling a registry stores: https, git+https, git+ssh, scp-style
# `git@github.com:owner/name.git`, a `/tree/main` or `#readme` tail, `www.`.
_GITHUB_REPOSITORY = re.compile(r"github\.com[/:]+([^/\s#?]+)/([^/\s#?]+)", re.IGNORECASE)


def points_at_repository(urls: Iterable[str], repository: str) -> bool | None:
    """Whether a registry's own project URLs name ``repository`` (``owner/name``).

    A registry holding a distribution of the manifest's name proves only that the NAME is taken,
    not that this repository published it: an unrelated project can own it (PyPI's
    ``aspose-page`` is a commercial product with no FOSS connection). Ownership needs the
    registry's own source or project URL to point back here. True when one does; False when the
    registry lists URLs and none does; None when it lists no URL at all, which is not a mismatch
    but is no corroboration either.
    """
    wanted = repository.strip().lower().removesuffix(".git")
    listed = [url for url in urls if url]
    if not listed:
        return None
    for url in listed:
        found = _GITHUB_REPOSITORY.search(url)
        if found and f"{found.group(1)}/{found.group(2).removesuffix('.git')}".lower() == wanted:
            return True
    return False


def install_verdict(
    *, conclusive: bool, published: bool | None, repository_matched: bool | None, summary: str
) -> tuple[Polarity, float, str]:
    """The polarity, confidence and evidence detail an install claim takes from a registry read.

    SUPPORTED needs the distribution published AND corroborated as this repository's own. A
    published distribution nobody corroborated stays UNRESOLVED - never SUPPORTED, and never
    CONTRADICTED either, because the registry did not say the claim is false. An unreadable
    registry is UNRESOLVED, an unpublished one CONTRADICTED.
    """
    if not conclusive or published is None:
        return "UNRESOLVED", 0.5, summary
    if not published:
        return "CONTRADICTED", 1.0, summary
    if repository_matched is True:
        return "SUPPORTED", 1.0, summary
    return (
        "UNRESOLVED",
        0.5,
        "package registry: a distribution of this name exists, but "
        + ownership_clause(repository_matched),
    )


def ownership_clause(repository_matched: bool | None) -> str:
    """Why a found distribution is not claimed as this repository's, for an install fact."""
    if repository_matched is False:
        return "ownership not confirmed: the registry's project URLs point at another repository"
    return (
        "ownership not confirmed: the registry lists no source repository to compare with this one"
    )


# What one registry reading means for an install claim. The classes are not interchangeable and a
# consumer must not collapse them: ``not_published`` is the registry's own answer ("we looked and
# it is not there") and may be stated plainly; ``unreadable`` and ``ambiguous`` are the absence of
# an answer (a transport or TLS failure, a 5xx that outlasted the retry policy, an unexpected
# status) and say nothing about the package, so the only honest response is to read again - a
# README must never tell a reader a package is unpublished because the network was down;
# ``ownership_unconfirmed`` is a name some project holds that nothing ties to this repository;
# ``no_registry`` is an ecosystem with no registry to ask (C++).
RegistryReading = Literal[
    "published", "not_published", "unreadable", "ambiguous", "ownership_unconfirmed", "no_registry"
]
# The classes that mean "ask again", not "the package is absent" (wave 6, JMAP-Go: an empty
# version list was filed under the first of these and failed BC-02 as an unreadable registry).
RETRYABLE_READINGS: frozenset[RegistryReading] = frozenset({"unreadable", "ambiguous"})


def registry_reading(detail: str | None) -> RegistryReading | None:
    """The class of one registry evidence detail, or None when it is not a registry reading.

    The details are the shared vocabulary both observation types write (``RegistryObservation.
    summary`` here and in ``extractors/surface/registry.py``, ``install_verdict``'s ownership
    sentence), so classifying the text classifies the reading without a plugin having to carry a
    second field. Order matters: an ownership sentence also contains "a distribution", and the
    registry-less sentence also contains "could not be read".
    """
    text = (detail or "").lower()
    if "ownership not confirmed" in text:
        return "ownership_unconfirmed"
    if "package registry: none could not be read" in text:
        return "no_registry"
    if "could not be read" in text or "package registry unreachable" in text:
        return "unreadable"
    if "answered ambiguously" in text:
        return "ambiguous"
    if "distribution not found" in text:
        return "not_published"
    if "package registry: found" in text:
        return "published"
    return None


def fact_registry_reading(fact: Fact) -> RegistryReading | None:
    """The registry reading an install fact's evidence records: the last evidence line that is
    one (the registry is asked after the manifest, so its line is last)."""
    for evidence in reversed(fact.evidence):
        reading = registry_reading(evidence.detail)
        if reading is not None:
            return reading
    return None


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
    # The registry's own project and source URLs, and whether one names the repository the
    # caller asked about (None: no repository was given, or the registry lists no URL).
    project_urls: tuple[str, ...] = ()
    repository_matched: bool | None = None

    @property
    def owned(self) -> bool:
        """Whether a found distribution is corroborated as this repository's own."""
        return self.found and self.repository_matched is True

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


# (name, manifest_version) -> the registry's reading; never raises for an unreachable registry.
RegistryObserver = Callable[[str, str | None], RegistryObservation]

OBSERVERS: dict[str, RegistryObserver] = {}


def register_observer(ecosystem: str, observer: RegistryObserver) -> None:
    """Register ``ecosystem``'s registry observer; the first registration stands."""
    OBSERVERS.setdefault(ecosystem, observer)


def observe_distribution(
    ecosystem: str, name: str, manifest_version: str | None = None
) -> RegistryObservation:
    """``ecosystem``'s registry reading of ``name``; an ecosystem with no observer is a
    configuration failure, never a guessed answer."""
    observer = OBSERVERS.get(ecosystem)
    if observer is None:
        known = ", ".join(sorted(OBSERVERS)) or "none"
        raise ConfigError(
            f"no package-registry observer registered for ecosystem {ecosystem!r} "
            f"(registered: {known}); its platforms/<ecosystem>.py module registers one on import"
        )
    return observer(name, manifest_version)
