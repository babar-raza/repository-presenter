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

A workflow command is read as part of ONE job's own steps, never stitched from unrelated ones
(the independent reviews of 2026-10-11: a release job's Debug build beside a package-consumer
``ctest --test-dir build-pkgtest``, and a sanitizer job's ``cmake --build build-asan`` without the
configure step that creates ``build-asan``; both fail on a clean clone). A command that works in a
build directory (``cmake --build X``, ``ctest --test-dir X``) is admitted only when the same job
configures X earlier with one printable, unconditional ``cmake -S . -B X``, which the fact then
carries as its ``precondition``; a test in a build directory must share the chosen build's job and
directory. Sanitizer, coverage, benchmark, documentation, package-test, minimum-toolchain and (in
a non-release workflow) release or package jobs, steps that run in another directory, and steps
that hold shell control flow are never read: no command is better than a wrong one. A tool the
project does not itself declare is named as a ``precondition`` too (``python -m build`` needs
``pip install build``).
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
RELEASE_WORKFLOW_FACT_ID = fact_id("build_test_asset", "release-workflow")
# The attribute a command fact carries when a reader must run something first: newline-joined.
PRECONDITION_ATTRIBUTE = "precondition"

_SAFE_LINE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_ ./:=@+,-]*")
_UNSAFE_WORD = re.compile(
    r"(?i)deploy|publish|token|secret|password|api-?key|sign|upload|push|twine|release"
)
# A build configuration named "Release" is not a release action: CMake and CTest take it as
# ``--config Release``, ``--build-config Release``, ``-C Release`` and
# ``-DCMAKE_BUILD_TYPE=Release``.
_BUILD_CONFIGURATION = re.compile(
    r"(?:--(?:build-)?config[ =]|-C |-DCMAKE_BUILD_TYPE=)(?i:release)\b"
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
    # A workflow command's job, and the build directory it works in (``None``: it works in none)
    # with the configure command that creates that directory in the same job.
    job: str = ""
    directory: str | None = None
    setup: tuple[str, ...] = ()


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


def _role_of(command: str) -> str | None:
    if any(rule.search(command) for rule in _TEST_RULES):
        return "test"
    if any(rule.search(command) for rule in _BUILD_RULES):
        return "build"
    return None


# Jobs and steps that are not the project's own build and test: a sanitizer, coverage, benchmark,
# documentation, package-consumer, packaging or minimum-toolchain leg builds a variant a reader
# cannot reproduce from the plain commands. Release and package jobs are also skipped in a
# workflow that is not itself a release workflow (a release workflow's own are all it has).
_SIDE_JOB = re.compile(
    r"(?i)sanitiz|\b(?:a|ub|t|m)san\b|valgrind|coverage|codecov|bench|\bdocs?\b|pkg-?test"
    r"|package[-_ ]?test|smoke|consumer|nuget|sbom|floor|minimum|reproducib"
)
_RELEASE_JOB = re.compile(r"(?i)release|publish|deploy|\bpack(?:age)?\b")
# A run that holds shell control flow runs its commands conditionally or repeatedly.
_CONTROL_LINE = re.compile(r"(?:if|for|while|until|case|then|else|elif|fi|do|done|esac)(?![\w./-])")
_CONFIGURE_LINE = re.compile(r"(?:^|\s)cmake\s(?!.*--build)(?=.*\s-B\s?(?P<dir>[^\s\\]+))")
_CONFIGURE_SOURCE = re.compile(r"\s-S\s?(?P<source>[^\s\\]+)")
_BUILD_DIRECTORY = re.compile(
    r"^cmake --build (?P<dir>[^\s-]\S*)|^ctest .*--test-dir[ =](?P<test>\S+)"
)
# The tools a build command needs that the project does not itself declare.
PRECONDITIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^python3? -m build\b"), "pip install build"),
)
_NODE_SCRIPT = re.compile(r"^npm (?:test|run (?P<name>[A-Za-z0-9:_-]+))\b")


@dataclass(frozen=True)
class _Run:
    """One line of one ``run`` step of a job, in file order."""

    line: str
    admitted: bool
    conditional: bool


def _admitted(line: str) -> bool:
    return (
        bool(line)
        and not line.endswith("\\")
        and len(line) <= _MAX_COMMAND_LENGTH
        and _SAFE_LINE.fullmatch(line) is not None
        and _UNSAFE_WORD.search(_BUILD_CONFIGURATION.sub("", line)) is None
    )


