"""Register the package-registry observers for every ecosystem that has one besides Python.

`components/issues/redetect.py` replays a registry read by ecosystem name through
`core/package_registry.py` and never imports an extractor (`RESEARCH_AND_GUIDELINES.md` section
7.4). Python's observer lives in `python_registry.py`; this module registers the remaining
registries - NuGet, npm, Maven Central, crates.io, the Go proxy - by wrapping the one typed probe
fact extraction already uses (`surface/registry.py::observe`, the vendored publication probe), so
there is a single registry client with one set of URL templates, quirks and retry policy rather than
a second one for re-detection.

`platforms/registry.py::known_ecosystems()` imports every module beside it, so importing this one
is a side effect of the same call that registers Python's observer; adding an ecosystem's registry
is a row in `REGISTRY_TYPES`, not an edit here.

An inconclusive reading (the registry unreachable, an unexpected status, an ambiguous body) becomes
an observation with ``error`` set, never ``found=False``: "we could not check" must not read as "the
package is missing" (`RESEARCH_AND_GUIDELINES.md` section 29.6 E5).
"""

from __future__ import annotations

from collections.abc import Callable

from repository_presenter.components.readme.extractors.surface.registry import (
    REGISTRY_TYPES,
    Fetch,
    Sleep,
    observe,
)
from repository_presenter.core.package_registry import (
    RegistryObservation,
    RegistryObserver,
    register_observer,
)

PYTHON = "python"  # registered by python_registry.py with its richer PyPI JSON read


def make_observer(
    ecosystem: str, *, fetch: Fetch | None = None, sleep: Sleep | None = None
) -> RegistryObserver:
    """``ecosystem``'s observer: ``(name, manifest_version) -> RegistryObservation``.

    ``fetch`` and ``sleep`` exist so a test supplies the registry's answers without a network or a
    backoff wait. ``manifest_version`` is accepted for the interface and unused: the shared probe
    answers "is this distribution published", which is all a re-detection asks.
    """

    def observer(name: str, manifest_version: str | None) -> RegistryObservation:
        reading = observe(ecosystem, name, fetch=fetch, sleep=sleep)
        url = reading.evidence_url or ""
        if not reading.conclusive:
            return RegistryObservation(name, url, found=False, error=reading.summary)
        return RegistryObservation(name, url, found=bool(reading.published))

    return observer


def register_all(register: Callable[[str, RegistryObserver], None] = register_observer) -> None:
    for ecosystem in REGISTRY_TYPES:
        if ecosystem != PYTHON:
            register(ecosystem, make_observer(ecosystem))


register_all()
