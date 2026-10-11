"""Build commands, test commands, and the CI matrix, read from the clone's own build files.

TC-COV-02 (G3-W08), first slice. The clone-information coverage inventory (TC-COV-01) measured
that the repository states how to build it and how to test it, and across which operating systems
and runtimes its CI runs, in files the sealed READMEs did not carry: ``test_command`` missing from
16 of 25 repositories that have one, ``build_command`` from 15 of 22, ``ci_matrix`` from 11 of 12.
Development and Testing (README_CONTRACT.md section 2 row 17) is the section that renders them.

Each is a ``build_test_asset`` fact, the kind that row already rests on, so no fact kind, schema,
or registry row is added. A command is only ever read, never composed, from the first of these
that names one, in rank order:

1. a ``run`` step of a push-or-pull-request workflow that is not a publish or release workflow;
2. a ``package.json`` script (``npm test``, ``npm run build``);
3. a ``Makefile`` target (``make test``, ``make build``);
4. the standard command of the toolchain whose manifest sits at the repository root - a table of
   rules (``CONVENTIONS``), never a branch per ecosystem, and for ``test`` only when the tree also
   shows tests;
5. a ``run`` step of a publish or release workflow, which proves the command exists and is last
   because it often carries release-only flags.

A command line that carries an expression, a secret-bearing word, a pipe or a redirect is never
admitted: the renderer prints the command verbatim and a reader runs it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.evidence.facts.assets import (
    has_test_evidence,
    is_release_workflow,
    workflow_documents,
)
from repository_presenter.core.facts import Evidence, Fact, fact_id

BUILD_COMMAND_FACT_ID = fact_id("build_test_asset", "build-command")
TEST_COMMAND_FACT_ID = fact_id("build_test_asset", "test-command")
CI_MATRIX_FACT_ID = fact_id("build_test_asset", "ci-matrix")

_SAFE_LINE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_ ./:=@+,-]*")
_UNSAFE_WORD = re.compile(
    r"(?i)deploy|publish|token|secret|password|api-?key|sign|upload|push|twine|release"
)
_MAX_COMMAND_LENGTH = 120
_MAX_MANIFEST_BYTES = 1024 * 1024

# Ordered: a line that is a test command is never also read as a build command (``mvn verify``).
# ``(?:\./)?`` admits the wrapper scripts; ``.*`` between a tool and its goal admits flags.
_TEST_RULES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"^(?:python3? -m )?pytest\b",
        r"^python3? -m unittest\b",
        r"^tox\b",
        r"^dotnet test\b",
        r"^cargo test\b",
        r"^go test\b",
        r"^(?:\./)?mvnw? .*\b(?:test|verify)\b",
        r"^npm (?:test|run test)\b",
        r"^(?:\./)?gradlew? .*\btest\b",
        r"^ctest\b",
        r"^make test\b",
    )
)
_BUILD_RULES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"^python3? -m build\b",
        r"^dotnet (?:build|pack)\b",
        r"^cargo (?:build|check)\b",
        r"^go build\b",
        r"^(?:\./)?mvnw? .*\b(?:package|install|compile)\b",
        r"^npm run build\b",
        r"^cmake --build\b",
        r"^make(?: build| all)?$",
        r"^(?:\./)?gradlew? .*\bbuild\b",
    )
)

# Source ranks (lower is preferred); see the module docstring.
_RANK_CI, _RANK_SCRIPT, _RANK_MAKE, _RANK_CONVENTION, _RANK_RELEASE_CI = range(5)


@dataclass(frozen=True)
class _Candidate:
    rank: int
    command: str
    path: str
    detail: str
    source: str


@dataclass(frozen=True)
class ConventionRule:
    """The standard build and test command of the toolchain whose manifest sits at the root.

    ``build`` and ``test`` are templates over ``{manifest}``, the matched path (a ``.sln`` file
    is matched by suffix at depth two or less, so its command names it). An empty command means
    the toolchain has no single standard one. ``test_needs`` is a substring the manifest text must
    carry for the test command to hold (``pytest`` in ``pyproject.toml``).
    """

    manifest: str
    build: str
    test: str
    test_needs: str = ""


CONVENTIONS: tuple[ConventionRule, ...] = (
    ConventionRule("Cargo.toml", "cargo build", "cargo test"),
    ConventionRule("go.mod", "go build ./...", "go test ./..."),
    ConventionRule("pom.xml", "mvn package", "mvn test"),
    ConventionRule("pyproject.toml", "", "pytest", test_needs="pytest"),
    ConventionRule("*.sln", "dotnet build {manifest}", "dotnet test {manifest}"),
)


def _commands_in(run: str) -> list[str]:
    """The single-line commands of a workflow ``run`` step that are safe to print verbatim."""
    found: list[str] = []
    for raw in run.splitlines():
        line = raw.strip()
        if line.startswith("$ "):
            line = line[2:].strip()
        if (
            not line
            or line.endswith("\\")
            or len(line) > _MAX_COMMAND_LENGTH
            or not _SAFE_LINE.fullmatch(line)
            or _UNSAFE_WORD.search(line)
        ):
            continue
        found.append(line)
    return found


def _role_of(command: str) -> str | None:
    if any(rule.search(command) for rule in _TEST_RULES):
        return "test"
    if any(rule.search(command) for rule in _BUILD_RULES):
        return "build"
    return None


def _workflow_candidates(
    clone_path: Path, tree_paths: Sequence[str]
) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    for path, document in workflow_documents(clone_path, tree_paths):
        jobs = document.get("jobs")
        if not isinstance(jobs, dict):
            continue
        release = is_release_workflow(path)
        for job_id, job in jobs.items():
            steps = job.get("steps") if isinstance(job, dict) else None
            for step in steps if isinstance(steps, list) else []:
                run = step.get("run") if isinstance(step, dict) else None
                if not isinstance(run, str):
                    continue
                for command in _commands_in(run):
                    role = _role_of(command)
                    if role is None:
                        continue
                    found[role].append(
                        _Candidate(
                            _RANK_RELEASE_CI if release else _RANK_CI,
                            command,
                            path,
                            f"job {job_id} runs `{command}`",
                            "ci workflow",
                        )
                    )
    return found


def _script_candidates(clone_path: Path, tree_paths: Sequence[str]) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    if "package.json" not in tree_paths:
        return found
    try:
        file = clone_path / "package.json"
        if file.stat().st_size > _MAX_MANIFEST_BYTES:
            return found
        document = json.loads(file.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return found
    scripts = document.get("scripts") if isinstance(document, dict) else None
    if not isinstance(scripts, dict):
        return found
    for name, role, command in (("test", "test", "npm test"), ("build", "build", "npm run build")):
        body = scripts.get(name)
        if isinstance(body, str) and body.strip() and "no test specified" not in body:
            found[role].append(
                _Candidate(
                    _RANK_SCRIPT,
                    command,
                    "package.json",
                    f'script "{name}" is defined',
                    "package.json script",
                )
            )
    return found


_MAKE_TARGET = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:(?!=)", re.MULTILINE)


def _makefile_candidates(
    clone_path: Path, tree_paths: Sequence[str]
) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    if "Makefile" not in tree_paths:
        return found
    try:
        file = clone_path / "Makefile"
        if file.stat().st_size > _MAX_MANIFEST_BYTES:
            return found
        targets = set(_MAKE_TARGET.findall(file.read_text("utf-8")))
    except (OSError, UnicodeDecodeError):
        return found
    if "test" in targets:
        found["test"].append(
            _Candidate(_RANK_MAKE, "make test", "Makefile", "target test is defined", "Makefile")
        )
    for target, command in (("build", "make build"), ("all", "make all")):
        if target in targets:
            found["build"].append(
                _Candidate(
                    _RANK_MAKE, command, "Makefile", f"target {target} is defined", "Makefile"
                )
            )
            break
    return found


def _manifest_path(rule: ConventionRule, tree_paths: Sequence[str]) -> str | None:
    if rule.manifest.startswith("*."):
        suffix = rule.manifest[1:]
        matches = sorted(
            (path for path in tree_paths if path.endswith(suffix) and path.count("/") <= 1),
            key=lambda path: (path.count("/"), path),
        )
        return matches[0] if matches else None
    return rule.manifest if rule.manifest in tree_paths else None


def _convention_candidates(
    clone_path: Path, tree_paths: Sequence[str]
) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    tested = has_test_evidence(tree_paths)
    for rule in CONVENTIONS:
        manifest = _manifest_path(rule, tree_paths)
        if manifest is None:
            continue
        if rule.build:
            command = rule.build.format(manifest=manifest)
            found["build"].append(
                _Candidate(
                    _RANK_CONVENTION,
                    command,
                    manifest,
                    f"standard `{command}` for the project declared in {manifest}; no workflow "
                    "step or script names it",
                    "toolchain convention",
                )
            )
        if rule.test and tested and _manifest_mentions(clone_path, manifest, rule.test_needs):
            command = rule.test.format(manifest=manifest)
            found["test"].append(
                _Candidate(
                    _RANK_CONVENTION,
                    command,
                    manifest,
                    f"standard `{command}` for the project declared in {manifest}, which has "
                    "tests in the tree; no workflow step or script names it",
                    "toolchain convention",
                )
            )
    return found


def _manifest_mentions(clone_path: Path, manifest: str, needle: str) -> bool:
    if not needle:
        return True
    try:
        file = clone_path / manifest
        if file.stat().st_size > _MAX_MANIFEST_BYTES:
            return False
        return needle in file.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return False


_SOURCES = (
    _workflow_candidates,
    _script_candidates,
    _makefile_candidates,
    _convention_candidates,
)


def command_facts(clone_path: Path, tree_paths: Sequence[str]) -> list[Fact]:
    """The build command and the test command the clone's own files name, one fact each.

    Several candidates of the best rank resolve to the first by (path, command), so the same tree
    always yields the same fact. A role no source names yields no fact and the section says
    nothing about it.
    """
    candidates: dict[str, list[_Candidate]] = {"build": [], "test": []}
    for source in _SOURCES:
        for role, found in source(clone_path, tree_paths).items():
            candidates[role].extend(found)
    facts: list[Fact] = []
    for role, identifier in (("build", BUILD_COMMAND_FACT_ID), ("test", TEST_COMMAND_FACT_ID)):
        if not candidates[role]:
            continue
        chosen = min(candidates[role], key=lambda c: (c.rank, c.path, c.command))
        facts.append(
            Fact(
                identifier,
                "build_test_asset",
                chosen.command,
                (Evidence(chosen.path, f"{role} command; {chosen.detail}"),),
                attributes={"role": f"{role} command", "source": chosen.source},
            )
        )
    return facts


# --- The CI matrix ---------------------------------------------------------------------------
# The matrix axes that say where the code is exercised: operating systems and language runtimes.
# Anything else (a feature flag, an archive format) says nothing a reader needs here.
_MATRIX_AXES = (
    "os",
    "python-version",
    "python",
    "node-version",
    "node",
    "dotnet-version",
    "dotnet",
    "go-version",
    "go",
    "java-version",
    "java",
    "jdk",
    "rust",
    "toolchain",
)
_MAX_AXIS_VALUES = 8
_PREFERRED_STEMS = ("ci", "build", "test", "tests", "main")


def _scalars(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    found: list[str] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, str | int | float):
            continue
        text = str(value).strip()
        if text and "${{" not in text and text not in found:
            found.append(text)
    return found


def _matrix_axes(matrix: Any) -> dict[str, list[str]]:
    """The reported axes of one ``strategy.matrix``: its own lists, then the values its ``include``
    entries add to the same keys (a matrix written only as ``include`` names its axes there)."""
    if not isinstance(matrix, dict):
        return {}
    axes: dict[str, list[str]] = {}
    for key in _MATRIX_AXES:
        values = _scalars(matrix.get(key))
        if values:
            axes[key] = values
    include = matrix.get("include")
    for entry in include if isinstance(include, list) else []:
        if not isinstance(entry, dict):
            continue
        for key in _MATRIX_AXES:
            added = _scalars([entry.get(key)]) if key in entry else []
            for value in added:
                if value not in axes.setdefault(key, []):
                    axes[key].append(value)
    return {key: values[:_MAX_AXIS_VALUES] for key, values in axes.items() if values}


def ci_matrix_fact(clone_path: Path, tree_paths: Sequence[str]) -> Fact | None:
    """The operating systems and runtimes the repository's own CI exercises.

    Read from the first job of the preferred non-release workflow that declares a matrix with at
    least one reported axis. The value is ``axis=value,value;axis=value`` in the matrix's own
    order of ``_MATRIX_AXES``; every value is the workflow's literal text (a YAML float such as
    ``3.10`` is kept as written, never read as 3.1).
    """
    found: list[tuple[tuple[int, str], str, str, dict[str, list[str]]]] = []
    for path, document in workflow_documents(clone_path, tree_paths):
        if is_release_workflow(path):
            continue
        jobs = document.get("jobs")
        if not isinstance(jobs, dict):
            continue
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        rank = (
            _PREFERRED_STEMS.index(stem) if stem in _PREFERRED_STEMS else len(_PREFERRED_STEMS),
            path,
        )
        for job_id, job in jobs.items():
            strategy = job.get("strategy") if isinstance(job, dict) else None
            axes = _matrix_axes(strategy.get("matrix") if isinstance(strategy, dict) else None)
            if axes:
                found.append((rank, path, str(job_id), axes))
                break
    if not found:
        return None
    _rank, path, job_id, axes = min(found, key=lambda item: item[0])
    value = ";".join(f"{key}={','.join(values)}" for key, values in axes.items())
    return Fact(
        CI_MATRIX_FACT_ID,
        "build_test_asset",
        value,
        (Evidence(path, f"job {job_id} strategy.matrix axes {', '.join(axes)}"),),
        attributes={"role": "ci matrix", "workflow": path},
    )


def matrix_axes(fact: Fact) -> list[tuple[str, list[str]]]:
    """The ``(axis, values)`` pairs of a ``ci-matrix`` fact's value, in order."""
    pairs: list[tuple[str, list[str]]] = []
    for part in fact.value.split(";"):
        key, _, values = part.partition("=")
        if key and values:
            pairs.append((key, values.split(",")))
    return pairs


__all__ = [
    "BUILD_COMMAND_FACT_ID",
    "CI_MATRIX_FACT_ID",
    "CONVENTIONS",
    "TEST_COMMAND_FACT_ID",
    "ConventionRule",
    "ci_matrix_fact",
    "command_facts",
    "matrix_axes",
]
