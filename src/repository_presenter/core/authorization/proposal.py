"""The typed authorization payload one README-proposal PR effect binds to (G6-W02;
``docs/EXECUTION_STATE_MACHINE.md`` G6 Work item 1; ``docs/STATE_MACHINE.md`` section 12's
effect-authorization machine).

``docs/STATE_MACHINE.md`` section 12 names what an authorization binds: target repository,
candidate hash, source revision, branch and operation type, PR title/body hash, credential
provider, permission class, expiration, and publication policy version. This module implements the
subset G6-W02's own acceptance bar names explicitly - candidate hash, source revision, branch, PR
intent, policy version, and expiry - plus the target repository every one of those fields is
meaningless without.

Two deterministic functions, no GitHub call, no LLM call, nothing agentic:

- :func:`authorize_proposal` assembles the payload from already-verified evidence (the sealed
  candidate bundle's own README bytes and recorded source revision) - never from a model's output.
- :func:`validate_authorization` re-checks every bound field against the exact effect about to be
  attempted, immediately before ``components/propose/effect.py`` makes any GitHub call. A mismatch
  on any field - a stale policy version, a candidate that changed since authorization was minted, a
  different branch, an expired clock - denies the effect outright; nothing here ever "mostly"
  matches.

``CURRENT_POLICY_VERSION`` is this project's own single source of truth for what a currently-valid
authorization looks like, mirroring ``bundle/seal.py``'s ``CONTRACT_VERSION``/
``ACCEPTANCE_PROFILE_VERSION`` pattern: bump it deliberately when the proposal policy itself changes
(which fields it binds, what counts as authorized), and every authorization minted against the old
value stops validating - never silently accepted as "close enough".
"""

from __future__ import annotations

from dataclasses import dataclass

CURRENT_POLICY_VERSION = "1"
PR_INTENT_README_PROPOSAL = "CREATE_OR_UPDATE_README_PROPOSAL"


@dataclass(frozen=True)
class ProposalAuthorization:
    """One exact, typed effect request - ``docs/STATE_MACHINE.md``'s ``AWAITING_AUTHORIZATION``
    state made concrete. Every field is a plain string so the payload serializes to JSON byte-for-
    byte and is reviewable evidence on its own, never a live object only this process can inspect.
    """

    repository: str
    candidate_hash: str
    source_revision: str
    branch: str
    pr_intent: str
    policy_version: str
    issued_at: str
    expires_at: str
    schema_version: int = 1


def authorize_proposal(
    *,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    branch: str,
    issued_at: str,
    expires_at: str,
    pr_intent: str = PR_INTENT_README_PROPOSAL,
    policy_version: str = CURRENT_POLICY_VERSION,
) -> ProposalAuthorization:
    """Assemble one authorization payload from already-verified evidence.

    This performs no validation of its own - it is a plain constructor, kept separate from
    :func:`validate_authorization` so a test can construct a deliberately stale, mismatched, or
    expired payload directly, without needing a second code path that "almost" assembles one
    wrong. The real gate is always :func:`validate_authorization`, run again immediately before any
    effect, never trusted from assembly time alone (``AGENTS.md`` "Recheck upstream revision
    immediately before an effect" - the same discipline extended to the whole authorization, not
    only the source revision).
    """
    return ProposalAuthorization(
        repository=repository,
        candidate_hash=candidate_hash,
        source_revision=source_revision,
        branch=branch,
        pr_intent=pr_intent,
        policy_version=policy_version,
        issued_at=issued_at,
        expires_at=expires_at,
    )


@dataclass(frozen=True)
class AuthorizationDecision:
    """The outcome of one :func:`validate_authorization` call. ``granted`` is ``True`` only when
    every bound field matches the exact effect about to be attempted and the clock has not passed
    ``expires_at``; every other case is a refusal, named in ``reason``."""

    granted: bool
    reason: str


def validate_authorization(
    authorization: ProposalAuthorization,
    *,
    now: str,
    expected_repository: str,
    expected_candidate_hash: str,
    expected_source_revision: str,
    expected_branch: str,
    expected_pr_intent: str = PR_INTENT_README_PROPOSAL,
    expected_policy_version: str = CURRENT_POLICY_VERSION,
) -> AuthorizationDecision:
    """Re-check every bound field of ``authorization`` against the exact effect about to be
    attempted. ``now`` is an injected ISO-8601 UTC timestamp (``%Y-%m-%dT%H:%M:%SZ``, the same
    format ``core/github/client.py``'s own clock uses) so expiry is tested deterministically rather
    than against the real wall clock; that format compares correctly as a plain string, so no
    parsing is needed to decide whether ``now`` has passed ``expires_at``.
    """
    if authorization.repository != expected_repository:
        return AuthorizationDecision(
            False,
            f"authorization is bound to {authorization.repository!r}, not "
            f"{expected_repository!r} - never reusable across targets",
        )
    if authorization.policy_version != expected_policy_version:
        return AuthorizationDecision(
            False,
            f"authorization policy_version {authorization.policy_version!r} is stale (current "
            f"{expected_policy_version!r}) - the proposal policy changed since this authorization "
            "was minted; re-mint before proposing",
        )
    if authorization.pr_intent != expected_pr_intent:
        return AuthorizationDecision(
            False,
            f"authorization pr_intent {authorization.pr_intent!r} does not match the effect being "
            f"attempted ({expected_pr_intent!r})",
        )
    if authorization.branch != expected_branch:
        return AuthorizationDecision(
            False,
            f"authorization is bound to branch {authorization.branch!r}, not {expected_branch!r}",
        )
    if authorization.candidate_hash != expected_candidate_hash:
        return AuthorizationDecision(
            False,
            "authorization candidate_hash does not match the candidate about to be proposed - the "
            "sealed bundle changed since this authorization was minted; re-mint",
        )
    if authorization.source_revision != expected_source_revision:
        return AuthorizationDecision(
            False,
            "authorization source_revision does not match the candidate's own recorded source "
            "revision; re-mint",
        )
    if now >= authorization.expires_at:
        return AuthorizationDecision(
            False, f"authorization expired at {authorization.expires_at} (now {now})"
        )
    return AuthorizationDecision(True, "authorized")
