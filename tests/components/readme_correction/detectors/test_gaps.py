"""Report-only gaps: the facts that would fill what the README lacks, never an edit."""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.detectors.gaps import report_gaps


def test_unseen_examples_types_formats_and_notices_are_reported_with_their_facts(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact(
            "example:001", "scene = Scene()\nscene.save('a.stl')\n", evidence=(("README.md", "x"),)
        ),
        make_fact("example:002", "shown = 1\n", evidence=(("README.md", "x"),)),
        make_fact(
            "public_symbol:p.scene",
            "p.Scene",
            evidence=(("a.py", "line 1; class"),),
            attributes={"symbol_kind": "class"},
        ),
        make_fact(
            "public_symbol:p.mesh",
            "p.Mesh",
            evidence=(("a.py", "line 2; class"),),
            attributes={"symbol_kind": "class"},
        ),
        make_fact("format:stl", ".stl", evidence=(("a.py", None),)),
        make_fact("format:obj", ".obj", evidence=(("a.py", None),)),
        make_fact("third_party_notices:file", "THIRD_PARTY_NOTICES.md", evidence=(("T", None),)),
        make_fact(
            "link_target:product.enterprise",
            "https://products.aspose.com/3d/java/",
            evidence=(("https://products.aspose.com/3d/", "enterprise target"),),
        ),
    )
    readme = "# P\n\nThe Scene class saves .stl.\n\n```python\nshown = 1\n```\n"
    result = report_gaps(make_context(readme, facts))
    assert result.edits == ()
    text = "\n".join(f.reason for f in result.findings)
    assert (
        "1 verified example(s) whose code the README never shows" in text and "example:001" in text
    )
    assert (
        "1 of 2 verified public types are named nowhere" in text and "public_symbol:p.mesh" in text
    )
    assert "1 verified format(s) named nowhere" in text and "format:obj" in text
    assert "no Enterprise Edition paragraph" in text and "link_target:product.enterprise" in text
    assert "THIRD_PARTY_NOTICES.md" in text and "never added" in text


def test_a_readme_that_says_everything_the_facts_hold_has_no_gaps(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact(
            "public_symbol:p.scene",
            "p.Scene",
            evidence=(("a.py", "line 1; class"),),
            attributes={"symbol_kind": "class"},
        ),
        make_fact("format:stl", ".stl", evidence=(("a.py", None),)),
    )
    result = report_gaps(make_context("# P\n\nScene reads .stl files.\n", facts))
    assert result.findings == ()


def test_a_no_dependencies_claim_beside_required_dependency_facts_is_reported(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = make_facts(
        make_fact("dependency:skiasharp", "SkiaSharp 2.88.8", evidence=(("x.csproj", None),)),
        drop=["dependency:none"],
    )
    readme = "# P\n\nBuilt as pure managed code.\n\nAlso fine: dependency-free docs.\n"
    result = report_gaps(make_context(readme, facts))
    lines = [f.line for f in result.findings if f.line]
    assert lines == [3, 5]
    assert "dependency:skiasharp" in result.findings[0].reason
    clean = report_gaps(make_context(readme, make_facts()))  # only dependency:none: no conflict
    assert not [f for f in clean.findings if f.line]
