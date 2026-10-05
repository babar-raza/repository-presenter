"""The At a Glance label-geometry policy: one wrap width for every node, one line ceiling.

``docs/README_CONTRACT.md`` section 2.1: "Every label is geometry-safe: no unbroken token over 28
characters, and no label wrapping past three lines at Mermaid's default node width - a longer title
is shortened at planning, never clipped at render. No custom styling directives."

``plans/idea.md``: "Input and output labels use deterministic wrapping and a common rendered-width
policy so sibling endpoint boxes remain visually consistent while height may grow for wrapped
text."

The policy is expressed once, here. Every node label - an input or output endpoint, the product, a
capability - wraps at the same width (:data:`GLANCE_LINE_CHARS`, the contract's own geometry unit)
and may grow in height up to :data:`GLANCE_MAX_LINES` lines; no node carries a width of its own (a
styling directive is already a BC-07 failure), so sibling boxes share one rendered width by
construction. Planning enforces it on the titles it chooses; BC-07 judges every label of the
rendered diagram against the same function.
"""

from __future__ import annotations

GLANCE_LINE_CHARS = 28
GLANCE_MAX_LINES = 3


def wrapped_lines(label: str, width: int = GLANCE_LINE_CHARS) -> list[str]:
    """``label`` wrapped greedily at ``width`` characters, a word longer than ``width`` broken.

    Deterministic: the same label always wraps to the same lines, which is what lets validation and
    planning agree on a label's height before anything is rendered.
    """
    lines: list[str] = []
    current = ""
    for word in label.split():
        while len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:width])
            word = word[width:]
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def label_height(label: str) -> int:
    """How many lines ``label`` occupies at the common node width."""
    return len(wrapped_lines(label))
