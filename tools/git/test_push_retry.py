"""Regression tests for push_retry.py.

Run directly (`pytest tools/git/test_push_retry.py`) - outside `pyproject.toml`'s
`pythonpath`/collection scope (`tools/README.md`'s boundary, `tools/reviewer/test_research_edit.py`
same convention), so this never runs as part of `pytest tests/`.

Two layers:

- Pure-function tests against `try_resolve_append_only_conflicts`/`_resolve_block`, using conflict
  text captured from **real** `git -c merge.conflictstyle=diff3 rebase` runs (not hand-guessed
  marker shapes) - one for the exact "two independent entries appended near the same point" shape
  this session hit repeatedly by hand, one for a genuinely ambiguous edit-and-append conflict.
- Integration tests that build real local git repositories (bare "remote" plus two clones,
  never a live network call) and drive `push_with_retry` end to end, proving the auto-resolved
  case actually lands on the remote with both sides present, the ambiguous case aborts and lands
  nothing, and a conflict in a file outside the allow-list aborts and names that file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from push_retry import (  # noqa: E402
    AmbiguousConflictError,
    auto_resolve_conflicts,
    push_with_retry,
    run_git,
    try_resolve_append_only_conflicts,
)

# ---------------------------------------------------------------------------------------------
# Pure-function tests, using conflict text captured verbatim from real `git rebase` runs.
# ---------------------------------------------------------------------------------------------


def test_resolve_append_only_conflict_keeps_both_sides_and_strips_markers() -> None:
    # Captured verbatim from a real `git -c merge.conflictstyle=diff3 rebase` run: two clones of
    # one repo each independently appended a new DECISION_LOG.md entry after the same last line
    # ("entry two text here."), then one rebased onto the other's already-pushed commit - exactly
    # the shape this session hit resolving push races by hand.
    text = (
        "# Decision Log\n\n- entry one text here.\n\n- entry two text here.\n"
        "<<<<<<< HEAD\n"
        "\n- entry three (from A).\n"
        "||||||| parent of f17cb88 (B appends entry four)\n"
        "=======\n"
        "\n- entry four (from B).\n"
        ">>>>>>> f17cb88 (B appends entry four)\n"
    )
    resolved = try_resolve_append_only_conflicts(text)
    assert "<<<<<<<" not in resolved
    assert "=======" not in resolved
    assert ">>>>>>>" not in resolved
    assert "|||||||" not in resolved
    # Both sides survive - neither is dropped in favour of the other.
    assert "- entry three (from A)." in resolved
    assert "- entry four (from B)." in resolved
    assert resolved == (
        "# Decision Log\n\n- entry one text here.\n\n- entry two text here.\n"
        "\n- entry three (from A).\n"
        "\n- entry four (from B).\n"
    )


def test_resolve_append_only_conflict_orders_two_dated_entries_chronologically() -> (
    None
):
    # Same append-only shape, but each side's new content carries docs/DECISION_LOG.md's own
    # `- **YYYY-MM-DD HH:MM UTC ...` entry format. "ours" (ordinarily HEAD/origin, landing first
    # in a real rebase) is deliberately given the *later* timestamp here to prove the ordering
    # logic actually reads and sorts by the timestamp, rather than merely preserving git's own
    # ours-then-theirs order.
    text = (
        "# Decision Log\n\n- prior entry.\n"
        "<<<<<<< HEAD\n"
        "\n- **2026-09-23 15:00 UTC - later entry, landed first in the rebase.**\n"
        "||||||| base\n"
        "=======\n"
        "\n- **2026-09-23 09:00 UTC - earlier entry, replayed second in the rebase.**\n"
        ">>>>>>> theirs\n"
    )
    resolved = try_resolve_append_only_conflicts(text)
    earlier_pos = resolved.index("09:00 UTC")
    later_pos = resolved.index("15:00 UTC")
    assert earlier_pos < later_pos, (
        "the 09:00 entry must be kept before the 15:00 entry"
    )


def test_resolve_append_only_conflict_falls_back_to_ours_first_without_timestamps() -> (
    None
):
    text = (
        "# Notes\n\nprior line.\n"
        "<<<<<<< HEAD\n"
        "new ours line.\n"
        "||||||| base\n"
        "=======\n"
        "new theirs line.\n"
        ">>>>>>> theirs\n"
    )
    resolved = try_resolve_append_only_conflicts(text)
    assert resolved.index("new ours line.") < resolved.index("new theirs line.")


def test_resolve_append_only_conflict_deduplicates_an_identical_append_on_both_sides() -> (
    None
):
    text = (
        "# Notes\n\nprior line.\n"
        "<<<<<<< HEAD\n"
        "same new line.\n"
        "||||||| base\n"
        "=======\n"
        "same new line.\n"
        ">>>>>>> theirs\n"
    )
    resolved = try_resolve_append_only_conflicts(text)
    assert resolved.count("same new line.") == 1


def test_resolve_raises_when_a_shared_base_line_was_edited_not_merely_appended_after() -> (
    None
):
    # Captured verbatim from a real rebase where one side edited the existing last line
    # ("entry two text here." -> "..., EDITED BY A.") while the other side, unaware of that edit,
    # appended a new entry after the *original* line - a genuine, non-append-only conflict.
    text = (
        "# Decision Log\n\n- entry one text here.\n\n"
        "<<<<<<< HEAD\n"
        "- entry two text here, EDITED BY A.\n"
        "||||||| parent of d9226ad (B appends entry three)\n"
        "- entry two text here.\n"
        "=======\n"
        "- entry two text here.\n"
        "\n- entry three (from B).\n"
        ">>>>>>> d9226ad (B appends entry three)\n"
    )
    with pytest.raises(AmbiguousConflictError, match="changed on at least one side"):
        try_resolve_append_only_conflicts(text)


def test_resolve_raises_when_markers_carry_no_diff3_base_section() -> None:
    # Plain (non-diff3) conflict markers - no `|||||||` section, so there is no common-ancestor
    # text to prove either side only appended. Must never be guessed past.
    text = "line one.\n<<<<<<< HEAD\nours.\n=======\ntheirs.\n>>>>>>> branch\n"
    with pytest.raises(AmbiguousConflictError, match="no diff3-style conflict markers"):
        try_resolve_append_only_conflicts(text)


# ---------------------------------------------------------------------------------------------
# Integration tests: real local git repositories, no live network call.
# ---------------------------------------------------------------------------------------------


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"git {args} failed:\n{result.stdout}\n{result.stderr}"
    )
    return result


def _init_repo_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A bare `remote`, plus two clones `clone_a`/`clone_b`, both configured with a local identity.
    `clone_a` holds the commit that will already be on `origin/main` when `clone_b` tries to push -
    i.e. `clone_b` is the one under test, the one racing a concurrent push."""
    remote = tmp_path / "remote"
    clone_a = tmp_path / "clone_a"
    clone_b = tmp_path / "clone_b"
    _run(["init", "-q", "--bare", str(remote)], tmp_path)
    _run(["clone", "-q", str(remote), str(clone_a)], tmp_path)
    _run(["clone", "-q", str(remote), str(clone_b)], tmp_path)
    for clone, name, email in (
        (clone_a, "Agent A", "a@example.com"),
        (clone_b, "Agent B", "b@example.com"),
    ):
        _run(["config", "user.email", email], clone)
        _run(["config", "user.name", name], clone)
    return remote, clone_a, clone_b


