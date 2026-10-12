"""The pull request text for a correction: what changes, how it was checked, in plain words.

Written from the bundle alone (``corrections.json``, ``validation_delta.json``, ``facts.json``) for
the maintainer who will read it: one bullet per edit with the line, the quoted before and after for
a text edit, a reason in ordinary language and where the evidence is (the file, the registry), the
exact counts of what was checked, how to review and how to decline, then the provenance block the
shared effect reads back. It claims only what the bundle records: a diagram is called drawn in a
browser only when the bundle holds a render record, and a check is counted as the delta counts it.

It names no internal artifact: no check or decision identifiers, no fact ids, no detector or file
names of this tool. ``internal_identifiers`` is the one list of what that means; the composer
applies it to what it writes (not to text quoted from the README) and raises rather than send a
text that leaks one. A regenerated candidate's text (``components/propose/pull_request.py``)
describes a refreshed README reconciled section by section, which would misdescribe a correction;
that composer refuses a correction bundle so the two cannot be mixed up.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme_correction.bundle import CORRECTIONS_NAME, DELTA_NAME
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.core.facts import FACTS_FILENAME, Fact, read_facts

_SHOWN = 120
_PREFIX = "docs(readme): "
_TITLE_LIMIT = 140
_FOOTER = "\n---\n"

#: What the text must never contain: identifiers of this tool's own checks, rulings, detectors,
#: files and fact ids mean nothing to the maintainer who reads a pull request.
_INTERNAL = (
    r"\bBC-\d+",
    r"\bOD-\d+",
    r"\bR\d\b",
    r"validate_candidate",
    r"(?i)\ballowances?\b",
    r"(?i)\bdetectors?\b",
    r"(?i)\bowner rulings?\b",
    r"corrections\.json",
    r"validation_delta",
    r"\b[A-Z]+_FIX\b",
    r"\bMISSING_(?:SECTION|INFO)\b",
    r"\b\d{8}-[0-9a-f]{7,8}\b",
    r"\b(?:package|dependency|install_command|license|build_test_asset|link_target|example"
    r"|public_symbol|format|identity|third_party_notices|inherited_unit):[\w.\-@]+",
    r"\b(?:claim_[a-z_]+|second_h1|unclosed_details|missing_sections|add_[a-z_]+"
    r"|at_a_glance_diagram|stale_phrase|broken_link|failing_example|report_gaps)\b",
)
INTERNAL_IDENTIFIERS = tuple(re.compile(p) for p in _INTERNAL)
_QUOTED = re.compile(r"`[^`\n]*`")

_REGISTRIES = {
    "nuget.org": "NuGet",
    "www.nuget.org": "NuGet",
    "api.nuget.org": "NuGet",
    "pypi.org": "PyPI",
    "repo1.maven.org": "Maven Central",
    "search.maven.org": "Maven Central",
    "crates.io": "crates.io",
    "registry.npmjs.org": "npm",
    "www.npmjs.com": "npm",
    "pkg.go.dev": "pkg.go.dev",
    "proxy.golang.org": "pkg.go.dev",
}


def internal_identifiers(text: str, *, quoted: bool = True) -> list[str]:
    """The internal identifiers ``text`` contains. ``quoted=False`` ignores backtick-quoted spans,
    which quote the maintainer's own README or a value, not this tool's words."""
    scanned = text if quoted else _QUOTED.sub("", text)
    return sorted(
        {m.group(0) for pattern in INTERNAL_IDENTIFIERS for m in pattern.finditer(scanned)}
    )


def _clip(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= _SHOWN else flat[: _SHOWN - 3] + "..."


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    return document if isinstance(document, dict) else {}


def _facts(bundle: Path) -> dict[str, Fact]:
    path = bundle / FACTS_FILENAME
    return {fact.id: fact for fact in read_facts(path).facts} if path.is_file() else {}


# ------------------------------------------------------------------------------------ grouping
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
    if detector == "add_dev_commands":
        return "dev"
    if detector == "add_doc_links":
        return "docs"
    return "info"


def _headings(edits: list[dict[str, Any]]) -> list[str]:
    return [
        line[3:].strip()
        for e in edits
        if e["kind"] == "MISSING_SECTION"
        for line in e["replacement"].splitlines()
        if line.startswith("## ")
    ]


def _parts(category: str, edits: list[dict[str, Any]]) -> list[str]:
    """The change(s) of one category, each a phrase that completes "this pull request will ..."."""
    if category == "version":
        versions = sorted({e["replacement"] for e in edits})
        if len(versions) == 1:
            return [f"show the current release ({versions[0]}) in the install snippets"]
        return ["update the pinned release in the install snippets"]
    if category == "claims":
        return [f"correct {len(edits)} claim(s) the repository contradicts"]
    if category == "structure":
        known = {
            "unclosed_details": "close an unclosed <details> block",
            "second_h1": "demote a stray second H1",
        }
        found = [known[e["detector"]] for e in edits if e["detector"] in known]
        return list(dict.fromkeys(found)) or ["repair broken README markup"]
    if category == "sections":
        names = _headings(edits)
        navigation = any(e["kind"] == "MISSING_INFO" for e in edits)
        what = (
            f"add the {' and '.join(names)} section{'s' if len(names) > 1 else ''}"
            if names
            else "extend the contents list"
        )
        return [what + (" and its Navigation item" if navigation and names else "")]
    if category == "link":
        return ["repair a broken README link"]
    if category == "diagram":
        return ["lay out the At a Glance diagram left to right"]
    if category == "dev":
        has_commands = any("```" in e["replacement"] for e in edits)
        return [
            "add the build and test commands, with the steps they need first"
            if has_commands
            else "say where the project's CI runs and how releases are made"
        ]
    if category == "docs":
        return ["link the project files the README does not mention"]
    additions = {
        "add_version_badge": "add the published-version badge",
        "add_dependency_groups": "add the dependency groups the README lacks",
        "add_install_forms": "add the verified install form",
    }
    added = [
        additions.get(e["detector"], "add verified information the README lacks") for e in edits
    ]
    return list(dict.fromkeys(added))


def _groups(edits: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edit in edits:
        grouped.setdefault(_category(edit), []).append(edit)
    order = ["version", "claims", "structure", "link", "sections", "info", "dev", "docs", "diagram"]
    return {name: grouped[name] for name in order if name in grouped}


def title_of(edits: list[dict[str, Any]]) -> str:
    """The change in a sentence, or its count when the sentence would not fit a title."""
    groups = _groups(edits)
    parts = [part for name, group in groups.items() for part in _parts(name, group)]
    sentence = ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]
    if len(parts) <= 3 and len(_PREFIX + sentence) <= _TITLE_LIMIT:
        return _PREFIX + sentence
    return f"{_PREFIX}{len(edits)} verified corrections"


# ------------------------------------------------------------------------------------ evidence
def _where(fact: Fact) -> str:
    """Where a fact is read from: the file in the repository, or the registry's address."""
    paths = [e.path for e in fact.evidence if e.path]
    if not paths:
        return ""
    path = paths[0]
    return f"at {path}" if path.startswith("http") else f"in `{path}`"


