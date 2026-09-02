"""The official entry point: ``repository-presenter --version`` and ``status``."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from repository_presenter import __version__
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_USAGE, main
from support import write_bundle, write_cursor

STATUS = r"\((READY|IN_PROGRESS|VERIFYING|ACCEPTED|BLOCKED_EXTERNAL|FAILED_INTERNAL)\)"


def test_version_flag_reports_program_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"repository-presenter {__version__}"


def test_status_reports_this_repository_cursor(
    repo_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status", "--root", str(repo_root)]) == EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"repository-presenter {__version__}"
    assert re.fullmatch(rf"gate: G\d_[A-Z_]+ {STATUS}", out[1])
    assert re.fullmatch(rf"work item: G\d-W\d\d {STATUS}", out[2])
    assert re.fullmatch(r"candidates: \d+/34 current reviewable no-op-proven", out[3])
    assert out[4] == "canary: aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def test_status_discovers_root_from_nested_working_directory(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    nested = project / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert main(["status"]) == EXIT_OK
    assert "candidates: 0/34 current reviewable no-op-proven" in capsys.readouterr().out


def test_status_without_cursor_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == EXIT_USAGE
    assert "no project/state.yaml found at or above" in capsys.readouterr().err
    assert main(["status", "--root", str(tmp_path)]) == EXIT_USAGE
    assert "no project/state.yaml under" in capsys.readouterr().err


def test_status_counts_each_repository_once(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    write_bundle(project, "owner__alpha", "bbb222", "READY_FOR_PROPOSAL")
    write_bundle(project, "owner__beta", "ccc333", "READY_FOR_PROPOSAL")
    write_cursor(project, recorded_candidates=2)
    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "candidates: 2/34" in capsys.readouterr().out


def test_status_ignores_unsealed_and_uncounted_bundles(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", None)
    write_bundle(project, "owner__beta", "bbb222", "ACCEPTED")
    write_bundle(project, "owner__gamma", "ccc333", "SUPERSEDED")
    write_bundle(project, "owner__delta", "ddd444", "INVALIDATED")
    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "candidates: 0/34" in capsys.readouterr().out


def test_status_flags_cursor_that_disagrees_with_disk(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    assert main(["status", "--root", str(project)]) == EXIT_INCONSISTENT
    captured = capsys.readouterr()
    assert "candidates: 1/34" in captured.out
    assert "cursor records 0 current candidates but 1 sealed on disk" in captured.err


def test_status_rejects_corrupt_bundle_manifest(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", None, raw="{not json")
    assert main(["status", "--root", str(project)]) == EXIT_INCONSISTENT
    assert "unreadable bundle manifest" in capsys.readouterr().err


def test_status_rejects_malformed_cursor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cursor = write_cursor(tmp_path)
    cursor.write_text("progress: [\n", encoding="utf-8")
    assert main(["status", "--root", str(tmp_path)]) == EXIT_INCONSISTENT
    assert "cursor is not valid YAML" in capsys.readouterr().err


def test_module_entry_point_matches_console_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "repository_presenter", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"repository-presenter {__version__}"
