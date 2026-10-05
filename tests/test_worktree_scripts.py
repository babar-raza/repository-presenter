"""scripts/sync_main.sh, scripts/new_worktree.sh and scripts/check_staleness.sh, against real git.

Pushes and PR merges move origin/main on GitHub only; a local ``main`` and any shared venv pointing
at the main checkout then serve stale code to every worktree (2026-10-05). These tests build a bare
"origin" plus clones in ``tmp_path`` and drive the real scripts under bash, positive and negative:
the fast-forward happens only when it is safe, every refusal leaves the repository exactly as it
was, and a new worktree starts from the freshly fetched origin/main, not the stale local main.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from support import REPO_ROOT

SCRIPTS = REPO_ROOT / "scripts"
SYNC_MAIN = (SCRIPTS / "sync_main.sh").as_posix()
NEW_WORKTREE = (SCRIPTS / "new_worktree.sh").as_posix()
CHECK_STALENESS = (SCRIPTS / "check_staleness.sh").as_posix()


def _find_bash() -> str | None:
    # On Windows the first bash on PATH can be the WSL launcher in System32, which cannot run these
    # scripts; Git for Windows' own bash sits beside git.
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parent.parent / "bin" / "bash.exe"
            if candidate.is_file():
                return str(candidate)
    return shutil.which("bash")


BASH = _find_bash()
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(BASH is None or GIT is None, reason="bash and git are required")

# Variables that would redirect git to another repository or change the scripts' behaviour.
_SCRUB = re.compile(r"^(GIT_.*|GITHUB_ACTIONS|RP_STALE_.*|NEW_WORKTREE_.*|CI_TOOLS_VENV)$")


def _env(**extra: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not _SCRUB.match(key)}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.invalid",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.invalid",
        GIT_TERMINAL_PROMPT="0",
    )
    env.update(extra)
    return env


def git(cwd: Path, *args: str) -> str:
    assert GIT is not None
    result = subprocess.run(
        [GIT, *args], cwd=cwd, env=_env(), capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}{result.stdout}"
    return result.stdout.strip()


def run_script(script: str, cwd: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    assert BASH is not None
    return subprocess.run(
        [BASH, script, *args],
        cwd=cwd,
        env=_env(**env),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@dataclass
class Remote:
    """A bare origin, a seed clone that publishes to it, and the "main checkout" clone."""

    origin: Path
    seed: Path
    main: Path
    advanced: int = 0

    def publish(self, name: str = "f.txt", text: str = "x\n", message: str = "advance") -> str:
        """A commit on origin/main made elsewhere (a PR merge), not yet fetched by ``main``."""
        (self.seed / name).write_text(text, encoding="utf-8", newline="\n")
        git(self.seed, "add", name)
        git(self.seed, "commit", "-m", message)
        git(self.seed, "push", "origin", "main")
        return git(self.seed, "rev-parse", "HEAD")

    def origin_main(self) -> str:
        return git(self.origin, "rev-parse", "refs/heads/main")

    def local_main(self) -> str:
        return git(self.main, "rev-parse", "refs/heads/main")


@pytest.fixture
def remote(tmp_path: Path) -> Remote:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    main = tmp_path / "repository-presenter"
    git(tmp_path, "init", "--bare", "--initial-branch=main", str(origin))
    git(tmp_path, "init", "--initial-branch=main", str(seed))
    git(seed, "remote", "add", "origin", str(origin))
    (seed / "a.txt").write_text("one\n", encoding="utf-8", newline="\n")
    git(seed, "add", "a.txt")
    git(seed, "commit", "-m", "initial")
    git(seed, "push", "origin", "main")
    git(tmp_path, "clone", str(origin), str(main))
    return Remote(origin=origin, seed=seed, main=main)


def status_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = [line for line in result.stdout.splitlines() if line.startswith("sync_main:")]
    assert len(lines) == 1, f"expected one status line, got: {result.stdout!r} / {result.stderr!r}"
    return lines[0]


def tree_state(repo: Path) -> tuple[str, str, str]:
    """HEAD, the local branches and the working-tree status: what a refusal must not move."""
    return (
        git(repo, "rev-parse", "HEAD"),
        git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"),
        git(repo, "status", "--porcelain"),
    )


# ---------------------------------------------------------------------------------------------
# sync_main.sh
# ---------------------------------------------------------------------------------------------


def test_fast_forwards_a_clean_main_checkout_that_is_behind(remote: Remote) -> None:
    remote.publish("b.txt", "two\n")
    tip = remote.publish("c.txt", "three\n")
    assert remote.local_main() != tip

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 0, result.stdout + result.stderr
    assert status_line(result).startswith("sync_main: OK fast-forwarded main")
    assert "behind 2, ahead 0" in status_line(result)
    assert remote.local_main() == tip == git(remote.main, "rev-parse", "HEAD")
    assert (remote.main / "c.txt").read_text(encoding="utf-8") == "three\n"


def test_is_idempotent_and_reports_up_to_date(remote: Remote) -> None:
    remote.publish()
    first = run_script(SYNC_MAIN, remote.main)
    before = tree_state(remote.main)
    second = run_script(SYNC_MAIN, remote.main)
    third = run_script(SYNC_MAIN, remote.main)

    assert first.returncode == 0 and "OK fast-forwarded" in status_line(first)
    assert second.returncode == third.returncode == 0
    assert status_line(second).startswith("sync_main: UP_TO_DATE")
    assert tree_state(remote.main) == before


def test_up_to_date_does_nothing_even_when_the_checkout_is_dirty(remote: Remote) -> None:
    (remote.main / "a.txt").write_text("edited\n", encoding="utf-8", newline="\n")
    result = run_script(SYNC_MAIN, remote.main)
    assert result.returncode == 0
    assert status_line(result).startswith("sync_main: UP_TO_DATE")
    assert (remote.main / "a.txt").read_text(encoding="utf-8") == "edited\n"


@pytest.mark.parametrize("staged", [False, True])
def test_refuses_uncommitted_tracked_changes_and_keeps_them(remote: Remote, staged: bool) -> None:
    remote.publish("b.txt", "two\n")
    old_main = remote.local_main()
    (remote.main / "a.txt").write_text("my work in progress\n", encoding="utf-8", newline="\n")
    if staged:
        git(remote.main, "add", "a.txt")
    before = tree_state(remote.main)

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED DIRTY")
    assert remote.local_main() == old_main
    assert tree_state(remote.main) == before
    assert (remote.main / "a.txt").read_text(encoding="utf-8") == "my work in progress\n"
    assert not (remote.main / "b.txt").exists()


def test_refuses_a_diverged_main_and_keeps_the_local_commit(remote: Remote) -> None:
    remote.publish("b.txt", "upstream\n")
    (remote.main / "local.txt").write_text("local\n", encoding="utf-8", newline="\n")
    git(remote.main, "add", "local.txt")
    git(remote.main, "commit", "-m", "local-only commit on main")
    local_tip = remote.local_main()

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED DIVERGED")
    assert "behind 1, ahead 1" in status_line(result)
    assert remote.local_main() == local_tip
    assert (remote.main / "local.txt").is_file() and not (remote.main / "b.txt").exists()


def test_refuses_a_main_that_is_only_ahead(remote: Remote) -> None:
    (remote.main / "local.txt").write_text("local\n", encoding="utf-8", newline="\n")
    git(remote.main, "add", "local.txt")
    git(remote.main, "commit", "-m", "unpushed")
    result = run_script(SYNC_MAIN, remote.main)
    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED DIVERGED")


def _start_conflicting_rebase(remote: Remote) -> None:
    """Leave the main checkout in the middle of a conflicting rebase of a topic branch."""
    git(remote.main, "checkout", "-b", "topic")
    (remote.main / "a.txt").write_text("topic edit\n", encoding="utf-8", newline="\n")
    git(remote.main, "commit", "-am", "topic edit")
    git(remote.main, "checkout", "main")
    remote.publish("a.txt", "upstream edit\n")
    git(remote.main, "fetch", "origin")
    git(remote.main, "checkout", "topic")
    assert BASH is not None and GIT is not None
    rebase = subprocess.run(
        [GIT, "rebase", "origin/main"],
        cwd=remote.main,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert rebase.returncode != 0, "the fixture needs a conflicting rebase"
    assert (Path(git(remote.main, "rev-parse", "--absolute-git-dir")) / "rebase-merge").exists()


def test_refuses_while_a_rebase_is_in_progress(remote: Remote) -> None:
    _start_conflicting_rebase(remote)
    old_main = remote.local_main()
    before = tree_state(remote.main)

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED OP_IN_PROGRESS")
    assert remote.local_main() == old_main
    assert tree_state(remote.main) == before
    assert (Path(git(remote.main, "rev-parse", "--absolute-git-dir")) / "rebase-merge").exists()


def test_refuses_while_a_merge_is_in_progress(remote: Remote) -> None:
    git(remote.main, "checkout", "-b", "topic")
    (remote.main / "a.txt").write_text("topic edit\n", encoding="utf-8", newline="\n")
    git(remote.main, "commit", "-am", "topic edit")
    remote.publish("a.txt", "upstream edit\n")
    git(remote.main, "fetch", "origin")
    assert GIT is not None
    merge = subprocess.run(
        [GIT, "merge", "origin/main"], cwd=remote.main, env=_env(), capture_output=True, check=False
    )
    assert merge.returncode != 0, "the fixture needs a conflicting merge"
    old_main = remote.local_main()

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED OP_IN_PROGRESS")
    assert remote.local_main() == old_main


def test_untracked_file_clash_is_surfaced_and_left_intact(remote: Remote) -> None:
    remote.publish("collide.txt", "from origin\n")
    old_main = remote.local_main()
    (remote.main / "collide.txt").write_text(
        "untracked and precious\n", encoding="utf-8", newline="\n"
    )

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 1
    assert status_line(result).startswith("sync_main: REFUSED UNTRACKED_CLASH")
    assert "collide.txt" in status_line(result)
    assert remote.local_main() == old_main
    assert (remote.main / "collide.txt").read_text(encoding="utf-8") == "untracked and precious\n"


def test_other_untracked_files_do_not_block_the_fast_forward(remote: Remote) -> None:
    tip = remote.publish("b.txt", "two\n")
    (remote.main / "scratch.log").write_text("keep me\n", encoding="utf-8", newline="\n")
    result = run_script(SYNC_MAIN, remote.main)
    assert result.returncode == 0, result.stdout
    assert remote.local_main() == tip
    assert (remote.main / "scratch.log").read_text(encoding="utf-8") == "keep me\n"


def test_updates_main_when_it_is_checked_out_nowhere_and_leaves_the_checkout_alone(
    remote: Remote,
) -> None:
    git(remote.main, "checkout", "-b", "topic")
    (remote.main / "a.txt").write_text("wip on topic\n", encoding="utf-8", newline="\n")
    tip = remote.publish("b.txt", "two\n")

    result = run_script(SYNC_MAIN, remote.main)

    assert result.returncode == 0, result.stdout + result.stderr
    assert status_line(result).startswith("sync_main: OK fast-forwarded main")
    assert remote.local_main() == tip
    assert git(remote.main, "rev-parse", "--abbrev-ref", "HEAD") == "topic"
    assert (remote.main / "a.txt").read_text(encoding="utf-8") == "wip on topic\n"
    assert not (remote.main / "b.txt").exists()


def test_fast_forwards_the_main_checkout_when_run_from_a_linked_worktree(
    remote: Remote, tmp_path: Path
) -> None:
    tip = remote.publish("b.txt", "two\n")
    linked = tmp_path / "linked"
    git(remote.main, "worktree", "add", "-b", "topic", str(linked), "main")

    result = run_script(SYNC_MAIN, linked)

    assert result.returncode == 0, result.stdout + result.stderr
    assert remote.local_main() == tip
    assert (remote.main / "b.txt").is_file()
    assert git(linked, "rev-parse", "HEAD") != tip  # the worktree's own branch is not touched


def test_check_mode_reports_and_changes_nothing(remote: Remote) -> None:
    remote.publish("b.txt", "two\n")
    old_main = remote.local_main()
    before = tree_state(remote.main)

    result = run_script(SYNC_MAIN, remote.main, "--check")

    assert result.returncode == 0
    assert status_line(result).startswith("sync_main: CHECK")
    assert "would fast-forward" in status_line(result)
    assert remote.local_main() == old_main
    assert tree_state(remote.main) == before


def test_check_mode_names_the_refusal_it_would_make(remote: Remote) -> None:
    remote.publish("b.txt", "two\n")
    (remote.main / "a.txt").write_text("dirty\n", encoding="utf-8", newline="\n")
    result = run_script(SYNC_MAIN, remote.main, "--check")
    assert result.returncode == 0
    assert "would refuse DIRTY" in status_line(result)


def test_an_unreachable_origin_is_an_error_not_a_guess(remote: Remote, tmp_path: Path) -> None:
    git(remote.main, "remote", "set-url", "origin", str(tmp_path / "does-not-exist.git"))
    before = tree_state(remote.main)
    result = run_script(SYNC_MAIN, remote.main)
    assert result.returncode == 2
    assert status_line(result).startswith("sync_main: ERROR FETCH_FAILED")
    assert tree_state(remote.main) == before


def test_an_unknown_option_is_a_usage_error(remote: Remote) -> None:
    result = run_script(SYNC_MAIN, remote.main, "--force")
    assert result.returncode == 2
    assert "usage" in result.stderr


GIT_CMD = r"\bgit\s+(-C\s+\S+\s+)?"


def _executable_lines(script: Path) -> str:
    return "\n".join(
        line
        for line in script.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )


@pytest.mark.parametrize("name", ["sync_main.sh", "new_worktree.sh", "check_staleness.sh"])
def test_no_script_runs_a_destructive_command(name: str) -> None:
    """Negative control on the scripts' own text: none of them can run what AGENTS.md forbids."""
    code = _executable_lines(SCRIPTS / name)
    forbidden = [
        GIT_CMD + r"(reset|clean|stash|rebase|checkout|restore|switch|push|gc|prune|am)\b",
        GIT_CMD + r"branch\b[^\n]*\s-[dDmMf]\b",
        GIT_CMD + r"branch\b[^\n]*--delete",
        r"\bgit\b[^\n]*--force",
        GIT_CMD + r"worktree\s+(remove|prune)\b",
        r"(^|[;&|\s])rm\s",
        r"--no-verify",
    ]
    for pattern in forbidden:
        match = re.search(pattern, code)
        assert match is None, f"{name} contains a forbidden command: {match.group(0)!r}"


