"""Run a command chain on a clean clone and write its receipt.

This is the second half of the ``add_dev_commands`` re-enable condition (``chain.py`` is the first):
the commands the Development and Testing addition would print are run, in order, in a fresh clone
of the pinned revision - a new directory, no build output, no git-ignored file the maintainers'
machine happens to hold - and every step must exit 0.

The chain is tried first with the machine's own toolchains (``core/toolchains.py``: the registry
first for the tools it records, each called by absolute path with its directory added to the one
child's ``PATH``, never to this process's). When that does not exit 0 - a missing runtime, a test
that only fails on Windows, a Node release newer than the one the CI pins - and a standard Linux
image exists for its tools, the same steps are run once more in a container started from the clean
clone, because the CI the commands come from runs on Linux. Either run that exits 0 is the receipt.

Boundaries, the same ones the example verifiers keep (``core/execution.py``):

* the environment is the secret-free allow-list plus a disposable profile (every package cache and
  home directory redirected into the run's workspace), so a run cannot read what an earlier one
  left, and a cache that was warm for the maintainers is cold here;
* a Python chain gets a new virtual environment, so ``pip install`` lands there and nowhere else;
* a container is started with the clean clone mounted read-only, copies it, and is removed;
* nothing leaves the run's workspace, and the workspace is removed afterwards.

A step that needs a tool nothing here has (``make``, ``uv``) makes the receipt ``NOT_VERIFIED``:
the chain is neither confirmed nor refuted, and the addition stays report-only. Output that reaches
a receipt is scrubbed of this machine's paths first (a receipt travels in a published fact).
"""

from __future__ import annotations

import contextlib
import os
import platform
import re
import shlex
import shutil
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from repository_presenter.components.readme_correction.chain import ChainPlan
from repository_presenter.components.readme_correction.receipts import (
    EXECUTED,
    FAILED,
    NOT_VERIFIED,
    TIMED_OUT,
    Receipt,
    StepResult,
)
from repository_presenter.core.execution import profile_environment, secret_free_environment
from repository_presenter.core.git_safety.clone import force_rmtree
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.process import TIMEOUT_EXIT_CODE, run_bounded
from repository_presenter.core.secrets import configured_secrets, redact
from repository_presenter.core.toolchains import (
    installed_pythons,
    probe_version,
    recorded_path,
    resolve_tool,
)

