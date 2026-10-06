"""The deferral policy: each DEFER_UNRESOLVED cause classified once, BLOCK or ADVISORY by registry.

One fixture per registered class proves its decision; the paired controls prove the class is
chosen by the cause and not by the shape alone; an unmatched cause must fail closed. An ADVISORY
unit must never reach the public text, which is proven through the same placement path the
composer reads.
"""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.composition.placement import (
    placed_texts,
    placements,
)
from repository_presenter.components.readme.evidence.facts.product_pages import ENTERPRISE_FACT_ID
from repository_presenter.components.readme.validation.deferrals import (
    DEFERRAL_CLASSES,
    review_deferrals,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REPO = "org/Aspose.Widget-FOSS-for-Python"
REVISION = "a" * 40


def _unit(number: int, kind: str, value: str) -> Fact:
    return Fact(
        f"inherited_unit:{number:03d}.{kind}",
        "inherited_unit",
        value,
        (Evidence("README.md", None),),
    )


def _example(number: int, polarity: str, unit: int | None = None, kind: str = "code_block") -> Fact:
    detail = f"lines 1-3; unit inherited_unit:{unit:03d}.{kind}" if unit is not None else None
    return Fact(
        f"example:{number:03d}",
        "example",
        "a verified example",
        (Evidence("README.md", detail),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument(REPO, REVISION, tuple(facts))


def _deferred(unit_id: str, rationale: str = "Preserved.") -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "disposition": "DEFER_UNRESOLVED",
        "destination_section": None,
        "fact_ids": [],
        "rationale": rationale,
    }


def _kept(unit_id: str, disposition: str = "OMIT_UNSUPPORTED") -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "disposition": disposition,
        "destination_section": None,
        "fact_ids": [],
        "rationale": "Kept.",
    }


def _only(findings: list[Any]) -> Any:
    assert len(findings) == 1, findings
    return findings[0]


def test_the_registry_holds_exactly_the_ten_real_causes() -> None:
    """A new class is an explicit change here, so it is reviewed rather than slipped in."""
    assert [cls.id for cls in DEFERRAL_CLASSES] == [
        "NO_VERIFIED_QUICK_START",
        "INTERNAL_DETAIL",
        "BUILD_TEST_PATH_UNRECORDED",
        "NOTICES_WITHOUT_RECORD",
        "UNVERIFIED_EXAMPLE",
        "ENTERPRISE_NO_VERIFIED_TARGET",
        "ENTERPRISE_NON_PROSE",
        "EXCLUDED_BY_PLAN",
        "SECTION_ABSENT",
        "LEADIN_OF_WITHHELD_CONTENT",
    ]
    assert {cls.decision for cls in DEFERRAL_CLASSES} == {"BLOCK", "ADVISORY"}


def test_an_unverified_only_example_with_no_quick_start_blocks() -> None:
    """Sealed bundles 3d-Java, Slides-.NET, Words-.NET, Words-Python: every example unverified,
    so the candidate would publish without any Quick Start. An extraction gap, so it blocks."""
    facts = _facts(_example(1, "UNRESOLVED", unit=1), _unit(1, "code_block", "```python\nx()\n```"))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.code_block")]}, facts)
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "NO_VERIFIED_QUICK_START",
        "BLOCK",
        "EXTRACTING",
    )


def test_the_same_unverified_example_is_advisory_once_a_sibling_example_is_verified() -> None:
    """Control: a verified Quick Start exists, so the unverified block is only an unexecuted
    additional example and withholding it is the truth-safe result."""
    facts = _facts(
        _example(1, "UNRESOLVED", unit=1),
        _example(2, "SUPPORTED"),
        _unit(1, "code_block", "```python\nx()\n```"),
    )
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.code_block")]}, facts)
    )
    assert (finding.class_id, finding.decision) == ("UNVERIFIED_EXAMPLE", "ADVISORY")


