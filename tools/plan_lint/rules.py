"""Static plan rules of section 6 (card TC-LNT-01-02): one function per rule, one finding code each.

Every rule is a pure function ``Plan -> list[Finding]``; ``lint_plan`` runs them all. Rule codes are
stable (tests and the ledger tooling refer to them).
"""

from __future__ import annotations

from collections.abc import Callable

from .cards import CHILD_ID, ITEM_ID, OPS, PARENT_ID, REQ_ID, Parent, Plan
from .findings import Finding

# The four governed sources (tests/test_version_bump_discipline.py GOVERNED holds the live list;
# tests/test_plan_lint.py proves the two agree). A card whose write set reaches one is governed.
GOVERNED_FILES: tuple[str, ...] = (
    "src/repository_presenter/components/readme/composition/renderer.py",
    "src/repository_presenter/components/readme/composition/authoring.py",
    "src/repository_presenter/components/readme/review/independent/review.py",
    "src/repository_presenter/components/readme/validation/registry.py",
)


def _segments(path: str) -> tuple[str, ...]:
    return tuple(part for part in path.replace("\\", "/").split("/") if part and part != ".")


def paths_overlap(a: str, b: str) -> bool:
    """True when one path equals or is a directory prefix of the other (segment-wise)."""
    left, right = _segments(a), _segments(b)
    shorter = min(len(left), len(right))
    return shorter > 0 and left[:shorter] == right[:shorter]


def _path_within(path: str, parent: str) -> bool:
    inner, outer = _segments(path), _segments(parent)
    return len(inner) >= len(outer) > 0 and inner[: len(outer)] == outer


def _all_ids(plan: Plan) -> list[tuple[str, str]]:
    ids = [(p.id, "parent") for p in plan.parents]
    ids += [(c.id, "child") for p in plan.parents for c in p.children]
    return ids


def rule_parse(plan: Plan) -> list[Finding]:
    return [Finding("PARSE", "plan", problem) for problem in plan.problems]


