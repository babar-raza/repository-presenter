"""The correction engine: run every registered detector, apply what survives, prove confinement.

Pure and deterministic: the same README, facts and tree always give the same bytes, with no
provider call anywhere on the path, so the zero-call no-op proof is a re-run and a byte comparison
(``is_stable``) rather than a ledger.
"""

from __future__ import annotations

from repository_presenter.components.readme_correction.apply import (
    apply_edits,
    confinement_violations,
    order_edits,
)
from repository_presenter.components.readme_correction.detectors import load_detectors
from repository_presenter.components.readme_correction.model import (
    Context,
    CorrectionResult,
    Edit,
    Finding,
)
from repository_presenter.components.readme_correction.text_gate import narration
from repository_presenter.core.errors import PresenterError


class CorrectionError(PresenterError):
    """The engine could not honestly correct this README (a violated invariant, never a skip)."""


def _without_narration(ctx: Context, edits: list[Edit], findings: list[Finding]) -> list[Edit]:
    """Drop every edit whose inserted text carries internal-assurance narration, with the
    contents-list item that points at a dropped section; the reason is reported."""
    bad = {id(edit): narration(edit.replacement) for edit in edits if narration(edit.replacement)}
    pairs = {
        (e.detector, e.order) for e in edits if id(e) in bad and e.detector == "missing_sections"
    }
    kept: list[Edit] = []
    for edit in edits:
        if id(edit) in bad or (edit.detector, edit.order) in pairs:
            hits = bad.get(id(edit)) or ["its section was dropped"]
            line = ctx.readme.count("\n", 0, edit.start) + 1
            findings.append(
                Finding(
                    edit.detector,
                    line,
                    "",
                    f"the text to insert carries internal narration ({', '.join(hits)}); "
                    "not applied",
                    edit.fact_ids,
                )
            )
        else:
            kept.append(edit)
    return kept


def correct(ctx: Context) -> CorrectionResult:
    edits: list[Edit] = []
    findings: list[Finding] = []
    for result in (detector(ctx) for detector in load_detectors().values()):
        edits.extend(result.edits)
        findings.extend(result.findings)
    edits = _without_narration(ctx, edits, findings)
    kept, dropped = order_edits(edits)
    for edit in dropped:
        line = ctx.readme.count("\n", 0, edit.start) + 1
        findings.append(
            Finding(edit.detector, line, edit.original, "overlaps another correction; not applied")
        )
    corrected, spans = apply_edits(ctx.readme, kept)
    problems = confinement_violations(ctx.readme, corrected, kept, spans)
    if problems:
        raise CorrectionError("correction is not confined to its edits: " + "; ".join(problems))
    return CorrectionResult(
        original=ctx.readme,
        corrected=corrected,
        edits=kept,
        output_spans=spans,
        findings=sorted(findings, key=lambda f: (f.line, f.detector, f.reason)),
    )


def is_stable(ctx: Context, result: CorrectionResult) -> tuple[bool, bool]:
    """``(deterministic, idempotent)``: a second run over the same inputs is byte-identical, and a
    run over the corrected text finds nothing further to correct."""
    again = correct(ctx)
    deterministic = again.corrected == result.corrected and again.edits == result.edits
    after = Context(ctx.entry, ctx.facts, result.corrected, ctx.tree_paths, ctx.readme_path)
    return deterministic, not correct(after).edits
