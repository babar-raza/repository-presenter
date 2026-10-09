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


def _unit(number: int, kind: str, value: str, section: str | None = None) -> Fact:
    """An inherited unit; ``section`` is the heading path the extractor records for it
    (evidence/facts/inherited.py: ``attributes["section"]``)."""
    return Fact(
        f"inherited_unit:{number:03d}.{kind}",
        "inherited_unit",
        value,
        (Evidence("README.md", None),),
        attributes={"section": section} if section else None,
    )


def _fact(fact_kind: str, key: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(
        f"{fact_kind}:{key}",
        fact_kind,
        value,
        (Evidence("manifest", None),),
        polarity=polarity,  # type: ignore[arg-type]
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


def test_the_registry_holds_exactly_the_fifteen_real_causes() -> None:
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
        "AT_A_GLANCE_COVERED_BY_DIAGRAM",
        "INSTALL_STEPS_UNVERIFIED",
        "LEADIN_OF_WITHHELD_CONTENT",
        "COMMAND_BLOCK_WITHHELD",
        "API_LISTING_COVERED_BY_CORE_API",
        "NO_EVIDENCE_EITHER_WAY",
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


# --- G7-W12 (REG-18): the UNCLASSIFIED family, from the 2026-10-09 re-seal pass's real units. ---
# Each fixture reproduces a unit the pipeline actually deferred (repository, unit id, source text,
# the section the extractor recorded for it, and the rationale the model wrote). The class is
# matched from what the bundle keeps that is NOT the model's prose about a different disposition:
# the unit's own source section, the facts, and the sibling dispositions.

_GLANCE = "Aspose.Slides FOSS for .NET > At a glance"


def _classify(facts: FactsDocument, entry: dict[str, Any], *rest: dict[str, Any]) -> Any:
    findings = review_deferrals({"dispositions": [entry, *rest]}, facts)
    return next(f for f in findings if f.unit_id == entry["unit_id"])


def test_a_caption_deferred_out_of_the_at_a_glance_section_is_advisory() -> None:
    """Slides-.NET 86c441b5 inherited_unit:007: the paragraph under 'At a glance' the model
    placed there. README_CONTRACT.md row 6 makes that section exactly one Mermaid fence, so the
    normalize fold defers a unit placed there with no citation, rewriting its disposition and
    leaving the model's now-contradicting rationale ('placed under the at_a_glance section')."""
    facts = _facts(
        _unit(
            7,
            "paragraph",
            "The diagram is an overview, not a contract. Each box is expanded under "
            "[What it can do](#what-it-can-do).",
            _GLANCE,
        )
    )
    deferred = _deferred(
        "inherited_unit:007.paragraph",
        "The paragraph is retained as written and placed under the at_a_glance section.",
    )
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision) == ("AT_A_GLANCE_COVERED_BY_DIAGRAM", "ADVISORY")


def test_the_same_caption_elsewhere_is_not_an_at_a_glance_deferral() -> None:
    """Control: the class is chosen by the unit's source section, not by its wording."""
    facts = _facts(
        _unit(7, "paragraph", "The diagram is an overview.", "Aspose.Slides FOSS for .NET > Usage")
    )
    deferred = _deferred("inherited_unit:007.paragraph", "Retained as written.")
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision) == ("UNCLASSIFIED", "BLOCK")


def test_install_steps_the_registry_cannot_verify_are_advisory_not_unclassified() -> None:
    """Cells-TypeScript fc186507 units 011 and 013: the package is not on npm (install_command
    CONTRADICTED), so the Installation row has nothing to render and normalize defers the
    superseded heading and the clone-and-install block with the model's stale rationale."""
    facts = _facts(
        _fact("install_command", "npm", "npm install excel-cells", "CONTRADICTED"),
        _fact("build_test_asset", "tests", "tests/"),
        _unit(11, "heading", "## Installation", "Aspose.Cells FOSS for TypeScript"),
        _unit(
            13,
            "code_block",
            "```bash\ngit clone https://example.com/x.git\ncd x\nnpm install\n```",
            "Aspose.Cells FOSS for TypeScript > Installation",
        ),
    )
    heading = _deferred(
        "inherited_unit:011.heading",
        "The Installation heading is rendered by the deterministic installation section.",
    )
    block = _deferred(
        "inherited_unit:013.code_block",
        "The git clone and npm install commands are verified and placed in the installation "
        "section.",
    )
    block["fact_ids"] = ["install_command:npm"]
    assert _classify(facts, heading, block).class_id == "INSTALL_STEPS_UNVERIFIED"
    assert _classify(facts, block, heading).class_id == "INSTALL_STEPS_UNVERIFIED"
    assert _classify(facts, heading, block).decision == "ADVISORY"