def rule_id_format(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    for parent in plan.parents:
        if not PARENT_ID.match(parent.id):
            found.append(Finding("ID_FORMAT", parent.id or "?", "parent id must be TC-<AREA>-NN"))
        for child in parent.children:
            if CHILD_ID.match(child.id) is None:
                found.append(
                    Finding("ID_FORMAT", child.id or "?", "child id must be TC-<AREA>-NN-CC")
                )
            elif child.id.rsplit("-", 1)[0] != parent.id:
                found.append(Finding("ID_FORMAT", child.id, f"child is not under {parent.id}"))
        if not parent.item:
            found.append(Finding("ITEM_FORMAT", parent.id, "card names no registered `item:`"))
        elif not ITEM_ID.match(parent.item):
            found.append(
                Finding("ITEM_FORMAT", parent.id, f"item {parent.item!r} is not G<gate>-W<nn>")
            )
    return found


def rule_unique_ids(plan: Plan) -> list[Finding]:
    seen: set[str] = set()
    found: list[Finding] = []
    for card_id, kind in _all_ids(plan):
        if card_id in seen:
            found.append(Finding("ID_DUPLICATE", card_id, f"duplicate {kind} id"))
        seen.add(card_id)
    return found


def rule_requirements(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    if not plan.has_requirements_section:
        return [Finding("REQ_UNDEFINED", "plan", "plan has no Requirements section")]
    referenced: set[str] = set()
    for parent in plan.parents:
        if not parent.reqs:
            found.append(Finding("PARENT_NO_REQ", parent.id, "parent names no REQ"))
        for req in parent.reqs:
            referenced.add(req)
            if not REQ_ID.match(req) or req not in plan.defined_reqs:
                found.append(
                    Finding("REQ_UNDEFINED", parent.id, f"{req} is not defined in Requirements")
                )
    for req in sorted(plan.defined_reqs - referenced):
        found.append(Finding("REQ_UNREFERENCED", req, "requirement has no parent card"))
    return found


def rule_shape(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    for parent in plan.parents:
        if not parent.children:
            found.append(Finding("PARENT_NO_CHILD", parent.id, "parent has no child"))
        for child in parent.children:
            if not child.steps:
                found.append(Finding("CHILD_NO_STEP", child.id, "child has no micro-step"))
            for step in child.steps:
                if step.op is None:
                    found.append(
                        Finding(
                            "STEP_FORMAT",
                            step.id,
                            f"step must be 'op | target | done-when', got {step.raw!r}",
                        )
                    )
                elif step.op not in OPS:
                    found.append(
                        Finding("STEP_OP", step.id, f"unknown op {step.op!r} (known: {OPS})")
                    )
            if child.kind == "investigation" and not child.produces:
                found.append(
                    Finding(
                        "INVESTIGATION_NO_PRODUCES",
                        child.id,
                        "an investigation child names the cards it will produce (`produces:`)",
                    )
                )
    return found


def _resolve(plan: Plan, ref: str) -> str | None:
    owner = plan.parent_of(ref)
    return owner.id if owner is not None else None


def depends_graph(plan: Plan) -> dict[str, list[str]]:
    """Parent -> parents it depends on (a child reference resolves to its owning parent)."""
    graph: dict[str, list[str]] = {}
    for parent in plan.parents:
        resolved = [_resolve(plan, ref) for ref in parent.depends]
        graph[parent.id] = [r for r in resolved if r is not None and r != parent.id]
    return graph


def rule_depends(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    for parent in plan.parents:
        for ref in parent.depends:
            owner = _resolve(plan, ref)
            if owner is None:
                found.append(Finding("DEPEND_UNKNOWN", parent.id, f"depends on unknown {ref}"))
            elif owner == parent.id:
                found.append(Finding("DEPEND_CYCLE", parent.id, f"depends on its own {ref}"))
    return found


def find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """A dependency cycle as a path of IDs, or None when the graph is a DAG."""
    state: dict[str, int] = {}  # 1 = on the stack, 2 = done
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if state.get(nxt) == 1:
                return [*stack[stack.index(nxt) :], nxt]
            if nxt not in state:
                cycle = visit(nxt)
                if cycle is not None:
                    return cycle
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if node not in state:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None


def rule_acyclic(plan: Plan) -> list[Finding]:
    cycle = find_cycle(depends_graph(plan))
    if cycle is None:
        return []
    return [Finding("DEPEND_CYCLE", cycle[0], "dependency cycle: " + " -> ".join(cycle))]


def ancestors(graph: dict[str, list[str]]) -> dict[str, set[str]]:
    """Transitive dependencies of every node (cycle-safe: a cycle just stops expanding)."""
    result: dict[str, set[str]] = {}
    for node in graph:
        seen: set[str] = set()
        todo = list(graph[node])
        while todo:
            current = todo.pop()
            if current in seen:
                continue
            seen.add(current)
            todo.extend(graph.get(current, []))
        result[node] = seen
    return result


def parallel_pairs(plan: Plan) -> list[tuple[Parent, Parent]]:
    """Parent pairs with no dependency path between them (they may run at the same time)."""
    above = ancestors(depends_graph(plan))
    pairs: list[tuple[Parent, Parent]] = []
    for i, left in enumerate(plan.parents):
        for right in plan.parents[i + 1 :]:
            if right.id not in above.get(left.id, set()) and left.id not in above.get(
                right.id, set()
            ):
                pairs.append((left, right))
    return pairs


def write_conflicts(left: Parent, right: Parent) -> list[tuple[str, str]]:
    return [(a, b) for a in left.write for b in right.write if paths_overlap(a, b)]


def rule_paths(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    for parent in plan.parents:
        if not parent.write:
            found.append(Finding("PATHS_NO_WRITE", parent.id, "card declares no `paths.write`"))
        for allowed in parent.write:
            for forbidden in parent.forbidden:
                if paths_overlap(allowed, forbidden):
                    found.append(
                        Finding(
                            "PATHS_ALLOWED_FORBIDDEN",
                            parent.id,
                            f"allowed {allowed!r} overlaps forbidden {forbidden!r}",
                        )
                    )
        for child in parent.children:
            for path in child.write or []:
                if not any(_path_within(path, allowed) for allowed in parent.write):
                    found.append(
                        Finding(
                            "PATHS_OUTSIDE_PARENT",
                            child.id,
                            f"child writes {path!r} outside its parent's allowed set",
                        )
                    )
    return found


def rule_parallel_writes(plan: Plan) -> list[Finding]:
    """Two cards that may run in parallel must not share a write prefix.

    Cards of one lane never run at the same time (a lane is one agent working one card), so a
    same-lane pair is serialised by the lane and is not a conflict. A plan's header may also name
    `serialised_paths:` (hot files only the supervisor writes, one at a time); an overlap wholly
    inside one of them is waived.
    """
    found: list[Finding] = []
    for left, right in parallel_pairs(plan):
        if left.lane and left.lane == right.lane:
            continue
        for a, b in write_conflicts(left, right):
            if any(_path_within(a, w) and _path_within(b, w) for w in plan.serialised_paths):
                continue  # a hot file the supervisor serialises (header `serialised_paths:`)
            found.append(
                Finding(
                    "PARALLEL_WRITE_CONFLICT",
                    f"{left.id}|{right.id}",
                    f"parallel cards share a write path ({a} ~ {b}); add a dependency or "
                    "split the paths",
                )
            )
    return found


def rule_governed(plan: Plan) -> list[Finding]:
    found: list[Finding] = []
    for parent in plan.parents:
        if parent.governed is None:
            found.append(
                Finding("GOVERNED_UNDECLARED", parent.id, "`governed:` must be true/false")
            )
        if parent.governed and not (parent.ground and parent.ground.strip()):
            found.append(
                Finding(
                    "GOVERNED_NO_GROUND",
                    parent.id,
                    "governed: true requires a `ground:` (G7-W22 safety/factual-accuracy ground "
                    "or the owner approval record)",
                )
            )
        touches = [g for g in GOVERNED_FILES for w in parent.write if paths_overlap(g, w)]
        if touches and parent.governed is not True:
            found.append(
                Finding(
                    "GOVERNED_UNDECLARED",
                    parent.id,
                    f"card writes governed source {touches[0]} but does not declare governed: true",
                )
            )
    return found


Rule = Callable[[Plan], list[Finding]]

RULES: tuple[Rule, ...] = (
    rule_parse,
    rule_id_format,
    rule_unique_ids,
    rule_requirements,
    rule_shape,
    rule_depends,
    rule_acyclic,
    rule_paths,
    rule_parallel_writes,
    rule_governed,
)


def lint_plan(plan: Plan) -> list[Finding]:
    findings: list[Finding] = []
    for rule in RULES:
        findings.extend(rule(plan))
    return findings