def _is_side(name: str, release: bool) -> bool:
    return _SIDE_JOB.search(name) is not None or (
        not release and _RELEASE_JOB.search(name) is not None
    )


def _elsewhere(step: dict[Any, Any], job: dict[Any, Any]) -> bool:
    """Whether a step runs in a directory other than the repository root."""
    defaults = job.get("defaults")
    run_defaults = defaults.get("run") if isinstance(defaults, dict) else None
    inherited = run_defaults.get("working-directory") if isinstance(run_defaults, dict) else None
    directory = step.get("working-directory", inherited)
    return isinstance(directory, str) and directory.strip() not in {"", ".", "./"}


def _job_runs(job: dict[Any, Any], release: bool) -> list[_Run]:
    steps = job.get("steps")
    runs: list[_Run] = []
    for step in steps if isinstance(steps, list) else []:
        run = step.get("run") if isinstance(step, dict) else None
        if not isinstance(run, str) or _elsewhere(step, job):
            continue
        if _SIDE_JOB.search(str(step.get("name", ""))):
            continue
        lines = [raw.strip().removeprefix("$ ").strip() for raw in run.splitlines()]
        controlled = any(_CONTROL_LINE.match(line) for line in lines)
        conditional = "if" in step
        runs.extend(
            _Run(line, not controlled and _admitted(line), conditional)
            for line in lines
            if line and not line.startswith("#")
        )
    return runs


def _build_directory(command: str) -> str | None:
    """The build directory a ``cmake --build`` or ``ctest`` command works in, ``""`` when it names
    none (it then works in the current directory, which no earlier step is shown to have set), and
    ``None`` for a command that works in no build directory."""
    match = _BUILD_DIRECTORY.match(command)
    if match is not None:
        return match.group("dir") or match.group("test")
    return "" if command.startswith(("cmake --build", "ctest")) else None


def _configure_for(directory: str, runs: list[_Run], before: int) -> str | None:
    """The one printable, unconditional ``cmake -S . -B <directory>`` an earlier line of the job
    runs, or ``None`` when there is none, when a configure of it cannot be printed (a variable, a
    continuation, a conditional leg, a source other than the root), or when two differ."""
    if not directory:
        return None
    configures: list[_Run] = []
    for run in runs[:before]:
        match = _CONFIGURE_LINE.search(run.line)
        if match is None or match.group("dir") != directory:
            continue
        source = _CONFIGURE_SOURCE.search(run.line)
        if source is not None and source.group("source") not in {".", "./"}:
            return None
        configures.append(run)
    if not configures or any(r.conditional or not r.admitted for r in configures):
        return None
    commands = {run.line for run in configures}
    return commands.pop() if len(commands) == 1 else None


