"""Reading an At a Glance diagram: its meaning, and a closed shape that refuses anything else."""

from __future__ import annotations

import pytest

from repository_presenter.components.readme_diagram.model import Glance, NotAGlanceError
from repository_presenter.components.readme_diagram.parse import clean_label, parse

BASE = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing OBJ file"]
  end
  PRODUCT["Aspose.3D FOSS for Python"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["One"]
    c2["Two"]
    c3["Three"]
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["An OBJ file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""

TWO_COLUMNS = """\
flowchart TD
  PRODUCT["P"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["One"]
      c2["Two"]
      c3["Three"]
    end
    subgraph capr[" "]
      direction TB
      c4["Four"]
      c5["Five"]
      c6["Six"]
    end
  end
  PRODUCT --> Capabilities
"""


def test_the_diagram_the_renderer_has_always_written_is_read_into_its_meaning() -> None:
    parsed = parse(BASE)
    assert parsed.glance == Glance(
        product="Aspose.3D FOSS for Python",
        starting_points=("An existing OBJ file",),
        capability_columns=(("One", "Two", "Three"),),
        outputs=("An OBJ file",),
    )
    assert parsed.root_direction == "TD"
    assert parsed.group_direction["StartingPoints"] == "LR"
    assert parsed.pinned == frozenset()
    assert parsed.init == {}


def test_two_columns_are_read_left_column_first_whatever_order_they_are_declared_in() -> None:
    natural = parse(TWO_COLUMNS)
    assert natural.glance.capability_columns == (("One", "Two", "Three"), ("Four", "Five", "Six"))
    assert natural.declared_columns == ("capl", "capr")
    swapped = TWO_COLUMNS.replace("capl", "TMP").replace("capr", "capl").replace("TMP", "capr")
    again = parse(swapped)
    # Renaming the clusters is not what reorders the columns: the node numbers are.
    assert again.glance.capability_columns == natural.glance.capability_columns


def test_a_group_title_is_a_label_and_is_kept() -> None:
    parsed = parse(BASE.replace('"Starting Points"', '"Inputs and formats"'))
    assert parsed.glance.starting_title == "Inputs and formats"
    assert parsed.glance.titles == ("Inputs and formats", "Core Capabilities", "Outputs")


def test_the_diagram_without_starting_points_or_outputs_has_the_shorter_chain() -> None:
    source = (
        'flowchart TD\n  PRODUCT["P"]\n  subgraph Capabilities["Core Capabilities"]\n'
        '    c1["A"]\n    c2["B"]\n    c3["C"]\n  end\n  PRODUCT --> Capabilities\n'
    )
    glance = parse(source).glance
    assert glance.starting_points == () and glance.outputs == ()
    assert glance.titles == ("Core Capabilities",)


def test_breaks_whitespace_and_entities_are_drawing_not_meaning() -> None:
    assert clean_label("Document,<br/>layer<br>metadata  <br />inspection") == (
        "Document, layer metadata inspection"
    )
    assert clean_label("Vec#lt;u8#gt; #amp; more") == "Vec<u8> & more"
    parsed = parse(BASE.replace('"One"', '"O<br/>ne  and<br>more"'))
    assert parsed.glance.capability_columns[0][0] == "O ne and more"
    assert parsed.raw_labels["c1"] == "O<br/>ne  and<br>more"


def test_the_init_directive_and_order_pins_are_read() -> None:
    source = '%%{init: {"htmlLabels": false}}%%\n' + BASE.replace(
        '    c3["Three"]\n', '    c3["Three"]\n    c1 ~~~ c2 ~~~ c3\n'
    )
    parsed = parse(source)
    assert parsed.init == {"htmlLabels": False}
    assert parsed.pinned == frozenset({"Capabilities"})


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        (BASE.replace("  StartingPoints -->", '  A["x"]\n  A --> B\n  StartingPoints -->'), "edge"),
        (BASE + "  classDef a fill:#fff\n", "unsupported statement"),
        (BASE + "  style PRODUCT fill:#fff\n", "unsupported statement"),
        (BASE.replace('PRODUCT["Aspose.3D FOSS for Python"]\n', ""), "product"),
        (BASE.replace("StartingPoints --> PRODUCT", "PRODUCT --> StartingPoints"), "chain"),
        (BASE.replace("--> Outputs", ""), "chain"),
        (BASE.replace('["Core Capabilities"]', '[" "]'), "title"),
        (
            BASE.replace("Capabilities[", "Extras[").replace("--> Capabilities", "--> Extras"),
            "outside",
        ),
        (BASE.replace("flowchart TD\n", ""), "no flowchart declaration"),
        (BASE + '  subgraph Extra["x"]\n', "never closed"),
        (BASE + "  end\n", "end without"),
        (BASE.replace('c2["Two"]', 'c1["Two"]'), "twice"),
        (BASE.replace('c3["Three"]', 'c3[""]'), "empty label"),
        ("%%{init: nonsense}%%\n" + BASE, "directive"),
        ("%%{init: {broken}}%%\n" + BASE, "not JSON"),
        (BASE.replace("flowchart TD", "sequenceDiagram"), "no flowchart declaration"),
    ],
)
def test_anything_outside_the_closed_shape_is_refused(source: str, reason: str) -> None:
    with pytest.raises(NotAGlanceError, match=reason):
        parse(source)


