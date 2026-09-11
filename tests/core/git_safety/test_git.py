"""The git wrapper pins determinism flags, disables prompts, and reports timeouts as results.

It also refuses to let an inherited ``GIT_DIR`` (or any of its repository-redirecting siblings)
send a command meant for the repository at ``cwd`` somewhere else - the defect measured on
2026-09-11 as fixture commits on live branches, a rewritten identity, and ``core.bare`` flipped
on this very checkout (RESEARCH_AND_GUIDELINES.md section 29, G4-W17 arrival item 55). The
controls at the end exercise real git, not a spy: one for the wrapper, one for the fixture that
builds every disposable repository through it.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.git_safety import git as git_module
from repository_presenter.core.git_safety.git import (
    REPOSITORY_REDIRECTING_ENV,
    github_https_auth_env,
    run_git,
)
from support import head_revision, init_git_repository


def _spy(monkeypatch: pytest.MonkeyPatch, returncode: int = 0) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_run_bounded(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(args=args, returncode=returncode, stdout="", stderr="")

    monkeypatch.setattr(git_module, "run_bounded", fake_run_bounded)
    return captured


def test_every_call_pins_determinism_and_long_path_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _spy(monkeypatch)
    run_git(["fetch", "origin", "main"])
    assert captured["args"] == [
        "git",
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.eol=lf",
        "-c",
        "core.longpaths=true",
        "fetch",
        "origin",
        "main",
    ]


def test_prompt_suppression_is_present_and_cannot_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _spy(monkeypatch)
    run_git(["status"], env={"GIT_TERMINAL_PROMPT": "1", "GCM_INTERACTIVE": "auto", "X": "y"})
    assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert captured["env"]["GCM_INTERACTIVE"] == "never"
    assert captured["env"]["X"] == "y"


def test_repository_redirecting_variables_never_reach_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Neither the inherited environment nor a caller's ``env`` can redirect the wrapper."""
    assert set(REPOSITORY_REDIRECTING_ENV) >= {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_NAMESPACE",
    }
    captured = _spy(monkeypatch)
    for name in REPOSITORY_REDIRECTING_ENV:
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    monkeypatch.setenv("GIT_AUTHOR_NAME", "kept")

    run_git(["status"], cwd=tmp_path, env={"GIT_DIR": str(tmp_path / "explicit"), "X": "y"})

    assert not set(captured["env"]) & set(REPOSITORY_REDIRECTING_ENV)
    assert captured["env"]["GIT_AUTHOR_NAME"] == "kept"
    assert captured["env"]["X"] == "y"


def test_a_fixture_shaped_commit_under_an_exported_git_dir_lands_in_its_own_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Real git, the measured shape: ``git init`` + config + commit in a throwaway directory while
    ``GIT_DIR`` names a surrounding repository - as every hook environment does. The commit must
    land in the throwaway directory; the surrounding HEAD, identity, and ``core.bare`` stay put."""
    surrounding = init_git_repository(tmp_path / "surrounding")
    assert run_git(["config", "user.name", "Owner"], cwd=surrounding).returncode == 0
    head_before = head_revision(surrounding)
    monkeypatch.setenv("GIT_DIR", str(surrounding / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(surrounding))
    monkeypatch.setenv("GIT_INDEX_FILE", str(surrounding / ".git" / "index"))

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        result = run_git(args, cwd=fixture)
        assert result.returncode == 0, result.stderr
        assert "re-init" not in result.stderr, result.stderr
    (fixture / "README.md").write_text("# fixture\n", encoding="utf-8")
    assert run_git(["add", "."], cwd=fixture).returncode == 0
    commit = run_git(["commit", "-q", "-m", "seed"], cwd=fixture)
    assert commit.returncode == 0, commit.stderr

    assert (fixture / ".git").is_dir()
    own_dir = run_git(["rev-parse", "--absolute-git-dir"], cwd=fixture).stdout.strip()
    assert Path(own_dir).resolve() == (fixture / ".git").resolve()
    assert head_revision(fixture) != head_before
    assert head_revision(surrounding) == head_before
    assert run_git(["config", "user.name"], cwd=surrounding).stdout.strip() == "Owner"
    assert run_git(["config", "--bool", "core.bare"], cwd=surrounding).stdout.strip() == "false"


def test_the_fixture_refuses_a_directory_git_already_resolves_inside_a_repository(
    tmp_path: Path,
) -> None:
    """``init_git_repository`` never trusts ``git init``'s exit status: a target that git already
    resolves inside some repository is refused before any command runs, and that repository is
    left exactly as it was."""
    outer = init_git_repository(tmp_path / "outer")
    head_before = head_revision(outer)

    with pytest.raises(RuntimeError, match="already resolves it inside"):
        init_git_repository(outer / "nested")

    assert head_revision(outer) == head_before
    assert not (outer / "nested" / ".git").exists()
    assert run_git(["status", "--porcelain"], cwd=outer).stdout == ""


def test_timeout_is_a_failed_result_not_an_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _spy(monkeypatch, returncode=124)
    result = run_git(["clone", "https://example.invalid/x.git"], timeout=0.01)
    assert result.returncode == 124
    assert "timed out after 0.01s" in result.stderr


def test_github_auth_env_never_exposes_the_raw_token() -> None:
    assert github_https_auth_env(None) == {}
    env = github_https_auth_env("private-read-token")
    assert env["GIT_CONFIG_COUNT"] == "1"
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
    assert env["GIT_CONFIG_VALUE_0"].startswith("AUTHORIZATION: basic ")
    assert "private-read-token" not in env["GIT_CONFIG_VALUE_0"]
    encoded = env["GIT_CONFIG_VALUE_0"].split()[-1]
    assert base64.b64decode(encoded) == b"x-access-token:private-read-token"
