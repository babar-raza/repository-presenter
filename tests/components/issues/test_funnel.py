"""TC-ISS-11: the issue funnel (PENDING, APPROVED, FILED, RESOLVED) and the alert for a handoff that
has waited too long. Pure counts and annotations; the age of a handoff is when it was first
committed, read from git (injected here, and once against a real disposable repository)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from repository_presenter.components.issues.funnel import (
    DEFAULT_MAX_PENDING_DAYS,
    FUNNEL_STAGES,
    FunnelRow,
    age_alerts,
    build_funnel,
    funnel_counts,
    render_funnel,
    stage_of,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
    write_handoff,
)
from repository_presenter.core.git_safety.git import run_git
from support import commit_all, init_git_repository

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def _handoff(
    status: str = "HANDOFF_PENDING",
    *,
    repository: str = "o/Aspose.X-FOSS-for-Python",
    digit: str = "1",
) -> Handoff:
    filed = status in {"FILED", "RESOLVED_UPSTREAM"}
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision="a" * 40,
        defect_fingerprint="sha256:" + digit * 64,
        triggering_check=TriggeringCheck(id="BC-02", version="3", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="x.py", detail="d"),),
        claim="c",
        suggested_issue_title="Aspose X: a defect that is long enough",
        suggested_issue_body="b\n",
        status=status,  # type: ignore[arg-type]
        issue_ref=IssueRef(3, "https://github.com/o/r/issues/3") if filed else None,
        close_reason="completed" if status == "RESOLVED_UPSTREAM" else None,
    )


def _row(
    status: str, *, approved: bool = False, age: int | None = 0, digit: str = "1"
) -> FunnelRow:
    handoff = _handoff(status, digit=digit)
    return FunnelRow(handoff, stage_of(handoff, approved=approved), age)


def test_the_stage_of_a_handoff_follows_its_status_and_its_approval() -> None:
    assert stage_of(_handoff("HANDOFF_PENDING"), approved=False) == "PENDING"
    assert stage_of(_handoff("HANDOFF_PENDING"), approved=True) == "APPROVED"
    assert stage_of(_handoff("HANDOFF_ACKNOWLEDGED"), approved=False) == "ACKNOWLEDGED"
    assert stage_of(_handoff("FILED"), approved=False) == "FILED"
    assert stage_of(_handoff("RESOLVED_UPSTREAM"), approved=False) == "RESOLVED"


def test_an_approval_does_not_advance_a_handoff_already_past_pending() -> None:
    assert stage_of(_handoff("FILED"), approved=True) == "FILED"


def test_the_counts_cover_every_stage_including_the_empty_ones_in_funnel_order() -> None:
    rows = [
        _row("HANDOFF_PENDING", digit="1"),
        _row("HANDOFF_PENDING", digit="2"),
        _row("HANDOFF_PENDING", approved=True, digit="3"),
        _row("FILED", digit="4"),
        _row("RESOLVED_UPSTREAM", digit="5"),
    ]
    counts = funnel_counts(rows)
    assert list(counts) == list(FUNNEL_STAGES)
    assert counts == {"PENDING": 2, "APPROVED": 1, "ACKNOWLEDGED": 0, "FILED": 1, "RESOLVED": 1}
    assert list(funnel_counts([])) == list(FUNNEL_STAGES)


def test_the_line_shows_the_funnel_in_order() -> None:
    line = render_funnel(funnel_counts([_row("HANDOFF_PENDING"), _row("FILED", digit="2")]))
    assert line == "issues: PENDING 1, APPROVED 0, ACKNOWLEDGED 0, FILED 1, RESOLVED 0"


def test_a_pending_handoff_older_than_the_limit_raises_a_warning_annotation() -> None:
    rows = [_row("HANDOFF_PENDING", age=20)]
    [alert] = age_alerts(rows, max_pending_days=14)
    annotation = alert.annotation()
    assert annotation.startswith("::warning ")
    assert "20 days" in annotation and "o/Aspose.X-FOSS-for-Python" in annotation
    assert "\n" not in annotation


def test_an_approved_but_unfiled_handoff_past_the_limit_is_also_alerted() -> None:
    assert (
        len(age_alerts([_row("HANDOFF_PENDING", approved=True, age=15)], max_pending_days=14)) == 1
    )


@pytest.mark.parametrize("status", ["FILED", "RESOLVED_UPSTREAM", "HANDOFF_ACKNOWLEDGED"])
def test_only_a_waiting_handoff_ages_into_an_alert(status: str) -> None:
    assert age_alerts([_row(status, age=400)], max_pending_days=14) == []


def test_a_handoff_exactly_at_the_limit_is_not_yet_late() -> None:
    assert age_alerts([_row("HANDOFF_PENDING", age=14)], max_pending_days=14) == []
    assert len(age_alerts([_row("HANDOFF_PENDING", age=15)], max_pending_days=14)) == 1


def test_an_unknown_age_is_never_alerted_but_is_reported() -> None:
    [alert] = age_alerts([_row("HANDOFF_PENDING", age=None)], max_pending_days=14)
    assert "age unknown" in alert.annotation()
    assert alert.annotation().startswith("::notice ")


def test_the_oldest_alert_comes_first_and_the_default_limit_is_two_weeks() -> None:
    assert DEFAULT_MAX_PENDING_DAYS == 14
    rows = [
        _row("HANDOFF_PENDING", age=20, digit="1"),
        _row("HANDOFF_PENDING", age=40, digit="2"),
    ]
    assert [a.age_days for a in age_alerts(rows, max_pending_days=14)] == [40, 20]


def test_a_secret_never_reaches_an_annotation_text() -> None:
    row = _row("HANDOFF_PENDING", age=30)
    [alert] = age_alerts([row], max_pending_days=14)
    assert "ghp_" not in alert.annotation()


# --- building the rows from the committed handoffs ---------------------------------------------


def _store(root: Path, *handoffs: Handoff) -> None:
    for handoff in handoffs:
        owner, name = handoff.repository.split("/", 1)
        digest = handoff.defect_fingerprint.removeprefix("sha256:")
        write_handoff(
            handoff, root / "evidence" / "upstream-defects" / f"{owner}__{name}" / f"{digest}.json"
        )


def test_build_funnel_reads_the_ledger_the_approvals_and_the_ages(tmp_path: Path) -> None:
    pending = _handoff("HANDOFF_PENDING", digit="1")
    approved = _handoff("HANDOFF_PENDING", digit="2")
    filed = _handoff("FILED", digit="3")
    _store(tmp_path, pending, approved, filed)
    ages = {approved.defect_fingerprint: NOW - timedelta(days=3)}

    rows = build_funnel(
        tmp_path / "evidence" / "upstream-defects",
        is_approved=lambda handoff: handoff.defect_fingerprint == approved.defect_fingerprint,
        first_seen=lambda path: ages.get("sha256:" + path.stem),
        now=NOW,
    )

    by_digit = {row.handoff.defect_fingerprint[7]: row for row in rows}
    assert [by_digit[d].stage for d in "123"] == ["PENDING", "APPROVED", "FILED"]
    assert by_digit["2"].age_days == 3 and by_digit["1"].age_days is None


def test_build_funnel_is_empty_for_a_tree_without_handoffs(tmp_path: Path) -> None:
    assert (
        build_funnel(tmp_path, is_approved=lambda h: False, first_seen=lambda p: None, now=NOW)
        == []
    )


def test_the_age_of_a_handoff_is_when_git_first_saw_it(tmp_path: Path) -> None:
    from repository_presenter.components.issues.funnel import git_first_seen

    init_git_repository(tmp_path, with_commit=False)
    handoff = _handoff("HANDOFF_PENDING")
    _store(tmp_path, handoff)
    path = next((tmp_path / "evidence" / "upstream-defects").rglob("*.json"))
    assert run_git(["add", "."], cwd=tmp_path).returncode == 0
    stamp = "2026-09-20T10:00:00+00:00"
    done = run_git(
        ["commit", "-q", "-m", "add the handoff"],
        cwd=tmp_path,
        env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp},
    )
    assert done.returncode == 0, done.stderr
    # A later edit must not reset the clock: the age is from the commit that added the file.
    write_handoff(handoff, path)
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    commit_all(tmp_path, "touch it again")

    seen = git_first_seen(tmp_path)(path)

    assert seen == datetime(2026, 9, 20, 10, 0, tzinfo=UTC)


def test_the_age_is_unknown_for_a_file_git_has_never_seen(tmp_path: Path) -> None:
    from repository_presenter.components.issues.funnel import git_first_seen

    init_git_repository(tmp_path)
    stray = tmp_path / "stray.json"
    stray.write_text(json.dumps({}), encoding="utf-8")
    assert git_first_seen(tmp_path)(stray) is None
