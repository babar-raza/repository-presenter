"""Find what is wrong with an At a Glance diagram's drawing, without drawing it.

Two defect families were measured on the 32 live READMEs (every one had both):

* **Orientation.** ``flowchart TD`` stacks Starting Points, Core Capabilities and Outputs in a
  column; and a ``direction`` line inside a group does what its author did not mean (``TB`` over
  unlinked nodes is a *row*, ``LR`` a *column*), so the capability "columns" lay out as rows.
* **Clipping.** Mermaid's default HTML labels are fixed-size ``foreignObject`` boxes sized from the
  font the label was measured in; drawn in any wider font they cut the text off. A label longer
  than Mermaid's own wrap width is also re-wrapped at render time from that same measurement.

The checks here are the deterministic model of those defects (the width table of ``geometry.py``
and the structure ``parse.py`` reads); ``render_check.py`` measures the same things in a real
browser. A diagram is *conforming* exactly when it equals what ``build.py`` writes for its meaning.
"""

from __future__ import annotations

from repository_presenter.components.readme_diagram.build import build_body
from repository_presenter.components.readme_diagram.geometry import (
    MERMAID_AUTO_WRAP_PX,
    text_px,
)
from repository_presenter.components.readme_diagram.model import (
    Defect,
    LintReport,
    NotAGlanceError,
)
from repository_presenter.components.readme_diagram.parse import (
    BREAK_TAG,
    Parsed,
    clean_label,
    parse,
)

ORIENTATION_VERTICAL = "ORIENTATION_VERTICAL"
CLIP_HTML_LABELS = "CLIP_HTML_LABELS"
CLIP_AUTO_WRAP = "CLIP_AUTO_WRAP"
LABEL_TOKEN_WIDE = "LABEL_TOKEN_WIDE"
LABEL_MARKUP_LOST = "LABEL_MARKUP_LOST"
LABEL_ENTITY_RISK = "LABEL_ENTITY_RISK"
GROUP_LAID_AS_ROW = "GROUP_LAID_AS_ROW"
ORDER_UNPINNED = "ORDER_UNPINNED"
COLUMN_ORDER = "COLUMN_ORDER"
NOT_CANONICAL = "NOT_CANONICAL"
UNRECOGNIZED = "UNRECOGNIZED"


def normalize(body: str) -> str:
    """``body`` with trailing whitespace and blank lines removed, ending in one newline."""
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def _flowchart_config(parsed: Parsed) -> dict[str, object]:
    flowchart = parsed.init.get("flowchart")
    return flowchart if isinstance(flowchart, dict) else {}


def _html_labels_on(parsed: Parsed) -> bool:
    flowchart = _flowchart_config(parsed)
    return not (parsed.init.get("htmlLabels") is False and flowchart.get("htmlLabels") is False)


def _wrap_width(parsed: Parsed) -> float:
    value = _flowchart_config(parsed).get("wrappingWidth")
    return float(value) if isinstance(value, int | float) else float(MERMAID_AUTO_WRAP_PX)


def _label_defects(parsed: Parsed) -> tuple[list[Defect], list[Defect]]:
    """``(defects, advisories)`` of the label texts: a line the renderer will re-wrap, and markup
    it will drop are defects; one word wider than the wrap width is advisory (a rewrite cannot
    split a word, and the box simply grows to it)."""
    wrap_px = _wrap_width(parsed)
    defects: list[Defect] = []
    advisories: list[Defect] = []
    for ident, raw in parsed.raw_labels.items():
        for line in (clean_label(part) for part in BREAK_TAG.split(raw)):
            width = text_px(line)
            if width <= wrap_px:
                continue
            if len(line.split()) == 1:
                advisories.append(
                    Defect(LABEL_TOKEN_WIDE, f"{ident}: one unbroken word of {width:.0f}px")
                )
            else:
                defects.append(
                    Defect(
                        CLIP_AUTO_WRAP,
                        f"{ident}: a line of {width:.0f}px against a {wrap_px:.0f}px wrap width, "
                        "so the renderer re-wraps it from its own measurement",
                    )
                )
        written = BREAK_TAG.sub(" ", raw)
        if "<" in written or ">" in written:
            defects.append(
                Defect(
                    LABEL_MARKUP_LOST,
                    f"{ident}: a raw < or > that Mermaid reads as an HTML tag and drops "
                    f"({written[:60]!r})",
                )
            )
    return defects, advisories


