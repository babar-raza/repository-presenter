"""The pull request's title and body (``components/propose/pull_request.py``, TC-PRP-01).

Golden files pin the exact text a maintainer reads; the other tests pin what the text may not
contain (an internal artifact name, a secret-shaped value) and that it is deterministic."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from repository_presenter.components.propose.pull_request import (
    PullRequestEvidence,
    compose_pull_request,
    compose_title,
    diff_sections,
    load_pull_request_evidence,
    product_name,
    readme_sections,
)

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "propose_pr"
REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
CANDIDATE_HASH = "ab" * 32
SOURCE_REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
POLICY_VERSION = "policy-test-1"

LIVE = """# Aspose.Cells FOSS for Java

Old badge row.

## Installation

Run the old command.

## Usage

Old usage.

## License

MIT.
"""

CANDIDATE = """# Aspose.Cells FOSS for Java

New badge row and a sharper opening.

## Installation

Run the old command.

## Usage

New usage with a verified example.

```
## not a heading, it is inside a fence
```

## Key Capabilities

Reads and writes workbooks.
"""

EVIDENCE = PullRequestEvidence(
    examples_executed=7,
    examples_total=9,
    install_verified=True,
    checks_passed=11,
    checks_total=11,
)

#: Names of this project's own artifacts and directories: none may reach a maintainer.
INTERNAL_NAMES = (
    "reports/",
    "runs/",
    "candidates/",
    "dispositions",
    "facts.json",
    "validation.json",
    "examples.json",
    "review.json",
    "manifest.json",
    "calls.jsonl",
    "README.patch",
    "BC-",
    "READY_FOR_PROPOSAL",
)


def _compose(live: str | None = LIVE, candidate: str = CANDIDATE, **overrides: object):  # type: ignore[no-untyped-def]
    fields: dict[str, object] = {
        "candidate_readme": candidate,
        "live_readme": live,
        "repository": REPOSITORY,
        "evidence": EVIDENCE,
        "candidate_hash": CANDIDATE_HASH,
        "source_revision": SOURCE_REVISION,
        "policy_version": POLICY_VERSION,
    }
    fields.update(overrides)
    return compose_pull_request(**fields)  # type: ignore[arg-type]


def test_the_title_and_body_match_their_golden_files() -> None:
    content = _compose()
    assert content.title == (GOLDEN / "title.txt").read_text(encoding="utf-8").rstrip("\n")
    assert content.body == (GOLDEN / "body.md").read_text(encoding="utf-8")


def test_the_title_names_the_product_and_counts_the_sections_changed() -> None:
    # Introduction and Usage rewritten, Key Capabilities added, License removed: four sections.
    assert (
        _compose().title
        == "docs(readme): refresh Aspose.Cells FOSS for Java README (4 sections updated)"
    )


def test_one_changed_section_reads_in_the_singular() -> None:
    candidate = LIVE.replace("Old usage.", "Better usage.")
    assert _compose(candidate=candidate).title.endswith("(1 section updated)")


def test_a_repository_with_no_readme_is_an_addition_not_a_refresh() -> None:
    content = _compose(live=None)
    assert content.title == "docs(readme): add Aspose.Cells FOSS for Java README"
    assert "no README yet" in content.body


def test_a_whitespace_only_difference_changes_no_section() -> None:
    candidate = LIVE.replace("\n", "\r\n") + "\n\n"
    content = _compose(candidate=candidate)
    assert content.title.endswith("README (formatting only)")
    assert "only formatting and whitespace" in content.body


def test_the_text_is_deterministic() -> None:
    assert _compose() == _compose()


def test_the_body_keeps_the_provenance_line_the_effect_reads_back() -> None:
    """``effect._CANDIDATE_HASH_LINE`` recognizes our own pull request by this line."""
    body = _compose().body
    assert re.search(r"candidate_hash:\s*([0-9a-f]{64})", body)
    assert f"- source_revision: {SOURCE_REVISION}" in body
    assert f"- policy_version: {POLICY_VERSION}" in body


def test_the_body_says_how_to_review_and_how_to_decline() -> None:
    body = _compose().body
    assert "### How to review" in body and "Files changed" in body
    assert "### How to decline" in body and "Close this pull request" in body
    assert "authorizes" in body


@pytest.mark.parametrize("live", [LIVE, None])
def test_no_internal_artifact_name_reaches_the_maintainer(live: str | None) -> None:
    content = _compose(live=live)
    text = content.title + "\n" + content.body
    leaked = [name for name in INTERNAL_NAMES if name in text]
    assert leaked == []


def test_only_headings_and_counts_are_quoted_never_readme_prose_or_secret_shaped_values() -> None:
    secret = "ghs_" + "A1b2C3d4" * 5
    candidate = CANDIDATE.replace("Reads and writes workbooks.", f"token {secret}")
    content = _compose(candidate=candidate)
    assert secret not in content.title + content.body


def test_unknown_verification_is_stated_not_invented() -> None:
    body = _compose(evidence=PullRequestEvidence()).body
    assert "No verification counts were recorded" in body
    assert "executed in isolation" not in body


def test_a_failed_install_check_is_not_reported_as_verified() -> None:
    body = _compose(evidence=PullRequestEvidence(install_verified=False)).body
    assert "NOT verified" in body


def test_a_readme_with_no_examples_to_run_says_so() -> None:
    body = _compose(evidence=PullRequestEvidence(examples_executed=0, examples_total=0)).body
    assert "none that need running" in body


def test_a_long_section_list_is_truncated_with_a_count() -> None:
    candidate = "# P\n\n" + "".join(f"## Section {n}\n\ntext {n}\n\n" for n in range(20))
    body = _compose(live="# P\n", candidate=candidate).body
    assert "and 8 more" in body


# --- the pieces ---------------------------------------------------------------------------------


def test_sections_ignore_headings_inside_code_fences() -> None:
    headings = [heading for heading, _ in readme_sections(CANDIDATE)]
    assert headings == ["Introduction", "Installation", "Usage", "Key Capabilities"]


def test_reordering_alone_is_not_an_update() -> None:
    reordered = "# T\n\n## B\n\nb\n\n## A\n\na\n"
    original = "# T\n\n## A\n\na\n\n## B\n\nb\n"
    assert diff_sections(original, reordered).count == 0


def test_a_repeated_heading_is_compared_occurrence_by_occurrence() -> None:
    before = "# T\n\n## Example\n\none\n\n## Example\n\ntwo\n"
    after = "# T\n\n## Example\n\none\n\n## Example\n\nTWO\n"
    changes = diff_sections(before, after)
    assert changes.updated == ("Example",) and changes.count == 1


def test_the_product_is_the_first_title_with_markup_removed() -> None:
    assert product_name("# [Aspose.X](https://x.example) `FOSS`\n", REPOSITORY) == "Aspose.X FOSS"
    assert product_name("no title here\n", REPOSITORY) == "Aspose.Cells-FOSS-for-Java"
    assert product_name("```\n# in a fence\n```\n", REPOSITORY) == "Aspose.Cells-FOSS-for-Java"


def test_the_title_helper_states_the_count_and_noun() -> None:
    changes = diff_sections(LIVE, CANDIDATE)
    assert (
        compose_title("P", LIVE, changes) == "docs(readme): refresh P README (4 sections updated)"
    )


# --- the evidence read from a sealed bundle -----------------------------------------------------


def _bundle(tmp_path: Path, receipts: object, checks: object) -> Path:
    if receipts is not None:
        (tmp_path / "examples.json").write_text(json.dumps(receipts), encoding="utf-8")
    if checks is not None:
        (tmp_path / "validation.json").write_text(json.dumps({"checks": checks}), encoding="utf-8")
    return tmp_path


def test_evidence_counts_come_from_the_bundles_own_records(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path,
        [{"outcome": "EXECUTED"}, {"outcome": "EXECUTED"}, {"outcome": "NEEDS_INPUT"}],
        [
            {"id": "BC-01", "verdict": "PASS"},
            {"id": "BC-02", "verdict": "PASS"},
            {"id": "BC-03", "verdict": "FAIL"},
        ],
    )
    assert load_pull_request_evidence(bundle) == PullRequestEvidence(2, 3, True, 2, 3)


def test_missing_or_malformed_records_leave_the_counts_unknown(tmp_path: Path) -> None:
    assert load_pull_request_evidence(tmp_path) == PullRequestEvidence()
    (tmp_path / "examples.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "validation.json").write_text('{"checks": "nope"}', encoding="utf-8")
    assert load_pull_request_evidence(tmp_path) == PullRequestEvidence()
