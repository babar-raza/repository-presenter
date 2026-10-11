"""The title and body of the README-proposal pull request (TC-PRP-01).

Every presenter pull request used to carry the same title and a body of three hashes, which told a
maintainer nothing they could act on. This module composes both deterministically from three inputs
only - the candidate README, the README the target currently has, and the counts the bundle's own
validation and example receipts recorded - so the same inputs always yield the same bytes and a
second ``propose`` run finds nothing to update.

The text speaks to the maintainer who will review the pull request: what changed (sections, by
heading, from the diff against the live file), what was verified (counts), how to review it, how to
decline it, and the provenance footer the effect itself reads back (``candidate_hash:`` is how it
recognizes its own pull request). It names no internal artifact and carries no value that could be a
secret: headings and counts only.
"""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.core.examples import RECEIPTS_FILENAME

VALIDATION_FILENAME = "validation.json"
#: The blocking check that verifies the README's install command against the package manifest.
INSTALL_CHECK = "BC-02"
#: Section headings listed per category before the remainder is summarized as a count.
MAX_LISTED_SECTIONS = 12
MAX_PRODUCT_LENGTH = 60
#: The pre-heading text of a README (its title, badges and opening) has no heading of its own.
INTRODUCTION = "Introduction"

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_H2 = re.compile(r"^##\s+(.+?)\s*#*\s*$")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


@dataclass(frozen=True)
class PullRequestEvidence:
    """What the sealed bundle recorded about its own verification: counts, nothing else.

    ``None`` means the bundle does not say (an ecosystem that verifies nothing, or a record that is
    absent or unreadable) - never a guess."""

    examples_executed: int | None = None
    examples_total: int | None = None
    install_verified: bool | None = None
    checks_passed: int | None = None
    checks_total: int | None = None


@dataclass(frozen=True)
class PullRequestContent:
    title: str
    body: str