def entity_risks(parsed: Parsed) -> list[Defect]:
    """Labels whose ``&``, ``<`` or ``>`` draw as entity text on Mermaid before 11.14 (advisory:
    the characters are the label's own, so a rewrite keeps them)."""
    texts = [*parsed.glance.labels, *parsed.glance.titles]
    return [
        Defect(LABEL_ENTITY_RISK, f"{text[:60]!r} holds & < or >")
        for text in texts
        if any(char in text for char in "&<>")
    ]


def _group_sizes(parsed: Parsed) -> dict[str, int]:
    glance = parsed.glance
    sizes = {"StartingPoints": len(glance.starting_points), "Outputs": len(glance.outputs)}
    columns = glance.capability_columns
    if len(columns) == 1:
        sizes["Capabilities"] = len(columns[0])
    else:
        sizes["capl"] = len(columns[0])
        sizes["capr"] = len(columns[1])
    return sizes


def _group_defects(parsed: Parsed) -> list[Defect]:
    defects: list[Defect] = []
    for group, size in _group_sizes(parsed).items():
        if size < 2 or group in parsed.pinned:
            continue
        direction = parsed.group_direction.get(group)
        if direction in {"TB", "TD"}:
            defects.append(
                Defect(
                    GROUP_LAID_AS_ROW,
                    f"{group} is `direction {direction}` over {size} unlinked nodes: a row",
                )
            )
        defects.append(Defect(ORDER_UNPINNED, f"{group}: {size} nodes whose order no edge pins"))
    if parsed.declared_columns == ("capl", "capr"):
        defects.append(
            Defect(
                COLUMN_ORDER,
                "capl is declared before capr: Mermaid draws sibling clusters in reverse "
                "declaration order, so the first half of the capabilities lands on the right",
            )
        )
    return defects


def first_difference(actual: str, expected: str) -> str:
    for number, (got, want) in enumerate(
        zip(actual.splitlines(), expected.splitlines(), strict=False), start=1
    ):
        if got != want:
            return f"line {number}: {got!r} != {want!r}"
    return "the line counts differ"


def lint_parsed(parsed: Parsed, body: str) -> LintReport:
    """Every defect of an already-parsed diagram; ``body`` is the source it came from."""
    defects: list[Defect] = []
    if parsed.root_direction in {"TD", "TB", "BT"}:
        defects.append(
            Defect(
                ORIENTATION_VERTICAL,
                f"`flowchart {parsed.root_direction}` stacks Starting Points, Core Capabilities "
                "and Outputs top to bottom",
            )
        )
    if _html_labels_on(parsed):
        defects.append(
            Defect(
                CLIP_HTML_LABELS,
                "HTML labels are fixed-size boxes measured in one font; a wider font clips them",
            )
        )
    label_defects, advisories = _label_defects(parsed)
    defects += label_defects
    defects += _group_defects(parsed)
    if not defects:
        expected = build_body(parsed.glance)
        actual = normalize(body)
        if actual != expected:
            defects.append(Defect(NOT_CANONICAL, first_difference(actual, expected)))
    return LintReport(True, tuple(defects), tuple(advisories + entity_risks(parsed)))


def lint_source(body: str) -> LintReport:
    """The verdict on one Mermaid source (without its fence)."""
    try:
        parsed = parse(body)
    except NotAGlanceError as error:
        return LintReport(False, (Defect(UNRECOGNIZED, str(error)),))
    return lint_parsed(parsed, body)
