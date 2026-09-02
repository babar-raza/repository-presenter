"""Bounded subprocesses: no interactive stdin, and a timeout kills the tree and returns 124."""

from __future__ import annotations

import sys

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
