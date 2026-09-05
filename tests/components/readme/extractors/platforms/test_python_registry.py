"""The PyPI observation: found, not found, transient failures retried, unreachable unresolved."""

from __future__ import annotations

import json

import httpx

from repository_presenter.components.readme.extractors.platforms.python_registry import (
    fetch_project_json,
    observe_pypi,
)


def _fetch_with(responses: list[httpx.Response]) -> tuple[list[str], object]:
    calls: list[str] = []

    def fetch(url: str) -> httpx.Response:
        calls.append(url)
        return responses.pop(0)

    return calls, fetch


def _project(latest: str, releases: list[str]) -> httpx.Response:
    payload = {"info": {"version": latest}, "releases": {v: [] for v in releases}}
    return httpx.Response(200, json=payload)


def test_found_distribution_reports_latest_and_published_state() -> None:
    calls, fetch = _fetch_with([_project("26.1.0", ["26.0.0", "26.1.0"])])
    observation = observe_pypi("aspose-3d-foss", "26.1.0", fetch=fetch)  # type: ignore[arg-type]
    assert calls == ["https://pypi.org/pypi/aspose-3d-foss/json"]
    assert observation.found and observation.latest_version == "26.1.0"
    assert observation.manifest_version_published is True
    # The summary is what the fact's evidence carries, so the version stays out of it and
    # travels in the probe record instead (section 27.2 RC7).
    assert observation.summary == "package registry: found; manifest version published"
    assert observation.status == 200 and observation.elapsed_ms is not None
    probe = observation.probe
    assert (probe.kind, probe.outcome, probe.observation) == (
        "package_registry",
        "FOUND",
        "latest 26.1.0",
    )
    older = observe_pypi(
        "aspose-3d-foss", "25.0.0", fetch=_fetch_with([_project("26.1.0", ["26.1.0"])])[1]
    )  # type: ignore[arg-type]
    assert older.manifest_version_published is False
    unknown = observe_pypi("aspose-3d-foss", None, fetch=_fetch_with([_project("1", ["1"])])[1])  # type: ignore[arg-type]
    assert unknown.manifest_version_published is None
    assert "manifest version unknown" in unknown.summary


def test_missing_distribution_is_not_found_without_retry() -> None:
    calls, fetch = _fetch_with([httpx.Response(404, json={"message": "Not Found"})])
    observation = observe_pypi("no-such-dist", "1.0", fetch=fetch, sleep=lambda _s: None)  # type: ignore[arg-type]
    assert (observation.found, observation.error) == (False, None)
    assert observation.summary == "package registry: distribution not found"
    assert len(calls) == 1


def test_transient_failures_are_retried_then_succeed() -> None:
    calls, fetch = _fetch_with(
        [
            httpx.Response(503, headers={"Retry-After": "2"}),
            httpx.Response(200, json={"info": {"version": "1.0"}, "releases": {"1.0": []}}),
        ]
    )
    sleeps: list[float] = []
    observation = observe_pypi("dist", "1.0", fetch=fetch, sleep=sleeps.append)  # type: ignore[arg-type]
    assert observation.found and len(calls) == 2
    assert sleeps == [2.0]


def test_unreachable_registry_leaves_the_claim_unresolved() -> None:
    def fetch(url: str) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    observation = observe_pypi("dist", "1.0", fetch=fetch, sleep=lambda _s: None)
    assert not observation.found
    assert observation.error is not None and "ConnectError" in observation.error
    assert observation.summary.startswith("package registry unreachable")


def test_malformed_and_unexpected_responses_are_errors() -> None:
    malformed = observe_pypi("dist", "1.0", fetch=_fetch_with([httpx.Response(200, text="{}")])[1])  # type: ignore[arg-type]
    assert malformed.error is not None and "malformed" in malformed.error
    forbidden = observe_pypi("dist", "1.0", fetch=_fetch_with([httpx.Response(403)])[1])  # type: ignore[arg-type]
    assert forbidden.error == "HTTP 403"


def test_fetch_uses_a_bounded_json_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept"] == "application/json"
        assert request.headers["User-Agent"].startswith("repository-presenter")
        return httpx.Response(200, json={"info": {"version": "2.0"}, "releases": {}})

    response = fetch_project_json(
        "https://pypi.org/pypi/x/json", transport=httpx.MockTransport(handler)
    )
    assert json.loads(response.text)["info"]["version"] == "2.0"
