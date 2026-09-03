"""Semantic shell v1: the seventeen sections of docs/README_CONTRACT.md section 2, in order.

Each section records who produces its content: ``D`` the deterministic renderer from facts,
``L`` LLM content units bound to fact IDs, ``M`` mixed (the LLM selects or describes, the
renderer emits every identifier, command, link, and code block). An inherited unit can be placed
only into an ``L`` or ``M`` section; a ``D`` section renders from facts and supersedes the unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

SHELL_VERSION = "3"
# Fixed level-three subheadings a shell row prescribes (README_CONTRACT.md section 2 row 9).
SUBSECTION_HEADINGS = frozenset(
    {
        "Required Package Dependencies",
        "Optional Dependencies",
        "Native and System Requirements",
        "Development Dependencies",
    }
)
Owner = Literal["D", "L", "M"]


@dataclass(frozen=True)
class Section:
    id: str
    heading: str | None
    required: bool
    visibility: Literal["visible", "collapsible", "below_the_fold"]
    owner: Owner
    condition: str | None
    content: str


SEMANTIC_SHELL: tuple[Section, ...] = (
    Section(
        "identity",
        None,
        True,
        "visible",
        "D",
        None,
        "Exactly one H1, the complete canonical product name.",
    ),
    Section(
        "badges",
        None,
        True,
        "visible",
        "D",
        None,
        "One badge row in stable order; a badge whose target is unavailable is omitted.",
    ),
    Section(
        "opening",
        None,
        True,
        "visible",
        "L",
        None,
        "Two to four sentences: what it does, problems it solves, who uses it.",
    ),
    Section(
        "navigation",
        "Navigation",
        True,
        "visible",
        "D",
        None,
        "Compact list of in-page links to the visible headed sections actually present.",
    ),
    Section(
        "at_a_glance",
        "At a Glance",
        False,
        "visible",
        "M",
        "at least one verified input format and one capability",
        "Mermaid typed capability graph.",
    ),
    Section(
        "key_capabilities",
        "Key Capabilities",
        True,
        "visible",
        "L",
        None,
        "Three to eight action-led items grounded in facts, one sentence each.",
    ),
    Section(
        "installation",
        "Installation",
        True,
        "visible",
        "D",
        None,
        "The verified install command for the ecosystem.",
    ),
    Section(
        "dependencies",
        "Dependencies",
        True,
        "visible",
        "D",
        None,
        "The dependency snapshot in four subsections; verified-zero is stated, never omitted.",
    ),
    Section(
        "quick_start",
        "Quick Start",
        True,
        "visible",
        "M",
        None,
        "One minimal example executed in isolation; the LLM supplies one lead-in sentence.",
    ),
    Section(
        "additional_examples",
        "Additional Examples",
        False,
        "collapsible",
        "M",
        "at least one further verified example",
        "A lead-in, then one details block: every further example under a task-named heading.",
    ),
    Section(
        "api_reference",
        "API Reference",
        False,
        "collapsible",
        "M",
        "the plan finds it useful",
        "At most twelve curated hub APIs from the verified public surface.",
    ),
    Section(
        "documentation_resources",
        "Documentation & Resources",
        False,
        "visible",
        "M",
        "verified relevant targets exist",
        "Verified documentation, reference, and knowledge-base links within ceilings.",
    ),
    Section(
        "scope_limitations",
        "Scope and Limitations",
        True,
        "visible",
        "L",
        None,
        "Every material limitation from evidence and inherited units.",
    ),
    Section(
        "development_testing",
        "Development and Testing",
        False,
        "visible",
        "M",
        "build or test assets exist",
        "How to build and test from the actual build files and CI.",
    ),
    Section(
        "enterprise_relationship",
        None,
        False,
        "below_the_fold",
        "M",
        "a verified aspose.com product target exists in policy",
        "One or two sentences relating the FOSS scope to the Enterprise Edition.",
    ),
    Section(
        "third_party_notices",
        "Third-Party Notices",
        False,
        "visible",
        "D",
        "the file exists",
        "Repository-relative link with normal link text.",
    ),
    Section(
        "license",
        "License",
        True,
        "visible",
        "D",
        None,
        "Prose declaration from the license fact.",
    ),
)


def section_ids() -> tuple[str, ...]:
    return tuple(section.id for section in SEMANTIC_SHELL)


def placeable_section_ids() -> frozenset[str]:
    """Sections an inherited unit may be placed into: those with LLM or mixed content."""
    return frozenset(section.id for section in SEMANTIC_SHELL if section.owner != "D")


def shell_packet() -> list[dict[str, Any]]:
    """The shell as a job packet field, with ``placeable`` saying where inherited units may go."""
    return [
        {
            "id": section.id,
            "heading": section.heading,
            "required": section.required,
            "visibility": section.visibility,
            "owner": section.owner,
            "placeable": section.owner != "D",
            "condition": section.condition,
            "content": section.content,
        }
        for section in SEMANTIC_SHELL
    ]
