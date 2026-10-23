"""``propose-ops``: the deterministic operations proposer, rule by rule.

Every rule has the case it proposes and the negative controls that must propose nothing, each with
its own typed reason; every proposed list is checked by the unchanged ``live_ops.check_ops``, which
is the proposer's only authority, and re-running gives the same bytes."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from live_anchored_support import BADGES, README, TREE, extra_facts
from repository_presenter.cli import EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.readme_correction import live_ops as lo
from repository_presenter.components.readme_correction import propose_ops as po
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.live_bundle import dump
from repository_presenter.components.readme_correction.model import Context
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from support import (
    commit_all,
    init_git_repository,
    monitor_registry_entry,
    write_registry_file,
)

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
BADGE_A, BADGE_B = BADGES.splitlines()  # supported by the link_target facts of extra_facts()


def make(fact_id: str, value: str, polarity: str, path: str, detail: str | None) -> Fact:
    return Fact(
        id=fact_id,
        kind=fact_id.split(":", 1)[0],  # type: ignore[arg-type]
        value=value,
        evidence=(Evidence(path, detail),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def fmt(fact_id: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return make(fact_id, value, polarity, "src/Main.java", None)


def dep(fact_id: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return make(fact_id, value, polarity, "pom.xml", "declared")


def readme(*sections: str, lead: str = "") -> str:
    body = "".join(sections)
    return f"# Aspose.3D FOSS for Java\n\n{lead}Reads and writes OBJ and STL files.\n\n{body}"


def h2(title: str, body: str = "Text.") -> str:
    return f"## {title}\n\n{body}\n\n"


FOUR = h2("Installation") + h2("Usage") + h2("Notes") + h2("License", "MIT.")


@pytest.fixture
def propose(make_context: Any, make_facts: Any) -> Any:
    def _propose(
        text: str,
        *facts: Any,
        tree: Sequence[str] = TREE,
        drop: Sequence[str] = (),
    ) -> po.Proposal:
        ctx: Context = make_context(text, make_facts(*facts, drop=drop), tree)
        proposal = po.propose(ctx)
        if proposal.ops:  # the check, unchanged, accepts every list that is proposed
            assert lo.check_ops(ctx, proposal.ops) == []
            corrected = lo.apply_ops(ctx.readme, proposal.ops)
            assert lo.confinement_proof(ctx.readme, corrected, proposal.ops)
        return proposal

    return _propose


def kinds(proposal: po.Proposal) -> list[str]:
    return [item.op.kind for item in proposal.proposed]


def skipped(proposal: po.Proposal, rule: str) -> list[str]:
    return [skip.code for skip in proposal.skipped if skip.rule == rule]


def corrected_of(text: str, proposal: po.Proposal) -> str:
    return lo.apply_ops(text, proposal.ops)


# ------------------------------------------------------------------------------ title case
def test_title_case_raises_only_lower_case_words_that_title_case_capitalises() -> None:
    assert po.title_case("Create a workbook") == "Create a Workbook"
    assert po.title_case("what it can do") == "What It Can Do"
    assert po.title_case("Build from source") == "Build From Source"
    assert po.title_case("Notes and comments") == "Notes and Comments"
    assert po.title_case("Where to go next") == "Where to Go Next"


def test_title_case_leaves_a_word_with_a_capital_a_digit_or_markup_alone() -> None:
    assert po.title_case("Export to glTF") == "Export to glTF"
    assert po.title_case("Read PDF files") == "Read PDF Files"
    assert po.title_case("Use `pip install` first") == "Use `pip install` First"
    assert po.title_case("3D scenes") == "3D Scenes"
    assert po.title_case("The iOS build") == "The iOS Build"
    assert po.title_case("See [the docs](x)") == "See [the docs](x)"


def test_title_case_is_idempotent_and_never_lowers_a_capital() -> None:
    for heading in (
        "Quick Start",
        "Documentation And Resources",
        "What It Can Do",
        "A Quick Example",
    ):
        assert po.title_case(heading) == heading
        assert po.title_case(po.title_case(heading)) == po.title_case(heading)


# --------------------------------------------------------------------------------- RETITLE
def test_retitle_maps_synonyms_to_the_standard_name_and_sentence_case_to_title_case(
    propose: Any,
) -> None:
    text = readme(
        h2("Features", "- a\n- b\n- c"),
        h2("Install"),
        h2("Quick start", "### Read a scene\n\nText."),
        h2("Scope"),
        h2("Documentation"),
        h2("Development"),
        h2("License", "MIT."),
    )
    proposal = propose(text)
    out = corrected_of(text, proposal)
    for name in (
        "## Key Capabilities",
        "## Installation",
        "## Quick Start",
        "### Read a Scene",
        "## Scope and Limitations",
        "## Documentation & Resources",
        "## Development and Testing",
    ):
        assert f"\n{name}\n" in out
    retitles = [item for item in proposal.proposed if item.op.kind == lo.RETITLE]
    assert all(item.op.evidence == (f"readme:{item.line}",) for item in retitles)


def test_retitle_never_renames_an_h3_to_a_standard_section_name(propose: Any) -> None:
    text = readme(h2("Quick Start", "### Features\n\nText.\n\n### Install\n\nText."))
    assert propose(text).ops == ()  # an H3 changes case only; these are already title case


def test_retitle_that_is_already_title_case_proposes_nothing(propose: Any) -> None:
    text = readme(h2("Installation"), h2("Quick Start"), h2("License", "MIT."))
    assert not [i for i in propose(text).proposed if i.op.kind == lo.RETITLE]


def test_retitle_to_a_section_the_readme_already_has_is_target_exists(propose: Any) -> None:
    text = readme(h2("Key Capabilities", "- a\n- b\n- c"), h2("Features"), h2("Installation"))
    proposal = propose(text)
    assert po.TARGET_EXISTS in skipped(proposal, po.RULE_RETITLE)
    assert "\n## Features\n" in corrected_of(text, proposal)


def test_retitle_that_would_break_an_anchor_link_is_dropped_by_the_check(propose: Any) -> None:
    text = readme(h2("Features", "Jump to [install](#install).\n\n- a"), h2("Install"))
    proposal = propose(text)
    out = corrected_of(text, proposal)
    assert "\n## Install\n" in out  # kept, so #install still resolves
    assert "\n## Key Capabilities\n" in out  # nothing links to #features
    refused = [s for s in proposal.skipped if s.rule == po.RULE_RETITLE]
    assert [s.check_code for s in refused] == [lo.BROKEN_ANCHOR_LINK]


def test_a_vocabulary_rename_the_check_refuses_falls_back_to_title_case(propose: Any) -> None:
    text = readme(
        h2("What it can do", "- a\n- b\n- c"),
        h2("Installation", "See [what it can do](#what-it-can-do)."),
    )
    proposal = propose(text)
    out = corrected_of(text, proposal)
    assert "\n## What It Can Do\n" in out and "Key Capabilities" not in out
    refused = [s for s in proposal.skipped if s.rule == po.RULE_RETITLE]
    assert [s.check_code for s in refused] == [lo.BROKEN_ANCHOR_LINK]


def test_what_it_can_do_is_the_key_capabilities_section_when_nothing_links_to_it(
    propose: Any,
) -> None:
    text = readme(h2("What it can do", "- a\n- b\n- c"), h2("Installation"))
    assert "\n## Key Capabilities\n" in corrected_of(text, propose(text))


def test_retitle_of_a_heading_with_a_symbol_is_not_plain(propose: Any) -> None:
    text = readme(h2("Enjoying it? Star it ⭐"), h2("Installation"))
    assert po.HEADING_NOT_PLAIN in skipped(propose(text), po.RULE_RETITLE)


def test_retitle_of_a_line_that_occurs_twice_is_anchor_not_unique(propose: Any) -> None:
    text = readme(
        h2("Installation"), "### Run it\n\nText.\n\n", h2("Usage"), "### Run it\n\nText.\n\n"
    )
    proposal = propose(text)
    assert skipped(proposal, po.RULE_RETITLE).count(po.ANCHOR_NOT_UNIQUE) == 2
    assert "### Run It" not in corrected_of(text, proposal)


def test_retitle_of_a_sibling_heading_that_contains_the_line_is_not_unique(propose: Any) -> None:
    # '## Features\n' is also inside '### Features\n'
    text = readme(h2("Features"), h2("Installation", "### Features\n\nText."))
    assert po.ANCHOR_NOT_UNIQUE in skipped(propose(text), po.RULE_RETITLE)


# ---------------------------------------------------------------------------------- REFLOW
def test_reflow_joins_consecutive_badge_lines_onto_one(propose: Any) -> None:
    proposal = propose(README, *extra_facts())
    item = next(i for i in proposal.proposed if i.op.kind == lo.REFLOW)
    assert item.op.anchor == BADGES and item.op.replacement == f"{BADGE_A} {BADGE_B}\n"
    assert f"{BADGE_A} {BADGE_B}\n\n" in corrected_of(README, proposal)


def test_reflow_that_makes_the_acceptance_judge_fail_is_not_proposed(propose: Any) -> None:
    # without an install command no fact supports the Maven badge once it is read as the badge row
    text = readme(h2("Installation"), lead=f"{BADGE_A}\n{BADGE_B}\n\n")
    proposal = propose(text, *extra_facts())
    assert lo.REFLOW not in kinds(proposal)
    assert po.INTRODUCES_FAILURE in skipped(proposal, po.RULE_REFLOW)


def test_reflow_of_one_badge_line_or_of_text_lines_proposes_nothing(propose: Any) -> None:
    for lead in (f"{BADGE_A}\n\n", f"{BADGE_A}\nSome words.\n\n", "First line.\nSecond line.\n\n"):
        text = readme(h2("Installation"), lead=lead)
        assert lo.REFLOW not in kinds(propose(text, *extra_facts())), lead


def test_reflow_only_looks_at_the_top_of_the_readme(propose: Any) -> None:
    text = readme(h2("Installation", f"{BADGE_A}\n{BADGE_B}"))
    assert lo.REFLOW not in kinds(propose(text, *extra_facts()))


def test_reflow_of_badge_lines_that_follow_a_line_directly_is_not_after_blank(
    propose: Any,
) -> None:
    text = "# Aspose.3D FOSS for Java\n" + f"{BADGE_A}\n{BADGE_B}\n\nReads files.\n\n" + h2("Usage")
    proposal = propose(text, *extra_facts())
    assert lo.REFLOW not in kinds(proposal)
    assert po.NOT_AFTER_BLANK in skipped(proposal, po.RULE_REFLOW)


# ------------------------------------------------------------------------------ DELETE_LINE
def test_delete_removes_a_list_item_whose_only_link_target_is_absent(propose: Any) -> None:
    text = readme(h2("Docs", "- See the [guide](docs/GUIDE.md).\n- Read the [notes](pom.xml)."))
    proposal = propose(text)
    item = next(i for i in proposal.proposed if i.op.kind == lo.DELETE_LINE)
    assert item.op.anchor == "- See the [guide](docs/GUIDE.md).\n"
    assert "tree-absent:docs/GUIDE.md" in item.op.evidence
    out = corrected_of(text, proposal)
    assert "GUIDE.md" not in out and "[notes](pom.xml)" in out


def test_delete_cites_the_contradicted_link_fact_when_the_facts_hold_one(
    propose: Any, make_fact: Any
) -> None:
    text = readme(h2("Docs", "- See the [notes](RELEASE_NOTES.md).\n- Read the [x](pom.xml)."))
    proposal = propose(text, *extra_facts())
    item = next(i for i in proposal.proposed if i.op.kind == lo.DELETE_LINE)
    assert "link_target:005" in item.op.evidence


def test_delete_keeps_an_item_whose_link_target_is_in_the_tree(propose: Any) -> None:
    text = readme(h2("Docs", "- Read the [notes](pom.xml).\n- Read the [x](LICENSE)."))
    assert lo.DELETE_LINE not in kinds(propose(text))


def test_delete_keeps_an_external_link_and_an_item_that_mixes_links(propose: Any) -> None:
    text = readme(
        h2(
            "Docs",
            "- Read [the site](https://example.org/gone).\n"
            "- See [a](docs/A.md) and [b](pom.xml).\n"
            "- See [c](docs/C.md) and [d](https://example.org).\n"
            "- Keep [e](pom.xml).",
        )
    )
    proposal = propose(text)
    assert lo.DELETE_LINE not in kinds(proposal)
    assert skipped(proposal, po.RULE_DELETE).count(po.MIXED_LINKS) == 2


def test_delete_never_reads_link_like_code_as_a_link(propose: Any) -> None:
    text = readme(h2("API", "- `operator[](index)`\n- `Add(x)` and `list[](key)`\n- plain"))
    proposal = propose(text)
    assert lo.DELETE_LINE not in kinds(proposal)
    assert po.REFUSED_BY_CHECK not in skipped(proposal, po.RULE_DELETE)


def test_delete_leaves_the_only_item_of_a_list_and_an_item_with_a_continuation(
    propose: Any,
) -> None:
    only = readme(h2("Docs", "- See the [guide](docs/GUIDE.md)."))
    assert po.WOULD_EMPTY_LIST in skipped(propose(only), po.RULE_DELETE)
    nested = readme(h2("Docs", "- See the [guide](docs/GUIDE.md)\n  - nested note\n- other"))
    assert po.CONTINUATION_LINE in skipped(propose(nested), po.RULE_DELETE)
    lazy = readme(h2("Docs", "- See the [guide](docs/GUIDE.md)\ncontinued text\n- other"))
    assert po.CONTINUATION_LINE in skipped(propose(lazy), po.RULE_DELETE)


def test_delete_ignores_a_list_item_inside_a_code_fence(propose: Any) -> None:
    text = readme(h2("Docs", "```md\n- See [guide](docs/GUIDE.md)\n- other\n```"))
    assert lo.DELETE_LINE not in kinds(propose(text))


# ----------------------------------------------------------------------------- NAVIGATION
def test_navigation_is_proposed_with_slugs_of_the_corrected_headings(propose: Any) -> None:
    text = readme(
        h2("Features", "- a\n- b\n- c"), h2("Install"), h2("Scope"), h2("License", "MIT.")
    )
    proposal = propose(text)
    out = corrected_of(text, proposal)
    nav = out.split("## Navigation\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert nav == [
        "- [Key Capabilities](#key-capabilities)",
        "- [Installation](#installation)",
        "- [Scope and Limitations](#scope-and-limitations)",
        "- [License](#license)",
    ]
    item = next(i for i in proposal.proposed if "Navigation" in i.sections)
    assert item.op.anchor.startswith("## Features\n")  # before the first H2, of the live README
    assert any(e.startswith("readme:") for e in item.op.evidence)


def test_navigation_needs_four_h2_sections_in_the_corrected_readme(propose: Any) -> None:
    three = readme(h2("Installation"), h2("Usage"), h2("License", "MIT."))
    proposal = propose(three)
    assert po.TOO_FEW_SECTIONS in skipped(proposal, po.RULE_NAVIGATION)
    assert proposal.ops == ()


def test_navigation_counts_the_sections_the_proposal_itself_adds(propose: Any) -> None:
    # three live H2 sections plus the Dependencies section the facts fill make four
    text = readme(h2("Installation"), h2("Quick Start"), h2("License", "MIT."))
    proposal = propose(text, dep("dependency:guava", "com.google.guava:guava:33.0"))
    out = corrected_of(text, proposal)
    assert "## Dependencies" in out and "## Navigation" in out
    assert "- [Dependencies](#dependencies)" in out


def test_navigation_is_not_proposed_for_a_readme_that_has_one(propose: Any) -> None:
    for name in ("Navigation", "Table of Contents", "Contents"):
        text = readme(h2(name, "- [a](#a)\n- [b](#b)"), FOUR)
        proposal = propose(text)
        assert po.SECTION_PRESENT in skipped(proposal, po.RULE_NAVIGATION), name
        assert not any("Navigation" in i.sections for i in proposal.proposed)


# --------------------------------------------------------------------------- DEPENDENCIES
DEPS = (
    dep("dependency:guava", "com.google.guava:guava:33.0"),
    dep("dependency:optional.json.jackson", "jackson-databind:2.17.0"),
    dep("dependency:development.dev.junit", "junit:junit:4.13.2"),
)


def test_dependencies_are_bucketed_by_fact_id_and_cite_their_facts(propose: Any) -> None:
    text = readme(h2("Installation"), h2("Quick Start"), h2("License", "MIT."))
    proposal = propose(text, *DEPS)
    item = next(i for i in proposal.proposed if "Dependencies" in i.sections)
    assert item.op.anchor.startswith("## Quick Start\n")
    inserted = lo.apply_ops(text, [item.op]).split("## Dependencies\n\n", 1)[1].split("## Quick")[0]
    assert inserted == (
        "### Required Package Dependencies\n\n- `com.google.guava:guava:33.0`\n\n"
        "### Optional Dependencies\n\n- `jackson-databind:2.17.0`\n\n"
        "### Development Dependencies\n\n- `junit:junit:4.13.2`\n\n"
    )
    assert {"dependency:guava", "dependency:optional.json.jackson"} <= set(item.op.evidence)


def test_dependencies_ignore_a_declared_none_and_facts_that_are_not_supported(
    propose: Any,
) -> None:
    text = readme(h2("Installation"), h2("Quick Start"), h2("License", "MIT."))
    proposal = propose(
        text, dep("dependency:guava", "com.google.guava:guava:33.0", "UNRESOLVED")
    )  # the base facts hold 'dependency:none'
    assert po.NO_SUPPORTED_DEPENDENCIES in skipped(proposal, po.RULE_DEPENDENCIES)
    assert not any("Dependencies" in i.sections for i in proposal.proposed)


def test_dependencies_are_not_proposed_for_a_readme_that_has_the_section_or_a_synonym(
    propose: Any,
) -> None:
    for name in ("Dependencies", "Requirements", "Prerequisites"):
        text = readme(h2("Installation"), h2(name), h2("Quick Start"), h2("License", "MIT."))
        proposal = propose(text, *DEPS)
        assert po.SECTION_PRESENT in skipped(proposal, po.RULE_DEPENDENCIES), name
        assert not any("Dependencies" in i.sections for i in proposal.proposed), name


def test_dependencies_with_no_later_section_to_go_before_have_no_place(propose: Any) -> None:
    text = readme(h2("Installation"), h2("Features", "- a\n- b\n- c"))
    assert po.NO_PLACE in skipped(propose(text, *DEPS), po.RULE_DEPENDENCIES)


# ---------------------------------------------------------------------------- AT A GLANCE
CAPABILITIES = (
    "- Read OBJ files\n"
    "- Write STL files, with options\n"
    "- Convert between formats using a stream\n"
    "- Build meshes from control points\n"
)
FORMATS = (fmt("format:input.obj", ".obj"), fmt("format:output.stl", ".stl"))


def with_capabilities(extra: str = "") -> str:
    return readme(
        h2("Features", CAPABILITIES),
        h2("Installation"),
        h2("Quick Start"),
        h2("License", "MIT."),
        lead=extra,
    )


def glance_labels(text: str, proposal: po.Proposal) -> list[str]:
    from repository_presenter.components.readme_diagram.parse import parse

    body = lo.glance_bodies(
        next(i.op for i in proposal.proposed if "At a Glance" in i.sections).replacement
    )[0]
    glance = parse(body).glance
    return [*glance.starting_points, glance.product, *glance.capabilities, *glance.outputs]


def test_glance_is_built_from_the_capabilities_list_and_the_format_facts(propose: Any) -> None:
    text = with_capabilities()
    proposal = propose(text, *FORMATS)
    labels = glance_labels(text, proposal)
    assert labels == [
        "OBJ file",
        "Aspose.3D FOSS for Java",
        "Read OBJ files",
        "Write STL files, with options",
        "Convert between formats",
        "Build meshes from control points",
        "STL file",
    ]
    item = next(i for i in proposal.proposed if "At a Glance" in i.sections)
    assert {"format:input.obj", "format:output.stl"} <= set(item.op.evidence)
    assert any(e.startswith("readme:") for e in item.op.evidence)


def test_every_label_of_the_glance_is_a_contiguous_substring_of_the_readme(propose: Any) -> None:
    text = with_capabilities()
    proposal = propose(text, *FORMATS)
    for label in glance_labels(text, proposal)[2:-1]:
        assert label in text, label


def test_glance_is_placed_after_the_navigation_and_both_in_one_insertion(propose: Any) -> None:
    text = with_capabilities()
    proposal = propose(text, *FORMATS)
    inserts = [i for i in proposal.proposed if i.op.kind == lo.INSERT_BEFORE]
    both = next(i for i in inserts if "At a Glance" in i.sections)
    assert both.sections == ("At a Glance", "Navigation") or set(both.sections) == {
        "At a Glance",
        "Navigation",
    }
    out = corrected_of(text, proposal)
    assert (
        out.index("## Navigation") < out.index("## At a Glance") < out.index("## Key Capabilities")
    )


def test_glance_with_fewer_than_three_capabilities_is_underivable(propose: Any) -> None:
    text = readme(
        h2("Features", "- Read OBJ files\n- Write STL files\n"), h2("Installation"), h2("Usage")
    )
    proposal = propose(text, *FORMATS)
    assert po.GLANCE_UNDERIVABLE in skipped(proposal, po.RULE_GLANCE)
    detail = next(s.detail for s in proposal.skipped if s.rule == po.RULE_GLANCE)
    assert detail.startswith(po.NO_CAPABILITIES_LIST) or detail.startswith(
        po.FEWER_THAN_THREE_CAPABILITIES
    )
    assert not any("At a Glance" in i.sections for i in proposal.proposed)


def test_glance_needs_a_starting_point_and_an_output_from_supported_facts(propose: Any) -> None:
    text = with_capabilities()
    none = propose(text)
    assert po.GLANCE_UNDERIVABLE in skipped(none, po.RULE_GLANCE)
    assert next(s.detail for s in none.skipped if s.rule == po.RULE_GLANCE).startswith(
        po.NO_STARTING_POINT
    )
    only_input = propose(text, fmt("format:input.obj", ".obj"))
    assert next(s.detail for s in only_input.skipped if s.rule == po.RULE_GLANCE).startswith(
        po.NO_OUTPUT
    )
    unresolved = propose(
        text, fmt("format:input.obj", ".obj"), fmt("format:output.stl", ".stl", "UNRESOLVED")
    )
    assert next(s.detail for s in unresolved.skipped if s.rule == po.RULE_GLANCE).startswith(
        po.NO_OUTPUT
    )


def test_glance_falls_back_to_the_readmes_own_formats_table_per_side(propose: Any) -> None:
    table = (
        "| Format | Load | Save |\n|---|:---:|:---:|\n"
        "| OBJ | Yes | No |\n| STL | Yes | Yes |\n| GLB | No | Yes |\n"
    )
    text = readme(
        h2("Features", CAPABILITIES),
        h2("Installation"),
        h2("Supported Formats", table),
        h2("License", "MIT."),
    )
    proposal = propose(text)
    labels = glance_labels(text, proposal)
    assert labels[0:2] == ["OBJ file", "STL file"] and labels[-2:] == ["STL file", "GLB file"]
    item = next(i for i in proposal.proposed if "At a Glance" in i.sections)
    assert any(e.startswith("readme:") for e in item.op.evidence)
    # a side that has SUPPORTED facts keeps them and ignores the table
    mixed = propose(text, fmt("format:input.obj", ".obj"))
    assert glance_labels(text, mixed)[0] == "OBJ file"
    assert glance_labels(text, mixed)[-2:] == ["STL file", "GLB file"]


def test_glance_is_not_proposed_for_a_readme_that_has_one(propose: Any) -> None:
    text = readme(h2("At a glance", "Diagram."), h2("Features", CAPABILITIES), FOUR)
    proposal = propose(text, *FORMATS)
    assert po.SECTION_PRESENT in skipped(proposal, po.RULE_GLANCE)
    assert not any("At a Glance" in i.sections for i in proposal.proposed)


def test_glance_never_takes_a_list_of_links_for_the_capabilities(propose: Any) -> None:
    text = readme(
        h2("Features", "- [One](#one)\n- [Two](#two)\n- [Three](#three)\n"),
        h2("Installation"),
        h2("Usage"),
    )
    proposal = propose(text, *FORMATS)
    assert po.GLANCE_UNDERIVABLE in skipped(proposal, po.RULE_GLANCE)


def test_glance_uses_the_first_list_before_installation_when_there_is_no_capabilities_heading(
    propose: Any,
) -> None:
    text = readme(
        h2("Overview", CAPABILITIES), h2("Installation"), h2("Usage"), h2("License", "MIT.")
    )
    labels = glance_labels(text, propose(text, *FORMATS))
    assert "Read OBJ files" in labels
    after = readme(h2("Installation"), h2("Overview", CAPABILITIES), h2("Usage"))
    assert po.GLANCE_UNDERIVABLE in skipped(propose(after, *FORMATS), po.RULE_GLANCE)


def test_glance_drops_a_label_the_diagram_contract_cannot_draw(propose: Any) -> None:
    long_word = "Supercalifragilisticexpialidocious" * 2
    bullets = CAPABILITIES + f"- Handle {long_word} streams\n"
    text = readme(h2("Features", bullets), h2("Installation"), h2("Usage"), h2("License", "MIT."))
    proposal = propose(text, *FORMATS)
    assert all(long_word not in label for label in glance_labels(text, proposal))


# ------------------------------------------------------------------------------- shortening
@pytest.mark.parametrize(
    ("bullet", "label"),
    [
        ("Read OBJ files", "Read OBJ files"),
        ("Read OBJ files into a scene", None),
        ("Create, load, edit, and save `.xlsx` workbooks", "Create, load, edit"),
        (
            "Read and write cell values and formulas using A1 references",
            "Read and write cell values",
        ),
        (
            "Manage worksheets, merged cells, hyperlinks, page setup",
            "Manage worksheets, merged cells, hyperlinks",
        ),
        ("**Fast** - parses large files", "Fast"),
        ("The converter writes PDF", "converter writes PDF"),
        ("Configure workbook, worksheet, and cell protection", "Configure workbook, worksheet"),
    ],
)
def test_shorten_cuts_a_bullet_to_five_of_its_own_words(bullet: str, label: str | None) -> None:
    result = po.shorten(bullet)
    if label is None:  # six words and nowhere to cut
        assert result is None
        return
    assert result is not None
    assert result in po.plain_text(bullet)  # a contiguous substring, so every word is the README's
    assert len(result.split()) <= po.MAX_LABEL_WORDS
    if label == "Fast":
        return
    assert result == label


def test_shorten_gives_up_rather_than_cut_a_bullet_with_no_place_to_cut() -> None:
    assert po.shorten("Convert OBJ files to STL files today") is None
    assert po.shorten("Convert OBJ files to STL files") is None
    assert po.shorten("") is None
    assert po.shorten("Uses <b>markup</b> & more") is None


# ---------------------------------------------------------------------------- the whole thing
def test_an_already_standard_readme_gets_no_change(propose: Any) -> None:
    standard = (
        "# Aspose.3D FOSS for Java\n\nReads files.\n\n"
        + h2("Navigation", "- [Installation](#installation)\n- [License](#license)")
        + h2("At a Glance", "Diagram.")
        + h2("Key Capabilities", CAPABILITIES)
        + h2("Installation")
        + h2("Dependencies")
        + h2("Quick Start")
        + h2("License", "MIT.")
    )
    proposal = propose(standard, *DEPS, *FORMATS)
    assert proposal.outcome == po.NO_CHANGE and proposal.ops == ()


def test_the_worked_example_is_reproduced_from_the_synthetic_readme(propose: Any) -> None:
    """The shape of the hand-written list: badge lines joined, headings retitled, a broken link
    deleted, Navigation and Dependencies inserted. Its capabilities are sentences with no place to
    cut, so the Glance is reported underivable rather than invented."""
    proposal = propose(README, *extra_facts(), *FORMATS)
    assert set(kinds(proposal)) == {lo.REFLOW, lo.RETITLE, lo.DELETE_LINE, lo.INSERT_BEFORE}
    out = corrected_of(README, proposal)
    for name in ("## Navigation", "## Dependencies", "## Key Capabilities"):
        assert f"\n{name}\n" in out
    assert "## At a Glance" not in out
    assert po.GLANCE_UNDERIVABLE in skipped(proposal, po.RULE_GLANCE)
    assert "RELEASE_NOTES.md" not in out and "CHANGELOG.md" in out


def test_proposing_twice_gives_the_same_bytes(propose: Any) -> None:
    first = propose(README, *extra_facts(), *FORMATS)
    second = propose(README, *extra_facts(), *FORMATS)
    assert dump(lo.ops_to_json(first.ops)) == dump(lo.ops_to_json(second.ops))
    assert first.report() == second.report()


def test_every_skip_has_a_typed_reason_and_a_rule(propose: Any) -> None:
    proposal = propose(README, *extra_facts())
    assert proposal.skipped
    for skip in proposal.skipped:
        assert skip.code in po.REASONS
        assert skip.rule in {
            po.RULE_RETITLE,
            po.RULE_REFLOW,
            po.RULE_DELETE,
            po.RULE_NAVIGATION,
            po.RULE_DEPENDENCIES,
            po.RULE_GLANCE,
            po.RULE_ALL,
        }


def test_a_crlf_readme_gets_no_insertion_but_keeps_its_line_endings(propose: Any) -> None:
    text = with_capabilities().replace("\n", "\r\n")
    proposal = propose(text, *FORMATS)
    assert lo.INSERT_BEFORE not in kinds(proposal)
    assert po.CRLF_README in skipped(proposal, po.RULE_NAVIGATION)
    out = corrected_of(text, proposal)
    assert "\r\n## Key Capabilities\r\n" in out


def test_a_proposal_that_would_fail_the_acceptance_judge_is_not_made(
    propose: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The judge's 'introduced' list refuses a bundle at production; the proposer asks the same
    function first and leaves out the operation that causes it."""
    real = po.validation_delta

    def delta(ctx: Context, result: Any, original: bytes) -> Any:
        out = real(ctx, result, original)
        if "## Dependencies" in result.corrected:
            out = {**out, "introduced": [{"check": "BC-99", "extra": 1, "details": ["x"]}]}
        return out

    monkeypatch.setattr(po, "validation_delta", delta)
    text = readme(h2("Installation"), h2("Quick Start"), h2("License", "MIT."), h2("Notes"))
    proposal = propose(text, *DEPS)
    assert po.INTRODUCES_FAILURE in skipped(proposal, po.RULE_DEPENDENCIES)
    assert not any("Dependencies" in i.sections for i in proposal.proposed)


