"""The official entry point: ``--version``, ``status``, and ``present``."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import __version__, cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_UNSAFE, EXIT_USAGE, main
from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety.clone import ReadOnlyClone, pinned_read_only_clone
from repository_presenter.core.git_safety.verify import PushBlockProof
from support import REPO_ROOT, commit_all, init_git_repository, write_bundle, write_cursor

STATUS = r"\((READY|IN_PROGRESS|VERIFYING|ACCEPTED|BLOCKED_EXTERNAL|FAILED_INTERNAL)\)"
CANARY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REVISION = "f" * 40


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


@pytest.fixture
def project_with_registry(project: Path) -> Path:
    (project / "data").mkdir()
    shutil.copy(REPO_ROOT / "data" / "registry.json", project / "data" / "registry.json")
    return project


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stand in for the network clone; records every call it receives."""
    calls: list[dict[str, Any]] = []

    def fake(clone_url: str, destination: Path, **kwargs: Any) -> ReadOnlyClone:
        calls.append({"clone_url": clone_url, "destination": destination, **kwargs})
        proof = PushBlockProof(True, "DISABLED", clone_url, True, True, None, "ok")
        return ReadOnlyClone(path=destination, clone_url=clone_url, revision=REVISION, proof=proof)

    monkeypatch.setattr(cli, "pinned_read_only_clone", fake)
    return calls


@pytest.fixture
def local_canary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Serve the canary's clone URL from a local repository through the real clone contract."""
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_bytes(b"# Aspose.3D for Python\n\nOriginal bytes.\n")
    (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = commit_all(source, "seed")
    calls: list[dict[str, Any]] = []

    def serve_locally(clone_url: str, destination: Path, **kwargs: Any) -> ReadOnlyClone:
        calls.append({"clone_url": clone_url, "destination": destination, **kwargs})
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(cli, "pinned_read_only_clone", serve_locally)
    return {"source": source, "revision": revision, "calls": calls}


def test_present_admits_clones_and_captures_the_source_snapshot(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GH_TOKEN", "ghp_read_only_token_value")
    revision = local_canary["revision"]
    clone_dir = "runs/clones/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    source_dir = f"runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-Python/{revision}/source"

    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])

    captured = capsys.readouterr()
    assert f"admitted: {CANARY} (mode dry_run, ecosystem python" in captured.out
    assert f"snapshot: {CANARY} at {revision} in {clone_dir} (push disabled, verified)" in (
        captured.out
    )
    source_line = next(line for line in captured.out.splitlines() if line.startswith("source: "))
    assert source_line.startswith(
        f"source: {source_dir} (3 files, 2 tree entries, readme README.md"
    )
    assert code == EXIT_INCONSISTENT
    assert "facts stage is not implemented" in captured.err
    assert local_canary["calls"] == [
        {
            "clone_url": f"https://github.com/{CANARY}.git",
            "destination": project_with_registry / Path(clone_dir),
            "token": "ghp_read_only_token_value",
        }
    ]
    assert "ghp_read_only_token_value" not in captured.out + captured.err
    written = project_with_registry / source_dir
    assert (written / "README.md").read_bytes() == b"# Aspose.3D for Python\n\nOriginal bytes.\n"
    assert (written / "tree.txt").read_text(encoding="utf-8").count("\n") == 2
    assert json.loads((written / "snapshot.json").read_text("utf-8"))["source_revision"] == revision


def test_present_rerun_on_the_same_revision_is_byte_identical(
    project_with_registry: Path, local_canary: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    first = [line for line in capsys.readouterr().out.splitlines() if line.startswith("source: ")]
    main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    second = [line for line in capsys.readouterr().out.splitlines() if line.startswith("source: ")]
    assert first == second
    assert "digest " in first[0]


def test_present_refuses_a_repository_outside_the_allow_list_before_cloning(
    project_with_registry: Path,
    fake_clone: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        ["present", "--repo", "some-org/Aspose.X-FOSS-for-Go", "--root", str(project_with_registry)]
    )
    captured = capsys.readouterr()
    assert code == EXIT_UNSAFE
    assert captured.out == ""
    assert "some-org/Aspose.X-FOSS-for-Go is not in the registry allow-list" in captured.err
    assert fake_clone == []


def test_present_reports_a_clone_that_cannot_be_proven_safe(
    project_with_registry: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> ReadOnlyClone:
        raise GitSafetyError("push is not proven blocked in the clone")

    monkeypatch.setattr(cli, "pinned_read_only_clone", refuse)
    assert main(["present", "--repo", CANARY, "--root", str(project_with_registry)]) == EXIT_UNSAFE
    assert "push is not proven blocked" in capsys.readouterr().err


def test_present_fails_closed_without_a_registry(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["present", "--repo", CANARY, "--root", str(project)]) == EXIT_USAGE
    assert "registry not found" in capsys.readouterr().err


def test_present_fails_closed_on_a_malformed_registry(
    project_with_registry: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = project_with_registry / "data" / "registry.json"
    document = json.loads(registry.read_text("utf-8"))
    document["entries"][0]["mode"] = "publish"
    registry.write_text(json.dumps(document), encoding="utf-8")
    assert main(["present", "--repo", CANARY, "--root", str(project_with_registry)]) == EXIT_USAGE
    assert "registry is malformed" in capsys.readouterr().err


def test_present_discovers_the_root_like_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["present", "--repo", CANARY]) == EXIT_USAGE
    assert "no project/state.yaml found at or above" in capsys.readouterr().err
    write_cursor(tmp_path)
    assert main(["present", "--repo", CANARY]) == EXIT_USAGE
    assert "registry not found" in capsys.readouterr().err
