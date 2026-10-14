"""The chain of commands a Development and Testing addition rests on.

``add_dev_commands`` was report-only because the independent review of the first correction
bundles found commands stitched from unrelated steps: a release job's Debug build beside a
package-test ``ctest``, a sanitizer job's ``cmake --build`` without the configure step that creates
its directory. Its re-enable condition (``additions.DEV_RE_ENABLE``) asks for commands that are
*one* CI job's steps, run in order on a clean clone. This module decides the first half: from the
build and test facts and the pinned workflows, the one chain of steps that may be shown together.

* A chain is one job of a workflow that is not a release workflow (``ci_job``), or the build and
  test commands of one project file - a Makefile, a ``package.json``, one toolchain manifest -
  (``project_files``). Commands that are not in the chosen job, come from a release workflow, or
  from different project files are left out and reported with the reason; they are never joined.
* The job's own dependency installs that come before the command (``pip install -e '.[test]'``,
  ``npm install``, ``dotnet restore``) and the configure step the extractor already found are part
  of the chain: a reader needs them as much as the CI does. They come first, in the job's order,
  then the build, then the test - the order the Development and Testing block prints them in.
* A test command narrowed to one file, module, case or filter is not the project's test command
  and is left out.

Nothing here runs anything. The second half - running the chain on a clean clone - is
``verify.py``; the facts then carry what both found (``receipts.apply_plan``).
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.assets import is_release_workflow
from repository_presenter.components.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    PRECONDITION_ATTRIBUTE,
    TEST_COMMAND_FACT_ID,
    CiJob,
    ci_jobs,
)
from repository_presenter.core.facts import Fact, FactsDocument

CI_JOB = "ci_job"
PROJECT_FILES = "project_files"
#: The attributes the correction path puts on a command fact (an extractor never does).
CHAIN_ATTRIBUTE = "command_chain"
CI_CONTIGUOUS_ATTRIBUTE = "ci_job_contiguous"
RECEIPT_ATTRIBUTE = "build_receipt"
RECEIPT_PLATFORM_ATTRIBUTE = "build_receipt_platform"
RECEIPT_FAILURE_ATTRIBUTE = "build_receipt_failed"
EXCLUDED_ATTRIBUTE = "chain_excluded"

COMMAND_FACT_IDS = (BUILD_COMMAND_FACT_ID, TEST_COMMAND_FACT_ID)
_ROLES = {BUILD_COMMAND_FACT_ID: "build", TEST_COMMAND_FACT_ID: "test"}

# A dependency install a job runs before its build or test: what a reader needs first.
_INSTALL = re.compile(
    r"^(?:python3? -m )?pip3? install\b|^npm (?:ci|install|i)\b|^yarn(?: install)?$"
    r"|^pnpm install\b|^dotnet restore\b|^go mod download\b|^cargo fetch\b"
)
# An install that only upgrades the installer is noise to a reader.
_SELF_UPGRADE = re.compile(
    r"^(?:python3? -m )?pip3? install(?: +--?[A-Za-z-]+)* +(?:--upgrade|-U)"
    r"(?: +(?:pip|setuptools|wheel))+$"
)
_QUOTED = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"")
_SHELL_META = re.compile(r"[<>|&;$`(){}\\%\n]")
_TOKEN = re.compile(r"[A-Za-z0-9_./:=@+,~^<>!*\[\]-]+")
_UNSAFE_WORD = re.compile(
    r"(?i)deploy|publish|token|secret|password|api-?key|sign|upload|push|twine|release"
)
_PIP_INSTALL = re.compile(r"^(?:python3? -m )?pip3? install +(?P<package>[A-Za-z0-9_.-]+)$")
_MAX_LINE = 160

# A test command narrowed to part of the suite: it runs one file, module, case or filter.
_NARROWED: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"^(?:python3? -m )?pytest\b.*(?:\s-k\b|\s-m\b|::|\s--deselect\b|\s--lf\b|\s\S+\.py\b)",
        r"^python3? -m unittest(?:\s+-\S+)*\s+(?!discover\b)[A-Za-z_][\w.]*",
        r"^go test\b.*(?:\s-run\b|\s-bench\b)",
        r"^dotnet test\b.*\s--filter\b",
        r"^(?:\./)?mvnw?\b.*-Dtest=",
        r"^cargo test\b.*(?:\s--test\b|\s--lib\b|\s--doc\b|\s--bin\b|\s-p\b|\s--package\b)",
        r"^npm (?:run )?test\b.*\s--\s",
        r"^ctest\b.*(?:\s-R\b|\s-E\b|\s-L\b)",
    )
)


@dataclass(frozen=True)
class Step:
    role: str  # "setup" | "build" | "test"
    command: str
    fact_id: str = ""


@dataclass(frozen=True)
class Exclusion:
    fact_id: str
    reason: str


@dataclass(frozen=True)
class ChainPlan:
    """The steps that may be shown, and run, together - or why none can be."""

    kind: str = ""  # CI_JOB, PROJECT_FILES, or "" when no chain exists
    source: str = ""  # "<workflow path> job <id>" or the project file
    steps: tuple[Step, ...] = ()
    excluded: tuple[Exclusion, ...] = ()
    note: str = ""  # why no chain exists (when ``kind`` is empty)

    @property
    def included(self) -> tuple[str, ...]:
        return tuple(step.fact_id for step in self.steps if step.fact_id)

    def digest(self) -> str:
        """Identifies the chain by what it runs (kind, source, steps), nothing else."""
        body = [self.kind, self.source, [[step.role, step.command] for step in self.steps]]
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()

    def setup_before(self, fact_id: str) -> tuple[str, ...]:
        """The setup lines that come before ``fact_id``'s command, in chain order."""
        lines: list[str] = []
        for step in self.steps:
            if step.fact_id == fact_id:
                break
            if step.role == "setup":
                lines.append(step.command)
        return tuple(lines)


