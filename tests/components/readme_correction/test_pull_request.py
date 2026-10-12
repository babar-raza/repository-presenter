"""The pull request text of a correction: plain words, from the bundle, with no internal identifier.

Golden shapes (the reviewers' drafts): a title that names the change, a lead that says why, one
bullet per edit with the line, the quoted before and after, a reason in ordinary language and where
the evidence is (the file or the registry), what was checked with exact counts, how to review, how
to decline. Nothing in it may be an identifier of this tool's own checks, rulings, detectors, files
or run ids (``internal_identifiers`` is the list), and none of the generic composer's overclaims.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.propose.pull_request import load_pull_request_evidence
from repository_presenter.components.readme.composition.renderer import line_counts
from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.pull_request import (
    INTERNAL_IDENTIFIERS,
    compose_correction_pull_request,
    internal_identifiers,
)
from repository_presenter.components.readme_correction.settle import correct_settled

NL = chr(10)
WORDS = "aspose-words-foss/Aspose.Words-FOSS-for-Python"
JAVA = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
FORBIDDEN = (
    "Every statement",
    "No verification counts",
    "reconciled",
    "Refreshes the README",
    "sections updated",
    "Rewritten sections",
    "so text no longer clips",
    "Starting Points -> product",  # only for a diagram that has that block (see the chain test)
)
XML_AND_GRADLE = [
    "",
    "```xml",
    "<artifactId>aspose-3d-foss</artifactId>",
    "```",
    "",
    "```groovy",
    "implementation 'org.aspose:aspose-3d-foss'",
    "```",
]
OTHER_SECTIONS = [
    "## Dependencies",
    "",
    "None.",
    "",
    "## Development and Testing",
    "",
    "Run it.",
    "",
]

VERSION = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0",
        "```",
        *XML_AND_GRADLE,
        "",
        *OTHER_SECTIONS,
        "## License",
        "",
        "MIT.",
        "",
    ]
)
STRUCTURE = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
        "```",
        *XML_AND_GRADLE,
        "",
        "# Pin the `v26` module path.",
        "",
        "<details>",
        "<summary>More commands</summary>",
        "",
        "```bash",
        "mvn test",
        "```",
        "",
        *OTHER_SECTIONS,
        "## License",
        "",
        "MIT.",
        "",
    ]
)
SECTIONS = NL.join(
    [
        "# Aspose.Cells FOSS for .NET",
        "",
        "## Navigation",
        "",
        "- [Installation](#installation)",
        "- [Quick Start](#quick-start)",
        "- [License](#license)",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
        "```",
        *XML_AND_GRADLE,
        "",
        "## Quick Start",
        "",
        "Run it.",
        "",
        "## Development and Testing",
        "",
        "Run it.",
        "",
        "## License",
        "",
        "MIT.",
        "",
    ]
)


def diagram(titles: bool = True, inputs: bool = True, first_title: str = "Starting Points") -> str:
    lines = ["flowchart TD"]
    if inputs:
        lines += [
            f'  subgraph StartingPoints["{first_title}"]',
            "    direction LR",
            '    i1["An existing OBJ, STL, or 3MF file"]',
            "  end",
        ]
    lines += [
        '  PRODUCT["Aspose.3D FOSS for Java"]',
        '  subgraph Capabilities["Core Capabilities"]',
        "    direction LR",
        '    subgraph capl[" "]',
        "      direction TB",
        '      c1["Scene-graph construction and traversal"]',
        '      c2["Mesh authoring and editing"]',
        '      c3["Parameterized primitive geometry"]',
        "    end",
        '    subgraph capr[" "]',
        "      direction TB",
        '      c4["Lambert, Phong, and PBR material assignment"]',
        '      c5["Polygon triangulation"]',
        '      c6["Keyframe animation and skeletal pose data"]',
        "    end",
        "  end",
        '  subgraph Outputs["Outputs"]',
        "    direction TB",
        '    o1["OBJ, STL, or 3MF file"]',
        "  end",
        (
            "  StartingPoints --> PRODUCT --> Capabilities --> Outputs"
            if inputs
            else "  PRODUCT --> Capabilities --> Outputs"
        ),
        "",
    ]
    return NL.join(lines)


def with_diagram(body: str) -> str:
    return NL.join(
        [
            "# Aspose.3D FOSS for Java",
            "",
            "## At a Glance",
            "",
            "```mermaid",
            body + "```",
            "",
            "## Installation",
            "",
            "```bash",
            "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
            "```",
            *XML_AND_GRADLE,
            "",
            *OTHER_SECTIONS,
            "## License",
            "",
            "MIT.",
            "",
        ]
    )


def compose(
    tmp_path: Path,
    make_context: Any,
    readme: str,
    *,
    facts: Any = None,
    repository: str = JAVA,
    render: dict[str, Any] | None = None,
    tree: Any = ("README.md", "LICENSE", "pom.xml"),
) -> Any:
    ctx = make_context(readme, facts, repository=repository, tree=tree)
    result, delta = correct_settled(ctx, readme.encode())
    directory = tmp_path / "bundle"
    files.write_bundle(ctx, readme.encode(), result, delta, directory, render=render)
    return compose_correction_pull_request(
        bundle=directory,
        repository=repository,
        candidate_hash="c" * 64,
        source_revision="a" * 40,
        policy_version="p1",
    )


def above_footer(content: Any) -> str:
    return str(content.body).split("\n---\n", 1)[0]


def assert_plain(content: Any) -> None:
    text = above_footer(content) + NL + content.title
    assert internal_identifiers(text) == [], internal_identifiers(text)
    for phrase in FORBIDDEN[:-1]:
        assert phrase not in text


def test_a_version_fix_names_the_release_the_lines_and_where_the_evidence_is(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, VERSION)
    assert (
        content.title == "docs(readme): show the current release (26.7.0) in the install snippets"
    )
    body = content.body
    assert "The README pins `26.5.0` (README.md line 6)" in body
    assert "lists `26.7.0` as the current release" in body
    assert "- README.md line 6: `26.5.0` -> `26.7.0`" in body
    assert "is shown at version 26.5.0, but the registry's current stable release is 26.7.0" in body
    assert "current release `26.7.0` on the package registry (at https://repo1.maven.org/x)" in body
    assert "package name `org.aspose:aspose-3d-foss` (in `pom.xml`)" in body
    assert "(idempotent: yes)" in body and "(model calls: 0)" in body
    assert "### How to review" in body and "### How to decline" in body
    assert "- candidate_hash: " + "c" * 64 in body and "- kind: correction" in body
    assert_plain(content)


def test_two_structure_fixes_say_why_in_ordinary_words_and_own_the_inferred_part(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, STRUCTURE)
    assert "demote a stray second H1" in content.title
    assert "close an unclosed <details> block" in content.title
    body = content.body
    assert "no wording changes" in body
    assert "is a second top-level heading, and a README has one: its title, on line 1" in body
    assert "deleting the `#` instead may read better" in body
    assert "is never closed, so everything after it renders collapsed" in body
    assert "that is our reading of where it should end, so tell us if it should end" in body
    assert "template has" not in body
    assert body.count("  - evidence: README.md line") >= 2
    assert_plain(content)


def test_a_check_that_reads_text_the_broken_markup_hid_is_said_in_words_not_counted_away(
    tmp_path: Path, make_context: Any
) -> None:
    body = compose(tmp_path, make_context, STRUCTURE).body
    assert "Closing the broken markup makes text visible that the checks could not read" in body
    assert "(for example the code span `v26`)" in body
    assert "That text is yours and this change does not alter it." in body


def test_an_inserted_section_cites_the_file_and_says_what_it_states(
    tmp_path: Path, make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact("package:name", "Aspose.Cells.FOSS", evidence=(("src/Cells.csproj", None),)),
        make_fact(
            "dependency:skiasharp", "SkiaSharp 2.88.8", evidence=(("src/Cells.csproj", "x"),)
        ),
        make_fact(
            "package:target_framework",
            "netstandard2.0;net8.0",
            evidence=(("src/Cells.csproj", "x"),),
        ),
        make_fact(
            "license:spdx", "MIT", evidence=(("LICENSE", "license text states this license"),)
        ),
        make_fact("license:file", "LICENSE", evidence=(("LICENSE", None),)),
    ]
    content = compose(tmp_path, make_context, SECTIONS, facts=facts)
    body = content.body
    assert "Dependencies" in content.title and "Navigation item" in content.title
    assert (
        "the README has no Dependencies section; this one states what the repository's own "
        "files declare" in body
    )
    assert "dependency `SkiaSharp 2.88.8` (in `src/Cells.csproj`)" in body
    assert "so the new section can be reached from the contents list" in body
    assert "template's" not in body
    assert_plain(content)


def test_a_badge_names_the_package_the_registry_and_the_release(
    tmp_path: Path, make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact("package:name", "aspose-words-foss", evidence=(("pyproject.toml", None),)),
        make_fact(
            "package:published_version",
            "26.3.0",
            evidence=(("https://pypi.org/pypi/x/json", None),),
        ),
        make_fact(
            "install_command:pip",
            "pip install aspose-words-foss",
            attributes={"install_kind": "registry"},
            evidence=(("pyproject.toml", None), ("https://pypi.org/x", "package registry: found")),
        ),
    ]
    readme = NL.join(["# P", "", "Intro.", "", "## Installation", "", "x", ""])
    content = compose(tmp_path, make_context, readme, facts=facts, repository=WORDS)
    assert (
        "The README has no version badge for the published package "
        "(aspose-words-foss on PyPI, current release 26.3.0)" in content.body
    )
    assert (
        "the README shows no version badge for the published package; it is added at the front "
        "of the badge row" in content.body
    )
    assert "lacks published-version badge" not in content.body
    assert "stable order" not in content.body
    assert_plain(content)


def test_a_diagram_redraw_says_what_is_unchanged_and_claims_no_render_without_a_record(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, with_diagram(diagram()))
    assert "lay out the At a Glance diagram left to right" in content.title
    body = content.body
    assert "is drawn top-down (`flowchart TD`)" in body
    assert "drawn left to right so the labels fit their boxes." in body
    assert "All 9 labels, the 3 group titles and the chain" in body
    assert "Starting Points -> the product -> Core Capabilities -> Outputs are unchanged" in body
    assert "(compared by script)" in body and "`flowchart LR`" in body
    assert "headless browser" not in body  # no render record, so no claim about one
    assert_plain(content)


def test_the_chain_names_the_blocks_the_diagram_really_has(
    tmp_path: Path, make_context: Any
) -> None:
    without = compose(tmp_path / "a", make_context, with_diagram(diagram(inputs=False))).body
    assert (
        "All 8 labels, the 2 group titles and the chain the product -> Core Capabilities -> Outputs"
        in without
    )
    assert "Starting Points" not in without
    renamed = compose(
        tmp_path / "b", make_context, with_diagram(diagram(first_title="Inputs and formats"))
    ).body
    assert "Inputs and formats -> the product -> Core Capabilities -> Outputs" in renamed
    assert "Starting Points" not in renamed


def test_a_recorded_render_states_the_tested_range_and_the_exact_counts(
    tmp_path: Path, make_context: Any
) -> None:
    render = {
        "status": "verified",
        "releases": ["11.17.2", "11.4.1", "11.12.0", "12.1.0"],
        "fonts": 6,
        "browser": "Chrome/154",
        "diagrams": [{"horizontal": True, "clipped_fonts": 0, "word_splits": 0, "problems": 0}],
    }
    body = compose(tmp_path, make_context, with_diagram(diagram()), render=render).body
    assert "so the labels fit their boxes in the Mermaid versions tested (11.4 to 12.1)." in body
    assert "Mermaid 11.17.2, 11.4.1, 11.12.0, 12.1.0" in body
    assert "horizontal on every release, 0 clipped labels, 0 words split across lines" in body
    unverified = {"status": "not_run", "reason": "no renderer installed"}
    other = compose(
        tmp_path / "again", make_context, with_diagram(diagram()), render=unverified
    ).body
    assert "headless browser" not in other and "Mermaid versions tested" not in other


def tight(readme: str) -> str:
    lines = line_counts(readme)[0]
    filler = NL.join(f"Maintainer line {n}." for n in range(299 - lines - 3))
    return readme.replace(
        "## Installation", "## Notes" + NL + NL + filler + NL + NL + "## Installation", 1
    )


def checks_line(content: Any) -> str:
    return next(
        line
        for line in content.body.splitlines()
        if line.startswith("- We ran repository-presenter")
    )


def delta_of(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "bundle" / files.DELTA_NAME).read_text(encoding="utf-8"))


def tally(delta: dict[str, Any]) -> tuple[int, int, int, int]:
    live, after = delta["live_failures"], delta["corrected_failures"]
    names = set(live) | set(after)
    removed = sum(max(live.get(n, 0) - after.get(n, 0), 0) for n in names)
    added = sum(max(after.get(n, 0) - live.get(n, 0), 0) for n in names)
    return sum(live.values()), sum(after.values()), removed, added


def test_a_correction_that_only_removes_failures_says_how_many_of_how_many(
    tmp_path: Path, make_context: Any
) -> None:
    content = compose(tmp_path, make_context, VERSION)
    before, after, removed, added = tally(delta_of(tmp_path))
    assert added == 0 and removed > 0
    assert f"They report {before} failure(s) on yours and {after} on the corrected one: " in (
        checks_line(content)
    )
    assert f"it removes {removed} of the {before} and adds none." in checks_line(content)
    assert "validate_candidate" not in content.body and "BC-" not in content.body


def test_failures_it_adds_are_stated_and_nothing_is_called_fewer_when_hidden_text_is_now_read(
    tmp_path: Path, make_context: Any
) -> None:
    # The Cells-Go case: closing the markup resolves failures and exposes one in text it hid.
    content = compose(tmp_path, make_context, STRUCTURE)
    _before, _after, removed, added = tally(delta_of(tmp_path))
    line = checks_line(content)
    assert added > 0  # the net may even be positive; the sentence still says removes and adds
    assert f"it removes {removed} and adds {added}; the added ones are explained below." in line
    assert "fewer" not in line and "no failure that yours" not in line
    assert "Closing the broken markup makes text visible" in content.body
    assert "they now report 1 issue(s) there (for example the code span `v26`)" in content.body
    assert "new problems this change introduces" not in content.body


def test_a_redraw_that_tips_the_length_limit_says_how_many_lines_and_by_how_much(
    tmp_path: Path, make_context: Any
) -> None:
    # The Email-Cpp case: one failure resolved, one added (length), net zero.
    content = compose(tmp_path, make_context, tight(with_diagram(diagram())))
    document = json.loads(
        (tmp_path / "bundle" / files.CORRECTIONS_NAME).read_text(encoding="utf-8")
    )
    edit = next(e for e in document["edits"] if e["kind"] == "DIAGRAM_FIX")
    grown = len(edit["replacement"].splitlines()) - len(edit["original"].splitlines())
    before, after, removed, added = tally(delta_of(tmp_path))
    line = checks_line(content)
    assert added > 0 and before - after <= 0
    assert f"it removes {removed} and adds {added}" in line and "fewer" not in line
    found = re.search(
        r"the README now has ([0-9]+) lines outside collapsed blocks, "
        r"([0-9]+) over the 300-line limit",
        content.body,
    )
    assert found is not None and int(found.group(1)) - 300 == int(found.group(2)) > 0
    assert f"the redrawn diagram adds {grown} lines" in content.body
    assert "the redraw is what makes the labels fit" in content.body
    assert "(yours was within it)" in content.body and "owner ruling" not in content.body
    assert_plain(content)


def test_a_content_fix_with_a_redraw_over_the_limit_states_both_without_a_false_net(
    tmp_path: Path, make_context: Any
) -> None:
    # The PDF-Java case: a version fix and a redraw; failures removed and one length failure added.
    readme = tight(with_diagram(diagram())).replace(":26.7.0", ":26.5.0", 1)
    content = compose(tmp_path, make_context, readme)
    before, after, removed, added = tally(delta_of(tmp_path))
    line = checks_line(content)
    assert removed > added > 0
    assert f"They report {before} failure(s) on yours and {after} on the corrected one: " in line
    assert f"it removes {removed} and adds {added}; the added ones are explained below." in line
    assert "fewer" not in line and "no failure that yours" not in line
    assert "the redrawn diagram adds" in content.body
    assert_plain(content)


@pytest.mark.parametrize(
    "text",
    [
        "BC-07",
        "OD-06",
        "R7",
        "validate_candidate",
        "an allowance",
        "the detector found",
        "corrections.json",
        "DIAGRAM_FIX",
        "20261011-4b724575",
        "package:name",
        "claim_version",
    ],
)
def test_the_identifier_scan_catches_each_kind_of_internal_name(text: str) -> None:
    assert internal_identifiers(f"See {text} for why.") != []
    assert INTERNAL_IDENTIFIERS


def test_quoted_readme_text_is_not_mistaken_for_an_internal_name() -> None:
    quoted = "The README says `BC-07 and R7` on line 4."
    assert internal_identifiers(quoted, quoted=False) == []
    assert internal_identifiers(quoted) != []


def test_a_text_that_would_leak_an_identifier_is_refused_not_sent(
    tmp_path: Path, make_context: Any
) -> None:
    ctx = make_context(VERSION)
    result, delta = correct_settled(ctx, VERSION.encode())
    directory = tmp_path / "bundle"
    files.write_bundle(ctx, VERSION.encode(), result, delta, directory)
    path = directory / files.CORRECTIONS_NAME
    document = json.loads(path.read_text(encoding="utf-8"))
    document["edits"][0]["rationale"] = "BC-14 says so, see OD-06"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="internal identifiers"):
        compose_correction_pull_request(
            bundle=directory,
            repository=JAVA,
            candidate_hash="c" * 64,
            source_revision="a" * 40,
            policy_version="p1",
        )


def test_the_regenerated_candidates_composer_refuses_a_correction_bundle(
    tmp_path: Path, make_context: Any
) -> None:
    compose(tmp_path, make_context, VERSION)
    with pytest.raises(ValueError, match="correction bundle"):
        load_pull_request_evidence(tmp_path / "bundle")
    document = json.loads(
        (tmp_path / "bundle" / files.CORRECTIONS_NAME).read_text(encoding="utf-8")
    )
    assert document["send"]["pr_order"] == 1  # a content correction goes first


DEV_AND_DOCS = NL.join(
    [
        "# Aspose.3D FOSS for Java",
        "",
        "## Installation",
        "",
        "```bash",
        "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
        "```",
        *XML_AND_GRADLE,
        "",
        "## Documentation & Resources",
        "",
        "- **[API](https://example.com)**",
        "",
        "## Development and Testing",
        "",
        "Run it.",
        "",
        "## License",
        "",
        "MIT.",
        "",
    ]
)
VERIFIED_CHAIN = {
    "command_chain": "ci_job",
    "ci_job_contiguous": "true",
    "build_receipt": "r" * 64,
    "build_receipt_platform": "Linux container node:20",
}


def test_build_and_test_commands_say_where_they_come_from_and_that_they_ran_on_a_clean_clone(
    tmp_path: Path, make_context: Any, make_fact: Any
) -> None:
    facts = [
        make_fact(
            "build_test_asset:build-command",
            "mvn package",
            evidence=((".github/workflows/ci.yml", "build command; job test runs `mvn package`"),),
            attributes=VERIFIED_CHAIN,
        ),
        make_fact(
            "build_test_asset:test-command",
            "mvn test",
            evidence=((".github/workflows/ci.yml", "test command; job test runs `mvn test`"),),
            attributes=VERIFIED_CHAIN,
        ),
    ]
    content = compose(tmp_path, make_context, DEV_AND_DOCS, facts=facts)
    body = content.body
    assert "add the build and test commands, with the steps they need first" in content.title
    assert "does not show how to build and test the project" in body
    assert "the CI job `test` in `.github/workflows/ci.yml` runs them" in body
    assert "every step exited 0 when run on a clean clone of this revision" in body
    assert "(Linux container node:20)" in body
    assert "build command `mvn package`, which ran to success" in body
    assert "test command `mvn test`" in body
    assert_plain(content)


def test_links_to_files_the_tree_holds_say_so_in_plain_words(
    tmp_path: Path, make_context: Any
) -> None:
    tree = ("README.md", "LICENSE", "pom.xml", "CHANGELOG.md", "SECURITY.md")
    content = compose(tmp_path, make_context, DEV_AND_DOCS, tree=tree)
    body = content.body
    assert "link the project files the README does not mention" in content.title
    assert "the README does not mention these files, and the repository holds them" in body
    assert "`CHANGELOG.md` exists in the repository" in body
    assert "do not" not in content.title.lower()
    assert_plain(content)
