"""Phase 2 apply: gated PATCH/PUT. Every test injects a fake write function - no test here, or
anywhere in this suite, makes a live GitHub call. The point of this file is the gate itself: an
unauthorized or under-credentialed call must reach neither ``patch`` nor ``put``, and a live-state
drift must abort the whole write rather than partially applying a stale diff."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.metadata.apply import (
    AUTHORIZATION_VARIABLE,
    ApplyResult,
    FieldOutcome,
    apply_metadata_diff,
    write_authorized,
)
from repository_presenter.components.metadata.proposal import (
    ProposedRepoMetadata,
    RepoMetadataDiff,
)
from repository_presenter.core.github.client import ObservedRepository

REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def _proposed(
    *, description: str | None = "New description.", homepage: str | None = "https://new/"
) -> ProposedRepoMetadata:
    return ProposedRepoMetadata(
        description=description,
        description_source="sealed README opening paragraph, first sentence"
        if description
        else None,
        topics=("python", "3d", "mit", "aspose", "foss"),
        topics_sources=("identity:platform", "identity:family", "license:spdx"),
        homepage=homepage,
        homepage_source="link_target:product.homepage" if homepage else None,
    )


def _diff(
    *,
    description_changed: bool = True,
    homepage_changed: bool = True,
    topics_changed: bool = True,
    observed_description: str | None = "Old description.",
    observed_homepage: str | None = "https://old/",
    observed_topics: tuple[str, ...] = (),
) -> RepoMetadataDiff:
    proposed = _proposed(
        description="New description." if description_changed else observed_description,
        homepage="https://new/" if homepage_changed else observed_homepage,
    )
    if not topics_changed:
        proposed = ProposedRepoMetadata(
            description=proposed.description,
            description_source=proposed.description_source,
            topics=observed_topics,
            topics_sources=proposed.topics_sources,
            homepage=proposed.homepage,
            homepage_source=proposed.homepage_source,
        )
    return RepoMetadataDiff(
        repository=REPO,
        proposed=proposed,
        observed_description=observed_description,
        observed_homepage=observed_homepage,
        observed_topics=observed_topics,
        description_changed=description_changed,
        homepage_changed=homepage_changed,
        topics_changed=topics_changed,
    )


def _observed(
    *,
    description: str | None = "Old description.",
    homepage: str | None = "https://old/",
    topics: tuple[str, ...] = (),
) -> ObservedRepository:
    return ObservedRepository(
        repository=REPO,
        description=description,
        homepage=homepage,
        topics=topics,
        observed_at="2026-09-26T00:00:00Z",
    )


class _RecordingWrite:
    """A fake ``WriteFn`` that records every call and returns a fixed response."""

    def __init__(self, status_code: int = 200, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


# ---------------------------------------------------------------------------
# write_authorized
# ---------------------------------------------------------------------------


def test_write_authorized_true_for_1_true_or_yes_case_insensitive() -> None:
    for value in ("1", "true", "True", "TRUE", "yes", "Yes"):
        assert write_authorized({AUTHORIZATION_VARIABLE: value}) is True


def test_write_authorized_false_when_absent_empty_or_any_other_value() -> None:
    assert write_authorized({}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: ""}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "0"}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "false"}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "GH_TOKEN"}) is False


def test_write_authorized_ignores_credential_looking_variables() -> None:
    """A write-scoped token being present must never itself flip authorization on."""
    assert write_authorized({"GH_METADATA_WRITE_TOKEN": "ghp_realtoken1234567890"}) is False


# ---------------------------------------------------------------------------
# apply_metadata_diff: refused before any network call
# ---------------------------------------------------------------------------


def test_unauthorized_makes_no_write_call_at_all() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={},
        patch=patch,
        put=put,
    )
    assert patch.calls == []
    assert put.calls == []
    assert result.authorized is False
    assert result.wrote_anything is False
    for outcome in (result.description, result.homepage, result.topics):
        assert outcome.applied is False
        assert outcome.changed is True
        assert AUTHORIZATION_VARIABLE in outcome.reason


def test_authorized_but_no_token_makes_no_write_call() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token=None,
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert patch.calls == []
    assert put.calls == []
    assert result.authorized is True
    assert result.wrote_anything is False
    assert all("token" in o.reason for o in (result.description, result.homepage, result.topics))


def test_no_changes_makes_no_write_call_even_when_fully_authorized() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    unchanged = _diff(description_changed=False, homepage_changed=False, topics_changed=False)
    result = apply_metadata_diff(
        unchanged,
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert patch.calls == []
    assert put.calls == []
    assert result.wrote_anything is False
    assert all(o.changed is False for o in (result.description, result.homepage, result.topics))


# ---------------------------------------------------------------------------
# apply_metadata_diff: the authorized write path
# ---------------------------------------------------------------------------


def test_authorized_write_patches_description_and_homepage_together_and_puts_topics() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert len(patch.calls) == 1
    url, token, payload = patch.calls[0]
    assert url == "https://api.github.com/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert token == "ghp_write"
    assert payload == {"description": "New description.", "homepage": "https://new/"}
    assert len(put.calls) == 1
    put_url, _put_token, put_payload = put.calls[0]
    assert put_url == (
        "https://api.github.com/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python/topics"
    )
    assert put_payload == {"names": ["python", "3d", "mit", "aspose", "foss"]}
    assert result.wrote_anything is True
    assert result.description == FieldOutcome("description", True, True, "written")
    assert result.homepage == FieldOutcome("homepage", True, True, "written")
    assert result.topics == FieldOutcome("topics", True, True, "written")


def test_only_the_changed_fields_are_written_one_field_changed() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    diff = _diff(homepage_changed=False, topics_changed=False)
    result = apply_metadata_diff(
        diff,
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert len(patch.calls) == 1
    assert patch.calls[0][2] == {"description": "New description."}
    assert put.calls == []
    assert result.description.applied is True
    assert result.homepage.changed is False
    assert result.homepage.applied is False
    assert result.topics.changed is False


def test_a_patch_failure_does_not_block_the_independent_topics_put() -> None:
    patch = _RecordingWrite(status_code=422, body={"message": "Validation failed"})
    put = _RecordingWrite(status_code=200)
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert result.description.applied is False
    assert "422" in result.description.reason
    assert result.homepage.applied is False
    assert "422" in result.homepage.reason
    assert result.topics.applied is True
    assert len(put.calls) == 1


def test_apply_never_raises_on_a_write_failure() -> None:
    patch = _RecordingWrite(status_code=500, body="server error")
    put = _RecordingWrite(status_code=500, body="server error")
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert result.wrote_anything is False


# ---------------------------------------------------------------------------
# apply_metadata_diff: recheck-before-effect (drift)
# ---------------------------------------------------------------------------


def test_live_drift_since_capture_aborts_the_whole_write_no_partial_apply() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    # Topics moved on GitHub since Phase 0 captured this diff's baseline.
    live = _observed(topics=("something-else",))
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
        refetch=lambda: live,
    )
    assert patch.calls == []
    assert put.calls == []
    assert result.wrote_anything is False
    assert "topics" in result.description.reason  # abort-all names every drifted field
    assert "re-run metadata capture" in result.description.reason


def test_no_drift_since_capture_proceeds_to_write() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    live = _observed()  # identical to the diff's own baseline observation
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
        refetch=lambda: live,
    )
    assert result.wrote_anything is True
    assert len(patch.calls) == 1
    assert len(put.calls) == 1


def test_drift_check_ignores_a_field_the_diff_never_proposed_changing() -> None:
    """Only fields the diff intends to change are compared against the live re-fetch - an
    unrelated live-side change to a field this diff leaves alone must never block the write."""
    patch = _RecordingWrite()
    put = _RecordingWrite()
    diff = _diff(homepage_changed=False)
    # Homepage differs live too, but this diff never proposed touching it - must not be treated
    # as drift.
    live = _observed(homepage="https://something-unrelated-changed/")
    result = apply_metadata_diff(
        diff,
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
        refetch=lambda: live,
    )
    assert result.wrote_anything is True
    assert len(patch.calls) == 1


# ---------------------------------------------------------------------------
# ApplyResult / FieldOutcome never leak the token
# ---------------------------------------------------------------------------


def test_apply_result_never_echoes_the_token() -> None:
    patch = _RecordingWrite()
    put = _RecordingWrite()
    result = apply_metadata_diff(
        _diff(),
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Python",
        token="ghp_super_secret_write_token",
        environment={AUTHORIZATION_VARIABLE: "1"},
        patch=patch,
        put=put,
    )
    assert isinstance(result, ApplyResult)
    dump = repr(result)
    assert "ghp_super_secret_write_token" not in dump
