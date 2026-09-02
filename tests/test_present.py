"""``repository-presenter present``: admission from the registry before anything else."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_UNSAFE, EXIT_USAGE, main
from support import REPO_ROOT, write_cursor

CANARY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"


@pytest.fixture
def project_with_registry(project: Path) -> Path:
    (project / "data").mkdir()
    shutil.copy(REPO_ROOT / "data" / "registry.json", project / "data" / "registry.json")
    return project


def test_present_admits_the_canary_from_the_registry(
    project_with_registry: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    assert f"admitted: {CANARY} (mode dry_run, ecosystem python" in captured.out
    assert code == EXIT_INCONSISTENT
    assert "snapshot stage is not implemented" in captured.err


def test_present_refuses_a_repository_outside_the_allow_list(
    project_with_registry: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["present", "--repo", "some-org/Aspose.X-FOSS-for-Go", "--root", str(project_with_registry)]
    )
    captured = capsys.readouterr()
    assert code == EXIT_UNSAFE
    assert captured.out == ""
    assert "some-org/Aspose.X-FOSS-for-Go is not in the registry allow-list" in captured.err


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