def test_three_capability_columns_a_titled_column_and_mixed_columns_are_refused() -> None:
    third = TWO_COLUMNS.replace(
        "  end\n  PRODUCT", '    subgraph capm[" "]\n      c7["Seven"]\n    end\n  end\n  PRODUCT'
    )
    with pytest.raises(NotAGlanceError, match="more than two"):
        parse(third)
    with pytest.raises(NotAGlanceError, match="titled or nested"):
        parse(TWO_COLUMNS.replace('capl[" "]', 'capl["Left"]'))
    mixed = TWO_COLUMNS.replace('    subgraph capl[" "]', '    c9["Loose"]\n    subgraph capl[" "]')
    with pytest.raises(NotAGlanceError, match="mixes"):
        parse(mixed)
    empty = TWO_COLUMNS.replace('      c4["Four"]\n      c5["Five"]\n      c6["Six"]\n', "")
    with pytest.raises(NotAGlanceError, match="empty capability column"):
        parse(empty)


def test_an_order_pin_that_is_not_a_groups_own_chain_is_refused() -> None:
    with pytest.raises(NotAGlanceError, match="order pin"):
        parse(BASE.replace('    c3["Three"]\n', '    c3["Three"]\n    c2 ~~~ c1\n'))
    with pytest.raises(NotAGlanceError, match="order pin"):
        parse(BASE.replace('    c3["Three"]\n', '    c3["Three"]\n    c1 ~~~ ghost\n'))


def test_every_live_diagram_is_read(live: dict[str, str]) -> None:
    assert len(live) == 32
    for name, source in live.items():
        glance = parse(source).glance
        assert glance.product and all(glance.labels), name
        assert 1 <= len(glance.capability_columns) <= 2, name
        assert len(glance.capabilities) >= 3, name


def test_the_live_set_has_the_shapes_the_investigation_counted(live: dict[str, str]) -> None:
    glances = {name: parse(source) for name, source in live.items()}
    two_columns = [n for n, p in glances.items() if len(p.glance.capability_columns) == 2]
    without_starting_points = [n for n, p in glances.items() if not p.glance.starting_points]
    retitled = [n for n, p in glances.items() if p.glance.starting_title != "Starting Points"]
    assert (len(two_columns), len(without_starting_points), len(retitled)) == (23, 1, 1)
    assert all(p.root_direction == "TD" for p in glances.values())
    assert all(p.declared_columns in {(), ("capl", "capr")} for p in glances.values())
