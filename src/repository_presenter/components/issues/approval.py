"""Per-handoff owner approval for filing an upstream issue.

`AGENTS.md` forbids writing to an Aspose product repository without the owner's explicit
authorization. A single repository variable cannot express that: once set it would authorize every
pending handoff, including ones the owner never read. So filing a handoff requires a persisted
approval record for that exact handoff, and the global variable is only a kill switch
(``file.py``: it can disable all writes and can never, alone, authorize one).

The record is a committed file, ``ops/issue_approvals/<handoff-id>.json``::

    {
      "handoff_id": "aspose-html-foss__Aspose.HTML-FOSS-for-Python__<64 hex chars>",
      "repository": "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
      "evidence_digest": "sha256:<64 hex chars>",
      "approver": "<the owner's GitHub login>",
      "approved_at": "2026-10-05T12:00:00Z",
      "expires_at": "2026-10-12T12:00:00Z"
    }

Verification (``verify_approval``) is fail-closed and re-runs at the moment of filing:

- the record exists and names this handoff id and this handoff's own target repository;
- ``evidence_digest`` equals the digest of the handoff as it is *now* (target, revision,
  fingerprint, triggering check, evidence, claim, title and body), so any change to what would be
  filed - or to where - voids the approval and needs a fresh one;
- it is neither dated in the future nor expired, and its validity window is at most
  ``MAX_APPROVAL_LIFETIME``, so an approval cannot become a standing authorization.

A record must not be creatable by the run that consumes it. ``GitApprovalStore`` therefore reads
the record only from a git ref (the commit the workflow run was triggered on), never from the
working tree, and refuses a record whose introducing commit was authored or committed by a bot
or whose history is a shallow clone (the introducing commit could not be identified). The
scheduled workflow additionally holds no ``contents: write`` grant and persists no checkout
credential, so no step of a run can push a record.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from repository_presenter.components.issues.model import Handoff
from repository_presenter.core.git_safety.git import run_git

APPROVALS_RELATIVE_DIR = "ops/issue_approvals"
MAX_APPROVAL_LIFETIME = timedelta(days=30)
CLOCK_SKEW = timedelta(minutes=5)

_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")
_HANDOFF_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*__[A-Za-z0-9_.-]+__[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]*$")
_BOT_MARKERS = ("[bot]", "github-actions")
_FIELDS = (
    "handoff_id",
    "repository",
    "evidence_digest",
    "approver",
    "approved_at",
    "expires_at",
)


class ApprovalError(ValueError):
    """An approval record is not well formed."""


class ApprovalProvenanceError(RuntimeError):
    """The approval record cannot be shown to be a committed, human-authored file."""


def is_valid_repository(repository: str) -> bool:
    """``True`` for exactly ``owner/name`` with GitHub's own character set - nothing that could
    redirect a request to another path."""
    return bool(_REPOSITORY.match(repository)) and ".." not in repository


def handoff_id(handoff: Handoff) -> str:
    """The stable id naming a handoff's approval file: ``<owner>__<name>__<fingerprint hex>``."""
    owner, name = handoff.repository.split("/", 1)
    digest = handoff.defect_fingerprint.removeprefix("sha256:")
    return f"{owner}__{name}__{digest}"


def approval_relative_path(identifier: str) -> str:
    return f"{APPROVALS_RELATIVE_DIR}/{identifier}.json"


