"""Derived maps (card TC-LNT-01-04): regenerated from the plan, never edited by hand.

Every map opens with the three non-authority header lines and is a pure function of the plan, so
regenerating twice yields identical bytes. CSV files carry the header as ``# key: value`` comment
lines (the first non-comment row is the column header); the YAML map carries it as top-level keys.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import yaml

from .cards import Plan
from .rules import ancestors, depends_graph, parallel_pairs, write_conflicts

HEADER_ROLE = "analysis_or_evidence_only"
MAP_FILES = (
    "requirement-traceability.csv",
    "dag.yaml",
    "dependency-matrix.csv",
    "file-lock-map.csv",
)


def _header(plan_label: str) -> list[tuple[str, str]]:
    return [
        ("authoritative_plan", plan_label),
        ("artifact_role", HEADER_ROLE),
        ("execution_authority", "false"),
    ]


def _csv(plan_label: str, rows: list[list[str]]) -> str:
    out = io.StringIO()
    for key, value in _header(plan_label):
        out.write(f"# {key}: {value}\n")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerows(rows)
    return out.getvalue()


def traceability_csv(plan: Plan, plan_label: str) -> str:
    """requirement -> parent -> child -> micro-step, one row per micro-step."""
    rows: list[list[str]] = [
        ["requirement", "parent", "child", "micro", "op", "target", "done_when"]
    ]
    by_req: dict[str, list[Any]] = {req: [] for req in sorted(plan.defined_reqs)}
    for parent in plan.parents:
        for req in parent.reqs:
            by_req.setdefault(req, []).append(parent)
    for req in sorted(by_req):
        parents = by_req[req]
        if not parents:
            rows.append([req, "", "", "", "", "", ""])
        for parent in parents:
            if not parent.children:
                rows.append([req, parent.id, "", "", "", "", ""])
            for child in parent.children:
                if not child.steps:
                    rows.append([req, parent.id, child.id, "", "", "", ""])
                for step in child.steps:
                    rows.append(
                        [
                            req,
                            parent.id,
                            child.id,
                            step.id,
                            step.op or "",
                            step.target or "",
                            step.done_when or "",
                        ]
                    )
    return _csv(plan_label, rows)


def topological_order(plan: Plan) -> list[str]:
    """Kahn's algorithm, plan order as the tie-break; a cycle leaves its members at the end."""
    graph = depends_graph(plan)
    position = {p.id: i for i, p in enumerate(plan.parents)}
    remaining = {node: set(deps) for node, deps in graph.items()}
    order: list[str] = []
    while remaining:
        ready = sorted((n for n, deps in remaining.items() if not deps), key=position.__getitem__)
        if not ready:
            order.extend(sorted(remaining, key=position.__getitem__))
            break
        order.extend(ready)
        for node in ready:
            del remaining[node]
        for deps in remaining.values():
            deps.difference_update(ready)
    return order


def dag_yaml(plan: Plan, plan_label: str) -> str:
    graph = depends_graph(plan)
    nodes = [
        {
            "id": p.id,
            "title": p.title,
            "lane": p.lane,
            "item": p.item,
            "governed": bool(p.governed),
            "depends": list(graph[p.id]),
            "children": [c.id for c in p.children],
        }
        for p in plan.parents
    ]
    document: dict[str, Any] = {
        "authoritative_plan": plan_label,
        "artifact_role": HEADER_ROLE,
        "execution_authority": False,
        "nodes": nodes,
        "topological_order": topological_order(plan),
    }
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=10_000)


def dependency_matrix_csv(plan: Plan, plan_label: str) -> str:
    """Row depends on column: ``1`` direct, ``t`` transitive only, empty otherwise."""
    graph = depends_graph(plan)
    above = ancestors(graph)
    ids = [p.id for p in plan.parents]
    rows = [["card", *ids]]
    for row_id in ids:
        cells = []
        for col_id in ids:
            if col_id in graph[row_id]:
                cells.append("1")
            elif col_id in above[row_id]:
                cells.append("t")
            else:
                cells.append("")
        rows.append([row_id, *cells])
    return _csv(plan_label, rows)


def file_lock_csv(plan: Plan, plan_label: str) -> str:
    """Every write path with its owning card and the parallel cards it collides with."""
    clashes: dict[str, set[str]] = {p.id: set() for p in plan.parents}
    for left, right in parallel_pairs(plan):
        if left.lane and left.lane == right.lane:
            continue
        if write_conflicts(left, right):
            clashes[left.id].add(right.id)
            clashes[right.id].add(left.id)
    rows = [["path", "card", "lane", "item", "parallel_conflicts"]]
    position = {p.id: i for i, p in enumerate(plan.parents)}
    entries = [(path, p) for p in plan.parents for path in p.write]
    for path, owner in sorted(entries, key=lambda e: (e[0], position[e[1].id])):
        rows.append([path, owner.id, owner.lane, owner.item, ";".join(sorted(clashes[owner.id]))])
    return _csv(plan_label, rows)


def generate_maps(plan: Plan, plan_label: str) -> dict[str, str]:
    return {
        "requirement-traceability.csv": traceability_csv(plan, plan_label),
        "dag.yaml": dag_yaml(plan, plan_label),
        "dependency-matrix.csv": dependency_matrix_csv(plan, plan_label),
        "file-lock-map.csv": file_lock_csv(plan, plan_label),
    }


def write_maps(plan: Plan, plan_label: str, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, text in generate_maps(plan, plan_label).items():
        target = out_dir / name
        target.write_bytes(text.encode("utf-8"))  # exact bytes: LF endings on every platform
        written.append(target)
    return written
