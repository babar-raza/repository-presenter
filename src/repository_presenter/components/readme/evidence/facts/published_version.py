"""The version the package registry lists as the package's current stable release.

A README states a version a reader can install ("`org.aspose:aspose-slides-foss` version 26.8.0").
The manifest says what the repository declares; only the registry says what a reader can actually
fetch, and the two differ whenever the repository is ahead of its last release or behind a later
one. `package:published_version` carries the registry's reading so BC-14 can hold a version
statement to it (`validation/claims.py`).

Rules the fact keeps:

- It exists only when the registry answered conclusively that the distribution is published and
  named a stable release. An unreachable registry, an ambiguous answer, a 404, an ecosystem with
  no registry (C++), or a body that lists only pre-releases yields no fact at all: a version is
  never guessed, and BC-14 judges nothing it has no fact for.
- Its evidence is a fixed sentence plus the registry URL - no timestamp, no HTTP status, no
  duration. The value is the registry's own state (a release published upstream changes it
  without the repository changing); the status and timing of the read stay in the probe record
  (`core/probes.py`, section 27.2 RC7).
- It is a ``package`` fact like ``package:version``, so it needs no new fact kind, schema change,
  or renderer registration, and no section renders it: only version statements are held to it.
"""

from __future__ import annotations

from repository_presenter.components.readme.extractors.surface.registry import (
    RegistryObservation,
    observe,
)
from repository_presenter.core.facts import Evidence, Fact, fact_id
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID
from repository_presenter.core.registry.models import RegistryEntry

PACKAGE_NAME_FACT_ID = fact_id("package", "name")

# Resolved at call time through this module attribute so a test injects its own reading and the
# suite never reaches a registry (tests/conftest.py replaces it with an inconclusive one).
_observe = observe


def published_version_fact(entry: RegistryEntry, package_name: Fact | None) -> Fact | None:
    """``package:published_version`` for ``entry``'s package, or None when nothing conclusive."""
    if package_name is None or package_name.polarity != "SUPPORTED":
        return None
    reading: RegistryObservation = _observe(entry.ecosystem, package_name.value)
    if not reading.conclusive or not reading.published or not reading.latest_version:
        return None
    return Fact(
        PUBLISHED_VERSION_FACT_ID,
        "package",
        reading.latest_version,
        (
            Evidence(
                reading.evidence_url or reading.registry,
                f"current stable release the {reading.registry} registry lists for the package; "
                "the registry's state, not the repository's",
            ),
        ),
        attributes={"registry": reading.registry},
    )
