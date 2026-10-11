"""The pull request text for a correction: what was changed, with its evidence, and nothing more.

A regenerated candidate's text says the README was refreshed and reconciled section by section;
that would misdescribe a correction, so a correction carries its own: every edit with the line it
is on, the quoted original, the replacement and the facts that dictate it, then how to verify the
patch, how to decline, and the same provenance block the shared effect expects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme_correction.bundle import CORRECTIONS_NAME

_TITLES = {
    "FALSE_CLAIM_FIX": "correct a README claim the repository contradicts",
    "MISSING_SECTION": "add a README section its facts fill",
    "BROKEN_LINK": "repair a broken README link",
    "STRUCTURE_FIX": "repair broken README markup",
    "MISSING_INFO": "add verified information the README lacks",
}
_LABELS = {
    "FALSE_CLAIM_FIX": "Claim the repository contradicts",
    "MISSING_SECTION": "Section added from verified facts",
    "BROKEN_LINK": "Broken link repaired",
    "STRUCTURE_FIX": "Broken markup repaired",
    "MISSING_INFO": "Verified information added",
}
_SHOWN = 120


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= _SHOWN else flat[: _SHOWN - 3] + "..."


def _item(edit: dict[str, Any]) -> list[str]:
    evidence = ", ".join(
        f"`{e['fact_id']}` ({e['status']})" if e["fact_id"] else f"`{e['value']}`"
        for e in edit["evidence"]
    )
    if edit["kind"] == "MISSING_SECTION":
        heading = next(line for line in edit["replacement"].splitlines() if line.startswith("## "))
        change = f"inserted `{heading}` before line {edit['line']}"
    elif edit["kind"] == "MISSING_INFO":
        shown = next((ln for ln in edit["replacement"].splitlines() if ln.strip()), "")
        extra = len([ln for ln in edit["replacement"].splitlines() if ln.strip()]) - 1
        more = f" (+{extra} more line(s))" if extra > 0 else ""
        change = f"added at line {edit['line']}: `{_clip(shown)}`{more}"
    elif not edit["original"]:
        change = f"inserted `{edit['replacement'].strip()}` before line {edit['line']}"
    else:
        change = (
            f"line {edit['line']}: `{_clip(edit['original'])}` -> `{_clip(edit['replacement'])}`"
        )
    return [f"- {change}", f"  - why: {edit['rationale']}", f"  - evidence: {evidence}"]


def compose_correction_pull_request(
    *,
    bundle: Path,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    policy_version: str,
) -> PullRequestContent:
    document = json.loads((bundle / CORRECTIONS_NAME).read_text(encoding="utf-8"))
    edits: list[dict[str, Any]] = document["edits"]
    kinds = sorted({edit["kind"] for edit in edits})
    product = repository.split("/", 1)[1]
    title = (
        f"{product}: {_TITLES[kinds[0]]}"
        if len(edits) == 1
        else f"{product}: {len(edits)} verified README corrections"
    )
    sections: list[str] = []
    for kind in kinds:
        sections += [
            f"### {_LABELS[kind]}",
            *(line for e in edits if e["kind"] == kind for line in _item(e)),
        ]
        sections.append("")
    body = "\n".join(
        [
            f"Corrects the README of **{product}** against the repository at revision "
            f"`{source_revision[:12]}`. Only `README.md` changes, and only the {len(edits)} "
            "edit(s) listed here: every other byte of your README is unchanged.",
            "",
            *sections,
            "### How to verify",
            "Open **Files changed**: each hunk is one listed edit. The evidence is the "
            "repository's own files and the package registry's current reading; no model wrote "
            "any of this text.",
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
            "- kind: correction",
            "",
        ]
    )
    return PullRequestContent(title=title, body=body)
