"""Running a chain on a clean clone: no network, no toolchain beyond the Python running the tests.

The host run is exercised with the interpreter that runs the tests standing in for every tool; the
container run with a scripted ``docker``. What is proved: the chain runs in a *fresh* clone of the
pinned revision (a build leftover in the pinned clone is not there), steps run in order and stop at
the first failure, a missing tool is ``NOT_VERIFIED`` while a command the chain never installed is
``FAILED``, a timeout is its own outcome, machine paths never reach the receipt, and a failing host
run is retried in a container that starts from a clean clone again.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

from repository_presenter.components.readme_correction import verify
from repository_presenter.components.readme_correction.chain import ChainPlan, Step
from repository_presenter.components.readme_correction.receipts import (
    EXECUTED,
    FAILED,
    NOT_VERIFIED,
    TIMED_OUT,
)
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE

PY = "python"


@pytest.fixture
def upstream(tmp_path: Path) -> tuple[Path, str]:
    """A pinned clone: one commit, and a build leftover the clean clone must not carry."""
    path = tmp_path / "pinned"
    path.mkdir()
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8", newline="\n")
    (path / ".gitignore").write_text("leftover.txt\n", encoding="utf-8", newline="\n")
    for args in (
        ["init", "-q", "-b", "main"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x"],
    ):
        assert run_git(args, cwd=path).returncode == 0
    (path / "leftover.txt").write_text("built on the maintainers' machine\n", encoding="utf-8")
    return path, run_git(["rev-parse", "HEAD"], cwd=path).stdout.strip()


@pytest.fixture(autouse=True)
def the_interpreter_stands_in_for_every_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify._Machine, "prepare", lambda self, program: None)
    monkeypatch.setattr(verify._Machine, "executable", lambda self, program: sys.executable)


def plan_of(*commands: str) -> ChainPlan:
    return ChainPlan(
        "project_files", "Makefile", tuple(Step("test", command) for command in commands)
    )


def run(upstream: tuple[Path, str], tmp_path: Path, plan: ChainPlan, **extra: Any) -> Any:
    clone, revision = upstream
    return verify.run_chain(
        plan,
        repository="o/r",
        revision=revision,
        clone_path=clone,
        scratch=tmp_path / "scratch",
        containers=False,
        **extra,
    )


def test_every_step_runs_in_order_in_a_fresh_clone_and_the_receipt_says_so(
    upstream: tuple[Path, str], tmp_path: Path
) -> None:
    plan = plan_of(
        f'{PY} -c "import os; print(sorted(os.listdir()))"',
        f"{PY} -c \"import os, sys; sys.exit(0 if not os.path.exists('leftover.txt') else 5)\"",
    )
    receipt = run(upstream, tmp_path, plan)
    assert receipt.outcome == EXECUTED and receipt.detail == "every step exited 0"
    assert [s.exit_code for s in receipt.steps] == [0, 0]  # no leftover.txt in the clean clone
    assert "tracked.txt" in receipt.steps[0].tail and "leftover.txt" not in receipt.steps[0].tail
    assert receipt.revision == upstream[1] and receipt.plan_digest == plan.digest()
    assert receipt.clean_clone is True and receipt.platform
    assert list((tmp_path / "scratch").iterdir()) == []  # the workspace is removed afterwards


def test_a_failing_step_stops_the_chain_and_the_rest_are_not_verified(
    upstream: tuple[Path, str], tmp_path: Path
) -> None:
    plan = plan_of(
        f'{PY} -c "print(1)"', f'{PY} -c "import sys; sys.exit(3)"', f'{PY} -c "print(2)"'
    )
    receipt = run(upstream, tmp_path, plan)
    assert receipt.outcome == FAILED and "exited 3" in receipt.detail
    assert [(s.outcome, s.exit_code) for s in receipt.steps] == [
        (EXECUTED, 0),
        (FAILED, 3),
        (NOT_VERIFIED, None),
    ]


def test_a_tool_the_machine_lacks_makes_the_receipt_neither_confirmed_nor_refuted(
    upstream: tuple[Path, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        verify._Machine,
        "prepare",
        lambda self, program: f"{program} is not available on this machine",
    )
    receipt = run(upstream, tmp_path, plan_of("make test"))
    assert receipt.outcome == NOT_VERIFIED and "make is not available" in receipt.detail


def test_a_command_nothing_in_the_chain_installs_is_a_failure_of_the_chain(
    upstream: tuple[Path, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verify._Machine, "executable", lambda self, program: None)
    receipt = run(upstream, tmp_path, plan_of("pytest"))
    assert receipt.outcome == FAILED and "is not found in a clean environment" in receipt.detail


def test_a_timeout_is_its_own_outcome(upstream: tuple[Path, str], tmp_path: Path) -> None:
    def never_finishes(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        return CompletedProcess(args, TIMEOUT_EXIT_CODE, "", "")

    receipt = run(
        upstream, tmp_path, plan_of(f'{PY} -c "pass"'), run=never_finishes, step_timeout=7
    )
    assert receipt.outcome == TIMED_OUT and "did not finish within 7 seconds" in receipt.detail


def test_machine_paths_and_secrets_never_reach_a_receipt(
    upstream: tuple[Path, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOME_API_TOKEN", "s3cr3t-value-0123456789")
    plan = plan_of(
        f"{PY} -c \"import os; print(os.getcwd()); print(r'C:\\Users\\someone\\x'); "
        f"print(os.environ.get('SOME_API_TOKEN', 'unset'))\""
    )
    receipt = run(upstream, tmp_path, plan)
    tail = receipt.steps[0].tail
    assert "<workspace>" in tail and "<home>" in tail
    assert "s3cr3t-value" not in tail and "someone" not in tail
    assert str(tmp_path) not in tail


def test_a_revision_the_clone_does_not_hold_cannot_be_verified(
    upstream: tuple[Path, str], tmp_path: Path
) -> None:
    clone, _revision = upstream
    receipt = verify.run_chain(
        plan_of(f'{PY} -c "pass"'),
        repository="o/r",
        revision="f" * 40,
        clone_path=clone,
        scratch=tmp_path / "scratch",
        containers=False,
    )
    assert receipt.outcome == NOT_VERIFIED and "clean clone" in receipt.detail


def test_which_image_carries_a_chain() -> None:
    assert (
        verify.container_image(plan_of("pytest -q", "python -m pip install -e .")) == "python:3.13"
    )
    assert verify.container_image(plan_of("mvn -B test")) == "maven:3.9-eclipse-temurin-21"
    assert verify.container_image(plan_of("npm install", "npm test")) == "node:20"
    assert verify.container_image(plan_of("go build ./...", "go test ./...")) == "golang:1"
    assert verify.container_image(plan_of("cargo test")) == "rust:1"
    assert verify.container_image(plan_of("make test")) is None
    assert verify.container_image(plan_of("npm test", "pytest")) is None  # no one image has both


def docker_script(outputs: dict[str, str]) -> Any:
    """A scripted ``docker``: ``info`` says linux, ``run`` prints what the test gives it."""

    def run(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        verb = args[1] if len(args) > 1 else ""
        if args[0] == "docker" or str(args[0]).endswith(("docker", "docker.exe")):
            if verb == "info":
                return CompletedProcess(args, 0, "linux\n", "")
            if verb == "run":
                return CompletedProcess(args, 0, outputs["run"], "")
            if verb == "image":
                return CompletedProcess(args, 0, "sha256:0123456789abcdef0123\n", "")
            return CompletedProcess(args, 0, "", "")
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            **{k: v for k, v in kwargs.items() if k in {"cwd", "env"}},
        )

    return run


def test_a_failing_host_run_is_retried_in_a_container_and_its_pass_is_the_receipt(
    upstream: tuple[Path, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verify.shutil, "which", lambda name, **kw: name)
    plan = ChainPlan("ci_job", "w job test", (Step("test", "npm test"),))
    clone, revision = upstream
    script = docker_script({"run": "@@START 0\nall good\n@@EXIT 0 0\n"})
    monkeypatch.setattr(
        verify._Machine, "executable", lambda self, program: None
    )  # the host run fails: npm is not found there
    receipt = verify.run_chain(
        plan,
        repository="o/r",
        revision=revision,
        clone_path=clone,
        scratch=tmp_path / "scratch",
        run=script,
    )
    assert receipt.outcome == EXECUTED
    assert receipt.platform == "Linux (docker container)"
    assert receipt.toolchain["container image"].startswith("node:20 (")
    assert receipt.steps[0].tail == "all good"


def test_a_container_that_fails_too_keeps_the_host_failure_and_names_both(
    upstream: tuple[Path, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(verify.shutil, "which", lambda name, **kw: name)
    plan = ChainPlan("ci_job", "w job test", (Step("test", "npm test"),))
    clone, revision = upstream
    script = docker_script({"run": "@@START 0\nboom\n@@EXIT 0 1\n"})
    monkeypatch.setattr(verify._Machine, "executable", lambda self, program: None)
    receipt = verify.run_chain(
        plan,
        repository="o/r",
        revision=revision,
        clone_path=clone,
        scratch=tmp_path / "scratch",
        run=script,
    )
    assert receipt.outcome == FAILED
    assert "not found in a clean environment" in receipt.detail
    assert "in a Linux container (node:20)" in receipt.detail and "exited 1" in receipt.detail


def test_the_container_script_runs_each_step_through_the_shell_and_stops_at_a_failure() -> None:
    script = verify._container_script(plan_of("npm install", "npm test"))
    assert script.startswith("exec 2>&1\nset +e\n")
    assert "echo '@@START 0'\nnpm install\nrc=$?" in script
    assert 'echo "@@EXIT 1 $rc"' in script and "exit 0" in script


@pytest.mark.parametrize(
    ("requires", "image"),
    [
        (">=3.10,<3.13", "python:3.12"),
        (">=3.11", "python:3.13"),
        ("==3.10.*", "python:3.10"),
        (">=3.14", "python:3.13"),  # nothing offered satisfies it: the default, and the run fails
        ("not a specifier", "python:3.13"),
    ],
)
def test_a_python_chain_runs_on_the_newest_interpreter_the_project_admits(
    tmp_path: Path, requires: str, image: str
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "p"\nrequires-python = "{requires}"\n', encoding="utf-8", newline="\n"
    )
    assert verify.container_image(plan_of("pytest -q"), tmp_path) == image
    assert verify.container_image(plan_of("npm test"), tmp_path) == "node:20"  # not Python


def test_a_machine_that_refuses_to_start_a_tool_is_not_a_failed_chain(
    upstream: tuple[Path, str], tmp_path: Path
) -> None:
    def blocked(args: list[str], **kwargs: Any) -> CompletedProcess[str]:
        raise OSError(4551, "An Application Control policy has blocked this file")

    receipt = run(upstream, tmp_path, plan_of(f'{PY} -c "pass"'), run=blocked)
    assert receipt.outcome == NOT_VERIFIED
    assert "could not be started on this machine" in receipt.detail
    assert "Application Control" in receipt.detail


def test_a_cmake_chain_gets_an_image_provisioned_like_a_ci_runner() -> None:
    plan = plan_of("cmake -S . -B build", "cmake --build build", "ctest --test-dir build")
    assert verify.container_image(plan) == "ubuntu:24.04"
    script = verify._container_script(plan, "ubuntu:24.04")
    assert "apt-get install -y -qq build-essential cmake git ninja-build ca-certificates" in script
    assert script.index("apt-get") < script.index("cp -a /ws/src/. /work/")
    assert "apt-get" not in verify._container_script(plan_of("npm test"), "node:20")