def _seed_base_commit(clone_a: Path, remote_relative_path: str, content: str) -> None:
    target = clone_a / remote_relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    _run(["add", "--", remote_relative_path], clone_a)
    _run(["commit", "-q", "-m", "base"], clone_a)
    _run(["push", "-q", "origin", "HEAD:main"], clone_a)


def _remote_file_content(remote: Path, path: str) -> str:
    result = _run(["show", f"main:{path}"], remote)
    return result.stdout


def test_push_with_retry_auto_resolves_a_clean_append_only_race_and_lands_both_sides(
    tmp_path: Path,
) -> None:
    remote, clone_a, clone_b = _init_repo_pair(tmp_path)
    rel = "docs/DECISION_LOG.md"
    _seed_base_commit(clone_a, rel, "# Decision Log\n\n- entry one.\n\n- entry two.\n")
    _run(["fetch", "-q", "origin", "main"], clone_b)
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_b)

    # Agent A appends and pushes first - this is what clone_b will race against.
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_a)
    with (clone_a / rel).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n- entry three (from A).\n")
    _run(["add", "--", rel], clone_a)
    _run(["commit", "-q", "-m", "A appends entry three"], clone_a)
    _run(["push", "-q", "origin", "HEAD:main"], clone_a)

    # Agent B independently appends, from the same original base, unaware A already landed.
    with (clone_b / rel).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n- entry four (from B).\n")
    _run(["add", "--", rel], clone_b)
    _run(["commit", "-q", "-m", "B appends entry four"], clone_b)

    exit_code = push_with_retry(clone_b, branch="main", remote="origin", max_retries=5)

    assert exit_code == 0
    landed = _remote_file_content(remote, rel)
    assert "- entry three (from A)." in landed
    assert "- entry four (from B)." in landed
    assert "<<<<<<<" not in landed
    # clone_b's working tree must have landed cleanly too, not left mid-rebase.
    status = _run(["status", "--porcelain"], clone_b).stdout
    assert status == ""