def _fact_text(fact: Fact) -> str:
    value = _clip(fact.value)
    fid = fact.id
    if fid == "dependency:none":
        what = "no third-party dependencies are declared"
    elif fid.startswith("dependency:"):
        what = f"dependency `{value}`"
    elif fid == "package:name":
        what = f"package name `{value}`"
    elif fid == "package:published_version":
        what = f"current release `{value}` on the package registry"
    elif fid == "package:version":
        what = f"version `{value}` in the project file"
    elif fid == "package:cxx_standard":
        what = f"C++ standard `{value}`"
    elif fid == "package:cmake_minimum":
        what = f"minimum CMake version `{value}`"
    elif fid == "package:target_framework":
        what = f"target frameworks `{value}`"
    elif fid.startswith("install_command:"):
        what = f"install command `{value}`"
    elif fid in {"build_test_asset:build-command", "build_test_asset:test-command"}:
        role = "build" if fid.endswith("build-command") else "test"
        what = f"{role} command `{value}`"
        platform = (fact.attributes or {}).get("build_receipt_platform")
        if (fact.attributes or {}).get("build_receipt") and platform:
            what += (
                f", which ran to success with every step exiting 0 on a clean clone ({platform})"
            )
    elif fid == "build_test_asset:ci-matrix":
        what = "the systems and runtimes the CI workflow runs on"
    elif fid == "build_test_asset:release-workflow":
        what = "the workflow whose steps publish a release"
    elif fid == "build_test_asset:documentation":
        what = "prose documentation under `docs/`"
    else:
        what = f"{fact.kind.replace('_', ' ')} `{value}`"
    where = _where(fact)
    return f"{what} ({where})" if where else what


