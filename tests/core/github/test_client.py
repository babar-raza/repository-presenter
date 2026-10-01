"""The GitHub client: read (``GET``) and write (``PATCH``/``PUT``/``POST``) - a fake fetch/write
only, no test here makes a live call. The write functions have no authorization check of their own
(that lives in ``components/metadata/apply.py`` and ``components/issues/file.py``); these tests
exercise only their own request/response handling in isolation."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    API_ROOT,
    create_issue,
    create_pull_request,
    create_ref,
    find_open_pull_request,
    get_contents,
    get_ref,
    get_repository,
    put_contents,
    replace_topics,
    update_pull_request,
    update_repository,
)


def _fetch(status_code: int, body: object) -> object:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == f"{API_ROOT}/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python"
        assert token == "ghp_test"
        return status_code, body

    return fetch


def test_a_populated_repository_reports_description_homepage_and_topics() -> None:
    body = {
        "description": "3D file format library",
        "homepage": "https://products.aspose.org/3d/python/",
        "topics": ["python", "3d", "aspose", "foss"],
    }
    observed = get_repository(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_test",
        fetch=_fetch(200, body),
        clock=lambda: "2026-09-23T00:00:00Z",
    )
    assert observed.repository == "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert observed.description == "3D file format library"
    assert observed.homepage == "https://products.aspose.org/3d/python/"
    assert observed.topics == ("python", "3d", "aspose", "foss")
    assert observed.observed_at == "2026-09-23T00:00:00Z"
    assert observed.schema_version == 1


def test_unset_description_homepage_and_topics_are_null_and_empty_not_guessed() -> None:
    body = {"description": None, "homepage": None, "topics": []}
    observed = get_repository(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_test",
        fetch=_fetch(200, body),
        clock=lambda: "2026-09-23T00:00:00Z",
    )
    assert observed.description is None
    assert observed.homepage is None
    assert observed.topics == ()


def test_empty_string_description_and_homepage_normalise_to_none() -> None:
    body = {"description": "", "homepage": "", "topics": []}
    observed = get_repository(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_test",
        fetch=_fetch(200, body),
        clock=lambda: "2026-09-23T00:00:00Z",
    )
    assert observed.description is None
    assert observed.homepage is None


def test_a_missing_repository_raises_rather_than_returning_a_partial_observation() -> None:
    with pytest.raises(RepositoryMetadataError):
        get_repository(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            token="ghp_test",
            fetch=_fetch(404, {"message": "Not Found"}),
        )


def test_a_rate_limited_or_denied_response_raises() -> None:
    with pytest.raises(RepositoryMetadataError):
        get_repository(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            token="ghp_test",
            fetch=_fetch(403, {"message": "rate limited"}),
        )


def test_an_unreachable_host_raises_rather_than_retrying_silently() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError: name resolution failed"

    with pytest.raises(RepositoryMetadataError):
        get_repository("aspose-3d-foss", "Aspose.3D-FOSS-for-Python", token="ghp_test", fetch=fetch)


def test_a_non_dict_body_on_200_raises_rather_than_being_treated_as_empty() -> None:
    with pytest.raises(RepositoryMetadataError):
        get_repository(
            "aspose-3d-foss", "Aspose.3D-FOSS-for-Python", token="ghp_test", fetch=_fetch(200, [])
        )


def test_no_token_is_still_a_valid_call_shape_public_repository_read() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert token is None
        return 200, {"description": None, "homepage": None, "topics": []}

    observed = get_repository(
        "aspose-3d-foss", "Aspose.3D-FOSS-for-Python", token=None, fetch=fetch
    )
    assert observed.topics == ()


# ---------------------------------------------------------------------------
# update_repository (PATCH) / replace_topics (PUT) - never called in production except by
# components/metadata/apply.py, and only past that module's own authorization gate.
# ---------------------------------------------------------------------------


class _RecordingWrite:
    def __init__(self, status_code: int = 200, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


def test_update_repository_sends_only_the_given_fields() -> None:
    write = _RecordingWrite()
    update_repository(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        description="New text",
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert token == "ghp_w"
    assert payload == {"description": "New text"}


def test_update_repository_can_send_both_fields_together() -> None:
    write = _RecordingWrite()
    update_repository(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        description="New text",
        homepage="https://new/",
        token="ghp_w",
        write=write,
    )
    assert write.calls[0][2] == {"description": "New text", "homepage": "https://new/"}


def test_update_repository_raises_value_error_with_nothing_to_change() -> None:
    write = _RecordingWrite()
    with pytest.raises(ValueError):
        update_repository("aspose-3d-foss", "Aspose.3D-FOSS-for-Python", token="ghp_w", write=write)
    assert write.calls == []


def test_update_repository_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        update_repository(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            description="x",
            token="",
            write=write,
        )
    assert write.calls == []


def test_update_repository_raises_on_a_non_200_status() -> None:
    write = _RecordingWrite(status_code=422, body={"message": "Validation failed"})
    with pytest.raises(RepositoryMetadataError):
        update_repository(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            description="x",
            token="ghp_w",
            write=write,
        )


def test_update_repository_raises_on_unreachable() -> None:
    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return -1, "ConnectError: name resolution failed"

    with pytest.raises(RepositoryMetadataError):
        update_repository(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            description="x",
            token="ghp_w",
            write=write,
        )


def test_replace_topics_puts_the_full_set() -> None:
    write = _RecordingWrite()
    replace_topics(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        topics=("python", "3d", "mit"),
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python/topics"
    assert token == "ghp_w"
    assert payload == {"names": ["python", "3d", "mit"]}


def test_replace_topics_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        replace_topics(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            topics=("python",),
            token="",
            write=write,
        )
    assert write.calls == []


def test_replace_topics_raises_on_a_non_200_status() -> None:
    write = _RecordingWrite(status_code=403, body={"message": "Forbidden"})
    with pytest.raises(RepositoryMetadataError):
        replace_topics(
            "aspose-3d-foss",
            "Aspose.3D-FOSS-for-Python",
            topics=("python",),
            token="ghp_w",
            write=write,
        )


# ---------------------------------------------------------------------------
# create_issue (POST) - never called in production except by components/issues/file.py, and only
# past that module's own authorization gate.
# ---------------------------------------------------------------------------


def test_create_issue_posts_title_and_body_and_returns_number_and_url() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={"number": 42, "html_url": "https://github.com/o/n/issues/42", "id": 999},
    )
    created = create_issue(
        "aspose-cells-foss",
        "Aspose.Cells-FOSS-for-Cpp",
        title="install_command:cmake is UNRESOLVED",
        body="See evidence.",
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues"
    assert token == "ghp_w"
    assert payload == {"title": "install_command:cmake is UNRESOLVED", "body": "See evidence."}
    assert created.number == 42
    assert created.url == "https://github.com/o/n/issues/42"


def test_create_issue_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_issue(
            "aspose-cells-foss",
            "Aspose.Cells-FOSS-for-Cpp",
            title="t",
            body="b",
            token="",
            write=write,
        )
    assert write.calls == []


def test_create_issue_raises_on_a_non_201_status() -> None:
    write = _RecordingWrite(status_code=422, body={"message": "Validation failed"})
    with pytest.raises(RepositoryMetadataError):
        create_issue(
            "aspose-cells-foss",
            "Aspose.Cells-FOSS-for-Cpp",
            title="t",
            body="b",
            token="ghp_w",
            write=write,
        )


def test_create_issue_raises_on_unreachable() -> None:
    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return -1, "ConnectError: name resolution failed"

    with pytest.raises(RepositoryMetadataError):
        create_issue(
            "aspose-cells-foss",
            "Aspose.Cells-FOSS-for-Cpp",
            title="t",
            body="b",
            token="ghp_w",
            write=write,
        )


def test_create_issue_raises_on_a_malformed_success_body() -> None:
    write = _RecordingWrite(status_code=201, body={"message": "created but no number field"})
    with pytest.raises(RepositoryMetadataError):
        create_issue(
            "aspose-cells-foss",
            "Aspose.Cells-FOSS-for-Cpp",
            title="t",
            body="b",
            token="ghp_w",
            write=write,
        )


# ---------------------------------------------------------------------------
# get_ref / create_ref / get_contents / put_contents / find_open_pull_request /
# create_pull_request / update_pull_request - never called in production except by
# components/propose/effect.py, and only past that module's own authorization gate.
# ---------------------------------------------------------------------------

OWNER = "babar-raza"
REPO = "disposable-target"


def test_get_ref_returns_the_tip_sha_when_the_branch_exists() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/git/ref/heads/main"
        return 200, {"object": {"sha": "abc123"}}

    assert get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch) == "abc123"


def test_get_ref_returns_none_when_the_branch_does_not_exist() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 404, {"message": "Not Found"}

    assert get_ref(OWNER, REPO, "presenter/readme-update", token="ghp_w", fetch=fetch) is None


def test_get_ref_raises_on_unreachable() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch)


def test_get_ref_raises_on_a_malformed_success_body() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, {"object": {}}

    with pytest.raises(RepositoryMetadataError):
        get_ref(OWNER, REPO, "main", token="ghp_w", fetch=fetch)


def test_create_ref_posts_the_new_branch_pointing_at_sha() -> None:
    write = _RecordingWrite(status_code=201, body={"ref": "refs/heads/presenter/readme-update"})
    create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="ghp_w", write=write)
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/git/refs"
    assert token == "ghp_w"
    assert payload == {"ref": "refs/heads/presenter/readme-update", "sha": "abc123"}


def test_create_ref_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="", write=write)
    assert write.calls == []


def test_create_ref_raises_on_a_non_201_status() -> None:
    write = _RecordingWrite(status_code=422, body={"message": "Reference already exists"})
    with pytest.raises(RepositoryMetadataError):
        create_ref(OWNER, REPO, "presenter/readme-update", "abc123", token="ghp_w", write=write)


def test_get_contents_decodes_base64_text() -> None:
    encoded = base64.b64encode(b"# Hello\n").decode("ascii")

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/contents/README.md?ref=main"
        return 200, {"sha": "filesha1", "content": encoded}

    contents = get_contents(OWNER, REPO, "README.md", ref="main", token="ghp_w", fetch=fetch)
    assert contents is not None
    assert contents.text == "# Hello\n"
    assert contents.sha == "filesha1"


def test_get_contents_returns_none_when_the_file_does_not_exist_on_this_branch() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 404, {"message": "Not Found"}

    found = get_contents(OWNER, REPO, "README.md", ref="presenter/x", token="ghp_w", fetch=fetch)
    assert found is None


def test_get_contents_raises_on_unreachable() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        get_contents(OWNER, REPO, "README.md", ref="main", token="ghp_w", fetch=fetch)


def test_put_contents_creates_a_new_file_with_no_sha() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={"content": {"sha": "newfilesha"}, "commit": {"sha": "newcommitsha"}},
    )
    outcome = put_contents(
        OWNER,
        REPO,
        "README.md",
        branch="presenter/readme-update",
        message="Update README via repository-presenter",
        text="# New\n",
        sha=None,
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/contents/README.md"
    assert token == "ghp_w"
    assert "sha" not in payload
    assert base64.b64decode(payload["content"]).decode("utf-8") == "# New\n"
    assert outcome.content_sha == "newfilesha"
    assert outcome.commit_sha == "newcommitsha"


def test_put_contents_updates_an_existing_file_with_its_sha() -> None:
    write = _RecordingWrite(
        status_code=200,
        body={"content": {"sha": "updatedsha"}, "commit": {"sha": "updatedcommit"}},
    )
    put_contents(
        OWNER,
        REPO,
        "README.md",
        branch="presenter/readme-update",
        message="m",
        text="# Updated\n",
        sha="oldsha",
        token="ghp_w",
        write=write,
    )
    assert write.calls[0][2]["sha"] == "oldsha"


def test_put_contents_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        put_contents(
            OWNER,
            REPO,
            "README.md",
            branch="b",
            message="m",
            text="t",
            sha=None,
            token="",
            write=write,
        )
    assert write.calls == []


def test_put_contents_raises_on_unreachable_the_lost_response_shape() -> None:
    """``components/propose/effect.py`` pattern-matches "unreachable" in this exact message to
    decide a response was lost (eligible for reconciliation) rather than hard-rejected."""

    def write(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        return -1, "ReadTimeout: the server did not respond"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        put_contents(
            OWNER,
            REPO,
            "README.md",
            branch="b",
            message="m",
            text="t",
            sha=None,
            token="ghp_w",
            write=write,
        )


def test_put_contents_raises_on_a_non_2xx_status() -> None:
    write = _RecordingWrite(status_code=409, body={"message": "sha does not match"})
    with pytest.raises(RepositoryMetadataError):
        put_contents(
            OWNER,
            REPO,
            "README.md",
            branch="b",
            message="m",
            text="t",
            sha="stalesha",
            token="ghp_w",
            write=write,
        )


def test_find_open_pull_request_returns_the_first_match() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        assert url == (
            f"{API_ROOT}/repos/{OWNER}/{REPO}/pulls?head={OWNER}:presenter/readme-update&state=open"
        )
        return 200, [
            {
                "number": 9,
                "html_url": "https://github.com/x/y/pull/9",
                "title": "Update README",
                "body": "body text",
            }
        ]

    found = find_open_pull_request(
        OWNER, REPO, head_branch="presenter/readme-update", token="ghp_w", fetch=fetch
    )
    assert found is not None
    assert found.number == 9
    assert found.title == "Update README"
    assert found.body == "body text"


def test_find_open_pull_request_returns_none_when_no_pr_is_open() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, []

    assert (
        find_open_pull_request(
            OWNER, REPO, head_branch="presenter/readme-update", token="ghp_w", fetch=fetch
        )
        is None
    )


def test_find_open_pull_request_raises_on_unreachable() -> None:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return -1, "ConnectError"

    with pytest.raises(RepositoryMetadataError, match="unreachable"):
        find_open_pull_request(
            OWNER, REPO, head_branch="presenter/readme-update", token="ghp_w", fetch=fetch
        )


def test_create_pull_request_posts_head_base_title_and_body() -> None:
    write = _RecordingWrite(
        status_code=201,
        body={
            "number": 11,
            "html_url": "https://github.com/x/y/pull/11",
            "title": "Update README",
            "body": "body",
        },
    )
    created = create_pull_request(
        OWNER,
        REPO,
        title="Update README",
        body="body",
        head="presenter/readme-update",
        base="main",
        token="ghp_w",
        write=write,
    )
    assert len(write.calls) == 1
    url, _token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/pulls"
    assert payload == {
        "title": "Update README",
        "body": "body",
        "head": "presenter/readme-update",
        "base": "main",
    }
    assert created.number == 11
    assert created.url == "https://github.com/x/y/pull/11"


def test_create_pull_request_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        create_pull_request(
            OWNER, REPO, title="t", body="b", head="h", base="main", token="", write=write
        )
    assert write.calls == []


def test_update_pull_request_patches_title_and_body() -> None:
    write = _RecordingWrite(
        status_code=200,
        body={"html_url": "https://github.com/x/y/pull/11", "title": "New title", "body": "new"},
    )
    updated = update_pull_request(
        OWNER, REPO, 11, title="New title", body="new", token="ghp_w", write=write
    )
    assert len(write.calls) == 1
    url, _token, payload = write.calls[0]
    assert url == f"{API_ROOT}/repos/{OWNER}/{REPO}/pulls/11"
    assert payload == {"title": "New title", "body": "new"}
    assert updated.number == 11
    assert updated.title == "New title"


def test_update_pull_request_refuses_without_a_token_no_call_made() -> None:
    write = _RecordingWrite()
    with pytest.raises(RepositoryMetadataError):
        update_pull_request(OWNER, REPO, 11, title="t", body="b", token="", write=write)
    assert write.calls == []


def test_update_pull_request_raises_on_a_non_200_status() -> None:
    write = _RecordingWrite(status_code=404, body={"message": "Not Found"})
    with pytest.raises(RepositoryMetadataError):
        update_pull_request(OWNER, REPO, 11, title="t", body="b", token="ghp_w", write=write)
