"""The package-registry lookup: ecosystems register observers, callers ask by name."""

from __future__ import annotations

import pytest

from repository_presenter.core import package_registry
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.package_registry import (
    RegistryObservation,
    install_verdict,
    observe_distribution,
    points_at_repository,
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


# TC-EXT-01 (G3-W08 cut 2): registry presence is not ownership.
@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/Owner/Name",
        "https://www.github.com/owner/name/tree/main/pkg#readme",
        "git+https://github.com/owner/name.git",
        "git+ssh://git@github.com/owner/name.git",
        "git@github.com:owner/name.git",
        "github.com/owner/name/v2",
    ],
)
def test_every_spelling_of_the_repository_url_corroborates(url: str) -> None:
    assert points_at_repository([url], "owner/name") is True


def test_another_repository_or_a_vendor_site_does_not_corroborate() -> None:
    assert points_at_repository(["https://github.com/owner/name-other"], "owner/name") is False
    assert points_at_repository(["https://products.aspose.com/page/"], "owner/name") is False
    assert points_at_repository(["https://github.com/other/name"], "owner/name") is False
    # Neither is a registry that lists nothing a mismatch: it is no corroboration either way.
    assert points_at_repository([], "owner/name") is None
    assert points_at_repository(["", ""], "owner/name") is None


def test_only_a_corroborated_published_distribution_supports_an_install_claim() -> None:
    def verdict(**kw: object) -> tuple[str, float]:
        base: dict[str, object] = {
            "conclusive": True,
            "published": True,
            "repository_matched": True,
            "summary": "s",
        }
        polarity, confidence, _ = install_verdict(**{**base, **kw})  # type: ignore[arg-type]
        return polarity, confidence

    assert verdict() == ("SUPPORTED", 1.0)
    assert verdict(repository_matched=False) == ("UNRESOLVED", 0.5)
    assert verdict(repository_matched=None) == ("UNRESOLVED", 0.5)
    assert verdict(published=False, repository_matched=None) == ("CONTRADICTED", 1.0)
    assert verdict(conclusive=False, published=None) == ("UNRESOLVED", 0.5)
