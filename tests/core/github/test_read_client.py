"""Read-only GitHub observations: a file, a tree, a default-branch head - found, not found,
transient failures retried, unreachable inconclusive. Mirrors
tests/components/readme/extractors/platforms/test_python_registry.py's own fixture shape."""

from __future__ import annotations

import base64

import httpx
import pytest

from repository_presenter.core.github import read_client
from repository_presenter.core.github.read_client import (
    fetch_default_branch_sha,
    fetch_file,
    fetch_get,
    fetch_tree,
)


def _fetch_with(responses: list[httpx.Response]):
    calls: list[str] = []

    def fetch(url: str, token: str | None) -> httpx.Response:
        calls.append(url)
        return responses.pop(0)

    return calls, fetch


def _contents_response(text: str) -> httpx.Response:
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return httpx.Response(200, json={"content": encoded, "encoding": "base64"})


def test_fetch_file_decodes_base64_content() -> None:
    calls, fetch = _fetch_with([_contents_response('build-backend = "setuptools.build_meta"\n')])
    result = fetch_file("o/r", "deadbeef", "pyproject.toml", fetch=fetch)
    assert calls == ["https://api.github.com/repos/o/r/contents/pyproject.toml?ref=deadbeef"]
    assert result.found is True
    assert result.content == 'build-backend = "setuptools.build_meta"\n'


def test_fetch_file_missing_is_not_found_without_error() -> None:
    calls, fetch = _fetch_with([httpx.Response(404, json={"message": "Not Found"})])
    result = fetch_file("o/r", "deadbeef", "missing.txt", fetch=fetch, sleep=lambda _s: None)
    assert (result.found, result.content, result.error) == (False, None, None)
    assert len(calls) == 1


def test_fetch_file_retries_transient_then_succeeds() -> None:
    calls, fetch = _fetch_with(
        [
            httpx.Response(503, headers={"Retry-After": "1"}),
            _contents_response("ok"),
        ]
    )
    sleeps: list[float] = []
    result = fetch_file("o/r", "rev", "f.py", fetch=fetch, sleep=sleeps.append)
    assert result.found and result.content == "ok"
    assert len(calls) == 2 and sleeps == [1.0]


def test_fetch_file_reports_malformed_response() -> None:
    _, fetch = _fetch_with([httpx.Response(200, json={"encoding": "base64"})])
    result = fetch_file("o/r", "rev", "f.py", fetch=fetch)
    assert result.found is False and result.error is not None and "malformed" in result.error


def test_fetch_tree_lists_only_blob_paths_and_reports_truncation() -> None:
    payload = {
        "tree": [
            {"path": "src", "type": "tree"},
            {"path": "src/a.py", "type": "blob"},
            {"path": "src/b.py", "type": "blob"},
        ],
        "truncated": True,
    }
    _, fetch = _fetch_with([httpx.Response(200, json=payload)])
    result = fetch_tree("o/r", "rev", fetch=fetch)
    assert result.paths == ("src/a.py", "src/b.py")
    assert result.truncated is True
    assert result.error is None


def test_fetch_tree_reports_http_error() -> None:
    _, fetch = _fetch_with([httpx.Response(404)])
    result = fetch_tree("o/r", "rev", fetch=fetch, sleep=lambda _s: None)
    assert result.paths == () and result.error == "HTTP 404"


def test_fetch_default_branch_sha_resolves_branch_then_commit() -> None:
    calls, fetch = _fetch_with(
        [
            httpx.Response(200, json={"default_branch": "main"}),
            httpx.Response(200, json={"sha": "abc123"}),
        ]
    )
    result = fetch_default_branch_sha("o/r", fetch=fetch)
    assert calls == [
        "https://api.github.com/repos/o/r",
        "https://api.github.com/repos/o/r/commits/main",
    ]
    assert (result.branch, result.sha, result.error) == ("main", "abc123", None)


def test_fetch_default_branch_sha_reports_repo_lookup_failure() -> None:
    _, fetch = _fetch_with([httpx.Response(404)])
    result = fetch_default_branch_sha("o/r", fetch=fetch, sleep=lambda _s: None)
    assert result.sha is None and result.error == "HTTP 404"


def test_unreachable_registry_is_reported_not_raised() -> None:
    def fetch(url: str, token: str | None) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    result = fetch_file("o/r", "rev", "f.py", fetch=fetch, sleep=lambda _s: None)
    assert result.found is False
    assert result.error is not None and "ConnectError" in result.error


def test_fetch_get_sends_a_bearer_token_and_api_version_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-token"
        assert request.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert request.headers["User-Agent"].startswith("repository-presenter")
        return httpx.Response(200, json={"ok": True})

    real_client = httpx.Client

    def client_factory(*args: object, **kwargs: object) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(read_client.httpx, "Client", client_factory)
    response = fetch_get("https://api.github.com/repos/o/r", "secret-token")
    assert response.status_code == 200
