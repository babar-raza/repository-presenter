"""The registry write gate at the two CLI entry points that are not ``propose``: a ``dry_run``
registry entry may produce a dry-run result and nothing else, so ``metadata --apply`` and
``file-upstream-defects --file`` are refused for it before any GitHub call, even fully armed.
(``propose`` is covered in ``tests/components/propose/test_cli.py``.)"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, main
from repository_presenter.components.issues.file import AUTHORIZATION_VARIABLE as ISSUES_VARIABLE
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.components.metadata.apply import (
    AUTHORIZATION_VARIABLE as METADATA_VARIABLE,
)
from support import monitor_registry_entry, write_registry_file

DRY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
FULL = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
FINGERPRINT = "b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365"


@pytest.fixture
def control(project: Path) -> Path:
    write_registry_file(
        project,
        [
            monitor_registry_entry(DRY, mode="dry_run", repository_id=1),
            monitor_registry_entry(FULL, mode="full", repository_id=2),
        ],
    )
    return project


def _fail(*args: object, **kwargs: object) -> Any:
    raise AssertionError("a refused write must make no GitHub call")


def test_metadata_apply_is_refused_for_a_dry_run_entry_before_any_github_call(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("capture_repo_metadata", "default_patch", "default_put"):
        monkeypatch.setattr(cli, name, _fail)
    monkeypatch.setenv(METADATA_VARIABLE, "1")
    monkeypatch.setenv("GH_METADATA_WRITE_TOKEN", "ghs_fake-token-for-this-test-only")

    exit_code = main(["metadata", "--repo", DRY, "--root", str(control), "--apply"])

    assert exit_code == EXIT_UNSAFE
    err = capsys.readouterr().err
    assert "registry_dry_run" in err
    assert "dry_run" in err


def test_metadata_without_apply_still_runs_for_a_dry_run_entry(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dry_run entry gets its dry-run result: the observation is captured, nothing is written."""
    from repository_presenter.core.github.client import ObservedRepository

    monkeypatch.setattr(
        cli,
        "capture_repo_metadata",
        lambda entry, *, token: ObservedRepository(
            repository=entry.repository,
            description=None,
            homepage=None,
            topics=(),
            observed_at="2026-10-05T00:00:00Z",
        ),
    )
    monkeypatch.setattr(cli, "default_patch", _fail)
    monkeypatch.setattr(cli, "default_put", _fail)

    assert main(["metadata", "--repo", DRY, "--root", str(control)]) == EXIT_OK
    assert "observed:" in capsys.readouterr().out


def _handoff(root: Path, repository: str) -> None:
    owner, name = repository.split("/", 1)
    directory = root / "evidence" / "upstream-defects" / f"{owner}__{name}"
    directory.mkdir(parents=True)
    payload = {
        "schema_version": 1,
        "repository": repository,
        "source_revision": REVISION,
        "defect_fingerprint": f"sha256:{FINGERPRINT}",
        "triggering_check": {"id": "BC-02", "version": "3", "causal_stage": "EXTRACTING"},
        "evidence": [{"path": "src/x.cpp", "detail": "fatal"}],
        "claim": "a defect",
        "suggested_issue_title": f"a defect in {name}",
        "suggested_issue_body": "body\n",
        "status": "HANDOFF_PENDING",
        "issue_ref": None,
        "close_reason": None,
    }
    (directory / f"{FINGERPRINT}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_issue_filing_skips_a_dry_run_entry_and_files_for_a_full_one(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _handoff(control, DRY)
    _handoff(control, FULL)
    posts: list[str] = []

    def post(url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        posts.append(url)
        return 201, {"number": 7, "html_url": "https://github.com/x/y/issues/7"}

    monkeypatch.setattr(cli, "default_post", post)
    monkeypatch.setattr(cli, "find_issue_with_marker", lambda *a, **k: None)
    monkeypatch.setattr(
        cli,
        "redetect",
        lambda handoff: RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id="BC-02",
            checked_at="2026-10-05T00:00:00+00:00",
            checked_at_revision=REVISION,
            revision_drifted=False,
            still_fires=True,
            note="still fires",
            fresh_evidence=(),
            proposed_status=None,
        ),
    )
    monkeypatch.setenv(ISSUES_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "ghs_fake-token-for-this-test-only")

    exit_code = main(["file-upstream-defects", "--root", str(control), "--file"])

    out = capsys.readouterr().out
    assert exit_code == EXIT_OK
    assert f"file: {DRY} not filed (registry_dry_run)" in out
    assert len(posts) == 1 and f"/repos/{FULL}/" in posts[0]  # only the full entry was written to


def test_a_dry_run_of_issue_filing_does_not_need_the_registry(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without ``--file`` nothing is written, so the gate does not apply and no registry is read."""
    _handoff(project, DRY)
    assert main(["file-upstream-defects", "--root", str(project)]) == EXIT_OK