def test_push_with_retry_aborts_on_a_genuinely_ambiguous_edit_conflict_and_lands_nothing(
    tmp_path: Path,
) -> None:
    remote, clone_a, clone_b = _init_repo_pair(tmp_path)
    rel = "docs/DECISION_LOG.md"
    _seed_base_commit(clone_a, rel, "# Decision Log\n\n- entry one.\n\n- entry two.\n")
    _run(["fetch", "-q", "origin", "main"], clone_b)
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_b)

    # Agent A edits the existing last entry (not a pure append) and pushes.
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_a)
    (clone_a / rel).write_text(
        "# Decision Log\n\n- entry one.\n\n- entry two, EDITED.\n",
        encoding="utf-8",
        newline="\n",
    )
    _run(["add", "--", rel], clone_a)
    _run(["commit", "-q", "-m", "A edits entry two"], clone_a)
    _run(["push", "-q", "origin", "HEAD:main"], clone_a)

    # Agent B, unaware of the edit, appends a new entry after the original line.
    with (clone_b / rel).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n- entry three (from B).\n")
    _run(["add", "--", rel], clone_b)
    _run(["commit", "-q", "-m", "B appends entry three"], clone_b)

    exit_code = push_with_retry(clone_b, branch="main", remote="origin", max_retries=5)

    assert exit_code == 1
    # Nothing landed on the remote beyond A's own commit.
    landed = _remote_file_content(remote, rel)
    assert "entry three (from B)" not in landed
    # The rebase was cleanly aborted, not left half-applied with conflict markers on disk.
    status = _run(["status", "--porcelain"], clone_b).stdout
    assert "UU" not in status
    on_disk = (clone_b / rel).read_text(encoding="utf-8")
    assert "<<<<<<<" not in on_disk


def test_push_with_retry_aborts_on_a_conflict_outside_the_allow_listed_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    remote, clone_a, clone_b = _init_repo_pair(tmp_path)
    rel = "README.md"
    _seed_base_commit(clone_a, rel, "line one.\nline two.\n")
    _run(["fetch", "-q", "origin", "main"], clone_b)
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_b)

    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_a)
    (clone_a / rel).write_text(
        "line one CHANGED BY A.\nline two.\n", encoding="utf-8", newline="\n"
    )
    _run(["add", "--", rel], clone_a)
    _run(["commit", "-q", "-m", "A edits line one"], clone_a)
    _run(["push", "-q", "origin", "HEAD:main"], clone_a)

    (clone_b / rel).write_text(
        "line one CHANGED BY B.\nline two.\n", encoding="utf-8", newline="\n"
    )
    _run(["add", "--", rel], clone_b)
    _run(["commit", "-q", "-m", "B edits line one"], clone_b)

    exit_code = push_with_retry(clone_b, branch="main", remote="origin", max_retries=5)

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "README.md" in out
    assert "needs human/agent judgment" in out or "ABORTED" in out
    landed = _remote_file_content(remote, rel)
    assert "CHANGED BY B" not in landed