def test_installation_content_is_not_unverifiable_while_an_install_command_is_verified() -> None:
    """Control: with a SUPPORTED install_command the Installation row renders, so the same
    deferred prose is a different cause (here none: it fails closed)."""
    facts = _facts(
        _fact("install_command", "pip", "pip install widget"),
        _unit(13, "paragraph", "Build it from source first.", "Widget > Installation"),
    )
    finding = _classify(facts, _deferred("inherited_unit:013.paragraph", "Placed in installation."))
    assert (finding.class_id, finding.decision) == ("UNCLASSIFIED", "BLOCK")


def test_an_editions_table_beside_units_folded_into_the_enterprise_row_is_advisory() -> None:
    """Slides-Java 620a2614 inherited_unit:082: the 'Choosing an Edition' table. Its neighbours
    in the same source section were folded into the Enterprise row (they cite the enterprise
    fact); a table has no row there. The model's rationale says 'edition', not 'enterprise', so
    the rationale alone never recognised it."""
    target = Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        "https://example.com/enterprise",
        (Evidence("README.md", None),),
    )
    section = "Aspose.Slides FOSS for Java > Documentation > Choosing an Edition"
    facts = _facts(
        target,
        _unit(81, "paragraph", "There are four editions.", section),
        _unit(82, "table", "| | .NET | Java |\n|---|---|---|\n| Save | yes | yes |", section),
    )
    folded = {
        "unit_id": "inherited_unit:081.paragraph",
        "disposition": "SUPERSEDE_REDUNDANT",
        "destination_section": "scope_limitations",
        "fact_ids": [ENTERPRISE_FACT_ID],
        "rationale": "Moved to the enterprise relationship.",
    }
    table = _deferred(
        "inherited_unit:082.table", "The edition comparison table is supported by the links."
    )
    finding = _classify(facts, table, folded)
    assert (finding.class_id, finding.decision) == ("ENTERPRISE_NON_PROSE", "ADVISORY")


def test_a_table_with_no_enterprise_sibling_and_no_enterprise_rationale_still_blocks() -> None:
    """Control: the target exists, but nothing ties this table to the Enterprise row."""
    target = Fact(
        ENTERPRISE_FACT_ID,
        "link_target",
        "https://example.com/enterprise",
        (Evidence("README.md", None),),
    )
    facts = _facts(target, _unit(82, "table", "| a | b |\n|---|---|\n| 1 | 2 |", "W > Docs"))
    finding = _classify(facts, _deferred("inherited_unit:082.table", "A comparison table."))
    assert (finding.class_id, finding.decision) == ("UNCLASSIFIED", "BLOCK")


def test_a_build_command_withheld_while_build_facts_exist_blocks_at_reconciliation() -> None:
    """3D-.NET 52b0f00e inherited_unit:067: `dotnet build src/converter/Converter.csproj` under
    Development, build_test_asset SUPPORTED. The first attempt said OMIT_UNSUPPORTED (which
    normalize keeps in Development and Testing); the re-ask template tells the model to answer
    DEFER_UNRESOLVED when it cannot cite, and normalize has no such rule for a DEFER. A command
    block is never withheld while build or install facts exist (placement_errors says so for an
    OMIT): this is an S4 defect, so it blocks, naming its stage."""
    facts = _facts(
        _fact("build_test_asset", "docs", "docs/"),
        _unit(
            67,
            "code_block",
            "```bash\ndotnet build src/converter/Converter.csproj\n```",
            "Aspose.3D FOSS for .NET > Development",
        ),
    )
    deferred = _deferred(
        "inherited_unit:067.code_block",
        "No fact supports or contradicts the build command for the console converter tool.",
    )
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision, finding.stage) == (
        "COMMAND_BLOCK_WITHHELD",
        "BLOCK",
        "RECONCILING",
    )


