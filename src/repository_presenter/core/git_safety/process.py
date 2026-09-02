"""Run subprocesses without an interactive stdin and kill the whole process tree on timeout."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

TIMEOUT_EXIT_CODE = 124


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate exactly the process tree that :func:`run_bounded` created."""
    if sys.platform == "win32":
        killer = subprocess.Popen(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            killer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            killer.kill()
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    if process.poll() is None:
        process.kill()


def run_bounded(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``args`` with a closed stdin; a timeout kills descendants and returns exit 124."""
    popen_kwargs: dict[str, Any] = {
        "cwd": str(cwd) if cwd else None,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "env": env,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process: subprocess.Popen[bytes] = subprocess.Popen(args, **popen_kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(
            args=args,
            returncode=process.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            stdout, stderr = b"", b""
        return subprocess.CompletedProcess(
            args=args,
            returncode=TIMEOUT_EXIT_CODE,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )
