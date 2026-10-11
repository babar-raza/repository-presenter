"""TC-ISS-10: the issue lifecycle across scheduled cycles.

Each cycle redetects every handoff. A filed defect that persists with *changed* evidence earns one
update comment on its own issue - never a second issue, never a repeat of an update already made. A
resolved defect goes down the close-approval path (``file.py`` / ``close_approval.py``) and, for the
candidate it was blocking, becomes a resume record for ``core/sealing_plan.py``."""

from __future__ import annotations

import json
from typing import Any

import pytest

from repository_presenter.components.issues.lifecycle import (
    UPDATE_MARKER_PREFIX,
    decide_update,
    evidence_state_digest,
    render_update,
    resume_contract,
    resume_record,
    update_marker,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.quality import text_quality_findings
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.github.client import IssueComment
from repository_presenter.core.sealing_plan import RESUME_CONTRACT_VERSION, parse_resume_contract

REPO = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
FILED_AT = "a" * 40
HEAD = "b" * 40
FINGERPRINT = "sha256:" + "d" * 64


def _handoff(*, status: str = "FILED") -> Handoff:
    filed = status in {"FILED", "RESOLVED_UPSTREAM"}
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=FILED_AT,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(
            id="NOT_PROCESSABLE", version="1", causal_stage="EXTRACTING"
        ),
        evidence=(EvidenceEntry(path="src/a.py", detail="SyntaxError"),),
        claim="102 of 119 source files do not parse",
        suggested_issue_title="Aspose.TeX FOSS for Python: source files do not parse",
        suggested_issue_body="body\n",
        status=status,  # type: ignore[arg-type]
        issue_ref=IssueRef(12, f"https://github.com/{REPO}/issues/12") if filed else None,
        close_reason="completed" if status == "RESOLVED_UPSTREAM" else None,
    )


def _result(
    *,
    fires: bool | None = True,
    drifted: bool = True,
    note: str = "still fires: 90/119 named source path(s) still fail to parse",
    detail: str = "SyntaxError at line 3",
    revision: str | None = HEAD,
) -> RedetectionResult:
    return RedetectionResult(
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="NOT_PROCESSABLE",
        checked_at="2026-10-11T09:00:00+00:00",
        checked_at_revision=revision,
        revision_drifted=drifted,
        still_fires=fires,
        note=note,
        fresh_evidence=(EvidenceEntry(path="src/a.py", detail=detail),),
        proposed_status="RESOLVED_UPSTREAM" if fires is False else None,
        proposed_close_reason="completed" if fires is False else None,
    )


def _comment(identifier: int, body: str) -> IssueComment:
    return IssueComment(identifier, body, "2026-10-10T00:00:00Z")


# --- the digest -------------------------------------------------------------------------------


def test_the_digest_depends_on_the_finding_and_not_on_the_revision_or_the_clock() -> None:
    a = _result(revision="1" * 40)
    b = _result(revision="2" * 40)
    assert evidence_state_digest(a) == evidence_state_digest(b)
    assert evidence_state_digest(a) != evidence_state_digest(_result(detail="another error"))
    assert evidence_state_digest(a) != evidence_state_digest(_result(note="still fires: 3 files"))


# --- deciding whether an update is due ---------------------------------------------------------


def test_the_first_update_waits_for_the_head_to_move_since_filing() -> None:
    quiet = decide_update(_handoff(), _result(drifted=False), [])
    assert quiet.post is False and "unchanged" in quiet.reason
    moved = decide_update(_handoff(), _result(drifted=True), [])
    assert moved.post is True and moved.plan is not None
    assert moved.plan.issue_number == 12


def test_changed_evidence_after_an_earlier_update_posts_a_new_comment() -> None:
    earlier = update_marker(FINGERPRINT, evidence_state_digest(_result()), "c" * 40)
    comments = [_comment(1, f"Update.\n\n{earlier}\n")]
    changed = _result(note="still fires: 40/119 named source path(s) still fail to parse")
    decision = decide_update(_handoff(), changed, comments)
    assert decision.post is True
    assert decision.plan is not None
    assert evidence_state_digest(changed) in decision.plan.body