# ---------------------------------------------------------------------------------------------
# new_worktree.sh
# ---------------------------------------------------------------------------------------------

ALLOW_ANY_DRIVE = {"NEW_WORKTREE_FORBIDDEN_DRIVES": ""}


def test_new_worktree_starts_from_the_fetched_origin_main_not_the_stale_local_main(
    remote: Remote,
) -> None:
    stale = remote.local_main()
    tip = remote.publish("b.txt", "two\n")  # origin moved; the clone has not fetched
    assert git(remote.main, "rev-parse", "refs/remotes/origin/main") == stale

    result = run_script(NEW_WORKTREE, remote.main, "demo", "feat/demo", **ALLOW_ANY_DRIVE)

    assert result.returncode == 0, result.stdout + result.stderr
    worktree = remote.main / "runs" / "wt" / "demo"
    assert git(worktree, "rev-parse", "HEAD") == tip
    assert git(worktree, "rev-parse", "--abbrev-ref", "HEAD") == "feat/demo"
    assert (worktree / "b.txt").is_file()
    assert remote.local_main() == stale  # the stale local main is neither used nor moved
    assert re.search(r"\bPYTHONPATH=", result.stdout)
    assert "src" in next(line for line in result.stdout.splitlines() if "PYTHONPATH=" in line)