def test_an_internal_governance_reference_is_advisory_and_never_public() -> None:
    """Sealed Words-.NET: a paragraph pointing at AGENTS.md, repository-internal detail."""
    facts = _facts(_unit(1, "paragraph", "Test gold files are documented in AGENTS.md."))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.paragraph")]}, facts)
    )
    assert (finding.class_id, finding.decision) == ("INTERNAL_DETAIL", "ADVISORY")


def test_a_build_command_with_no_build_test_asset_blocks() -> None:
    """Sealed Cells-.NET, Cells-Cpp, Words-.NET: the upstream documents a build path that the
    extractor never recorded as a build_test_asset, so Development and Testing cannot render."""
    facts = _facts(_unit(1, "code_block", "```bash\ndotnet build Solution.sln\n```"))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.code_block")]}, facts)
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "BUILD_TEST_PATH_UNRECORDED",
        "BLOCK",
        "EXTRACTING",
    )


def test_a_build_command_is_not_unrecorded_once_its_section_renders() -> None:
    """Control: with a build_test_asset recorded, Development and Testing renders, so the same
    command is no longer a missing-section cause (it then needs its own cause, or fails closed)."""
    build = Fact(
        "build_test_asset:solution",
        "build_test_asset",
        "Solution.sln",
        (Evidence("Solution.sln", None),),
    )
    facts = _facts(build, _unit(1, "code_block", "```bash\ndotnet build Solution.sln\n```"))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.code_block")]}, facts)
    )
    assert finding.class_id != "BUILD_TEST_PATH_UNRECORDED"


def test_licensing_notices_the_upstream_documents_without_a_record_block() -> None:
    """Sealed Aspose.PDF-Go: bundled OFL fonts and a Third-Party Notices heading, with no
    third_party_notices fact. Dropping attribution is a licensing risk, so it blocks."""
    facts = _facts(
        _unit(1, "paragraph", "The bundled fonts are licensed under the SIL Open Font License.")
    )
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.paragraph")]}, facts)
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "NOTICES_WITHOUT_RECORD",
        "BLOCK",
        "EXTRACTING",
    )


def test_an_unverified_example_with_a_quick_start_is_advisory() -> None:
    """Sealed Aspose.PDF-C++, Aspose.Slides-Java: the example did not execute, but the Quick Start
    renders, so withholding the block is an advisory outcome, never public."""
    facts = _facts(
        _example(1, "UNRESOLVED", unit=1),
        _example(2, "SUPPORTED"),
        _unit(1, "code_block", "```cpp\nrun();\n```"),
    )
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.code_block")]}, facts)
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "UNVERIFIED_EXAMPLE",
        "ADVISORY",
        None,
    )


def test_enterprise_relationship_text_without_a_verified_target_is_advisory() -> None:
    """Sealed Aspose.Cells-Go, Aspose.Words-Python: the Enterprise Edition link is not verified at
    this revision, so the relationship row cannot render it."""
    facts = _facts(_unit(1, "paragraph", "These limits do not apply to the Enterprise Edition."))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.paragraph")]}, facts)
    )
    assert (finding.class_id, finding.decision) == (
        "ENTERPRISE_NO_VERIFIED_TARGET",
        "ADVISORY",
    )


def test_an_enterprise_table_or_list_with_a_verified_target_is_advisory() -> None:
    """Sealed Aspose.Slides-Java: the editions table and list have no row to render in; the
    verified target already carries the relationship."""
    target = Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        "https://example.com/enterprise",
        (Evidence("README.md", None),),
    )
    facts = _facts(target, _unit(1, "table", "| Edition | Repo |\n|---|---|\n| Enterprise | x |"))
    deferred = _deferred(
        "inherited_unit:001.table", "The table is moved to the enterprise_relationship section."
    )
    finding = _only(review_deferrals({"dispositions": [deferred]}, facts))
    assert (finding.class_id, finding.decision) == ("ENTERPRISE_NON_PROSE", "ADVISORY")


