"""Routing and invalidation read fields, never prose (RESEARCH_AND_GUIDELINES.md 27.2 RC8, 27.5 D5).

The legacy shape, measured on this system's own artifacts: the causal stage was recovered by regex
from a bracketed prefix inside a finding's text, the target section by regex from the first of a
check's detail strings, and invalidation keyed on ``details[0]``. Each made a sentence a control
plane, so rewording a message changed where a defect was routed or whether a sealed candidate was
invalidated.

Two shapes produce that, and this module rejects both in the modules that route defects, judge
findings, and invalidate bundles: a regular expression applied to a record's prose - directly or
through a local name assigned from it - and an indexed read of a record's ``details`` list inside a
decision. Prose still travels: a record carries its detail strings for a reader, a repair packet
shows them to the model, and quote location matches the reviewer's quote against the candidate's
own text. What may not happen is a decision taken by reading them.
"""

from __future__ import annotations

import ast

from support import REPO_ROOT

SOURCE_ROOT = REPO_ROOT / "src/repository_presenter"
# The modules that decide where a defect goes, whether a finding blocks, and whether a failure
# invalidates an accepted candidate.
HELD = (
    "components/readme/repair/targeted.py",
    "components/readme/repair/rounds.py",
    "components/readme/bundle/seal.py",
    "components/readme/bundle/evaluation.py",
    "components/readme/review/independent/review.py",
)
# The keys of a failure or finding record that carry prose a person wrote or a model wrote.
PROSE_KEYS = frozenset({"text", "detail", "details", "rationale"})
REGEX_CALLS = frozenset({"match", "search", "fullmatch", "findall", "finditer", "sub", "split"})


def _prose_keys(node: ast.AST) -> set[str]:
    """The prose keys this expression reads, whether by ``x["details"]`` or ``x.get("details")``."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and child.value in PROSE_KEYS:
            found.add(str(child.value))
    return found


def _regex_target(call: ast.Call) -> ast.AST | None:
    """The expression a regular-expression call is applied to, or None when it is not one."""
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr in REGEX_CALLS:
        if isinstance(func.value, ast.Name) and func.value.id == "re":
            return call.args[1] if len(call.args) > 1 else None
        return call.args[0] if call.args else None
    return None


def prose_decisions(source: str) -> list[str]:
    """Every place this module lets prose decide: regex over a record's prose, or ``details[i]``."""
    tree = ast.parse(source)
    offences: list[str] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        # Local names assigned from a prose key are the same value under another name.
        tainted: set[str] = set()
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and _prose_keys(node.value):
                tainted.update(target.id for target in node.targets if isinstance(target, ast.Name))
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                target = _regex_target(node)
                if target is not None and (
                    _prose_keys(target)
                    or any(
                        isinstance(child, ast.Name) and child.id in tainted
                        for child in ast.walk(target)
                    )
                ):
                    offences.append(
                        f"{function.name}:{node.lineno}: a regular expression decides from prose"
                    )
            indexed = (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, int)
            )
            if indexed and (
                _prose_keys(node.value)
                or (isinstance(node.value, ast.Name) and node.value.id in tainted)
            ):
                offences.append(
                    f"{function.name}:{node.lineno}: a decision indexes a record's prose"
                )
    return offences


def test_no_routing_or_invalidation_module_decides_from_prose() -> None:
    offences = {
        path: prose_decisions((SOURCE_ROOT / path).read_text("utf-8"))
        for path in HELD
        if prose_decisions((SOURCE_ROOT / path).read_text("utf-8"))
    }
    assert offences == {}


def test_the_two_retired_shapes_are_flagged() -> None:
    # The causal stage recovered by regex from a bracketed prefix in the finding's text.
    marked = (
        "import re\n"
        "_MARK = re.compile(r'^\\[at (\\S+)\\] ')\n"
        "def route(finding):\n"
        "    text = str(finding.get('text', ''))\n"
        "    found = _MARK.match(text)\n"
        "    return found.group(1) if found else None\n"
    )
    assert prose_decisions(marked) == ["route:5: a regular expression decides from prose"]
    # The target section recovered by regex from the first detail string.
    detailed = (
        "import re\n"
        "_SECTION = re.compile(r'^([a-z_]+):')\n"
        "def route(check):\n"
        "    return _SECTION.match(str(check['details'][0]))\n"
    )
    assert prose_decisions(detailed) == [
        "route:4: a regular expression decides from prose",
        "route:4: a decision indexes a record's prose",
    ]
    # Invalidation keyed on details[0], with or without a regex.
    keyed = "def invalidates(check):\n    return check.get('details')[0] == 'REJECT_FACTUAL'\n"
    assert prose_decisions(keyed) == ["invalidates:2: a decision indexes a record's prose"]
    # A record that carries its prose for a reader is untouched by the rule.
    carried = (
        "def record(check):\n"
        "    return {'id': check['id'], 'details': list(check.get('details', []))}\n"
    )
    assert prose_decisions(carried) == []