def test_a_cited_command_deferral_is_not_the_withheld_command_defect() -> None:
    """Control: a deferral that cites a fact was a decision about that fact, not the uncited
    relabel the rule targets."""
    facts = _facts(
        _fact("build_test_asset", "docs", "docs/"),
        _unit(67, "code_block", "```bash\nmake\n```", "P > Development"),
    )
    deferred = _deferred("inherited_unit:067.code_block", "Deferred.")
    deferred["fact_ids"] = ["build_test_asset:docs"]
    assert _classify(facts, deferred).class_id != "COMMAND_BLOCK_WITHHELD"


def test_a_claim_with_no_fact_either_way_is_advisory_when_it_names_no_verified_symbol() -> None:
    """3D-Python 65b1f577 inherited_unit:075: the release procedure. The model searched the
    SUPPORTED and CONTRADICTED facts, cited none and said so; the unit spells no verified symbol,
    so nothing in the facts contradicts that. DEFER_UNRESOLVED means exactly this
    (prompts/source_reconciliation.yaml): withheld, listed for the owner, never rendered."""
    facts = _facts(
        _fact("public_symbol", "widget.scene", "widget.Scene"),
        _fact("build_test_asset", "tests", "tests/"),
        _unit(
            75,
            "paragraph",
            "Releases are cut by bumping `version` in `setup.py` and tagging `v<version>`.",
            "Widget > Development",
        ),
    )
    deferred = _deferred(
        "inherited_unit:075.paragraph",
        "No fact confirms the release procedure details; the publish workflow is not verified.",
    )
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision) == ("NO_EVIDENCE_EITHER_WAY", "ADVISORY")


def test_the_no_evidence_attestation_is_refused_when_the_unit_spells_a_verified_symbol() -> None:
    """Negative control: a unit that spells a SUPPORTED public symbol verbatim falsifies 'no fact
    supports it' (the packet shows a bounded sample of symbols, the facts hold all of them), so
    the attestation is not accepted and the deferral stays an unclassified, blocking cause."""
    facts = _facts(
        _fact("public_symbol", "widget.scene", "widget.Scene"),
        _unit(75, "paragraph", "Call `widget.Scene` to open a file.", "Widget > Usage"),
    )
    deferred = _deferred(
        "inherited_unit:075.paragraph", "No fact in the provided list supports this."
    )
    assert _classify(facts, deferred).decision == "BLOCK"


def test_a_no_evidence_attestation_that_cites_a_fact_is_not_an_attestation() -> None:
    """Control: if the model cited a fact it did find evidence; its prose cannot also say none."""
    facts = _facts(
        _fact("public_symbol", "widget.scene", "widget.Scene"),
        _unit(75, "paragraph", "Releases are cut by tagging.", "Widget > Development"),
    )
    deferred = _deferred("inherited_unit:075.paragraph", "No fact confirms the procedure.")
    deferred["fact_ids"] = ["public_symbol:widget.scene"]
    assert _classify(facts, deferred).decision == "BLOCK"


def test_an_api_listing_under_api_reference_naming_verified_symbols_is_advisory() -> None:
    """Slides-Python 4e63447b inherited_unit:095.001: `Chart` / `chart_data -> ChartData`, under
    'API Reference > Charts'. The facts hold the symbols (slides_foss.charts.Chart ...); the
    packet showed the model a bounded sample, so it answered 'no fact in the provided list'. Its
    sibling lists in other batches were SUPERSEDE_REDUNDANT into api_reference
    (README_CONTRACT.md row 14: the Core API table renders from the verified symbols)."""
    facts = _facts(
        _fact("public_symbol", "slides_foss.charts.chart", "slides_foss.charts.Chart"),
        _fact("public_symbol", "slides_foss.charts.chartdata", "slides_foss.charts.ChartData"),
        _unit(
            95,
            "list",
            "- `Chart`\n  - `chart_data -> ChartData`, `chart_title -> ChartTitle`",
            "Aspose.Slides FOSS for Python > API Reference > Charts",
        ),
    )
    deferred = _deferred(
        "inherited_unit:095.list",
        "No fact in the provided list supports or contradicts the inclusion of this chart list.",
    )
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision) == ("API_LISTING_COVERED_BY_CORE_API", "ADVISORY")


def test_an_api_listing_naming_no_verified_symbol_is_not_covered_by_the_core_api() -> None:
    """Control: nothing in the Core API table would cover a listing of symbols the facts do not
    hold (PDF-Java's TiffDevice shape) - it is a no-evidence deferral, a different cause."""
    facts = _facts(
        _fact("public_symbol", "pdf.document", "pdf.Document"),
        _unit(
            123,
            "list",
            "- `TiffDevice`\n  - `process(Document, OutputStream)`",
            "Aspose.PDF FOSS for Java > API Reference",
        ),
    )
    deferred = _deferred(
        "inherited_unit:123.list", "No fact in the provided list confirms or denies its presence."
    )
    assert _classify(facts, deferred).class_id == "NO_EVIDENCE_EITHER_WAY"


