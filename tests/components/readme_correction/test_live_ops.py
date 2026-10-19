"""Live-anchored operations: the pure apply, the confinement proof and every per-kind rule, each
with a negative control that must be refused with its own typed code."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import pytest

from live_anchored_support import (
    AT_A_GLANCE,
    BADGES,
    DEPENDENCIES,
    GLANCE,
    NAVIGATION,
    README,
    RELEASE_LINE,
    TREE,
    corrected,
    extra_facts,
    good_ops,
    line_of,
    make,
    retitle,
)
from repository_presenter.components.readme_correction import live_ops as lo
from repository_presenter.components.readme_correction.live_bundle import dump
from repository_presenter.components.readme_correction.model import Context
from repository_presenter.components.readme_diagram.build import build_body
from repository_presenter.components.readme_diagram.model import Glance

FEATURES = "## Features\n"
Build = Callable[..., Context]


@pytest.fixture
def build(make_context: Any, make_facts: Any) -> Build:
    def _build(
        readme: str = README, tree: Sequence[str] = TREE, drop: Sequence[str] = ()
    ) -> Context:
        return make_context(readme, make_facts(*extra_facts(), drop=drop), tree)

    return _build


def codes(ctx: Context, ops: Sequence[lo.Op]) -> set[str]:
    return {refusal.code for refusal in lo.check_ops(ctx, ops)}


def insert(text: str, *evidence: str, op_id: str = "ins") -> lo.Op:
    ev = evidence or (f"readme:{line_of(FEATURES)}",)
    return make(op_id, lo.INSERT_BEFORE, FEATURES, text + FEATURES, *ev)


# ----------------------------------------------------------------------------- the whole thing
def test_every_kind_together_pass_every_rule_and_give_the_expected_bytes(build: Build) -> None:
    ctx, ops = build(), good_ops()
    assert {op.kind for op in ops} == lo.OP_KINDS
    assert lo.check_ops(ctx, ops) == []
    result = lo.apply_ops(README, ops)
    assert result == corrected()
    assert lo.confinement_proof(README, result, ops)


def test_apply_ops_is_pure_and_does_not_depend_on_the_order_given(build: Build) -> None:
    ops = good_ops()
    assert lo.apply_ops(README, ops) == lo.apply_ops(README, list(reversed(ops))) == corrected()
    assert lo.apply_ops(README, ops) == lo.apply_ops(README, ops)  # no state between calls


def test_a_retitle_of_the_heading_an_insertion_goes_before_does_not_overlap_it() -> None:
    placed = lo.place(README, good_ops())
    inserted = next(p for p in placed if p.op.id == "nav")
    renamed = next(p for p in placed if p.op.id == "features")
    assert inserted.start == inserted.end == renamed.start and inserted.end < renamed.end
    assert inserted.text == NAVIGATION + AT_A_GLANCE


def test_operations_round_trip_through_operations_json_with_sorted_keys() -> None:
    ops = good_ops()
    data = lo.ops_to_json(ops)
    assert lo.ops_from_json(data) == tuple(ops)
    dumped = json.loads(dump(data), object_pairs_hook=lambda pairs: [key for key, _ in pairs])
    assert all(keys == sorted(keys) for keys in dumped)  # operations.json is written sorted


# ------------------------------------------------------------------------ confinement (proof)
def test_confinement_proof_refuses_text_changed_outside_the_spans() -> None:
    ops = good_ops()
    result = corrected()
    assert lo.confinement_proof(README, result, ops)
    assert not lo.confinement_proof(README, result.replace("MIT.", "Apache."), ops)
    assert not lo.confinement_proof(README, result.replace("Needs Java 17", "Needs Java 21"), ops)
    assert not lo.confinement_proof(README, result + "\n", ops)
    assert not lo.confinement_proof(README, README, ops)  # the operations are not applied


def test_confinement_proof_refuses_a_span_that_holds_other_text() -> None:
    result = corrected().replace("## Quick Start\n", "## Quickstart\n")
    assert not lo.confinement_proof(README, result, good_ops())


# ------------------------------------------------------------------------------ shape / anchors
def test_unknown_kind_is_refused_when_the_operation_is_built_or_read() -> None:
    with pytest.raises(lo.LiveOpError) as built:
        lo.Op("x", "REWRITE", "a", "b", ())
    assert built.value.code == lo.UNKNOWN_KIND
    data = lo.ops_to_json(good_ops())
    data[0]["kind"] = "REWRITE"
    with pytest.raises(lo.LiveOpError) as read:
        lo.ops_from_json(data)
    assert read.value.code == lo.UNKNOWN_KIND


@pytest.mark.parametrize(
    "bad",
    [
        "not a list",
        [["not", "a", "dict"]],
        [{"id": "a", "kind": "RETITLE", "anchor": "x", "replacement": "y"}],  # no evidence key
        [{"id": "a", "kind": "RETITLE", "anchor": "x", "replacement": "y", "evidence": [1]}],
        [
            {
                "id": "a",
                "kind": "RETITLE",
                "anchor": "x",
                "replacement": "y",
                "evidence": [],
                "extra": 1,
            }
        ],
    ],
)
def test_a_malformed_operations_file_is_refused(bad: Any) -> None:
    with pytest.raises(lo.LiveOpError) as raised:
        lo.ops_from_json(bad)
    assert raised.value.code == lo.BAD_OPERATIONS


def test_an_operation_that_is_not_closed_in_shape_is_refused() -> None:
    with pytest.raises(lo.LiveOpError):
        lo.Op("a", lo.DELETE_LINE, "x", "y", ())  # a delete replaces with nothing
    with pytest.raises(lo.LiveOpError):
        lo.Op("a", lo.RETITLE, "x", "x", ())  # a replacement equal to the anchor
    with pytest.raises(lo.LiveOpError):
        lo.Op("a b", lo.RETITLE, "x", "y", ())  # an id that is not a token
    with pytest.raises(lo.LiveOpError):
        lo.Op("a", lo.RETITLE, "", "y", ())


def test_no_operations_is_refused(build: Build) -> None:
    assert codes(build(), []) == {lo.NO_OPERATIONS}


def test_an_anchor_missing_from_the_readme_is_refused(build: Build) -> None:
    op = retitle("a", "## Features", "## Key Capabilities")
    ghost = lo.Op("g", lo.RETITLE, "## Missing\n", "## Absent\n", op.evidence)
    assert codes(build(), [ghost]) == {lo.ANCHOR_NOT_FOUND}


def test_an_anchor_that_occurs_twice_is_refused(build: Build) -> None:
    text = README + "\n## Features\n\nAgain.\n"
    op = lo.Op("a", lo.RETITLE, "## Features\n", "## Key Capabilities\n", ("readme:9",))
    assert codes(build(text), [op]) == {lo.ANCHOR_NOT_UNIQUE}


def test_an_anchor_that_is_part_of_a_line_is_refused(build: Build) -> None:
    op = lo.Op(
        "a", lo.RETITLE, "Features\n", "Capabilities\n", ("readme:9",)
    )  # inside '## Features'
    assert codes(build(), [op]) == {lo.ANCHOR_NOT_LINE_ALIGNED}
    tail = lo.Op("b", lo.REFLOW, "Java is a free", "Java   is a free", ("readme:5",))
    assert codes(build(), [tail]) == {lo.ANCHOR_NOT_LINE_ALIGNED}


def test_overlapping_operations_are_refused(build: Build) -> None:
    both = [
        make(
            "a",
            lo.RETITLE,
            "## Scope\n",
            "## Scope and Limitations\n",
            f"readme:{line_of('## Scope')}",
        ),
        make(
            "b", lo.RETITLE, "## Scope\n", "## Limits and Scope\n", f"readme:{line_of('## Scope')}"
        ),
    ]
    assert codes(build(), both) == {lo.OVERLAPPING_OPERATIONS}
    inside = lo.Op("c", lo.REFLOW, "- Only OBJ and STL are supported.\n- Read", "x", ())
    assert codes(build(), [inside]) == {lo.ANCHOR_NOT_LINE_ALIGNED}


def test_two_insertions_at_one_place_have_no_order_and_are_refused(build: Build) -> None:
    first = insert(NAVIGATION, op_id="one")
    second = insert(AT_A_GLANCE, op_id="two")
    assert codes(build(), [first, second]) == {lo.OVERLAPPING_OPERATIONS}


def test_duplicate_ids_are_refused(build: Build) -> None:
    ops = [
        retitle("same", "## Scope", "## Scope and Limitations"),
        retitle("same", "## Features", "## Key Capabilities"),
    ]
    assert codes(build(), ops) == {lo.DUPLICATE_ID}


def test_an_insertion_must_end_with_its_anchor_unchanged(build: Build) -> None:
    op = make("a", lo.INSERT_BEFORE, FEATURES, NAVIGATION + "## Capabilities\n", "readme:9")
    assert codes(build(), [op]) == {lo.INSERT_NOT_BEFORE_ANCHOR}


# ------------------------------------------------------------------------------------ evidence
def test_an_operation_without_evidence_is_refused(build: Build) -> None:
    bare = lo.Op("a", lo.RETITLE, "## Scope\n", "## Scope and Limitations\n", ())
    assert lo.MISSING_EVIDENCE in codes(build(), [bare])


def test_evidence_must_resolve_against_the_facts_and_the_readme(build: Build) -> None:
    scope = f"readme:{line_of('## Scope')}"

    def with_evidence(*evidence: str) -> set[str]:
        op = lo.Op("a", lo.RETITLE, "## Scope\n", "## Scope and Limitations\n", evidence)
        return codes(build(), [op])

    assert with_evidence(scope, "dependency:ghost") == {lo.EVIDENCE_UNKNOWN}
    assert with_evidence(scope, "readme:999") == {lo.EVIDENCE_UNKNOWN}
    assert with_evidence(scope, "readme:zero") == {lo.EVIDENCE_UNKNOWN}
    assert with_evidence(scope, "tree-absent:README.md") == {lo.EVIDENCE_UNKNOWN}  # it is there
    assert with_evidence(scope, "link_target:005") == {lo.EVIDENCE_WRONG_POLARITY}  # CONTRADICTED
    assert with_evidence(scope) == set()


def test_a_fact_that_is_not_supported_cannot_back_an_operation(build: Build) -> None:
    ctx = build(drop=("dependency:guava",))
    assert lo.EVIDENCE_UNKNOWN in codes(ctx, good_ops())


# --------------------------------------------------------------------------------------- RETITLE
@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("## Scope", "## Scope and Limitations"),  # the standard name of the section
        ("## Features", "## Key Capabilities"),
        ("## Development", "## Development and Testing"),
        ("## Quick start", "## Quick Start"),  # case only
        ("### Read a scene", "### Read a Scene"),
    ],
)
def test_a_retitle_keeps_the_words_or_takes_the_standard_name(
    build: Build, old: str, new: str
) -> None:
    assert codes(build(), [retitle("a", old, new)]) == set()


def test_a_retitle_to_a_heading_with_the_same_words_ignoring_and_symbols(build: Build) -> None:
    text = README.replace("## Scope\n", "## Scope and Limits\n")
    op = retitle("a", "## Scope and Limits", "## Scope & Limits", text)
    assert codes(build(text), [op]) == set()


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("## Scope", "## Marketing Pitch", lo.RETITLE_NOT_COSMETIC),  # other words
        (
            "## Features",
            "## Scope and Limitations",
            lo.RETITLE_NOT_COSMETIC,
        ),  # another section's name
        ("## License", "## Key Capabilities", lo.RETITLE_NOT_COSMETIC),
        ("## Scope", "### Scope and Limitations", lo.RETITLE_NOT_COSMETIC),  # the level changes
        ("## Scope", "Scope and Limitations", lo.RETITLE_NOT_A_HEADING),  # not a heading any more
    ],
)
def test_a_retitle_that_changes_the_meaning_or_shape_is_refused(
    build: Build, old: str, new: str, code: str
) -> None:
    assert codes(build(), [retitle("a", old, new)]) == {code}


def test_the_h1_is_never_retitled(build: Build) -> None:
    op = retitle("a", "# Aspose.3D FOSS for Java", "# Aspose 3D for Java")
    assert codes(build(), [op]) == {lo.RETITLE_NOT_COSMETIC}


def test_a_retitle_spanning_two_lines_is_refused(build: Build) -> None:
    op = make("a", lo.RETITLE, "## Scope\n\n", "## Scope and Limitations\n\n", "readme:1")
    assert lo.RETITLE_NOT_A_HEADING in codes(build(), [op])


def test_a_heading_inside_a_code_fence_is_not_a_heading(build: Build) -> None:
    text = README.replace("Run `mvn test`.\n", "```md\n## Notes\n```\n")
    op = lo.Op("a", lo.RETITLE, "## Notes\n", "## NOTES\n", ("readme:44",))
    assert lo.RETITLE_NOT_A_HEADING in codes(build(text), [op])


def test_a_retitle_must_cite_the_line_of_its_own_anchor(build: Build) -> None:
    op = lo.Op("a", lo.RETITLE, "## Scope\n", "## Scope and Limitations\n", ("readme:1",))
    assert codes(build(), [op]) == {lo.EVIDENCE_NOT_THE_ANCHOR}


def test_a_retitle_that_would_orphan_a_link_to_the_heading_is_refused(build: Build) -> None:
    text = README.replace("Run the example.", "Run the example, see [scope](#scope).")
    assert codes(build(text), [retitle("a", "## Scope", "## Scope and Limitations")]) == {
        lo.BROKEN_ANCHOR_LINK
    }


def test_a_retitle_that_makes_two_headings_share_an_anchor_is_refused(build: Build) -> None:
    text = README.replace("## Development\n", "## Key Capabilities\n\nMore.\n\n## Development\n")
    assert codes(build(text), [retitle("a", "## Features", "## Key Capabilities")]) == {
        lo.DUPLICATE_HEADING
    }


# ---------------------------------------------------------------------------------------- REFLOW
def reflow(replacement: str, anchor: str = BADGES) -> lo.Op:
    return make("flow", lo.REFLOW, anchor, replacement, "link_target:001")


def test_a_reflow_changes_whitespace_only(build: Build) -> None:
    assert codes(build(), [reflow(BADGES.replace(")\n[", ") ["))]) == set()
    assert codes(build(), [reflow(BADGES.replace(")\n[", ")\n\n["))]) == {
        lo.REFLOW_CHANGES_LINKS  # two paragraphs where there was one
    }
    assert codes(build(), [reflow(BADGES.replace("License: MIT", "License: BSD"))]) == {
        lo.REFLOW_CHANGES_CHARACTERS
    }
    # the same characters, but a space inside a link target (or between two words) is a change
    assert codes(build(), [reflow(BADGES.replace("LICENSE", "LICEN SE"))]) == {
        lo.REFLOW_CHANGES_CHARACTERS
    }
    paragraph = "Run the example.\n"
    assert codes(build(), [reflow("Runthe example.\n", paragraph)]) == {
        lo.REFLOW_CHANGES_CHARACTERS
    }


def test_a_reflow_never_touches_code_or_a_block_that_is_not_a_paragraph(build: Build) -> None:
    code = "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0\n"
    assert codes(build(), [reflow(code.replace(" -D", "  -D"), code)]) == {
        lo.REFLOW_NOT_A_PARAGRAPH
    }
    items = "- Read OBJ files into a scene\n- Write STL files from a scene\n"
    assert codes(build(), [reflow(items.replace("\n- ", " - "), items)]) == {
        lo.REFLOW_NOT_A_PARAGRAPH
    }
    heading = "## Installation\n"
    assert codes(build(), [reflow("##  Installation\n", heading)]) == {lo.REFLOW_NOT_A_PARAGRAPH}


def test_a_reflow_must_be_a_whole_paragraph(build: Build) -> None:
    first = BADGES.splitlines(keepends=True)[0]
    assert codes(build(), [reflow(first.replace("\n", "  \n"), first)]) == {
        lo.REFLOW_NOT_A_PARAGRAPH  # the badge paragraph continues on the next line
    }


# ------------------------------------------------------------------------------------ DELETE_LINE
def delete(anchor: str = RELEASE_LINE, *evidence: str) -> lo.Op:
    return make("del", lo.DELETE_LINE, anchor, "", *(evidence or ("link_target:005",)))


def test_a_delete_removes_one_list_item_whose_link_target_is_missing(build: Build) -> None:
    assert codes(build(), [delete()]) == set()
    # no fact needed when the tree itself proves the target absent
    ctx = build(drop=("link_target:005",))
    assert codes(ctx, [delete(RELEASE_LINE, "tree-absent:RELEASE_NOTES.md")]) == set()


def test_a_delete_of_a_link_to_a_file_the_tree_holds_is_refused(build: Build) -> None:
    line = "- Read the [changelog](CHANGELOG.md).\n"
    assert codes(build(), [delete(line, "link_target:006")]) == {lo.DELETE_LINK_NOT_BROKEN}


def test_a_delete_of_a_line_that_is_not_one_list_item_is_refused(build: Build) -> None:
    plain = "Run the example.\n"
    assert codes(build(), [delete(plain)]) == {lo.DELETE_NOT_A_LIST_ITEM}
    two = RELEASE_LINE + "- Read the [changelog](CHANGELOG.md).\n"
    assert codes(build(), [delete(two)]) == {lo.DELETE_NOT_A_LIST_ITEM}
    no_link = "- Only OBJ and STL are supported.\n"
    assert codes(build(), [delete(no_link)]) == {lo.DELETE_NOT_A_LIST_ITEM}


def test_a_delete_of_an_external_link_is_refused(build: Build) -> None:
    text = README.replace(RELEASE_LINE, RELEASE_LINE + "- See [site](https://example.org/gone).\n")
    line = "- See [site](https://example.org/gone).\n"
    assert codes(build(text), [delete(line, "link_target:005")]) == {lo.DELETE_LINK_NOT_BROKEN}


def test_a_delete_must_name_the_fact_or_the_tree_that_shows_the_target_missing(
    build: Build,
) -> None:
    assert codes(build(), [delete(RELEASE_LINE, f"readme:{line_of('release notes')}")]) == {
        lo.DELETE_EVIDENCE_MISSING
    }
    assert codes(build(drop=("link_target:005",)), [delete(RELEASE_LINE, "readme:1")]) == {
        lo.DELETE_EVIDENCE_MISSING
    }


def test_a_delete_that_would_orphan_a_continuation_line_is_refused(build: Build) -> None:
    text = README.replace(RELEASE_LINE, RELEASE_LINE + "  and the rest of the item.\n")
    assert codes(build(text), [delete()]) == {lo.DELETE_ORPHANS_TEXT}


# ------------------------------------------------------------------------------- INSERT_BEFORE
def test_an_insertion_goes_before_a_heading_and_is_whole_blocks(build: Build) -> None:
    before_text = make(
        "a", lo.INSERT_BEFORE, "Run the example.\n", NAVIGATION + "Run the example.\n", "readme:1"
    )
    assert codes(build(), [before_text]) == {lo.INSERT_SHAPE}
    glued = lo.Op(
        "b",
        lo.INSERT_BEFORE,
        "## Installation\n",
        "## Navigation\n- [x](#x)\n## Installation\n",
        ("readme:1",),
    )
    assert codes(build(), [glued]) == {lo.INSERT_SHAPE}


def test_an_insertion_must_be_h2_sections_without_an_h1(build: Build) -> None:
    assert codes(build(), [insert("# Another Title\n\n")]) == {lo.INSERT_SHAPE}
    assert codes(build(), [insert("Some words.\n\n")]) == {lo.INSERT_SHAPE}


def test_an_insertion_may_only_open_a_section_with_its_own_verification(build: Build) -> None:
    assert codes(build(), [insert("## Marketing\n\n- Buy it.\n\n")]) == {
        lo.INSERT_SECTION_NOT_ALLOWED
    }


def test_a_section_the_readme_already_has_is_not_inserted_again(build: Build) -> None:
    text = README.replace("## Installation\n", "## Dependencies\n\nNone.\n\n## Installation\n")
    ops = [insert(DEPENDENCIES, "dependency:guava", f"readme:{line_of('jackson')}")]
    assert lo.INSERT_DUPLICATE_SECTION in codes(build(text), ops)


def test_an_insertion_is_short(build: Build) -> None:
    long_nav = (
        NAVIGATION + "".join("- [Key Capabilities](#key-capabilities)\n" for _ in range(200)) + "\n"
    )
    assert lo.INSERT_TOO_LONG in codes(build(), [insert(long_nav)])


def test_inserted_text_carries_no_url_the_readme_or_the_facts_do_not_know(build: Build) -> None:
    nav = NAVIGATION.replace(
        "- [License](#license)\n", "- [License](#license) https://evil.example/x\n"
    )
    assert lo.INSERT_URL_UNSUPPORTED in codes(build(), [insert(nav + AT_A_GLANCE)])
    known = DEPENDENCIES.replace(
        "for the JSON export.",
        "for the JSON export (https://central.sonatype.com/artifact/org.aspose/aspose-3d-foss).",
    )
    ops = [
        insert(
            known,
            "dependency:guava",
            "dependency:development.junit",
            f"readme:{line_of('jackson')}",
        )
    ]
    assert lo.INSERT_URL_UNSUPPORTED not in codes(build(), ops)  # a URL the README already has


def test_inserted_text_that_narrates_its_own_verification_is_refused(build: Build) -> None:
    nav = NAVIGATION.replace(
        "## Navigation\n", "## Navigation\n\nVerified against this revision.\n"
    )
    assert lo.INSERT_NARRATION in codes(build(), [insert(nav)])


# ---------------------------------------------------------------------------------- Navigation
def test_navigation_links_every_heading_it_names_by_its_slug_and_text(build: Build) -> None:
    ok = "## Navigation\n\n- [Features](#features)\n- [Installation](#installation)\n\n"
    assert codes(build(), [insert(ok)]) == set()


@pytest.mark.parametrize(
    "bad",
    [
        "## Navigation\n\n- [Features](#feature)\n- [Installation](#installation)\n\n",  # slug
        "## Navigation\n\n- [Capabilities](#features)\n- [Installation](#installation)\n\n",  # text
        "## Navigation\n\n- [Features](#features)\n- [Features](#features)\n\n",  # twice
        "## Navigation\n\n- [Features](#features)\n\n",  # one item is not a navigation
        "## Navigation\n\n- [Quick start](#quick-start)\n- [Features](#features)\n- Pay now\n\n",
        "## Navigation\n\n- [Quick start](#quick-start)\n- [Overview](#overview)\n\n",  # no such H2
    ],
)
def test_navigation_that_does_not_match_the_corrected_headings_is_refused(
    build: Build, bad: str
) -> None:
    assert codes(build(), [insert(bad)]) == {lo.NAVIGATION_MISMATCH}


def test_navigation_is_checked_against_the_headings_after_the_retitles(build: Build) -> None:
    nav = (
        "## Navigation\n\n- [Key Capabilities](#key-capabilities)\n"
        "- [Installation](#installation)\n\n"
    )
    alone = insert(nav)
    assert codes(build(), [alone]) == {lo.NAVIGATION_MISMATCH}  # no retitle yet
    both = [alone, retitle("t", "## Features", "## Key Capabilities")]
    assert codes(build(), both) == set()


def test_navigation_cites_the_readme_text_it_summarises(build: Build) -> None:
    ok = "## Navigation\n\n- [Features](#features)\n- [Installation](#installation)\n\n"
    op = make("n", lo.INSERT_BEFORE, FEATURES, ok + FEATURES, "link_target:002")
    assert codes(build(), [op]) == {lo.MISSING_EVIDENCE}


# -------------------------------------------------------------------------------- Dependencies
def deps(text: str = DEPENDENCIES, *evidence: str) -> lo.Op:
    ev = evidence or (
        "dependency:guava",
        "dependency:development.junit",
        f"readme:{line_of('jackson')}",
    )
    return make("deps", lo.INSERT_BEFORE, "## Quick start\n", text + "## Quick start\n", *ev)


def test_dependencies_are_the_supported_facts_and_what_the_readme_states(build: Build) -> None:
    assert codes(build(), [deps()]) == set()


@pytest.mark.parametrize(
    ("change", "evidence"),
    [
        (("`com.google.guava:guava:33.0`", "`com.example:evil:1.0`"), None),  # not a fact
        (
            ("`junit:junit:4.13.2` (extra `dev`)", "`junit:junit:4.13.2` (extra `prod`)"),
            None,
        ),  # word
        (("### Development Dependencies", "### Marketing Dependencies"), None),  # not a bucket
        (
            (
                "- `jackson-databind:2.17.0` for the JSON export.",
                "- `jackson-databind:9.9.9` for the JSON export.",
            ),
            None,
        ),
        (
            ("- `jackson-databind:2.17.0` for the JSON export.", "- Jackson for the JSON export."),
            None,
        ),
        (
            ("`com.google.guava:guava:33.0`", "`com.google.guava:guava:33.0`"),
            ("dependency:development.junit", "readme:30"),
        ),
        (
            (
                "- `jackson-databind:2.17.0` for the JSON export.",
                "- `jackson-databind:2.17.0` for the JSON export. [x](#nowhere)",
            ),
            None,
        ),
    ],
)
def test_dependencies_that_a_source_does_not_support_are_refused(
    build: Build, change: tuple[str, str], evidence: tuple[str, ...] | None
) -> None:
    text = DEPENDENCIES.replace(*change)
    ops = [deps(text, *evidence)] if evidence else [deps(text)]
    assert codes(build(), ops) == {lo.DEPENDENCIES_UNSUPPORTED}


def test_a_fact_listed_in_the_wrong_bucket_is_refused(build: Build) -> None:
    swapped = DEPENDENCIES.replace("`com.google.guava:guava:33.0`", "`junit:junit:4.13.2`")
    assert codes(
        build(), [deps(swapped, "dependency:development.junit", f"readme:{line_of('jackson')}")]
    ) == {lo.DEPENDENCIES_UNSUPPORTED}


def test_a_readme_stated_dependency_in_a_required_bucket_is_refused(build: Build) -> None:
    text = DEPENDENCIES.replace("`com.google.guava:guava:33.0`", "`jackson-databind:2.17.0`")
    ev = ("dependency:development.junit", f"readme:{line_of('jackson')}")
    assert codes(build(), [deps(text, *ev)]) == {lo.DEPENDENCIES_UNSUPPORTED}


def test_an_empty_dependencies_section_is_refused(build: Build) -> None:
    assert codes(
        build(), [deps("## Dependencies\n\n### Required Package Dependencies\n\n", "readme:1")]
    ) == {lo.DEPENDENCIES_UNSUPPORTED}


def test_dependency_links_must_name_a_heading_of_the_corrected_readme(build: Build) -> None:
    linked = DEPENDENCIES.replace(
        "for the JSON export.", "for the JSON export, see [Read a Scene](#read-a-scene)."
    )
    ev = ("dependency:guava", "dependency:development.junit", f"readme:{line_of('jackson')}")
    assert codes(build(), [deps(linked, *ev)]) == {
        lo.DEPENDENCIES_UNSUPPORTED
    }  # still 'Read a scene'
    both = [deps(linked, *ev), retitle("sub", "### Read a scene", "### Read a Scene")]
    assert codes(build(), both) == set()


# ------------------------------------------------------------------------------------ At a Glance
def glance_op(body: str) -> lo.Op:
    return insert("## At a Glance\n\n```mermaid\n" + body + "```\n\n")


def test_a_glance_diagram_passes_the_lint_and_uses_only_words_the_sources_state(
    build: Build,
) -> None:
    assert codes(build(), [insert(AT_A_GLANCE)]) == set()


def test_a_glance_that_is_not_one_mermaid_block_is_refused(build: Build) -> None:
    assert codes(build(), [insert("## At a Glance\n\nA picture.\n\n")]) == {lo.GLANCE_NOT_A_DIAGRAM}
    two = AT_A_GLANCE + "```mermaid\n" + build_body(GLANCE) + "```\n\n"
    assert codes(build(), [insert(two)]) == {lo.GLANCE_NOT_A_DIAGRAM}
    stray = AT_A_GLANCE.replace("```\n\n", "```\n\nA caption.\n\n")
    assert codes(build(), [insert(stray)]) == {lo.GLANCE_NOT_A_DIAGRAM}
    assert codes(build(), [glance_op("sequenceDiagram\n  A->>B: hi\n")]) == {
        lo.GLANCE_NOT_A_DIAGRAM
    }


def test_a_glance_the_diagram_lint_flags_as_stacked_or_clipping_is_refused(build: Build) -> None:
    stacked = build_body(GLANCE).replace("flowchart LR", "flowchart TD")
    assert codes(build(), [glance_op(stacked)]) == {lo.GLANCE_LINT}
    html_labels = build_body(GLANCE).replace('"htmlLabels": false', '"htmlLabels": true')
    assert lo.GLANCE_LINT in codes(build(), [glance_op(html_labels)])


def test_a_glance_label_word_no_source_states_is_refused_and_listed(build: Build) -> None:
    other = Glance(
        product=GLANCE.product,
        starting_points=("Quantum teleportation",),
        capability_columns=GLANCE.capability_columns,
        outputs=GLANCE.outputs,
    )
    refusals = lo.check_ops(build(), [glance_op(build_body(other))])
    assert [r.code for r in refusals] == [lo.GLANCE_UNSUPPORTED_WORDS]
    assert "Quantum" in refusals[0].message and "teleportation" in refusals[0].message
    assert "OBJ" not in refusals[0].message


def test_a_glance_word_a_supported_fact_value_states_is_supported(build: Build) -> None:
    other = Glance(
        product=GLANCE.product,
        starting_points=("Guava",),  # only the guava dependency fact says it
        capability_columns=GLANCE.capability_columns,
        outputs=GLANCE.outputs,
    )
    assert codes(build(), [glance_op(build_body(other))]) == set()
    assert lo.GLANCE_UNSUPPORTED_WORDS in codes(
        build(drop=("dependency:guava",)), [glance_op(build_body(other))]
    )


def test_a_glance_ordering_defect_is_tolerated_and_recorded_not_hidden(build: Build) -> None:
    six = Glance(
        product=GLANCE.product,
        starting_points=("OBJ files",),
        capability_columns=(
            ("Read OBJ files", "Write STL files", "Convert OBJ files to STL files"),
            ("Read a scene", "Write a scene", "Run the example"),
        ),
        outputs=("STL files",),
    )
    canonical = build_body(six)
    assert lo.glance_notes(canonical) == []
    swapped = canonical.replace("capr", "TMP").replace("capl", "capr").replace("TMP", "capl")
    notes = lo.glance_notes(swapped)
    assert {n["code"] for n in notes} == {"COLUMN_ORDER", "CONTRACT_COMPOSING"}
    assert codes(build(), [glance_op(swapped)]) == set()
    assert {"COLUMN_ORDER", "NOT_CANONICAL"} == lo.GLANCE_TOLERATED_DEFECTS


def test_a_glance_with_too_few_capabilities_fails_the_content_contract(build: Build) -> None:
    few = Glance(
        product=GLANCE.product,
        starting_points=("OBJ files",),
        capability_columns=(("Read OBJ files into a scene", "Write STL files from a scene"),),
        outputs=("STL files",),
    )
    refusals = lo.check_ops(build(), [glance_op(build_body(few))])
    assert [r.code for r in refusals] == [lo.GLANCE_LINT]
    assert "at least 3" in refusals[0].message


# ----------------------------------------------------------------------------- stemming and glue
def test_word_support_ignores_case_plural_and_verb_endings_but_not_other_words() -> None:
    support = "Password-encrypted workbooks, styling and the style resolver"
    assert lo.unsupported_words("Encryption of styles", support) == []
    assert lo.unsupported_words("A new existing workbook", support) == []  # glue words
    assert lo.unsupported_words("Quantum workbooks", support) == ["Quantum"]
    assert lo.unsupported_words("encrypt", "encrypted") == []
    assert lo.unsupported_words("cat", "category") == ["cat"]


def test_github_slugs_follow_github_for_the_headings_navigation_links_to() -> None:
    assert lo.github_slug("Documentation & Resources") == "documentation--resources"
    assert lo.github_slug("Scope and Limitations") == "scope-and-limitations"
    assert lo.github_slug("`code` and [link](https://x.y)") == "code-and-link"
    heads = lo.parse_headings("## A\n\n## A\n\n```\n## B\n```\n")
    assert list(lo.slug_map(heads)) == ["a", "a-1"]
