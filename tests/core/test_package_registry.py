"""The package-registry lookup: ecosystems register observers, callers ask by name."""

from __future__ import annotations

import pytest

from repository_presenter.core import package_registry
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.package_registry import (
    RegistryObservation,
    observe_distribution,
    register_observer,
)


def _observer(found: bool) -> package_registry.RegistryObserver:
    def observe(name: str, version: str | None) -> RegistryObservation:
        return RegistryObservation(name, f"https://registry.example/{name}", found=found)

    return observe


def test_python_registers_its_observer_when_its_module_is_imported() -> None:
    from repository_presenter.components.readme.extractors.platforms import python_registry

    assert package_registry.OBSERVERS["python"] is python_registry.observe_pypi


def test_an_unregistered_ecosystem_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(package_registry, "OBSERVERS", {})
    with pytest.raises(
        ConfigError, match="no package-registry observer registered for ecosystem 'go'"
    ):
        observe_distribution("go", "example.com/mod")


def test_the_first_registration_stands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(package_registry, "OBSERVERS", {})
    register_observer("demo", _observer(True))
    register_observer("demo", _observer(False))
    assert observe_distribution("demo", "pkg").found is True


def test_the_observation_summary_and_probe_keep_their_meaning() -> None:
    missing = RegistryObservation("p", "https://r/p", found=False, status=404)
    assert missing.summary == "package registry: distribution not found"
    assert missing.probe.outcome == "NOT_FOUND"
    unreachable = RegistryObservation("p", "https://r/p", found=False, error="HTTP 500")
    assert unreachable.summary == "package registry unreachable: HTTP 500"
    assert unreachable.probe.outcome == "UNREACHABLE"
