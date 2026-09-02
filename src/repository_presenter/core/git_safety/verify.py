"""Independently re-derive proof that push is blocked, never by attempting a real push."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.hooks import BLOCK_MARKER
from repository_presenter.core.git_safety.neuter import DISABLED_PUSH_URL


@dataclass(frozen=True)
class PushBlockProof:
    """What the verifier observed; ``ok`` requires both controls to be in place."""

    ok: bool
    push_url: str | None
    fetch_url: str | None
    hook_installed: bool
    hook_contains_marker: bool
    executable_bit_set: bool | None
    detail: str


def verify_push_blocked(repo_path: Path) -> PushBlockProof:
    """Read the remote configuration and the hook from disk and judge both controls."""
    remote_result = run_git(["remote", "-v"], cwd=repo_path, timeout=10)
    push_url = None
    fetch_url = None
    for line in remote_result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "origin":
            if parts[2] == "(push)":
                push_url = parts[1]
            elif parts[2] == "(fetch)":
                fetch_url = parts[1]

    hook_path = repo_path / ".git" / "hooks" / "pre-push"
    hook_installed = hook_path.is_file()
    hook_text = hook_path.read_text(encoding="utf-8") if hook_installed else ""
    hook_contains_marker = BLOCK_MARKER in hook_text

    executable_bit_set: bool | None = None
    if sys.platform != "win32" and hook_installed:
        executable_bit_set = bool(hook_path.stat().st_mode & 0o111)

    ok = push_url == DISABLED_PUSH_URL and hook_installed and hook_contains_marker
    detail = (
        f"push_url={push_url!r} (expected {DISABLED_PUSH_URL!r}), "
        f"hook_installed={hook_installed}, hook_contains_marker={hook_contains_marker}"
    )
    if sys.platform == "win32":
        detail += ", executable_bit=not checked (no meaningful bit on NTFS)"
    return PushBlockProof(
        ok=ok,
        push_url=push_url,
        fetch_url=fetch_url,
        hook_installed=hook_installed,
        hook_contains_marker=hook_contains_marker,
        executable_bit_set=executable_bit_set,
        detail=detail,
    )
