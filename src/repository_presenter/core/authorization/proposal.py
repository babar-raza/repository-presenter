"""The persisted, reviewable authorization record one README-proposal PR effect binds to (G6-W02;
``docs/EXECUTION_STATE_MACHINE.md`` G6 Work item 1; ``docs/STATE_MACHINE.md`` section 12's
effect-authorization machine; ``docs/DECISION_LOG.md`` 2026-10-05).

Authorization is independent of the proposal. It is a JSON file committed to this control
repository under ``ops/proposal-authorizations/`` by a person (the approver), reviewed like any
other change, and merged to ``main`` *before* the run that consumes it. The run reads it, checks
its git provenance (:mod:`repository_presenter.core.authorization.record_provenance`), and then
verifies every bound field against the exact candidate it is about to propose. Nothing in a
dispatching run's inputs can mint, extend, or alter it: a record created or edited during the run is
not an ancestor of the commit the run was triggered at, and is refused.

Bound fields (``docs/STATE_MACHINE.md`` section 12, the subset this effect uses): target repository,
candidate hash (the sha256 of the exact README text), source revision, base branch, presenter
branch, PR intent, policy version, approver, issue/expiry window, and an explicit re-proposal list.

``CURRENT_POLICY_VERSION`` is this project's single source of truth for what a currently-valid
authorization looks like: bump it when the policy changes (which fields it binds, what counts as
authorized) and every record minted against the old value stops validating.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError

CURRENT_POLICY_VERSION = "1"
PR_INTENT_README_PROPOSAL = "CREATE_OR_UPDATE_README_PROPOSAL"
AUTHORIZATION_DIRNAME = Path("ops") / "proposal-authorizations"
#: The longest an authorization may stay valid, issue to expiry. A standing authorization is not an
#: authorization of one exact effect.
MAX_LIFETIME = timedelta(days=7)
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ProposalAuthorization(BaseModel):
    """One exact, typed effect authorization - ``docs/STATE_MACHINE.md``'s ``AWAITING_
    AUTHORIZATION`` state made concrete, and the exact shape of the on-disk record. Every field is
    a plain scalar so the payload is reviewable evidence on its own."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    repository: str = Field(min_length=1)
    #: sha256 of the exact README text (``core/hashing.py::sha256_text``) this record approves.
    candidate_hash: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    pr_intent: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    approver: str = Field(min_length=1)
    issued_at: str = Field(pattern=r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
    expires_at: str = Field(pattern=r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
    #: Pull requests (by number) on the presenter branch that this record explicitly allows the
    #: effect to supersede with a new one. Empty means: never recreate after a merged/closed PR.
    supersedes_prs: tuple[StrictInt, ...] = ()


def authorize_proposal(
    *,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    base_branch: str,
    branch: str,
    approver: str,
    issued_at: str,
    expires_at: str,
    supersedes_prs: tuple[int, ...] = (),
    pr_intent: str = PR_INTENT_README_PROPOSAL,
    policy_version: str = CURRENT_POLICY_VERSION,
) -> ProposalAuthorization:
    """Assemble one record. A plain constructor: it checks the record's shape but not its
    meaning, so a test can build a deliberately stale or mismatched record. It is used to *draft*
    the record a person then reviews and commits (``cli.py``'s ``draft-proposal-authorization``);
    the gate is always :func:`validate_authorization`, run against the committed record
    immediately before an effect."""
    return ProposalAuthorization(
        repository=repository,
        candidate_hash=candidate_hash,
        source_revision=source_revision,
        base_branch=base_branch,
        branch=branch,
        pr_intent=pr_intent,
        policy_version=policy_version,
        approver=approver,
        issued_at=issued_at,
        expires_at=expires_at,
        supersedes_prs=supersedes_prs,
    )


def record_filename(repository: str, candidate_hash: str) -> str:
    """The canonical file name of the record for one exact candidate."""
    return f"{repository.replace('/', '__')}__{candidate_hash[:12]}.json"


def render_record(authorization: ProposalAuthorization) -> str:
    """The canonical on-disk bytes of a record (sorted keys, trailing newline) - what a person
    reviews in the pull request that introduces it."""
    return json.dumps(authorization.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_authorization_file(path: Path | None) -> ProposalAuthorization:
    """Parse the record at ``path``; raise :class:`WriteRefusedError` (typed) when it is missing,
    unreadable, or malformed. Provenance is checked separately by the caller."""
    if path is None:
        raise WriteRefusedError(
            Refusal.AUTHORIZATION_MISSING,
            "no authorization record supplied (--authorization-record): a proposal is never "
            "authorized by its own run",
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WriteRefusedError(
            Refusal.AUTHORIZATION_MISSING, f"authorization record not found: {path}"
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise WriteRefusedError(
            Refusal.AUTHORIZATION_UNREADABLE, f"authorization record unreadable: {path}: {exc}"
        ) from exc
    try:
        return ProposalAuthorization.model_validate_json(raw)
    except ValidationError as exc:
        raise WriteRefusedError(
            Refusal.AUTHORIZATION_UNREADABLE, f"authorization record is malformed: {path}: {exc}"
        ) from exc


@dataclass(frozen=True)
class AuthorizationDecision:
    """The outcome of one :func:`validate_authorization` call. ``granted`` is ``True`` only when
    every bound field matches the exact effect about to be attempted and the clock is inside the
    record's window; every other case is a refusal with a typed ``code`` and a ``reason``."""

    granted: bool
    reason: str
    code: Refusal | None = None


def _refuse(code: Refusal, reason: str) -> AuthorizationDecision:
    return AuthorizationDecision(False, reason, code)


def _parse_time(value: str) -> datetime:
    return datetime.strptime(value, _TIME_FORMAT).replace(tzinfo=UTC)


def validate_authorization(
    authorization: ProposalAuthorization,
    *,
    now: str,
    expected_repository: str,
    expected_candidate_hash: str,
    expected_source_revision: str,
    expected_base_branch: str,
    expected_branch: str,
    expected_pr_intent: str = PR_INTENT_README_PROPOSAL,
    expected_policy_version: str = CURRENT_POLICY_VERSION,
) -> AuthorizationDecision:
    """Re-check every bound field of ``authorization`` against the exact effect about to be
    attempted. ``now`` is an injected ISO-8601 UTC timestamp (``%Y-%m-%dT%H:%M:%SZ``) so expiry is
    tested deterministically; that format compares correctly as a plain string.

    The ``expected_*`` values must come from the candidate and the live target - never from the
    record itself - which is what makes the record an independent authority."""
    mismatch = Refusal.AUTHORIZATION_MISMATCH
    if authorization.repository != expected_repository:
        return _refuse(
            mismatch,
            f"authorization is bound to {authorization.repository!r}, not "
            f"{expected_repository!r} - never reusable across targets",
        )
    if authorization.policy_version != expected_policy_version:
        return _refuse(
            mismatch,
            f"authorization policy_version {authorization.policy_version!r} is stale (current "
            f"{expected_policy_version!r}) - the proposal policy changed since this authorization "
            "was minted; re-mint before proposing",
        )
    if authorization.pr_intent != expected_pr_intent:
        return _refuse(
            mismatch,
            f"authorization pr_intent {authorization.pr_intent!r} does not match the effect being "
            f"attempted ({expected_pr_intent!r})",
        )
    if authorization.branch != expected_branch:
        return _refuse(
            mismatch,
            f"authorization is bound to branch {authorization.branch!r}, not {expected_branch!r}",
        )
    if authorization.base_branch != expected_base_branch:
        return _refuse(
            mismatch,
            f"authorization is bound to base branch {authorization.base_branch!r}, not "
            f"{expected_base_branch!r}",
        )
    if authorization.candidate_hash != expected_candidate_hash:
        return _refuse(
            mismatch,
            "authorization candidate_hash does not match the candidate about to be proposed - the "
            "sealed bundle changed since this authorization was minted; re-mint",
        )
    if authorization.source_revision != expected_source_revision:
        return _refuse(
            mismatch,
            "authorization source_revision does not match the candidate's own recorded source "
            "revision; re-mint",
        )
    if now >= authorization.expires_at:
        return _refuse(
            Refusal.AUTHORIZATION_EXPIRED,
            f"authorization expired at {authorization.expires_at} (now {now})",
        )
    if authorization.issued_at >= authorization.expires_at:
        return _refuse(
            mismatch, "authorization window is empty: issued_at is not before expires_at"
        )
    if _parse_time(authorization.expires_at) - _parse_time(authorization.issued_at) > MAX_LIFETIME:
        return _refuse(
            mismatch,
            f"authorization lifetime exceeds {MAX_LIFETIME.days} days - a standing authorization "
            "is not an authorization of one exact effect",
        )
    if now < authorization.issued_at:
        return _refuse(
            mismatch, f"authorization is not yet valid (issued_at {authorization.issued_at})"
        )
    return AuthorizationDecision(True, "authorized")
