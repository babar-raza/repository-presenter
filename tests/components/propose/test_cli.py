"""``repository-presenter propose`` wiring: dry-run by default, and, even with --propose, writes
nothing without the explicit authorization variable and a write-scoped token. No test here makes a
live GitHub call - every GitHub-facing function is monkeypatched on the ``cli`` module.

Uses ``--readme-file``/``--source-revision`` throughout (the disposable-target proof path) rather
than a registry-admitted sealed candidate, exactly as the real G6-W02 disposable-target exercise
would: no disposable test repository is registry-admitted, so there is no ``candidates/`` bundle to
read for it either.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.propose.effect import AUTHORIZATION_VARIABLE
from repository_presenter.core.github.client import (
    CommitOutcome,
    FileContents,
    PullRequestRef,
)
from repository_presenter.core.github.read_client import DefaultBranchRead

REPOSITORY = "babar-raza/disposable-target"
SOURCE_REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"


@pytest.fixture
def readme_file(tmp_path: Path) -> Path:
    path = tmp_path / "candidate-readme.md"
    path.write_text("# Disposable Target\n\nProposed content.\n", encoding="utf-8")
    return path


def _common_args(project: Path, readme_file: Path) -> list[str]:
    return [
        "propose",
        "--repo",
        REPOSITORY,
        "--root",
        str(project),
        "--readme-file",
        str(readme_file),
        "--source-revision",
        SOURCE_REVISION,
    ]


def test_readme_file_without_source_revision_is_a_usage_error(
    project: Path, readme_file: Path
) -> None:
    exit_code = main(
        ["propose", "--repo", REPOSITORY, "--root", str(project), "--readme-file", str(readme_file)]
    )
    assert exit_code != EXIT_OK


def test_dry_run_without_propose_flag_makes_no_github_call_at_all(
    project: Path,
    readme_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("dry run must make no GitHub call")

    monkeypatch.setattr(cli, "fetch_default_branch_sha", fail)
    monkeypatch.setattr(cli, "default_get_ref", fail)
    monkeypatch.setattr(cli, "default_put_contents", fail)

    exit_code = main(_common_args(project, readme_file))

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "dry run" in out
    assert "candidate_hash=" in out
    assert "source_revision=" + SOURCE_REVISION in out


def test_propose_without_authorization_writes_nothing(
    project: Path,
    readme_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("unauthorized propose must make no GitHub call")

    monkeypatch.setattr(cli, "fetch_default_branch_sha", fail)
    monkeypatch.setattr(cli, "default_get_ref", fail)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main([*_common_args(project, readme_file), "--propose"])

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "not authorized" in out


def test_propose_authorized_with_token_creates_branch_and_pr(
    project: Path,
    readme_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repo, *, token: DefaultBranchRead(repo, sha=SOURCE_REVISION, branch="main"),
    )

    create_ref_calls: list[tuple[str, str]] = []

    def fake_get_ref(owner: str, name: str, branch: str, *, token: str) -> str | None:
        assert token == "fake-write-token-for-this-test-only"
        if branch == "main":
            return "base-sha-1"
        return None  # presenter branch does not exist yet

    def fake_create_ref(owner: str, name: str, branch: str, sha: str, *, token: str) -> None:
        create_ref_calls.append((branch, sha))

    def fake_get_contents(
        owner: str, name: str, path: str, *, ref: str, token: str
    ) -> FileContents | None:
        return None  # nothing on the presenter branch yet

    put_calls: list[dict[str, Any]] = []

    def fake_put_contents(
        owner: str,
        name: str,
        path: str,
        *,
        branch: str,
        message: str,
        text: str,
        sha: str | None,
        token: str,
    ) -> CommitOutcome:
        put_calls.append({"branch": branch, "text": text, "sha": sha})
        return CommitOutcome(content_sha="newfilesha", commit_sha="newcommitsha")

    def fake_find_open_pull_request(
        owner: str, name: str, *, head_branch: str, token: str
    ) -> PullRequestRef | None:
        return None

    create_pr_calls: list[dict[str, Any]] = []

    def fake_create_pull_request(
        owner: str, name: str, *, title: str, body: str, head: str, base: str, token: str
    ) -> PullRequestRef:
        create_pr_calls.append({"title": title, "head": head, "base": base})
        return PullRequestRef(
            number=1, url=f"https://github.com/{owner}/{name}/pull/1", title=title, body=body
        )

    monkeypatch.setattr(cli, "default_get_ref", fake_get_ref)
    monkeypatch.setattr(cli, "default_create_ref", fake_create_ref)
    monkeypatch.setattr(cli, "default_get_contents", fake_get_contents)
    monkeypatch.setattr(cli, "default_put_contents", fake_put_contents)
    monkeypatch.setattr(cli, "default_find_open_pull_request", fake_find_open_pull_request)
    monkeypatch.setattr(cli, "default_create_pull_request", fake_create_pull_request)

    exit_code = main([*_common_args(project, readme_file), "--propose"])

    assert exit_code == EXIT_OK
    assert create_ref_calls == [("repository-presenter/readme-update", "base-sha-1")]
    assert len(put_calls) == 1
    assert put_calls[0]["text"] == "# Disposable Target\n\nProposed content.\n"
    assert len(create_pr_calls) == 1
    out = capsys.readouterr().out
    assert "effected=True" in out
    assert "https://github.com/babar-raza/disposable-target/pull/1" in out


def test_propose_blocks_on_a_stale_source_revision(
    project: Path,
    readme_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The authorization was minted for ``SOURCE_REVISION``; if the live default branch has moved
    on by the time the write is attempted, the effect must refuse - the "recheck immediately before
    an effect" acceptance bar."""
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    def moved(repo: str, *, token: str) -> DefaultBranchRead:
        return DefaultBranchRead(repo, sha="0" * 40, branch="main")

    monkeypatch.setattr(cli, "fetch_default_branch_sha", moved)

    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("a stale source must block before any write call")

    monkeypatch.setattr(cli, "default_create_ref", fail)
    monkeypatch.setattr(cli, "default_put_contents", fail)
    # get_ref is called for the base branch only after the recheck passes; here it never should be.
    monkeypatch.setattr(cli, "default_get_ref", fail)

    exit_code = main([*_common_args(project, readme_file), "--propose"])

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "stale source" in out
