"""The pull request text for a correction: what changes, how it was checked, and nothing more.

Written from the bundle alone (``corrections.json``, ``validation_delta.json``): one bullet per edit
with the line, the quoted before and after for a text edit and the evidence fact with its status,
the exact counts the validators and the re-run recorded, how to review it and how to decline it,
then the provenance block the shared effect reads back. It claims only what the bundle records: a
diagram is called render-verified only when the bundle holds a render record, a check is counted
only as the delta counts it, and it never says a statement was "checked" in general.

A regenerated candidate's text (``components/propose/pull_request.py``) describes a refreshed
README reconciled section by section, which would misdescribe a correction; that composer refuses a
correction bundle (``load_pull_request_evidence``) so the two cannot be mixed up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme_correction.bundle import CORRECTIONS_NAME, DELTA_NAME
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse

_SHOWN = 120
_PREFIX = "docs(readme): "


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= _SHOWN else flat[: _SHOWN - 3] + "..."


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    return document if isinstance(document, dict) else {}


def _category(edit: dict[str, Any]) -> str:
    kind, detector = edit["kind"], edit["detector"]
    if kind == "DIAGRAM_FIX":
        return "diagram"
    if kind == "FALSE_CLAIM_FIX":
        return "version" if detector == "claim_version" else "claims"
    if kind == "STRUCTURE_FIX":
        return "structure"
    if kind == "BROKEN_LINK":
        return "link"
    if kind == "MISSING_SECTION" or (kind == "MISSING_INFO" and detector == "missing_sections"):
        return "sections"
    return "info"


def _headings(edits: list[dict[str, Any]]) -> list[str]:
    return [
        line[3:].strip()
        for e in edits
        if e["kind"] == "MISSING_SECTION"
        for line in e["replacement"].splitlines()
        if line.startswith("## ")
    ]


def _phrase(category: str, edits: list[dict[str, Any]]) -> str:
    if category == "version":
        versions = sorted({e["replacement"] for e in edits})
        if len(versions) == 1:
            return f"show the current release ({versions[0]}) in the install snippets"
        return "update the pinned release in the install snippets"
    if category == "claims":
        return f"correct {len(edits)} claim(s) the repository contradicts"
    if category == "structure":
        parts = {
            "unclosed_details": "close an unclosed <details> block",
            "second_h1": "demote a stray second H1",
        }
        found = [parts[e["detector"]] for e in edits if e["detector"] in parts]
        return " and ".join(dict.fromkeys(found)) or "repair broken README markup"
    if category == "sections":
        names = _headings(edits)
        navigation = any(e["kind"] == "MISSING_INFO" for e in edits)
        what = (
            f"add the {' and '.join(names)} section{'s' if len(names) > 1 else ''}"
            if names
            else "extend the contents list"
        )
        return what + (" and its Navigation item" if navigation and names else "")
    if category == "link":
        return "repair a broken README link"
    if category == "diagram":
        return "lay out the At a Glance diagram left to right"
    additions = {
        "add_version_badge": "add the published-version badge",
        "add_dependency_groups": "add the dependency groups the README lacks",
        "add_install_forms": "add the verified install form",
    }
    added = [
        additions.get(e["detector"], "add verified information the README lacks") for e in edits
    ]
    return " and ".join(dict.fromkeys(added))


def _groups(edits: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edit in edits:
        grouped.setdefault(_category(edit), []).append(edit)
    order = ["version", "claims", "structure", "link", "sections", "info", "diagram"]
    return {name: grouped[name] for name in order if name in grouped}


def title_of(edits: list[dict[str, Any]]) -> str:
    groups = _groups(edits)
    phrases = [_phrase(name, group) for name, group in groups.items()]
    if len(phrases) <= 2:
        return _PREFIX + " and ".join(phrases)
    return f"{_PREFIX}{len(edits)} verified corrections"


def _evidence(edit: dict[str, Any]) -> str:
    parts = []
    for item in edit["evidence"]:
        if item["fact_id"]:
            value = f": {_clip(str(item['value']))}" if item.get("value") else ""
            parts.append(f"`{item['fact_id']}` ({item['status']}){value}")
        else:
            parts.append(f"`{item['value']}`")
    return "; ".join(parts) or "the README's own text"


def _diagram_counts(edit: dict[str, Any]) -> str:
    try:
        glance = parse(edit["replacement"]).glance
    except NotAGlanceError:
        return "every label, group title and edge"
    labels = len(glance.labels)
    return f"all {labels} labels, the {len(glance.titles)} group titles and the chain"


def _bullet(edit: dict[str, Any]) -> list[str]:
    kind, line = edit["kind"], edit["line"]
    why = f"  - why: {edit['rationale']}"
    evidence = f"  - evidence: {_evidence(edit)}"
    if kind == "DIAGRAM_FIX":
        return [
            f"- **At a Glance diagram** (README.md line {line}): redrawn left to right so text no "
            f"longer clips. {_diagram_counts(edit)} Starting Points -> product -> Core "
            "Capabilities -> Outputs are unchanged (compared by script). Layout hints only: "
            "`flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in "
            "order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).",
            f"  - evidence: `README.md:{line}` (the diagram as it is today)",
        ]
    if kind == "MISSING_SECTION":
        heading = next(x for x in edit["replacement"].splitlines() if x.startswith("## "))
        return [f"- inserted `{heading}` before line {line}", why, evidence]
    if kind == "MISSING_INFO":
        shown = next((x for x in edit["replacement"].splitlines() if x.strip()), "")
        extra = len([x for x in edit["replacement"].splitlines() if x.strip()]) - 1
        more = f" (+{extra} more line(s))" if extra > 0 else ""
        return [f"- added at line {line}: `{_clip(shown)}`{more}", why, evidence]
    if not edit["original"]:
        return [f"- inserted `{edit['replacement'].strip()}` before line {line}", why, evidence]
    change = f"`{_clip(edit['original'])}` -> `{_clip(edit['replacement'])}`"
    return [f"- README.md line {line}: {change}", why, evidence]


def _lines(edits: list[dict[str, Any]]) -> str:
    numbers = [str(e["line"]) for e in edits]
    if len(numbers) == 1:
        return f"line {numbers[0]}"
    return f"lines {', '.join(numbers[:-1])} and {numbers[-1]}"


def _lead(groups: dict[str, list[dict[str, Any]]], revision: str) -> list[str]:
    paragraphs: list[str] = []
    for name, edits in groups.items():
        if name == "diagram":
            head = edits[0]["original"].splitlines()[:3]
            top_down = any(line.strip() == "flowchart TD" for line in head)
            paragraphs.append(
                f"The At a Glance diagram (README.md {_lines(edits)}) is drawn "
                + (
                    "top-down (`flowchart TD`), so on GitHub the three blocks stack vertically "
                    if top_down
                    else "so that the blocks stack vertically "
                )
                + "and its labels sit in fixed-size boxes that a wider font can clip. This "
                "redraws the same diagram left to right with boxes sized by their text. Mermaid "
                "body only; no prose is touched."
            )
        elif name == "version":
            old = ", ".join(sorted({f"`{e['original']}`" for e in edits}))
            new = ", ".join(sorted({f"`{e['replacement']}`" for e in edits}))
            paragraphs.append(
                f"The README pins {old} (README.md {_lines(edits)}); the package registry lists "
                f"{new} as the current release, so a reader who copies the snippet gets an "
                "older one."
            )
        elif name == "structure":
            paragraphs.append(
                "Rendering problems in README.md; no wording changes. Each is explained in the "
                "list below, with the line it sits on."
            )
        elif name == "sections":
            names = _headings(edits)
            what = " and ".join(f"`{n}`" for n in names) if names else "a contents item"
            paragraphs.append(
                f"The README has no {what} section; it is rendered from facts verified against "
                f"the repository at revision `{revision[:12]}` (listed below), and gets its "
                "Navigation item where the README has a contents list."
            )
        elif name == "info":
            lacks = _phrase(name, edits).replace("add the ", "").replace("add ", "")
            paragraphs.append(
                f"The README lacks {lacks}, which the repository at revision "
                f"`{revision[:12]}` verifies (evidence listed below)."
            )
        else:
            paragraphs.append(
                f"{_phrase(name, edits).capitalize()}, against the repository at revision "
                f"`{revision[:12]}` (evidence listed below)."
            )
    return paragraphs


def _delta_lines(delta: dict[str, Any]) -> list[str]:
    if not delta:
        return []
    introduced = delta.get("introduced", [])
    resolved = sum(item["fewer"] for item in delta.get("resolved", []))
    line = (
        "- The project's validators (`validate_candidate`, checks BC-01 to BC-14) fail no check "
        f"more often on the corrected README than on yours: {len(introduced)} introduced "
        f"failure(s), {resolved} fewer failure(s) than before"
    )
    revealed = delta.get("revealed", [])
    allowed = delta.get("allowed", [])
    if revealed:
        line += (
            f"; {len(revealed)} check(s) now judge text that was hidden inside the broken markup"
        )
    if allowed:
        rulings = ", ".join(sorted({a["ruling"] for a in allowed}))
        line += f"; {sum(a['extra'] for a in allowed)} recorded under owner ruling(s) {rulings}"
    return [line + "."]


def _render_lines(document: dict[str, Any]) -> list[str]:
    render = document.get("render_check")
    if not render or render.get("status") != "verified":
        return []
    diagrams = render["diagrams"]
    horizontal = all(d["horizontal"] for d in diagrams)
    clipped = sum(d["clipped_fonts"] for d in diagrams)
    splits = sum(d["word_splits"] for d in diagrams)
    problems = sum(d["problems"] for d in diagrams)
    return [
        f"- The redrawn diagram was drawn in a headless browser on Mermaid "
        f"{', '.join(render['releases'])}, natively and in {render['fonts'] - 1} wider fonts: "
        f"{'horizontal on every release' if horizontal else 'NOT horizontal on every release'}, "
        f"{clipped} clipped labels, {splits} words split across lines, {problems} other problems."
    ]


def compose_correction_pull_request(
    *,
    bundle: Path,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    policy_version: str,
) -> PullRequestContent:
    document = _json(bundle / CORRECTIONS_NAME)
    delta = _json(bundle / DELTA_NAME)
    edits: list[dict[str, Any]] = document["edits"]
    groups = _groups(edits)
    stability = document.get("stability", {})
    checks = [
        "- Only `README.md` changes, and only at the places listed: with the edits removed, the "
        "corrected README and yours are identical.",
        *_delta_lines(delta),
        "- Running the correction again on the corrected README makes no further edit "
        f"(idempotent: {'yes' if stability.get('idempotent') else 'NO'}); the same inputs give the "
        f"same bytes (deterministic: {'yes' if stability.get('deterministic') else 'NO'}). No "
        f"model wrote any of this text (model calls: {stability.get('provider_calls', 0)}).",
        *_render_lines(document),
    ]
    changes: list[str] = []
    for edit in edits:
        changes += _bullet(edit)
    body = "\n".join(
        [
            *[p + "\n" for p in _lead(groups, source_revision)],
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
    return PullRequestContent(title=title_of(edits), body=body)
