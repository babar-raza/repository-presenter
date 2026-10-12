"""What a kept inherited unit is about, read from the heading path it sat under in the source.

Reconciliation (where a unit the reply filed in the wrong section belongs) and placement (which of
the renderer's own sections already state it) read the one answer. The cases are the headings of the
wave-6 bundles (BarCode-Python, Slides-Python, PDF-Python, 3D-Java), not invented ones.
"""

from __future__ import annotations

import pytest

from repository_presenter.components.readme.composition.source_topics import (
    heading_parts,
    path_topic,
    root_heading,
    topic_of,
    unit_topic,
)
from repository_presenter.core.facts import Evidence, Fact


def _unit(ordinal: int, kind: str, section: str | None) -> Fact:
    return Fact(
        f"inherited_unit:{ordinal:03}.{kind}",
        "inherited_unit",
        "Text.",
        (Evidence("README.md", None),),
        attributes={"section": section} if section else None,
    )


@pytest.mark.parametrize(
    ("heading", "topic"),
    [
        # what the Installation and Dependencies sections print
        ("Aspose.BarCode FOSS for Python > Installation", "install"),
        (
            "Aspose.Slides FOSS for Python > Dependencies > Native and System Requirements",
            "install",
        ),
        ("Aspose.PDF FOSS for Python > Installation > Optional extras", "install"),
        # a development dependency is build material, not an install requirement: the deepest
        # heading is read first, and "development" is a build word
        ("Aspose.BarCode FOSS for Python > Dependencies > Development Dependencies", "build"),
        # a heading that only gets the reader going is not the Installation section's subject: the
        # prose under it is often the first example's explanation
        ("Aspose.Cells FOSS for Go > Getting Started", "setup"),
        ("Aspose.Cells FOSS for Go > Setup", "setup"),
        # what the shell prints itself
        ("Aspose.3D FOSS for Java > License", "furniture"),
        ("Aspose.3D FOSS for Java > Table of Contents", "furniture"),
        # the rest of the registry
        ("Aspose.Slides FOSS for Python > Scope and Limitations", "limits"),
        ("Aspose.Slides FOSS for Python > Documentation & Resources", "resources"),
        ("Aspose.Slides FOSS for Python > Examples", "example"),
        ("Aspose.PDF FOSS for Python > API Reference > Low-Code Plugins", "api"),
        ("Aspose.PDF FOSS for Python > Key Capabilities", "capabilities"),
        ("Aspose.Slides FOSS for Python > Development and Testing", "build"),
        ("Aspose.Slides FOSS for Python > Zebra", None),
    ],
)
def test_the_topic_is_read_from_the_deepest_heading_that_names_one(
    heading: str, topic: str | None
) -> None:
    assert topic_of(heading_parts(heading)[1:]) == topic


def test_the_title_is_taken_off_the_front_and_a_unit_under_it_has_no_topic() -> None:
    """``Aspose.Note FOSS`` names a product, not a note: the first part of every path is the
    README's title and is never read as a topic."""
    units = [
        _unit(2, "paragraph", "Aspose.Note FOSS for Python"),
        _unit(3, "paragraph", "Aspose.Note FOSS for Python > Installation"),
        _unit(4, "code_block", "Aspose.Note FOSS for Python > Installation"),
    ]
    root = root_heading(units)
    assert root == "aspose note foss for python"
    assert unit_topic(units[0], root) is None  # the product introduction
    assert unit_topic(units[1], root) == "install"
    assert path_topic("Aspose.Note FOSS for Python > Installation", root) == "install"
    assert path_topic(None, root) is None
    # a README with no title: its first part is a section, read as one
    assert (
        root_heading([_unit(2, "paragraph", "Installation"), _unit(3, "paragraph", "Usage")])
        is None
    )
    assert path_topic("Installation", None) == "install"