# ----------------------------------------------------------------------------------- the CLI
@pytest.fixture
def target(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text(README, encoding="utf-8", newline="\n")
    for name in ("LICENSE", "pom.xml", "CHANGELOG.md"):
        (source / name).write_text(f"{name}\n", encoding="utf-8")
    revision = commit_all(source, "seed")
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode="dry_run")])

    def serve(clone_url: str, destination: Path, **kwargs: Any) -> Any:
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(po, "pinned_read_only_clone", serve)
    monkeypatch.setattr(correction_run, "pinned_read_only_clone", serve)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return {"root": project, "revision": revision, "tmp": tmp_path}


def write_facts_for(target: dict[str, Any], make_facts: Any, *extra: Any) -> Path:
    path = target["tmp"] / "facts.json"
    write_facts(
        FactsDocument(REPOSITORY, target["revision"], tuple(make_facts(*extra_facts(), *extra))),
        path,
    )
    return path


def run_cli(target: dict[str, Any], *extra: str) -> int:
    return main(["propose-ops", "--repo", REPOSITORY, "--root", str(target["root"]), *extra])


def test_propose_ops_writes_the_file_and_the_report_and_correct_readme_applies_it(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts = write_facts_for(target, make_facts, *FORMATS)
    out = target["tmp"] / "ops.json"
    assert run_cli(target, "--facts", str(facts), "--out", str(out)) == EXIT_OK
    said = capsys.readouterr().out
    assert "PROPOSED" in said and "DELETE_LINE 1" in said
    report = json.loads((target["tmp"] / "ops.json.report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == po.PROPOSED and report["ops_file"] == "ops.json"
    assert report["revision"] == target["revision"]
    assert {item["id"] for item in report["proposed"]} == {
        op["id"] for op in json.loads(out.read_text(encoding="utf-8"))
    }
    bundle = target["tmp"] / "bundle"
    assert (
        main(
            [
                "correct-readme",
                "--repo",
                REPOSITORY,
                "--root",
                str(target["root"]),
                "--facts",
                str(facts),
                "--ops",
                str(out),
                "--out",
                str(bundle),
            ]
        )
        == EXIT_OK
    )
    assert (bundle / "README.md").read_text(encoding="utf-8").count("## Navigation") == 1


def test_propose_ops_with_nothing_to_propose_writes_a_report_and_no_operations_file(
    target: dict[str, Any], make_facts: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    standard = (
        "# Aspose.3D FOSS for Java\n\nReads files.\n\n"
        + h2("Navigation", "- [License](#license)\n- [Usage](#usage)")
        + h2("Usage")
        + h2("License", "MIT.")
    )
    source = init_git_repository(tmp_path / "standard", with_commit=False)
    (source / "README.md").write_text(standard, encoding="utf-8", newline="\n")
    revision = commit_all(source, "seed")

    def serve(clone_url: str, destination: Path, **kwargs: Any) -> Any:
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(po, "pinned_read_only_clone", serve)
    facts = target["tmp"] / "facts.json"
    write_facts(FactsDocument(REPOSITORY, revision, tuple(make_facts())), facts)
    out = target["tmp"] / "none.json"
    assert run_cli(target, "--facts", str(facts), "--out", str(out)) == EXIT_OK
    assert not out.exists()
    report = json.loads((target["tmp"] / "none.json.report.json").read_text(encoding="utf-8"))
    assert report["outcome"] == po.NO_CHANGE and report["ops_file"] is None


def test_propose_ops_refuses_facts_for_another_revision(
    target: dict[str, Any], make_facts: Any
) -> None:
    facts = target["tmp"] / "stale.json"
    write_facts(FactsDocument(REPOSITORY, "b" * 40, tuple(make_facts())), facts)
    assert run_cli(target, "--facts", str(facts), "--out", str(target["tmp"] / "o.json")) != EXIT_OK
    assert not (target["tmp"] / "o.json").exists()


def test_propose_ops_needs_facts_and_a_listed_repository(target: dict[str, Any]) -> None:
    with pytest.raises(SystemExit) as raised:
        run_cli(target, "--out", str(target["tmp"] / "o.json"))
    assert raised.value.code == EXIT_USAGE
    rc = main(
        [
            "propose-ops",
            "--repo",
            "someone/else",
            "--root",
            str(target["root"]),
            "--facts",
            str(target["tmp"] / "f.json"),
            "--out",
            str(target["tmp"] / "o.json"),
        ]
    )
    assert rc != EXIT_OK
