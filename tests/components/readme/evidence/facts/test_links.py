"""Link targets: extracted once each, resolved by kind, never assumed."""

from __future__ import annotations

import httpx

from repository_presenter.components.readme.evidence.facts.links import (
    check_anchor,
    check_external,
    check_relative,
    extract_links,
    fetch_status,
    heading_slug,
    heading_slugs,
    link_facts,
)

README = """# Aspose.3D FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)](https://pypi.org/project/aspose-3d-foss/)

See the [Quick start](#quick-start), the [license](LICENSE), and [docs](docs/releasing.md#steps).
Contact <mailto:support@example.com> or visit <https://example.com/> again: [x](https://example.com/).

## Quick start

![diagram](docs/diagram.png) and [broken](#nowhere) and [gone](missing/file.md).
"""


def test_links_are_extracted_once_each_in_order_with_kind_line_and_text() -> None:
    links = extract_links(README)
    assert [(link.ordinal, link.href, link.kind, link.line) for link in links] == [
        (1, "https://img.shields.io/pypi/v/aspose-3d-foss.svg", "external", 3),
        (2, "https://pypi.org/project/aspose-3d-foss/", "external", 3),
        (3, "#quick-start", "anchor", 5),
        (4, "LICENSE", "relative", 5),
        (5, "docs/releasing.md#steps", "relative", 5),
        (6, "mailto:support@example.com", "mailto", 5),
        (7, "https://example.com/", "external", 5),
        (8, "docs/diagram.png", "relative", 10),
        (9, "#nowhere", "anchor", 10),
        (10, "missing/file.md", "relative", 10),
    ]
    assert links[1].text == "PyPI"
    assert links[3].text == "license"
    assert extract_links("") == []


def test_heading_slugs_follow_the_github_form() -> None:
    assert heading_slug("Quick start") == "quick-start"
    assert heading_slug("Scene graph (`aspose.threed`)") == "scene-graph-asposethreed"
    assert heading_slug("Documentation & resources") == "documentation--resources"
    assert heading_slugs(README) == {"aspose3d-foss-for-python", "quick-start"}
    assert check_anchor("#quick-start", heading_slugs(README)).outcome == "RESOLVED"
    assert check_anchor("#nowhere", heading_slugs(README)).outcome == "MISSING"


def test_relative_links_resolve_against_the_tree() -> None:
    tree = ["LICENSE", "docs/releasing.md", "docs/diagram.png", "src/pkg/__init__.py"]
    assert check_relative("LICENSE", tree).outcome == "RESOLVED"
    assert check_relative("./docs/releasing.md#steps", tree).outcome == "RESOLVED"
    assert check_relative("src/pkg/", tree).detail == "tree contains src/pkg"
    assert check_relative("src", tree).outcome == "RESOLVED"
    assert check_relative("missing/file.md", tree).outcome == "MISSING"
    assert check_relative("", tree).outcome == "MISSING"


def test_external_links_resolve_by_status_with_retry_and_redirects() -> None:
    responses = {"https://a/": [(200, "https://a/")], "https://r/": [(200, "https://final/")]}
    responses["https://gone/"] = [(404, "https://gone/")]
    responses["https://gated/"] = [(403, "https://gated/")]
    responses["https://flaky/"] = [(503, "https://flaky/"), (200, "https://flaky/")]
    responses["https://down/"] = [None, None]

    def fetch(url: str) -> tuple[int, str]:
        item = responses[url].pop(0)
        if item is None:
            raise httpx.ConnectError("down")
        return item

    sleeps: list[float] = []
    assert check_external("https://a/", fetch=fetch).detail == "HTTP 200"
    assert check_external("https://r/", fetch=fetch).detail == "HTTP 200 via https://final/"
    assert check_external("https://gone/", fetch=fetch).outcome == "MISSING"
    gated = check_external("https://gated/", fetch=fetch)
    assert (gated.outcome, gated.detail) == ("UNCHECKED", "HTTP 403 (access-gated)")
    flaky = check_external("https://flaky/", fetch=fetch, sleep=sleeps.append)
    assert flaky.outcome == "RESOLVED" and len(sleeps) == 1
    down = check_external("https://down/", fetch=fetch, sleep=sleeps.append)
    assert down.outcome == "UNCHECKED" and down.detail.startswith("unreachable: ConnectError")


def test_link_facts_carry_both_the_readme_location_and_the_resolution() -> None:
    tree = ["LICENSE", "docs/releasing.md", "docs/diagram.png"]
    statuses = {
        "https://img.shields.io/pypi/v/aspose-3d-foss.svg": 200,
        "https://pypi.org/project/aspose-3d-foss/": 200,
        "https://example.com/": 404,
    }
    facts, probes = link_facts("README.md", README.encode(), tree, fetch=lambda u: (statuses[u], u))
    by_value = {f.value: f for f in facts}
    assert [f.id for f in facts][:3] == ["link_target:001", "link_target:002", "link_target:003"]
    assert by_value["LICENSE"].polarity == "SUPPORTED"
    assert by_value["docs/releasing.md#steps"].polarity == "SUPPORTED"
    assert by_value["#quick-start"].polarity == "SUPPORTED"
    assert by_value["#nowhere"].polarity == "CONTRADICTED"
    assert by_value["missing/file.md"].polarity == "CONTRADICTED"
    assert by_value["https://example.com/"].polarity == "CONTRADICTED"
    assert by_value["mailto:support@example.com"].polarity == "UNRESOLVED"
    pypi = by_value["https://pypi.org/project/aspose-3d-foss/"]
    assert pypi.evidence[0].path == "README.md"
    assert pypi.evidence[0].detail == "line 3; external; text 'PyPI'"
    assert pypi.evidence[1].path == "https://pypi.org/project/aspose-3d-foss/"
    assert pypi.evidence[1].detail == "RESOLVED: HTTP 200"
    # One probe record per external read, with the status and the duration the fact omits.
    assert {probe.target for probe in probes} == set(statuses)
    assert {probe.outcome for probe in probes} == {"RESOLVED", "MISSING"}
    assert all(probe.elapsed_ms is not None for probe in probes)
    assert {probe.status for probe in probes} == {200, 404}
    assert (
        link_facts("README.md", README.encode(), tree, fetch=lambda u: (statuses[u], u))[0] == facts
    )


def test_a_head_that_condemns_a_link_is_confirmed_with_a_get() -> None:
    """HEAD is an optimisation; a negative verdict comes from the method a reader would use.

    Measured 2026-09-06: `https://www.nuget.org/packages/Aspose.3D.FOSS/` answers HEAD with 404
    and GET with 200, so BC-06 called the NuGet badge's own target missing and failed the whole
    Aspose.3D for .NET candidate at EXTRACTING.
    """
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if str(request.url).endswith("/hostile/"):
            return httpx.Response(200 if request.method == "GET" else 404)
        return httpx.Response(200 if request.method == "HEAD" else 500)

    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def client(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return original(**kwargs)  # type: ignore[arg-type]

    httpx.Client = client  # type: ignore[misc]
    try:
        assert fetch_status("https://h/hostile/") == (200, "https://h/hostile/")
        assert fetch_status("https://h/plain/") == (200, "https://h/plain/")
    finally:
        httpx.Client = original  # type: ignore[misc]
    # The hostile host was asked twice; the well-behaved one only once.
    assert [method for method, url in calls if "hostile" in url] == ["HEAD", "GET"]
    assert [method for method, url in calls if "plain" in url] == ["HEAD"]
