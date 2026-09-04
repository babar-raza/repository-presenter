"""Placements deterministic code cannot honour fold into the disposition it can."""

from __future__ import annotations

from repository_presenter.components.readme.reconciliation.dispositions import (
    code_units_by_polarity,
    normalize,
    placement_errors,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument


def _fact(
    fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", detail: str = ""
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("README.md", detail or None),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    "org/Aspose.Widget-FOSS-for-Python",
    "a" * 40,
    (
        _fact("identity:repository", "identity", "org/Aspose.Widget-FOSS-for-Python"),
        _fact("format:output.glb", "format", ".glb"),
        _fact(
            "example:001",
            "example",
            "open('in.obj')",
            "UNRESOLVED",
            "lines 5-7; python fence; unit inherited_unit:003.code_block",
        ),
        _fact("link_target:001", "link_target", "https://products.aspose.com/widget/python/"),
        _fact("inherited_unit:002.paragraph", "inherited_unit", "See the Enterprise Edition."),
        _fact("inherited_unit:003.code_block", "inherited_unit", "```python\nopen('in.obj')\n```"),
        _fact("inherited_unit:005.code_block", "inherited_unit", "```mermaid\ngraph LR\n```"),
        _fact("inherited_unit:006.code_block", "inherited_unit", "```mermaid\ngraph TD\n```"),
    ),
)


def _entry(
    unit: str, disposition: str, destination: str | None, *fact_ids: str
) -> dict[str, object]:
    return {
        "unit_id": unit,
        "disposition": disposition,
        "destination_section": destination,
        "fact_ids": list(fact_ids),
        "rationale": "because",
    }


def test_unrenderable_placements_are_deferred_or_superseded() -> None:
    assert code_units_by_polarity(FACTS, "UNRESOLVED") == {
        "inherited_unit:003.code_block": "example:001"
    }
    output = {
        "dispositions": [
            _entry("inherited_unit:003.code_block", "VERIFIED_PRESERVE", "quick_start"),
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "enterprise_relationship",
                "link_target:001",
            ),
            _entry(
                "inherited_unit:005.code_block",
                "VERIFIED_PRESERVE",
                "at_a_glance",
                "format:output.glb",
            ),
            _entry("inherited_unit:006.code_block", "VERIFIED_PRESERVE", "at_a_glance"),
        ]
    }
    assert normalize(output, FACTS) == []
    folded = {entry["unit_id"]: entry for entry in output["dispositions"]}
    assert folded["inherited_unit:003.code_block"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:003.code_block"]["destination_section"] is None
    assert folded["inherited_unit:003.code_block"]["fact_ids"] == ["example:001"]
    assert folded["inherited_unit:002.paragraph"]["disposition"] == "DEFER_UNRESOLVED"
    assert folded["inherited_unit:002.paragraph"]["destination_section"] is None
    assert folded["inherited_unit:002.paragraph"]["fact_ids"] == ["link_target:001"]
    assert folded["inherited_unit:005.code_block"]["disposition"] == "SUPERSEDE_REDUNDANT"
    assert folded["inherited_unit:005.code_block"]["destination_section"] is None
    assert folded["inherited_unit:006.code_block"]["disposition"] == "DEFER_UNRESOLVED"
    assert placement_errors(output, FACTS) == []


def test_enterprise_prose_is_superseded_by_row_18_once_the_live_target_is_verified() -> None:
    # Row 18 is the shell's closing paragraph of Scope and Limitations: inherited Enterprise
    # prose placed there is superseded by it citing the target, and a banner row placed there
    # has no row yet at this revision, so it is deferred rather than rendered headless.
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_MOVE",
                "enterprise_relationship",
                "link_target:001",
            ),
            _entry("inherited_unit:003.badge_row", "VERIFIED_MOVE", "enterprise_relationship"),
        ]
    }
    target = Fact(
        "link_target:product.enterprise",
        "link_target",
        "https://products.aspose.com/widget/python/",
        (Evidence("https://products.aspose.com/widget/python/", "HTTP 200; enterprise target"),),
        attributes={"role": "enterprise", "level": "platform"},
    )
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, target))
    assert normalize(output, facts) == []
    prose, banner = output["dispositions"]
    assert prose["disposition"] == "SUPERSEDE_REDUNDANT"
    assert prose["destination_section"] == "scope_limitations"
    assert prose["fact_ids"] == ["link_target:001", "link_target:product.enterprise"]
    assert banner["disposition"] == "DEFER_UNRESOLVED"
    assert banner["destination_section"] is None


