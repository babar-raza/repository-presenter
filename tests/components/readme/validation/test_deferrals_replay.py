"""Replay of the current sealed bundles under the combined TC-DSP-01 + deferral-class code.

PR #328 stopped a supersession standing unless its destination provably carries the unit, so the
reconciler's last attempt defers such a unit with a typed rationale. Without a class for that
cause BC-05 would report each one as UNCLASSIFIED BLOCK. This replays the 30 CURRENT bundles
through the reconciliation replay (reused, not re-implemented) and proves the new class turns
exactly those units advisory and changes nothing else.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator
from typing import Any

import pytest

from repository_presenter.components.readme.reconciliation.dispositions import (
    RECOVERED_COVERAGE_RATIONALE,
)
from repository_presenter.components.readme.validation import deferrals
from repository_presenter.components.readme.validation.deferrals import (
    DeferralFinding,
    review_deferrals,
)
from support import REPO_ROOT

_REPLAY = REPO_ROOT / "tests/components/readme/reconciliation/test_supersession_coverage.py"
_NEW_CLASS = "NOT_CARRIED_BY_NAMED_SECTION"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("supersession_coverage_replay", _REPLAY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # a dataclass resolves its own module by name
    spec.loader.exec_module(module)
    return module


_coverage = _load()
needs_candidates = pytest.mark.skipif(
    not _coverage._current_bundles(), reason="no sealed candidates"
)


def _judged() -> Iterator[tuple[str, dict[str, Any], Any, dict[str, Any] | None]]:
    """Each current bundle: its name, the dispositions its last attempt leaves, facts, plan."""
    for name, bundle in _coverage._current_bundles():
        row = _coverage.replay(name, bundle)
        plan_path = bundle / "plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.is_file() else None
        yield name, row.final, row.facts, plan


def _prefixed(document: dict[str, Any]) -> set[str]:
    return {
        str(entry["unit_id"])
        for entry in document["dispositions"]
        if entry["disposition"] == "DEFER_UNRESOLVED"
        and str(entry.get("rationale") or "").startswith(RECOVERED_COVERAGE_RATIONALE.rstrip())
    }


def _blocks(findings: list[DeferralFinding]) -> set[tuple[str, str]]:
    return {(f.unit_id, f.class_id) for f in findings if f.decision == "BLOCK"}


@needs_candidates
def test_replay_only_the_typed_deferrals_turn_advisory_and_nothing_else_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    carried = 0
    repositories = 0
    for name, document, facts, plan in _judged():
        with_class = review_deferrals(document, facts, plan)
        monkeypatch.setattr(
            deferrals,
            "DEFERRAL_CLASSES",
            tuple(c for c in deferrals.DEFERRAL_CLASSES if c.id != _NEW_CLASS),
        )
        without_class = review_deferrals(document, facts, plan)
        monkeypatch.undo()

        # Every unit keeps its finding except the ones the new class takes from UNCLASSIFIED.
        assert [f.unit_id for f in with_class] == [f.unit_id for f in without_class], name
        changed = {f.unit_id for f, g in zip(with_class, without_class, strict=True) if f != g}
        taken = {f.unit_id for f in with_class if f.class_id == _NEW_CLASS}
        assert changed == taken, name
        assert all(
            g.class_id == "UNCLASSIFIED" and g.decision == "BLOCK"
            for f, g in zip(with_class, without_class, strict=True)
            if f.unit_id in taken
        ), name
        # Every BLOCK that is not the unclassified fallback is untouched.
        assert {b for b in _blocks(with_class) if b[1] != "UNCLASSIFIED"} == {
            b for b in _blocks(without_class) if b[1] != "UNCLASSIFIED"
        }, name
        # No unit carrying the typed deferral is left UNCLASSIFIED.
        assert not {u for u, c in _blocks(with_class) if c == "UNCLASSIFIED"} & _prefixed(
            document
        ), name
        carried += len(taken)
        repositories += bool(taken)
    assert carried > 0 and repositories > 0