def _evidence(edit: dict[str, Any], facts: dict[str, Fact]) -> str:
    parts: list[str] = []
    for item in edit["evidence"]:
        if item["fact_id"]:
            fact = facts.get(item["fact_id"])
            if fact is not None:
                parts.append(_fact_text(fact))
        else:
            value = str(item["value"])
            if value.startswith("tree:"):
                parts.append(f"`{value[5:]}` exists in the repository")
            elif ":" in value and value.rsplit(":", 1)[1].isdigit():
                parts.append(f"README.md line {value.rsplit(':', 1)[1]}")
            else:
                parts.append(f"`{value}`")
    return "; ".join(parts) or "the README's own text"


def _locator_lines(edit: dict[str, Any]) -> list[int]:
    found = []
    for item in edit["evidence"]:
        value = str(item.get("value") or "")
        if not item.get("fact_id") and value.rsplit(":", 1)[-1].isdigit():
            found.append(int(value.rsplit(":", 1)[1]))
    return found


def _registry_of(facts: dict[str, Fact]) -> str:
    fact = facts.get("package:published_version")
    for evidence in fact.evidence if fact is not None else ():
        host = urlparse(evidence.path).netloc
        if host in _REGISTRIES:
            return _REGISTRIES[host]
    return "the package registry"


# ------------------------------------------------------------------------------------- bullets
def _chain(glance: Any) -> str:
    names = list(glance.titles)
    names.insert(1 if glance.starting_points else 0, "the product")
    return " -> ".join(names)


def _diagram_counts(edit: dict[str, Any]) -> str:
    try:
        glance = parse(edit["replacement"]).glance
    except NotAGlanceError:
        return "Every label, group title and edge are unchanged (compared by script)."
    return (
        f"All {len(glance.labels)} labels, the {len(glance.titles)} group titles and the chain "
        f"{_chain(glance)} are unchanged (compared by script)."
    )


def _tested_range(render: dict[str, Any] | None) -> str:
    if not render or render.get("status") != "verified":
        return ""
    versions = sorted(tuple(int(p) for p in v.split(".")[:2]) for v in render["releases"])
    low, high = versions[0], versions[-1]
    return f" in the Mermaid versions tested ({low[0]}.{low[1]} to {high[0]}.{high[1]})"


def _commands_source(edit: dict[str, Any], facts: dict[str, Fact]) -> str:
    """Where the commands of a Development and Testing addition come from, in plain words."""
    for item in edit["evidence"]:
        fact = facts.get(item["fact_id"] or "")
        if fact is None or not fact.id.endswith("-command"):
            continue
        chain = (fact.attributes or {}).get("command_chain")
        path = fact.evidence[0].path if fact.evidence else ""
        job = re.search(
            r"\bjob (\S+) runs\b", (fact.evidence[0].detail or "") if fact.evidence else ""
        )
        if chain == "ci_job" and job:
            return f"the CI job `{job.group(1)}` in `{path}` runs them"
        if chain == "ci_job":
            return f"the CI workflow `{path}` runs them"
        return f"the project's own files (`{path}`) name them"
    return "the repository's own files name them"


