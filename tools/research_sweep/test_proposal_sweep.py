"""Regression tests for proposal_sweep.py.

Every test scans small, synthetic fixture text built to match the real marker conventions read
directly out of docs/RESEARCH_LANE_{B,C,D,E,F}.md while writing this module - never the real,
large docs/ files themselves (this project's own test convention for tools/ scripts; see
tools/discovery/test_portfolio_discovery.py's docstring for the parallel). Run directly:
`pytest tools/research_sweep/test_proposal_sweep.py` - this directory is deliberately outside
pyproject.toml's `pythonpath`/collection scope (tools/README.md's boundary from src/), so it never
runs as part of `pytest tests/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# tools/research_sweep/ is outside pyproject.toml's pythonpath, same as tools/reviewer/ and
# tools/discovery/ - inserted here rather than adding a conftest.py, matching those modules' own
# precedent (test_portfolio_discovery.py, test_research_edit.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from proposal_sweep import (  # noqa: E402
    ProposalEntry,
    check_admission,
    collect_proposals,
    find_proposals_in_text,
    render_report,
    run_sweep,
)


@pytest.fixture
def lane_dir(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    return d


# --- Case 1: a PROPOSAL correctly detected as ADMITTED (heading style, lane-E shape) -------------


def test_heading_style_proposal_admitted(lane_dir: Path) -> None:
    lane_text = (
        "# lane-e decision log\n\n"
        "### PROPOSAL E22 - `repository_investigation` (S3) is the one fact-citing job with no "
        "enum pin\n\n"
        "**Decision.** Lane E writes no fix: the schema construction lives in "
        "composition/planning.py.\n"
    )
    (lane_dir / "RESEARCH_LANE_E.md").write_text(lane_text, encoding="utf-8")
    decision_log = (
        "## 31. Provisional decision log\n\n"
        "- 2026-09-20 (loop, PROVISIONAL) - G4-W17 arrival item 90 landed: closes the S3 enum-pin "
        "gap lane E's own docs/RESEARCH_LANE_E.md PROPOSAL E22 named, via a new "
        "`citable_fact_ids` pin.\n"
    )
    (lane_dir / "DECISION_LOG.md").write_text(decision_log, encoding="utf-8")

    report = run_sweep(
        root=lane_dir.parent,
        lane_glob="docs/RESEARCH_LANE_*.md",
        admission_files=("docs/DECISION_LOG.md",),
    )

    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.entry.code == "E22"
    assert finding.status == "admitted"
    assert finding.admission_excerpt is not None
    assert "PROPOSAL E22" in finding.admission_excerpt
    assert report.unadmitted == ()
    assert report.no_identifier == ()


# --- Case 2: a PROPOSAL correctly detected as UNADMITTED (heading style, lane-D shape) -----------


def test_heading_style_proposal_unadmitted(lane_dir: Path) -> None:
    lane_text = (
        "# lane-d decision log\n\n"
        "### PROPOSAL P31 - a Rust trait's default method is never surfaced as public\n\n"
        "File: extractors/platforms/rust.py. Repositories: aspose-cells-foss/"
        "Aspose.Cells-FOSS-for-Rust.\n"
    )
    (lane_dir / "RESEARCH_LANE_D.md").write_text(lane_text, encoding="utf-8")
    decision_log = (
        "## 31. Provisional decision log\n\n"
        "- 2026-09-19 (loop, PROVISIONAL) - G4-W17 arrival item 88 landed: an unrelated fix, "
        "PROPOSAL P30 closed by measurement.\n"
    )
    (lane_dir / "DECISION_LOG.md").write_text(decision_log, encoding="utf-8")

    report = run_sweep(
        root=lane_dir.parent,
        lane_glob="docs/RESEARCH_LANE_*.md",
        admission_files=("docs/DECISION_LOG.md",),
    )

    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.entry.code == "P31"
    assert finding.status == "unadmitted"
    assert finding.admission_excerpt is None
    assert report.unadmitted == (finding,)
    assert finding in report.needs_review


# --- Case 3: edge-case formatting - lane B's plain parenthetical PROPOSAL carries no code --------
# (bold span opens mid-line at the date/tag, PROPOSAL appears later in the same bold span, and the
# entry has no letter/number/backtick identifier at all - read directly off
# docs/RESEARCH_LANE_B.md's own real "**2026-09-06 . G4-W14 . PROPOSAL (primary loop, ...)**"
# shape).


def test_bold_entry_no_identifier_is_always_flagged(lane_dir: Path) -> None:
    lane_text = (
        "# lane-b decision log\n\n"
        "- **2026-09-06 (`date` checked) - G4-W14 - PROPOSAL (primary loop, "
        "`composition/renderer.py`): `_IMPORT` is Python-shaped, so no TypeScript example ever "
        "matches an `import_path` fact.** Resume predicate: `_IMPORT` also matches a quoted "
        "module specifier; then re-run the two TypeScript repositories.\n"
    )
    (lane_dir / "RESEARCH_LANE_B.md").write_text(lane_text, encoding="utf-8")
    # Even if the admission log happens to contain the word PROPOSAL elsewhere, an entry with no
    # extractable code can never be matched to it - this is the point of the "no_identifier" class.
    decision_log = "## 31. Provisional decision log\n\nPROPOSAL (primary loop, unrelated) noted.\n"
    (lane_dir / "DECISION_LOG.md").write_text(decision_log, encoding="utf-8")

    report = run_sweep(
        root=lane_dir.parent,
        lane_glob="docs/RESEARCH_LANE_*.md",
        admission_files=("docs/DECISION_LOG.md",),
    )

    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.entry.code is None
    assert finding.entry.marker_style == "bold_entry"
    assert finding.status == "no_identifier"
    assert finding in report.needs_review
    assert "composition/renderer.py" in finding.entry.excerpt


# --- Further edge cases: lane-C date+letter bold style, and a long multi-line bold span ----------


def test_bold_entry_date_letter_style(lane_dir: Path) -> None:
    """Lane C's real shape: `- **PROPOSAL <date> <letter> · <description...>**`, sometimes
    wrapping across several lines before the closing `**` (this is why the detector uses a
    lookahead rather than trying to consume through to the closing marker - see the module
    docstring)."""
    lane_text = (
        "# lane-c decision log\n\n"
        "- **PROPOSAL 2026-09-06 A · G4-W12 · `extractors/surface/registry.py` cannot express a "
        "Maven coordinate, so every Java install fact is UNRESOLVED.** File: "
        "src/repository_presenter/components/readme/extractors/surface/registry.py, `observe()`. "
        "Defect: it builds a candidate mapping missing group_id or artifact_id and the probe "
        "never issues a request for any Java package at all, across every repository in the "
        "cohort, which is a long enough sentence to have once exceeded a bounded consumption "
        "window in an earlier draft of this detector.**\n"
    )
    (lane_dir / "RESEARCH_LANE_C.md").write_text(lane_text, encoding="utf-8")
    (lane_dir / "DECISION_LOG.md").write_text("## 31. Provisional decision log\n", encoding="utf-8")

    entries = collect_proposals(root=lane_dir.parent, lane_glob="docs/RESEARCH_LANE_*.md")
    assert len(entries) == 1
    assert entries[0].code == "A"
    assert entries[0].marker_style == "bold_entry"


def test_heading_style_backtick_wrapped_code(lane_dir: Path) -> None:
    """Lane E's other real heading shape: the code precedes a backtick-wrapped PROPOSAL, e.g.
    `### E16 \\`PROPOSAL\\` — ...`."""
    text = "### E16 `PROPOSAL` — a length-budget repair cannot verify its own revision shrinks\n"
    entries = find_proposals_in_text(text, "docs/RESEARCH_LANE_E.md")
    assert len(entries) == 1
    assert entries[0].code == "E16"
    assert entries[0].marker_style == "heading"


# --- Reference vs. entry: an inline mention of an existing PROPOSAL is not a new finding ---------


def test_inline_reference_is_not_a_new_entry() -> None:
    text = (
        "Resume predicate: PROPOSAL E15 lands, then re-run "
        "`present --repo aspose-page-foss/Aspose.Page-FOSS-for-Python`. Its previous predicates "
        "are closed.\n"
    )
    assert find_proposals_in_text(text, "docs/RESEARCH_LANE_E.md") == []


# --- Dedup: a restated/re-cited code collapses to its first occurrence ---------------------------


def test_duplicate_code_mentions_collapse_to_one_finding(lane_dir: Path) -> None:
    lane_text = (
        "# lane-c decision log\n\n"
        "- **PROPOSAL 2026-09-11 S · `fact_ids` is bounded neither in element content nor in "
        "count, so the runaway sample spends its whole token budget.**\n\n"
        "- **PROPOSAL S is CLOSED, live, at the stage it blocked.** Cells Java's "
        "`source_reconciliation` now succeeds.\n"
    )
    (lane_dir / "RESEARCH_LANE_C.md").write_text(lane_text, encoding="utf-8")
    (lane_dir / "DECISION_LOG.md").write_text("## 31. Provisional decision log\n", encoding="utf-8")

    entries = collect_proposals(root=lane_dir.parent, lane_glob="docs/RESEARCH_LANE_*.md")
    assert len(entries) == 1
    assert entries[0].code == "S"
    assert "runaway sample" in entries[0].excerpt


# --- check_admission unit-level behaviour ---------------------------------------------------------


def test_check_admission_matches_backtick_quoted_code() -> None:
    entry = ProposalEntry(
        source_file="docs/RESEARCH_LANE_B.md",
        line_no=10,
        marker_style="bold_entry",
        code="LANE-B-R5-F3",
        excerpt="a presentation finding is never asked whether its own quote lies in its section",
    )
    admission_text = (
        "item 116 (LANDED, LANE-B-W14R7-F1) ... unrelated ... "
        "closed by `8b03b34`, PROPOSAL `LANE-B-R5-F3` landed in review/independent/review.py"
    )
    finding = check_admission(entry, admission_text)
    assert finding.status == "admitted"
    assert finding.admission_excerpt is not None


def test_check_admission_does_not_confuse_similar_codes() -> None:
    """PROPOSAL P1 must not be reported admitted just because PROPOSAL P12 is mentioned."""
    entry = ProposalEntry(
        source_file="docs/RESEARCH_LANE_D.md",
        line_no=5,
        marker_style="heading",
        code="P1",
        excerpt="the shared extractor's kind table does not know Go's node types",
    )
    admission_text = "item 9 (lane D PROPOSAL P12): a different, unrelated fix landed."
    finding = check_admission(entry, admission_text)
    assert finding.status == "unadmitted"


# --- render_report smoke test ----------------------------------------------------------------------


def test_render_report_lists_every_needs_review_finding(lane_dir: Path) -> None:
    lane_text = (
        "### PROPOSAL Z9 - a defect with no admission entry anywhere\n\n"
        "Something concrete and repeatable.\n"
    )
    (lane_dir / "RESEARCH_LANE_F.md").write_text(lane_text, encoding="utf-8")
    (lane_dir / "DECISION_LOG.md").write_text("## 31. Provisional decision log\n", encoding="utf-8")
    report = run_sweep(root=lane_dir.parent, lane_glob="docs/RESEARCH_LANE_*.md")
    text = render_report(report)
    assert "UNADMITTED" in text
    assert "Z9" in text
    assert "docs/RESEARCH_LANE_F.md" in text
