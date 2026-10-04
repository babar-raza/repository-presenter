"""Phase 3: the gated write half of upstream-defect issue management - file a ``HANDOFF_PENDING``
handoff as a real GitHub issue, and close a ``FILED`` handoff once its own check no longer fires.

`AGENTS.md` "Security and Effects" requires every target write to be gated by the owner's explicit
authorization, never inferred from a credential's presence or scope. Every one of these must hold
before this module ever calls ``core/github/client.py``'s ``create_issue`` (``close_issue`` is
gated by 1 and 2 only - it can only close an issue this system recorded as filed):

1. ``write_authorized(environment)`` - the kill switch. The owner-controlled repository variable
   ``REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`` must be set to a truthy value. It can disable
   every write by being unset or changed; it can never, alone, authorize one.
2. A write-scoped token is actually supplied (``GH_ISSUES_WRITE_TOKEN`` - never the read-only
   ``GH_TOKEN``, a distinct App installation token scoped to one target repository).
3. A per-handoff owner approval record (``approval.py``: ``ops/issue_approvals/<handoff-id>.json``)
   exists for this exact handoff, names its target repository, matches the handoff's current
   evidence digest, and has not expired. A changed handoff, or a missing or expired record, is
   refused before any network call.
4. The target is the handoff's own recorded repository: it is a well-formed ``owner/name``, it is
   the repository the approval names, and (when the caller states one) it is the repository the
   caller is operating on.

Three further guards hold even with every gate open:

- Duplicate filing is refused twice over. A handoff whose ``status`` is not ``HANDOFF_PENDING`` is
  never filed, and - because a scheduled run starts from a fresh checkout whose artifact may still
  read ``HANDOFF_PENDING`` - the target repository itself is searched for an issue whose body
  carries this defect's fingerprint marker (``fingerprint_marker``). Such an issue is recorded as
  the handoff's ``issue_ref`` and never re-filed. An inconclusive search refuses the filing rather
  than assuming absence (``AGENTS.md``: "reconcile uncertain remote effects before retrying").
- The defect is rechecked against the repository's current state immediately before the write
  (``AGENTS.md`` "Recheck upstream revision immediately before an effect"); a stale or inconclusive
  finding is never turned into a live issue.
- Closing requires a ``FILED`` handoff, a recheck that positively says the defect no longer fires,
  and a redetection-proposed ``RESOLVED_UPSTREAM`` with its close reason. It never closes an issue
  this system did not file (the handoff's own ``issue_ref``), and never on an inconclusive check.

Each function here reports what it did or would do and never raises for an ordinary refusal, a
network failure, or a GitHub rejection - a failed effect for one handoff is returned to the caller,
which keeps processing the others.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from repository_presenter.components.issues.approval import (
    ApprovalStore,
    evidence_digest,
    handoff_id,
    is_valid_repository,
    verify_approval,
)
from repository_presenter.components.issues.model import CloseReason, Handoff, IssueRef
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    WriteFn,
    close_issue,
    create_issue,
    default_patch,
    default_post,
)

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

_NOT_AUTHORIZED_REASON = (
    f"kill switch engaged: {AUTHORIZATION_VARIABLE} is not 1, so every write is disabled "
    "(setting it never authorizes a filing by itself - each handoff also needs its own approval "
    "record)"
)
_NO_APPROVAL_SOURCE_REASON = "no approval record source configured - refusing to file"
_NO_TOKEN_REASON = "no write-scoped token available (GH_ISSUES_WRITE_TOKEN, never GH_TOKEN)"

# GitHub's own state_reason values for a closed issue; CloseReason ("not planned") is ours.
_STATE_REASON = {"completed": "completed", "not planned": "not_planned"}


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only while the owner's kill switch ``AUTHORIZATION_VARIABLE`` is set to a truthy
    value. Absence, an empty string, or any other value disables writes - fail closed. A ``True``
    here is necessary and never sufficient: filing also needs the handoff's own approval record."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


def fingerprint_marker(defect_fingerprint: str) -> str:
    """The hidden marker every filed body carries, so the target repository itself records which
    defect an issue is for. It is exactly what ``find_issue_with_marker`` searches for."""
    return f"<!-- repository-presenter-defect: {defect_fingerprint} -->"


def body_with_marker(handoff: Handoff) -> str:
    """The suggested body, with the fingerprint marker appended once when a handoff does not
    already carry it."""
    marker = fingerprint_marker(handoff.defect_fingerprint)
    body = handoff.suggested_issue_body
    if marker in body:
        return body
    return f"{body.rstrip()}\n\n{marker}\n"


def _split(repository: str) -> tuple[str, str]:
    owner, name = repository.split("/", 1)
    return owner, name


@dataclass(frozen=True)
class FileResult:
    """The outcome of one ``file_handoff`` call.

    ``filed`` is ``True`` only when a real ``POST /repos/{owner}/{repo}/issues`` call succeeded and
    returned an issue GitHub actually created. ``issue_ref`` is also set when an existing upstream
    issue was recognised as this defect's (``filed`` stays ``False``): the caller then records the
    handoff as ``FILED`` without another write. ``error`` marks an authorized write that GitHub
    rejected or could not be reached; every other non-filing is a refusal named in ``reason``.
    """

    repository: str
    defect_fingerprint: str
    authorized: bool
    filed: bool
    reason: str
    issue_ref: IssueRef | None
    error: bool = False


@dataclass(frozen=True)
class FilingPlan:
    """What filing one handoff would do, decided by read-only checks alone."""

    repository: str
    defect_fingerprint: str
    title: str
    refusal: str | None
    already_filed: IssueRef | None
    handoff_id: str = ""
    evidence_digest: str = ""
    approval_refused: bool = False

    @property
    def ready(self) -> bool:
        return self.refusal is None and self.already_filed is None


def _not_pending_reason(status: str) -> str:
    return (
        f"status is {status!r}, not HANDOFF_PENDING - only a pending handoff may be filed "
        "(this is the duplicate-filing guard: an already-FILED handoff is never re-filed)"
    )


def _target_refusal(handoff: Handoff, expected_repository: str | None) -> str | None:
    if not is_valid_repository(handoff.repository):
        return f"handoff target {handoff.repository!r} is not a valid owner/name"
    if (
        expected_repository is not None
        and handoff.repository.casefold() != expected_repository.casefold()
    ):
        return (
            f"target mismatch: handoff targets {handoff.repository}, but this run operates on "
            f"{expected_repository} - refusing to file outside the recorded target"
        )
    return None


def plan_filing(
    handoff: Handoff,
    *,
    existing: Callable[[], IssueRef | None] | None = None,
    recheck: Callable[[], RedetectionResult] | None = None,
    approvals: ApprovalStore | None = None,
    now: Callable[[], datetime] | None = None,
    expected_repository: str | None = None,
) -> FilingPlan:
    """Decide whether ``handoff`` would be filed, using only read calls.

    The target and the owner's per-handoff approval record are checked first, from committed
    files alone, so a handoff nobody approved never causes a network call. ``approvals`` is
    required: a plan with no approval source is a refusal.

    ``existing`` searches the target for an issue already carrying this fingerprint; ``recheck``
    re-runs the handoff's own check at the current revision. Both may raise
    :class:`RepositoryMetadataError`, which is reported as an inconclusive refusal, never assumed
    away. Neither is consulted for a handoff that is not ``HANDOFF_PENDING``.
    """

    def _plan(
        refusal: str | None, already: IssueRef | None = None, *, refused: bool = False
    ) -> FilingPlan:
        return FilingPlan(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            title=handoff.suggested_issue_title,
            refusal=refusal,
            already_filed=already,
            handoff_id=handoff_id(handoff) if is_valid_repository(handoff.repository) else "",
            evidence_digest=evidence_digest(handoff),
            approval_refused=refused,
        )

    if handoff.status != "HANDOFF_PENDING":
        return _plan(_not_pending_reason(handoff.status))

    target_refusal = _target_refusal(handoff, expected_repository)
    if target_refusal is not None:
        return _plan(target_refusal)

    if approvals is None:
        return _plan(_NO_APPROVAL_SOURCE_REASON, refused=True)
    verdict = verify_approval(handoff, approvals, now=now)
    if not verdict.approved:
        return _plan(verdict.reason, refused=True)

    if existing is not None:
        try:
            found = existing()
        except RepositoryMetadataError as exc:
            return _plan(
                f"upstream lookup inconclusive ({exc}) - refusing to file without proof that "
                "no issue for this defect exists"
            )
        if found is not None:
            return _plan(None, already=found)

    if recheck is not None:
        result = recheck()
        if result.still_fires is False:
            return _plan(
                "recheck: this handoff's own triggering_check no longer fires at the "
                f"repository's current state ({result.note}) - refusing to file a stale finding"
            )
        if result.still_fires is None:
            return _plan(
                f"recheck: inconclusive ({result.note}) - refusing to file without a fresh "
                "confirmation that the defect still fires"
            )
    return _plan(None)


def file_handoff(
    handoff: Handoff,
    *,
    token: str | None,
    environment: Mapping[str, str],
    create: WriteFn = default_post,
    existing: Callable[[], IssueRef | None] | None = None,
    recheck: Callable[[], RedetectionResult] | None = None,
    approvals: ApprovalStore | None = None,
    now: Callable[[], datetime] | None = None,
    expected_repository: str | None = None,
) -> FileResult:
    """File ``handoff`` as a real GitHub issue - but only past every gate in this module's own
    docstring. Every early return below makes no network call at all."""

    def _refuse(authorized: bool, reason: str, *, error: bool = False) -> FileResult:
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=authorized,
            filed=False,
            reason=reason,
            issue_ref=None,
            error=error,
        )

    if not write_authorized(environment):
        return _refuse(False, _NOT_AUTHORIZED_REASON)

    if not token:
        return _refuse(True, _NO_TOKEN_REASON)

    plan = plan_filing(
        handoff,
        existing=existing,
        recheck=recheck,
        approvals=approvals,
        now=now,
        expected_repository=expected_repository,
    )
    if plan.already_filed is not None:
        found = plan.already_filed
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=True,
            filed=False,
            reason=(
                f"already filed upstream as #{found.number} ({found.url}) - recorded, not re-filed"
            ),
            issue_ref=found,
        )
    if plan.refusal is not None:
        return _refuse(True, plan.refusal)

    owner, name = _split(handoff.repository)
    try:
        created = create_issue(
            owner,
            name,
            title=handoff.suggested_issue_title,
            body=body_with_marker(handoff),
            token=token,
            write=create,
        )
    except RepositoryMetadataError as exc:
        return _refuse(True, str(exc), error=True)

    return FileResult(
        repository=handoff.repository,
        defect_fingerprint=handoff.defect_fingerprint,
        authorized=True,
        filed=True,
        reason="filed",
        issue_ref=IssueRef(number=created.number, url=created.url),
    )


@dataclass(frozen=True)
class CloseResult:
    """The outcome of one ``close_handoff`` call. ``closed`` is ``True`` only after GitHub answered
    HTTP 200 for the ``PATCH`` that closed the issue this handoff points to."""

    repository: str
    defect_fingerprint: str
    authorized: bool
    closed: bool
    reason: str
    close_reason: CloseReason | None
    error: bool = False


def plan_close(handoff: Handoff, result: RedetectionResult) -> str | None:
    """``None`` when ``handoff`` may be closed on ``result``; otherwise the refusal reason. Pure:
    no network call. Only a ``FILED`` handoff with an ``issue_ref``, a positive
    ``still_fires is False`` recheck, and a redetection-proposed ``RESOLVED_UPSTREAM`` can close."""
    if handoff.status != "FILED" or handoff.issue_ref is None:
        return (
            f"status is {handoff.status!r} with no filed issue - only an issue this system filed "
            "is ever closed"
        )
    if result.still_fires is None:
        return f"recheck inconclusive ({result.note}) - refusing to close"
    if result.still_fires:
        return f"the defect still fires ({result.note}) - nothing to close"
    if result.proposed_status != "RESOLVED_UPSTREAM" or result.proposed_close_reason is None:
        return "redetection proposes no resolution for this handoff"
    return None


def close_handoff(
    handoff: Handoff,
    result: RedetectionResult,
    *,
    token: str | None,
    environment: Mapping[str, str],
    write: WriteFn = default_patch,
) -> CloseResult:
    """Close the issue ``handoff`` filed, with the close reason ``result`` proposes - but only past
    the same authorization gate as filing, and only when ``plan_close`` agrees."""

    def _refuse(authorized: bool, reason: str, *, error: bool = False) -> CloseResult:
        return CloseResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=authorized,
            closed=False,
            reason=reason,
            close_reason=None,
            error=error,
        )

    if not write_authorized(environment):
        return _refuse(False, _NOT_AUTHORIZED_REASON)
    if not token:
        return _refuse(True, _NO_TOKEN_REASON)
    refusal = plan_close(handoff, result)
    if refusal is not None:
        return _refuse(True, refusal)
    assert handoff.issue_ref is not None and result.proposed_close_reason is not None
    owner, name = _split(handoff.repository)
    try:
        close_issue(
            owner,
            name,
            handoff.issue_ref.number,
            state_reason=_STATE_REASON[result.proposed_close_reason],
            token=token,
            write=write,
        )
    except RepositoryMetadataError as exc:
        return _refuse(True, str(exc), error=True)
    return CloseResult(
        repository=handoff.repository,
        defect_fingerprint=handoff.defect_fingerprint,
        authorized=True,
        closed=True,
        reason=f"closed #{handoff.issue_ref.number} as {result.proposed_close_reason!r}",
        close_reason=result.proposed_close_reason,
    )
