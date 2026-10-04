"""Build and test assets read from the tree inventory: tests, CI workflows, docs, examples."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from repository_presenter.core.facts import Evidence, Fact, fact_id

_MAX_EVIDENCE_PATHS = 5
_WORKFLOW_PREFIX = ".github/workflows/"
_MAX_WORKFLOW_BYTES = 256 * 1024
# The workflow file names the badge URL carries verbatim: no path separator, no query, no space.
_WORKFLOW_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.ya?ml")
# A workflow that exists to publish, deploy, scan, or tend the repository is not its build status.
_NOT_BUILD_STATUS = re.compile(
    r"(?i)publish|release|deploy|pages|docs?\b|codeql|dependabot|label|stale|sync|mirror|welcome"
)
# A run step that builds, tests, or checks the code: the evidence a workflow is a real build.
_BUILD_STEP = re.compile(
    r"(?i)\b(pytest|tox|nox|unittest|ctest|cmake|cargo|dotnet|mvn|gradle|gradlew|make|msbuild"
    r"|go (?:test|build|vet)|npm (?:test|run build|ci|run test)|yarn (?:test|build)"
    r"|pnpm (?:test|build)|ruff|mypy|python -m (?:pytest|unittest|build)|test|build)\b"
)
_PREFERRED_STEMS = ("ci", "build", "test", "tests", "main")
_BRANCH_GLOB = re.compile(r"[*?\[!]")
_EVERY_BRANCH = frozenset({"**", "*"})
_DEFAULT_BRANCHES = frozenset({"main", "master", "**", "*"})
# The shell-owned link target a build-status badge renders from (renderer.badge_slots): the
# verified workflow page. A link_target, like the banner and Enterprise targets, so no new fact
# kind; planning keeps it out of every model-assignable link.
CI_BADGE_FACT_ID = fact_id("link_target", "badge.ci")


def _directory_fact(name: str, prefix: str, paths: Sequence[str], detail: str) -> Fact | None:
    matches = sorted(path for path in paths if path.startswith(prefix))
    if not matches:
        return None
    evidence = tuple(Evidence(path) for path in matches[:_MAX_EVIDENCE_PATHS])
    return Fact(
        fact_id("build_test_asset", name),
        "build_test_asset",
        prefix,
        (*evidence, Evidence(prefix, f"{len(matches)} files; {detail}")),
    )


def _triggers(document: dict[Any, Any]) -> dict[str, Any]:
    """The workflow's ``on`` as a mapping of event name to its config. YAML 1.1 reads the bare
    key ``on`` as boolean ``True``, so both spellings are tried."""
    raw = document.get("on", document.get(True))
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {str(item): None for item in raw if isinstance(item, str)}
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _build_step(document: dict[Any, Any]) -> str | None:
    """The first ``run`` command, in file order, that builds, tests, or checks the code."""
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return None
    for job in jobs.values():
        steps = job.get("steps") if isinstance(job, dict) else None
        for step in steps if isinstance(steps, list) else []:
            command = step.get("run") if isinstance(step, dict) else None
            if isinstance(command, str):
                match = _BUILD_STEP.search(command)
                if match is not None:
                    return match.group(0).lower()
    return None


def _branch(push: Any) -> tuple[bool, str | None]:
    """``(usable, branch)`` for a push trigger.

    A push with no filter, with ``branches: ['**']`` (every branch), or with a
    ``branches-ignore`` that spares ``main`` and ``master`` runs on the default branch, so its
    status exists and the badge names no branch. A filter that lists literal branches names
    ``main``, ``master``, or the first listed. A push that filters only ``tags``, ignores the
    default branch, or lists only partial globs has no default-branch status to show: unusable.
    """
    if not isinstance(push, dict):
        return True, None
    branches = push.get("branches")
    if branches is None:
        if push.get("tags") is not None or push.get("tags-ignore") is not None:
            return False, None  # tags only: a branch push does not trigger it
        ignored = push.get("branches-ignore")
        if isinstance(ignored, str):
            ignored = [ignored]
        if isinstance(ignored, list) and any(b in _DEFAULT_BRANCHES for b in ignored):
            return False, None
        return True, None
    if isinstance(branches, str):
        branches = [branches]
    if not isinstance(branches, list):
        return False, None
    names = [b for b in branches if isinstance(b, str) and b]
    if any(b in _EVERY_BRANCH for b in names):
        return True, None
    literal = [b for b in names if not _BRANCH_GLOB.search(b)]
    if not literal:
        return False, None
    for preferred in ("main", "master"):
        if preferred in literal:
            return True, preferred
    return True, literal[0]


def ci_badge_fact(repository: str, clone_path: Path, tree_paths: Sequence[str]) -> Fact | None:
    """The build-status badge target: the one workflow in the clone that is a real build status.

    plans/idea.md: "real build status ... may not be ... fabricated merely to fill the row." A
    workflow qualifies only when its file name is safe to put in a badge URL, it is not a
    publish/deploy/scan workflow, it is triggered by ``push`` (so the default branch has a
    status; a pull-request-only or manual workflow has none), and one of its steps runs a build,
    test, or check command. The badge's branch is read from the workflow's own ``push.branches``,
    never assumed. Several qualifying workflows resolve to the preferred stem (``ci``, ``build``,
    ``test``...) then the first by name; none qualifying is ``None``, and the row has no build
    slot. Nothing is read from the network: the file at this revision is the target.
    """
    qualifying: list[tuple[str, str, str | None, str]] = []
    for path in sorted(tree_paths):
        name = path[len(_WORKFLOW_PREFIX) :]
        if not path.startswith(_WORKFLOW_PREFIX) or not _WORKFLOW_FILE.fullmatch(name):
            continue
        if _NOT_BUILD_STATUS.search(name):
            continue
        file = clone_path / path
        try:
            if file.stat().st_size > _MAX_WORKFLOW_BYTES:
                continue
            document = yaml.safe_load(file.read_text("utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if not isinstance(document, dict):
            continue
        triggers = _triggers(document)
        if "push" not in triggers:
            continue
        usable, branch = _branch(triggers["push"])
        step = _build_step(document)
        if usable and step is not None:
            qualifying.append((path, name, branch, step))
    if not qualifying:
        return None

    def rank(item: tuple[str, str, str | None, str]) -> tuple[int, str]:
        stem = item[1].rsplit(".", 1)[0].lower()
        return (
            _PREFERRED_STEMS.index(stem) if stem in _PREFERRED_STEMS else len(_PREFERRED_STEMS),
            item[1],
        )

    path, name, branch, step = min(qualifying, key=rank)
    url = f"https://github.com/{repository}/actions/workflows/{name}"
    where = f"push on {branch}" if branch else "push on every branch"
    return Fact(
        CI_BADGE_FACT_ID,
        "link_target",
        url,
        (Evidence(path, f"triggers {where}; runs {step}; build status badge target"),),
        attributes={
            "role": "build status badge",
            "workflow": path,
            **({"branch": branch} if branch else {}),
        },
    )


def asset_facts(tree_paths: Sequence[str]) -> list[Fact]:
    """One fact per asset class present in the tree, with the paths that prove it."""
    candidates = (
        _directory_fact("tests", "tests/", tree_paths, "test suite"),
        _directory_fact("ci", ".github/workflows/", tree_paths, "GitHub Actions workflows"),
        _directory_fact("docs", "docs/", tree_paths, "documentation directory"),
        _directory_fact("examples", "examples/", tree_paths, "example directory"),
    )
    return [fact for fact in candidates if fact is not None]
