"""Write the At a Glance diagram: three blocks left to right, labels that grow their own box.

Why the diagram is drawn this way (each point measured in a real render, Mermaid 11.4 to 12.1, see
``render_check.py``; the layout facts are in ``tests/components/readme_diagram``):

* **Left to right.** ``flowchart LR`` puts ``Starting Points``, the product, ``Core Capabilities``
  and ``Outputs`` in one row. The old ``flowchart TD`` stacked them, and every ``direction`` line
  inside a group that the chain edge reaches was drawn against its author's intent: ``TB`` over
  unlinked nodes lays them in a *row*, ``LR`` in a *column*.
* **Columns that stay in order.** A group of several nodes is a column only when its nodes are
  chained with invisible ``~~~`` edges under ``direction TB``; that also pins the reading order,
  which an unpinned group leaves to the renderer (Mermaid 12 reverses it).
* **Two capability columns side by side, left column first.** Core ``direction TB`` lays the two
  column clusters out as a row in every release measured. On Mermaid 11.4 to 11.17 the siblings
  come out in reverse declaration order, so the right column is declared first. Mermaid 12.1 orders
  them by its own heuristic (reversed for 20 of the 23 live two-column diagrams): still side by
  side, the first column left only on 11.x, the line GitHub runs (owner report 2026-10-11).
* **No clipping.** Mermaid's default HTML labels are fixed-size ``foreignObject`` boxes measured in
  one font: any wider font clips them. ``htmlLabels: false`` (both the root and the ``flowchart``
  key, for 11.4 to 12.1) draws SVG text in a box sized from the text, which survives a font swap.
* **No re-wrapping.** Every label is broken into ``<br/>`` lines by ``geometry.wrap_label`` inside
  a pixel budget that stays under the wrap width, so the renderer never wraps it again. Mermaid 11
  wraps at 200 px; Mermaid 12 wraps SVG text at about 15 characters and splits words, so
  ``wrappingWidth`` is set to ``WRAPPING_WIDTH_PX`` (in 12.1 the two capability columns are then
  drawn in the renderer's own order, as they already were in 20 of 23 live diagrams).
* **Characters Mermaid would eat.** ``<u8>`` in a label is dropped as an HTML tag. ``<`` and ``>``
  are written ``#lt;`` and ``#gt;``, which draw correctly from Mermaid 11.14; before 11.14 SVG
  labels show any ``&``, ``<`` or ``>`` as its entity text (a Mermaid bug, measured 11.4 to 11.13),
  so planning should keep those characters out of diagram labels (``lint.LABEL_ENTITY_RISK``).

Pure and deterministic; the renderer owns every node, edge and label.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from repository_presenter.components.readme_diagram.geometry import wrap_label
from repository_presenter.components.readme_diagram.model import Glance

#: Mermaid 12 re-wraps SVG text labels at about 15 characters on top of the hard ``<br/>`` breaks,
#: and breaks inside a word ("password-protec / ted)"); 11.x does not. A wrapping width wider than
#: any label line (the budgets below are 200 px) leaves the builder's own breaks as the only ones
#: on every release (measured on 11.4.1, 11.12.0, 11.17.2 and 12.1.0: 0 re-wraps, 0 split words,
#: lines unchanged on 11.x).
WRAPPING_WIDTH_PX = 400
#: ``htmlLabels`` is set at the root and under ``flowchart``: from 11.17 the root key alone gives
#: all-SVG labels, but 11.4 to 11.12 draw the group titles as HTML unless both are set (measured).
INIT: dict[str, object] = {
    "htmlLabels": False,
    "flowchart": {
        "htmlLabels": False,
        "nodeSpacing": 22,
        "rankSpacing": 26,
        "padding": 10,
        "useMaxWidth": True,
        "wrappingWidth": WRAPPING_WIDTH_PX,
    },
}
#: The line budget, in modelled pixels, for one capability column and for two: two columns share
#: the width of a README, so each gets less.
BUDGET_ONE_COLUMN_PX = 200.0
BUDGET_TWO_COLUMNS_PX = 160.0
#: Up to this many capabilities form one column; more form two balanced columns (contract 2.1).
ONE_COLUMN_MAX = 5

BREAK = "<br/>"


def init_directive() -> str:
    """The one ``%%{init: ...}%%`` line every diagram opens with."""
    return "%%{init: " + json.dumps(INIT, separators=(", ", ": ")) + "}%%"


def balanced_columns(titles: Sequence[str]) -> tuple[tuple[str, ...], ...]:
    """The contract's column rule: up to five capabilities in one column, more in two balanced."""
    items = tuple(titles)
    if len(items) <= ONE_COLUMN_MAX:
        return (items,)
    left = (len(items) + 1) // 2
    return (items[:left], items[left:])