def narrows_test(command: str) -> bool:
    """Whether a test command runs only part of the suite."""
    return any(pattern.search(command) for pattern in _NARROWED)


def _printable(part: str) -> bool:
    try:
        tokens = shlex.split(part)
    except ValueError:
        return False
    return bool(tokens) and all(_TOKEN.fullmatch(token) for token in tokens)


def setup_parts(line: str) -> list[str] | None:
    """The printable install commands of one job line (split at ``&&``, installer self-upgrades
    dropped), ``[]`` when the line installs nothing, ``None`` when it installs something that
    cannot be printed as one plain command (an expression, a pipe, a redirect, a secret word)."""
    found: list[str] = []
    for part in (piece.strip() for piece in line.split("&&")):
        if not _INSTALL.match(part) or _SELF_UPGRADE.match(part):
            continue
        outside = _QUOTED.sub("", part)
        if (
            len(part) > _MAX_LINE
            or _SHELL_META.search(outside)
            or _UNSAFE_WORD.search(part)
            or not _printable(part)
        ):
            return None
        found.append(part)
    return found


def installs(emitted: list[str], wanted: str) -> bool:
    """Whether an install already in the chain covers ``wanted`` (``pip install build`` is
    covered by ``python -m pip install --upgrade pip build``)."""
    if wanted in emitted:
        return True
    named = _PIP_INSTALL.match(wanted)
    if named is None:
        return False
    pattern = re.compile(rf"\bpip3? install\b[^\n]*(?<![\w-]){re.escape(named.group('package'))}\b")
    return any(pattern.search(line) for line in emitted)


_PYTEST = re.compile(r"^(?:python3? -m )?pytest\b")
_NODE_SCRIPT = re.compile(r"^npm (?:test|t|run [A-Za-z0-9:_-]+)\b")
_REQUIREMENT_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_EXTRA_PREFERENCE = ("test", "tests", "testing", "dev")


def _declares_pytest(requirements: object) -> bool:
    if not isinstance(requirements, list):
        return False
    for item in requirements:
        named = _REQUIREMENT_NAME.match(item) if isinstance(item, str) else None
        if named is not None and named.group(1).lower() == "pytest":
            return True
    return False


