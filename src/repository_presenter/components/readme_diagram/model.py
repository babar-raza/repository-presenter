"""Typed records of the At a Glance diagram: what it says, and what is wrong with how it draws.

The diagram's meaning is five things only - the product, the input formats, the capabilities in
reading order and column, the output formats, and the one chain between them
(``StartingPoints --> PRODUCT --> Capabilities --> Outputs``; README_CONTRACT.md section 2.1).
``Glance`` holds exactly that and nothing about how it is drawn, so a rebuild that keeps a
``Glance`` equal keeps every label and every edge of the diagram it replaces.
"""

from __future__ import annotations

from dataclasses import dataclass


class NotAGlanceError(ValueError):
    """The Mermaid source is not an At a Glance chain this package may rewrite.

    Raised for any shape outside the closed one the renderer writes (an extra edge, a style
    directive, a third capability column, an unknown subgraph): such a diagram is left exactly as
    its authors wrote it rather than guessed at.
    """


@dataclass(frozen=True)
class Glance:
    """The meaning of one At a Glance diagram.

    Every label is plain text with no ``<br/>`` and single spaces: how a label breaks across lines
    is a drawing decision (``geometry.wrap_label``), never part of what the diagram says.
    ``capability_columns`` is one column or two, each in reading order, the left column first.
    The three group titles are labels too (a live diagram may title its first group "Inputs and
    formats"), so they are kept; the defaults are the contract's own.
    """

    product: str
    starting_points: tuple[str, ...]
    capability_columns: tuple[tuple[str, ...], ...]
    outputs: tuple[str, ...]
    starting_title: str = "Starting Points"
    capabilities_title: str = "Core Capabilities"
    outputs_title: str = "Outputs"

    @property
    def capabilities(self) -> tuple[str, ...]:
        """Every capability label, left column first."""
        return tuple(label for column in self.capability_columns for label in column)

    @property
    def labels(self) -> tuple[str, ...]:
        """Every node label the diagram shows, in drawing order."""
        return (*self.starting_points, self.product, *self.capabilities, *self.outputs)

    @property
    def titles(self) -> tuple[str, ...]:
        """The group titles of the groups the diagram has."""
        return (
            *((self.starting_title,) if self.starting_points else ()),
            self.capabilities_title,
            *((self.outputs_title,) if self.outputs else ()),
        )


@dataclass(frozen=True)
class Defect:
    """One way a diagram is drawn that a reader will see go wrong, or that makes it fragile."""

    code: str
    detail: str


@dataclass(frozen=True)
class LintReport:
    """The verdict on one Mermaid source: recognised or not, and every defect found."""

    recognized: bool
    defects: tuple[Defect, ...]
    #: Things worth knowing that a rewrite cannot or must not change (the label's own text).
    advisories: tuple[Defect, ...] = ()

    @property
    def codes(self) -> frozenset[str]:
        return frozenset(defect.code for defect in self.defects)

    @property
    def conforming(self) -> bool:
        """A recognised diagram with no defect: exactly what ``build`` would write (advisories do
        not count: they describe the content, which a rewrite never changes)."""
        return self.recognized and not self.defects