STEP_TIMEOUT_SECONDS = 1500.0
CLONE_TIMEOUT_SECONDS = 600.0
_TAIL_LINES = 12
_TAIL_WIDTH = 200
_PYTHON_PROGRAMS = frozenset({"python", "python3", "py", "pip", "pip3"})
#: Tools that live in the virtual environment once something installs them: found there after
#: the chain's own ``pip install`` has run, and a failure to find one is the chain's.
_VENV_TOOLS = frozenset({"pytest", "py.test", "tox", "nox", "coverage", "ruff", "mypy", "twine"})
#: The Linux image whose toolchain runs a chain whose every program is in the set. The versions are
#: the ones the CI the commands come from pins (setup-node 20) or a current release.
_CONTAINER_IMAGES: tuple[tuple[frozenset[str], str], ...] = (
    (_PYTHON_PROGRAMS | _VENV_TOOLS, "python:3.13"),
    (frozenset({"mvn"}), "maven:3.9-eclipse-temurin-21"),
    (frozenset({"go"}), "golang:1"),
    (frozenset({"cargo"}), "rust:1"),
    (frozenset({"npm", "node", "npx"}), "node:20"),
    (frozenset({"cmake", "ctest", "ninja"}), "ubuntu:24.04"),
)
#: What a bare image needs before the chain's own steps, as the CI's runner image has it
#: preinstalled or the job installs it: a compiler, CMake, git (FetchContent) and certificates.
_PROVISION = {
    "ubuntu:24.04": (
        "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
        "build-essential cmake git ninja-build ca-certificates"
    ),
}
_PYTHON_IMAGE_VERSIONS = ("3.13", "3.12", "3.11", "3.10", "3.9")
_HOME_PATH = re.compile(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+")
_MARK = re.compile(r"^@@(START|EXIT) (\d+)(?: (-?\d+))?$")
_DOCKER_PROBE_SECONDS = 30.0

Runner = Callable[..., "CompletedProcess[str]"]


@dataclass
class _Machine:
    """What one chain run needs resolved, built as the steps ask for it."""

    workspace: Path
    run: Runner
    directories: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    tools: dict[str, str] = field(default_factory=dict)
    venv: Path | None = None

    def _add(self, name: str, executable: str | None) -> str | None:
        if executable is None:
            return f"{name} is not available on this machine"
        directory = str(Path(executable).parent)
        if directory not in self.directories:
            self.directories.append(directory)
        self.tools.setdefault(name, probe_version(name, executable) or "present")
        return None

    def _python(self) -> str | None:
        if self.venv is not None:
            return None
        pythons = installed_pythons()
        host = str(pythons[-1][1]) if pythons else sys.executable
        venv = self.workspace / "venv"
        made = self.run([host, "-m", "venv", str(venv)], cwd=self.workspace, timeout=300.0)
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        if made.returncode != 0 or not scripts.is_dir():
            return "a virtual environment could not be created"
        self.venv = venv
        self.directories.insert(0, str(scripts))
        listing = self.run(
            [str(_executable(scripts, "python")), "--version"], cwd=self.workspace, timeout=60.0
        )
        self.tools["python"] = (listing.stdout or listing.stderr).strip().splitlines()[0]
        self.environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        self.environment["PYTHONUTF8"] = "1"  # the encoding a Linux CI runner has by default
        return None

    def prepare(self, program: str) -> str | None:
        """Make ``program`` resolvable; the reason it cannot be, or ``None``."""
        name = program.lower().removesuffix(".exe").removesuffix(".cmd")
        if name in _PYTHON_PROGRAMS or name in _VENV_TOOLS:
            return self._python()
        if name in {"mvn", "mvnw"}:
            javac = resolve_tool("javac")
            problem = self._add("mvn", resolve_tool("mvn")) or self._add("javac", javac)
            if problem is None and javac is not None:
                self.environment["JAVA_HOME"] = str(Path(javac).parent.parent)
            return problem
        if name == "dotnet":
            # A test project built for an older runtime than the machine's SDK ships (net9.0
            # tests, a net10 SDK) runs on the newest installed runtime instead of aborting.
            self.environment.update(
                DOTNET_NOLOGO="1",
                DOTNET_CLI_TELEMETRY_OPTOUT="1",
                DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1",
                DOTNET_ROLL_FORWARD="LatestMajor",
                # no build server outlives the run holding files of the workspace open
                DOTNET_CLI_USE_MSBUILD_SERVER="0",
                MSBUILDDISABLENODEREUSE="1",
                UseSharedCompilation="false",
            )
            self.tools["dotnet roll-forward"] = "LatestMajor"
            return self._add("dotnet", resolve_tool("dotnet"))
        if name == "go":
            return self._add("go", resolve_tool("go"))
        if name in {"cargo", "rustc"}:
            return self._cargo()
        if name in {"cmake", "ctest", "ninja"}:
            self.environment["CMAKE_GENERATOR"] = "Ninja"
            return (
                self._add("cmake", resolve_tool("cmake"))
                or self._add("ninja", resolve_tool("ninja"))
                or self._add("gxx", resolve_tool("gxx"))
            )
        if name in {"node", "npm", "npx", "yarn", "pnpm"}:
            return self._add("node", resolve_tool("node"))
        return f"{program} is not available on this machine"

    def _cargo(self) -> str | None:
        cargo = resolve_tool("cargo")
        problem = self._add("cargo", cargo)
        if problem is None and cargo is not None:
            sibling = Path(cargo).parent.parent.parent / "rustup-home"
            home = (
                os.environ.get("RUSTUP_HOME")
                or recorded_path("rustup_home")
                or (str(sibling) if sibling.is_dir() else "")
            )
            if home:
                self.environment["RUSTUP_HOME"] = home
        return problem

    def executable(self, program: str) -> str | None:
        path = os.pathsep.join([*self.directories, os.environ.get("PATH", "")])
        if program in {"python", "python3", "py"} and self.venv is not None:
            scripts = self.venv / ("Scripts" if os.name == "nt" else "bin")
            return str(_executable(scripts, "python"))
        return shutil.which(program, path=path)

    def child_environment(self) -> dict[str, str]:
        env = secret_free_environment(dict(os.environ))
        env.update(profile_environment(self.workspace))
        env.update(self.environment)
        env["PATH"] = os.pathsep.join([*self.directories, os.environ.get("PATH", "")])
        return env


def _executable(directory: Path, name: str) -> Path:
    exe = directory / f"{name}.exe"
    return exe if exe.exists() or os.name == "nt" else directory / name


def _scrub(text: str, workspace: Path) -> str:
    cleaned = text.replace(str(workspace), "<workspace>").replace(
        str(workspace).replace("\\", "/"), "<workspace>"
    )
    cleaned = _HOME_PATH.sub("<home>", cleaned)
    secrets = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    return redact(cleaned, secrets)


def _tail(text: str, workspace: Path) -> str:
    lines = [line.rstrip() for line in _scrub(text, workspace).splitlines() if line.strip()]
    return "\n".join(line[:_TAIL_WIDTH] for line in lines[-_TAIL_LINES:])


def _clean_clone(clone_path: Path, revision: str, source: Path) -> bool:
    """A fresh clone of ``clone_path`` at ``revision`` in ``source``: nothing a build left."""
    cloned = run_git(
        ["clone", "--quiet", "--no-hardlinks", str(clone_path), str(source)],
        timeout=CLONE_TIMEOUT_SECONDS,
        env={"GIT_LFS_SKIP_SMUDGE": "1"},  # as the pinned clone: large files stay pointers
    )
    if cloned.returncode == 0:
        cloned = run_git(["checkout", "--quiet", "--detach", revision], cwd=source)
    if cloned.returncode != 0:
        return False
    return run_git(["rev-parse", "HEAD"], cwd=source).stdout.strip() == revision


def _skipped(plan: ChainPlan, start: int) -> list[StepResult]:
    return [StepResult(step.command, NOT_VERIFIED) for step in plan.steps[start:]]


def _failure(step: str, outcome: str, code: int | None, output: str, step_timeout: float) -> str:
    what = (
        f"did not finish within {int(step_timeout)} seconds"
        if outcome == TIMED_OUT
        else f"exited {code}"
    )
    last = output.splitlines()[-1] if output else ""
    return f"`{step}` {what}: {last}"[:400]


def _run_on_host(
    plan: ChainPlan,
    make: Callable[..., Receipt],
    source: Path,
    workspace: Path,
    step_timeout: float,
    run: Runner,
) -> Receipt:
    host = _Machine(workspace, run)
    results: list[StepResult] = []
    for index, step in enumerate(plan.steps):
        try:
            argv = shlex.split(step.command)
        except ValueError:
            return make(NOT_VERIFIED, f"`{step.command}` cannot be split into a command")
        problem = host.prepare(argv[0])
        if problem is not None:  # this machine lacks the toolchain: neither confirmed nor refuted
            detail = f"`{step.command}` was not run: {problem}"
            return make(NOT_VERIFIED, detail, (*results, *_skipped(plan, index)), host.tools)
        executable = host.executable(argv[0])
        if executable is None:  # a clean environment has no such command and nothing installs it
            detail = (
                f"`{step.command}` was not run: `{argv[0]}` is not found in a clean environment "
                "and no earlier step installs it"
            )
            return make(FAILED, detail, (*results, *_skipped(plan, index)), host.tools)
        started = time.monotonic()
        try:
            done = run(
                [str(executable), *argv[1:]],
                cwd=source,
                timeout=step_timeout,
                env=host.child_environment(),
            )
        except OSError as exc:  # the machine would not start it (an application-control policy)
            detail = f"`{step.command}` could not be started on this machine: {exc.strerror or exc}"
            return make(NOT_VERIFIED, detail, (*results, *_skipped(plan, index)), host.tools)
        seconds = round(time.monotonic() - started, 1)
        output = _tail(f"{done.stdout}\n{done.stderr}", workspace)
        outcome = (
            TIMED_OUT
            if done.returncode == TIMEOUT_EXIT_CODE
            else EXECUTED
            if done.returncode == 0
            else FAILED
        )
        results.append(StepResult(step.command, outcome, done.returncode, seconds, output))
        if outcome != EXECUTED:
            detail = _failure(step.command, outcome, done.returncode, output, step_timeout)
            return make(outcome, detail, (*results, *_skipped(plan, index + 1)), host.tools)
    return make(EXECUTED, "every step exited 0", tuple(results), host.tools)


def _python_version(source: Path | None) -> str:
    """The newest CPython the project's ``requires-python`` admits among the images offered."""
    if source is not None:
        try:
            text = (source / "pyproject.toml").read_text(encoding="utf-8")
            project = tomllib.loads(text).get("project", {})
            specifier = SpecifierSet(str(project.get("requires-python", "")))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, InvalidSpecifier):
            return _PYTHON_IMAGE_VERSIONS[0]
        for version in _PYTHON_IMAGE_VERSIONS:
            if specifier.contains(f"{version}.99"):
                return version
    return _PYTHON_IMAGE_VERSIONS[0]


