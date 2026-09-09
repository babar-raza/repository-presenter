"""Bounded subprocesses: no interactive stdin, and a timeout kills the tree and returns 124."""

from __future__ import annotations

import subprocess
import sys
import time

import pytest

from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE, run_bounded


def test_completed_process_carries_decoded_output() -> None:
    result = run_bounded(
        [sys.executable, "-c", "print('out'); import sys; sys.exit(3)"], timeout=30
    )
    assert result.returncode == 3
    assert result.stdout.strip() == "out"


def test_stdin_is_closed_so_a_prompt_cannot_block() -> None:
    result = run_bounded(
        [sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"], timeout=30
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "''"


def test_timeout_returns_exit_124_instead_of_raising() -> None:
    result = run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.5)
    assert result.returncode == TIMEOUT_EXIT_CODE


def test_a_cancellation_during_communicate_still_kills_the_process_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TB-08, external review D8, 2026-09-08: only ``TimeoutExpired`` was ever cleaned up - any
    other exception escaping ``communicate()``, ``KeyboardInterrupt`` included, used to leak the
    child process tree."""
    captured: dict[str, subprocess.Popen[bytes]] = {}
    original_communicate = subprocess.Popen.communicate

    def raising_communicate(
        self: subprocess.Popen[bytes], *args: object, **kwargs: object
    ) -> object:
        captured["process"] = self
        monkeypatch.setattr(subprocess.Popen, "communicate", original_communicate)
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess.Popen, "communicate", raising_communicate)
    with pytest.raises(KeyboardInterrupt):
        run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], timeout=30)

    process = captured["process"]
    for _ in range(50):
        if process.poll() is not None:
            break
        time.sleep(0.1)
    assert process.poll() is not None, "the child process was left running after cancellation"
