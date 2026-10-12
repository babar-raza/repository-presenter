"""add_dev_commands and add_doc_links (and the Development and Documentation sections built from the
same facts) only report until their facts are reliable; every skipped edit has a typed reason."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.detectors.additions import (
    DEV_RE_ENABLE,
    DOCS_RE_ENABLE,
    add_dev_commands,
    add_doc_links,
    docs_hold_documentation,
)
from repository_presenter.components.readme_correction.detectors.sections import missing_sections
from repository_presenter.components.readme_correction.docs import DOCS_FACT_ID
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import (
    REPORT_ONLY_REASONS,
    Finding,
    InvalidEditError,
)
from repository_presenter.components.readme_correction.settle import correct_settled

NL = chr(10)
DEV = NL.join(["# P", "", "## Development and Testing", "", "Run it the usual way.", "", ""]) + (
    NL.join(["## License", "", "MIT.", ""])
)
DOCS = NL.join(
    ["# P", "", "## Documentation & Resources", "", "- **[API](https://example.com)**", "", ""]
) + NL.join(["## License", "", "MIT.", ""])
TREE = ("README.md", "LICENSE", "CHANGELOG.md", "docs/guide.md")


def command_facts(make_fact: Any, **attributes: str) -> list[Any]:
    return [
        make_fact(
            "build_test_asset:build-command",
            "mvn package",
            evidence=(("pom.xml", "x"),),
            attributes=attributes or None,
        ),
        make_fact(
            "build_test_asset:test-command",
            "mvn test",
            evidence=(("pom.xml", "x"),),
            attributes=attributes or None,
        ),
    ]


def test_dev_commands_are_only_reported_with_their_candidate_and_the_re_enable_condition(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(DEV, make_facts(*command_facts(make_fact)))
    result = add_dev_commands(ctx)
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.report_only_reason == "RE_ENABLE_CONDITION_UNMET"
    assert "mvn package" in finding.candidate and "mvn test" in finding.candidate
    assert finding.re_enable == DEV_RE_ENABLE and "ONE CI job" in finding.re_enable
    assert set(finding.fact_ids) >= {
        "build_test_asset:build-command",
        "build_test_asset:test-command",
    }


def test_dev_commands_edit_once_a_job_chain_and_a_build_receipt_are_recorded(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = command_facts(make_fact, ci_job_contiguous="true", build_receipt="receipt-1")
    (edit,) = add_dev_commands(make_context(DEV, make_facts(*facts))).edits
    assert "mvn package" in edit.replacement
    half = command_facts(make_fact, ci_job_contiguous="true")  # no receipt
    assert add_dev_commands(make_context(DEV, make_facts(*half))).edits == ()


def test_a_command_already_shown_is_reported_as_already_shown(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = DEV.replace("Run it the usual way.", "Run `mvn clean package` and `mvn test`.")
    result = add_dev_commands(make_context(readme, make_facts(*command_facts(make_fact))))
    assert result.edits == ()
    assert {f.report_only_reason for f in result.findings} == {"ALREADY_SHOWN"}


def test_the_docs_link_waits_for_a_documentation_fact_but_a_community_file_does_not(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    result = add_doc_links(make_context(DOCS, tree=TREE))
    (edit,) = result.edits  # CHANGELOG.md is a path of the pinned tree: its link needs no more
    assert "CHANGELOG.md" in edit.replacement and "docs/" not in edit.replacement
    assert edit.locators == ("tree:CHANGELOG.md",)
    (finding,) = result.findings  # docs/ holds markdown, but no fact says any of it is prose
    assert finding.report_only_reason == "RE_ENABLE_CONDITION_UNMET"
    assert "docs/" in finding.candidate and finding.re_enable == DOCS_RE_ENABLE
    assert finding.locators == ("tree:docs/",)
    fact = make_fact(DOCS_FACT_ID, "docs/", evidence=(("docs/guide.md", "documentation"),))
    documented = add_doc_links(make_context(DOCS, make_facts(fact), tree=TREE))
    (edit,) = documented.edits
    assert "CHANGELOG.md" in edit.replacement and "[Documentation](docs/)" in edit.replacement
    assert edit.fact_ids == (DOCS_FACT_ID,) and documented.findings == ()


def test_a_docs_directory_holding_only_assets_is_never_called_documentation(
    make_context: Any,
) -> None:
    assets = (
        "README.md",
        "docs/media/banner-readme.png",
        "docs/nuget/icon.png",
        "docs/nuget/README.md",
    )
    ctx = make_context(DOCS, tree=assets)
    assert not docs_hold_documentation(ctx)
    result = add_doc_links(ctx)
    assert {f.report_only_reason for f in result.findings} == {"DOCS_HOLDS_NO_DOCUMENTATION"}
    assert not any("docs/" in f.candidate for f in result.findings)
    assert docs_hold_documentation(make_context(DOCS, tree=TREE))


def test_a_whole_development_section_is_reported_but_a_documentation_section_of_tree_links_is_not(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = NL.join(["# P", "", "## Installation", "", "x", "", "## License", "", "MIT.", ""])
    ctx = make_context(readme, make_facts(*command_facts(make_fact)), tree=TREE)
    result = missing_sections(ctx)
    assert not any("## Development and Testing" in e.replacement for e in result.edits)
    docs = [e for e in result.edits if "## Documentation" in e.replacement]
    assert len(docs) == 1 and "CHANGELOG.md" in docs[0].replacement
    assert "docs/" not in docs[0].replacement  # no fact says docs/ holds prose
    held = {
        f.report_only_reason
        for f in result.findings
        if f.report_only_reason and "## " in f.candidate
    }
    assert held == {"RE_ENABLE_CONDITION_UNMET"}
    assert correct(ctx).corrected.count("## Development and Testing") == 0
    assert correct(ctx).corrected.count("## Documentation & Resources") == 1


def test_a_report_only_reason_is_one_of_the_closed_set() -> None:
    assert Finding("d", 0, "", "r", report_only_reason="ALREADY_SHOWN").report_only_reason
    with pytest.raises(InvalidEditError):
        Finding("d", 0, "", "r", report_only_reason="BECAUSE")
    assert "RE_ENABLE_CONDITION_UNMET" in REPORT_ONLY_REASONS


def test_the_bundle_lists_every_report_only_candidate_with_its_typed_reason(
    tmp_path: Path, make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    ctx = make_context(DEV, make_facts(*command_facts(make_fact)))
    result, delta = correct_settled(ctx, DEV.encode())
    directory = tmp_path / "bundle"
    files.write_bundle(ctx, DEV.encode(), result, delta, directory)
    document = json.loads((directory / files.CORRECTIONS_NAME).read_text(encoding="utf-8"))
    (entry,) = [e for e in document["report_only"] if e["detector"] == "add_dev_commands"]
    assert entry["report_only_reason"] == "RE_ENABLE_CONDITION_UNMET"
    assert "mvn package" in entry["candidate"] and entry["re_enable"] == DEV_RE_ENABLE
    assert "build_test_asset:build-command" in entry["evidence"]["fact_ids"]
    assert all(f["detector"] != "add_dev_commands" for f in document["unapplied_findings"])
    assert validation_delta(ctx, result, DEV.encode())["introduced"] == []


# ------------------------------------------------------------------- chains, receipts, sentences
VERIFIED = {
    "command_chain": "ci_job",
    "ci_job_contiguous": "true",
    "build_receipt": "r" * 64,
    "build_receipt_platform": "Linux container node:20",
}


def verified_facts(make_fact: Any, **extra: str) -> list[Any]:
    return command_facts(make_fact, **{**VERIFIED, **extra})


def test_a_verified_chain_is_edited_in_with_its_setup_before_the_commands(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = [
        make_fact(
            "build_test_asset:build-command",
            "mvn package",
            evidence=(("pom.xml", "x"),),
            attributes={**VERIFIED, "precondition": "mvn -B dependency:resolve"},
        ),
        make_fact(
            "build_test_asset:test-command",
            "mvn test",
            evidence=(("pom.xml", "x"),),
            attributes={**VERIFIED, "precondition": "mvn -B dependency:resolve"},
        ),
    ]
    (edit,) = add_dev_commands(make_context(DEV, make_facts(*facts))).edits
    assert "```bash\nmvn -B dependency:resolve\nmvn package\nmvn test\n```" in edit.replacement
    assert edit.replacement.index("dependency:resolve") < edit.replacement.index("mvn package")


@pytest.mark.parametrize(
    ("recorded", "code"),
    [
        ("NOT_RUN: the chain has not been run on a clean clone", "NO_BUILD_RECEIPT"),
        ("NOT_VERIFIED: make is not available on this machine", "NO_BUILD_RECEIPT"),
        ("FAILED: `mvn test` exited 1: Tests run: 3, Failures: 1", "BUILD_RECEIPT_FAILED"),
        ("TIMED_OUT: `mvn test` did not finish within 1500 seconds", "BUILD_RECEIPT_FAILED"),
    ],
)
def test_a_chain_without_a_passing_receipt_is_held_with_the_reason_it_has(
    make_context: Any, make_facts: Any, make_fact: Any, recorded: str, code: str
) -> None:
    attributes = {k: v for k, v in VERIFIED.items() if not k.startswith("build_receipt")}
    facts = command_facts(make_fact, **attributes, build_receipt_failed=recorded)
    result = add_dev_commands(make_context(DEV, make_facts(*facts)))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.report_only_reason == code
    assert recorded.partition(": ")[2] in finding.reason
    assert "mvn test" in finding.candidate


def test_a_command_left_out_of_the_chain_is_held_and_never_printed(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = [
        make_fact(
            "build_test_asset:build-command",
            "mvn package",
            evidence=(("pom.xml", "x"),),
            attributes={"chain_excluded": "it is not a step of the CI job ci.yml job test"},
        ),
        make_fact(
            "build_test_asset:test-command",
            "mvn test",
            evidence=(("pom.xml", "x"),),
            attributes=VERIFIED,
        ),
    ]
    result = add_dev_commands(make_context(DEV, make_facts(*facts)))
    (edit,) = result.edits
    assert "mvn test" in edit.replacement and "mvn package" not in edit.replacement
    (held,) = result.findings
    assert held.report_only_reason == "NOT_IN_VERIFIED_CHAIN"
    assert "is not a step of the CI job" in held.reason and held.candidate == "mvn package"


def test_the_ci_matrix_and_release_sentences_need_no_receipt(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = [
        make_fact(
            "build_test_asset:ci-matrix",
            "os=ubuntu-latest,windows-latest;python-version=3.11,3.12",
            evidence=((".github/workflows/ci.yml", "job test strategy.matrix axes os"),),
        ),
        make_fact(
            "build_test_asset:release-workflow",
            ".github/workflows/release.yml",
            evidence=((".github/workflows/release.yml", "release step; job publish"),),
        ),
    ]
    (edit,) = add_dev_commands(make_context(DEV, make_facts(*facts))).edits
    assert "runs on Ubuntu and Windows, with Python 3.11 and 3.12" in edit.replacement
    release = "Releases run through the [release workflow](.github/workflows/release.yml)"
    assert release in edit.replacement
    assert "```" not in edit.replacement  # no command: nothing to run, nothing to prove
    assert set(edit.fact_ids) == {"build_test_asset:ci-matrix", "build_test_asset:release-workflow"}


def test_a_ci_matrix_the_readme_already_states_in_words_is_not_repeated(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    matrix = make_fact(
        "build_test_asset:ci-matrix",
        "python-version=3.10,3.11,3.12",
        evidence=((".github/workflows/ci.yml", "matrix"),),
    )
    stated = DEV.replace("Run it the usual way.", "CI runs the suite on Python 3.10 through 3.12.")
    assert add_dev_commands(make_context(stated, make_facts(matrix))).edits == ()
    elsewhere = DEV.replace("Run it the usual way.", "The suite needs Python 3.10 or newer.")
    assert len(add_dev_commands(make_context(elsewhere, make_facts(matrix))).edits) == 1


def test_a_setup_line_the_readme_already_shows_is_not_printed_again(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    facts = [
        make_fact(
            "build_test_asset:test-command",
            "pytest -q",
            evidence=(("pyproject.toml", "x"),),
            attributes={**VERIFIED, "precondition": "python -m pip install -e .\nnpm install"},
        )
    ]
    readme = DEV.replace("Run it the usual way.", "First `python -m pip install -e .` once.")
    (edit,) = add_dev_commands(make_context(readme, make_facts(*facts))).edits
    assert "```bash\nnpm install\npytest -q\n```" in edit.replacement
    assert "pip install -e" not in edit.replacement


def test_a_tool_the_chain_installs_first_is_not_held_as_needing_an_install(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    fact = make_fact(
        "build_test_asset:build-command",
        "python -m build",
        evidence=(("pyproject.toml", "x"),),
        attributes={**VERIFIED, "precondition": "pip install build"},
    )
    (edit,) = add_dev_commands(make_context(DEV, make_facts(fact))).edits
    assert "pip install build\npython -m build" in edit.replacement
    bare = make_fact(
        "build_test_asset:build-command", "python -m build", evidence=(("pyproject.toml", "x"),)
    )
    (held,) = add_dev_commands(make_context(DEV, make_facts(bare))).findings
    assert held.report_only_reason == "NEEDS_INSTALL_FIRST"


def test_an_addition_goes_in_front_of_the_rule_that_closes_its_section(
    make_context: Any,
) -> None:
    readme = NL.join(
        [
            "# P",
            "",
            "## Documentation & Resources",
            "",
            "- **[API](https://example.com)**",
            "",
            "---",
            "",
            "## License",
            "",
            "MIT.",
            "",
        ]
    )
    (edit,) = add_doc_links(make_context(readme, tree=TREE)).edits
    lines = (readme[: edit.start] + edit.replacement + readme[edit.end :]).splitlines()
    assert lines.index("- **[Changelog](CHANGELOG.md)** — release history.") < lines.index("---")
    assert lines[lines.index("---") - 1] == ""  # the rule still closes the section
    # a setext heading's underline is not a rule: nothing lands between its text and its dashes
    setext = NL.join(
        ["# P", "", "## Documentation", "", "Guide", "-----", "", "## License", "", "MIT.", ""]
    )
    (setext_edit,) = add_doc_links(make_context(setext, tree=TREE)).edits
    assert setext[: setext_edit.start].endswith("-----\n")


def test_a_receipt_that_ran_the_command_as_printed_settles_the_install_question(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """``python -m pytest`` needs pytest, which a chain may install through an extra the CI line
    names (``pip install -e '.[test]'``): when the chain ran to success as printed, it is not held
    as needing an install the evidence does not name."""
    attributes = {**VERIFIED, "precondition": "python -m pip install -e '.[test]'"}
    fact = make_fact(
        "build_test_asset:test-command",
        "python -m pytest -q",
        evidence=((".github/workflows/ci.yml", "job test runs `python -m pytest -q`"),),
        attributes=attributes,
    )
    (edit,) = add_dev_commands(make_context(DEV, make_facts(fact))).edits
    assert "python -m pip install -e '.[test]'\npython -m pytest -q" in edit.replacement
    unverified = make_fact(
        "build_test_asset:test-command",
        "python -m pytest -q",
        evidence=((".github/workflows/ci.yml", "x"),),
    )
    (held,) = add_dev_commands(make_context(DEV, make_facts(unverified))).findings
    assert held.report_only_reason == "NEEDS_INSTALL_FIRST"


def test_an_addition_before_a_never_closed_details_block_survives_the_structure_fix(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    """A section whose ``<details>`` is never closed cannot take an addition at its end (it would
    be collapsed). The addition goes in front of the opener instead, so closing the block (the
    structure fix) and adding to the section agree: a second run finds nothing more to do."""
    readme = NL.join(
        [
            "# P",
            "",
            "## Development and Testing",
            "",
            "Run it the usual way.",
            "",
            "<details>",
            "<summary>More</summary>",
            "",
            "Extra notes.",
            "",
            "## License",
            "",
            "MIT.",
            "",
        ]
    )
    fact = make_fact(
        "build_test_asset:test-command",
        "mvn test",
        evidence=(("pom.xml", "x"),),
        attributes=VERIFIED,
    )
    ctx = make_context(readme, make_facts(fact))
    result, _delta = correct_settled(ctx, readme.encode())
    assert {"add_dev_commands", "unclosed_details"} <= {e.detector for e in result.edits}
    corrected = result.corrected
    assert corrected.index("mvn test") < corrected.index("<details>")  # visible, before the block
    assert corrected.index("</details>") < corrected.index("## License")
    again, _ = correct_settled(make_context(corrected, make_facts(fact)), corrected.encode())
    assert again.edits == []