def test_a_placement_into_at_a_glance_is_covered_by_the_diagram_or_deferred() -> None:
    # README_CONTRACT.md row 6: At a Glance is exactly one Mermaid fence and nothing else, so a
    # paragraph placed there is superseded by the diagram when it cites facts and deferred when
    # it cites none, while a heading, which the shell owns and never renders verbatim, stands.
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "at_a_glance"),
            _entry(
                "inherited_unit:004.paragraph", "VERIFIED_MOVE", "at_a_glance", "format:output.stl"
            ),
            _entry("inherited_unit:007.heading", "VERIFIED_PRESERVE", "at_a_glance"),
        ]
    }
    assert normalize(output, FACTS) == []
    bare, cited, heading = output["dispositions"]
    assert (bare["disposition"], bare["destination_section"]) == ("DEFER_UNRESOLVED", None)
    assert (cited["disposition"], cited["destination_section"]) == ("SUPERSEDE_REDUNDANT", None)
    assert heading["disposition"] == "VERIFIED_PRESERVE"


def test_a_verbatim_placement_into_an_absent_section_is_sent_back_for_re_routing() -> None:
    # No third-party notices are verified, so that section cannot appear at this revision: a
    # paragraph placed there is re-routed by the reconciler (README_CONTRACT.md section 3).
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "third_party_notices"),
        ]
    }
    assert normalize(output, FACTS) == [
        "inherited_unit:002.paragraph: section third_party_notices does not appear in this "
        "candidate (its condition does not hold at this revision); place the unit in another "
        "section or choose DEFER_UNRESOLVED"
    ]
    assert output["dispositions"][0]["disposition"] == "VERIFIED_PRESERVE"


def test_a_unit_may_be_superseded_by_a_planned_sections_own_content() -> None:
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "SUPERSEDE_REDUNDANT", "key_capabilities"),
            _entry("inherited_unit:003.code_block", "SUPERSEDE_REDUNDANT", None),
        ]
    }
    assert placement_errors(output, FACTS) == [
        "inherited_unit:003.code_block: SUPERSEDE_REDUNDANT names the section whose content "
        "renders or covers the unit in destination_section, or cites at least one fact ID"
    ]


def test_a_supersession_by_an_absent_section_is_deferred_for_the_owner() -> None:
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:002.paragraph", "SUPERSEDE_REDUNDANT", "enterprise_relationship"
            ),
            _entry("inherited_unit:007.heading", "SUPERSEDE_REDUNDANT", "enterprise_relationship"),
        ]
    }
    assert normalize(output, FACTS) == []
    assert output["dispositions"][0]["disposition"] == "DEFER_UNRESOLVED"
    assert output["dispositions"][0]["destination_section"] is None
    assert output["dispositions"][1]["disposition"] == "SUPERSEDE_REDUNDANT"


def test_a_command_block_is_never_omitted_while_build_facts_exist() -> None:
    block = Fact(
        "inherited_unit:071.code_block",
        "inherited_unit",
        "```bash" + chr(10) + "python -m unittest discover tests/" + chr(10) + "```",
        (Evidence("README.md", "lines 1-3; code_block"),),
    )
    assets = Fact("build_test_asset:tests", "build_test_asset", "tests/", (Evidence("tests/"),))
    omitted = {"dispositions": [_entry("inherited_unit:071.code_block", "OMIT_UNSUPPORTED", None)]}
    with_assets = FactsDocument(
        FACTS.repository, FACTS.source_revision, (*FACTS.facts, block, assets)
    )
    without = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, block))
    assert placement_errors(omitted, with_assets) == [
        "inherited_unit:071.code_block: a command block is never OMIT_UNSUPPORTED while build "
        "or install facts exist (build_test_asset:tests); choose VERIFIED_PRESERVE into "
        "development_testing, or SUPERSEDE_REDUNDANT by installation for an install command"
    ]
    assert placement_errors(omitted, without) == []


def test_a_placed_code_block_whose_example_is_contradicted_folds_into_an_omission() -> None:
    failed = Fact(
        "example:002",
        "example",
        "boom()",
        (Evidence("README.md", "lines 9-9; python fence; unit inherited_unit:009.code_block"),),
        polarity="CONTRADICTED",
    )
    block = Fact(
        "inherited_unit:009.code_block",
        "inherited_unit",
        "```python" + chr(10) + "boom()" + chr(10) + "```",
        (Evidence("README.md"),),
    )
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, failed, block))
    output = {
        "dispositions": [
            _entry("inherited_unit:009.code_block", "VERIFIED_PRESERVE", "quick_start")
        ]
    }
    assert normalize(output, facts) == []
    assert output["dispositions"][0]["disposition"] == "OMIT_UNSUPPORTED"
    assert output["dispositions"][0]["destination_section"] is None
    assert output["dispositions"][0]["fact_ids"] == ["example:002"]


