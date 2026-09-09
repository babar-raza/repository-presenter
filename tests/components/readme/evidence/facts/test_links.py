"""Link targets: extracted once each, resolved by kind, never assumed."""

from __future__ import annotations

import socket
from collections.abc import Callable

import httpx
import pytest

from repository_presenter.components.readme.evidence.facts.links import (
    PrivateAddressError,
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


def test_extract_links_discovers_raw_html_anchors_and_images() -> None:
    """TB-09, D9: markdown-it tokenizes a raw `<a href>`/`<img src>` tag as `html_inline`,
    invisible to the CommonMark `link_open`/`image` handling alone - a target only ever written
    as raw HTML (a common README banner/badge pattern) was silently missing from link checking."""
    html_readme = (
        "# Title\n\n"
        'See <a href="https://example.com/docs">the docs</a> for more.\n\n'
        'Badge: <a href="https://example.com/">'
        '<img src="https://example.com/badge.svg" alt="Badge"></a>\n'
    )
    links = extract_links(html_readme)
    assert [(link.href, link.kind, link.text) for link in links] == [
        ("https://example.com/docs", "external", "the docs"),
        ("https://example.com/badge.svg", "external", "Badge"),
        ("https://example.com/", "external", ""),
    ]
    # The markdown-syntax equivalent of the first case returns the identical target.
    markdown_equivalent = "# Title\n\nSee [the docs](https://example.com/docs) for more.\n"
    assert extract_links(markdown_equivalent)[0].href == links[0].href

    # A bare, unwrapped <img> tag (no anchor) is discovered the same way as a markdown image -
    # as long as prose keeps it part of the paragraph's own inline content; markdown-it tokenizes
    # a *lone* HTML tag occupying an entire line by itself as a block, not `html_inline`, which
    # is this fix's own documented, out-of-scope boundary (see links.py's docstring).
    bare_image = extract_links('Logo: <img src="https://example.com/logo.png" alt="Logo">\n')
    assert [(link.href, link.text) for link in bare_image] == [
        ("https://example.com/logo.png", "Logo")
    ]

    # A stray, unmatched closing tag or an unrelated raw HTML element claims no target.
    assert extract_links("</a> and <br> and <span>text</span>\n") == []


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


def _mock_addresses(monkeypatch: pytest.MonkeyPatch, hosts: dict[str, str]) -> None:
    """Deterministic, network-free DNS: only the named hosts resolve, to the given address."""

    def fake_getaddrinfo(host: object, *args: object, **kwargs: object) -> object:
        if host in hosts:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (hosts[host], 0))]
        raise socket.gaierror(f"unresolvable in test: {host!r}")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def _with_mock_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def client(**kwargs: object) -> httpx.Client:
        kwargs["transport"] = transport
        return original(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "Client", client)


# TB-08, external review D8, 2026-09-08: fetch_status made no address check at all, so a link
# resolving - directly or via a redirect - to a loopback, link-local, or otherwise private/
# reserved address was fetched exactly like any other. No test here ever makes a real network
# request: DNS resolution is monkeypatched deterministically, and the HTTP layer is MockTransport,
# the same technique the external review packet itself used.


def test_fetch_status_rejects_a_direct_link_to_a_private_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_addresses(monkeypatch, {"internal": "169.254.169.254"})
    _with_mock_transport(monkeypatch, lambda request: httpx.Response(200))
    with pytest.raises(PrivateAddressError, match="private/reserved address"):
        fetch_status("https://internal/metadata")


def test_fetch_status_rejects_a_redirect_to_a_private_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.host == "redirector":
            return httpx.Response(302, headers={"Location": "https://internal/"})
        return httpx.Response(200)

    _mock_addresses(monkeypatch, {"redirector": "93.184.216.34", "internal": "127.0.0.1"})
    _with_mock_transport(monkeypatch, handler)
    with pytest.raises(PrivateAddressError, match="private/reserved address"):
        fetch_status("https://redirector/")
    # The redirect target itself was never actually requested - rejected before that request.
    assert calls == ["https://redirector/"]


def test_check_external_reports_a_rejected_private_target_as_unchecked_without_retrying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[str] = []

    def fetch(url: str) -> tuple[int, str]:
        attempts.append(url)
        raise PrivateAddressError(f"{url} resolves to a private/reserved address")

    result = check_external("https://internal/", fetch=fetch, sleep=lambda s: None)
    assert result.outcome == "UNCHECKED"
    assert result.detail.startswith("rejected:")
    assert len(attempts) == 1  # never retried - a private address does not become public


def test_fetch_status_does_not_reject_a_host_that_fails_to_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing to protect against reaching if the name resolves to nothing; left to fail
    naturally at the transport layer, exactly as before this fix - proven directly rather than
    only inferred from the pre-existing tests above (which happen to use unresolvable hosts)."""
    _mock_addresses(monkeypatch, {})  # every host is unresolvable
    _with_mock_transport(monkeypatch, lambda request: httpx.Response(200))
    assert fetch_status("https://anything-unresolvable/") == (
        200,
        "https://anything-unresolvable/",
    )
