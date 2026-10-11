"""The issue lifecycle across scheduled cycles (TC-ISS-10): pure decisions, no network, no write.

Every cycle of ``issues-scheduled.yml`` redetects each handoff (``redetect.py``). What a cycle may
do with the answer:

- **The defect persists with the same evidence**: nothing. Not a new issue (the fingerprint marker
  makes filing idempotent, ``file.py``) and not a repeat comment.
- **The defect persists and its evidence changed** (a different count of failing files, a new error
  text): one *update comment* on the existing issue, never a duplicate issue. ``decide_update``
  keeps the comment idempotent without any local state: each update ends in a marker that carries
  the digest of the evidence it reported (``evidence_state_digest``), and a later cycle posts only
  when its digest differs from the latest marker on the issue. Before any update exists, the first
  one waits for the repository's head to move since filing, so a cycle that merely re-confirms the
  filed finding is silent.
- **The defect is gone**: ``redetect`` proposes ``RESOLVED_UPSTREAM`` and ``file.py`` closes the
  issue only with the owner's close approval (``close_approval.py``); that path is unchanged. The
  candidate the defect was blocking becomes a ``ResumeRecord`` (``resume_record``), written as the
  contract ``core/sealing_plan.py`` reads, so the sealing plan takes it up whatever the drift
  monitor says.

Writing the comment is ``file.py::comment_on_filed``; this module decides and renders. The text is
held to ``quality.text_quality_findings`` (no secret, no internal vocabulary, no promotional or
blaming tone) and an update that fails the gate is not posted, never softened.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from repository_presenter.components.issues.approval import handoff_id
from repository_presenter.components.issues.model import Handoff
from repository_presenter.components.issues.quality import text_quality_findings
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.github.client import IssueComment
from repository_presenter.core.sealing_plan import RESUME_CONTRACT_VERSION, ResumeRecord

UPDATE_MARKER_PREFIX = "<!-- repository-presenter-update:"
_UPDATE_MARKER = re.compile(
    r"<!-- repository-presenter-update: (?P<fingerprint>sha256:[0-9a-f]{64}) "
    r"digest=(?P<digest>sha256:[0-9a-f]{64}) revision=(?P<revision>[0-9a-f]{7,64}) -->"
)
MAX_EVIDENCE_LINES = 8


def evidence_state_digest(result: RedetectionResult) -> str:
    """The digest of what a cycle found: the redetector's note and its fresh evidence. Independent
    of the revision and the clock, so the same finding at a later head digests the same and does
    not earn another comment."""
    canonical = {
        "note": result.note,
        "evidence": [{"path": e.path, "detail": e.detail} for e in result.fresh_evidence],
    }
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def update_marker(defect_fingerprint: str, digest: str, revision: str) -> str:
    """The hidden marker that ends an update comment: which defect, which evidence, which head."""
    return f"{UPDATE_MARKER_PREFIX} {defect_fingerprint} digest={digest} revision={revision} -->"


@dataclass(frozen=True)
class UpdatePlan:
    """One update comment, ready to post."""

    issue_number: int
    digest: str
    revision: str
    body: str


@dataclass(frozen=True)
class UpdateDecision:
    """Whether a cycle posts an update, and why or why not (the reason is logged either way)."""

    post: bool
    reason: str
    plan: UpdatePlan | None = None


def render_update(handoff: Handoff, result: RedetectionResult) -> str:
    """The comment a maintainer reads: the current head, what is still wrong, the evidence."""
    revision = result.checked_at_revision or handoff.source_revision
    evidence = result.fresh_evidence[:MAX_EVIDENCE_LINES]
    lines = [
        "## Update",
        "",
        f"At revision `{revision}` the defect reported here is still present "
        f"(this report was verified at `{handoff.source_revision}`).",
        "",
        result.note,
        "",
        "### Current evidence",
        "",
        *(
            f"- `{entry.path}`" + (f": {entry.detail}" if entry.detail else "")
            for entry in evidence
        ),
    ]
    if len(result.fresh_evidence) > len(evidence):
        lines.append(f"- and {len(result.fresh_evidence) - len(evidence)} more")
    lines += [
        "",
        update_marker(handoff.defect_fingerprint, evidence_state_digest(result), revision),
    ]
    return "\n".join(lines) + "\n"


def _latest_digest(handoff: Handoff, comments: Sequence[IssueComment]) -> str | None:
    """The digest in the newest update comment this system made for ``handoff``'s defect."""
    for comment in reversed(comments):
        for match in reversed(list(_UPDATE_MARKER.finditer(comment.body))):
            if match.group("fingerprint") == handoff.defect_fingerprint:
                return match.group("digest")
    return None


def decide_update(
    handoff: Handoff, result: RedetectionResult, comments: Sequence[IssueComment]
) -> UpdateDecision:
    """Whether this cycle posts an update comment on ``handoff``'s filed issue."""
    if handoff.status != "FILED" or handoff.issue_ref is None:
        return UpdateDecision(
            False, f"status is {handoff.status!r}: only a FILED handoff's issue is updated"
        )
    if result.still_fires is None:
        return UpdateDecision(False, f"recheck inconclusive ({result.note}): no update")
    if result.still_fires is False:
        return UpdateDecision(False, "the defect no longer fires: the close path, not a comment")
    if result.checked_at_revision is None:
        return UpdateDecision(False, "the current revision is unknown: no update")
    digest = evidence_state_digest(result)
    last = _latest_digest(handoff, comments)
    if last is None:
        if not result.revision_drifted:
            return UpdateDecision(
                False,
                "the head has not moved since filing and the evidence is unchanged: no update",
            )
        was, now = handoff.source_revision[:12], result.checked_at_revision[:12]
        why = f"the head moved from {was} to {now}"
    elif last == digest:
        return UpdateDecision(
            False, "the evidence is unchanged since the latest update: already posted"
        )
    else:
        why = "the evidence changed since the latest update"
    body = render_update(handoff, result)
    findings = text_quality_findings(body)
    if findings:
        return UpdateDecision(
            False,
            "the update text fails the quality gate: " + "; ".join(str(f) for f in findings),
        )
    return UpdateDecision(
        True,
        f"{why}: one update comment",
        UpdatePlan(handoff.issue_ref.number, digest, result.checked_at_revision, body),
    )


def resume_record(handoff: Handoff, result: RedetectionResult) -> ResumeRecord | None:
    """The record that lets ``core/sealing_plan.py`` take up the candidate this defect was
    blocking: the redetect says, firmly, that the check no longer fires. A handoff already
    ``RESOLVED_UPSTREAM`` was resumed by an earlier cycle and is not resumed again."""
    if result.still_fires is not False or handoff.status == "RESOLVED_UPSTREAM":
        return None
    return ResumeRecord(
        repository=handoff.repository,
        resolved_revision=result.checked_at_revision,
        handoff_id=handoff_id(handoff),
    )


def resume_contract(records: Iterable[ResumeRecord]) -> dict[str, Any]:
    """The JSON ``read_resume_contract`` in ``core/sealing_plan.py`` reads: one row per repository
    (the first record wins), sorted so the file is deterministic."""
    rows: dict[str, ResumeRecord] = {}
    for record in records:
        rows.setdefault(record.repository, record)
    return {
        "schema_version": RESUME_CONTRACT_VERSION,
        "repositories": [
            {
                "repository": record.repository,
                "resolved_revision": record.resolved_revision,
                "handoff_id": record.handoff_id,
            }
            for _, record in sorted(rows.items())
        ],
    }
