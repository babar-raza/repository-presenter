"""The At a Glance component: the diagram, and the label geometry every stage judges it by.

``docs/README_CONTRACT.md`` section 2.1 and ``docs/README_STANDARD.md`` STR-28 (owner ruling R7,
OD-10): the diagram is drawn left to right, split by key capability, with every box grown to its
text and no label clipped; "a longer title is shortened at planning, never clipped at render".

The drawing, the width model and the contract live once, in ``components/readme_diagram``, because
the live-first correction path draws the same diagram; this module is the composition package's one
door onto it, so the renderer (which writes the diagram), planning (which shortens a title that
cannot fit) and BC-07 (which judges the result) all read the same policy:

* a label is wrapped into ``<br/>`` lines by one character-width model (the envelope of five
  measured fonts), inside one pixel budget per diagram (one capability column or two);
* no label wraps past :data:`GLANCE_MAX_LINES` lines and no word is wider than the budget;
* the labels are drawn as SVG text in a box sized from the text, so a font wider than the one that
  measured them cannot clip them (``readme_diagram/build.py`` records why, and
  ``readme_diagram/render_check.py`` proves it in a real browser).
"""

from __future__ import annotations

from collections.abc import Sequence

from repository_presenter.components.readme_diagram import Glance, balanced_columns, build_block
from repository_presenter.components.readme_diagram.build import line_budget_px
from repository_presenter.components.readme_diagram.contract import (
    MAX_LABEL_LINES,
    ContractFailure,
    title_failure,
    topology_failures,
)
from repository_presenter.components.readme_diagram.geometry import label_lines

#: No label wraps past this many lines at its diagram's line budget (README_CONTRACT.md 2.1).
GLANCE_MAX_LINES = MAX_LABEL_LINES


def draw_at_a_glance(
    *,
    product: str,
    starting_points: Sequence[str],
    capability_titles: Sequence[str],
    outputs: Sequence[str],
) -> list[str]:
    """The fenced Mermaid block of the diagram: one chain, ``Starting Points``, the product,
    ``Core Capabilities`` (one column up to five capabilities, two balanced columns from six) and
    ``Outputs``, left to right; a group with nothing verified is omitted with its hop."""
    return build_block(
        Glance(
            product=product,
            starting_points=tuple(starting_points),
            capability_columns=balanced_columns(tuple(capability_titles)),
            outputs=tuple(outputs),
        )
    )


def capability_title_problem(title: str, capability_count: int) -> str | None:
    """Why ``title`` cannot be drawn geometry-safe in a diagram of ``capability_count``
    capabilities (a word wider than the line budget, or too many lines), or ``None``: planning
    shortens such a title, the renderer never clips it."""
    return title_failure(title, capability_count)


def diagram_failures(body: str, has_inputs: bool) -> list[ContractFailure]:
    """README_CONTRACT.md section 2.1 against one Mermaid body: BC-07's topology and geometry."""
    return topology_failures(body, has_inputs)


def label_height(label: str, capability_count: int = 1) -> int:
    """How many lines ``label`` occupies in a diagram of ``capability_count`` capabilities."""
    glance = Glance("", (), balanced_columns(tuple("x" * capability_count)), ())
    return label_lines(label, line_budget_px(glance))
