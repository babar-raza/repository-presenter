"""The read-only organization listing: paged, bounded, incomplete rather than quietly short."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from repository_presenter.components.monitor import org_listing
from repository_presenter.components.monitor.org_listing import (
    PAGE_SIZE,
    list_organization_repositories,
)

TOKEN = "ghs_fixture_listing_read_token_0123456789"


def _record(
    identity: int, name: str, org: str = "aspose-email-foss", **flags: Any
) -> dict[str, Any]:
    return {
        "id": identity,
        "full_name": f"{org}/{name}",
        "name": name,
        "archived": False,
        "private": False,
        "fork": False,
        "default_branch": "main",
        "pushed_at": "2026-09-26T20:04:06Z",
        "language": "Python",
        **flags,
    }


class Pages:
    """A fake ``fetch``: answers each call with the next queued response (the last one repeats,
    so a retried transient failure keeps failing) and records the URL."""

    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []
        self.tokens: list[str | None] = []

    def __call__(self, url: str, token: str | None) -> httpx.Response:
        self.urls.append(url)
        self.tokens.append(token)
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


def test_a_short_page_is_the_whole_listing_and_only_the_organization_endpoint_is_read() -> None:
    fetch = Pages(httpx.Response(200, json=[_record(2, "B"), _record(1, "A", archived=True)]))

    listing = list_organization_repositories("aspose-email-foss", token=TOKEN, fetch=fetch)

    assert listing.complete and listing.error is None
    assert [r.full_name for r in listing.repositories] == [
        "aspose-email-foss/B",
        "aspose-email-foss/A",
    ]
    assert listing.repositories[1].archived is True
    assert listing.repositories[0].language == "Python"
    # One request, to the organization's listing and nothing else: no per-repository read exists.
    assert fetch.urls == [
        "https://api.github.com/orgs/aspose-email-foss/repos?type=all&per_page=100&page=1"
    ]
    assert fetch.tokens == [TOKEN]


def test_full_pages_are_followed_until_a_short_one_with_urls_the_code_chose() -> None:
    first = [_record(i, f"R{i}") for i in range(1, PAGE_SIZE + 1)]
    second = [_record(PAGE_SIZE + 1, "Last")]
    # A Link header pointing at another host must not be followed with the bearer token.
    hostile = {"Link": '<https://evil.example/steal?page=2>; rel="next"'}
    fetch = Pages(
        httpx.Response(200, json=first, headers=hostile), httpx.Response(200, json=second)
    )

    listing = list_organization_repositories("aspose-email-foss", token=TOKEN, fetch=fetch)

    assert len(listing.repositories) == PAGE_SIZE + 1 and listing.complete
    assert [url.rsplit("page=", 1)[1] for url in fetch.urls] == ["1", "2"]
    assert all(
        url.startswith("https://api.github.com/orgs/aspose-email-foss/repos?") for url in fetch.urls
    )


def test_an_exactly_full_last_page_is_followed_by_an_empty_one() -> None:
    page = [_record(i, f"R{i}") for i in range(1, PAGE_SIZE + 1)]
    fetch = Pages(httpx.Response(200, json=page), httpx.Response(200, json=[]))

    listing = list_organization_repositories("aspose-email-foss", fetch=fetch)

    assert len(listing.repositories) == PAGE_SIZE and listing.complete


def test_the_page_cap_marks_the_listing_truncated_not_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(org_listing, "MAX_PAGES", 2)
    full = [_record(i, f"R{i}") for i in range(1, PAGE_SIZE + 1)]
    fetch = Pages(httpx.Response(200, json=full), httpx.Response(200, json=full))

    listing = list_organization_repositories("aspose-email-foss", fetch=fetch)

    assert listing.truncated and not listing.complete and listing.error is None
    assert len(fetch.urls) == 2


@pytest.mark.parametrize("status", [401, 403, 404])
def test_a_refused_listing_is_an_error_with_no_repositories(status: int) -> None:
    fetch = Pages(httpx.Response(status, json={"message": "no"}))

    listing = list_organization_repositories("aspose-email-foss", token=TOKEN, fetch=fetch)

    assert listing.error == f"HTTP {status}" and listing.repositories == () and not listing.complete


def test_a_failure_on_a_later_page_discards_the_partial_list() -> None:
    page = [_record(i, f"R{i}") for i in range(1, PAGE_SIZE + 1)]
    fetch = Pages(httpx.Response(200, json=page), httpx.Response(500))

    listing = list_organization_repositories(
        "aspose-email-foss", fetch=fetch, sleep=lambda _s: None
    )

    # A partial list read as the whole would under-count: the listing is an error instead.
    assert listing.error is not None and listing.repositories == ()


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "not a list"},
        [{"id": 1}],
        [{"id": "1", "full_name": "aspose-email-foss/A"}],
        [{"id": True, "full_name": "aspose-email-foss/A"}],
        [{"id": 1, "full_name": "not a name"}],
        ["aspose-email-foss/A"],
    ],
)
def test_a_record_that_cannot_be_read_makes_the_listing_an_error_never_a_shorter_one(
    payload: Any,
) -> None:
    fetch = Pages(httpx.Response(200, json=payload))

    listing = list_organization_repositories("aspose-email-foss", fetch=fetch)

    assert listing.error is not None and listing.error.startswith("malformed listing response")
    assert listing.repositories == ()


def test_transport_failures_are_retried_then_recorded_with_the_token_redacted() -> None:
    def fetch(url: str, token: str | None) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach host with {token}")

    listing = list_organization_repositories(
        "aspose-email-foss", token=TOKEN, fetch=fetch, sleep=lambda _s: None
    )

    assert listing.error is not None
    assert TOKEN not in listing.error


def test_a_record_of_another_organization_is_not_counted_and_a_bad_name_is_refused() -> None:
    fetch = Pages(
        httpx.Response(200, json=[_record(1, "A"), _record(2, "Stray", org="someone-else")])
    )

    listing = list_organization_repositories("Aspose-Email-FOSS", fetch=fetch)

    assert [r.full_name for r in listing.repositories] == ["aspose-email-foss/A"]
    refused = list_organization_repositories("bad/org", fetch=Pages())
    assert refused.error == "not a valid organization name"
