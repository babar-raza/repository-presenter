"""The GitHub client's issue-lifecycle primitives (TC-ISS-09/10/11): telling a lost create response
from a rejected one, scanning for the issues this system filed, and reading and writing issue
comments. A fake fetch/write only; no test here makes a live call."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    API_ROOT,
    ISSUE_LIST_MAX_PAGES,
    MARKER_PREFIX,
    IssueOutcomeUnknownError,
    create_issue,
    create_issue_comment,
    list_issue_comments,
    scan_marker_issues,
)

OWNER = "aspose-cells-foss"
REPO = "Aspose.Cells-FOSS-for-Cpp"
MARKER = f"{MARKER_PREFIX} sha256:{'a' * 64} -->"


class _Write:
    def __init__(self, status: int, body: object) -> None:
        self.status, self.body = status, body
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status, self.body


_CREATED = {"number": 7, "html_url": "https://github.com/o/n/issues/7"}


# --- a lost response is not a rejection ---------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (-1, "ReadTimeout: timed out"),
        (408, None),
        (500, {"message": "boom"}),
        (502, None),
        (503, None),
        (504, None),
        (201, {"unexpected": True}),
        (201, None),
    ],
)
def test_create_issue_marks_an_ambiguous_outcome_as_unknown(status: int, body: object) -> None:
    with pytest.raises(IssueOutcomeUnknownError):
        create_issue(OWNER, REPO, title="t", body="b", token="w", write=_Write(status, body))


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422, 429])
def test_create_issue_a_definite_rejection_is_not_unknown(status: int) -> None:
    with pytest.raises(RepositoryMetadataError) as caught:
        create_issue(OWNER, REPO, title="t", body="b", token="w", write=_Write(status, {}))
    assert not isinstance(caught.value, IssueOutcomeUnknownError)


def test_an_unknown_outcome_is_still_a_repository_metadata_error() -> None:
    assert issubclass(IssueOutcomeUnknownError, RepositoryMetadataError)


# --- scan_marker_issues -------------------------------------------------------------------------


class _Pages:
    def __init__(self, *pages: tuple[int, object]) -> None:
        self.pages = list(pages)
        self.urls: list[str] = []

    def __call__(self, url: str, token: str | None) -> tuple[int, object]:
        self.urls.append(url)
        return self.pages[min(len(self.urls) - 1, len(self.pages) - 1)]


def _issue(number: int, body: str, state: str = "open", created: str = "2026-10-11T01:00:00Z"):  # type: ignore[no-untyped-def]
    return {
        "number": number,
        "html_url": f"https://github.com/o/n/issues/{number}",
        "body": body,
        "state": state,
        "created_at": created,
    }


def test_scan_returns_only_issues_carrying_the_marker_prefix_with_state_and_creation() -> None:
    fetch = _Pages(
        (
            200,
            [
                _issue(1, "unrelated"),
                _issue(2, f"text\n{MARKER}\n", "closed", "2026-10-09T10:00:00Z"),
                {**_issue(3, MARKER), "pull_request": {"url": "x"}},
                _issue(4, f"x {MARKER}", "open", "2026-10-11T02:00:00Z"),
            ],
        )
    )
    found = scan_marker_issues(OWNER, REPO, token="r", fetch=fetch)
    assert [(i.number, i.state, i.created_at) for i in found] == [
        (2, "closed", "2026-10-09T10:00:00Z"),
        (4, "open", "2026-10-11T02:00:00Z"),
    ]
    assert "state=all" in fetch.urls[0]


def test_scan_passes_state_and_since_to_the_listing() -> None:
    fetch = _Pages((200, []))
    scan_marker_issues(
        OWNER, REPO, token="r", state="open", since="2026-10-11T00:00:00Z", fetch=fetch
    )
    assert "state=open" in fetch.urls[0]
    assert "since=2026-10-11T00:00:00Z" in fetch.urls[0]


def test_scan_pages_until_a_short_page() -> None:
    full = [_issue(n, "no") for n in range(100)]
    fetch = _Pages((200, full), (200, [_issue(900, MARKER)]))
    assert [i.number for i in scan_marker_issues(OWNER, REPO, token="r", fetch=fetch)] == [900]


@pytest.mark.parametrize("status", [-1, 403, 500])
def test_scan_fails_closed_never_reporting_zero_on_an_error(status: int) -> None:
    with pytest.raises(RepositoryMetadataError):
        scan_marker_issues(OWNER, REPO, token="r", fetch=_Pages((status, "x")))


def test_scan_fails_closed_past_the_page_cap() -> None:
    fetch = _Pages((200, [_issue(n, "no") for n in range(100)]))
    with pytest.raises(RepositoryMetadataError, match="cannot prove"):
        scan_marker_issues(OWNER, REPO, token="r", fetch=fetch)
    assert len(fetch.urls) == ISSUE_LIST_MAX_PAGES


# --- comments -----------------------------------------------------------------------------------


def test_list_comments_returns_id_body_and_creation_in_order() -> None:
    fetch = _Pages(
        (
            200,
            [
                {"id": 11, "body": "first", "created_at": "2026-10-10T00:00:00Z"},
                {"id": 12, "body": "second", "created_at": "2026-10-11T00:00:00Z"},
            ],
        )
    )
    comments = list_issue_comments(OWNER, REPO, 7, token="r", fetch=fetch)
    assert [(c.id, c.body) for c in comments] == [(11, "first"), (12, "second")]
    assert fetch.urls[0].startswith(f"{API_ROOT}/repos/{OWNER}/{REPO}/issues/7/comments")


def test_list_comments_fails_closed_on_an_error() -> None:
    with pytest.raises(RepositoryMetadataError):
        list_issue_comments(OWNER, REPO, 7, token="r", fetch=_Pages((404, None)))


def test_create_comment_posts_the_body_and_returns_the_comment() -> None:
    write = _Write(201, {"id": 99, "body": "hello", "created_at": "2026-10-11T00:00:00Z"})
    comment = create_issue_comment(OWNER, REPO, 7, body="hello", token="w", write=write)
    assert comment.id == 99
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/issues/7/comments"
    assert token == "w"
    assert payload == {"body": "hello"}


def test_create_comment_refuses_without_a_token_and_makes_no_call() -> None:
    write = _Write(201, {})
    with pytest.raises(RepositoryMetadataError):
        create_issue_comment(OWNER, REPO, 7, body="hello", token="", write=write)
    assert write.calls == []


@pytest.mark.parametrize("status", [-1, 502])
def test_create_comment_marks_an_ambiguous_outcome_as_unknown(status: int) -> None:
    with pytest.raises(IssueOutcomeUnknownError):
        create_issue_comment(OWNER, REPO, 7, body="hello", token="w", write=_Write(status, "boom"))


def test_create_comment_a_rejection_is_not_unknown() -> None:
    with pytest.raises(RepositoryMetadataError) as caught:
        create_issue_comment(OWNER, REPO, 7, body="hello", token="w", write=_Write(403, {}))
    assert not isinstance(caught.value, IssueOutcomeUnknownError)