def test_auto_resolve_conflicts_never_modifies_a_file_on_the_ambiguous_path(
    tmp_path: Path,
) -> None:
    # Directly exercises auto_resolve_conflicts' own contract ("no file is modified" on failure),
    # not only the higher-level push_with_retry behaviour above.
    remote, clone_a, clone_b = _init_repo_pair(tmp_path)
    rel = "docs/RESEARCH_AND_GUIDELINES.md"
    _seed_base_commit(clone_a, rel, "## 1. Section\n\nshared line.\n")
    _run(["fetch", "-q", "origin", "main"], clone_b)
    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_b)

    _run(["checkout", "-q", "-B", "main", "origin/main"], clone_a)
    (clone_a / rel).write_text(
        "## 1. Section\n\nshared line EDITED.\n", encoding="utf-8", newline="\n"
    )
    _run(["add", "--", rel], clone_a)
    _run(["commit", "-q", "-m", "A edits shared line"], clone_a)
    _run(["push", "-q", "origin", "HEAD:main"], clone_a)

    with (clone_b / rel).open("a", encoding="utf-8", newline="\n") as f:
        f.write("\nnew appended line from B.\n")
    _run(["add", "--", rel], clone_b)
    _run(["commit", "-q", "-m", "B appends"], clone_b)

    _run(["fetch", "-q", "origin", "main"], clone_b)
    rebase = run_git(
        ["-c", "merge.conflictstyle=diff3", "rebase", "origin/main"], clone_b
    )
    assert rebase.returncode != 0

    before = (clone_b / rel).read_bytes()
    ok, message = auto_resolve_conflicts(clone_b)
    after = (clone_b / rel).read_bytes()

    assert ok is False
    assert "RESEARCH_AND_GUIDELINES.md" in message
    assert before == after  # untouched on failure

    _run(["rebase", "--abort"], clone_b)


# ---------------------------------------------------------------------------------------------
# Retry-exhaustion reporting (monkeypatched git, deterministic non-fast-forward simulation).
# ---------------------------------------------------------------------------------------------


def test_push_with_retry_reports_failure_clearly_once_retries_are_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import push_retry

    calls: list[list[str]] = []

    def fake_run_git(
        args: list[str], cwd: Path, *, env: dict[str, str] | None = None
    ) -> push_retry.GitResult:
        calls.append(args)
        if args[0] == "fetch":
            return push_retry.GitResult(0, "", "")
        if "rebase" in args:
            return push_retry.GitResult(0, "", "")  # always a clean, no-op rebase
        if args[0] == "push":
            return push_retry.GitResult(
                1, "", "! [rejected] main -> main (non-fast-forward)"
            )
        raise AssertionError(f"unexpected git call in this test: {args}")

    monkeypatch.setattr(push_retry, "run_git", fake_run_git)
    monkeypatch.setattr(push_retry, "conflicted_files", lambda cwd: [])

    exit_code = push_retry.push_with_retry(
        tmp_path, branch="main", remote="origin", max_retries=3
    )

    assert exit_code == 1
    push_attempts = [c for c in calls if c and c[0] == "push"]
    assert len(push_attempts) == 3  # bounded - never loops forever
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "exhausted 3 attempt" in out


def test_push_with_retry_rejects_a_max_retries_below_one() -> None:
    with pytest.raises(ValueError):
        push_with_retry(Path("."), max_retries=0)
