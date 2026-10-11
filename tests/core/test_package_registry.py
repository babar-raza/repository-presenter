"""The package-registry lookup: ecosystems register observers, callers ask by name."""

from __future__ import annotations

import pytest

from repository_presenter.core import package_registry
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Evidence, Fact
from repository_presenter.core.package_registry import (
    RETRYABLE_READINGS,
    RegistryObservation,
    fact_registry_reading,
    install_verdict,
    observe_distribution,
    ownership_clause,
    points_at_repository,
    register_observer,
    registry_reading,
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


# --- the class of a registry reading (BC-02, wave 6) ---------------------------------------------
# The details are the ones the wave-6 reseal recorded on the install facts of the eleven BC-02 rows.


@pytest.mark.parametrize(
    ("detail", "reading"),
    [
        ("package registry: distribution not found on maven", "not_published"),  # JMAP-Java
        ("package registry: distribution not found on cargo", "not_published"),  # JMAP-Rust
        ("package registry: distribution not found", "not_published"),  # JMAP-Python (core read)
        ("package registry: distribution not found on nuget", "not_published"),  # GIS
        ("package registry: go_modules could not be read", "unreadable"),  # JMAP-Go as recorded
        ("package registry unreachable: ConnectError", "unreadable"),  # core observation, outage
        ("package registry: nuget answered ambiguously", "ambiguous"),
        ("package registry: none could not be read", "no_registry"),  # JMAP-Cpp: C++ has none
        ("package registry: found on pypi", "published"),
        ("package registry: found; manifest version published", "published"),
        (
            "package registry: a distribution of this name exists, but " + ownership_clause(False),
            "ownership_unconfirmed",
        ),  # 3D-Python
        (
            "package registry: a distribution of this name exists, but " + ownership_clause(None),
            "ownership_unconfirmed",
        ),  # Page-Python
        ("install command for the coordinate the `pom.xml` manifest declares", None),
        ("source build for the CMake project; C++ has no package registry to install from", None),
        ("", None),
        (None, None),
    ],
)
def test_a_registry_detail_is_classified_by_what_the_registry_did_say(
    detail: str | None, reading: str | None
) -> None:
    assert registry_reading(detail) == reading


def test_only_an_unanswered_read_is_a_retry_and_an_absent_package_is_not() -> None:
    assert {"unreadable", "ambiguous"} == RETRYABLE_READINGS
    assert "not_published" not in RETRYABLE_READINGS
    assert "ownership_unconfirmed" not in RETRYABLE_READINGS


def test_an_install_facts_reading_is_its_last_registry_line() -> None:
    fact = Fact(
        "install_command:cargo",
        "install_command",
        "cargo add aspose-jmap-foss",
        (
            Evidence("Cargo.toml", "install command for the crate name the manifest declares"),
            Evidence("https://crates.io/x", "package registry: distribution not found on cargo"),
        ),
        polarity="CONTRADICTED",
    )
    assert fact_registry_reading(fact) == "not_published"
    manifest_only = Fact(
        "install_command:cargo", "install_command", "cargo add x", (Evidence("Cargo.toml", "m"),)
    )
    assert fact_registry_reading(manifest_only) is None
