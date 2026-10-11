"""Synthetic upstream repositories for the local workflow rehearsal (TC-REF-11-01 scaffolding).

Each scenario is a local bare git repository under ``<world>/upstreams/rehearsal-org/<name>.git``
with deterministic history (fixed author, committer and dates, so a scenario's commit ids are
stable across runs and machines). ``world.json`` beside them carries what git cannot: archived and
deleted repositories, head overrides, and injected HTTP failures; the fake GitHub service
(``fake_github.py``) reads it. Nothing here touches a network or a real repository.

The scenario table is returned by ``build_world`` and written to ``scenarios.json``:
``name, repository, sealed_revision, head_revision, expectation``. ``sealed_revision`` is the commit
a notional sealed candidate was built from; ``head_revision`` is what the upstream serves now.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OWNER = "rehearsal-org"
_DATE = "2026-01-01T00:00:00+00:00"
_ENV = {
    "GIT_AUTHOR_NAME": "Rehearsal",
    "GIT_AUTHOR_EMAIL": "rehearsal@example.invalid",
    "GIT_COMMITTER_NAME": "Rehearsal",
    "GIT_COMMITTER_EMAIL": "rehearsal@example.invalid",
    "GIT_AUTHOR_DATE": _DATE,
    "GIT_COMMITTER_DATE": _DATE,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}

BASE_FILES = {
    "README.md": "# Synthetic\n\nA synthetic upstream used by the workflow rehearsal.\n",
    "pyproject.toml": '[project]\nname = "synthetic"\nversion = "1.0.0"\n',
    "src/synthetic/__init__.py": "def hello():\n    return 'hello'\n",
    "docs/NOTES.md": "Notes.\n",
}


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    expectation: str


SCENARIOS = (
    Scenario("relevant-change", "a commit touching a source file the README consumed",
             "classified as a relevant change: exactly one candidate update"),
    Scenario("irrelevant-change", "a commit touching only an unconsumed documentation file",
             "head moved, bundle still current: no update"),
    Scenario("maintainer-readme-edit", "a maintainer edits README.md upstream after the seal",
             "reconciled by the inherited-content path, never overwritten"),
    Scenario("force-pushed-history", "history rewritten so the sealed revision is unreachable",
             "sealed revision gone: treated as drift, never as no change"),
    Scenario("deleted-repository", "the repository no longer exists (HTTP 404)",
             "unreachable: recorded, no write"),
    Scenario("archived-repository", "the repository is archived (read-only upstream)",
             "observed, never proposed to"),
    Scenario("unchanged", "no commit after the sealed revision",
             "zero provider calls, no update"),
)


def _remove(path: Path) -> None:
    """Remove a tree, including git's read-only object files (Windows)."""

    def retry(function: Any, target: str, _info: Any) -> None:
        os.chmod(target, 0o700)
        function(target)

    shutil.rmtree(path, onerror=retry)


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env={**os.environ, **_ENV}, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _commit(work: Path, message: str, files: dict[str, str]) -> str:
    for relative, content in files.items():
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    _git(["add", "-A"], work)
    _git(["commit", "-q", "-m", message], work)
    return _git(["rev-parse", "HEAD"], work)


def build_repository(
    world: Path,
    name: str,
    steps: list[tuple[str, dict[str, str]]],
    *,
    owner: str = OWNER,
    rewrite_first: bool = False,
) -> list[str]:
    """Create ``<world>/upstreams/<OWNER>/<name>.git`` from ``steps``; return each commit id.

    ``rewrite_first`` replaces the first commit afterwards with a different root (a force-push), so
    the id of commit 0 is no longer reachable from the head.
    """
    bare = world / "upstreams" / owner / f"{name}.git"
    if bare.exists():
        _remove(bare)
    work = world / "work" / name
    if work.exists():
        _remove(work)
    work.mkdir(parents=True)
    _git(["init", "-q", "-b", "main"], work)
    commits = [_commit(work, message, files) for message, files in steps]
    if rewrite_first:
        # A new root with different content, then the remaining history replayed on top of it.
        _git(["checkout", "-q", "--orphan", "rewritten"], work)
        _git(["rm", "-rfq", "."], work)
        _commit(work, "rewritten root", {**BASE_FILES, "README.md": BASE_FILES["README.md"] + "(rewritten)\n"})
        _git(["branch", "-M", "main"], work)
        commits.append(_git(["rev-parse", "HEAD"], work))
    bare.parent.mkdir(parents=True, exist_ok=True)
    _git(["clone", "-q", "--bare", str(work), str(bare)], world)
    _git(["config", "http.uploadpack", "true"], bare)
    _remove(work)
    return commits


def build_world(world: Path) -> list[dict[str, Any]]:
    """Build every scenario under ``world``; write ``world.json`` and ``scenarios.json``."""
    world.mkdir(parents=True, exist_ok=True)
    first = ("initial", BASE_FILES)
    rows: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"archived": [], "deleted": [], "heads": {}, "failures": {}}
    plans: dict[str, tuple[list[tuple[str, dict[str, str]]], bool]] = {
        "unchanged": ([first], False),
        "relevant-change": (
            [first, ("change public API", {"src/synthetic/__init__.py": "def hello(name):\n    return name\n"})],
            False,
        ),
        "irrelevant-change": ([first, ("update notes", {"docs/NOTES.md": "More notes.\n"})], False),
        "maintainer-readme-edit": (
            [first, ("edit README", {"README.md": BASE_FILES["README.md"] + "\nMaintainer paragraph.\n"})],
            False,
        ),
        "force-pushed-history": ([first, ("second", {"docs/NOTES.md": "Second.\n"})], True),
        "archived-repository": ([first], False),
        "deleted-repository": ([first], False),
    }
    for scenario in SCENARIOS:
        steps, rewrite = plans[scenario.name]
        commits = build_repository(world, scenario.name, steps, rewrite_first=rewrite)
        repository = f"{OWNER}/{scenario.name}"
        if scenario.name == "archived-repository":
            meta["archived"].append(repository)
        if scenario.name == "deleted-repository":
            meta["deleted"].append(repository)
        rows.append(
            {
                "name": scenario.name,
                "repository": repository,
                "description": scenario.description,
                "expectation": scenario.expectation,
                "sealed_revision": commits[0],
                "head_revision": commits[-1],
            }
        )
    (world / "world.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (world / "scenarios.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rows


if __name__ == "__main__":
    import sys

    for row in build_world(Path(sys.argv[1])):
        print(row["name"], row["sealed_revision"][:10], row["head_revision"][:10])