def test_unchanged_evidence_never_repeats_an_update() -> None:
    marker = update_marker(FINGERPRINT, evidence_state_digest(_result()), "c" * 40)
    decision = decide_update(_handoff(), _result(), [_comment(1, f"Update\n{marker}\n")])
    assert decision.post is False and "already" in decision.reason


def test_only_the_latest_update_governs_so_a_reversion_is_reported() -> None:
    first = update_marker(FINGERPRINT, evidence_state_digest(_result()), "c" * 40)
    second = update_marker(FINGERPRINT, evidence_state_digest(_result(detail="other")), "d" * 40)
    comments = [_comment(1, first), _comment(2, second)]
    assert decide_update(_handoff(), _result(), comments).post is True


def test_another_defects_update_marker_is_ignored() -> None:
    other = update_marker("sha256:" + "e" * 64, evidence_state_digest(_result()), "c" * 40)
    decision = decide_update(_handoff(), _result(drifted=False), [_comment(1, other)])
    assert decision.post is False  # nothing of ours yet, and the head has not moved


@pytest.mark.parametrize(
    ("kwargs", "word"),
    [
        ({"fires": None}, "inconclusive"),
        ({"fires": False}, "close"),
        ({"revision": None}, "revision"),
    ],
)
def test_no_update_without_a_firm_current_finding(kwargs: dict[str, Any], word: str) -> None:
    decision = decide_update(_handoff(), _result(**kwargs), [])
    assert decision.post is False and word in decision.reason


@pytest.mark.parametrize("status", ["HANDOFF_PENDING", "RESOLVED_UPSTREAM"])
def test_only_a_filed_handoff_is_updated(status: str) -> None:
    decision = decide_update(_handoff(status=status), _result(), [])
    assert decision.post is False and "FILED" in decision.reason


def test_an_update_that_fails_the_quality_gate_is_not_posted() -> None:
    leaking = _result(detail="token ghp_abcdefghijklmnopqrstuvwxyz0123456789 leaked")
    decision = decide_update(_handoff(), leaking, [])
    assert decision.post is False and "quality" in decision.reason


# --- the text ----------------------------------------------------------------------------------


def test_the_update_text_names_the_revision_the_evidence_and_carries_its_marker() -> None:
    body = render_update(_handoff(), _result())
    assert HEAD in body and "src/a.py" in body and "SyntaxError at line 3" in body
    assert body.count(UPDATE_MARKER_PREFIX) == 1
    assert update_marker(FINGERPRINT, evidence_state_digest(_result()), HEAD) in body
    assert text_quality_findings(body) == []


# --- the resume record -------------------------------------------------------------------------


def test_a_resolved_defect_yields_a_resume_record_at_the_revision_it_was_resolved_at() -> None:
    record = resume_record(_handoff(), _result(fires=False))
    assert record is not None
    assert record.repository == REPO and record.resolved_revision == HEAD
    assert record.handoff_id is not None and record.handoff_id.startswith("aspose-tex-foss__")


@pytest.mark.parametrize("fires", [True, None])
def test_a_persisting_or_inconclusive_defect_yields_no_resume_record(fires: bool | None) -> None:
    assert resume_record(_handoff(), _result(fires=fires)) is None


def test_a_pending_handoff_that_no_longer_fires_also_resumes_its_candidate() -> None:
    assert resume_record(_handoff(status="HANDOFF_PENDING"), _result(fires=False)) is not None


def test_an_already_resolved_handoff_does_not_resume_again() -> None:
    assert resume_record(_handoff(status="RESOLVED_UPSTREAM"), _result(fires=False)) is None


def test_the_resume_contract_is_what_sealing_plan_reads() -> None:
    record = resume_record(_handoff(), _result(fires=False))
    assert record is not None
    contract = resume_contract([record, record])  # a repeated repository is written once
    assert contract["schema_version"] == RESUME_CONTRACT_VERSION
    parsed = parse_resume_contract(json.loads(json.dumps(contract)))
    assert [(r.repository, r.resolved_revision) for r in parsed] == [(REPO, HEAD)]
