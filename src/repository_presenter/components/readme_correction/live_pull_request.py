"""The pull request text for a live-anchored bundle: the operations, by kind, with their evidence.

Written from the bundle alone (``corrections.json``, ``validation_delta.json``, ``facts.json``) for
the maintainer who will read it. It claims only what the bundle records and what a person can see
in **Files changed**: the README changes at the listed places and nowhere else, and each place is
listed with the line, the text before and after, and what supports it. It reuses the correction
text's count of the checks, which are the ones about the maintainers' own README (commands,
examples, links, version and edition claims); the layout and wording checks this tool applies to
the READMEs it writes are never described as faults of the live one.

It names no internal artifact (``pull_request.internal_identifiers``), and it never says a model
wrote or checked the text: the checks call none, and the operations' authorship is not its claim.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme_correction.bundle import (
    CORRECTIONS_NAME,
    DELTA_NAME,
    ORIGINAL_NAME,
)
from repository_presenter.components.readme_correction.live_ops import (
    DELETE_LINE,
    REFLOW,
    RETITLE,
    retitle_reason,
)
from repository_presenter.components.readme_correction.pull_request import (
    _PREFIX,
    _TITLE_LIMIT,
    _clip,
    _delta_lines,
    _fact_text,
    _facts,
    _join,
    _json,
    internal_identifiers,
)
from repository_presenter.core.facts import Fact

_SECTION_WHY = {
    "Navigation": "a list of links to the README's own sections, so a visitor can jump to one",
    "Dependencies": (
        "the packages the project file declares, and the optional one the README itself names"
    ),
    "At a Glance": "a small diagram drawn only from words the README and the project already use",
}


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _title(operations: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    titles: list[str] = []
    for op in operations:
        counts[op["kind"]] = counts.get(op["kind"], 0) + 1
        titles += [t for t in op["sections"] if t not in titles]
    parts: list[str] = []
    if counts.get(RETITLE):
        parts.append(f"retitle {_plural(counts[RETITLE], 'heading')}")
    if titles:
        parts.append(f"add {_join(titles)}")
    if counts.get(REFLOW):
        parts.append("join the badge lines")
    if counts.get(DELETE_LINE):
        parts.append("remove a broken link")
    phrase = ", ".join(parts)
    if parts and len(_PREFIX + phrase) <= _TITLE_LIMIT:
        return _PREFIX + phrase
    return f"{_PREFIX}{_plural(len(operations), 'evidenced edit')} to headings, sections and links"


def _evidence(op: dict[str, Any], facts: dict[str, Fact]) -> str:
    parts: list[str] = []
    for item in op["evidence"]:
        if item["status"] == "README_TEXT":
            parts.append(f"README.md line {item['ref'].split(':', 1)[1]}")
        elif item["status"] == "TREE_ABSENT":
            parts.append(f"`{item['value']}` is not in the repository")
        elif item["ref"] in facts:
            parts.append(_fact_text(facts[item["ref"]]))
    return "; ".join(parts) or "the README's own text"


def _lines(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def _bullet(op: dict[str, Any], facts: dict[str, Fact]) -> list[str]:
    kind, line = op["kind"], op["line"]
    evidence = f"  - evidence: {_evidence(op, facts)}"
    if kind == RETITLE:
        before, after = op["anchor"].strip(), op["replacement"].strip()
        why = (
            "the same words in the heading style the Aspose FOSS READMEs share"
            if retitle_reason(before, after) == "same_words"
            else "the name the Aspose FOSS READMEs give this section"
        )
        return [f"- README.md line {line}: `{before}` -> `{after}`", f"  - why: {why}", evidence]
    if kind == REFLOW:
        count = _lines(op["anchor"])
        return [
            f"- README.md lines {line}-{line + count - 1}: {count} badge lines are joined onto one "
            "line (the same badges and links; only the line breaks change)",
            "  - why: the Aspose FOSS READMEs keep the badges in one row",
            evidence,
        ]
    if kind == DELETE_LINE:
        return [
            f"- README.md line {line}: removed `{_clip(op['anchor'].strip())}`",
            "  - why: it links to a file the repository does not contain",
            evidence,
        ]
    heading = ", ".join(f"`## {t}`" for t in op["sections"])
    why = "; ".join(f"{t}: {_SECTION_WHY[t]}" for t in op["sections"] if t in _SECTION_WHY)
    return [f"- inserted {heading} before line {line}", f"  - why: {why}", evidence]


def compose_live_anchored_pull_request(
    *,
    bundle: Path,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    policy_version: str,
) -> PullRequestContent:
    document = _json(bundle / CORRECTIONS_NAME)
    delta = _json(bundle / DELTA_NAME)
    facts = _facts(bundle)
    operations: list[dict[str, Any]] = document["operations"]
    original_file = bundle / ORIGINAL_NAME
    original = original_file.read_text(encoding="utf-8") if original_file.is_file() else ""
    stability = document.get("stability", {})
    changes: list[str] = []
    for op in operations:
        changes += _bullet(op, facts)
    details = [" ".join(note["detail"].split()) for note in document.get("diagram_notes", [])]
    notes = (
        [
            f"- The diagram check reports {_plural(len(details), 'layout note')} on the new "
            f"At a Glance diagram, which we left as drawn: {'; '.join(details)}"
        ]
        if details
        else []
    )
    checks = [
        "- Only `README.md` changes, and only at the places listed: with those places removed, the "
        "proposed README and yours are identical. Every other line is byte for byte yours.",
        "- Each listed place was checked against your README, the repository's files and the "
        "facts read from this revision: a heading keeps its words or takes the section's standard "
        "name, a link in an added section points at a heading that exists, a listed dependency "
        "is one the project file declares or your README names, and a removed link is one whose "
        "target is missing.",
        *_delta_lines(delta, [], original),
        *notes,
        "- Applying the same changes again gives the same bytes "
        f"(deterministic: {'yes' if stability.get('deterministic') else 'NO'}). These checks make "
        f"no model call (model calls: {stability.get('provider_calls', 0)}).",
    ]
    kinds = {op["kind"] for op in operations}
    shapes = [
        text
        for kind, text in (
            (RETITLE, "a heading"),
            (REFLOW, "a line break"),
            (DELETE_LINE, "one removed list item whose link target is missing"),
            ("INSERT_BEFORE", "a section added before one of your headings"),
        )
        if kind in kinds
    ]
    lead = (
        f"This brings `README.md` to the shared Aspose FOSS README structure with "
        f"{_plural(len(operations), 'change')}, each listed below with its line, the text before "
        "and after, and what supports it. No sentence you wrote is rewritten: a change is "
        f"{_join(shapes)}, and nothing else."
    )
    above = "\n".join(
        [
            lead,
            "",
            "### What changes",
            *changes,
            "",
            "### How this was checked",
            *checks,
            "",
            "### How to review",
            "Open **Files changed**: each hunk is one change listed above, and nothing else in "
            "README.md differs.",
            "",
            "### How to decline",
            "Close this pull request without merging. It will not be reopened or recreated for "
            "this proposal; a new pull request appears only after someone explicitly authorizes "
            "a new proposal for this repository.",
        ]
    )
    leaked = internal_identifiers(above, quoted=False)
    if leaked:
        raise ValueError(f"the pull request text would carry internal identifiers: {leaked}")
    footer = "\n".join(
        [
            "---",
            "Proposed by repository-presenter, a tool that compares each Aspose FOSS README with "
            "its repository. Provenance:",
            f"- candidate_hash: {candidate_hash}",
            f"- source_revision: {source_revision}",
            f"- policy_version: {policy_version}",
            "- kind: live_anchored",
            "",
        ]
    )
    return PullRequestContent(title=_title(operations), body=above + "\n\n" + footer)
