"""Placements deterministic code cannot honour fold into the disposition it can."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.reconciliation.dispositions import (
    code_units_by_polarity,
    normalize,
    placement_errors,
    reconciliation_batches,
    reconciliation_schema,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT


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


def test_a_verbatim_placement_into_an_absent_section_is_deferred_not_dropped() -> None:
    """No third-party notices are verified, so that section cannot appear at this revision.

    README_CONTRACT.md section 3 lets an excluded destination re-route or fail closed, and no
    re-ask can honour a placement no plan may include. Measured 2026-09-06: Aspose.Cells and
    Aspose.Words for .NET each routed build and test snippets into development_testing, whose
    condition is false because neither records a build_test_asset, and both candidates died on
    it. The unit is deferred for the owner, exactly as a supersession by an absent section is.
    """
    output = {
        "dispositions": [
            _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "third_party_notices"),
        ]
    }
    assert normalize(output, FACTS) == []
    deferred = output["dispositions"][0]
    assert deferred["disposition"] == "DEFER_UNRESOLVED"
    assert deferred["destination_section"] is None
    # Mutation control: a destination that does appear is left exactly as the reconciler chose.
    present = _entry("inherited_unit:002.paragraph", "VERIFIED_PRESERVE", "opening")
    kept = {"dispositions": [present]}
    assert normalize(kept, FACTS) == []
    assert kept["dispositions"][0]["destination_section"] == "opening"


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


def test_a_non_install_command_defers_when_development_and_testing_has_nothing() -> None:
    """An install fact alone does not mean Development and Testing renders.

    Measured 2026-09-06: Aspose.Words and Aspose.Cells for .NET both have `install_command:dotnet`
    SUPPORTED and zero `build_test_asset` facts, so a maintainer's `dotnet test` block was routed
    to `development_testing` by `install_ids` alone - a section whose own condition
    (`bool(facts.by_kind("build_test_asset"))`) is false - and the candidate died on the same
    placement `plan_checks` already knows to defer.
    """
    tests_block = Fact(
        "inherited_unit:071.code_block",
        "inherited_unit",
        "```bash" + chr(10) + "dotnet test" + chr(10) + "```",
        (Evidence("README.md", "lines 80-82; code_block; under X > Development and Testing"),),
    )
    dotnet = Fact(
        "install_command:dotnet",
        "install_command",
        "dotnet add package Aspose.Widget",
        (Evidence("Widget.csproj", "manifest"), Evidence("nuget", "package registry: found")),
    )
    facts = FactsDocument(
        FACTS.repository, FACTS.source_revision, (*FACTS.facts, tests_block, dotnet)
    )
    output = {"dispositions": [_entry("inherited_unit:071.code_block", "OMIT_UNSUPPORTED", None)]}
    assert normalize(output, facts) == []
    entry = output["dispositions"][0]
    assert entry["disposition"] == "DEFER_UNRESOLVED"
    assert entry["destination_section"] is None


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


def test_the_schema_names_exactly_this_readmes_inherited_units() -> None:
    # The canary's reconciliation paired the right ordinals with the wrong type suffixes and lost
    # the transaction: "unknown inherited unit inherited_unit:037.paragraph ... no disposition for
    # inherited units: inherited_unit:037.code_block". The code knows the units exactly
    # (RESEARCH_AND_GUIDELINES.md section 27.5 D1, cause RC1 in 27.2).
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    batch = list(FACTS.by_kind("inherited_unit"))
    schema = reconciliation_schema(loaded, batch, FACTS, {})
    units = [fact.id for fact in FACTS.by_kind("inherited_unit")]
    dispositions = schema["properties"]["dispositions"]
    assert dispositions["minItems"] == dispositions["maxItems"] == len(units)
    assert dispositions["items"]["properties"]["unit_id"] == {"type": "string", "enum": units}
    assert "maxItems" not in loaded.manifest.output.schema_["properties"]["dispositions"]

    def entry(unit_id: str) -> dict[str, Any]:
        return {
            "unit_id": unit_id,
            "disposition": "OMIT_UNSUPPORTED",
            "destination_section": None,
            "fact_ids": [],
            "rationale": "r",
        }

    validator = Draft202012Validator(schema)
    invented = [*units[:-1], units[-1].rsplit(".", 1)[0] + ".paragraph"]
    assert [
        error.json_path
        for error in validator.iter_errors({"dispositions": [entry(u) for u in invented]})
    ] == [f"$.dispositions[{len(units) - 1}].unit_id"]
    short = {"dispositions": [entry(u) for u in units[:-1]]}
    assert [error.json_path for error in validator.iter_errors(short)] == ["$.dispositions"]
    assert list(validator.iter_errors({"dispositions": [entry(u) for u in units]})) == []


def _inherited_units_facts(count: int) -> FactsDocument:
    # A minimal document of exactly `count` inherited_unit facts and nothing else -
    # reconciliation_schema() reads only by_kind("inherited_unit"), and FACTS's own small,
    # fixed baseline set would otherwise skew a 10x ratio comparison at these small counts.
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        tuple(
            _fact(f"inherited_unit:{i:05}.paragraph", "inherited_unit", f"Paragraph {i}.")
            for i in range(count)
        ),
    )


def test_each_batchs_own_schema_is_bounded_to_its_own_units_not_the_repositorys_total() -> None:
    """PHASE0/G: the real fix for J1/G1a's own finding ('dispositions.minItems/maxItems/unit_id
    enum are built directly from every inherited_unit fact, no cap') is that reconciliation_schema()
    can no longer even be called against the repository's own full unit set - batch_units is
    required, and every real caller (rounds.py) gets it from reconciliation_batches(), which
    itself bounds each batch to _RECONCILIATION_BATCH units regardless of the repository's own
    total (test_dispositions.py's own test_reconciliation_batches_bounds_each_batchs_own_size
    proves that half directly). What this test proves is the two functions compose correctly:
    every batch reconciliation_batches() produces gets a schema whose own minItems/maxItems/enum
    is sized to exactly that batch, in both a 200-unit and a 2000-unit repository - the schema
    itself never grows past _RECONCILIATION_BATCH regardless of total repository size, closing
    c575035's own bug class for real rather than moving the marker."""
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    for total in (200, 2000):
        facts = _inherited_units_facts(total)
        batches = reconciliation_batches(facts)
        for _, batch_units in batches:
            schema = reconciliation_schema(loaded, batch_units, facts, {})
            dispositions = schema["properties"]["dispositions"]
            assert dispositions["maxItems"] == dispositions["minItems"] == len(batch_units)
            assert dispositions["maxItems"] <= 40
            assert dispositions["items"]["properties"]["unit_id"]["enum"] == [
                fact.id for fact in batch_units
            ]
            # S4-REGRESSION: the citable set is bounded by the same batch - here nothing but
            # this batch's own units is citable, so the fact_ids enum never grows with the
            # repository's total either.
            citable = dispositions["items"]["properties"]["fact_ids"]["items"]["enum"]
            assert citable == sorted(fact.id for fact in batch_units)