def test_a_lead_in_to_examples_that_the_plan_already_shows_is_advisory() -> None:
    """Sealed Aspose.Cells-Cpp, Aspose.Words-.NET: the plan's quick starts consume every verified
    example, so Additional Examples is excluded at this plan and its lead-in is withheld."""
    facts = _facts(
        _example(1, "SUPPORTED", unit=2),
        _unit(1, "paragraph", "A few more examples follow."),
        _unit(2, "code_block", "```python\na()\n```"),
    )
    plan = {"quick_start_example_id": "example:001", "second_quick_start_example_id": None}
    deferred = _deferred(
        "inherited_unit:001.paragraph", "Belongs in the additional_examples section."
    )
    finding = _only(review_deferrals({"dispositions": [deferred]}, facts, plan))
    assert (finding.class_id, finding.decision) == ("EXCLUDED_BY_PLAN", "ADVISORY")


def test_a_placement_into_a_section_absent_at_this_revision_is_advisory() -> None:
    """Sealed Aspose.Words-.NET: a paragraph whose named section does not render here. Supported
    prose with no public home, recorded for the reviewer."""
    facts = _facts(_unit(1, "paragraph", "Shared setup text."))
    deferred = _deferred(
        "inherited_unit:001.paragraph", "Supports the additional examples section."
    )
    finding = _only(review_deferrals({"dispositions": [deferred]}, facts))
    assert (finding.class_id, finding.decision) == ("SECTION_ABSENT", "ADVISORY")


def test_a_colon_lead_in_whose_block_was_withheld_is_advisory() -> None:
    """Sealed Aspose.Cells-Rust and Words-Python: a sentence promising the block that follows it,
    withheld with that block so the document never promises absent content."""
    facts = _facts(
        _unit(1, "paragraph", "Typical usage, with the options below:"),
        _unit(2, "code_block", "```python\nrun()\n```"),
    )
    dispositions = {
        "dispositions": [
            _deferred("inherited_unit:001.paragraph", "Preserved."),
            _kept("inherited_unit:002.code_block"),
        ]
    }
    finding = _only(review_deferrals(dispositions, facts))
    assert (finding.class_id, finding.decision) == ("LEADIN_OF_WITHHELD_CONTENT", "ADVISORY")


def test_an_unmatched_cause_fails_closed() -> None:
    """Negative control: a deferral no registered class recognises blocks until one is added."""
    facts = _facts(_unit(1, "paragraph", "Plain prose with nothing that names a cause."))
    finding = _only(
        review_deferrals({"dispositions": [_deferred("inherited_unit:001.paragraph")]}, facts)
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "UNCLASSIFIED",
        "BLOCK",
        "RECONCILING",
    )


def test_a_non_deferred_disposition_is_never_reviewed() -> None:
    facts = _facts(_unit(1, "paragraph", "A verified paragraph."))
    kept = {"dispositions": [_kept("inherited_unit:001.paragraph", "VERIFIED_PRESERVE")]}
    assert review_deferrals(kept, facts) == []


@pytest.mark.parametrize(
    ("unit_text", "rationale"),
    [
        ("Test gold files are documented in AGENTS.md.", "Preserved."),
        ("Shared setup text.", "Supports the additional examples section."),
    ],
)
def test_an_advisory_deferral_never_reaches_the_public_text(unit_text: str, rationale: str) -> None:
    """ADVISORY is a record, not a placement: the composer's own placement path renders only
    PLACED dispositions, so neither the unit nor its text can appear in the public README."""
    facts = _facts(_unit(1, "paragraph", unit_text), _unit(2, "paragraph", "Kept verbatim."))
    dispositions = {
        "dispositions": [
            _deferred("inherited_unit:001.paragraph", rationale),
            {
                "unit_id": "inherited_unit:002.paragraph",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "opening",
                "fact_ids": [],
                "rationale": "Kept.",
            },
        ]
    }
    plan: dict[str, Any] = {"sections": [{"section_id": "opening", "include": True}]}
    decisions = placements(plan, dispositions, facts, "python")
    assert [d.unit_id for d in decisions] == ["inherited_unit:002.paragraph"]
    rendered = " ".join(text for texts in placed_texts(decisions).values() for text in texts)
    assert unit_text not in rendered
    assert review_deferrals(dispositions, facts)[0].decision == "ADVISORY"
