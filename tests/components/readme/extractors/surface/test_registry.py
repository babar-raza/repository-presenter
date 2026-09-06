"""The registry façade observes, and says plainly when it did not."""

from __future__ import annotations

import json
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.surface.registry import (
    REGISTRY_TYPES,
    RegistryObservation,
    observe,
    registry_type,
)


class _Response:
    """What the vendored probe expects a fetch to return."""

    def __init__(self, status: int, payload: dict[str, Any] | None = None) -> None:
        self.status = status
        self.status_code = status
        self.text = json.dumps(payload or {})
        self.body = self.text
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def test_every_ecosystem_the_portfolio_uses_names_its_registry() -> None:
    """Section 29.12: one probe, every registry - and C++ honestly has none."""
    assert registry_type("python") == "pypi" and registry_type("net") == "nuget"
    assert registry_type("java") == "maven" and registry_type("rust") == "cargo"
    assert registry_type("cpp") == "", "C++ has no package registry; the façade must not invent one"
    assert set(REGISTRY_TYPES) == {"python", "net", "java", "typescript", "go", "rust"}


def test_an_offline_probe_is_inconclusive_rather_than_negative() -> None:
    """ "We could not check" is not "we checked and it is false" (section 29.6 E5).

    A caller that took an offline reading as CONTRADICTED would write a disposition saying the
    package is unpublished, on no evidence at all.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a probe reached the network while offline")

    reading = observe("net", "Aspose.Widget", fetch=refuse, offline=True)
    assert reading.published is None and reading.ambiguous is True
    assert not reading.conclusive
    assert "offline" in reading.source


def test_an_ecosystem_without_a_registry_never_reaches_the_network() -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("C++ has no registry to reach")

    reading = observe("cpp", "aspose-widget", fetch=refuse)
    assert reading.registry == "" and not reading.conclusive


def test_a_published_package_reads_as_published_through_an_injected_fetch() -> None:
    """No test touches a real registry; the fetch is the seam the façade exposes."""
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(200, {"id": "Aspose.Widget", "versions": ["1.0.0"]})

    reading = observe("net", "Aspose.Widget", fetch=fetch)
    assert calls and "nuget" in calls[0].lower()
    assert reading.registry == "nuget" and reading.name == "Aspose.Widget"
    assert reading.published is not None


@pytest.mark.parametrize("status", [404, 500])
def test_a_registry_that_answers_nothing_useful_stays_inconclusive_or_unpublished(
    status: int,
) -> None:
    """A 404 may mean unpublished; a 500 means we do not know. Neither may be silently the other."""

    def fetch(url: str, **kwargs: Any) -> _Response:
        return _Response(status)

    reading = observe("net", "Aspose.Widget", fetch=fetch)
    assert reading.published is not True
    if status == 500:
        assert not reading.conclusive


def test_the_reading_summarises_itself_in_the_vocabulary_a_check_expects() -> None:
    """BC-02 asks an install command to show a manifest reading and a package-registry reading.

    Measured 2026-09-06: the .NET install fact said "published on nuget" and BC-02 failed
    Aspose.3D for .NET outright at EXTRACTING. The phrase belongs to the shared reading, so no
    plugin has to remember it.
    """
    found = RegistryObservation("nuget", "Aspose.3D.FOSS", True, False, "https://x", "api", "s")
    missing = RegistryObservation("nuget", "Aspose.Slides.FOSS", False, False, None, "api", "s")
    unread = RegistryObservation("nuget", "x", None, False, None, None, "s")
    ambiguous = RegistryObservation("nuget", "x", True, True, None, "api", "s")

    assert found.summary == "package registry: found on nuget"
    assert missing.summary == "package registry: distribution not found on nuget"
    assert unread.summary == "package registry: nuget could not be read"
    assert ambiguous.summary == "package registry: nuget answered ambiguously"
    # The registry's current version is never in the evidence: it is the registry's state.
    assert all("version" not in o.summary for o in (found, missing, unread, ambiguous))