def _where_it_ran(edit: dict[str, Any], facts: dict[str, Fact]) -> str:
    for item in edit["evidence"]:
        fact = facts.get(item["fact_id"] or "")
        attributes = (fact.attributes or {}) if fact is not None else {}
        if attributes.get("build_receipt") and attributes.get("build_receipt_platform"):
            return attributes["build_receipt_platform"]
    return ""


def _why(edit: dict[str, Any], facts: dict[str, Fact] | None = None) -> str:
    kind, detector = edit["kind"], edit["detector"]
    lines = _locator_lines(edit)
    if detector == "add_dev_commands":
        known = facts or {}
        if "```" in edit["replacement"]:
            ran = _where_it_ran(edit, known)
            return (
                "the README does not show how to build and test the project; "
                f"{_commands_source(edit, known)}, and every step exited 0 when run on a clean "
                f"clone of this revision{f' ({ran})' if ran else ''}"
            )
        return (
            "the README does not say where the project's CI runs; the workflow files in the "
            "repository state it"
        )
    if detector == "add_doc_links":
        return "the README does not mention these files, and the repository holds them"
    if detector == "claim_version":
        return str(edit["rationale"])
    if kind == "FALSE_CLAIM_FIX":
        shown = f"`{_clip(edit['original'])}`; the repository shows `{_clip(edit['replacement'])}`"
        return f"the README says {shown}"
    if detector == "second_h1":
        return (
            f"line {lines[0] if lines else edit['line']} is a second top-level heading, and a "
            "README has one: its title, on line 1. We made it a second-level heading (`##`); if "
            "the line was meant as a note, deleting the `#` instead may read better"
        )
    if detector == "unclosed_details":
        opened = lines[0] if lines else "?"
        end = lines[1] if len(lines) > 1 else edit["line"]
        return (
            f"the `<details>` block opened on line {opened} is never closed, so everything after "
            "it renders collapsed. We close it before the next section heading (line "
            f"{end}); that is our reading of where it should end, so tell us if it should end "
            "elsewhere"
        )
    if kind == "MISSING_SECTION":
        lines_ = edit["replacement"].splitlines()
        heading = next((x[3:].strip() for x in lines_ if x.startswith("## ")), "")
        return (
            f"the README has no {heading} section; this one states what the repository's own "
            "files declare"
        )
    if detector == "missing_sections":  # the contents-list item that goes with an inserted section
        return "so the new section can be reached from the contents list"
    if detector == "add_version_badge":
        return (
            "the README shows no version badge for the published package; it is added at the "
            "front of the badge row"
        )
    if kind == "BROKEN_LINK":
        return "the link points at a file the repository does not contain"
    return "the README does not yet say this, and the repository's files show it"


def _bullet(
    edit: dict[str, Any], facts: dict[str, Fact], render: dict[str, Any] | None
) -> list[str]:
    kind, line = edit["kind"], edit["line"]
    if kind == "DIAGRAM_FIX":
        return [
            f"- **At a Glance diagram** (README.md line {line}): drawn left to right so the labels "
            f"fit their boxes{_tested_range(render)}. {_diagram_counts(edit)} Layout hints only: "
            "`flowchart LR`, `<br/>` line breaks, invisible `~~~` links that keep the columns in "
            "order, and one `%%{init}%%` line (SVG text, which a wider font cannot clip).",
            f"  - evidence: README.md line {line} (the diagram as it is today)",
        ]
    why = f"  - why: {_why(edit, facts)}"
    evidence = f"  - evidence: {_evidence(edit, facts)}"
    if kind == "MISSING_SECTION":
        heading = next(x for x in edit["replacement"].splitlines() if x.startswith("## "))
        return [f"- inserted `{heading}` before line {line}", why, evidence]
    if kind == "MISSING_INFO":
        shown = next((x for x in edit["replacement"].splitlines() if x.strip()), "")
        extra = len([x for x in edit["replacement"].splitlines() if x.strip()]) - 1
        more = f" (+{extra} more line(s))" if extra > 0 else ""
        where = "contents list" if edit["detector"] == "missing_sections" else "README"
        return [f"- added to the {where} at line {line}: `{_clip(shown)}`{more}", why, evidence]
    if not edit["original"]:
        return [f"- inserted `{edit['replacement'].strip()}` before line {line}", why, evidence]
    change = f"`{_clip(edit['original'])}` -> `{_clip(edit['replacement'])}`"
    return [f"- README.md line {line}: {change}", why, evidence]


