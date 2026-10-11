"""Keep only the edits that leave every validation check no worse than the live README had it.

``correct`` proposes every edit the detectors find; some can still tip a check the live README was
sitting on (a README at the 300-visible-line budget gains two lines; a badge row gains a badge out
of its stable order). Refusing the whole correction for that would withhold the edits that are
fine, so each droppable group of edits - a section with its contents item, or a single edit - is
judged alone against the live README with only its structure fixes applied, the ones that fail are
dropped and reported with the check and its detail, and what remains is judged again together
until nothing it does introduces a failure. Structure fixes are the baseline and are never dropped
(``check.validation_delta``). The result is a pure function of the inputs, so the gate re-derives
it byte for byte.
"""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import assemble, collect
from repository_presenter.components.readme_correction.model import (
    STRUCTURE_FIX,
    Context,
    CorrectionResult,
    Edit,
    Finding,
)


def _group(edit: Edit) -> tuple[Any, ...]:
    """The unit a validation failure drops: a section and its contents item go together."""
    if edit.detector == "missing_sections":
        return ("missing_sections", edit.order)
    return (edit.detector, edit.start, edit.end)


def _reason(introduced: list[dict[str, Any]]) -> str:
    parts = [
        f"{item['check']}: {item['details'][0][:110]}" for item in introduced if item["details"]
    ]
    return (
        "would make a validation check fail that the live README passes (" + "; ".join(parts) + ")"
    )


def correct_settled(ctx: Context, original: bytes) -> tuple[CorrectionResult, dict[str, Any]]:
    """``(result, validation delta)`` with the offending edit groups dropped and reported."""
    edits, findings = collect(ctx)
    result = assemble(ctx, edits, findings)
    delta = validation_delta(ctx, result, original)
    while delta["introduced"]:
        fixed = [e for e in result.edits if e.kind == STRUCTURE_FIX]
        groups: dict[tuple[Any, ...], list[Edit]] = {}
        for edit in result.edits:
            if edit.kind != STRUCTURE_FIX:
                groups.setdefault(_group(edit), []).append(edit)
        bad: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for key, members in groups.items():
            solo = assemble(ctx, fixed + members, [])
            introduced = validation_delta(ctx, solo, original)["introduced"]
            if introduced:
                bad[key] = introduced
        if not bad:  # each group is fine alone but not together: drop the last one in order
            last = max(groups, key=lambda k: min(e.start for e in groups[k]))
            bad[last] = delta["introduced"]
        for key, introduced in bad.items():
            first = groups[key][0]
            line = ctx.readme.count(chr(10), 0, first.start) + 1
            findings.append(Finding(first.detector, line, "", _reason(introduced), first.fact_ids))
        kept = [e for e in result.edits if _group(e) not in bad]
        result = assemble(ctx, kept, findings)
        delta = validation_delta(ctx, result, original)
    return result, delta
