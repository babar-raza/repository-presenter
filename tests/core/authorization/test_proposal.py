"""The typed README-proposal authorization payload (G6-W02): assembly is a plain constructor,
validation is the real gate, re-checked against the exact effect about to be attempted."""

from __future__ import annotations

from repository_presenter.core.authorization.proposal import (
    CURRENT_POLICY_VERSION,
    PR_INTENT_README_PROPOSAL,
    AuthorizationDecision,
    ProposalAuthorization,
    authorize_proposal,
    validate_authorization,
)

REPO = "babar-raza/disposable-target"
CANDIDATE_HASH = "sha256:aaaa"
SOURCE_REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
BRANCH = "repository-presenter/readme-update"


def _authorization(**overrides: object) -> ProposalAuthorization:
    fields: dict[str, object] = {
        "repository": REPO,
        "candidate_hash": CANDIDATE_HASH,
        "source_revision": SOURCE_REVISION,
        "branch": BRANCH,
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