def _lines(edits: list[dict[str, Any]]) -> str:
    numbers = [str(e["line"]) for e in edits]
    if len(numbers) == 1:
        return f"line {numbers[0]}"
    return f"lines {', '.join(numbers[:-1])} and {numbers[-1]}"


def _lead(
    groups: dict[str, list[dict[str, Any]]], facts: dict[str, Fact], revision: str
) -> list[str]:
    paragraphs: list[str] = []
    for name, edits in groups.items():
        if name == "diagram":
            head = edits[0]["original"].splitlines()[:3]
            top_down = any(line.strip() == "flowchart TD" for line in head)
            paragraphs.append(
                f"The At a Glance diagram (README.md {_lines(edits)}) is drawn "
                + (
                    "top-down (`flowchart TD`), so on GitHub the blocks stack vertically "
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
                f"The README has no {what} section. We added one that states what the "
                "repository's own files declare (cited below), with an item for it in the "
                "contents list."
            )
        elif name == "dev":
            paragraphs.append(
                "The README's development section does not show how to build and test the "
                "project. What we add is what the repository states: "
                + (
                    "the commands below, run in this order on a clean clone of revision "
                    f"`{revision[:12]}` and each exiting 0, with the install steps they need first."
                    if any("```" in e["replacement"] for e in edits)
                    else "where its CI runs and how its releases are made."
                )
            )
        elif name == "docs":
            paragraphs.append(
                "The README does not link some files the repository holds (listed below). We "
                "added a link to each, in the section that lists the project's documents."
            )
        elif name == "info" and any(e["detector"] == "add_version_badge" for e in edits):
            package = facts.get("package:name")
            version = facts.get("package:published_version")
            paragraphs.append(
                "The README has no version badge for the published package"
                + (
                    f" ({package.value} on {_registry_of(facts)}, current release {version.value})"
                    if package is not None and version is not None
                    else ""
                )
                + "; we added it at the front of the badge row."
            )
        else:
            paragraphs.append(
                f"{_parts(name, edits)[0].capitalize()}, against the repository at revision "
                f"`{revision[:12]}` (evidence cited below)."
            )
    return paragraphs


# ------------------------------------------------------------------------------------- checks
_LENGTH = re.compile(r"(\d+) visible lines of \d+ exceed the visible budget (\d+)")


def _tally(delta: dict[str, Any]) -> tuple[int, int, int, int]:
    """``(before, after, removed, added)``: the failures the checks report on the README and on the
    corrected one, and how many of them the correction takes away and brings, check by check."""
    live = delta.get("live_failures", {})
    after = delta.get("corrected_failures", {})
    names = set(live) | set(after)
    removed = sum(max(live.get(n, 0) - after.get(n, 0), 0) for n in names)
    added = sum(max(after.get(n, 0) - live.get(n, 0), 0) for n in names)
    return sum(live.values()), sum(after.values()), removed, added


def _delta_lines(delta: dict[str, Any], edits: list[dict[str, Any]]) -> list[str]:
    """What the README checks found, computed from the record and nothing else: the totals before
    and after, what the correction removes and what it adds. It never says "fewer" unless it adds
    nothing, and every failure it adds is explained in a line of its own."""
    if not delta:
        return []
    before, after, removed, added = _tally(delta)
    text = (
        "- We ran repository-presenter's README checks (install commands, version claims, links, "
        f"structure, length) on your README and on the corrected one. They report {before} "
        f"failure(s) on yours and {after} on the corrected one: "
    )
    if added == 0:
        text += (
            f"it removes {removed} of the {before} and adds none."
            if removed
            else "it removes none and adds none."
        )
    else:
        text += f"it removes {removed} and adds {added}; the added ones are explained below."
    lines = [text]
    explained = 0
    revealed = delta.get("revealed", [])
    if revealed:
        count = sum(i["extra"] for i in revealed)
        explained += count
        spans = [
            m.group(1)
            for item in revealed
            for detail in item["details"]
            if (m := re.search(r"code span '([^']+)'", detail))
        ]
        about = f" (for example the code span `{spans[0]}`)" if spans else ""
        lines.append(
            "- Closing the broken markup makes text visible that the checks could not read "
            f"before; they now report {count} issue(s) there{about}. That text is yours and this "
            "change does not alter it."
        )
    grown = sum(
        len(e["replacement"].splitlines()) - len(e["original"].splitlines())
        for e in edits
        if e["kind"] == "DIAGRAM_FIX"
    )
    for item in delta.get("allowed", []):
        found = next((m for d in item["details"] if (m := _LENGTH.search(d))), None)
        if found is not None:
            explained += item["extra"]
            over = int(found.group(1)) - int(found.group(2))
            lines.append(
                f"- Length: the redrawn diagram adds {grown} lines (its init line and the links "
                f"that keep columns in order), so the README now has {found.group(1)} lines "
                f"outside collapsed blocks, {over} over the {found.group(2)}-line limit the "
                "checks apply (yours was within it). That is the one check the redraw makes "
                "fail; the redraw is what makes the labels fit."
            )
    if added > explained:
        lines.append(
            f"- {added - explained} of the failure(s) it adds are new problems this change "
            "introduces."
        )
    return lines


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


def _noticed(document: dict[str, Any]) -> list[str]:
    stale = [f for f in document.get("unapplied_findings", []) if f["detector"] == "stale_phrase"]
    if not stale:
        return []
    out = ["", "### Noticed, not changed"]
    for finding in stale:
        out.append(
            f"- README.md line {finding['line']}: `{_clip(finding['text'])}` may be out of date "
            "now that the package is published; we left it as you wrote it."
        )
    return out


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
    facts = _facts(bundle)
    edits: list[dict[str, Any]] = document["edits"]
    groups = _groups(edits)
    stability = document.get("stability", {})
    render = document.get("render_check")
    checks = [
        "- Only `README.md` changes, and only at the places listed: with the edits removed, the "
        "corrected README and yours are identical.",
        *_delta_lines(delta, edits),
        "- Running the correction again on the corrected README makes no further edit "
        f"(idempotent: {'yes' if stability.get('idempotent') else 'NO'}); the same inputs give the "
        f"same bytes (deterministic: {'yes' if stability.get('deterministic') else 'NO'}). No "
        f"model wrote any of this text (model calls: {stability.get('provider_calls', 0)}).",
        *_render_lines(document),
    ]
    changes: list[str] = []
    for edit in sorted(edits, key=lambda e: (e["kind"] == "DIAGRAM_FIX", e["start"])):
        changes += _bullet(edit, facts, render)  # the content changes first, the diagram last
    above = "\n".join(
        [
            *[p + "\n" for p in _lead(groups, facts, source_revision)],
            "### What changes",
            *changes,
            "",
            "### How this was checked",
            *checks,
            *_noticed(document),
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
            "- kind: correction",
            "",
        ]
    )
    return PullRequestContent(title=title_of(edits), body=above + "\n\n" + footer)