def test_new_worktree_links_the_shared_venv(remote: Remote) -> None:
    venv = remote.main / ".venv"
    venv.mkdir()
    (venv / "marker.txt").write_text("shared\n", encoding="utf-8", newline="\n")

    result = run_script(NEW_WORKTREE, remote.main, "withvenv", "feat/withvenv", **ALLOW_ANY_DRIVE)

    assert result.returncode == 0, result.stdout + result.stderr
    linked = remote.main / "runs" / "wt" / "withvenv" / ".venv"
    assert (linked / "marker.txt").read_text(encoding="utf-8") == "shared\n"
    assert "venv: " in result.stdout and "WARNING" not in result.stdout
    # The link is to the shared venv, not a copy.
    (venv / "later.txt").write_text("added after\n", encoding="utf-8", newline="\n")
    assert (linked / "later.txt").is_file()


def test_new_worktree_warns_but_succeeds_without_a_shared_venv(remote: Remote) -> None:
    result = run_script(NEW_WORKTREE, remote.main, "novenv", "feat/novenv", **ALLOW_ANY_DRIVE)
    assert result.returncode == 0
    assert "WARNING no shared venv" in result.stdout


def test_new_worktree_works_from_inside_a_linked_worktree(remote: Remote) -> None:
    first = run_script(NEW_WORKTREE, remote.main, "one", "feat/one", **ALLOW_ANY_DRIVE)
    assert first.returncode == 0
    inner = remote.main / "runs" / "wt" / "one"
    second = run_script(NEW_WORKTREE, inner, "two", "feat/two", **ALLOW_ANY_DRIVE)
    assert second.returncode == 0, second.stdout + second.stderr
    assert (remote.main / "runs" / "wt" / "two").is_dir()  # always under the MAIN checkout


