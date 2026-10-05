"""Per-issue owner approval for closing an upstream issue this system filed.

Closing an issue is a write to a product repository, so it is gated at least as strictly as filing
(`approval.py`, `AGENTS.md` "Security and Effects"). A filing approval never authorizes a close:
what the owner approved to post is not what they approved to resolve. The close approval is its
own committed file, ``ops/issue_close_approvals/<handoff-id>.json``::

    {
      "handoff_id": "aspose-html-foss__Aspose.HTML-FOSS-for-Python__<64 hex chars>",
      "repository": "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
      "issue_number": 42,
      "close_reason": "completed",
      "evidence_digest": "sha256:<64 hex chars>",
      "approver": "<the owner's GitHub login>",
      "approved_at": "2026-10-05T12:00:00Z",
      "expires_at": "2026-10-12T12:00:00Z"
    }

``verify_close_approval`` is fail-closed and re-runs at the moment of closing. The record must:

- name this handoff id and this handoff's own target repository;
- name the exact issue number the handoff recorded as filed (``issue_ref``), so approving the
  close of #7 can never close #8;
- name the same close reason (``completed`` or ``not_planned``, GitHub's own ``state_reason``
  values) the deterministic redetection proposes now - an approval for ``completed`` does not
  cover a ``not_planned`` close;
- carry the handoff's current evidence digest (``approval.evidence_digest``), so a changed handoff
  needs a fresh approval;
- be neither dated in the future nor expired, and span at most ``MAX_APPROVAL_LIFETIME``.

Records are read only by ``approval.GitApprovalStore`` (``directory=CLOSE_APPROVALS_RELATIVE_DIR``):
from a git ref of the control repository, never the working tree, and never a bot-authored file.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from repository_presenter.components.issues.approval import (
    BOT_MARKERS,
    CLOCK_SKEW,
    DIGEST_PATTERN,
    HANDOFF_ID_PATTERN,
    MAX_APPROVAL_LIFETIME,
    ApprovalError,
    ApprovalProvenanceError,
    ApprovalStore,
    evidence_digest,
    handoff_id,
    is_valid_repository,
    parse_timestamp,
)
from repository_presenter.components.issues.model import Handoff

CLOSE_APPROVALS_RELATIVE_DIR: Final = "ops/issue_close_approvals"
CLOSE_REASONS: Final = ("completed", "not_planned")

_FIELDS = (
    "handoff_id",
    "repository",
    "issue_number",
    "close_reason",
    "evidence_digest",
    "approver",
    "approved_at",
    "expires_at",
)


def close_approval_relative_path(identifier: str) -> str:
    return f"{CLOSE_APPROVALS_RELATIVE_DIR}/{identifier}.json"


@dataclass(frozen=True)
class CloseApprovalRecord:
    handoff_id: str
    repository: str
    issue_number: int
    close_reason: str
    evidence_digest: str
    approver: str
    approved_at: datetime
    expires_at: datetime


def parse_close_approval(text: str) -> CloseApprovalRecord:
    """Parse and structurally validate one close-approval file; raises :class:`ApprovalError`."""
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApprovalError(f"not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ApprovalError("top level must be a mapping")
    missing = [f for f in _FIELDS if f not in loaded]
    if missing:
        raise ApprovalError(f"missing field(s): {', '.join(missing)}")
    unknown = sorted(set(loaded) - set(_FIELDS))
    if unknown:
        raise ApprovalError(f"unknown field(s): {', '.join(str(u) for u in unknown)}")
    strings: dict[str, str] = {}
    for field in ("handoff_id", "repository", "close_reason", "evidence_digest", "approver"):
        value = loaded[field]
        if not isinstance(value, str) or not value.strip():
            raise ApprovalError(f"{field} must be a non-empty string")
        strings[field] = value.strip()
    number = loaded["issue_number"]
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ApprovalError("issue_number must be a positive integer")
    if not HANDOFF_ID_PATTERN.match(strings["handoff_id"]):
        raise ApprovalError("handoff_id is not <owner>__<name>__<64 hex>")
    if not is_valid_repository(strings["repository"]):
        raise ApprovalError("repository is not owner/name")
    if strings["close_reason"] not in CLOSE_REASONS:
        raise ApprovalError(f"close_reason must be one of {', '.join(CLOSE_REASONS)}")
    if not DIGEST_PATTERN.match(strings["evidence_digest"]):
        raise ApprovalError("evidence_digest is not sha256:<64 hex>")
    if any(marker in strings["approver"].lower() for marker in BOT_MARKERS):
        raise ApprovalError("approver must be a person, not a bot or workflow identity")
    approved_at = parse_timestamp(loaded["approved_at"], "approved_at")
    expires_at = parse_timestamp(loaded["expires_at"], "expires_at")
    if expires_at <= approved_at:
        raise ApprovalError("expires_at must be after approved_at")
    if expires_at - approved_at > MAX_APPROVAL_LIFETIME:
        raise ApprovalError(
            f"validity window exceeds {MAX_APPROVAL_LIFETIME.days} days - an approval is not a "
            "standing authorization"
        )
    return CloseApprovalRecord(
        handoff_id=strings["handoff_id"],
        repository=strings["repository"],
        issue_number=number,
        close_reason=strings["close_reason"],
        evidence_digest=strings["evidence_digest"],
        approver=strings["approver"],
        approved_at=approved_at,
        expires_at=expires_at,
    )


@dataclass(frozen=True)
class CloseApprovalVerdict:
    approved: bool
    reason: str
    record: CloseApprovalRecord | None = None


def verify_close_approval(
    handoff: Handoff,
    store: ApprovalStore,
    *,
    close_reason: str | None,
    now: Callable[[], datetime] | None = None,
) -> CloseApprovalVerdict:
    """Whether ``store`` holds a current, matching owner approval to close exactly the issue
    ``handoff`` recorded as filed, for ``close_reason`` (GitHub's ``completed``/``not_planned``).

    ``close_reason=None`` skips only the reason comparison - used by the pre-network count of
    handoffs a run may act on, before redetection has proposed a reason. Never use it to close."""
    identifier = handoff_id(handoff)
    expected_path = close_approval_relative_path(identifier)

    def deny(reason: str) -> CloseApprovalVerdict:
        return CloseApprovalVerdict(False, reason)

    if not is_valid_repository(handoff.repository):
        return deny(f"handoff target {handoff.repository!r} is not a valid owner/name")
    if handoff.issue_ref is None:
        return deny("the handoff records no filed issue to close")
    try:
        text = store.read(identifier)
    except ApprovalProvenanceError as exc:
        return deny(f"close approval provenance unverifiable ({exc})")
    if text is None:
        return deny(f"no close approval record ({expected_path} is not committed)")
    try:
        record = parse_close_approval(text)
    except ApprovalError as exc:
        return deny(f"close approval record malformed ({expected_path}): {exc}")
    if record.handoff_id != identifier:
        return deny(f"close approval names a different handoff ({record.handoff_id})")
    if record.repository.casefold() != handoff.repository.casefold():
        return deny(
            f"close approval target mismatch: approved for {record.repository}, handoff targets "
            f"{handoff.repository}"
        )
    if record.issue_number != handoff.issue_ref.number:
        return deny(
            f"close approval names issue #{record.issue_number}, but the handoff filed "
            f"#{handoff.issue_ref.number}"
        )
    if close_reason is not None and record.close_reason != close_reason:
        return deny(
            f"close approval is for reason {record.close_reason!r}, but the check proves "
            f"{close_reason!r}"
        )
    current = evidence_digest(handoff)
    if record.evidence_digest != current:
        return deny(
            "close approval digest mismatch: the handoff changed since it was approved "
            f"(approved {record.evidence_digest}, now {current}) - a fresh approval is required"
        )
    moment = (now or (lambda: datetime.now(UTC)))()
    if record.approved_at > moment + CLOCK_SKEW:
        return deny(f"close approval is dated in the future ({record.approved_at.isoformat()})")
    if moment >= record.expires_at:
        return deny(f"close approval expired at {record.expires_at.isoformat()}")
    return CloseApprovalVerdict(
        True,
        f"close approved by {record.approver} until {record.expires_at.isoformat()}",
        record,
    )