def _cite(*fact_ids: str) -> dict[str, Any]:
    return {
        "dispositions": [
            {
                "unit_id": fact.id,
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "identity",
                "fact_ids": list(fact_ids) if index == 0 else [],
                "rationale": "r",
            }
            for index, fact in enumerate(FACTS.by_kind("inherited_unit"))
        ]
    }


def test_fact_ids_travel_as_an_enum_so_a_bare_kind_prefix_cannot_be_written() -> None:
    """S4-REGRESSION (Reviewer P0, 2026-09-11; lane D PROPOSAL P23 and lane C PROPOSAL S, both
    measured live). G4-W17 arrival item 40 (e2a1a83) pinned `fact_ids` items by the pattern
    `^(<kinds>):` on an array with no maxItems - fixing a real defect (Aspose.PDF for Python cited
    the packet's own investigation keys, "product_summary:fact_ids", twice; the first pass's
    Aspose.Note wrote the disposition value OMIT_UNSUPPORTED there). Under strict json_schema
    decoding the bare kind prefix "public_symbol:" satisfies that pattern, and the decoder emitted
    it until the 32,000-token budget was gone - 1,047 times in one array on Aspose.Cells for Go,
    finish_reason length on both runs, identically on Aspose.Cells and Slides for Java; S4 runs
    for every repository, so nothing anywhere could seal. The IDs a disposition may cite are known
    here exactly, so they travel as an enum - the treatment unit_id already had, and the one field
    every runaway reply still got right. Lane D replayed the identical request with this one
    change: finish_reason stop, 3,560 tokens, 40 of 40 dispositions."""
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    # A method-kind symbol is outside DECLARED_SYMBOL_KINDS, so the packet's own facts list never
    # shows it - yet the investigation cites it, and the prompt lets the job copy an ID from the
    # investigation's own fact_ids arrays, so it is citable. An ID the investigation cites that
    # names no fact at all is not.
    method = Fact(
        "public_symbol:widget.scene.save",
        "public_symbol",
        "widget.Scene.save",
        (Evidence("x"),),
        attributes={"symbol_kind": "method"},
    )
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, method))
    investigation = {
        "capabilities": [
            {
                "title": "Save",
                "text": "Saves.",
                "fact_ids": ["public_symbol:widget.scene.save", "format:output.glb", "format:x"],
            }
        ]
    }
    batch = list(facts.by_kind("inherited_unit"))
    schema = reconciliation_schema(loaded, batch, facts, investigation)
    items = schema["properties"]["dispositions"]["items"]["properties"]["fact_ids"]["items"]
    # Exactly what the packet shows: its SUPPORTED and CONTRADICTED facts (example:001 is
    # UNRESOLVED and absent - normalize() adds it by code where a rule calls for it), the
    # investigation's cited known facts, and this batch's own units.
    assert items == {
        "type": "string",
        "enum": [
            "format:output.glb",
            "identity:repository",
            "inherited_unit:002.paragraph",
            "inherited_unit:003.code_block",
            "inherited_unit:005.code_block",
            "inherited_unit:006.code_block",
            "link_target:001",
            "public_symbol:widget.scene.save",
        ],
    }
    assert "pattern" not in items
    # The manifest itself is untouched: the specialisation is per call, never a shared mutation.
    assert loaded.manifest.output.schema_["properties"]["dispositions"]["items"]["properties"][
        "fact_ids"
    ] == {"type": "array", "items": {"type": "string"}}

    validator = Draft202012Validator(schema)
    for refused in (
        "public_symbol:",  # the runaway's own token: a bare kind prefix
        "link_target:",
        "product_summary:fact_ids",  # item 40's own case stays refused
        "OMIT_UNSUPPORTED",
        "installation",
        "public_symbol:aspose.page.common",  # well-shaped, names no fact the packet shows
        "example:001",  # a real fact, UNRESOLVED, so never shown to the job
        "format:x",  # cited by the investigation but naming no fact
    ):
        assert [error.json_path for error in validator.iter_errors(_cite(refused))] == [
            "$.dispositions[0].fact_ids[0]"
        ], refused
    # The measured runaway shape - the same prefix over and over - is refused at every position,
    # so a decoder honouring this schema can never start down that path.
    runaway = _cite(*(["public_symbol:"] * 5))
    assert [error.json_path for error in validator.iter_errors(runaway)] == [
        f"$.dispositions[0].fact_ids[{i}]" for i in range(5)
    ]
    # Every real citation the packet can carry still validates, an inherited unit and an
    # investigation-cited symbol included.
    cited = _cite(
        "identity:repository",
        "format:output.glb",
        "inherited_unit:002.paragraph",
        "public_symbol:widget.scene.save",
    )
    assert list(validator.iter_errors(cited)) == []


def test_a_batch_with_nothing_citable_pins_fact_ids_empty_rather_than_an_empty_enum() -> None:
    """An empty enum is not a valid JSON Schema shape to hand a decoder; with nothing citable the
    array is pinned to zero length instead (the guard unit_id's own `if not units` already has)."""
    loaded = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
    empty = FactsDocument(FACTS.repository, FACTS.source_revision, ())
    schema = reconciliation_schema(loaded, [], empty, {})
    fact_ids = schema["properties"]["dispositions"]["items"]["properties"]["fact_ids"]
    assert fact_ids == {"type": "array", "maxItems": 0}
    assert "pattern" not in json.dumps(schema)