@dataclass(frozen=True)
class SectionChanges:
    """Section headings by what the diff against the live README did to them."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    updated: tuple[str, ...] = ()
    lines_added: int = 0
    lines_removed: int = 0

    @property
    def count(self) -> int:
        return len(self.added) + len(self.removed) + len(self.updated)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_pull_request_evidence(bundle: Path) -> PullRequestEvidence:
    """The verification counts of the sealed ``bundle``, read from its validation record and its
    example receipts. A missing or malformed record leaves that count unknown."""
    receipts = _read_json(bundle / RECEIPTS_FILENAME)
    executed = total = None
    if isinstance(receipts, list):
        rows = [row for row in receipts if isinstance(row, dict)]
        total = len(rows)
        executed = sum(1 for row in rows if row.get("outcome") == "EXECUTED")
    validation = _read_json(bundle / VALIDATION_FILENAME)
    install = passed = checks = None
    if isinstance(validation, dict) and isinstance(validation.get("checks"), list):
        rows = [row for row in validation["checks"] if isinstance(row, dict)]
        checks = len(rows)
        passed = sum(1 for row in rows if row.get("verdict") == "PASS")
        install_rows = [row for row in rows if row.get("id") == INSTALL_CHECK]
        if install_rows:
            install = install_rows[0].get("verdict") == "PASS"
    return PullRequestEvidence(executed, total, install, passed, checks)


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip("\n")


def readme_sections(text: str) -> list[tuple[str, str]]:
    """``(heading, body)`` for the opening (before the first ``##`` heading) and for each ``##``
    section, in order. A ``## `` line inside a fenced code block is code, not a heading."""
    sections: list[tuple[str, list[str]]] = [(INTRODUCTION, [])]
    fence: str | None = None
    for line in text.replace("\r\n", "\n").split("\n"):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
        heading = None if fence is not None or marker else _H2.match(line)
        if heading:
            sections.append((_plain(heading.group(1)), []))
        else:
            sections[-1][1].append(line)
    return [(heading, _normalize("\n".join(lines))) for heading, lines in sections]


def _keyed(sections: Sequence[tuple[str, str]]) -> dict[tuple[str, int], str]:
    """Sections by ``(heading, occurrence)`` so a repeated heading is still compared one-to-one."""
    seen: dict[str, int] = {}
    keyed: dict[tuple[str, int], str] = {}
    for heading, body in sections:
        occurrence = seen.get(heading, 0)
        seen[heading] = occurrence + 1
        keyed[(heading, occurrence)] = body
    return keyed


def diff_sections(live: str, candidate: str) -> SectionChanges:
    """Which sections the candidate adds, removes or rewrites relative to ``live``, and the size
    of the line diff. Reordering alone is not an update."""
    before, after = _keyed(readme_sections(live)), _keyed(readme_sections(candidate))
    added = tuple(key[0] for key in after if key not in before)
    removed = tuple(key[0] for key in before if key not in after)
    updated = tuple(key[0] for key in after if key in before and before[key] != after[key])
    lines_added = lines_removed = 0
    for line in difflib.unified_diff(
        _normalize(live).split("\n"), _normalize(candidate).split("\n"), lineterm="", n=0
    ):
        if line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            lines_removed += 1
    return SectionChanges(added, removed, updated, lines_added, lines_removed)


def _plain(markdown: str) -> str:
    """A heading or title as plain text on one line: images dropped, links reduced to their text,
    backticks and asterisks removed (underscores are kept: they occur in names)."""
    text = _LINK.sub(r"\1", _IMAGE.sub("", markdown))
    return " ".join(text.replace("`", "").replace("*", "").split())


def product_name(candidate: str, repository: str) -> str:
    """The product the README is about: its first ``#`` title, else the repository's own name."""
    fence: str | None = None
    for line in candidate.replace("\r\n", "\n").split("\n"):
        marker = _FENCE.match(line)
        if marker:
            fence = None if fence == marker.group(1)[0] else marker.group(1)[0]
            continue
        title = None if fence else _H1.match(line)
        if title:
            name = _plain(title.group(1))
            if name:
                return name[:MAX_PRODUCT_LENGTH].rstrip()
    return repository.split("/", 1)[-1][:MAX_PRODUCT_LENGTH]


def compose_title(product: str, live: str | None, changes: SectionChanges) -> str:
    """``docs(readme): refresh <Product> README (<n> sections updated)`` - ``add`` when the target
    has no README yet, ``(formatting only)`` when no section differs."""
    if live is None:
        return f"docs(readme): add {product} README"
    if changes.count == 0:
        return f"docs(readme): refresh {product} README (formatting only)"
    noun = "section" if changes.count == 1 else "sections"
    return f"docs(readme): refresh {product} README ({changes.count} {noun} updated)"


def _listed(label: str, headings: Sequence[str]) -> str | None:
    if not headings:
        return None
    shown = ", ".join(f"**{heading}**" for heading in headings[:MAX_LISTED_SECTIONS])
    rest = len(headings) - MAX_LISTED_SECTIONS
    return f"- {label} ({len(headings)}): {shown}" + (f" and {rest} more" if rest > 0 else "")


def _verified_lines(evidence: PullRequestEvidence) -> list[str]:
    lines: list[str] = []
    if evidence.examples_total is not None and evidence.examples_executed is not None:
        if evidence.examples_total == 0:
            lines.append("- Code examples: the README presents none that need running.")
        else:
            lines.append(
                f"- Code examples: {evidence.examples_executed} of {evidence.examples_total} "
                "executed in isolation against this revision of the repository."
            )
    if evidence.install_verified is not None:
        lines.append(
            "- Install command: "
            + (
                "check passed against the project's package manifest and the registry."
                if evidence.install_verified
                else "NOT verified - review it before merging."
            )
        )
    if evidence.checks_total is not None and evidence.checks_passed is not None:
        lines.append(
            f"- Automated checks: {evidence.checks_passed} of {evidence.checks_total} passed "
            "(facts, links, examples, preserved content, secrets, structure, independent review)."
        )
    return lines or ["- No verification counts were recorded for this proposal."]


def compose_pull_request(
    *,
    candidate_readme: str,
    live_readme: str | None,
    repository: str,
    evidence: PullRequestEvidence,
    candidate_hash: str,
    source_revision: str,
    policy_version: str,
) -> PullRequestContent:
    """The title and body for one candidate against the README the target has now."""
    product = product_name(candidate_readme, repository)
    changes = diff_sections(live_readme or "", candidate_readme)
    title = compose_title(product, live_readme, changes)

    changed = [
        line
        for line in (
            _listed("Rewritten sections", changes.updated),
            _listed("New sections", changes.added),
            _listed("Removed sections", changes.removed),
        )
        if line
    ]
    if live_readme is None:
        changed = ["- The repository has no README yet; this adds one."]
    elif not changed:
        changed = ["- No section differs; only formatting and whitespace change."]
    size = f"{changes.lines_added} lines added, {changes.lines_removed} removed"

    body = "\n".join(
        [
            f"Refreshes the README of **{product}** from the repository as it stands at revision "
            f"`{source_revision[:12]}`. Only `README.md` changes.",
            "",
            "### What changed",
            *changed,
            f"- Size of the change: {size}.",
            "",
            "### What was verified",
            *_verified_lines(evidence),
            "",
            "### How to review",
            "Open **Files changed**: the whole proposal is the `README.md` diff there. Every "
            "statement in the new text was checked against this repository at the revision "
            "above, and your existing README was reconciled section by section.",
            "",
            "### How to decline",
            "Close this pull request without merging. It will not be reopened or recreated for "
            "this proposal; a new pull request appears only after someone explicitly authorizes "
            "a new proposal for this repository.",
            "",
            "---",
            "Proposed by repository-presenter. Provenance:",
            f"- candidate_hash: {candidate_hash}",
            f"- source_revision: {source_revision}",
            f"- policy_version: {policy_version}",
            "",
        ]
    )
    return PullRequestContent(title=title, body=body)