def _package_scripts(clone_path: Path, tree_paths: Sequence[str]) -> dict[str, Any] | None:
    """The root ``package.json``'s ``scripts``, or ``None`` when there is none to read."""
    if "package.json" not in tree_paths:
        return None
    try:
        file = clone_path / "package.json"
        if file.stat().st_size > _MAX_MANIFEST_BYTES:
            return None
        document = json.loads(file.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    scripts = document.get("scripts") if isinstance(document, dict) else None
    return scripts if isinstance(scripts, dict) else None


def _names_a_missing_script(command: str, scripts: dict[str, Any] | None) -> bool:
    """Whether an ``npm test`` or ``npm run <name>`` command names a script the root package.json
    does not define (it would fail on a clean clone)."""
    match = _NODE_SCRIPT.match(command)
    if match is None:
        return False
    return not _script_defined(scripts, match.group("name") or "test")


def _workflow_candidates(
    clone_path: Path, tree_paths: Sequence[str]
) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    scripts = _package_scripts(clone_path, tree_paths)
    for path, document in workflow_documents(clone_path, tree_paths):
        jobs = document.get("jobs")
        if not isinstance(jobs, dict):
            continue
        release = is_release_workflow(path)
        for job_id, job in jobs.items():
            if not isinstance(job, dict) or _is_side(f"{job_id} {job.get('name', '')}", release):
                continue
            runs = _job_runs(job, release)
            for position, run in enumerate(runs):
                role = _role_of(run.line) if run.admitted else None
                if role is None or _names_a_missing_script(run.line, scripts):
                    continue
                directory = _build_directory(run.line)
                configure = None
                if directory is not None:
                    configure = _configure_for(directory, runs, position)
                    if configure is None:
                        continue
                found[role].append(
                    _Candidate(
                        _RANK_RELEASE_CI if release else _RANK_CI,
                        run.line,
                        path,
                        f"job {job_id} runs `{run.line}`",
                        "ci workflow",
                        str(job_id),
                        directory,
                        (configure,) if configure is not None else (),
                    )
                )
    return found


def _script_defined(scripts: dict[str, Any] | None, name: str) -> bool:
    body = scripts.get(name) if scripts is not None else None
    return isinstance(body, str) and bool(body.strip()) and "no test specified" not in body


def _script_candidates(clone_path: Path, tree_paths: Sequence[str]) -> dict[str, list[_Candidate]]:
    found: dict[str, list[_Candidate]] = {"build": [], "test": []}
    scripts = _package_scripts(clone_path, tree_paths)
    for name, role, command in (("test", "test", "npm test"), ("build", "build", "npm run build")):
        if _script_defined(scripts, name):
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
    nothing about it. A test that works in a build directory is kept only beside the chosen build
    of the same job and directory; otherwise no test is named rather than one that cannot run.
    """
    candidates: dict[str, list[_Candidate]] = {"build": [], "test": []}
    for source in _SOURCES:
        for role, found in source(clone_path, tree_paths).items():
            candidates[role].extend(found)

    def best(options: list[_Candidate]) -> _Candidate | None:
        return min(options, key=lambda c: (c.rank, c.path, c.command, c.job), default=None)

    build = best(candidates["build"])
    chain = (build.path, build.job, build.directory) if build is not None else None
    test = best(
        [
            c
            for c in candidates["test"]
            if c.directory is None or (c.path, c.job, c.directory) == chain
        ]
    )
    facts: list[Fact] = []
    for role, identifier, chosen in (
        ("build", BUILD_COMMAND_FACT_ID, build),
        ("test", TEST_COMMAND_FACT_ID, test),
    ):
        if chosen is None:
            continue
        setup = (
            *chosen.setup,
            *(need for rule, need in PRECONDITIONS if rule.search(chosen.command)),
        )
        detail = f"{role} command; {chosen.detail}" + "".join(f"; after `{need}`" for need in setup)
        attributes = {"role": f"{role} command", "source": chosen.source}
        if setup:
            attributes[PRECONDITION_ATTRIBUTE] = "\n".join(setup)
        facts.append(
            Fact(
                identifier,
                "build_test_asset",
                chosen.command,
                (Evidence(chosen.path, detail),),
                attributes=attributes,
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


# --- The release workflow --------------------------------------------------------------------
# A workflow is where releases run only if one of its steps publishes a package, uploads release
# assets or creates a release; its file name proves nothing (a ``ci.yml`` that only tests, or a
# ``lint.yml``, is not one), and a registry that holds nothing proves the same.
_PUBLISH_ACTIONS = frozenset(
    {
        "pypa/gh-action-pypi-publish",
        "softprops/action-gh-release",
        "actions/create-release",
        "actions/upload-release-asset",
        "ncipollo/release-action",
        "marvinpinto/action-automatic-releases",
        "svenstaro/upload-release-action",
        "goreleaser/goreleaser-action",
        "jreleaser/release-action",
        "googleapis/release-please-action",
        "js-devtools/npm-publish",
        "taiki-e/create-gh-release-action",
        "taiki-e/upload-rust-binary-action",
    }
)
_PUBLISH_COMMANDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("twine upload", re.compile(r"\btwine upload\b")),
    ("npm publish", re.compile(r"\b(?:npm|yarn|pnpm)(?: run)? publish\b")),
    ("cargo publish", re.compile(r"\bcargo publish\b")),
    ("nuget push", re.compile(r"\bnuget push\b")),
    ("mvn deploy", re.compile(r"\bmvnw?\b.*\b(?:deploy|release:perform)\b")),
    ("gradle publish", re.compile(r"\bgradlew?\b.*\bpublish(?!ToMavenLocal)")),
    ("gh release", re.compile(r"\bgh release (?:create|upload)\b")),
    ("goreleaser release", re.compile(r"\bgoreleaser release\b")),
    ("package publish", re.compile(r"\b(?:poetry|uv|hatch|flit|pdm) publish\b")),
    ("gem push", re.compile(r"\bgem push\b")),
)
# A rehearsal or a test index publishes nothing a user installs.
_NOT_A_RELEASE = re.compile(r"(?i)--dry-run|test\.pypi\.org|testpypi")
# A comment or an echoed message names a command without running it.
_NOT_A_COMMAND = re.compile(r"\s*(?:#|echo\b|printf\b)")


def _publishing_step(step: Any) -> str | None:
    """What a workflow step does that releases something, or ``None``."""
    if not isinstance(step, dict):
        return None
    uses = step.get("uses")
    if isinstance(uses, str):
        action = uses.split("@", 1)[0].strip().lower()
        if action in _PUBLISH_ACTIONS and not _NOT_A_RELEASE.search(str(step.get("with"))):
            return f"uses {action}"
    run = step.get("run")
    for line in run.splitlines() if isinstance(run, str) else []:
        if _NOT_A_RELEASE.search(line) or _NOT_A_COMMAND.match(line):
            continue
        for label, pattern in _PUBLISH_COMMANDS:
            if pattern.search(line):
                return f"runs {label}"
    return None


def release_workflow_fact(clone_path: Path, tree_paths: Sequence[str]) -> Fact | None:
    """The workflow whose own step publishes a package, uploads release assets or creates a
    release, or ``None`` when no workflow in the clone does (the renderer then writes no release
    sentence). Several resolve to one whose file name says publish or release, then the first by
    path, so the same tree always yields the same fact."""
    found: list[tuple[tuple[int, str], str, str, str]] = []
    for path, document in workflow_documents(clone_path, tree_paths):
        jobs = document.get("jobs")
        for job_id, job in jobs.items() if isinstance(jobs, dict) else []:
            steps = job.get("steps") if isinstance(job, dict) else None
            for step in steps if isinstance(steps, list) else []:
                action = _publishing_step(step)
                if action is not None:
                    named = re.search(r"(?i)publish|release", path.rsplit("/", 1)[-1]) is not None
                    found.append(((0 if named else 1, path), path, str(job_id), action))
                    break
    if not found:
        return None
    _rank, path, job_id, action = min(found, key=lambda item: item[0])
    return Fact(
        RELEASE_WORKFLOW_FACT_ID,
        "build_test_asset",
        path,
        (Evidence(path, f"release step; job {job_id} {action}"),),
        attributes={"role": "release workflow", "workflow": path},
    )


# --- Equivalent commands ---------------------------------------------------------------------
# Whether a command a README already shows makes another redundant: the same program, the same
# subcommand words and the same target, however the line is spelled (whitespace, a prompt, a
# ``python -m`` or ``uv run`` wrapper, ``npm run test`` for ``npm test``, flags, an extra goal as
# in ``mvn clean package`` for ``mvn package``).
_PROMPT = re.compile(r"^\s*(?:[$>]\s*)?")
_ENV_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*")
_WRAPPERS = (
    ("sudo",),
    ("time",),
    ("uv", "run"),
    ("poetry", "run"),
    ("pipenv", "run"),
    ("hatch", "run"),
    ("pdm", "run"),
    ("npx",),
    ("bundle", "exec"),
    ("python", "-m"),
    ("python3", "-m"),
    ("py", "-m"),
)
_PROGRAM_FAMILY = {"yarn": "npm", "pnpm": "npm", "bun": "npm", "mvnw": "mvn", "gradlew": "gradle"}
_PROJECT_FILE = re.compile(r"(?i)\.(?:sln|slnx|csproj|fsproj|vbproj|vcxproj)$")
_PATH_LIKE = re.compile(r"[/\\]|^\.+$|\.\w{1,6}$")
# A flag that opens a mode of its program is a subcommand word (``cmake --build``); the value of
# a flag is neither a subcommand nor a target, except the directories these flags name.
_MODE_FLAGS = frozenset({"--build", "--install", "--preset", "--workflow"})
_DIRECTORY_FLAGS = {
    "cmake": frozenset({"-B", "--build"}),
    "ctest": frozenset({"--test-dir"}),
    "make": frozenset({"-C"}),
}
_VALUE_FLAGS = {
    "cmake": frozenset({"-S", "-C", "-j", "--config", "--target", "--parallel"}),
    "ctest": frozenset({"-C", "-j", "-R", "-E", "--build-config", "--parallel"}),
    # ``-k``, ``-m`` and ``--filter`` narrow what runs, so their words stay subcommand words:
    # ``pytest -k slow`` does not stand in for ``pytest``.
    "dotnet": frozenset({"-c", "-f", "--configuration", "--framework", "--logger"}),
    "pytest": frozenset({"-n", "-p"}),
    "mvn": frozenset({"-pl", "-f", "-T", "-P"}),
    "make": frozenset({"-j"}),
}
_COMMAND_SPLIT = re.compile(r"\s*(?:&&|\|\||[;|])\s*")
_INLINE_CODE = re.compile(r"`+([^`\n]+)`+")
_FENCE = re.compile(r"(`{3,}|~{3,})")


@dataclass(frozen=True)
class CommandForm:
    """A command reduced to what makes it the same command: its program, its subcommand words and
    the targets it names."""

    program: str
    verbs: frozenset[str]
    targets: frozenset[str]

    def covers(self, other: CommandForm) -> bool:
        """Whether running this command already does what ``other`` does."""
        return (
            self.program == other.program
            and other.verbs <= self.verbs
            and (bool(other.verbs) or not self.verbs)
            and (not other.targets or other.targets <= self.targets)
        )


def command_form(text: str) -> CommandForm | None:
    """The ``CommandForm`` of one command line, or ``None`` for a line that is not one."""
    tokens = _PROMPT.sub("", text.split(" #", 1)[0]).split()
    if not tokens or tokens[0].startswith("#"):
        return None
    while tokens and _ENV_ASSIGNMENT.fullmatch(tokens[0]):
        tokens.pop(0)
    stripped = True
    while stripped and tokens:
        stripped = False
        for wrapper in _WRAPPERS:
            if len(tokens) > len(wrapper) and tuple(tokens[: len(wrapper)]) == wrapper:
                tokens, stripped = tokens[len(wrapper) :], True
    if not tokens:
        return None
    name = tokens[0].removeprefix("./").removeprefix(".\\").lower()
    name = re.sub(r"\.(?:cmd|bat|exe|sh)$", "", name)
    program = _PROGRAM_FAMILY.get(name, name)
    verbs: set[str] = set()
    targets: set[str] = set()
    directory_flags = _DIRECTORY_FLAGS.get(program, frozenset())
    value_flags = _VALUE_FLAGS.get(program, frozenset())
    pending = ""
    for token in tokens[1:]:
        if pending:
            if pending in directory_flags:
                targets.add(token.rstrip("/\\"))
            pending = ""
        elif token.startswith("-"):
            flag, equals, value = token.partition("=")
            if flag in _MODE_FLAGS:
                verbs.add(flag)
            if equals:
                if flag in directory_flags:
                    targets.add(value.rstrip("/\\"))
            elif flag in directory_flags or flag in value_flags:
                pending = flag
        elif (program == "npm" and token == "run") or (
            program in {"dotnet", "msbuild"} and _PROJECT_FILE.search(token)
        ):
            continue
        elif _PATH_LIKE.search(token):
            targets.add(token.rstrip("/\\"))
        else:
            verbs.add(token.lower())
    return CommandForm(program, frozenset(verbs), frozenset(targets))


def commands_in_text(text: str) -> list[CommandForm]:
    """Every command a README text shows: each line of a code fence or of an indented or prompted
    block, and each inline code span, split at ``&&``, ``;`` and pipes."""
    forms: list[CommandForm] = []
    fence = ""
    for raw in text.splitlines():
        marker = _FENCE.match(raw.strip())
        if marker is not None and (not fence or marker.group(1)[0] == fence):
            fence = "" if fence else marker.group(1)[0]
            continue
        if fence or raw.startswith(("    ", "\t")) or raw.lstrip().startswith(("$ ", "> ")):
            sources = [raw]
        else:
            sources = _INLINE_CODE.findall(raw)
        for source in sources:
            for part in _COMMAND_SPLIT.split(source):
                form = command_form(part)
                if form is not None:
                    forms.append(form)
    return forms


__all__ = [
    "BUILD_COMMAND_FACT_ID",
    "CI_MATRIX_FACT_ID",
    "CONVENTIONS",
    "PRECONDITIONS",
    "PRECONDITION_ATTRIBUTE",
    "RELEASE_WORKFLOW_FACT_ID",
    "TEST_COMMAND_FACT_ID",
    "CommandForm",
    "ConventionRule",
    "ci_matrix_fact",
    "command_facts",
    "command_form",
    "commands_in_text",
    "matrix_axes",
    "release_workflow_fact",
]
