"""Which package a handoff's registry URL names, for every registry the portfolio publishes to."""

from __future__ import annotations

import pytest

from repository_presenter.components.issues.model import EvidenceEntry
from repository_presenter.components.issues.registry_evidence import (
    RegistryIdentity,
    registry_identities,
    registry_identity,
)


@pytest.mark.parametrize(
    ("url", "ecosystem", "name"),
    [
        ("https://pypi.org/pypi/aspose-html-foss/json", "python", "aspose-html-foss"),
        ("https://pypi.org/pypi/aspose-html-foss/1.2.3/json", "python", "aspose-html-foss"),
        ("https://pypi.org/project/aspose-font/", "python", "aspose-font"),
        ("https://registry.npmjs.org/@aspose%2f3d", "typescript", "@aspose/3d"),
        ("https://registry.npmjs.org/@aspose%2F3d", "typescript", "@aspose/3d"),
        ("https://registry.npmjs.org/@asposefoss/pdf", "typescript", "@asposefoss/pdf"),
        ("https://registry.npmjs.org/left-pad", "typescript", "left-pad"),
        ("https://www.npmjs.com/package/@aspose/3d", "typescript", "@aspose/3d"),
        (
            "https://api.nuget.org/v3-flatcontainer/aspose.imaging.foss/index.json",
            "net",
            "aspose.imaging.foss",
        ),
        ("https://www.nuget.org/packages/Aspose.Imaging.Foss", "net", "aspose.imaging.foss"),
        ("https://www.nuget.org/packages/Aspose.Imaging.Foss/1.0.0", "net", "aspose.imaging.foss"),
        (
            "https://api.nuget.org/v3/registration5-gz-semver2/aspose.imaging.foss/index.json",
            "net",
            "aspose.imaging.foss",
        ),
        (
            "https://repo1.maven.org/maven2/com/aspose/aspose-slides-foss/maven-metadata.xml",
            "java",
            "com.aspose:aspose-slides-foss",
        ),
        (
            "https://central.sonatype.com/artifact/com.aspose/aspose-slides-foss/26.8.0",
            "java",
            "com.aspose:aspose-slides-foss",
        ),
        ("https://crates.io/api/v1/crates/aspose-cells-foss", "rust", "aspose-cells-foss"),
        ("https://crates.io/crates/aspose-cells-foss", "rust", "aspose-cells-foss"),
        (
            "https://proxy.golang.org/github.com/!aspose/cells/@v/list",
            "go",
            "github.com/Aspose/cells",
        ),
        ("https://proxy.golang.org/example.com/mod/@latest", "go", "example.com/mod"),
        ("https://pkg.go.dev/example.com/mod@v1.2.3", "go", "example.com/mod"),
    ],
)
def test_a_registry_url_names_its_package(url: str, ecosystem: str, name: str) -> None:
    assert registry_identity(url) == RegistryIdentity(ecosystem, name)


@pytest.mark.parametrize(
    "url",
    [
        "README.md",
        "docker run gcc:14 cmake --build",
        "http://pypi.org/pypi/x/json",  # not https
        "https://example.com/pypi/x/json",  # no registry owns the host
        "https://pypi.org/",  # a registry, but no package
        "https://registry.npmjs.org/-/v1/search?text=aspose",  # an API root, not a package
        "https://registry.npmjs.org/@scope-only",  # a scope names no package
        "https://repo1.maven.org/maven2/com/aspose/aspose-slides-foss/26.8.0/aspose.pom",
        "https://proxy.golang.org/@v/list",  # no module before the marker
    ],
)
def test_a_url_that_names_no_single_package_is_not_guessed(url: str) -> None:
    assert registry_identity(url) is None


def test_a_control_entry_names_no_defective_package() -> None:
    """The Imaging-.NET handoff records `aspose.imaging` as a control that must succeed."""
    evidence = (
        EvidenceEntry(
            "https://api.nuget.org/v3-flatcontainer/aspose.imaging.foss/index.json", "HTTP 404"
        ),
        EvidenceEntry("https://www.nuget.org/packages/Aspose.Imaging.Foss", "HTTP 404 (badge)"),
        EvidenceEntry(
            "https://api.nuget.org/v3-flatcontainer/aspose.imaging/index.json",
            "Control: HTTP 200, so the probe itself works",
        ),
    )
    assert registry_identities(evidence) == {RegistryIdentity("net", "aspose.imaging.foss")}


def test_two_registries_in_one_handoff_are_two_identities() -> None:
    evidence = (
        EvidenceEntry("https://pypi.org/pypi/a/json", "HTTP 404"),
        EvidenceEntry("https://registry.npmjs.org/b", "HTTP 404"),
    )
    assert len(registry_identities(evidence)) == 2


def test_evidence_without_a_registry_url_has_no_identity() -> None:
    assert registry_identities((EvidenceEntry("README.md", "line 4"),)) == frozenset()
