"""Read-only ``GET /repos/{owner}/{repo}``: a fake fetch only, no test here makes a live call."""

from __future__ import annotations

import pytest

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import API_ROOT, get_repository


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