def test_new_worktree_refuses_an_existing_local_branch(remote: Remote) -> None:
    git(remote.main, "branch", "feat/taken")
    taken = git(remote.main, "rev-parse", "feat/taken")

    result = run_script(NEW_WORKTREE, remote.main, "fresh", "feat/taken", **ALLOW_ANY_DRIVE)

    assert result.returncode == 1
    assert "REFUSED BRANCH_EXISTS" in result.stdout
    assert not (remote.main / "runs" / "wt" / "fresh").exists()
    assert git(remote.main, "rev-parse", "feat/taken") == taken


def test_new_worktree_refuses_a_branch_that_exists_only_on_origin(remote: Remote) -> None:
    git(remote.seed, "push", "origin", "main:refs/heads/feat/remote-only")
    result = run_script(NEW_WORKTREE, remote.main, "fresh", "feat/remote-only", **ALLOW_ANY_DRIVE)
    assert result.returncode == 1
    assert "REFUSED REMOTE_BRANCH_EXISTS" in result.stdout
    assert not (remote.main / "runs" / "wt" / "fresh").exists()


def test_new_worktree_refuses_a_taken_path_and_leaves_it_alone(remote: Remote) -> None:
    taken = remote.main / "runs" / "wt" / "busy"
    taken.mkdir(parents=True)
    (taken / "precious.txt").write_text("someone's work\n", encoding="utf-8", newline="\n")

    result = run_script(NEW_WORKTREE, remote.main, "busy", "feat/busy", **ALLOW_ANY_DRIVE)

    assert result.returncode == 1
    assert "REFUSED PATH_TAKEN" in result.stdout
    assert (taken / "precious.txt").read_text(encoding="utf-8") == "someone's work\n"
    assert git(remote.main, "branch", "--list", "feat/busy") == ""