def line_budget_px(glance: Glance) -> float:
    """The width every label of ``glance`` wraps to: one budget per diagram, so siblings agree."""
    return BUDGET_ONE_COLUMN_PX if len(glance.capability_columns) == 1 else BUDGET_TWO_COLUMNS_PX


def encode_text(text: str) -> str:
    """``text`` as Mermaid reads it between quotes: no ``"``, ``<`` and ``>`` as entities."""
    text = text.replace('"', "'").replace("<", "#lt;").replace(">", "#gt;")
    return re.sub(r"&(?=\w+;)", "#amp;", text)


def label_text(label: str, budget_px: float) -> str:
    """``label`` as it is written between the quotes: wrapped into ``<br/>`` lines."""
    return BREAK.join(encode_text(line) for line in wrap_label(label, budget_px))


def _title(title: str) -> str:
    return encode_text(title)


def _node(ident: str, label: str, budget_px: float, indent: str) -> str:
    return f'{indent}{ident}["{label_text(label, budget_px)}"]'


def _column(
    prefix: str, labels: Sequence[str], first: int, budget_px: float, indent: str
) -> list[str]:
    """``direction TB``, the nodes numbered from ``first``, and the chain that pins their order."""
    lines = [f"{indent}direction TB"]
    lines += [
        _node(f"{prefix}{first + offset}", label, budget_px, indent)
        for offset, label in enumerate(labels)
    ]
    if len(labels) > 1:
        lines.append(indent + " ~~~ ".join(f"{prefix}{first + n}" for n in range(len(labels))))
    return lines


def node_ids(glance: Glance) -> dict[str, str]:
    """Every node id the diagram uses, with its label, numbered as ``build_body`` numbers them:
    ``i1..`` inputs, ``PRODUCT``, ``c1..`` capabilities across the columns left to right, ``o1..``
    outputs. The real-render check finds the nodes it measures by these ids."""
    ids = {f"i{n}": label for n, label in enumerate(glance.starting_points, start=1)}
    ids["PRODUCT"] = glance.product
    ids.update({f"c{n}": label for n, label in enumerate(glance.capabilities, start=1)})
    ids.update({f"o{n}": label for n, label in enumerate(glance.outputs, start=1)})
    return ids


def build_body(glance: Glance) -> str:
    """The Mermaid source of ``glance``, without its code fence, ending in a newline."""
    budget = line_budget_px(glance)
    lines = [init_directive(), "flowchart LR"]
    chain: list[str] = []
    if glance.starting_points:
        lines.append(f'  subgraph StartingPoints["{_title(glance.starting_title)}"]')
        lines += _column("i", glance.starting_points, 1, budget, "    ")
        lines.append("  end")
        chain.append("StartingPoints")
    lines.append(_node("PRODUCT", glance.product, budget, "  "))
    chain.append("PRODUCT")
    lines.append(f'  subgraph Capabilities["{_title(glance.capabilities_title)}"]')
    columns = glance.capability_columns
    if len(columns) == 1:
        lines += _column("c", columns[0], 1, budget, "    ")
    else:
        lines.append("    direction TB")
        starts = [
            1 + sum(len(column) for column in columns[:index]) for index in range(len(columns))
        ]
        # Declared right to left: Mermaid draws sibling clusters of a row in reverse order.
        for index in reversed(range(len(columns))):
            name = ("capl", "capr")[index]
            lines.append(f'    subgraph {name}[" "]')
            lines += _column("c", columns[index], starts[index], budget, "      ")
            lines.append("    end")
    lines.append("  end")
    chain.append("Capabilities")
    if glance.outputs:
        lines.append(f'  subgraph Outputs["{_title(glance.outputs_title)}"]')
        lines += _column("o", glance.outputs, 1, budget, "    ")
        lines.append("  end")
        chain.append("Outputs")
    lines.append("  " + " --> ".join(chain))
    return "\n".join(lines) + "\n"


def build_block(glance: Glance) -> list[str]:
    """The README lines of the diagram: the fenced ``mermaid`` block."""
    return ["```mermaid", *build_body(glance).rstrip("\n").split("\n"), "```"]