def container_image(plan: ChainPlan, source: Path | None = None) -> str | None:
    """The Linux image that carries every program of ``plan``, or ``None`` if no one image does.
    A Python chain gets the newest interpreter the project's ``requires-python`` admits."""
    programs: set[str] = set()
    for step in plan.steps:
        try:
            programs.add(Path(shlex.split(step.command)[0]).name.lower())
        except (ValueError, IndexError):
            return None
    for members, image in _CONTAINER_IMAGES:
        if programs <= members:
            return f"python:{_python_version(source)}" if image.startswith("python:") else image
    return None


def _container_script(plan: ChainPlan, image: str = "") -> str:
    lines = ["exec 2>&1", "set +e"]
    if image in _PROVISION:
        lines += [_PROVISION[image] + " || { echo 'provisioning failed'; exit 0; }"]
    lines += ["mkdir -p /work && cp -a /ws/src/. /work/ && cd /work || exit 97"]
    for index, step in enumerate(plan.steps):
        lines += [
            f"echo '@@START {index}'",
            step.command,
            "rc=$?",
            f'echo "@@EXIT {index} $rc"',
            'if [ "$rc" -ne 0 ]; then exit 0; fi',
        ]
    return "\n".join(lines) + "\n"


def _docker_ready(run: Runner) -> bool:
    docker = shutil.which("docker")
    if docker is None:
        return False
    probe = run([docker, "info", "--format", "{{.OSType}}"], timeout=_DOCKER_PROBE_SECONDS)
    return probe.returncode == 0 and probe.stdout.strip() == "linux"