@pytest.mark.parametrize("name", ["../escape", "a/b", ".hidden", "with space", "C:evil", ""])
def test_new_worktree_refuses_a_name_that_could_leave_runs_wt(remote: Remote, name: str) -> None:
    result = run_script(NEW_WORKTREE, remote.main, name, "feat/x", **ALLOW_ANY_DRIVE)
    assert result.returncode == 1
    assert "REFUSED BAD_NAME" in result.stdout
    assert not (remote.main / "runs").exists()


@pytest.mark.parametrize("branch", ["main", "origin/x", "bad..name", "has space"])
def test_new_worktree_refuses_a_bad_branch(remote: Remote, branch: str) -> None:
    result = run_script(NEW_WORKTREE, remote.main, "ok", branch, **ALLOW_ANY_DRIVE)
    assert result.returncode == 1
    assert "REFUSED BAD_BRANCH" in result.stdout
    assert not (remote.main / "runs").exists()


def test_new_worktree_refuses_a_checkout_on_a_forbidden_drive(remote: Remote) -> None:
    """The default forbids C:; the test forbids the drive tmp_path is on, with the same effect."""
    if os.name != "nt":
        pytest.skip("drive letters exist on Windows only")
    drive = remote.main.resolve().drive.rstrip(":")
    result = run_script(
        NEW_WORKTREE, remote.main, "demo", "feat/demo", NEW_WORKTREE_FORBIDDEN_DRIVES=drive
    )
    assert result.returncode == 1
    assert "REFUSED FORBIDDEN_DRIVE" in result.stdout
    assert not (remote.main / "runs").exists()
    assert git(remote.main, "branch", "--list", "feat/demo") == ""