def implied_setup(command: str, clone_path: Path, tree_paths: Sequence[str]) -> list[str]:
    """The install a project-file command needs first, when the project's own files say how.

    A ``package.json`` script runs the tools the project's dependencies provide, so its chain
    starts with ``npm install``. ``pytest`` is installed by the extra (or dependency group) of
    ``pyproject.toml`` that lists it; when none does, nothing is implied and the chain, run on a
    clean clone, fails honestly. Anything else (``mvn``, ``go``, ``dotnet``, ``cargo``) resolves its
    own dependencies and implies nothing."""
    if _NODE_SCRIPT.match(command) and "package.json" in tree_paths:
        return ["npm install"]
    if _PYTEST.match(command) and "pyproject.toml" in tree_paths:
        try:
            document = tomllib.loads((clone_path / "pyproject.toml").read_text("utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return []
        project = document.get("project")
        extras = project.get("optional-dependencies") if isinstance(project, dict) else None
        found = sorted(name for name, items in (extras or {}).items() if _declares_pytest(items))
        found.sort(
            key=lambda name: _EXTRA_PREFERENCE.index(name) if name in _EXTRA_PREFERENCE else 9
        )
        if found:
            return [f'python -m pip install -e ".[{found[0]}]"']
        groups = document.get("dependency-groups")
        named = sorted(name for name, items in (groups or {}).items() if _declares_pytest(items))
        if named:
            return [f"python -m pip install -e . --group {named[0]}"]
    return []


def _facts_by_role(facts: FactsDocument) -> dict[str, Fact]:
    return {
        _ROLES[fact.id]: fact
        for fact in facts.facts
        if fact.id in COMMAND_FACT_IDS and fact.polarity == "SUPPORTED"
    }


def _is_ci(fact: Fact) -> bool:
    return (fact.attributes or {}).get("source") == "ci workflow"


def _precondition_lines(fact: Fact) -> list[str]:
    return list((fact.attributes or {}).get(PRECONDITION_ATTRIBUTE, "").splitlines())


def _job_label(job: CiJob) -> str:
    return f"{job.path} job {job.job}"


def _holds(job: CiJob, command: str) -> bool:
    return any(run.admitted and run.line == command for run in job.runs)


def _locate(jobs: list[CiJob], wanted: dict[str, str]) -> CiJob | None:
    """The first non-release job that holds every wanted command, else the one holding the test
    command, else the one holding the build command."""
    usable = [job for job in jobs if not job.release]
    for job in usable:
        if all(_holds(job, command) for command in wanted.values()):
            return job
    for role in ("test", "build"):
        if role in wanted:
            for job in usable:
                if _holds(job, wanted[role]):
                    return job
    return None


def _ci_setup(job: CiJob, included: dict[str, Fact]) -> tuple[list[str], str]:
    """The setup lines of ``job`` before its last included command, or ``([], reason)``."""
    positions: dict[str, int] = {}
    for index, run in enumerate(job.runs):
        for role, fact in included.items():
            if role not in positions and run.admitted and run.line == fact.value:
                positions[role] = index
    last = max(positions.values())
    required = [line for fact in included.values() for line in _precondition_lines(fact)]
    commands = {fact.value for fact in included.values()}
    setup: list[str] = []
    for run in job.runs[: last + 1]:
        if run.line in commands:
            continue
        if run.line in required:
            if run.conditional or not run.admitted:
                return [], f"its setup step `{run.line[:60]}` is conditional or not printable"
            if run.line not in setup:
                setup.append(run.line)
            continue
        parts = setup_parts(run.line)
        if parts is None:
            return [], f"an install step of the job (`{run.line[:60]}`) cannot be printed safely"
        if parts and run.conditional:
            return [], f"an install step of the job (`{parts[0][:60]}`) is conditional"
        setup += [part for part in parts if part not in setup]
    # a tool the extractor found is needed (``pip install build``) that no job line installs
    setup = [line for line in required if not installs(setup, line)] + setup
    return list(dict.fromkeys(setup)), ""


def plan_chain(facts: FactsDocument, clone_path: Path, tree_paths: Sequence[str]) -> ChainPlan:
    """The chain of the SUPPORTED build and test facts, with what it leaves out and why."""
    by_role = _facts_by_role(facts)
    if not by_role:
        return ChainPlan(note="no build or test command is recorded")
    excluded: list[Exclusion] = []
    eligible: dict[str, Fact] = {}
    for role, fact in by_role.items():
        evidence_path = fact.evidence[0].path if fact.evidence else ""
        if _is_ci(fact) and is_release_workflow(evidence_path):
            excluded.append(
                Exclusion(fact.id, f"it is a step of a release workflow ({evidence_path})")
            )
        elif role == "test" and narrows_test(fact.value):
            excluded.append(Exclusion(fact.id, "it runs only part of the test suite"))
        else:
            eligible[role] = fact
    if not eligible:
        return ChainPlan(excluded=tuple(excluded), note="no command is eligible")
    ci = {role: fact for role, fact in eligible.items() if _is_ci(fact)}
    if ci:
        job = _locate(ci_jobs(clone_path, tree_paths), {r: f.value for r, f in ci.items()})
        if job is None:
            note = "no CI job outside a release workflow runs the commands as plain steps"
            excluded += [Exclusion(fact.id, note) for fact in eligible.values()]
            return ChainPlan(excluded=tuple(excluded), note=note)
        included = {role: fact for role, fact in ci.items() if _holds(job, fact.value)}
        excluded += [
            Exclusion(fact.id, f"it is not a step of the CI job {_job_label(job)}")
            for role, fact in eligible.items()
            if role not in included
        ]
        setup, problem = _ci_setup(job, included)
        if problem:
            excluded += [Exclusion(fact.id, problem) for fact in included.values()]
            return ChainPlan(excluded=tuple(excluded), note=problem)
        steps = [Step("setup", line) for line in setup]
        steps += [Step(role, included[role].value, included[role].id) for role in _order(included)]
        return ChainPlan(CI_JOB, _job_label(job), tuple(steps), tuple(excluded))
    # no CI command: the build and the test of one project file
    origins = {
        role: ((fact.attributes or {}).get("source", ""), fact.evidence[0].path)
        for role, fact in eligible.items()
    }
    chosen = eligible
    if len(set(origins.values())) > 1:
        keep = "test" if "test" in eligible else "build"
        excluded += [
            Exclusion(fact.id, "it comes from a different project file than the other command")
            for role, fact in eligible.items()
            if role != keep
        ]
        chosen = {keep: eligible[keep]}
    wanted = [line for fact in chosen.values() for line in _precondition_lines(fact)]
    for role in _order(chosen):
        wanted += implied_setup(chosen[role].value, clone_path, tree_paths)
    steps = [Step("setup", line) for line in dict.fromkeys(wanted)]
    steps += [Step(role, chosen[role].value, chosen[role].id) for role in _order(chosen)]
    return ChainPlan(PROJECT_FILES, origins[next(iter(chosen))][1], tuple(steps), tuple(excluded))


def _order(by_role: dict[str, Fact]) -> list[str]:
    """Build before test, the order the block prints them in."""
    return [role for role in ("build", "test") if role in by_role]
