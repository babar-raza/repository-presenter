"""TC-ISS-11 at the command line: ``status`` shows the issue funnel, and ``issue-funnel`` prints it
with an annotation for every handoff that has waited too long. Offline; ages come from an injected
git reader and approvals from an injected store."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, main
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
    write_handoff,
)

REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"


def _handoff(digit: str, status: str = "HANDOFF_PENDING") -> Handoff:
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision="a" * 40,
        defect_fingerprint="sha256:" + digit * 64,
        triggering_check=TriggeringCheck(id="BC-02", version="3", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="x.cpp", detail="d"),),
        claim="c",
        suggested_issue_title="Aspose Cells: a defect that is long enough",
        suggested_issue_body="b\n",
        status=status,  # type: ignore[arg-type]
        issue_ref=IssueRef(3, "https://github.com/o/r/issues/3") if status == "FILED" else None,
    )


@pytest.fixture
def funnel_project(project: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Three handoffs: an old pending one, a fresh approved one, a filed one."""
    ages = {"1": 30, "2": 2, "3": 60}
    handoffs = [_handoff("1"), _handoff("2"), _handoff("3", "FILED")]
    directory = project / "evidence" / "upstream-defects" / REPO.replace("/", "__")
    for handoff in handoffs:
        write_handoff(
            handoff, directory / f"{handoff.defect_fingerprint.removeprefix('sha256:')}.json"
        )
    now = datetime.now(UTC)

    def first_seen(root: Path) -> Any:
        return lambda path: now - timedelta(days=ages[path.stem[0]])

    class Approvals:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def read(self, identifier: str) -> str | None:
            return None

    monkeypatch.setattr(cli, "git_first_seen", first_seen)
    monkeypatch.setattr(cli, "GitApprovalStore", Approvals)
    monkeypatch.setattr(
        cli,
        "_issue_handoff_is_approved",
        lambda store: lambda handoff: handoff.defect_fingerprint.endswith("2" * 64),
    )
    return project


def test_status_shows_the_issue_funnel(
    funnel_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["status", "--root", str(funnel_project)])
    assert "issues: PENDING 1, APPROVED 1, ACKNOWLEDGED 0, FILED 1, RESOLVED 0" in (
        capsys.readouterr().out
    )


def test_status_json_carries_the_funnel_counts(
    funnel_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["status", "--root", str(funnel_project), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert report["issues"] == {
        "PENDING": 1,
        "APPROVED": 1,
        "ACKNOWLEDGED": 0,
        "FILED": 1,
        "RESOLVED": 0,
    }


def test_status_without_any_handoff_adds_no_funnel_line(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["status", "--root", str(project)])
    assert "issues:" not in capsys.readouterr().out


def test_issue_funnel_prints_the_funnel_and_an_annotation_per_late_handoff(
    funnel_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["issue-funnel", "--root", str(funnel_project), "--max-pending-days", "14"])

    out = capsys.readouterr().out
    assert exit_code == EXIT_OK  # a late handoff is a warning, not a failure
    assert "issues: PENDING 1, APPROVED 1" in out
    annotations = [line for line in out.splitlines() if line.startswith("::")]
    assert len(annotations) == 1
    assert annotations[0].startswith("::warning ") and "30 days" in annotations[0]


def test_issue_funnel_can_be_made_to_fail_on_an_alert(funnel_project: Path) -> None:
    code = main(["issue-funnel", "--root", str(funnel_project), "--fail-on-alert"])
    assert code == EXIT_INCONSISTENT
    assert (
        main(["issue-funnel", "--root", str(funnel_project), "--max-pending-days", "90"]) == EXIT_OK
    )


def test_issue_funnel_with_a_high_limit_prints_no_annotation(
    funnel_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["issue-funnel", "--root", str(funnel_project), "--max-pending-days", "90"])
    assert not [line for line in capsys.readouterr().out.splitlines() if line.startswith("::")]


def test_issue_funnel_rejects_a_negative_limit(funnel_project: Path) -> None:
    from repository_presenter.cli import EXIT_USAGE

    assert main(["issue-funnel", "--root", str(funnel_project), "--max-pending-days", "-1"]) == (
        EXIT_USAGE
    )
