"""Deterministic push-retry wrapper: fetch -> rebase -> push, bounded retries, never `--force`.

Written per `docs/investigations/05-production-autonomy.md` section 5's own highest-leverage
recommendation ("a small deterministic push wrapper (fetch -> rebase/merge -> retry N times
against `origin/main`... never against a shared local branch another live agent might be
editing)") and `docs/PRODUCTION_ROADMAP.md`'s WS5 ruling, which names this exact script (unbuilt,
unscheduled) as one of two queued hardening items closing failure class A (push races under
concurrent commits - `docs/DECISION_LOG.md` 2026-09-11 17:36/17:58 UTC, 2026-09-17 line 3457) at
its root.

Owner/reviewer tooling (`tools/README.md`'s boundary): never imported by `src/`, never read for an
acceptance predicate, never touched by the loop or a lane. It is invoked by hand (or by a future
CI job) at the moment an isolated worktree's branch needs to land on a shared target branch that
other concurrently-live write-capable agents may also be pushing to right now.

## What it does, per attempt

1. `git fetch <remote> <branch>`
2. `git -c merge.conflictstyle=diff3 rebase <remote>/<branch>` - diff3 style is required, not
   cosmetic: the auto-resolution below depends on seeing the common-ancestor text for a conflict
   hunk, which only diff3 style provides (plain conflict markers carry no base section, and this
   script treats that shape as "cannot prove it's a clean append" - see `_CONFLICT_RE`).
3. On a clean rebase, `git push <remote> HEAD:<branch>`. A rejection (non-fast-forward, another
   agent landed first) retries from step 1, bounded by `--max-retries`.
4. On a rebase conflict, this script does **not** attempt to auto-resolve arbitrary conflicts -
   that requires judgment. It detects exactly one narrow, well-defined case and handles nothing
   else automatically:

   Every conflicted file must be `docs/DECISION_LOG.md` and/or
   `docs/RESEARCH_AND_GUIDELINES.md` (`AUTO_RESOLVABLE_FILES`) - these two files already carry an
   established append-only convention (`AGENTS.md`'s own "keep both sides" rule for exactly these
   two files). Within each such file, every conflict hunk must be a clean append: both `ours` and
   `theirs` must start with the identical `base` text the diff3 marker records, i.e. neither side
   edited or removed anything the other side also touched - both sides only appended new content
   after a shared, unedited point (`_resolve_block`). If every conflicted file and every hunk in it
   meets that bar, both sides are kept, in chronological order when a `YYYY-MM-DD HH:MM`-shaped
   timestamp can be read from each side's new content (`_order_chronologically`), and only the
   conflict markers are removed - never a pick of one side over the other.

   Any other conflict - a different file, a hunk where a shared line was edited, markers with no
   base section - aborts the rebase (`git rebase --abort`) and reports the exact file(s) needing
   human/agent judgment. This script never guesses in the general case.

Never runs `--force` anywhere, on any git subcommand.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The two files this project's own convention (AGENTS.md) already treats as append-only, keep-
# both-sides on conflict. Nothing else is eligible for auto-resolution, ever - listed here, not
# inferred from a path pattern, so extending the set is a deliberate, reviewable one-line change.
AUTO_RESOLVABLE_FILES = frozenset(
    {
        "docs/DECISION_LOG.md",
        "docs/RESEARCH_AND_GUIDELINES.md",
    }
)

# Git exports these into every hook's environment and they outrank both cwd and -C, silently
# redirecting a command meant for the repository at `cwd` to some other repository - the exact
# mechanism behind failure class E in docs/investigations/05-production-autonomy.md (already fixed
# once, in src/repository_presenter/core/git_safety/git.py, for the product's own git wrapper).
# This script is a second, independent surface running the same risk (a caller's shell may already
# carry one of these from an outer hook), so it scrubs the same names before every git call.
_REPOSITORY_REDIRECTING_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)

# `git rebase --continue` must never block on an editor (no commit-message change is ever needed
# here); "true" is a real, no-op executable shipped with Git for Windows/Git Bash and every POSIX
# environment this project runs on.
_NO_EDITOR_ENV = {"GIT_EDITOR": "true", "GIT_SEQUENCE_EDITOR": "true"}

# Matches one diff3-style conflict hunk and captures its three sections. Requires the `|||||||`
# base section explicitly (see module docstring): a plain (non-diff3) marker set simply never
# matches, so a file with no diff3 base section is correctly treated as "not provably a clean
# append" by the caller, never guessed at.
_CONFLICT_RE = re.compile(
    r"^<<<<<<< [^\n]*\n"
    r"(?P<ours>.*?)"
    r"^\|\|\|\|\|\|\| [^\n]*\n"
    r"(?P<base>.*?)"
    r"^=======\n"
    r"(?P<theirs>.*?)"
    r"^>>>>>>> [^\n]*\n",
    re.MULTILINE | re.DOTALL,
)

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})")


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


def run_git(
    args: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> GitResult:
    """Run one `git` subprocess against the repository at `cwd`. Never raises on a non-zero exit -
    every caller here reads `.returncode` explicitly and decides what it means. Scrubs the
    repository-redirecting env vars (see `_REPOSITORY_REDIRECTING_ENV`) from both the inherited
    environment and any caller-supplied `env`, and merges `env` last so a caller's explicit choice
    (e.g. `_NO_EDITOR_ENV`) always wins over the inherited process environment."""
    full_env = {
        k: v for k, v in os.environ.items() if k not in _REPOSITORY_REDIRECTING_ENV
    }
    if env:
        full_env.update(
            {k: v for k, v in env.items() if k not in _REPOSITORY_REDIRECTING_ENV}
        )
    proc = subprocess.run(
        ["git", *args], cwd=cwd, env=full_env, capture_output=True, text=True
    )
    return GitResult(proc.returncode, proc.stdout, proc.stderr)


def conflicted_files(cwd: Path) -> list[str]:
    """Paths (repo-relative, forward-slash) currently unmerged, per `git diff --diff-filter=U`."""
    res = run_git(["diff", "--name-only", "--diff-filter=U"], cwd)
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


class AmbiguousConflictError(Exception):
    """A conflict is not the narrow, clean append-only shape this script may resolve on its own -
    some content shared with the base was itself changed (not merely followed by new material) on
    at least one side, or no diff3 base section was present to prove otherwise. The caller must
    abort the rebase and report this to a human/agent; nothing here ever guesses past it."""


def _extract_date_key(text: str) -> tuple[int, int, int, int, int] | None:
    match = _DATE_RE.search(text)
    if match is None:
        return None
    y, mo, d, h, mi = (int(g) for g in match.groups())
    return (y, mo, d, h, mi)


def _order_chronologically(extra_ours: str, extra_theirs: str) -> tuple[str, str]:
    """Return (first, second) in chronological order when both sides carry a recognizable
    `YYYY-MM-DD HH:MM`-shaped timestamp (`docs/DECISION_LOG.md`'s own entry format) near their
    start. When either side carries no such timestamp, or the two are equal, falls back to a
    stable, documented default (ours first) - a fallback ordering, not a guess at a fact neither
    side states."""
    key_ours = _extract_date_key(extra_ours)
    key_theirs = _extract_date_key(extra_theirs)
    if key_ours is not None and key_theirs is not None and key_theirs < key_ours:
        return extra_theirs, extra_ours
    return extra_ours, extra_theirs


def _resolve_block(ours: str, base: str, theirs: str) -> str:
    """Resolve one conflict hunk's three sections, or raise `AmbiguousConflictError`. Both `ours`
    and `theirs` must start with `base` verbatim - the only way to be certain neither side edited
    or removed anything the other side shares, without guessing."""
    if not (ours.startswith(base) and theirs.startswith(base)):
        raise AmbiguousConflictError(
            "a line shared with the common base was changed on at least one side - "
            "not a clean append-only conflict"
        )
    extra_ours = ours[len(base) :]
    extra_theirs = theirs[len(base) :]
    if extra_ours.strip("\n") == extra_theirs.strip("\n"):
        # Identical content landed on both sides (e.g. a retried push already carrying the same
        # entry) - keep one copy, never a duplicate.
        return base + extra_ours
    first, second = _order_chronologically(extra_ours, extra_theirs)
    return base + first + second


def try_resolve_append_only_conflicts(text: str) -> str:
    """Resolve every clean append-only conflict hunk in `text`, keeping both sides in
    chronological order and removing only the conflict markers. Raises `AmbiguousConflictError`
    (leaving `text` and the file on disk untouched by the caller) the moment any hunk is not a
    clean append - never writes a partial resolution."""
    if _CONFLICT_RE.search(text) is None:
        raise AmbiguousConflictError(
            "no diff3-style conflict markers found (no '|||||||' base section) - "
            "cannot prove this is a clean append without the common-ancestor text"
        )

    def _sub(match: re.Match[str]) -> str:
        return _resolve_block(
            match.group("ours"), match.group("base"), match.group("theirs")
        )

    # re.sub calls `_sub` eagerly for every match before returning; a raise inside `_sub`
    # propagates immediately, so this function either returns a fully-resolved string or raises -
    # never a partially-resolved one.
    return _CONFLICT_RE.sub(_sub, text)


def auto_resolve_conflicts(cwd: Path) -> tuple[bool, str]:
    """Attempt the narrow append-only auto-resolution across every currently conflicted file.

    On success: every conflicted file has been rewritten and `git add`-ed, and (True, "") is
    returned. On failure: **no file is modified**, and (False, <message>) is returned, naming the
    exact file(s) that need human/agent judgment - the caller must `git rebase --abort`."""
    files = conflicted_files(cwd)
    if not files:
        return (
            False,
            "rebase failed with no conflicted files reported - nothing to auto-resolve",
        )

    ineligible = sorted(f for f in files if f not in AUTO_RESOLVABLE_FILES)
    if ineligible:
        return False, (
            "conflict outside the narrow docs/DECISION_LOG.md / "
            "docs/RESEARCH_AND_GUIDELINES.md append-only case - needs human/agent judgment: "
            + ", ".join(ineligible)
        )

    resolved: dict[str, str] = {}
    for rel_path in files:
        text = (cwd / rel_path).read_text(encoding="utf-8")
        try:
            resolved[rel_path] = try_resolve_append_only_conflicts(text)
        except AmbiguousConflictError as exc:
            return False, f"{rel_path}: {exc} - needs human/agent judgment"

    for rel_path, new_text in resolved.items():
        (cwd / rel_path).write_text(new_text, encoding="utf-8", newline="\n")
        run_git(["add", "--", rel_path], cwd)

    return True, ""


def push_with_retry(
    cwd: Path,
    *,
    branch: str = "main",
    remote: str = "origin",
    max_retries: int = 5,
) -> int:
    """Fetch -> rebase -> push against `<remote>/<branch>`, up to `max_retries` attempts. Returns
    a process-style exit code (0 success, 1 failure). Never passes `--force` to any git command."""
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")

    for attempt in range(1, max_retries + 1):
        print(
            f"[push_retry] attempt {attempt}/{max_retries}: git fetch {remote} {branch}"
        )
        fetch = run_git(["fetch", remote, branch], cwd)
        if fetch.returncode != 0:
            print(f"[push_retry] fetch failed, will retry: {fetch.stderr.strip()}")
            continue

        rebase = run_git(
            ["-c", "merge.conflictstyle=diff3", "rebase", f"{remote}/{branch}"],
            cwd,
            env=_NO_EDITOR_ENV,
        )
        while rebase.returncode != 0:
            files = conflicted_files(cwd)
            if not files:
                # A rebase failure with nothing conflicted is not this script's narrow case to
                # handle (dirty tree, hook failure, etc.) - abort cleanly and report, not retryable.
                print(
                    f"[push_retry] rebase failed for a non-conflict reason:\n{rebase.stderr}"
                )
                run_git(["rebase", "--abort"], cwd)
                return 1
            ok, message = auto_resolve_conflicts(cwd)
            if not ok:
                run_git(["rebase", "--abort"], cwd)
                print(
                    f"[push_retry] ABORTED (rebase --abort run, nothing landed): {message}"
                )
                return 1
            print(
                f"[push_retry] auto-resolved append-only conflict in: {', '.join(files)}"
            )
            rebase = run_git(["rebase", "--continue"], cwd, env=_NO_EDITOR_ENV)

        push = run_git(["push", remote, f"HEAD:{branch}"], cwd)
        if push.returncode == 0:
            print(f"[push_retry] pushed cleanly on attempt {attempt}/{max_retries}")
            return 0
        print(
            f"[push_retry] push rejected on attempt {attempt}/{max_retries}, will retry: "
            f"{push.stderr.strip()}"
        )

    print(
        f"[push_retry] FAILED: exhausted {max_retries} attempt(s) without a clean push"
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic push-retry wrapper: fetch -> rebase -> push, bounded retries, never "
            "--force. Auto-resolves only a clean, append-only conflict confined to "
            "docs/DECISION_LOG.md and/or docs/RESEARCH_AND_GUIDELINES.md; any other conflict "
            "aborts and names the file(s) needing human/agent judgment."
        )
    )
    parser.add_argument(
        "--branch", default="main", help="target branch (default: main)"
    )
    parser.add_argument(
        "--remote", default="origin", help="remote name (default: origin)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=5, help="bounded retry count (default: 5)"
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="repository working directory (default: current directory)",
    )
    args = parser.parse_args(argv)
    return push_with_retry(
        Path(args.cwd).resolve(),
        branch=args.branch,
        remote=args.remote,
        max_retries=args.max_retries,
    )


if __name__ == "__main__":
    sys.exit(main())
