"""The At a Glance diagram a README draws badly: stacked blocks, and labels a wider font clips.

Measured on the 32 live portfolio READMEs that carry the diagram (``components/readme_diagram``,
the one builder, and its investigation): all 32 are ``flowchart TD``, which stacks Starting
Points, Core Capabilities and Outputs in a column, and all 32 clip as soon as the browser draws the
labels in a wider font than the one that measured them. The correction is the same diagram - every
label, group title and edge unchanged - redrawn left to right with SVG text labels that grow with
their text. It is one multi-line edit to the lines between the fence markers; the README text
outside them is untouched.

Two things must hold before the detector may edit, and until they do it reports instead:

* the correction shape exists in this build (``model.DIAGRAM_FIX``: an edit that replaces a whole
  diagram body, which the one-line kinds cannot express); and
* the validator the correction is judged by accepts the redrawn diagram. BC-07 as it stands demands
  the old ``flowchart TD`` chain, so applying the edit today would make the whole bundle fail the
  "no check fails more often than on the live README" gate. The detector asks the running BC-07
  directly, so it starts editing in the same build that teaches BC-07 the horizontal contract
  (``readme_diagram.contract``) and never needs a flag flipped.

A diagram that is not the At a Glance chain, or already conforms, is not touched.
"""

from __future__ import annotations

from repository_presenter.components.readme.validation import registry as validation
from repository_presenter.components.readme_correction import model
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    Context,
    DetectorResult,
    Edit,
    Finding,
)
from repository_presenter.components.readme_diagram.lint import lint_parsed, normalize
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.components.readme_diagram.rebuild import mermaid_fences, rebuild_body

DETECTOR = "at_a_glance_diagram"


def _validator_accepts(body: str, has_inputs: bool) -> bool:
    """Whether the running BC-07 finds nothing wrong with ``body`` as an At a Glance diagram;
    false when its topology check cannot be asked (fail closed, never a guess)."""
    topology = getattr(validation, "_topology_failures", None)
    if topology is None:
        return False
    return not topology(body, has_inputs)


def _withheld(shape_exists: bool, accepted: bool) -> str:
    reasons = []
    if not shape_exists:
        reasons.append("this build has no correction kind that replaces a whole diagram body")
    if not accepted:
        reasons.append("the running BC-07 still requires the vertical `flowchart TD` drawing")
    return "; ".join(reasons)


@detector(DETECTOR)
def at_a_glance_diagram(ctx: Context) -> DetectorResult:
    """Redraw each defective At a Glance diagram, or report it while the edit is not yet allowed."""
    lines = ctx.readme.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    kind = getattr(model, "DIAGRAM_FIX", None)
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
        accepted = _validator_accepts(after, bool(parsed.glance.starting_points))
        if kind is None or not accepted:
            findings.append(
                Finding(
                    DETECTOR,
                    number,
                    fence.body.splitlines()[0] if fence.body else "",
                    f"the diagram is drawn with {codes}; the corrected drawing is withheld "
                    f"({_withheld(kind is not None, accepted)})",
                )
            )
            continue
        eol = "\r\n" if opener.endswith("\r\n") else "\n"
        edits.append(
            Edit(
                kind=kind,
                detector=DETECTOR,
                start=offsets[fence.first],
                end=offsets[fence.last],
                original=fence.body,
                replacement=after.replace("\n", eol),
                fact_ids=(),
                locators=(f"{ctx.readme_path}:{number}",),
                rationale=(
                    f"the At a Glance diagram on line {number} is drawn with {codes}; the same "
                    "labels, titles and chain are redrawn left to right with SVG text labels"
                ),
            )
        )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
