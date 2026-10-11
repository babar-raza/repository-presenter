"""Writing the diagram: the horizontal form, and the properties that make it hold in a browser."""

from __future__ import annotations

import json
import re

import pytest

from repository_presenter.components.readme_diagram import (
    balanced_columns,
    build_block,
    build_body,
    init_directive,
    parse,
)
from repository_presenter.components.readme_diagram.build import (
    BUDGET_ONE_COLUMN_PX,
    BUDGET_TWO_COLUMNS_PX,
    INIT,
    encode_text,
    line_budget_px,
    node_ids,
)
from repository_presenter.components.readme_diagram.geometry import text_px
from repository_presenter.components.readme_diagram.model import Glance
from repository_presenter.components.readme_diagram.parse import clean_label

EIGHT = tuple(f"Capability number {n} of the product" for n in range(1, 9))
GLANCE = Glance(
    product="Aspose.3D FOSS for Python",
    starting_points=("An existing OBJ, STL, or 3MF file", "A second input"),
    capability_columns=balanced_columns(EIGHT),
    outputs=("OBJ, STL, or 3MF file",),
)


def _visible_edges(body: str) -> list[str]:
    return [line.strip() for line in body.splitlines() if "-->" in line]


def test_the_diagram_opens_with_the_init_line_and_flows_left_to_right() -> None:
    lines = build_body(GLANCE).splitlines()
    assert lines[0] == init_directive()
    assert lines[1] == "flowchart LR"
    assert build_block(GLANCE) == ["```mermaid", *lines, "```"]


def test_the_init_line_draws_svg_text_under_both_keys_and_leaves_wrapping_to_the_builder() -> None:
    directive = init_directive()
    assert directive.startswith("%%{init: ") and directive.endswith("}%%")
    config = json.loads(directive.removeprefix("%%{init: ").removesuffix("}%%"))
    assert config == INIT
    assert config["htmlLabels"] is False
    assert config["flowchart"]["htmlLabels"] is False
    # Setting wrappingWidth reverses the order of the two capability columns in Mermaid 12.1.
    assert "wrappingWidth" not in config["flowchart"]


def test_the_three_blocks_and_the_product_are_declared_in_chain_order() -> None:
    body = build_body(GLANCE)
    order = [
        body.index('subgraph StartingPoints["Starting Points"]'),
        body.index('PRODUCT["'),
        body.index('subgraph Capabilities["Core Capabilities"]'),
        body.index('subgraph Outputs["Outputs"]'),
    ]
    assert order == sorted(order)
    assert _visible_edges(body) == ["StartingPoints --> PRODUCT --> Capabilities --> Outputs"]


def test_there_is_no_styling_directive_and_no_html_label() -> None:
    body = build_body(GLANCE)
    assert not re.search(r"^\s*(style|classDef|linkStyle|click)\b", body, re.MULTILINE)
    assert "<" not in body.replace("<br/>", "")


def test_two_columns_are_declared_right_to_left_so_mermaid_draws_them_left_to_right() -> None:
    body = build_body(GLANCE)
    assert body.index('subgraph capr[" "]') < body.index('subgraph capl[" "]')
    parsed = parse(body)
    assert parsed.declared_columns == ("capr", "capl")
    # The left column holds the first half in reading order, numbered from c1.
    assert parsed.glance.capability_columns == balanced_columns(EIGHT)
    left = body[body.index('subgraph capl[" "]') :]
    assert 'c1["' in left and 'c4["' in left and 'c5["' not in left.split("end")[0]


def test_every_group_of_several_nodes_is_a_pinned_top_to_bottom_column() -> None:
    body = build_body(GLANCE)
    assert "i1 ~~~ i2" in body
    assert "c1 ~~~ c2 ~~~ c3 ~~~ c4" in body
    assert "c5 ~~~ c6 ~~~ c7 ~~~ c8" in body
    assert "o1 ~~~" not in body  # one node: nothing to order
    assert body.count("direction TB") == 5  # Starting Points, Core, two columns, Outputs
    assert "direction LR" not in body


