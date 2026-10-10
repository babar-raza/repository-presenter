"""What a package registry said about one distribution, and the lookup that asks for it.

Re-checking an upstream defect (`components/issues/redetect.py`) must replay a registry read, but a
stage after facts never imports an extractor (`RESEARCH_AND_GUIDELINES.md` section 7.4,
`docs/REPOSITORY_LAYOUT.md` section 2.1). So the observation type and the lookup live here in
`core/`, the same shape as `core/ecosystems.py`: an ecosystem's own platform module registers its
observer as a side effect of being imported, and a caller asks by ecosystem name without knowing
which module answers. An ecosystem that registered none fails closed with `ConfigError`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from repository_presenter.core.errors import ConfigError
from repository_presenter.core.probes import ProbeRecord


# The fact that carries the registry's current stable release (evidence/facts/published_version.py
# emits it; validation/claims.py holds a README's version statements to it). Named here, in `core/`,
# because the validator that reads it must not import the extractor that emits it.
PUBLISHED_VERSION_FACT_ID = "package:published_version"


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
