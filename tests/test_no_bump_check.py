"""tools/workflow_rehearsal/no_bump_check.py: a branch's diff moves no governed version.

Every verdict is proved on a disposable local git repository (no network, no product import); one
more test runs the tool over the real TC-REF-10 commit when it is present in the checkout (hosted CI
checks out at depth 1, where that test skips cleanly and the plan-lint tests carry the CI proof).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from support import REPO_ROOT

TOOL_DIR = REPO_ROOT / "tools" / "workflow_rehearsal"
sys.path.insert(0, str(TOOL_DIR))

import no_bump_check  # noqa: E402

DISCIPLINE = (
    "from dataclasses import dataclass\n\n\n"
    "@dataclass(frozen=True)\nclass GovernedSource:\n    component: str\n    path: str\n"
    "    constants: tuple[str, ...]\n\n\n"
    "GOVERNED = (\n"
    '    GovernedSource("renderer", "src/pkg/renderer.py", ("RENDERER_VERSION",)),\n'
    '    GovernedSource("validator", "src/pkg/registry.py", ("VALIDATOR_VERSION",)),\n'
    ")\n"
)
RENDERER = 'RENDERER_VERSION = "1"\n\n\ndef render() -> int:\n    """Render."""\n    return 1\n'
REGISTRY = 'VALIDATOR_VERSION = "1"\nCHECKS = (Check("BC-01", "1", "first"),)\n'
SHELL = 'SHELL_VERSION = "6"\n\n\ndef shell() -> int:\n    return 1\n'


def git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def write(root: Path, relative: str, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def commit(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "-c", "commit.gpgsign=false", "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "core.hooksPath", str(tmp_path / "no-hooks"))  # a disposable repo has none
    write(root, "tests/test_version_bump_discipline.py", DISCIPLINE)
    write(root, "src/pkg/renderer.py", RENDERER)
    write(root, "src/pkg/registry.py", REGISTRY)
    write(root, "src/pkg/shell.py", SHELL)
    write(root, "src/pkg/checks.py", 'CHECKS = (Check("BC-02", "1", "x"),)\n')
    write(root, "tools/note.txt", "base\n")
    commit(root, "base")
    git(root, "checkout", "-q", "-b", "branch")
    return root


def verdict(root: Path, *, no_src: bool = False) -> list[str]:
    return no_bump_check.check(root, "main", "HEAD", no_src=no_src)


def test_a_branch_that_only_touches_tools_docs_and_tests_passes(repo: Path) -> None:
    write(repo, "tools/workflow_rehearsal/new.py", "X = 1\n")
    write(repo, "docs/OPERATIONS_RUNBOOK.md", "text\n")
    write(repo, "tests/test_new.py", "def test_x() -> None: ...\n")
    commit(repo, "rehearsal work")
    assert verdict(repo) == []
    assert verdict(repo, no_src=True) == []


@pytest.mark.parametrize("path", ["src/pkg/renderer.py", "src/pkg/registry.py"])
def test_touching_a_governed_source_fails_even_for_a_docstring_edit(repo: Path, path: str) -> None:
    original = (repo / path).read_text(encoding="utf-8")
    write(
        repo, path, original + "\n# a comment: no meaning change, still a governed file touched\n"
    )
    commit(repo, "touch governed")
    assert any(v.startswith("governed source changed") and path in v for v in verdict(repo))


def test_moving_any_version_constant_in_src_fails_even_outside_the_governed_list(
    repo: Path,
) -> None:
    write(repo, "src/pkg/shell.py", SHELL.replace('"6"', '"7"'))
    commit(repo, "bump shell")
    found = verdict(repo)
    assert any("SHELL_VERSION" in v and "'6' -> '7'" in v for v in found)
    assert not any(v.startswith("governed source changed") for v in found)


def test_a_src_change_that_moves_no_version_passes_unless_no_src_is_asked(repo: Path) -> None:
    write(repo, "src/pkg/shell.py", SHELL.replace("return 1", "return 2"))
    commit(repo, "edit shell")
    assert verdict(repo) == []
    assert any("not allowed for a no_bump card" in v for v in verdict(repo, no_src=True))


def test_a_per_check_version_move_is_a_version_move(repo: Path) -> None:
    write(repo, "src/pkg/checks.py", 'CHECKS = (Check("BC-02", "2", "x"),)\n')
    commit(repo, "move check")
    assert any("Check:BC-02" in v and "'1' -> '2'" in v for v in verdict(repo))


def test_a_deleted_constant_and_a_new_file_are_told_apart(repo: Path) -> None:
    write(repo, "src/pkg/fresh.py", 'FRESH_VERSION = "1"\n')
    commit(repo, "new file carries its own constants")
    assert verdict(repo) == []
    git(repo, "rm", "-q", "src/pkg/shell.py")
    commit(repo, "delete shell")
    assert any("SHELL_VERSION" in v and "<absent>" in v for v in verdict(repo))


def test_only_what_the_branch_changed_counts_not_what_the_base_gained(repo: Path) -> None:
    git(repo, "checkout", "-q", "main")
    write(repo, "src/pkg/renderer.py", RENDERER.replace('"1"', '"2"'))
    commit(repo, "main moves on and bumps")
    git(repo, "checkout", "-q", "branch")
    write(repo, "tools/note.txt", "branch\n")
    commit(repo, "branch work")
    assert verdict(repo) == []


def test_it_refuses_to_decide_rather_than_pass(repo: Path) -> None:
    with pytest.raises(no_bump_check.Undecidable):
        no_bump_check.check(repo, "no-such-ref", "HEAD")
    (repo / "tests" / "test_version_bump_discipline.py").unlink()
    with pytest.raises(no_bump_check.Undecidable):
        verdict(repo)


def test_the_command_line_exit_codes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo, "tools/note.txt", "branch\n")
    commit(repo, "ok")
    assert no_bump_check.main(["main", "--root", str(repo)]) == 0
    assert "no_bump_check: OK" in capsys.readouterr().out
    write(repo, "src/pkg/renderer.py", RENDERER.replace("return 1", "return 2"))
    commit(repo, "bad")
    assert no_bump_check.main(["main", "--root", str(repo)]) == 1
    assert "VIOLATION: governed source changed" in capsys.readouterr().out
    assert no_bump_check.main(["nope", "--root", str(repo)]) == 2


def _present(revision: str) -> bool:
    done = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def test_the_ref_10_commit_touched_no_governed_file_and_moved_no_version() -> None:
    """The recorded TC-REF-10 harness commit, against its own parent (skips where it is absent)."""
    ref10 = "38456556"
    if not (_present(ref10) and _present(f"{ref10}~1")):
        pytest.skip("the TC-REF-10 commit is not in this checkout (depth-1 hosted checkout)")
    assert no_bump_check.check(REPO_ROOT, f"{ref10}~1", ref10, no_src=True) == []