def test_new_worktree_default_branch_name(remote: Remote) -> None:
    result = run_script(NEW_WORKTREE, remote.main, "plain", **ALLOW_ANY_DRIVE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        git(remote.main / "runs" / "wt" / "plain", "rev-parse", "--abbrev-ref", "HEAD")
        == "wt/plain"
    )


def test_new_worktree_unreachable_origin_creates_nothing(remote: Remote, tmp_path: Path) -> None:
    git(remote.main, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = run_script(NEW_WORKTREE, remote.main, "demo", "feat/demo", **ALLOW_ANY_DRIVE)
    assert result.returncode == 2
    assert "ERROR FETCH_FAILED" in result.stdout
    assert not (remote.main / "runs").exists()


# ---------------------------------------------------------------------------------------------
# check_staleness.sh and its ci_check.sh wiring
# ---------------------------------------------------------------------------------------------


def _advance(remote: Remote, count: int) -> None:
    for _ in range(count):
        remote.advanced += 1
        remote.publish(
            f"n{remote.advanced}.txt", f"{remote.advanced}\n", f"change {remote.advanced}"
        )


def test_staleness_warns_naming_the_remedies_when_far_behind(remote: Remote) -> None:
    _advance(remote, 3)
    result = run_script(CHECK_STALENESS, remote.main, RP_STALE_COMMITS="2")
    assert result.returncode == 0
    assert "WARNING this checkout is 3 commits behind origin/main" in result.stdout
    assert "sync_main.sh" in result.stdout and "new_worktree.sh" in result.stdout


def test_staleness_is_quiet_within_the_threshold(remote: Remote) -> None:
    _advance(remote, 2)
    result = run_script(CHECK_STALENESS, remote.main, RP_STALE_COMMITS="2")
    assert result.returncode == 0 and result.stdout == ""


def test_staleness_default_threshold_is_twenty(remote: Remote) -> None:
    _advance(remote, 20)
    quiet = run_script(CHECK_STALENESS, remote.main)
    assert quiet.returncode == 0 and quiet.stdout == ""
    _advance(remote, 1)
    loud = run_script(CHECK_STALENESS, remote.main)
    assert loud.returncode == 0 and "21 commits behind origin/main" in loud.stdout


def test_staleness_fetches_so_a_never_fetched_clone_cannot_look_current(remote: Remote) -> None:
    _advance(remote, 3)
    assert git(remote.main, "rev-list", "--count", "HEAD..origin/main") == "0"  # unfetched
    stale_view = run_script(CHECK_STALENESS, remote.main, RP_STALE_COMMITS="2", RP_STALE_FETCH="0")
    assert stale_view.stdout == ""  # without a fetch the old ref hides the drift
    fresh_view = run_script(CHECK_STALENESS, remote.main, RP_STALE_COMMITS="2")
    assert "3 commits behind" in fresh_view.stdout


def test_staleness_never_fails_when_origin_is_unreachable(remote: Remote, tmp_path: Path) -> None:
    git(remote.main, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = run_script(CHECK_STALENESS, remote.main)
    assert result.returncode == 0


def test_staleness_is_skipped_on_github_actions(remote: Remote) -> None:
    _advance(remote, 3)
    result = run_script(CHECK_STALENESS, remote.main, RP_STALE_COMMITS="1", GITHUB_ACTIONS="true")
    assert result.returncode == 0 and result.stdout == ""


def test_staleness_outside_a_repository_is_silent(tmp_path: Path) -> None:
    result = run_script(CHECK_STALENESS, tmp_path)
    assert result.returncode == 0 and result.stdout == ""


def test_ci_check_runs_the_staleness_check_as_a_warning_only() -> None:
    """Wired, and unable to change an outcome or the exit code."""
    text = (SCRIPTS / "ci_check.sh").read_text(encoding="utf-8")
    calls = [
        line
        for line in text.splitlines()
        if "check_staleness.sh" in line and not line.startswith("#")
    ]
    assert calls == ['bash "$SCRIPT_DIR/check_staleness.sh" || true']
    assert 'OUTCOMES["staleness' not in text