def _run_in_container(
    plan: ChainPlan,
    make: Callable[..., Receipt],
    image: str,
    workspace: Path,
    step_timeout: float,
    run: Runner,
) -> Receipt:
    docker = shutil.which("docker") or "docker"
    name = f"rp-chain-{plan.digest()[:12]}"
    script = _container_script(plan, image)
    (workspace / "run.sh").write_text(script, encoding="utf-8", newline="\n")
    started = time.monotonic()
    done = run(
        [
            docker,
            "run",
            "--rm",
            "--name",
            name,
            "-e",
            "CI=true",
            "-v",
            f"{workspace}:/ws:ro",
            image,
            "bash",
            "/ws/run.sh",
        ],
        timeout=step_timeout * max(1, len(plan.steps)),
    )
    seconds = round(time.monotonic() - started, 1)
    identity = run([docker, "image", "inspect", "--format", "{{.Id}}", image], timeout=60.0)
    tools = {"container image": f"{image} ({identity.stdout.strip()[7:19]})"}
    if image in _PROVISION:
        tools["container provisioning"] = "apt: build-essential cmake git ninja-build"
    if done.returncode == TIMEOUT_EXIT_CODE:
        run([docker, "rm", "-f", name], timeout=60.0)  # the container this run started
        detail = f"the container did not finish within {int(seconds)} seconds"
        return make(TIMED_OUT, detail, (), tools)
    blocks: dict[int, list[str]] = {}
    exits: dict[int, int] = {}
    current = -1
    for line in done.stdout.splitlines():
        mark = _MARK.match(line.strip())
        if mark is None:
            blocks.setdefault(current, []).append(line)
        elif mark.group(1) == "START":
            current = int(mark.group(2))
        else:
            exits[int(mark.group(2))] = int(mark.group(3))
    results: list[StepResult] = []
    for index, step in enumerate(plan.steps):
        if index not in exits:
            break
        output = _tail("\n".join(blocks.get(index, [])), workspace)
        outcome = EXECUTED if exits[index] == 0 else FAILED
        results.append(StepResult(step.command, outcome, exits[index], 0.0, output))
        if outcome != EXECUTED:
            detail = _failure(step.command, FAILED, exits[index], output, step_timeout)
            return make(FAILED, detail, (*results, *_skipped(plan, index + 1)), tools)
    if len(results) == len(plan.steps):
        return make(EXECUTED, "every step exited 0", tuple(results), tools)
    cause = _tail("\n".join(blocks.get(-1, []) + blocks.get(len(results), [])), workspace)
    return make(NOT_VERIFIED, f"the container did not run the chain: {cause}"[:400], (), tools)