def test_an_omitted_command_block_folds_to_installation_or_development_and_testing() -> None:
    install = Fact(
        "inherited_unit:015.code_block",
        "inherited_unit",
        "```bash" + chr(10) + "pip install aspose-x-foss" + chr(10) + "```",
        (Evidence("README.md", "lines 20-22; code_block; under X > Installation"),),
    )
    tests_block = Fact(
        "inherited_unit:071.code_block",
        "inherited_unit",
        "```bash" + chr(10) + "python -m unittest discover tests/" + chr(10) + "```",
        (Evidence("README.md", "lines 80-82; code_block; under X > Development and Testing"),),
    )
    pip = Fact(
        "install_command:pip",
        "install_command",
        "pip install aspose-x-foss",
        (Evidence("setup.py", "manifest"), Evidence("pypi", "package registry: found")),
    )
    assets = Fact("build_test_asset:tests", "build_test_asset", "tests/", (Evidence("tests/"),))
    facts = FactsDocument(
        FACTS.repository, FACTS.source_revision, (*FACTS.facts, install, tests_block, pip, assets)
    )
    output = {
        "dispositions": [
            _entry("inherited_unit:015.code_block", "OMIT_UNSUPPORTED", None),
            _entry("inherited_unit:071.code_block", "OMIT_UNSUPPORTED", None),
        ]
    }
    assert normalize(output, facts) == []
    first, second = output["dispositions"]
    assert (first["disposition"], first["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "installation",
    )
    assert first["fact_ids"] == ["install_command:pip"]
    assert (second["disposition"], second["destination_section"]) == (
        "VERIFIED_PRESERVE",
        "development_testing",
    )
    assert second["fact_ids"] == ["build_test_asset:tests"]


def _verified_banner_facts() -> FactsDocument:
    image_url = "https://products.aspose.org/media/widget/python/banner-readme.png"
    homepage_url = "https://products.aspose.org/widget/python/"
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            Fact(
                "link_target:product.banner",
                "link_target",
                image_url,
                (Evidence(image_url, "HTTP 200"),),
            ),
            Fact(
                "link_target:product.homepage",
                "link_target",
                homepage_url,
                (Evidence(homepage_url, "HTTP 200"),),
            ),
        ),
    )


def _banner_placements() -> dict[str, object]:
    return {
        "dispositions": [
            _entry(
                "inherited_unit:003.badge_row",
                "VERIFIED_MOVE",
                "enterprise_relationship",
                "link_target:product.banner",
                "link_target:product.homepage",
            ),
            _entry("inherited_unit:009.image", "VERIFIED_PRESERVE", "banner"),
        ]
    }


def test_a_placed_banner_row_is_superseded_by_row_3_or_deferred_while_unresolved() -> None:
    # README_CONTRACT.md row 3 is shell-rendered from the verified illustration and homepage
    # facts; the inherited banner row, wherever the reconciler places it, is superseded by it.
    folded = _banner_placements()
    assert normalize(folded, _verified_banner_facts()) == []
    row, image = folded["dispositions"]  # type: ignore[misc]
    assert (row["disposition"], row["destination_section"]) == ("SUPERSEDE_REDUNDANT", "banner")
    assert row["fact_ids"] == ["link_target:product.banner", "link_target:product.homepage"]
    assert (image["disposition"], image["destination_section"]) == ("SUPERSEDE_REDUNDANT", "banner")
    # The folded output is what the store keeps and re-judges on reuse: it must hold again.
    assert normalize(folded, _verified_banner_facts()) == []
    deferred = _banner_placements()
    assert normalize(deferred, FACTS) == []
    entries = deferred["dispositions"]  # type: ignore[misc]
    assert [entry["disposition"] for entry in entries] == ["DEFER_UNRESOLVED"] * 2


def test_an_inherited_api_table_placed_into_the_reference_is_covered_by_the_verified_table() -> (
    None
):
    # README_CONTRACT.md row 14: the Core API table is deterministic from the symbol facts, so
    # an inherited table placed into api_reference is superseded by it; prose placed there stays.
    output = {
        "dispositions": [
            _entry("inherited_unit:060.table", "VERIFIED_PRESERVE", "api_reference"),
            _entry("inherited_unit:057.paragraph", "VERIFIED_PRESERVE", "api_reference"),
        ]
    }
    assert normalize(output, FACTS) == []
    table, prose = output["dispositions"]
    assert (table["disposition"], table["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "api_reference",
    )
    assert (prose["disposition"], prose["destination_section"]) == (
        "VERIFIED_PRESERVE",
        "api_reference",
    )


def test_an_inherited_paragraph_placed_into_the_opening_is_covered_by_the_rewrite() -> None:
    # README_CONTRACT.md row 4: the opening is one authored paragraph, so an inherited paragraph
    # placed there only repeats it; a heading placed there is the shell's anyway and stands.
    output = {
        "dispositions": [
            _entry(
                "inherited_unit:002.paragraph",
                "VERIFIED_PRESERVE",
                "opening",
                "identity:repository",
            ),
            _entry("inherited_unit:001.heading", "VERIFIED_PRESERVE", "opening"),
        ]
    }
    assert normalize(output, FACTS) == []
    paragraph, heading = output["dispositions"]
    assert (paragraph["disposition"], paragraph["destination_section"]) == (
        "SUPERSEDE_REDUNDANT",
        "opening",
    )
    assert heading["disposition"] == "VERIFIED_PRESERVE"
