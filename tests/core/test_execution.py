"""The execution boundary: no inherited credentials, no stdin, hard timeout, redacted output."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from repository_presenter.core.execution import (
    execute,
    profile_environment,
    secret_free_environment,
)


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


def test_extra_environment_is_filtered_for_credential_like_names_too(tmp_path: Path) -> None:
    """TB-08, external review D8, 2026-09-08: extra_environment used to be merged in raw after
    the base was filtered, so a caller-supplied credential-like name bypassed the boundary."""
    script = tmp_path / "leak.py"
    script.write_text(
        "import os\n"
        "print('MY_API_KEY' in os.environ)\n"
        "print(os.environ.get('CACHE_DIR'))\n"
        # Simulates the value leaking into output through some other channel entirely (a log
        # line, a traceback) - proving removed_secret_values covers extra_environment too, not
        # only whether the child's own os.environ carries the name.
        "print('leaked elsewhere: sk-injected-through-the-overlay')\n",
        encoding="utf-8",
    )
    result = execute(
        [sys.executable, "-I", str(script)],
        workspace=tmp_path,
        timeout_seconds=60,
        base_environment={"PATH": "x"},
        extra_environment={
            "SYSTEMROOT": "C:/Windows",
            "PATH": __import__("os").environ["PATH"],
            "MY_API_KEY": "sk-injected-through-the-overlay",
            "CACHE_DIR": "kept, not credential-shaped",
        },
    )
    assert result.return_code == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "False"  # MY_API_KEY never reached the child's environment
    assert lines[1] == "kept, not credential-shaped"  # a legitimate overlay name still passes
    assert "MY_API_KEY" not in result.environment_names
    assert "CACHE_DIR" in result.environment_names
    assert "sk-injected-through-the-overlay" not in result.stdout + result.stderr


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


def test_a_disposable_profile_points_every_toolchain_cache_inside_the_workspace(
    tmp_path: Path,
) -> None:
    """A verification reads no state a previous run left, and leaves none behind.

    RESEARCH_AND_GUIDELINES.md section 29.6 E5. The names are the ones a compiled toolchain
    actually writes through - NuGet, Cargo, Go, Gradle, npm - so a .NET or Rust verifier needs no
    redirection of its own; it adds this overlay and runs.
    """
    overlay = profile_environment(tmp_path)
    assert set(overlay) >= {
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "NUGET_PACKAGES",
        "CARGO_HOME",
        "GOMODCACHE",
        "GRADLE_USER_HOME",
        "PIP_CACHE_DIR",
    }
    assert all(Path(value).is_relative_to(tmp_path) for value in overlay.values())
    # A toolchain that finds its cache path missing writes to the real home instead, so the
    # directories exist before anything runs.
    assert all(Path(value).is_dir() for value in overlay.values())
    assert overlay["HOME"] == overlay["USERPROFILE"]
    # It is an overlay, not a replacement: the secret-free base still governs what is inherited.
    merged = {**secret_free_environment({"PATH": "p", "GH_TOKEN": "t"}), **overlay}
    assert "GH_TOKEN" not in merged and merged["CI"] == "true"
    assert merged["HOME"] == overlay["HOME"]
