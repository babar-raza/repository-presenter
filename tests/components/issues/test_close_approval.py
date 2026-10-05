"""The owner's per-issue close approval (``ops/issue_close_approvals/<handoff-id>.json``).

A close approval names the exact filed issue and the close reason, expires, and is read from a git
ref - never the working tree, never a bot-authored file, and never from the *filing* approval
directory. Every refusal here is a negative control: a record that does not match the close being
attempted must not authorize it.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.issues.approval import (
    MAX_APPROVAL_LIFETIME,
    ApprovalError,
    ApprovalProvenanceError,
    GitApprovalStore,
    handoff_id,
)
from repository_presenter.components.issues.close_approval import (
    CLOSE_APPROVALS_RELATIVE_DIR,
    close_approval_relative_path,
    parse_close_approval,
    verify_close_approval,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.core.git_safety.git import run_git
from support import (
    MemoryApprovalStore,
    approval_text,
    close_approval_text,
    closing_store,
    commit_all,
    init_git_repository,
)

REPO = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
REVISION = "bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11"
FINGERPRINT = "sha256:ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a"
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _filed(number: int = 42) -> Handoff:
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-02", version="2", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="pyproject.toml", detail="bad build-backend"),),
        claim=f"At revision {REVISION}, {REPO} cannot be built.",
        suggested_issue_title="build-backend does not exist",
        suggested_issue_body="## Summary\n\nbroken.\n",
        status="FILED",
        issue_ref=IssueRef(number=number, url=f"https://github.com/{REPO}/issues/{number}"),
    )


def _text(handoff: Handoff, **overrides: Any) -> str:
    overrides.setdefault("approved_at", NOW - timedelta(hours=1))
    return close_approval_text(handoff, **overrides)


def _verify(handoff: Handoff, text: str | None, reason: str | None = "not_planned") -> Any:
    store = MemoryApprovalStore({} if text is None else {handoff_id(handoff): text})
    return verify_close_approval(handoff, store, close_reason=reason, now=lambda: NOW)


def test_a_matching_unexpired_record_is_approved() -> None:
    handoff = _filed()
    verdict = _verify(handoff, _text(handoff))
    assert verdict.approved is True
    assert verdict.record is not None
    assert verdict.record.issue_number == 42
    assert verdict.record.close_reason == "not_planned"


def test_the_record_lives_in_its_own_directory_not_the_filing_approvals() -> None:
    identifier = handoff_id(_filed())
    assert close_approval_relative_path(identifier) == (
        f"{CLOSE_APPROVALS_RELATIVE_DIR}/{identifier}.json"
    )
    assert CLOSE_APPROVALS_RELATIVE_DIR == "ops/issue_close_approvals"


def test_the_reason_can_be_left_open_only_for_counting() -> None:
    handoff = _filed()
    assert _verify(handoff, _text(handoff, close_reason="completed"), None).approved is True
    assert (
        _verify(handoff, _text(handoff, close_reason="completed"), "not_planned").approved is False
    )


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"issue_number": 43}, "#43"),
        ({"close_reason": "completed"}, "reason"),
        ({"digest": "sha256:" + "1" * 64}, "digest mismatch"),
        ({"repository": "aspose-html-foss/Other"}, "target mismatch"),
        (
            {
                "approved_at": NOW - timedelta(days=8),
                "expires_at": NOW - timedelta(days=1),
            },
            "expired",
        ),
        (
            {"approved_at": NOW + timedelta(hours=2), "expires_at": NOW + timedelta(days=2)},
            "future",
        ),
    ],
    ids=["issue-number", "reason", "digest", "repository", "expired", "future"],
)
def test_a_record_that_does_not_match_the_close_is_refused(
    overrides: dict[str, Any], fragment: str
) -> None:
    handoff = _filed(42)
    verdict = _verify(handoff, _text(handoff, **overrides))
    assert verdict.approved is False
    assert fragment in verdict.reason


def test_no_record_is_refused_and_names_the_file_to_commit() -> None:
    verdict = _verify(_filed(), None)
    assert verdict.approved is False
    assert "no close approval record" in verdict.reason
    assert "ops/issue_close_approvals/" in verdict.reason


def test_a_handoff_with_no_filed_issue_has_nothing_to_close() -> None:
    handoff = replace(_filed(), status="HANDOFF_PENDING", issue_ref=None)
    verdict = verify_close_approval(handoff, MemoryApprovalStore(), close_reason="completed")
    assert verdict.approved is False
    assert "no filed issue" in verdict.reason


def test_a_filing_approval_record_is_not_a_close_approval() -> None:
    """The two kinds of record have different fields; a filing record fails to parse as a close."""
    handoff = _filed()
    verdict = _verify(handoff, approval_text(handoff, approved_at=NOW - timedelta(hours=1)))
    assert verdict.approved is False
    assert "malformed" in verdict.reason


def test_a_record_filed_under_another_handoffs_id_is_refused() -> None:
    handoff = _filed()
    other = replace(handoff, defect_fingerprint="sha256:" + "e" * 64)
    store = MemoryApprovalStore({handoff_id(handoff): _text(other)})
    verdict = verify_close_approval(handoff, store, close_reason="not_planned", now=lambda: NOW)
    assert verdict.approved is False
    assert "different handoff" in verdict.reason


def test_an_untrusted_store_is_refused() -> None:
    class Untrusted:
        def read(self, identifier: str) -> str | None:
            raise ApprovalProvenanceError("bot-authored")

    verdict = verify_close_approval(_filed(), Untrusted(), close_reason="completed")
    assert verdict.approved is False
    assert "provenance" in verdict.reason


def _edit(handoff: Handoff, **changes: Any) -> str:
    record = json.loads(_text(handoff))
    record.update(changes)
    return json.dumps(record)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda r: r.pop("issue_number"), "missing field"),
        (lambda r: r.update(extra="x"), "unknown field"),
        (lambda r: r.update(issue_number="42"), "issue_number"),
        (lambda r: r.update(issue_number=0), "issue_number"),
        (lambda r: r.update(issue_number=True), "issue_number"),
        (lambda r: r.update(close_reason="wontfix"), "close_reason"),
        (lambda r: r.update(close_reason="not planned"), "close_reason"),
        (lambda r: r.update(approver="github-actions[bot]"), "not a bot"),
        (lambda r: r.update(evidence_digest="md5:00"), "evidence_digest"),
        (lambda r: r.update(handoff_id="nope"), "handoff_id"),
        (lambda r: r.update(approved_at="2026-10-05T11:00:00"), "timezone"),
    ],
)
def test_a_malformed_record_is_refused(mutation: Any, expected: str) -> None:
    record = json.loads(_text(_filed()))
    mutation(record)
    with pytest.raises(ApprovalError, match=expected):
        parse_close_approval(json.dumps(record))


def test_a_standing_approval_longer_than_the_maximum_window_is_refused() -> None:
    handoff = _filed()
    text = _text(
        handoff,
        approved_at=NOW - timedelta(hours=1),
        expires_at=NOW + MAX_APPROVAL_LIFETIME + timedelta(days=1),
    )
    with pytest.raises(ApprovalError, match="standing authorization"):
        parse_close_approval(text)


def test_not_json_is_refused() -> None:
    with pytest.raises(ApprovalError, match="not valid JSON"):
        parse_close_approval("{nope")


# ---------------------------------------------------------------------------
# GitApprovalStore(directory=...): committed, human-authored, in the run's own commit - and the
# close store reads only its own directory
# ---------------------------------------------------------------------------


def _commit(repo: Path, handoff: Handoff, text: str, directory: str, name: str = "Owner") -> None:
    target = repo / directory / f"{handoff_id(handoff)}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    assert run_git(["config", "user.name", name], cwd=repo).returncode == 0
    assert (
        run_git(["config", "user.email", f"{name.lower()}@example.com"], cwd=repo).returncode == 0
    )
    commit_all(repo, "approve")


def _git_store(repo: Path, ref: str = "HEAD") -> GitApprovalStore:
    return GitApprovalStore(repo, ref, directory=CLOSE_APPROVALS_RELATIVE_DIR)


def test_a_committed_human_close_record_is_read_and_verified(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _filed()
    _commit(repo, handoff, _text(handoff), CLOSE_APPROVALS_RELATIVE_DIR)
    verdict = verify_close_approval(
        handoff, _git_store(repo), close_reason="not_planned", now=lambda: NOW
    )
    assert verdict.approved is True


def test_the_close_store_does_not_read_the_filing_approvals_directory(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _filed()
    _commit(
        repo,
        handoff,
        _text(handoff),
        "ops/issue_approvals",  # a close-shaped record in the *filing* directory
    )
    verdict = verify_close_approval(
        handoff, _git_store(repo), close_reason="not_planned", now=lambda: NOW
    )
    assert verdict.approved is False
    assert "no close approval record" in verdict.reason


def test_a_close_record_only_in_the_working_tree_is_invisible(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _filed()
    target = repo / CLOSE_APPROVALS_RELATIVE_DIR / f"{handoff_id(handoff)}.json"
    target.parent.mkdir(parents=True)
    target.write_text(_text(handoff), encoding="utf-8")
    verdict = verify_close_approval(
        handoff, _git_store(repo), close_reason="not_planned", now=lambda: NOW
    )
    assert verdict.approved is False


def test_a_close_record_committed_after_the_trigger_commit_is_invisible(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    trigger = run_git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    handoff = _filed()
    _commit(repo, handoff, _text(handoff), CLOSE_APPROVALS_RELATIVE_DIR)
    refused = verify_close_approval(
        handoff, _git_store(repo, trigger), close_reason="not_planned", now=lambda: NOW
    )
    assert refused.approved is False


def test_a_bot_authored_close_record_is_refused(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _filed()
    _commit(repo, handoff, _text(handoff), CLOSE_APPROVALS_RELATIVE_DIR, name="github-actions[bot]")
    verdict = verify_close_approval(
        handoff, _git_store(repo), close_reason="not_planned", now=lambda: NOW
    )
    assert verdict.approved is False
    assert "bot" in verdict.reason


def test_a_hostile_directory_is_rejected() -> None:
    for directory in ("../outside", "ops/../..", "bad dir", "--output=x"):
        with pytest.raises(ApprovalProvenanceError):
            GitApprovalStore(Path("."), "HEAD", directory=directory)


def test_closing_store_helper_builds_a_valid_record() -> None:
    """The support helper itself produces a record this module accepts (guards the fixtures)."""
    handoff = _filed()
    store = closing_store(handoff, approved_at=NOW - timedelta(hours=1))
    verdict = verify_close_approval(handoff, store, close_reason="not_planned", now=lambda: NOW)
    assert verdict.approved is True