def run_chain(
    plan: ChainPlan,
    *,
    repository: str,
    revision: str,
    clone_path: Path,
    scratch: Path,
    step_timeout: float = STEP_TIMEOUT_SECONDS,
    run: Runner = run_bounded,
    containers: bool = True,
) -> Receipt:
    """Run ``plan``'s steps in a fresh clone of ``clone_path`` at ``revision``; the receipt."""
    host_name = f"{platform.system()} {platform.release()} {platform.machine()}"

    def receipt_for(where: str) -> Callable[..., Receipt]:
        def make(
            outcome: str,
            detail: str,
            steps: tuple[StepResult, ...] = (),
            tools: dict[str, str] | None = None,
        ) -> Receipt:
            return Receipt(
                repository, revision, plan.digest(), outcome, detail, steps, tools or {}, where
            )

        return make

    workspace = scratch / f"{plan.digest()[:10]}-{revision[:8]}"
    if workspace.exists():
        force_rmtree(workspace)
    workspace.mkdir(parents=True)
    try:
        source = workspace / "src"
        if not _clean_clone(clone_path, revision, source):
            return receipt_for(host_name)(
                NOT_VERIFIED, "a clean clone of the revision could not be made"
            )
        try:
            first = _run_on_host(plan, receipt_for(host_name), source, workspace, step_timeout, run)
        except OSError as exc:  # the machine would not start a tool (an application-control policy)
            detail = f"the chain could not be started on this machine: {exc.strerror or exc}"
            first = receipt_for(host_name)(NOT_VERIFIED, detail)
        image = container_image(plan, source)
        if first.outcome == EXECUTED or not containers or image is None or not _docker_ready(run):
            return first
        force_rmtree(source)  # the host run built in it: the container starts from a clean clone
        if not _clean_clone(clone_path, revision, source):
            return first
        second = _run_in_container(
            plan, receipt_for("Linux (docker container)"), image, workspace, step_timeout, run
        )
        if second.outcome == EXECUTED:
            return second
        return Receipt(
            first.repository,
            first.revision,
            first.plan_digest,
            first.outcome,
            f"{first.detail} | in a Linux container ({image}): {second.detail}"[:600],
            first.steps,
            first.toolchain,
            first.platform,
        )
    finally:
        with contextlib.suppress(OSError):
            force_rmtree(workspace)
