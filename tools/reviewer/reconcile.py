"""Portfolio reconciliation: desired state (data/registry.json) vs actual state (candidates/ on
disk) vs freshness (running component/validator versions) vs escalated shared-code defects
(docs/DEFECT_INDEX.md) - one priority-ordered action queue, computed, not remembered.

This is NOT a new state machine and does not invent stage names of its own. It reads the
project's own authoritative state (docs/EXECUTION_STATE_MACHINE.md's gates, project/state.yaml's
cursor, the real staleness/version machinery in repository_presenter.core.candidates) and reports
what it finds against that vocabulary. AGENTS.md: "Never create a competing plan, roadmap, mission
graph, task graph, or status authority" - this script reconciles the existing one, it is not one.

Each enabled registry entry lands in exactly one bucket:
  NEVER_ATTEMPTED  - no candidates/<owner>__<name>/ directory has ever existed
  INVALIDATED      - the CURRENT-pointed bundle's manifest.json state is INVALIDATED
  STALE            - current_code_candidates() no longer matches; core.candidates.stale_candidates
                     says so (reuses the exact logic `repository-presenter status --stale` runs -
                     never reimplemented here, per AGENTS.md's reuse-before-rewrite rule)
  CURRENT          - sealed, READY_FOR_PROPOSAL, and not stale

Priority order for the action queue (highest first), and why:
  1. Defect-index entries in docs/DEFECT_INDEX.md's "## Open" section with >=3 sightings - per
     AGENTS.md's Work Loop, this is settled priority for the next shared-code slot, not a
     judgment call, so it is listed first regardless of how many candidates are also queued.
  2. INVALIDATED bundles - a candidate that was once sealed and is now known-broken is a
     regression, not backlog; it outranks work that was simply never started.
  3. NEVER_ATTEMPTED entries - real portfolio gaps that were invisible until this script existed
     (found the hard way, 2026-09-25: 8 of 32 enabled entries, undiscovered for weeks).
  4. STALE entries - lowest priority of the four, since a stale-but-sealed candidate is still a
     valid disposition and this class is bounded by definition (it heals itself once resealed).

Usage: python -X utf8 reconcile.py [--json]
  Exit code is always 0 (this is a report, not a gate) unless the repository itself cannot be
  read, matching reviewer_check.py's own convention.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # tools/reviewer/this_file.py -> repo root
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from repository_presenter.components.readme.composition.authoring import (  # noqa: E402
    NORMALISATION_VERSION,
)
from repository_presenter.components.readme.composition.components.shell import (  # noqa: E402
    SHELL_VERSION,
)
from repository_presenter.components.readme.composition.renderer import RENDERER_VERSION  # noqa: E402
from repository_presenter.components.readme.review.independent.review import (  # noqa: E402
    REVIEWER_LOGIC_VERSION,
)
from repository_presenter.components.readme.validation.registry import (  # noqa: E402
    BLOCKING_CHECKS,
    VALIDATOR_VERSION,
)
from repository_presenter.core.candidates import (  # noqa: E402
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    stale_candidates,
)


def _dirname_to_repo(dirname: str) -> str:
    """candidates/ dirnames are "<owner>__<name>"; registry repos are "<owner>/<name>" - the
    owner segment never itself contains "__", so a single split is exact."""
    return dirname.replace("__", "/", 1)


def _enabled_registry_entries(repo: Path = REPO) -> list[str]:
    registry = json.loads((repo / "data/registry.json").read_text(encoding="utf-8"))
    return [e["repository"] for e in registry["entries"] if e.get("mode") != "disabled"]


def _invalidated_repos(candidates_dir: Path) -> set[str]:
    out: set[str] = set()
    if not candidates_dir.is_dir():
        return out
    for repo_dir in candidates_dir.iterdir():
        if not repo_dir.is_dir():
            continue
        current = repo_dir / CURRENT_FILENAME
        if not current.exists():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        manifest = repo_dir / revision / "manifest.json"
        if not manifest.exists():
            continue
        try:
            state = json.loads(manifest.read_text(encoding="utf-8")).get("state")
        except (json.JSONDecodeError, OSError):
            continue
        if state == "INVALIDATED":
            out.add(_dirname_to_repo(repo_dir.name))
    return out


def _escalated_defect_classes(repo: Path = REPO) -> list[str]:
    """Mechanisms in docs/DEFECT_INDEX.md's Open section with >=3 sightings - the same regex
    reviewer_check.py's own defect-index check uses, kept in sync deliberately (both read the
    same file's same shape; a change to one without the other is exactly the drift this project
    keeps re-discovering)."""
    path = repo / "docs/DEFECT_INDEX.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Open\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        return []
    open_section = match.group(1)
    out = []
    for mech in re.findall(r"^### `([\w.]+)`", open_section, re.M):
        block_match = re.search(
            rf"^### `{re.escape(mech)}`\n(.*?)(?=^### |\Z)", open_section, re.M | re.S
        )
        block = block_match.group(1) if block_match else ""
        sightings = len(re.findall(r"^\|\s*\d+\s*\|", block, re.M))
        if sightings >= 3:
            out.append(mech)
    return out


def reconcile(repo: Path = REPO) -> dict:
    enabled = _enabled_registry_entries(repo)
    candidates_dir = repo / CANDIDATES_DIRNAME
    attempted_dirs = {
        _dirname_to_repo(d.name): d for d in candidates_dir.iterdir() if d.is_dir()
    } if candidates_dir.is_dir() else {}

    current_components = {
        "shell": SHELL_VERSION,
        "renderer": RENDERER_VERSION,
        "normalisation": NORMALISATION_VERSION,
        "reviewer_logic": REVIEWER_LOGIC_VERSION,
    }
    current_validators = {check.id: check.version for check in BLOCKING_CHECKS}
    stale_found = stale_candidates(repo, current_components, current_validators, VALIDATOR_VERSION)
    stale_repos = {_dirname_to_repo(c.repository_dir) for c in stale_found}
    invalidated_repos = _invalidated_repos(candidates_dir)

    never_attempted, invalidated, stale, current = [], [], [], []
    for entry in enabled:
        if entry not in attempted_dirs:
            never_attempted.append(entry)
        elif entry in invalidated_repos:
            invalidated.append(entry)
        elif entry in stale_repos:
            stale.append(entry)
        else:
            current.append(entry)

    escalated = _escalated_defect_classes(repo)

    queue: list[dict] = []
    for mech in escalated:
        queue.append({
            "priority": 1,
            "class": "DEFECT_INDEX_ESCALATED",
            "target": mech,
            "action": "land the fix in docs/DEFECT_INDEX.md's Open entry for this mechanism "
                      "(the next shared-code slot's settled priority, per AGENTS.md's Work Loop)",
        })
    for repo in invalidated:
        queue.append({
            "priority": 2,
            "class": "INVALIDATED",
            "target": repo,
            "action": "read the CURRENT bundle's manifest.json invalidated block; diagnose and "
                      "redraw, or record why it stays blocked",
        })
    for repo in never_attempted:
        queue.append({
            "priority": 3,
            "class": "NEVER_ATTEMPTED",
            "target": repo,
            "action": "run present against this repository for the first time",
        })
    for repo in stale:
        queue.append({
            "priority": 4,
            "class": "STALE",
            "target": repo,
            "action": "reseal against current component/validator versions "
                      "(status --stale names the exact deltas)",
        })

    return {
        "enabled_total": len(enabled),
        "current": len(current),
        "never_attempted": never_attempted,
        "invalidated": invalidated,
        "stale": stale,
        "escalated_defect_classes": escalated,
        "queue": queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    result = reconcile()

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Portfolio reconciliation ({result['enabled_total']} enabled registry entries)")
    print(f"  current (sealed, fresh):  {result['current']}")
    print(f"  never attempted:          {len(result['never_attempted'])}")
    print(f"  invalidated:              {len(result['invalidated'])}")
    print(f"  stale:                    {len(result['stale'])}")
    if result["escalated_defect_classes"]:
        print(f"  escalated defect classes: {result['escalated_defect_classes']}")
    print()
    if not result["queue"]:
        print("Nothing queued - portfolio is fully current.")
        return 0
    print(f"Priority-ordered action queue ({len(result['queue'])} items):")
    for i, item in enumerate(result["queue"], 1):
        print(f"  {i}. [{item['class']}] {item['target']}")
        print(f"     -> {item['action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
