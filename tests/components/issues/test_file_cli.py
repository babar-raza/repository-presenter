"""``repository-presenter file-upstream-defects --file`` wiring: dry-run by default, and, even
with --file, writes nothing without the explicit authorization variable, a write-scoped token, and
a recheck confirming the defect still fires. No test here makes a live GitHub call -
``default_post`` and ``redetect`` are both monkeypatched fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.issues.file import AUTHORIZATION_VARIABLE
from repository_presenter.components.issues.model import load_handoff

REPO_DIR = "aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp"
REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
FINGERPRINT = "b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365"

HANDOFF_PAYLOAD = {
    "schema_version": 1,
    "repository": REPOSITORY,
    "source_revision": REVISION,
    "defect_fingerprint": f"sha256:{FINGERPRINT}",
    "triggering_check": {"id": "BC-02", "version": "3", "causal_stage": "EXTRACTING"},
    "evidence": [{"path": "src/x/NumberFormat.cpp", "detail": "trigraph '??/' is fatal"}],
    "claim": f"At revision {REVISION}, {REPOSITORY}'s own install_command:cmake is UNRESOLVED.",
    "suggested_issue_title": f"install_command:cmake is UNRESOLVED at {REVISION[:12]}",
    "suggested_issue_body": "repository-presenter's validation pipeline found this.\n",
    "status": "HANDOFF_PENDING",
    "issue_ref": None,
    "close_reason": None,
}


@pytest.fixture(autouse=True)
def _no_live_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every upstream call these tests reach is an injected fake: the marker lookup finds nothing
    by default, the recheck confirms the defect still fires, and any PATCH is recorded, never sent.
    A test that needs a different answer overrides the one name it cares about."""
    monkeypatch.setattr(cli, "find_issue_with_marker", lambda *a, **k: None)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setattr(cli, "default_patch", _RecordingCreate(status_code=200, body={}))
    monkeypatch.setattr(cli, "default_post", _RecordingCreate())


@pytest.fixture
def project_with_handoff(project: Path) -> Path:
    handoff_dir = project / "evidence" / "upstream-defects" / REPO_DIR
    handoff_dir.mkdir(parents=True)
    (handoff_dir / f"{FINGERPRINT}.json").write_text(
        json.dumps(HANDOFF_PAYLOAD, indent=2) + "\n", encoding="utf-8"
    )
    return project


