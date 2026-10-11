"""Workflow shape checks: the part of actionlint that needs no binary, plus an actionlint wrapper.

TC-REF-10-01. ``check_workflow`` returns a list of typed findings for one parsed workflow; an empty
list is clean. ``run_actionlint`` runs the real ``actionlint`` binary when one is available (the
``ACTIONLINT`` environment variable, ``actionlint`` on PATH, or ``D:/tools/actionlint``) and returns
``None`` when it is not, so a test can skip rather than fail. Neither touches a network.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from inventory import REPO_ROOT, WORKFLOWS_DIR, load_workflow

_EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.S)
_STEPS_REF = re.compile(r"\bsteps\.([A-Za-z_][A-Za-z0-9_-]*)")
_NEEDS_REF = re.compile(r"\bneeds\.([A-Za-z_][A-Za-z0-9_-]*)")
_MATRIX_REF = re.compile(r"\bmatrix\.([A-Za-z_][A-Za-z0-9_-]*)")
# Event fields a third party controls; interpolated into a shell script they are an injection path.
_UNTRUSTED = re.compile(
    r"github\.event\.(?:issue|pull_request|comment|review|review_comment|head_commit|pages|"
    r"discussion|commits)\.[A-Za-z0-9_.\[\]*]*(?:title|body|name|label|ref|message|email|login)\b"
    r"|github\.head_ref"
)
_PINNED = re.compile(r"^[^@\s]+@(v\d+(?:\.\d+){0,2}|[0-9a-f]{40})$")
_CRON_FIELD = re.compile(r"^[0-9*/,\-]+$")


def _expressions(node: Any) -> list[str]:
    """Every ``${{ }}`` expression body found in any string inside ``node``."""
    found: list[str] = []
    if isinstance(node, str):
        found.extend(_EXPRESSION.findall(node))
    elif isinstance(node, dict):
        for value in node.values():
            found.extend(_expressions(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_expressions(value))
    return found


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def _cycle(graph: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> list[str] | None:
        if state.get(node) == 1:
            return [*trail[trail.index(node) :], node]
        if state.get(node) == 2:
            return None
        state[node] = 1
        for nxt in graph.get(node, []):
            if nxt in graph and (found := visit(nxt, [*trail, node])):
                return found
        state[node] = 2
        return None

    for start in graph:
        if found := visit(start, []):
            return found
    return None


def check_workflow(workflow: dict[str, Any], *, root: Path = REPO_ROOT) -> list[str]:
    """Typed findings for one parsed workflow (empty when clean)."""
    findings: list[str] = []
    for key in ("name", "on", "jobs"):
        if key not in workflow:
            findings.append(f"missing top-level key {key!r}")
    jobs = workflow.get("jobs") or {}
    if not jobs:
        findings.append("no jobs")
    if "permissions" not in workflow and not all("permissions" in j for j in jobs.values()):
        findings.append("no workflow-level permissions and not every job declares its own")
    on = workflow.get("on")
    if isinstance(on, dict):
        if "pull_request_target" in on:
            findings.append("pull_request_target is not allowed")
        for item in (on.get("schedule") or []):
            fields = str(item.get("cron", "")).split()
            if len(fields) != 5 or not all(_CRON_FIELD.match(f) for f in fields):
                findings.append(f"malformed cron {item.get('cron')!r}")
    graph = {job_id: _needs(job) for job_id, job in jobs.items()}
    for job_id, needs in graph.items():
        for need in needs:
            if need not in jobs:
                findings.append(f"job {job_id}: needs unknown job {need!r}")
    if (loop := _cycle(graph)) is not None:
        findings.append("needs cycle: " + " -> ".join(loop))
    for job_id, job in jobs.items():
        findings.extend(_check_job(job_id, job, graph[job_id], root))
    return findings


def _check_job(job_id: str, job: dict[str, Any], needs: list[str], root: Path) -> list[str]:
    findings: list[str] = []
    prefix = f"job {job_id}: "
    reusable = "uses" in job
    if reusable == ("runs-on" in job):
        findings.append(prefix + "exactly one of runs-on and uses (reusable call) is required")
    if reusable:
        ref = str(job["uses"])
        if ref.startswith("./") and not (root / ref[2:]).is_file():
            findings.append(prefix + f"reusable workflow {ref} does not exist")
    elif not job.get("steps"):
        findings.append(prefix + "no steps")
    step_ids: set[str] = set()
    for index, step in enumerate(job.get("steps") or []):
        label = prefix + f"step {index + 1}"
        if ("run" in step) == ("uses" in step):
            findings.append(label + ": exactly one of run and uses is required")
        if "id" in step:
            if step["id"] in step_ids:
                findings.append(label + f": duplicate step id {step['id']!r}")
            step_ids.add(step["id"])
        uses = step.get("uses")
        if uses and not str(uses).startswith("./") and not _PINNED.match(str(uses)):
            findings.append(label + f": action {uses!r} is not pinned to a version or sha")
        if uses and str(uses).startswith("./") and not (root / str(uses)[2:]).exists():
            findings.append(label + f": local action {uses} does not exist")
        for expression in _EXPRESSION.findall(str(step.get("run", ""))):
            if _UNTRUSTED.search(expression):
                findings.append(label + f": untrusted event field in a script: {expression.strip()}")
    expressions = _expressions({k: v for k, v in job.items() if k != "steps"}) + _expressions(
        job.get("steps")
    )
    for ref in sorted(set(_STEPS_REF.findall(" ".join(expressions)))):
        if ref not in step_ids:
            findings.append(prefix + f"expression reads steps.{ref}, which no step of the job defines")
    for ref in sorted(set(_NEEDS_REF.findall(" ".join(expressions)))):
        if ref not in needs:
            findings.append(prefix + f"expression reads needs.{ref}, which the job does not list in needs")
    matrix = (job.get("strategy") or {}).get("matrix")
    if not matrix:
        used = sorted(set(_MATRIX_REF.findall(" ".join(expressions))))
        if used:
            findings.append(prefix + f"expression reads matrix.{used[0]} but the job has no matrix")
    return findings


def check_all(directory: Path = WORKFLOWS_DIR, *, root: Path = REPO_ROOT) -> dict[str, list[str]]:
    """File name -> findings, for every workflow in ``directory``."""
    return {p.name: check_workflow(load_workflow(p), root=root) for p in sorted(directory.glob("*.yml"))}


def find_actionlint() -> str | None:
    """Path to an actionlint binary, or ``None``."""
    explicit = os.environ.get("ACTIONLINT")
    if explicit and Path(explicit).is_file():
        return explicit
    on_path = shutil.which("actionlint")
    if on_path:
        return on_path
    for candidate in ("D:/tools/actionlint/actionlint.exe", "D:/tools/actionlint/actionlint"):
        if Path(candidate).is_file():
            return candidate
    return None


def run_actionlint(directory: Path = WORKFLOWS_DIR) -> tuple[int, str] | None:
    """``(exit code, output)`` of actionlint over every workflow, or ``None`` when not installed."""
    binary = find_actionlint()
    if binary is None:
        return None
    files = sorted(str(p) for p in directory.glob("*.yml"))
    result = subprocess.run([binary, "-no-color", *files], capture_output=True, text=True, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


if __name__ == "__main__":
    bad = 0
    for name, found in check_all().items():
        for finding in found:
            bad += 1
            print(f"{name}: {finding}")
    lint = run_actionlint()
    print("actionlint: not installed" if lint is None else f"actionlint exit {lint[0]}\n{lint[1]}")
    raise SystemExit(1 if bad or (lint and lint[0]) else 0)
