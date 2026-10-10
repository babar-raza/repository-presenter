"""TC-CLM-01: `observe` reads the registry's current stable release from the body its own probe
fetched - no second request, no guess, and no version when the body does not say one."""

from __future__ import annotations

import json
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.surface.registry import observe


class _Response:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status_code = status
        self.body = body


def _serving(routes: dict[str, bytes]) -> tuple[list[str], Any]:
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        body = routes.get(url)
        return _Response(404) if body is None else _Response(200, body)

    return calls, fetch


def _json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode()


MAVEN_URL = "https://repo1.maven.org/maven2/org/aspose/aspose-slides-foss/maven-metadata.xml"
MAVEN_XML = (
    b"<metadata><versioning><latest>26.7.0</latest><release>26.7.0</release>"
    b"<versions><version>26.6.0</version><version>26.7.0</version></versions></versioning>"
    b"</metadata>"
)


@pytest.mark.parametrize(
    ("ecosystem", "name", "routes", "expected"),
    [
        (
            "java",
            "org.aspose:aspose-slides-foss",
            {MAVEN_URL: MAVEN_XML},
            "26.7.0",
        ),
        (
            "net",
            "Aspose.PDF.FOSS",
            {
                "https://api.nuget.org/v3-flatcontainer/aspose.pdf.foss/index.json": _json(
                    {"versions": ["26.9.0", "26.10.0", "26.11.0-rc1", "26.2.0"]}
                )
            },
            "26.10.0",
        ),
        (
            "typescript",
            "@asposefoss/pdf",
            {
                "https://registry.npmjs.org/%40asposefoss%2Fpdf": _json(
                    {"dist-tags": {"latest": "26.9.0", "next": "27.0.0-rc.1"}}
                )
            },
            "26.9.0",
        ),
        (
            "rust",
            "aspose-cells-foss",
            {
                "https://crates.io/api/v1/crates/aspose-cells-foss": _json(
                    {"crate": {"max_stable_version": "26.7.0", "max_version": "26.8.0-rc1"}}
                )
            },
            "26.7.0",
        ),
        (
            "python",
            "aspose-note-foss",
            {
                "https://pypi.org/pypi/aspose-note-foss/json": _json(
                    {"info": {"version": "26.1.0"}, "releases": {"26.1.0": []}, "urls": []}
                )
            },
            "26.1.0",
        ),
    ],
)
def test_each_registry_names_its_current_release_from_the_body_the_probe_read(
    ecosystem: str, name: str, routes: dict[str, bytes], expected: str
) -> None:
    calls, fetch = _serving(routes)
    reading = observe(ecosystem, name, fetch=fetch, sleep=lambda _s: None)
    assert reading.conclusive and reading.published
    assert reading.latest_version == expected
    # Nothing was asked of the registry beyond what the publication probe itself reads
    # (PyPI's details read is the probe's own second request).
    assert set(calls) <= set(routes) | {
        "https://api.nuget.org/v3/registration5-semver1/aspose.pdf.foss/index.json"
    }


def test_the_go_proxy_list_yields_its_highest_plain_release() -> None:
    module = "github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go/v26"
    url = (
        "https://proxy.golang.org/github.com/aspose-widget-foss/!aspose.!widget-!f!o!s!s-for-!go/"
        "v26/@v/list"
    )
    _, fetch = _serving({url: b"v26.7.0\nv26.10.1\nv26.9.0\nv27.0.0-rc1\n"})
    reading = observe("go", module, fetch=fetch, sleep=lambda _s: None)
    assert reading.latest_version == "v26.10.1"


def test_a_prerelease_only_registry_yields_no_version() -> None:
    _, fetch = _serving(
        {
            MAVEN_URL: b"<metadata><versioning><release>1.0.0-rc1</release>"
            b"<versions><version>1.0.0-rc1</version></versions></versioning></metadata>"
        }
    )
    reading = observe("java", "org.aspose:aspose-slides-foss", fetch=fetch, sleep=lambda _s: None)
    assert reading.published and reading.latest_version is None


def test_a_malformed_body_yields_no_version_never_a_guess() -> None:
    _, fetch = _serving({"https://registry.npmjs.org/aspose-x": b"<html>not json</html>"})
    reading = observe("typescript", "aspose-x", fetch=fetch, sleep=lambda _s: None)
    assert reading.latest_version is None


def test_an_unpublished_or_offline_reading_carries_no_version() -> None:
    _, fetch = _serving({})
    gone = observe("typescript", "aspose-x", fetch=fetch, sleep=lambda _s: None)
    assert gone.published is False and gone.latest_version is None
    assert observe("typescript", "aspose-x", offline=True).latest_version is None
    assert observe("cpp", "aspose_cells_foss_cpp").latest_version is None
