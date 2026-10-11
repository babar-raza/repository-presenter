"""README_CONTRACT.md section 2.1 for the horizontal At a Glance diagram, as one pure function.

This is the replacement body for BC-07's ``_topology_failures`` (``validation/registry.py``) and
the ceilings planning checks a capability title against, written here so the governed change that
adopts it is a delegation, not a rewrite. It judges a *candidate* README's diagram, which the
renderer wrote: unlike ``lint.py`` (which describes any drawing it can parse), it holds the
diagram to the contract exactly.

The contract, in the order the checks run:

1. The diagram is the closed shape ``parse.py`` reads, and it *is* what ``build.py`` writes for its
   meaning: ``flowchart LR`` after the one init line, the three groups left to right, columns
   pinned and declared right to left, labels wrapped by the width model, no styling directive.
2. Starting Points only with a verified input format; three to eight capabilities; one column up to
   five, two balanced columns from six.
3. Geometry safe: no label wraps past four lines at the diagram's line budget, and no word is wider
   than that budget (a longer title is shortened at planning, never clipped at render).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repository_presenter.components.readme_diagram.build import (
    ONE_COLUMN_MAX,
    build_body,
    line_budget_px,
)
from repository_presenter.components.readme_diagram.geometry import label_lines, widest_token_px
from repository_presenter.components.readme_diagram.lint import first_difference, normalize
from repository_presenter.components.readme_diagram.model import Glance, NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse

Stage = Literal["PLANNING", "COMPOSING"]
COMPOSING: Stage = "COMPOSING"
PLANNING: Stage = "PLANNING"
MIN_CAPABILITIES = 3
MAX_CAPABILITIES = 8
#: The most lines one label may wrap to at the diagram's budget (the old ceiling was three at 28
#: characters; the budget is in pixels now, and a title longer than this is shortened at planning).
MAX_LABEL_LINES = 4


@dataclass(frozen=True)
class ContractFailure:
    """One contract failure; ``stage`` is the earliest stage that can repair it."""

    stage: Stage
    message: str


def _count_failures(glance: Glance, has_inputs: bool) -> list[ContractFailure]:
    failures: list[ContractFailure] = []
    if glance.starting_points and not has_inputs:
        failures.append(
            ContractFailure(
                PLANNING, "At a Glance shows Starting Points without a verified input format"
            )
        )
    count = len(glance.capabilities)
    columns = glance.capability_columns
    if count > MAX_CAPABILITIES:
        failures.append(
            ContractFailure(PLANNING, f"At a Glance shows {count} capabilities; at most 8")
        )
    elif count < MIN_CAPABILITIES:
        failures.append(
            ContractFailure(PLANNING, f"At a Glance shows {count} capabilities; at least 3")
        )
    elif count <= ONE_COLUMN_MAX and len(columns) != 1:
        failures.append(
            ContractFailure(
                COMPOSING, f"At a Glance: {count} capabilities form one column, not two"
            )
        )
    elif count > ONE_COLUMN_MAX:
        if len(columns) != 2:
            failures.append(
                ContractFailure(
                    COMPOSING,
                    f"At a Glance: {count} capabilities form two balanced columns; "
                    f"found {len(columns)} column(s)",
                )
            )
        elif abs(len(columns[0]) - len(columns[1])) > 1:
            failures.append(
                ContractFailure(
                    COMPOSING,
                    f"At a Glance: {count} capabilities form two balanced columns; "
                    f"found {len(columns[0])} and {len(columns[1])}",
                )
            )
    return failures


def label_failures(glance: Glance) -> list[ContractFailure]:
    """Every label that is not geometry safe at ``glance``'s line budget."""
    budget = line_budget_px(glance)
    failures: list[ContractFailure] = []
    for label in (*glance.labels, *glance.titles):
        if widest_token_px(label) > budget:
            failures.append(
                ContractFailure(
                    PLANNING,
                    f"At a Glance label {label!r} has a word wider than the {budget:.0f}px "
                    "line budget; shorten the title",
                )
            )
        lines = label_lines(label, budget)
        if lines > MAX_LABEL_LINES:
            failures.append(
                ContractFailure(
                    PLANNING,
                    f"At a Glance label {label!r} wraps to {lines} lines at the {budget:.0f}px "
                    f"line budget; at most {MAX_LABEL_LINES}",
                )
            )
    return failures


def title_failure(title: str, glance_capability_count: int) -> str | None:
    """Why a capability ``title`` is not geometry safe for a diagram of that many capabilities."""
    columns = 1 if glance_capability_count <= ONE_COLUMN_MAX else 2
    probe = Glance("", (), tuple(() for _ in range(columns)), ())
    budget = line_budget_px(probe)
    if widest_token_px(title) > budget:
        return f"has a word wider than the {budget:.0f}px line budget"
    lines = label_lines(title, budget)
    if lines > MAX_LABEL_LINES:
        return (
            f"wraps to {lines} lines at the {budget:.0f}px line budget; at most {MAX_LABEL_LINES}"
        )
    return None


def topology_failures(body: str, has_inputs: bool) -> list[ContractFailure]:
    """README_CONTRACT.md section 2.1 against one diagram body (the text between the fences)."""
    try:
        parsed = parse(body)
    except NotAGlanceError as error:
        return [ContractFailure(COMPOSING, f"At a Glance is not the contract's chain: {error}")]
    glance = parsed.glance
    failures: list[ContractFailure] = []
    actual = normalize(body)
    expected = build_body(glance)
    if actual != expected:
        failures.append(
            ContractFailure(
                COMPOSING,
                "At a Glance is not the contract's horizontal drawing of its own content "
                f"({first_difference(actual, expected)})",
            )
        )
    failures += _count_failures(glance, has_inputs)
    failures += label_failures(glance)
    return failures
