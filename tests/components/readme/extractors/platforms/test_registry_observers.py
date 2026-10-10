"""The non-Python registry observers: the shared probe, answered through core."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from repository_presenter.components.readme.extractors.platforms import (
    python_registry,
    registry_observers,
)
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems
from repository_presenter.components.readme.extractors.surface._vendor.aspose_extraction.package_registries import (  # noqa: E501
    FetchResponse,
)
from repository_presenter.components.readme.extractors.surface.registry import REGISTRY_TYPES
from repository_presenter.core import package_registry

Fetch = Callable[..., FetchResponse | None]


def answering(status: int | None, body: bytes = b"{}") -> tuple[Fetch, list[str]]:
    asked: list[str] = []

    def fetch(url: str, *args: object, **kwargs: object) -> FetchResponse | None:
        asked.append(url)
        return None if status is None else FetchResponse(status_code=status, body=body)

    return fetch, asked


# ecosystem, package name, the body a published package answers with, a url fragment of the read
CASES = [
    ("typescript", "@aspose/3d", b'{"maintainers": [{"name": "a"}]}', "registry.npmjs.org"),
    ("net", "Aspose.Imaging.Foss", b"{}", "api.nuget.org/v3-flatcontainer/aspose.imaging.foss"),
    ("java", "com.aspose:aspose-slides-foss", b"<metadata/>", "repo1.maven.org/maven2/com/aspose"),
    ("rust", "aspose-cells-foss", b'{"crate": {"id": "x"}}', "crates.io/api/v1/crates"),
    ("go", "example.com/mod", b"v1.0.0\n", "proxy.golang.org/example.com/mod/@v/list"),
]


@pytest.mark.parametrize(
    ("ecosystem", "name", "body", "fragment"), CASES, ids=[c[0] for c in CASES]
)
def test_a_published_package_is_found(
    ecosystem: str, name: str, body: bytes, fragment: str
) -> None:
    fetch, asked = answering(200, body)
    observation = registry_observers.make_observer(ecosystem, fetch=fetch, sleep=lambda _s: None)(
        name, None
    )
    assert observation.found is True and observation.error is None
    assert fragment in observation.url and any(fragment in url for url in asked)


@pytest.mark.parametrize(
    ("ecosystem", "name", "body", "fragment"), CASES, ids=[c[0] for c in CASES]
)
def test_a_404_is_the_registrys_answer_not_found(
    ecosystem: str, name: str, body: bytes, fragment: str
) -> None:
    fetch, _ = answering(404, b"")
    observation = registry_observers.make_observer(ecosystem, fetch=fetch, sleep=lambda _s: None)(
        name, None
    )
    assert observation.found is False and observation.error is None


@pytest.mark.parametrize(
    ("ecosystem", "name", "body", "fragment"), CASES, ids=[c[0] for c in CASES]
)
@pytest.mark.parametrize("status", [None, 500, 403])
def test_an_unanswered_registry_is_an_error_never_not_found(
    ecosystem: str, name: str, body: bytes, fragment: str, status: int | None
) -> None:
    """Negative control: 'we could not check' must not read as 'the package is missing'."""
    fetch, _ = answering(status, b"")
    observation = registry_observers.make_observer(ecosystem, fetch=fetch, sleep=lambda _s: None)(
        name, None
    )
    assert observation.found is False
    assert observation.error is not None and "package registry" in observation.error


def test_every_registry_but_pythons_is_registered_through_core() -> None:
    known_ecosystems()  # the call that imports every platform module, as the CLI does
    wanted = set(REGISTRY_TYPES) - {"python"}
    assert wanted <= set(package_registry.OBSERVERS)
    assert package_registry.OBSERVERS["python"] is python_registry.observe_pypi


def test_register_all_never_replaces_the_python_observer() -> None:
    seen: list[str] = []
    registry_observers.register_all(lambda ecosystem, observer: seen.append(ecosystem))
    assert "python" not in seen and set(seen) == set(REGISTRY_TYPES) - {"python"}
