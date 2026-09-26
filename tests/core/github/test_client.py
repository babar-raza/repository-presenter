"""The GitHub client: read (``GET``) and write (``PATCH``/``PUT``) - a fake fetch/write only, no
test here makes a live call. The write functions have no authorization check of their own (that
lives in ``components/metadata/apply.py``); these tests exercise only their own request/response
handling in isolation."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    API_ROOT,
    get_repository,
    replace_topics,
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
