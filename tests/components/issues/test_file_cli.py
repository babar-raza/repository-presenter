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
}


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