def test_up_to_five_capabilities_are_one_pinned_column_and_more_are_two_balanced() -> None:
    five = Glance("P", (), balanced_columns(EIGHT[:5]), ())
    body = build_body(five)
    assert "capl" not in body and "c1 ~~~ c2 ~~~ c3 ~~~ c4 ~~~ c5" in body
    assert [len(c) for c in balanced_columns(EIGHT[:6])] == [3, 3]
    assert [len(c) for c in balanced_columns(EIGHT[:7])] == [4, 3]
    assert [len(c) for c in balanced_columns(EIGHT)] == [4, 4]


def test_absent_groups_are_omitted_with_their_hop() -> None:
    body = build_body(Glance("P", (), balanced_columns(EIGHT[:3]), ()))
    assert "StartingPoints" not in body and "Outputs" not in body
    assert _visible_edges(body) == ["PRODUCT --> Capabilities"]


def test_every_label_is_wrapped_inside_the_budget_of_its_diagram() -> None:
    for glance in (GLANCE, Glance("P", (), balanced_columns(EIGHT[:4]), ("Out",))):
        budget = line_budget_px(glance)
        body = build_body(glance)
        for label in re.findall(r'\["([^"]*)"\]', body):
            for line in label.split("<br/>"):
                words = clean_label(line).split()
                assert text_px(clean_label(line)) <= budget or len(words) == 1, (line, budget)
    assert BUDGET_TWO_COLUMNS_PX < BUDGET_ONE_COLUMN_PX


def test_building_is_idempotent_and_keeps_the_meaning() -> None:
    body = build_body(GLANCE)
    assert parse(body).glance == GLANCE
    assert build_body(parse(body).glance) == body


def test_node_ids_are_the_ids_the_source_uses_and_number_across_the_columns() -> None:
    ids = node_ids(GLANCE)
    assert list(ids) == ["i1", "i2", "PRODUCT", *[f"c{n}" for n in range(1, 9)], "o1"]
    body = build_body(GLANCE)
    assert set(re.findall(r"^\s*(\w+)\[\"", body, re.MULTILINE)) - {
        "StartingPoints",
        "Capabilities",
        "Outputs",
        "capl",
        "capr",
    } == set(ids)
    assert ids["c5"] == EIGHT[4]


def test_text_mermaid_would_eat_or_double_read_is_encoded() -> None:
    assert encode_text('say "hi"') == "say 'hi'"
    assert encode_text("Vec<u8>") == "Vec#lt;u8#gt;"
    assert encode_text("R&D") == "R&D"
    assert encode_text("a &amp; b") == "a #amp;amp; b"
    assert encode_text("a &lt; b") == "a #amp;lt; b"
    glance = Glance("P", (), (("A<T>", "B", "C"),), ())
    assert parse(build_body(glance)).glance == glance


def test_every_live_diagram_rebuilds_to_a_stable_horizontal_drawing(live: dict[str, str]) -> None:
    for name, source in live.items():
        glance = parse(source).glance
        body = build_body(glance)
        assert body.splitlines()[:2] == [init_directive(), "flowchart LR"], name
        assert parse(body).glance == glance, name
        assert build_body(parse(body).glance) == body, name
        edges = _visible_edges(body)
        assert len(edges) == 1 and edges[0].endswith(("Capabilities", "Outputs")), name


@pytest.mark.parametrize("count", range(3, 9))
def test_the_column_rule_holds_for_every_count_the_contract_allows(count: int) -> None:
    columns = balanced_columns(EIGHT[:count])
    assert len(columns) == (1 if count <= 5 else 2)
    assert sum(len(column) for column in columns) == count
    assert max(len(c) for c in columns) - min(len(c) for c in columns) <= 1
