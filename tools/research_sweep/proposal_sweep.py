"""Sweep `docs/RESEARCH_LANE_*.md` for `PROPOSAL` findings not yet cross-referenced in the shared
admission log, and report them.

Commissioned by `docs/investigations/05-production-autonomy.md` §1 class H ("written findings sit
unadmitted to the shared work queue for days, with no mechanical sweep") and §2's own named fix for
it ("a periodic grep of `docs/RESEARCH_LANE_*.md` for `PROPOSAL` headings not yet cross-referenced
... would close the 'sat unnoticed' failure mode mechanically... a sweep can guarantee visibility,
never guarantee correct disposition"), landed under `docs/PRODUCTION_ROADMAP.md` WS5's own queued
hardening item ("a scheduled sweep of `docs/RESEARCH_LANE_*.md` for un-admitted `PROPOSAL`
headings"). READ-ONLY, REPORT-ONLY: this module never edits a `RESEARCH_LANE_*.md` file, never
edits the admission log, and never admits anything on its own - see the module docstring's own
"Detection vs. admission" note below and `tools/README.md`'s standing boundary (owner/reviewer
tooling never writes to `docs/`).

## Where the admission log actually lives (a discrepancy worth recording)

Investigation 05 and this task's own commissioning text both cite "`docs/RESEARCH_AND_GUIDELINES.md`
§29" as the shared arrival list. Live cross-checking (2026-09-23) found that citation is stale:
`RESEARCH_AND_GUIDELINES.md`'s current §29 is "Ecosystem extraction," unrelated; `RESEARCH_AND_GUIDELINES.md`
§3005 records its own history here - "`docs/RESEARCH_AND_GUIDELINES.md`'s own §31 no longer exists
in that file (moved to this file on 2026-09-08)." Every lane file's own header agrees: each of
`docs/RESEARCH_LANE_{B,C,D,E,F}.md` opens with "entries in DECISION_LOG.md section 31 shape... the
owner reviews asynchronously and merges what belongs in §31." So the real, current admission ledger
is `docs/DECISION_LOG.md`'s own "## 31. Provisional decision log" section, not
`RESEARCH_AND_GUIDELINES.md` §29 - this module cross-references against `DECISION_LOG.md` by
default (`DEFAULT_ADMISSION_FILES`), and against whatever files `--admission-file` names instead,
so a future renumbering does not silently break detection.

## Detection vs. admission

Per investigation 05 §2: "detection is automatable; admission is not." This module answers only
"does this PROPOSAL have any citation back to it in the admission log," never "is this PROPOSAL
correct" or "where should it be queued." A PROPOSAL this module reports as admitted may still be
un-landed (investigated, deferred, or still open) - the admission log's own text already says so,
and that is exactly what a human/owner reviews next. A PROPOSAL this module reports as unadmitted
needs a human or supervising agent to read it and decide whether, and how, to admit it - this
module never does that step itself.

## The two marker conventions this module recognises

Read directly off real entries in the five current lane files before writing these patterns (never
guessed):

1. **Heading style** (lanes D, E, F; example: `docs/RESEARCH_LANE_E.md`):
   ``### E16 `PROPOSAL` `` followed by a dash and prose, `### PROPOSAL E22 - ...`,
   `### PROPOSAL P1 — ...`.
2. **Bold-entry style** (lanes B, C; example: `docs/RESEARCH_LANE_C.md`):
   `- **PROPOSAL 2026-09-06 A ; G4-W12 ; ...**` (date + one/two-letter code), or lane B's two
   sub-shapes: `**PROPOSAL (primary loop, core/ecosystems.py):** ...` (bold starts at
   PROPOSAL) and `- **2026-09-06 ; G4-W14 ; PROPOSAL (primary loop, extractors/surface/
   extractor.py): ...**` (bold starts at the date, PROPOSAL mid-span), plus a later lane-B
   sub-shape carrying a backtick shared-code identifier: PROPOSAL LANE-B-R5-F3 (shared code) -
   backtick-quoted in the real file, elided here to keep this docstring's own backticks unambiguous.

Lane B's plain parenthetical shape (`PROPOSAL (primary loop, ...)`) carries **no extractable
identifier** - this is the deliberately-kept edge case: such an entry can never be mechanically
matched against the admission log (there is nothing distinctive enough to search for without an
unacceptable false-positive/false-negative rate), so it is always reported, tagged
``code is None``, for a human to check by hand. Silently treating "no code" as "can't be wrong, skip
it" would recreate exactly the class-H gap this tool exists to close.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LANE_GLOB = "docs/RESEARCH_LANE_*.md"
DEFAULT_ADMISSION_FILES: tuple[str, ...] = ("docs/DECISION_LOG.md",)

# --- Marker patterns -------------------------------------------------------------------------
# Both patterns are intentionally line-anchored (`re.MULTILINE`, `^`) so an inline *reference* to
# an existing proposal ("resume predicate: PROPOSAL E15 lands") is not mistaken for a fresh entry -
# only a literal markdown heading or the lead bold span of a list item/paragraph counts as a marker.

# Style 1: a markdown heading (2-6 #'s) whose text contains the literal word PROPOSAL.
_HEADING_PATTERN = re.compile(r"^#{2,6}[ \t]+(?P<rest>.*\bPROPOSAL\b.*)$", re.MULTILINE)

# Style 2: the bold span opening a line (optionally after a `- ` list marker) contains PROPOSAL
# within its first ~180 characters (DOTALL-scoped so a wrapped line still counts). This is a
# zero-width lookahead - it only anchors the *start* of the entry; it deliberately does not try to
# locate the bold span's closing `**`, because several real entries' bold text runs for multiple
# lines/paragraphs and a bounded "consume up to the closing **" pattern silently drops entries
# whenever that span is longer than the bound (measured directly against docs/RESEARCH_LANE_C.md
# while building this module: a naive bounded-consumption pattern under-counted by exactly the
# entries whose bold span exceeded the bound, including a real one, PROPOSAL AG).
_BOLD_ENTRY_START_PATTERN = re.compile(
    r"^[ \t]*-?[ \t]*\*\*(?=(?s:(?:(?!\*\*).){0,180}?\bPROPOSAL\b))",
    re.MULTILINE,
)
_BOLD_ENTRY_WINDOW = 250  # chars scanned after the bold marker for code extraction + excerpt

# --- Code extraction, tried in this priority order for each candidate window --------------------
_CODE_BACKTICK = re.compile(r"PROPOSAL\s*`([A-Z0-9][A-Z0-9-]{1,60})`")  # PROPOSAL `LANE-B-R5-F3`
_CODE_DATE_LETTER = re.compile(  # PROPOSAL 2026-09-06 A ·  /  PROPOSAL 2026-09-17 AG ·
    r"PROPOSAL\s+\d{4}-\d{2}-\d{2}\s+([A-Z]{1,2})\b"
)
_CODE_INLINE = re.compile(r"PROPOSAL\s+([A-Z]{1,4}\d{1,3})\b")  # PROPOSAL E22 / PROPOSAL P1
_CODE_BARE_LETTER = re.compile(r"PROPOSAL\s+([A-Z]{1,2})\b")  # PROPOSAL S / PROPOSAL N (restated)
_CODE_PATTERNS = (_CODE_BACKTICK, _CODE_DATE_LETTER, _CODE_INLINE, _CODE_BARE_LETTER)

_WHITESPACE = re.compile(r"\s+")


def _extract_code(window: str) -> str | None:
    """Return the first PROPOSAL identifier found in ``window``, or ``None`` if the entry carries
    no machine-checkable identifier (lane B's plain parenthetical shape)."""
    for pattern in _CODE_PATTERNS:
        match = pattern.search(window)
        if match:
            return match.group(1)
    return None


def _clean_excerpt(text: str, limit: int = 220) -> str:
    """Collapse whitespace/markdown noise for a short, readable excerpt."""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    collapsed = collapsed.replace("**", "")
    if len(collapsed) > limit:
        return collapsed[:limit].rstrip() + "…"
    return collapsed


@dataclass(frozen=True)
class ProposalEntry:
    """One detected `PROPOSAL` marker in a `docs/RESEARCH_LANE_*.md` file."""

    source_file: str  # path relative to the repo root, e.g. "docs/RESEARCH_LANE_E.md"
    line_no: int  # 1-based line number of the marker
    marker_style: str  # "heading" or "bold_entry"
    code: str | None  # extracted identifier, or None if the entry carries none
    excerpt: str  # short, cleaned text for a human to recognise the finding by


def find_proposals_in_text(text: str, source_file: str) -> list[ProposalEntry]:
    """Return every `PROPOSAL` marker detected in ``text`` (one lane file's content)."""
    entries: list[ProposalEntry] = []

    for match in _HEADING_PATTERN.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        rest = match.group("rest")
        code = _extract_code("PROPOSAL " + rest)  # normalise "<code> PROPOSAL" -> code-searchable
        entries.append(
            ProposalEntry(
                source_file=source_file,
                line_no=line_no,
                marker_style="heading",
                code=code,
                excerpt=_clean_excerpt(rest),
            )
        )

    for match in _BOLD_ENTRY_START_PATTERN.finditer(text):
        line_no = text.count("\n", 0, match.start()) + 1
        window = text[match.end() : match.end() + _BOLD_ENTRY_WINDOW]
        code = _extract_code(window)
        entries.append(
            ProposalEntry(
                source_file=source_file,
                line_no=line_no,
                marker_style="bold_entry",
                code=code,
                excerpt=_clean_excerpt(window, limit=180),
            )
        )

    entries.sort(key=lambda e: e.line_no)
    return entries


def load_lane_files(
    lane_glob: str = DEFAULT_LANE_GLOB, root: Path = REPO_ROOT
) -> list[Path]:
    """Return every file matching ``lane_glob`` under ``root``, sorted for deterministic output."""
    return sorted(root.glob(lane_glob))


def collect_proposals(
    lane_glob: str = DEFAULT_LANE_GLOB, root: Path = REPO_ROOT
) -> list[ProposalEntry]:
    """Scan every matching lane file and return every detected `PROPOSAL` entry, deduplicated.

    Deduplication: entries sharing the same non-``None`` ``code`` are collapsed to their first
    occurrence in file-then-line order - a later mention of the same code (a status update such as
    "PROPOSAL S is CLOSED", or a corroborating cross-lane reference such as "lane E's PROPOSAL E3")
    is the same finding, not a second one. Entries with no code (``code is None``) are never
    collapsed against each other - each is reported on its own, since nothing distinguishes a
    restatement from a genuinely new uncoded finding without a code to key on.
    """
    all_entries: list[ProposalEntry] = []
    for path in load_lane_files(lane_glob, root):
        try:
            rel = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            rel = str(path)
        text = path.read_text(encoding="utf-8")
        all_entries.extend(find_proposals_in_text(text, rel))

    seen_codes: set[str] = set()
    deduped: list[ProposalEntry] = []
    for entry in sorted(all_entries, key=lambda e: (e.source_file, e.line_no)):
        if entry.code is not None:
            if entry.code in seen_codes:
                continue
            seen_codes.add(entry.code)
        deduped.append(entry)
    return deduped


# --- Cross-reference against the admission log ---------------------------------------------------


@dataclass(frozen=True)
class SweepFinding:
    """One `ProposalEntry` plus its admission status."""

    entry: ProposalEntry
    status: str  # "admitted" | "unadmitted" | "no_identifier"
    admission_excerpt: str | None  # short context from the admission log, when status=="admitted"


def _load_admission_text(admission_files: tuple[str, ...], root: Path) -> str:
    chunks: list[str] = []
    for rel in admission_files:
        path = root / rel
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def check_admission(entry: ProposalEntry, admission_text: str) -> SweepFinding:
    """Classify one entry against the admission log's text.

    A code-bearing entry is "admitted" the moment its exact identifier appears anywhere in the
    admission log next to the word PROPOSAL (`PROPOSAL <code>`, optionally backtick-quoted) - this
    matches how every real admission in `docs/DECISION_LOG.md` cites its source finding (`"lane D
    PROPOSAL P2"`, `"PROPOSAL E9's two discriminators"`, or "PROPOSAL " followed by a
    backtick-quoted code such as LANE-B-W14R6-F1).
    "Admitted" here means "reached the shared queue," not "landed/fixed" - an admission entry that
    reads "investigated, not landed" still counts, matching this task's own definition and
    investigation 05's own class-H framing (the failure was findings sitting *unseen*, not findings
    sitting unresolved).

    An entry with no extractable code can never be matched this way (see the module docstring's
    "Detection vs. admission" note) and is always classified ``"no_identifier"`` - always surfaced,
    never silently assumed clear.
    """
    if entry.code is None:
        return SweepFinding(entry=entry, status="no_identifier", admission_excerpt=None)

    pattern = re.compile(r"\bPROPOSAL\s*`?" + re.escape(entry.code) + r"`?\b")
    match = pattern.search(admission_text)
    if match is None:
        return SweepFinding(entry=entry, status="unadmitted", admission_excerpt=None)

    start = max(0, match.start() - 60)
    end = min(len(admission_text), match.end() + 100)
    context = _clean_excerpt(admission_text[start:end], limit=200)
    return SweepFinding(entry=entry, status="admitted", admission_excerpt=context)


@dataclass(frozen=True)
class SweepReport:
    """The full outcome of one sweep pass."""

    findings: tuple[SweepFinding, ...]
    lane_files: tuple[str, ...]
    admission_files: tuple[str, ...]

    @property
    def admitted(self) -> tuple[SweepFinding, ...]:
        return tuple(f for f in self.findings if f.status == "admitted")

    @property
    def unadmitted(self) -> tuple[SweepFinding, ...]:
        return tuple(f for f in self.findings if f.status == "unadmitted")

    @property
    def no_identifier(self) -> tuple[SweepFinding, ...]:
        return tuple(f for f in self.findings if f.status == "no_identifier")

    @property
    def needs_review(self) -> tuple[SweepFinding, ...]:
        """Everything this sweep could not confirm as admitted - the tool's actionable output."""
        return tuple(f for f in self.findings if f.status != "admitted")


def run_sweep(
    *,
    root: Path = REPO_ROOT,
    lane_glob: str = DEFAULT_LANE_GLOB,
    admission_files: tuple[str, ...] = DEFAULT_ADMISSION_FILES,
) -> SweepReport:
    """Run one full, read-only sweep: detect every PROPOSAL, classify each against the admission
    log's current text. Never writes anything - see the module docstring's "Detection vs.
    admission" note. This is the function to call from a recurring cadence (a cron-style wrapper,
    a heartbeat check, or `tools/reviewer/reviewer_check.py`) - it takes no interactive input and
    produces a plain, serialisable result.
    """
    entries = collect_proposals(lane_glob, root)
    admission_text = _load_admission_text(admission_files, root)
    findings = tuple(check_admission(entry, admission_text) for entry in entries)
    lane_files = tuple(
        str(p.relative_to(root)).replace("\\", "/") for p in load_lane_files(lane_glob, root)
    )
    return SweepReport(
        findings=findings, lane_files=lane_files, admission_files=admission_files
    )


_BARE_LETTER_CODE = re.compile(r"^[A-Z]{1,2}$")  # e.g. "L", "AG" - no digit, no "LANE-" prefix

_BARE_LETTER_CAVEAT = (
    "Note on bare 1-2 letter codes (docs/RESEARCH_LANE_C.md's own convention): this project's "
    "admission log does not always restate a bare letter code when it admits the finding it names "
    "- some admissions instead cite the lane, repository, and failing check in prose (e.g. "
    "\"[lane C, Slides Java, BC-10]\") with no literal \"PROPOSAL L\" anywhere. This detector can "
    "only match an exact code citation (see the module's own \"Detection vs. admission\" "
    "docstring note), so bare-letter findings below are the most likely to include false "
    "positives - spot-check these first by reading the lane file's own excerpt and searching the "
    "admission log by content, not only by code."
)


def render_report(report: SweepReport) -> str:
    """Render ``report`` as human-readable text - the one-off-check output shape."""
    lines: list[str] = []
    add = lines.append
    add("PROPOSAL sweep")
    add(f"  lane files scanned : {len(report.lane_files)} ({', '.join(report.lane_files)})")
    add(f"  admission log(s)   : {', '.join(report.admission_files)}")
    add(f"  total detected     : {len(report.findings)}")
    add(f"  admitted           : {len(report.admitted)}")
    add(f"  unadmitted         : {len(report.unadmitted)}")
    add(f"  no identifier      : {len(report.no_identifier)}")
    add("")

    if not report.needs_review:
        add("Nothing needs review - every detected PROPOSAL is cross-referenced in the admission "
            "log.")
        return "\n".join(lines) + "\n"

    add("NEEDS REVIEW (detected, not confirmed admitted - a human/agent decides, this tool does "
        "not):")
    add("")

    has_bare_letter = any(
        f.entry.code and _BARE_LETTER_CODE.match(f.entry.code) for f in report.unadmitted
    )
    if has_bare_letter:
        add(_BARE_LETTER_CAVEAT)
        add("")

    by_file: dict[str, list[SweepFinding]] = {}
    for finding in report.unadmitted + report.no_identifier:
        by_file.setdefault(finding.entry.source_file, []).append(finding)

    for source_file in sorted(by_file):
        findings = sorted(by_file[source_file], key=lambda f: f.entry.line_no)
        add(f"{source_file} ({len(findings)} finding(s)):")
        for finding in findings:
            e = finding.entry
            if finding.status == "unadmitted":
                tag = f"UNADMITTED code={e.code}"
            else:
                tag = "NO IDENTIFIER - always needs manual review"
            add(f"  - line {e.line_no} ({e.marker_style}, {tag})")
            add(f"      {e.excerpt}")
        add("")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proposal_sweep.py",
        description=(
            "READ-ONLY. Scans docs/RESEARCH_LANE_*.md for PROPOSAL findings and reports which "
            "ones have no citation back to them in the admission log (default: "
            "docs/DECISION_LOG.md). Never edits any file, never admits anything - detection "
            "only, per docs/investigations/05-production-autonomy.md class H."
        ),
    )
    parser.add_argument(
        "--lane-glob",
        default=DEFAULT_LANE_GLOB,
        help="glob (relative to the repo root) for lane files to scan",
    )
    parser.add_argument(
        "--admission-file",
        action="append",
        dest="admission_files",
        default=None,
        metavar="PATH",
        help=(
            "a file (relative to the repo root) to cross-reference PROPOSAL codes against "
            "(repeatable). Default: docs/DECISION_LOG.md."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root to resolve --lane-glob/--admission-file against",
    )
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help=(
            "exit 1 if anything needs review (unadmitted or no-identifier). Off by default: this "
            "tool reports, it does not gate anything, per its own read-only/report-only scope."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    admission_files = tuple(args.admission_files) if args.admission_files else DEFAULT_ADMISSION_FILES
    report = run_sweep(
        root=args.root, lane_glob=args.lane_glob, admission_files=admission_files
    )
    print(render_report(report), end="")
    if args.fail_on_findings and report.needs_review:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