def test_a_font_word_in_an_api_listing_is_not_a_licensing_notice() -> None:
    """Slides-Python 4e63447b inherited_unit:101.006: `FontScheme` / `major -> Fonts`. The bare
    word 'font' blocked it as unrecorded third-party notices (it also blocked a Mermaid label in
    Cells-TypeScript and an examples row naming a Font class). A font is a notice only when the
    text says it is bundled, embedded or redistributed."""
    facts = _facts(
        _fact("public_symbol", "slides_foss.fontscheme", "slides_foss.FontScheme"),
        _unit(
            101,
            "list",
            "- `FontScheme`\n  - `major -> Fonts`, `minor -> Fonts`, `name`",
            "Aspose.Slides FOSS for Python > API Reference > Styling",
        ),
    )
    deferred = _deferred(
        "inherited_unit:101.list", "No fact in the provided list supports or contradicts this."
    )
    finding = _classify(facts, deferred)
    assert finding.class_id != "NOTICES_WITHOUT_RECORD"
    assert (finding.class_id, finding.decision) == ("API_LISTING_COVERED_BY_CORE_API", "ADVISORY")


def test_bundled_fonts_without_a_notices_record_still_block() -> None:
    """Negative control for the tightening: bundled font files with no third_party_notices fact
    remain a licensing risk (aspose-pdf-foss Go), with or without the word 'licensed'."""
    facts = _facts(_unit(88, "paragraph", "The embedded fonts ship with the library."))
    finding = _classify(facts, _deferred("inherited_unit:088.paragraph"))
    assert (finding.class_id, finding.decision, finding.stage) == (
        "NOTICES_WITHOUT_RECORD",
        "BLOCK",
        "EXTRACTING",
    )


def test_a_development_paragraph_with_no_build_asset_is_the_unrecorded_path_cause() -> None:
    """Cells-Cpp 9f852d0f inherited_unit:061: the GoogleTest paragraph under 'Development'. Its
    tests sit one directory down (Aspose.Cells.Foss.Cpp/tests/), which asset_facts did not see, so
    no build_test_asset exists and Development and Testing cannot render. The model's rationale
    ('retained as written') says nothing; the unit's source section does."""
    facts = _facts(
        _unit(
            61,
            "paragraph",
            "This links the `aspose_cells_foss` library and uses `FetchContent` to download "
            "GoogleTest.",
            "Aspose.Cells FOSS for C++ > Development",
        )
    )
    finding = _classify(
        facts, _deferred("inherited_unit:061.paragraph", "The paragraph is retained as written.")
    )
    assert (finding.class_id, finding.decision, finding.stage) == (
        "BUILD_TEST_PATH_UNRECORDED",
        "BLOCK",
        "EXTRACTING",
    )


def test_a_sentence_that_only_mentions_a_verified_class_name_is_still_a_no_evidence_claim() -> None:
    """Slides-.NET 86c441b5 (live re-run 2026-10-10) inherited_unit:028: 'A new `Presentation` is a
    13-part package ... a slide size of `9144000 x 6858000` EMU'. The model cited nothing and said
    'No fact supports the slide size claim'. `Presentation` is a verified class, but a class name
    inside a sentence about EMU constants verifies none of the constants, so a bare name does not
    falsify the attestation in prose (it does in a listing, where the name is the subject)."""
    facts = _facts(
        _fact(
            "public_symbol", "aspose.slides.foss.presentation", "Aspose.Slides.Foss.Presentation"
        ),
        _unit(
            28,
            "paragraph",
            "A new `Presentation` is a 13-part package with one slide and a slide size of "
            "`9144000 x 6858000` EMU.",
            "Aspose.Slides FOSS for .NET > Quick start",
        ),
    )
    deferred = _deferred(
        "inherited_unit:028.paragraph",
        "No fact supports the slide size claim; it is unsupported and cannot be deferred to a "
        "section.",
    )
    finding = _classify(facts, deferred)
    assert (finding.class_id, finding.decision) == ("NO_EVIDENCE_EITHER_WAY", "ADVISORY")