class _RecordingCreate:
    def __init__(self, status_code: int = 201, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body if body is not None else {"number": 7, "html_url": "https://x/issues/7"}

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


def _fires_true(handoff: object) -> object:
    from repository_presenter.components.issues.redetect import RedetectionResult

    return RedetectionResult(
        repository=REPOSITORY,
        defect_fingerprint=f"sha256:{FINGERPRINT}",
        triggering_check_id="BC-02",
        checked_at="2026-09-27T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=True,
        note="still fires",
        fresh_evidence=(),
        proposed_status=None,
    )


def test_dry_run_without_file_flag_writes_nothing_and_says_so(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "would file" in out
    assert "dry run" in out


def test_file_without_authorization_writes_nothing(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "not authorized" in out
    assert AUTHORIZATION_VARIABLE in out


def test_file_authorized_with_token_and_confirmed_recheck_writes_and_updates_the_artifact(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_OK
    assert len(create.calls) == 1
    url, token, payload = create.calls[0]
    assert url == f"https://api.github.com/repos/{REPOSITORY}/issues"
    assert token == "fake-write-token-for-this-test-only"
    assert payload["title"] == HANDOFF_PAYLOAD["suggested_issue_title"]
    out = capsys.readouterr().out
    assert "filed=True" in out
    assert "now FILED" in out

    handoff_path = (
        project_with_handoff / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"
    )
    updated = load_handoff(handoff_path)
    assert updated.status == "FILED"
    assert updated.issue_ref is not None
    assert updated.issue_ref.number == 7
    assert updated.issue_ref.url == "https://x/issues/7"


def test_file_aborts_when_recheck_says_the_defect_no_longer_fires(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from repository_presenter.components.issues.redetect import RedetectionResult

    def fires_false(handoff: object) -> RedetectionResult:
        return RedetectionResult(
            repository=REPOSITORY,
            defect_fingerprint=f"sha256:{FINGERPRINT}",
            triggering_check_id="BC-02",
            checked_at="2026-09-27T00:00:00+00:00",
            checked_at_revision=REVISION,
            revision_drifted=False,
            still_fires=False,
            note="no longer fires: upstream fixed it",
            fresh_evidence=(),
            proposed_status=None,
        )

    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", fires_false)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "no longer fires" in out
    handoff_path = (
        project_with_handoff / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"
    )
    assert load_handoff(handoff_path).status == "HANDOFF_PENDING"


def test_a_second_file_run_never_double_files_the_same_handoff(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    first = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])
    capsys.readouterr()
    second = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert first == EXIT_OK
    assert second == EXIT_OK
    assert len(create.calls) == 1
    out = capsys.readouterr().out
    assert "skip - status is 'FILED'" in out


def test_no_handoffs_on_record_is_reported_plainly(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["file-upstream-defects", "--root", str(project)])
    assert exit_code == EXIT_OK
    assert "no handoffs on record" in capsys.readouterr().out


def test_repo_filter_reports_plainly_when_nothing_matches(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--repo",
            "someone-else/unrelated",
        ]
    )
    assert exit_code == EXIT_OK
    assert "no handoff found for 'someone-else/unrelated'" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The scheduled run: dedup across fresh checkouts, failure isolation, the gated close, and the
# matrix the workflow fans out over.
# ---------------------------------------------------------------------------

OTHER_REPO = "acme-org/second-repo"
OTHER_FINGERPRINT = "c" * 64


def _write_second_handoff(project: Path) -> None:
    payload = {
        **HANDOFF_PAYLOAD,
        "repository": OTHER_REPO,
        "defect_fingerprint": f"sha256:{OTHER_FINGERPRINT}",
        "suggested_issue_title": "second, independent defect",
        "suggested_issue_body": "independent finding\n",
    }
    directory = project / "evidence" / "upstream-defects" / "acme-org__second-repo"
    directory.mkdir(parents=True)
    (directory / f"{OTHER_FINGERPRINT}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _handoff_path(project: Path) -> Path:
    return project / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"


def _write_filed_handoff(project: Path, *, number: int = 7) -> None:
    payload = {
        **HANDOFF_PAYLOAD,
        "status": "FILED",
        "issue_ref": {"number": number, "url": f"https://x/issues/{number}"},
    }
    _handoff_path(project).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _resolved_not_planned(handoff: object) -> object:
    from repository_presenter.components.issues.redetect import RedetectionResult

    return RedetectionResult(
        repository=REPOSITORY,
        defect_fingerprint=f"sha256:{FINGERPRINT}",
        triggering_check_id="BC-02",
        checked_at="2026-10-04T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=False,
        note="no longer fires",
        fresh_evidence=(),
        proposed_status="RESOLVED_UPSTREAM",
        proposed_close_reason="not planned",
    )


def test_a_second_run_from_a_fresh_checkout_files_nothing_when_the_upstream_issue_exists(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from repository_presenter.components.issues.model import IssueRef

    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(
        cli, "find_issue_with_marker", lambda *a, **k: _Found(number=7, url="https://x/issues/7")
    )
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_OK
    assert create.calls == []
    assert "already filed" in capsys.readouterr().out
    updated = load_handoff(_handoff_path(project_with_handoff))
    assert updated.status == "FILED"
    assert updated.issue_ref == IssueRef(number=7, url="https://x/issues/7")


def test_a_failed_filing_for_one_handoff_does_not_stop_the_others(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    failing = _RecordingCreate(status_code=500, body={"message": "boom"})
    succeeding = _RecordingCreate()

    def route(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        if f"/repos/{REPOSITORY}/" in url:
            return failing(url, token, payload)
        return succeeding(url, token, payload)

    monkeypatch.setattr(cli, "default_post", route)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert len(failing.calls) == 1
    assert len(succeeding.calls) == 1
    assert exit_code != EXIT_OK
    assert load_handoff(_handoff_path(project_with_handoff)).status == "HANDOFF_PENDING"
    other = project_with_handoff / "evidence" / "upstream-defects" / "acme-org__second-repo"
    assert load_handoff(other / f"{OTHER_FINGERPRINT}.json").status == "FILED"
    assert "filed=True" in capsys.readouterr().out


def test_a_resolved_filed_handoff_is_closed_with_its_close_reason(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_filed_handoff(project_with_handoff)
    patch = _RecordingCreate(status_code=200, body={"state": "closed"})
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "redetect", _resolved_not_planned)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["redetect-upstream-defects", "--root", str(project_with_handoff), "--close"])

    assert exit_code == EXIT_OK
    assert len(patch.calls) == 1
    url, token, payload = patch.calls[0]
    assert url == f"https://api.github.com/repos/{REPOSITORY}/issues/7"
    assert token == "fake-write-token-for-this-test-only"
    assert payload == {"state": "closed", "state_reason": "not_planned"}
    updated = load_handoff(_handoff_path(project_with_handoff))
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "not planned"
    assert updated.issue_ref is not None and updated.issue_ref.number == 7
    assert "fake-write-token-for-this-test-only" not in capsys.readouterr().out


def test_close_without_the_gate_makes_no_call_and_says_what_it_would_close(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_filed_handoff(project_with_handoff)
    patch = _RecordingCreate(status_code=200, body={"state": "closed"})
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "redetect", _resolved_not_planned)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(["redetect-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    assert patch.calls == []
    out = capsys.readouterr().out
    assert "would close #7" in out
    assert load_handoff(_handoff_path(project_with_handoff)).status == "FILED"


def test_the_dry_run_names_each_handoff_it_would_file_with_the_gate_unset(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "would file" in out
    assert HANDOFF_PAYLOAD["suggested_issue_title"] in out
    assert "second, independent defect" in out
    assert AUTHORIZATION_VARIABLE in out


def test_issue_targets_lists_each_repository_with_pending_or_filed_handoffs_as_json(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    exit_code = main(["issue-targets", "--root", str(project_with_handoff)])
    assert exit_code == EXIT_OK
    targets = json.loads(capsys.readouterr().out)
    assert targets == [
        {"repo": OTHER_REPO, "owner": "acme-org", "name": "second-repo"},
        {"repo": REPOSITORY, "owner": "aspose-cells-foss", "name": "Aspose.Cells-FOSS-for-Cpp"},
    ]


def test_issue_targets_is_an_empty_list_when_nothing_is_actionable(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["issue-targets", "--root", str(project)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []


class _Found:
    """Stands in for a ``CreatedIssue`` returned by the upstream marker lookup."""

    def __init__(self, *, number: int, url: str) -> None:
        self.number = number
        self.url = url
