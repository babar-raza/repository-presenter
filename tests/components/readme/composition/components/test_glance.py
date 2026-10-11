"""The At a Glance component: one label geometry for planning, the renderer and BC-07 (R7, OD-10).

Updated from the V2 item 9 tests (a common 28-character wrap and a three-line ceiling): the width is
now a pixel budget from one character-width model (components/readme_diagram/geometry.py), the
ceiling is four lines, and a word wider than the budget is left whole rather than broken, because
the diagram is drawn as SVG text in a box that grows with its text.
"""

from __future__ import annotations

from repository_presenter.components.readme.composition.components.glance import (
    GLANCE_MAX_LINES,
    capability_title_problem,
    diagram_failures,
    draw_at_a_glance,
    label_height,
)
from repository_presenter.components.readme_diagram import lint_source, parse
from repository_presenter.components.readme_diagram.build import (
    BUDGET_ONE_COLUMN_PX,
    BUDGET_TWO_COLUMNS_PX,
)
from repository_presenter.components.readme_diagram.geometry import text_px

TITLES = ("Read and write scenes", "Export STL", "Edit meshes")


def _body(lines: list[str]) -> str:
    return "\n".join(lines[1:-1])


def test_the_policy_is_a_pixel_budget_per_column_count_and_four_lines() -> None:
    assert GLANCE_MAX_LINES == 4
    assert BUDGET_TWO_COLUMNS_PX < BUDGET_ONE_COLUMN_PX <= 200  # inside Mermaid's own wrap width


def test_a_short_label_is_one_line() -> None:
    assert label_height("Convert to PDF") == 1
    assert label_height("") == 0


def test_a_label_wraps_at_whole_words_inside_the_budget() -> None:
    label = "Read and parse PostScript and EPS documents"
    assert label_height(label) == 3  # the model is the envelope of five fonts: conservative
    assert label_height(label, capability_count=8) >= label_height(label, capability_count=3)
    # the one-column budget holds every line of the wrapped label
    body = _body(
        draw_at_a_glance(
            product="Aspose.Page FOSS for Python",
            starting_points=(),
            capability_titles=(label, "Two", "Three"),
            outputs=(),
        )
    )
    shown = next(line for line in body.splitlines() if 'c1["' in line)
    assert all(text_px(part) <= BUDGET_ONE_COLUMN_PX for part in shown.split('"')[1].split("<br/>"))


def test_a_word_wider_than_the_budget_is_kept_whole_and_planning_names_it() -> None:
    word = "x" * 60
    assert label_height(word) == 1
    problem = capability_title_problem(word, 3)
    assert problem is not None and "word wider than the 200px line budget" in problem
    assert capability_title_problem("Convert to PDF", 3) is None


def test_wrapping_is_deterministic() -> None:
    label = "An existing OBJ, STL, 3MF, GLB, glTF, or FBX file"
    assert label_height(label) == label_height(label) == 3


def test_a_long_title_wraps_past_the_ceiling() -> None:
    long_title = " ".join(["Export", "scenes"] * 12)
    assert label_height(long_title, capability_count=8) > GLANCE_MAX_LINES
    problem = capability_title_problem(long_title, 8)
    assert problem is not None and "at most 4" in problem


def test_the_component_draws_the_contracts_diagram_from_the_plans_selections() -> None:
    lines = draw_at_a_glance(
        product="Aspose.3D FOSS for Python",
        starting_points=("An existing OBJ file",),
        capability_titles=TITLES,
        outputs=("GLB file",),
    )
    assert lines[0] == "```mermaid" and lines[-1] == "```" and lines[2] == "flowchart LR"
    body = _body(lines)
    assert lint_source(body).conforming
    assert diagram_failures(body, True) == []
    assert parse(body).glance.capabilities == TITLES
    # Starting Points without a verified input format is a planning failure, drawn or not.
    assert [f.stage for f in diagram_failures(body, False)] == ["PLANNING"]
