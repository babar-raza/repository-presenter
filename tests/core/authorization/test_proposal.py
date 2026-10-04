"""The typed README-proposal authorization payload (G6-W02): assembly is a plain constructor,
validation is the real gate, re-checked against the exact effect about to be attempted."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    CURRENT_POLICY_VERSION,
    PR_INTENT_README_PROPOSAL,
    AuthorizationDecision,
    ProposalAuthorization,
    authorize_proposal,
    load_authorization_file,
    record_filename,
    render_record,
    validate_authorization,
)
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError

REPO = "babar-raza/disposable-target"
CANDIDATE_HASH = "sha256:aaaa"
SOURCE_REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
BRANCH = "repository-presenter/readme-update"
BASE_BRANCH = "main"


def _authorization(**overrides: object) -> ProposalAuthorization:
    fields: dict[str, object] = {
        "repository": REPO,
        "candidate_hash": CANDIDATE_HASH,
        "source_revision": SOURCE_REVISION,
        "base_branch": BASE_BRANCH,
        "branch": BRANCH,
        "approver": "a-person",
        "issued_at": "2026-10-01T00:00:00Z",
        "expires_at": "2026-10-01T01:00:00Z",
    }
    fields.update(overrides)
    return authorize_proposal(**fields)  # type: ignore[arg-type]


def _validate(
    authorization: ProposalAuthorization, *, now: str = "2026-10-01T00:30:00Z"
) -> AuthorizationDecision:
    return validate_authorization(
        authorization,
        now=now,
        expected_repository=REPO,
        expected_candidate_hash=CANDIDATE_HASH,
        expected_source_revision=SOURCE_REVISION,
        expected_base_branch=BASE_BRANCH,
        expected_branch=BRANCH,
    )


def test_authorize_proposal_assembles_the_given_fields_with_the_current_defaults() -> None:
    authorization = _authorization()
    assert authorization.repository == REPO
    assert authorization.candidate_hash == CANDIDATE_HASH
    assert authorization.source_revision == SOURCE_REVISION
    assert authorization.branch == BRANCH
    assert authorization.pr_intent == PR_INTENT_README_PROPOSAL
    assert authorization.policy_version == CURRENT_POLICY_VERSION
    assert authorization.schema_version == 1


def test_a_matching_authorization_within_its_window_is_granted() -> None:
    decision = _validate(_authorization())
    assert decision.granted is True
    assert decision.reason == "authorized"


def test_a_different_repository_is_denied() -> None:
    decision = _validate(_authorization(repository="other-org/other-repo"))
    assert decision.granted is False
    assert "other-org/other-repo" in decision.reason
    assert REPO in decision.reason


def test_a_stale_policy_version_is_denied() -> None:
    decision = _validate(_authorization(policy_version="0"))
    assert decision.granted is False
    assert "policy_version" in decision.reason
    assert "stale" in decision.reason


def test_a_mismatched_pr_intent_is_denied() -> None:
    decision = _validate(_authorization(pr_intent="SOMETHING_ELSE"))
    assert decision.granted is False
    assert "pr_intent" in decision.reason


def test_a_different_branch_is_denied() -> None:
    decision = _validate(_authorization(branch="some-other-branch"))
    assert decision.granted is False
    assert "branch" in decision.reason


def test_a_candidate_hash_mismatch_is_denied_the_sealed_bundle_moved() -> None:
    decision = _validate(_authorization(candidate_hash="sha256:bbbb"))
    assert decision.granted is False
    assert "candidate_hash" in decision.reason


def test_a_source_revision_mismatch_is_denied() -> None:
    decision = _validate(_authorization(source_revision="0" * 40))
    assert decision.granted is False
    assert "source_revision" in decision.reason


def test_an_expired_authorization_is_denied() -> None:
    authorization = _authorization(expires_at="2026-10-01T00:00:00Z")
    decision = _validate(authorization, now="2026-10-01T00:00:01Z")
    assert decision.granted is False
    assert "expired" in decision.reason


def test_an_authorization_exactly_at_its_expiry_instant_is_denied_boundary_is_inclusive() -> None:
    authorization = _authorization(expires_at="2026-10-01T00:30:00Z")
    decision = _validate(authorization, now="2026-10-01T00:30:00Z")
    assert decision.granted is False


def test_an_authorization_one_second_before_expiry_is_still_granted() -> None:
    authorization = _authorization(expires_at="2026-10-01T00:30:00Z")
    decision = _validate(authorization, now="2026-10-01T00:29:59Z")
    assert decision.granted is True


def test_the_first_failing_check_wins_repository_before_policy_version() -> None:
    """Field-order documentation as a test: a payload wrong in multiple ways still reports one
    reason, deterministically, rather than a list that could silently drop a finding."""
    authorization = _authorization(repository="other/other", policy_version="0")
    decision = _validate(authorization)
    assert decision.granted is False
    assert "other/other" in decision.reason


# ---------------------------------------------------------------------------
# the persisted record: base branch, window, typed codes, and loading from disk
# ---------------------------------------------------------------------------


def test_a_different_base_branch_is_denied() -> None:
    decision = _validate(_authorization(base_branch="develop"))
    assert decision.granted is False
    assert decision.code is Refusal.AUTHORIZATION_MISMATCH
    assert "base branch" in decision.reason


def test_an_expired_authorization_carries_the_expired_code() -> None:
    decision = _validate(_authorization(), now="2026-10-01T02:00:00Z")
    assert decision.granted is False
    assert decision.code is Refusal.AUTHORIZATION_EXPIRED


def test_an_authorization_not_yet_valid_is_denied() -> None:
    decision = _validate(_authorization(), now="2026-09-30T23:59:59Z")
    assert decision.granted is False
    assert decision.code is Refusal.AUTHORIZATION_MISMATCH
    assert "not yet valid" in decision.reason


def test_a_standing_authorization_beyond_the_maximum_lifetime_is_denied() -> None:
    decision = _validate(_authorization(expires_at="2027-10-01T00:00:00Z"))
    assert decision.granted is False
    assert "lifetime" in decision.reason


def test_an_empty_window_is_denied() -> None:
    authorization = _authorization(
        issued_at="2026-10-01T00:40:00Z", expires_at="2026-10-01T00:40:00Z"
    )
    decision = _validate(authorization, now="2026-10-01T00:30:00Z")
    assert decision.granted is False


def test_every_decision_that_refuses_names_a_typed_code() -> None:
    for overrides in (
        {"repository": "other/other"},
        {"policy_version": "0"},
        {"pr_intent": "X"},
        {"branch": "b"},
        {"candidate_hash": "z"},
        {"source_revision": "z"},
    ):
        decision = _validate(_authorization(**overrides))
        assert decision.granted is False
        assert decision.code is Refusal.AUTHORIZATION_MISMATCH
    assert _validate(_authorization()).code is None


def test_a_record_round_trips_through_its_canonical_bytes(tmp_path: Path) -> None:
    authorization = _authorization(supersedes_prs=(3, 9))
    path = tmp_path / "record.json"
    path.write_text(render_record(authorization), encoding="utf-8")
    assert load_authorization_file(path) == authorization


def test_the_record_file_name_names_the_repository_and_candidate() -> None:
    assert record_filename(REPO, "ab" * 32) == "babar-raza__disposable-target__abababababab.json"


def test_no_record_path_is_the_missing_code() -> None:
    with pytest.raises(WriteRefusedError) as info:
        load_authorization_file(None)
    assert info.value.code is Refusal.AUTHORIZATION_MISSING
    assert info.value.exit_code == 3


def test_a_record_that_does_not_exist_is_the_missing_code(tmp_path: Path) -> None:
    with pytest.raises(WriteRefusedError) as info:
        load_authorization_file(tmp_path / "absent.json")
    assert info.value.code is Refusal.AUTHORIZATION_MISSING


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        "{}",
        '{"repository": "x"}',
        # an unknown field is refused, so a record cannot smuggle in terms this code never reads
        render_record(_authorization()).replace('"approver"', '"surprise": 1, "approver"'),
        # an empty approver is no approver
        render_record(_authorization()).replace('"a-person"', '""'),
        # a time that is not the canonical UTC form cannot be compared as a string
        render_record(_authorization()).replace("2026-10-01T01:00:00Z", "tomorrow"),
    ],
)
def test_a_malformed_record_is_the_unreadable_code(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(WriteRefusedError) as info:
        load_authorization_file(path)
    assert info.value.code is Refusal.AUTHORIZATION_UNREADABLE


def test_the_record_directory_lives_under_ops() -> None:
    assert AUTHORIZATION_DIRNAME.as_posix() == "ops/proposal-authorizations"
