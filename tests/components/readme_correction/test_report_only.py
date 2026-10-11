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
    DOCS_FACT_ID,
    DOCS_RE_ENABLE,
    add_dev_commands,
    add_doc_links,
    docs_hold_documentation,
)
from repository_presenter.components.readme_correction.detectors.sections import missing_sections
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


def test_doc_links_are_only_reported_until_a_documentation_fact_exists(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    result = add_doc_links(make_context(DOCS, tree=TREE))
    assert result.edits == ()
    (finding,) = result.findings
    assert finding.report_only_reason == "RE_ENABLE_CONDITION_UNMET"
    assert "CHANGELOG.md" in finding.candidate and finding.re_enable == DOCS_RE_ENABLE
    assert "tree:CHANGELOG.md" in finding.locators
    fact = make_fact(DOCS_FACT_ID, "docs/", evidence=(("docs/guide.md", "documentation"),))
    (edit,) = add_doc_links(make_context(DOCS, make_facts(fact), tree=TREE)).edits
    assert "CHANGELOG.md" in edit.replacement


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


def test_whole_development_and_documentation_sections_are_reported_not_inserted(
    make_context: Any, make_facts: Any, make_fact: Any
) -> None:
    readme = NL.join(["# P", "", "## Installation", "", "x", "", "## License", "", "MIT.", ""])
    ctx = make_context(readme, make_facts(*command_facts(make_fact)), tree=TREE)
    result = missing_sections(ctx)
    assert not any("## Development and Testing" in e.replacement for e in result.edits)
    assert not any("## Documentation" in e.replacement for e in result.edits)
    held = {
        f.report_only_reason
        for f in result.findings
        if f.report_only_reason and "## " in f.candidate
    }
    assert held == {"RE_ENABLE_CONDITION_UNMET"}
    assert correct(ctx).corrected.count("## Development and Testing") == 0


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
