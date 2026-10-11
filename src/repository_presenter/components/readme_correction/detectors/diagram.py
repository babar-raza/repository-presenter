"""The At a Glance diagram a README draws badly: stacked blocks, and labels a wider font clips.

Measured on the 32 live portfolio READMEs that carry the diagram (``components/readme_diagram``,
the one builder, and its investigation): all 32 are ``flowchart TD``, which stacks Starting
Points, Core Capabilities and Outputs in a column, and all 32 clip as soon as the browser draws the
labels in a wider font than the one that measured them. The correction is the same diagram - every
label, group title and edge unchanged - redrawn left to right with SVG text labels that grow with
their text. It is one multi-line edit to the lines between the fence markers; the README text
outside them is untouched.

The edit is a ``DIAGRAM_FIX``: an edit that replaces a whole diagram body, which the one-line kinds
cannot express. The detector edits only when the horizontal At a Glance contract
(``readme_diagram.contract``) finds nothing wrong with the redrawn body that it did not already find
in the live one (``_introduced``), and reports otherwise.

BC-07 now judges the diagram by the same contract (the governed adoption of owner ruling R7), so
the redrawn body adds no At a Glance failure of its own. What it can still add is lines: the init
line and the invisible column links make it a few lines longer, which can tip BC-07's visible-length
budget a README sat just under. Owner ruling OD-06 lets visible length grow to add a required
element and R7 requires the horizontal drawing, so the typed ``check.ALLOWANCES`` entry covers
exactly that failure for this edit kind (recorded under ``allowed`` in ``validation_delta.json``,
never ``introduced``) and bounds it: any other edit that lengthens the README further is still
introduced.

A diagram that is not the At a Glance chain, or already conforms, is not touched.
"""

from __future__ import annotations

from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    DIAGRAM_FIX,
    Context,
    DetectorResult,
    Edit,
    Finding,
)
from repository_presenter.components.readme_diagram import contract
from repository_presenter.components.readme_diagram.lint import lint_parsed, normalize
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.components.readme_diagram.rebuild import mermaid_fences, rebuild_body

DETECTOR = "at_a_glance_diagram"


def _introduced(live: str, after: str, has_inputs: bool) -> list[str]:
    """The contract failures the redrawn ``after`` has that the live body ``live`` did not.

    ``readme_diagram.contract`` is the rule BC-07's topology check is being migrated to (owner
    ruling R7). Judged the way every correction is judged - no worse than the live README - the
    drawing must leave it nothing new to say: the contract's composing failures (not the horizontal
    drawing of its own content, unbalanced columns) are all repaired by the rebuild, while the
    content ceilings it also holds (at most eight capabilities, a label of at most four lines, no
    word wider than the line budget) police what a model may author at planning, and the labels
    here are the maintainers' own, kept as they wrote them, so what the live diagram already
    exceeded it still exceeds and is not new. Whether such a label draws clear is settled by the
    real render (``readme_diagram.render_check``), not by this deterministic gate."""
    known = {failure.message for failure in contract.topology_failures(live, has_inputs)}
    return [
        failure.message
        for failure in contract.topology_failures(after, has_inputs)
        if failure.message not in known
    ]


def _kept_ceilings(live: str, after: str, has_inputs: bool) -> int:
    known = {failure.message for failure in contract.topology_failures(live, has_inputs)}
    return sum(
        1 for failure in contract.topology_failures(after, has_inputs) if failure.message in known
    )


@detector(DETECTOR)
def at_a_glance_diagram(ctx: Context) -> DetectorResult:
    """Redraw each defective At a Glance diagram, or report it while the edit is not yet allowed."""
    lines = ctx.readme.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[Edit] = []
    findings: list[Finding] = []
    for fence in mermaid_fences(lines):
        opener = lines[fence.first - 1]
        if opener[0] in " \t":
            continue
        try:
            parsed = parse(fence.body)
        except NotAGlanceError:
            continue  # another kind of diagram: not ours to redraw
        report = lint_parsed(parsed, fence.body)
        after = rebuild_body(fence.body)
        if report.conforming or normalize(fence.body) == after:
            continue
        number = fence.first + 1
        codes = ", ".join(sorted(report.codes))
        has_inputs = bool(parsed.glance.starting_points)
        worse = _introduced(fence.body, after, has_inputs)
        if worse:
            findings.append(
                Finding(
                    DETECTOR,
                    number,
                    fence.body.splitlines()[0] if fence.body else "",
                    f"the diagram is drawn with {codes}; the corrected drawing is withheld "
                    f"(the horizontal At a Glance contract would fail it anew: {worse[0][:110]})",
                )
            )
            continue
        kept = _kept_ceilings(fence.body, after, has_inputs)
        note = (
            f"; its content already exceeded {kept} regeneration ceiling(s) and is kept as the "
            "maintainers wrote it"
            if kept
            else ""
        )
        eol = "\r\n" if opener.endswith("\r\n") else "\n"
        edits.append(
            Edit(
                kind=DIAGRAM_FIX,
                detector=DETECTOR,
                start=offsets[fence.first],
                end=offsets[fence.last],
                original=fence.body,
                replacement=after.replace("\n", eol),
                fact_ids=(),
                locators=(f"{ctx.readme_path}:{number}",),
                rationale=(
                    f"the At a Glance diagram on line {number} is drawn with {codes}; the same "
                    f"labels, titles and chain are redrawn left to right with SVG text labels{note}"
                ),
            )
        )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