def evidence_digest(handoff: Handoff) -> str:
    """Digest of everything that determines what would be filed and where.

    Lifecycle fields (``status``, ``issue_ref``, ``close_reason``) are deliberately excluded: a
    handoff moving through its lifecycle is not a change to the content the owner approved.
    """
    canonical = {
        "repository": handoff.repository,
        "source_revision": handoff.source_revision,
        "defect_fingerprint": handoff.defect_fingerprint,
        "triggering_check": {
            "id": handoff.triggering_check.id,
            "version": handoff.triggering_check.version,
            "causal_stage": handoff.triggering_check.causal_stage,
        },
        "evidence": [{"path": e.path, "detail": e.detail} for e in handoff.evidence],
        "claim": handoff.claim,
        "suggested_issue_title": handoff.suggested_issue_title,
        "suggested_issue_body": handoff.suggested_issue_body,
    }
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApprovalRecord:
    handoff_id: str
    repository: str
    evidence_digest: str
    approver: str
    approved_at: datetime
    expires_at: datetime


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ApprovalError(f"{field} must be an ISO-8601 UTC timestamp string")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalError(f"{field} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ApprovalError(f"{field} carries no timezone (use ...Z)")
    return parsed.astimezone(UTC)


def parse_approval(text: str) -> ApprovalRecord:
    """Parse and structurally validate one approval file; raises :class:`ApprovalError`."""
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApprovalError(f"not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ApprovalError("top level must be a mapping")
    unknown = sorted(set(loaded) - set(_FIELDS))
    missing = [f for f in _FIELDS if f not in loaded]
    if missing:
        raise ApprovalError(f"missing field(s): {', '.join(missing)}")
    if unknown:
        raise ApprovalError(f"unknown field(s): {', '.join(str(u) for u in unknown)}")
    strings: dict[str, str] = {}
    for field in ("handoff_id", "repository", "evidence_digest", "approver"):
        value = loaded[field]
        if not isinstance(value, str) or not value.strip():
            raise ApprovalError(f"{field} must be a non-empty string")
        strings[field] = value.strip()
    if not _HANDOFF_ID.match(strings["handoff_id"]):
        raise ApprovalError("handoff_id is not <owner>__<name>__<64 hex>")
    if not is_valid_repository(strings["repository"]):
        raise ApprovalError("repository is not owner/name")
    if not _DIGEST.match(strings["evidence_digest"]):
        raise ApprovalError("evidence_digest is not sha256:<64 hex>")
    if any(marker in strings["approver"].lower() for marker in _BOT_MARKERS):
        raise ApprovalError("approver must be a person, not a bot or workflow identity")
    approved_at = _timestamp(loaded["approved_at"], "approved_at")
    expires_at = _timestamp(loaded["expires_at"], "expires_at")
    if expires_at <= approved_at:
        raise ApprovalError("expires_at must be after approved_at")
    if expires_at - approved_at > MAX_APPROVAL_LIFETIME:
        raise ApprovalError(
            f"validity window exceeds {MAX_APPROVAL_LIFETIME.days} days - an approval is not a "
            "standing authorization"
        )
    return ApprovalRecord(
        handoff_id=strings["handoff_id"],
        repository=strings["repository"],
        evidence_digest=strings["evidence_digest"],
        approver=strings["approver"],
        approved_at=approved_at,
        expires_at=expires_at,
    )


class ApprovalStore(Protocol):
    """Where approval records come from. ``read`` returns the record text, ``None`` when no record
    exists for the id, and raises :class:`ApprovalProvenanceError` when one exists but cannot be
    trusted."""

    def read(self, identifier: str) -> str | None: ...


@dataclass(frozen=True)
class ApprovalVerdict:
    approved: bool
    reason: str
    record: ApprovalRecord | None = None


def verify_approval(
    handoff: Handoff,
    store: ApprovalStore,
    *,
    now: Callable[[], datetime] | None = None,
) -> ApprovalVerdict:
    """Whether ``store`` holds a current, matching owner approval for exactly this handoff."""
    identifier = handoff_id(handoff)
    expected_path = approval_relative_path(identifier)

    def deny(reason: str) -> ApprovalVerdict:
        return ApprovalVerdict(False, reason)

    if not is_valid_repository(handoff.repository):
        return deny(f"handoff target {handoff.repository!r} is not a valid owner/name")
    try:
        text = store.read(identifier)
    except ApprovalProvenanceError as exc:
        return deny(f"approval provenance unverifiable ({exc})")
    if text is None:
        return deny(f"no approval record ({expected_path} is not committed)")
    try:
        record = parse_approval(text)
    except ApprovalError as exc:
        return deny(f"approval record malformed ({expected_path}): {exc}")
    if record.handoff_id != identifier:
        return deny(f"approval names a different handoff ({record.handoff_id})")
    if record.repository.casefold() != handoff.repository.casefold():
        return deny(
            f"approval target mismatch: approved for {record.repository}, handoff targets "
            f"{handoff.repository}"
        )
    current = evidence_digest(handoff)
    if record.evidence_digest != current:
        return deny(
            "approval digest mismatch: the handoff changed since it was approved "
            f"(approved {record.evidence_digest}, now {current}) - a fresh approval is required"
        )
    moment = (now or (lambda: datetime.now(UTC)))()
    if record.approved_at > moment + CLOCK_SKEW:
        return deny(f"approval is dated in the future ({record.approved_at.isoformat()})")
    if moment >= record.expires_at:
        return deny(f"approval expired at {record.expires_at.isoformat()}")
    return ApprovalVerdict(
        True, f"approved by {record.approver} until {record.expires_at.isoformat()}", record
    )


class GitApprovalStore:
    """Reads approval records from a git ref of the control repository, never the working tree.

    The ref is the commit a run was triggered on, so a file a step of that run creates (or even
    commits locally) is invisible to it. A record whose introducing commit is bot-authored, or
    whose introducing commit cannot be identified (shallow clone), is refused.
    """

    def __init__(self, root: Path, ref: str = "HEAD") -> None:
        if not _REF.match(ref):
            raise ApprovalProvenanceError(f"unacceptable git ref {ref!r}")
        self._root = root
        self._ref = ref

    def _git(self, *args: str) -> str:
        completed = run_git(list(args), cwd=self._root, timeout=60)
        if completed.returncode != 0:
            raise ApprovalProvenanceError(f"git {args[0]} failed: {completed.stderr.strip()[:200]}")
        return str(completed.stdout)

    def read(self, identifier: str) -> str | None:
        if not _HANDOFF_ID.match(identifier):
            raise ApprovalProvenanceError(f"unacceptable handoff id {identifier!r}")
        path = approval_relative_path(identifier)
        if not self._git("ls-tree", "--name-only", self._ref, "--", path).strip():
            return None
        if self._git("rev-parse", "--is-shallow-repository").strip() == "true":
            raise ApprovalProvenanceError(
                "shallow clone: the commit that introduced the record cannot be identified "
                "(check out with fetch-depth: 0)"
            )
        identities = self._git(
            "log", "-1", "--format=%an <%ae>%n%cn <%ce>", self._ref, "--", path
        ).lower()
        if not identities.strip():
            raise ApprovalProvenanceError("no commit introduces the record")
        if any(marker in identities for marker in _BOT_MARKERS):
            raise ApprovalProvenanceError("the record was authored or committed by a bot identity")
        return self._git("show", f"{self._ref}:{path}")
