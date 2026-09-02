"""The execution boundary: no inherited credentials, no stdin, hard timeout, redacted output."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from repository_presenter.core.execution import execute, secret_free_environment


def test_environment_is_an_allow_list_without_credential_like_names() -> None:
    clean = secret_free_environment(
        {
            "PATH": "/usr/bin",
            "HOME": "/home/x",
            "GH_TOKEN": "ghp_secret_value_1234567890",
            "LLM_API_KEY": "sk-secret",
            "MY_PASSWORD": "hunter2",
            "RANDOM_VAR": "not allowed either",
            "SystemRoot": "C:/Windows",
        }
    )
    assert set(clean) == {
        "PATH",
        "HOME",
        "SystemRoot",
        "CI",
        "GIT_TERMINAL_PROMPT",
        "GCM_INTERACTIVE",
        "PYTHONDONTWRITEBYTECODE",
    }
    assert clean["CI"] == "true"


def test_examples_run_without_secrets_and_their_output_is_redacted(tmp_path: Path) -> None:
    script = tmp_path / "leak.py"
    script.write_text(
        "import os, sys\n"
        "print('token' in ' '.join(os.environ).lower())\n"
        "print('GH_TOKEN' in os.environ)\n"
        "print('here is ghp_secret_value_1234567890 and sk-anotherSecretValue')\n"
        "print(repr(sys.stdin.read()))\n",
        encoding="utf-8",
    )
    result = execute(
        [sys.executable, "-I", str(script)],
        workspace=tmp_path,
        timeout_seconds=60,
        base_environment={"PATH": "x", "GH_TOKEN": "ghp_secret_value_1234567890"},
        extra_environment={"SYSTEMROOT": "C:/Windows", "PATH": __import__("os").environ["PATH"]},
    )
    assert result.return_code == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "False"
    assert lines[1] == "False"
    assert lines[2] == "here is [REDACTED] and [REDACTED]"
    assert lines[3] == "''"
    assert "ghp_secret_value_1234567890" not in result.stdout + result.stderr
    assert "GH_TOKEN" not in result.environment_names


def test_timeout_kills_the_example_and_is_recorded(tmp_path: Path) -> None:
    result = execute(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        workspace=tmp_path,
        timeout_seconds=1,
        extra_environment={"SYSTEMROOT": "C:/Windows"},
    )
    assert result.timed_out
    assert result.return_code == 124


@pytest.mark.parametrize(
    ("argv", "timeout", "message"),
    [
        ([], 10, "must identify an executable"),
        (["python"], 0, "timeout must be within"),
        (["python"], 301, "timeout must be within"),
    ],
)
def test_invalid_requests_are_rejected(
    tmp_path: Path, argv: list[str], timeout: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        execute(argv, workspace=tmp_path, timeout_seconds=timeout)


def test_missing_workspace_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workspace does not exist"):
        execute(["python"], workspace=tmp_path / "nope", timeout_seconds=5)
