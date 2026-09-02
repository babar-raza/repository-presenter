"""The git wrapper pins determinism flags, disables prompts, and reports timeouts as results."""

from __future__ import annotations

import base64
import subprocess
from typing import Any

import pytest

from repository_presenter.core.git_safety import git as git_module
from repository_presenter.core.git_safety.git import github_https_auth_env, run_git


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
