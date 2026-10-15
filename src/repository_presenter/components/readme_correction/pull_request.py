"""The pull request text for a correction: what changes, how it was checked, in plain words.

Written from the bundle alone (``corrections.json``, ``validation_delta.json``, ``facts.json``,
``README.original.md``) for the maintainer who will read it: one bullet per edit with the line, the
quoted before and after for a text edit, a reason in ordinary language and where the evidence is
(the file, the registry), the exact counts of what was checked, how to review and how to decline,
then the provenance block the shared effect reads back. It claims only what the bundle records: a
diagram is called drawn in a browser only when the bundle holds a render record, and a check is
counted as the delta counts it.

What the README already shows is read from the whole original README, never assumed: a command it
shows anywhere (or in another form) is never called missing, and the text says which of build and
test it adds. "No wording changes" is said only when no line of the maintainers' text changes. A
command is credited to the file that states it (a workflow job, a package script, a make target),
and a standard command to the project file that marks the toolchain, never to a manifest that
merely sits beside it. A title names the change, or counts exactly the edits listed.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme.evidence.facts.commands import commands_in_text
from repository_presenter.components.readme_correction.bundle import (
    CORRECTIONS_NAME,
    DELTA_NAME,
    ORIGINAL_NAME,
)
from repository_presenter.components.readme_correction.commands import form_covered
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


_ROLE_OF = {"build_test_asset:build-command": "build", "build_test_asset:test-command": "test"}
_ROLE_WORDS = {"build": "how to build", "test": "how to run the tests"}
_ROLE_SHORT = {"build": "how to build", "test": "how to test"}
_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
_WRAPPERS = frozenset({"python", "python3", "py"})
_H2 = re.compile(r"(?m)^## ")
_LINK_ITEM = re.compile(r"- \*\*\[([^\]]+)\]\(([^)]+)\)\*\*")
_DOCS_HEADING = "Documentation & Resources"


def _squash(text: str) -> str:
    return " ".join(text.split())


def _join(words: list[str], *, oxford: bool = False) -> str:
    if len(words) < 2:
        return "".join(words)
    if len(words) == 2:
        return f"{words[0]} and {words[1]}"
    return f"{', '.join(words[:-1])}{',' if oxford else ''} and {words[-1]}"


@dataclass(frozen=True)
class _Dev:
    """What the Development and Testing additions hold, and what the live README already shows.

    ``shown`` is computed from the whole live README, and from the candidates the correction
    itself held back as already shown: a command the README shows anywhere is never called
    missing."""

    commands: tuple[Fact, ...] = ()  # the build and test facts the block prints, build first
    setup: tuple[str, ...] = ()  # the lines the block runs before them
    block: bool = False  # a fenced block of commands is added
    ci: bool = False  # a sentence about where the CI runs
    release: bool = False  # a sentence about how releases are made
    shown: dict[str, str | None] = field(default_factory=dict)  # role -> the command as written
    here: bool = False  # what the README shows is in the section the block is added to
    after: bool = False  # the block follows the README's own command, in the same section
    platform: str = ""  # where the receipt ran the commands

    @property
    def roles(self) -> tuple[str, ...]:
        return tuple(_ROLE_OF[f.id] for f in self.commands)


def _block_lines(text: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for raw in text.splitlines():
        if raw.startswith("```"):
            inside = not inside
        elif inside and raw.strip():
            lines.append(raw.strip())
    return lines


def _dev_content(edits: list[dict[str, Any]]) -> tuple[bool, bool, bool]:
    """``(commands, CI sentence, release sentence)`` the Development and Testing edits add."""
    text = "\n".join(e["replacement"] for e in edits)
    return (
        "```" in text,
        re.search(r"\bworkflow\]\([^)]+\) runs\b", text) is not None,
        "Releases run through" in text,
    )


def _dev_state(
    edits: list[dict[str, Any]], facts: dict[str, Fact], original: str, document: dict[str, Any]
) -> _Dev:
    """The Development and Testing additions in terms of what they add and what the README shows."""
    dev = [e for e in edits if _category(e) == "dev"]
    if not dev:
        return _Dev()
    block, ci, release = _dev_content(dev)
    cited: dict[str, Fact] = {}
    for edit in dev:
        for item in edit["evidence"]:
            fact_id = item["fact_id"] or ""
            if fact_id in _ROLE_OF and fact_id in facts:
                cited[_ROLE_OF[fact_id]] = facts[fact_id]
    commands = tuple(cited[role] for role in ("build", "test") if role in cited)
    wanted = {_squash(line) for f in commands for line in [f.value, *f.value.splitlines()]}
    setup = tuple(
        line
        for line in _block_lines("\n".join(e["replacement"] for e in dev))
        if _squash(line) not in wanted
    )
    held = {
        _squash(f["candidate"])
        for f in document.get("report_only", [])
        if f["detector"] == "add_dev_commands" and f["report_only_reason"] == "ALREADY_SHOWN"
    }
    forms = commands_in_text(original)
    flat = _squash(original)
    shown: dict[str, str | None] = {}
    seen: list[Fact] = []
    for fact_id, role in _ROLE_OF.items():
        fact = facts.get(fact_id)
        if fact is None or role in cited or fact.polarity != "SUPPORTED":
            continue
        if _squash(fact.value) in held or form_covered(forms, fact.value):
            shown[role] = fact.value.splitlines()[0] if _squash(fact.value) in flat else None
            seen.append(fact)
    here = after = False
    first = next((e for e in dev if "```" in e["replacement"]), None)
    if first is not None and seen:
        where = first["start"]
        begin = max((m.start() for m in _H2.finditer(original) if m.start() < where), default=0)
        end = next((m.start() for m in _H2.finditer(original) if m.start() >= where), len(original))
        section = commands_in_text(original[begin:end])
        here = all(form_covered(section, f.value) for f in seen)
        anchor = next(iter(shown.values())) if len(shown) == 1 else None
        after = bool(anchor) and original.find(anchor or "", begin, where) >= 0
    platform = next(
        (
            f.attributes["build_receipt_platform"]
            for f in commands
            if f.attributes and f.attributes.get("build_receipt")
            if f.attributes.get("build_receipt_platform")
        ),
        "",
    )
    return _Dev(commands, setup, block, ci, release, shown, here, after, platform)


def _dev_sentence_words(ci: bool, release: bool) -> str:
    if ci and release:
        return "where the project's CI runs and how its releases are made"
    return "where the project's CI runs" if ci else "how the project's releases are made"


def _roles_phrase(roles: tuple[str, ...]) -> str:
    if len(roles) > 1:
        return "how to build and test the project"
    return f"{_ROLE_SHORT[roles[0]]} the project" if roles else "how to build and test the project"


def _shown_words(shown: dict[str, str | None]) -> str:
    return " and ".join(f"`{v}`" if v else _ROLE_WORDS[r] for r, v in shown.items())


def _program(command: str) -> str:
    tokens = command.split()
    if len(tokens) > 2 and tokens[0] in _WRAPPERS and tokens[1] == "-m":
        return tokens[2]
    return tokens[0].rsplit("/", 1)[-1] if tokens else "build"


def _structure_phrase(edits: list[dict[str, Any]]) -> str:
    words = {
        "second_h1": "a second top-level heading",
        "unclosed_details": "a `<details>` block that is never closed",
    }
    found = [words.get(e["detector"], "broken markup") for e in edits]
    count = _COUNT_WORDS.get(len(edits), str(len(edits)))
    noun = "markup problem" if len(edits) == 1 else "markup problems"
    return f"{'a' if len(edits) == 1 else count} {noun} in README.md ({_join(found)})"


def _wording_neutral(edit: dict[str, Any]) -> bool:
    """Whether a structure fix that changes a line of the README changes none of its words: a
    heading's ``#`` marks."""
    original, replacement = str(edit["original"]), str(edit["replacement"])
    return edit["detector"] == "second_h1" and original.lstrip("#") == replacement.lstrip("#")


def _links_section(edits: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """``(label, target)`` of an inserted ``Documentation & Resources`` section made only of
    links, else ``[]``."""
    found: list[tuple[str, str]] = []
    for edit in edits:
        if edit["kind"] != "MISSING_SECTION":
            continue
        lines = [x for x in edit["replacement"].splitlines() if x.strip()]
        matches = [_LINK_ITEM.match(x) for x in lines[1:]]
        if lines[:1] == [f"## {_DOCS_HEADING}"] and matches and all(matches):
            found += [(m.group(1), m.group(2)) for m in matches if m]
    return found


def _dev_title(dev: _Dev) -> list[str]:
    parts: list[str] = []
    if dev.commands:
        program = _program(dev.commands[0].value)
        single = dev.roles[0] if program == dev.roles[0] else f"{program} {dev.roles[0]}"
        what = "build and test commands" if len(dev.commands) > 1 else f"{single} command"
        steps = f", with the steps {'it needs' if len(dev.commands) == 1 else 'they need'} first"
        parts.append(f"add the {what}{steps if dev.setup else ''}")
    elif dev.block:
        parts.append("add the build and test commands")
    if dev.ci or dev.release:
        parts.append(f"say {_dev_sentence_words(dev.ci, dev.release)}")
    return parts or ["add verified information the README lacks"]


def _parts(category: str, edits: list[dict[str, Any]], dev: _Dev) -> list[str]:
    """The change(s) of one category, each a phrase that completes "this pull request will ...";
    a count is the number of edits listed, never fewer."""
    if category == "version":
        versions = sorted({e["replacement"] for e in edits})
        if len(versions) == 1:
            return [f"show the current release ({versions[0]}) in the install snippets"]
        return ["update the pinned release in the install snippets"]
    if category == "claims":
        return [f"correct {len(edits)} claim(s) the repository contradicts"]
    if category == "structure":
        phrases = {
            "unclosed_details": (
                "close an unclosed <details> block",
                "close {n} unclosed <details> blocks",
            ),
            "second_h1": ("demote a stray second H1", "demote {n} stray second H1s"),
        }
        out = []
        for detector, (one, many) in phrases.items():
            n = sum(e["detector"] == detector for e in edits)
            out += [one] if n == 1 else [many.format(n=n)] if n else []
        known = sum(e["detector"] in phrases for e in edits)
        return out + (["repair broken README markup"] if known < len(edits) else [])
    if category == "sections":
        names = _headings(edits)
        links = _links_section(edits)
        counted = sum(_has_item(edits, name) for name in names)
        if links and names == [_DOCS_HEADING]:
            labels = [label for label, _target in links]
            what = (
                f"add {_join(labels)} links in a {_DOCS_HEADING} section"
                if len(labels) > 1
                else f"add a {labels[0]} link in a {_DOCS_HEADING} section"
            )
        elif names:
            what = f"add the {' and '.join(names)} section{'s' if len(names) > 1 else ''}"
        else:
            what = "extend the contents list"
        if counted:
            what += " and its Navigation item" if counted == 1 else " and their Navigation items"
        return [what]
    if category == "link":
        return [
            "repair a broken README link"
            if len(edits) == 1
            else f"repair {len(edits)} broken README links"
        ]
    if category == "diagram":
        return ["lay out the At a Glance diagram left to right"]
    if category == "dev":
        return [" and ".join(_dev_title(dev))]
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


def title_of(edits: list[dict[str, Any]], dev: _Dev | None = None) -> str:
    """The change in a sentence. When it would have more than three parts, two or more structure
    fixes become one (``fix two markup problems``); when it still would not fit a title, the title
    is the count of the edits, which is the number of changes listed."""
    groups = _groups(edits)
    state = dev or _Dev(block=any(_dev_content(groups.get("dev", []))[:1]))
    parts = {name: _parts(name, group, state) for name, group in groups.items()}
    if sum(len(p) for p in parts.values()) > 3 and len(groups.get("structure", [])) > 1:
        count = _COUNT_WORDS.get(len(groups["structure"]), str(len(groups["structure"])))
        parts["structure"] = [f"fix {count} markup problems"]
    flat = [part for found in parts.values() for part in found]
    sentence = ", ".join(flat[:-1]) + " and " + flat[-1] if len(flat) > 1 else flat[0]
    if len(flat) <= 3 and len(_PREFIX + sentence) <= _TITLE_LIMIT:
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


_PROJECT_KINDS = {
    "go.mod": "a Go module",
    "Cargo.toml": "a Rust crate",
    "pom.xml": "a Maven project",
    "pyproject.toml": "a Python project",
    ".sln": "a .NET solution",
}


def _project_kind(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return _PROJECT_KINDS.get(name) or _PROJECT_KINDS.get(Path(name).suffix) or "the project"


def _evidence_head(fact: Fact) -> tuple[str, str]:
    """``(path, detail)`` of the evidence that names a command: the file that states it."""
    first = fact.evidence[0] if fact.evidence else None
    return (first.path, first.detail or "") if first is not None else ("", "")


def _origin_key(fact: Fact) -> tuple[str, str, str]:
    path, detail = _evidence_head(fact)
    job = re.search(r"\bjob (\S+) runs\b", detail)
    attributes = fact.attributes or {}
    source = attributes.get("source", "")
    if not source and (job or attributes.get("command_chain") == "ci_job"):
        source = "ci workflow"
    return (source, path, job.group(1) if job else "")


def _command_where(fact: Fact) -> str:
    """Where a build or test command is stated, as a short noun phrase: the workflow job, the
    package script or make target that defines it, or the project file a standard command is for."""
    source, path, job = _origin_key(fact)
    _path, detail = _evidence_head(fact)
    named = re.search(r'script "([^"]+)"|target (\S+) is defined', detail)
    name = (named.group(1) or named.group(2)) if named else ""
    if source == "ci workflow":
        return f"named by job `{job}` of `{path}`" if job else f"named in `{path}`"
    if source == "package.json script" and name:
        return f"the `{name}` script of `{path}`"
    if source == "Makefile" and name:
        return f"the `{name}` target of `{path}`"
    return f"the standard command for {_project_kind(path)}, `{path}`"


def _origins(commands: tuple[Fact, ...]) -> str:
    """Who states the commands, in a clause: the file that does (workflow, package script, make
    target), or for a standard command, the project file that marks the toolchain. A manifest is
    never credited with naming a command it only sits beside."""
    groups: dict[tuple[str, str, str], list[Fact]] = {}
    for fact in commands:
        groups.setdefault(_origin_key(fact), []).append(fact)
    clauses: list[str] = []
    for (source, path, job), found in groups.items():
        many = len(found) > 1
        names = []
        for fact in found:
            named = re.search(r'script "([^"]+)"|target (\S+) is defined', _evidence_head(fact)[1])
            if named:
                names.append(f"`{named.group(1) or named.group(2)}`")
        if source == "ci workflow":
            where = f"the CI job `{job}` in `{path}`" if job else f"the CI workflow `{path}`"
            clauses.append(f"{where} runs {'them' if many else 'it'}")
        elif source in {"package.json script", "Makefile"} and names:
            noun = "script" if source == "package.json script" else "target"
            clauses.append(
                f"the {_join(names)} {noun}{'s' if len(names) > 1 else ''} in `{path}` "
                f"{'define' if many else 'defines'} {'them' if many else 'it'}"
            )
        else:
            values = _join([f"`{f.value}`" for f in found])
            clauses.append(
                f"`{path}` marks {_project_kind(path)}, so {values} "
                f"{'apply' if many else 'applies'}"
            )
    return "; ".join(clauses) or "the repository's own files name them"


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
        what = f"{role} command `{value}` ({_command_where(fact)})"
        platform = (fact.attributes or {}).get("build_receipt_platform")
        if (fact.attributes or {}).get("build_receipt") and platform:
            what += (
                f", which ran to success with every step exiting 0 on a clean clone ({platform})"
            )
        return what  # the file that states it is named above, never the manifest beside it
    elif fid == "build_test_asset:ci":
        what = "the repository's workflow files"
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


def _either(words: list[str]) -> str:
    if len(words) < 2:
        return "".join(words)
    return f"{', '.join(words[:-1])} or {words[-1]}"


def _dev_why(dev: _Dev) -> str:
    if not dev.commands:
        return (
            "the README does not show how to build and test the project; the repository's own "
            "files name them"
        )
    if dev.shown:
        lack = (
            f"the README shows {_join([_ROLE_SHORT[r] for r in dev.shown])} but not "
            f"{_ROLE_SHORT[dev.roles[0]]}"
        )
    else:
        lack = f"the README does not show {_roles_phrase(dev.roles)}"
    ran = f" ({dev.platform})" if dev.platform else ""
    exited = (
        "it exited 0 on a clean clone of this revision"
        if len(dev.commands) == 1 and not dev.setup
        else "every step exited 0 when run on a clean clone of this revision"
    )
    return f"{lack}; {_origins(dev.commands)}, and {exited}{ran}"


def _why(edit: dict[str, Any], dev: _Dev | None = None) -> str:
    kind, detector = edit["kind"], edit["detector"]
    lines = _locator_lines(edit)
    if detector == "add_dev_commands":
        if "```" in edit["replacement"]:
            return _dev_why(dev or _Dev())
        _commands, ci, release = _dev_content([edit])
        return (
            f"the README does not say {_dev_sentence_words(ci, release)}; the workflow files "
            "in the repository state it"
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
        links = _links_section([edit])
        if links:
            targets = _either([f"`{target}`" for _label, target in links])
            return (
                f"the README has no {heading} section and does not link {targets}, which the "
                "repository holds"
            )
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
    edit: dict[str, Any], facts: dict[str, Fact], render: dict[str, Any] | None, dev: _Dev
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
    why = f"  - why: {_why(edit, dev)}"
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


def _structure_lead(edits: list[dict[str, Any]]) -> str:
    """The paragraph for the markup fixes alone. It says no wording changes only when no line of
    the README is changed by them; a heading marker is a changed line, and is said so."""
    closing = "Each is explained in the list below, with the line it sits on."
    changed = [e for e in edits if e["original"]]
    if not changed:
        return f"Rendering problems in README.md; no wording changes. {closing}"
    if all(_wording_neutral(e) for e in changed):
        only = (
            f"The only existing line that changes is line {changed[0]['line']}, and only its "
            "heading level"
            if len(changed) == 1
            else f"Existing lines change only at {_lines(changed)}, and only in heading levels"
        )
        return f"Rendering problems in README.md. {only}; no word changes. {closing}"
    return f"Rendering problems in README.md. {closing}"


def _overview_item(name: str, edits: list[dict[str, Any]], dev: _Dev) -> str:
    if name == "version":
        return "a release the registry has moved past"
    if name == "claims":
        return "claims the repository contradicts"
    if name == "link":
        return "a broken link" if len(edits) == 1 else f"{len(edits)} broken links"
    if name == "sections":
        names = _headings(edits)
        if names:
            return f"a missing {_join(names)} section{'s' if len(names) > 1 else ''}"
        return "a contents item"
    if name == "dev":
        items = []
        if dev.commands or dev.block:
            what = (
                "build and test commands" if len(dev.commands) != 1 else f"a {dev.roles[0]} command"
            )
            items.append(f"{what} the development section lacks")
        if dev.ci or dev.release:
            items.append(f"a sentence saying {_dev_sentence_words(dev.ci, dev.release)}")
        return _join(items)
    if name == "docs":
        return "links to project files the README does not mention"
    if name == "diagram":
        return "the At a Glance diagram layout"
    return "information the README lacks"


def _overview(groups: dict[str, list[dict[str, Any]]], dev: _Dev) -> str:
    """One sentence naming every change of a pull request that mixes markup fixes with others."""
    first = _structure_phrase(sorted(groups["structure"], key=lambda e: e["start"]))
    items = [first[0].upper() + first[1:]]
    items += [_overview_item(n, e, dev) for n, e in groups.items() if n != "structure"]
    return f"{_join(items, oxford=True)}. Each is listed below with its line."


def _dev_lead(dev: _Dev, revision: str) -> str:
    said: list[str] = []
    rev = f"revision `{revision[:12]}`"
    if dev.commands:
        if dev.shown:
            head = (
                f"{'The development section' if dev.here else 'The README'} shows "
                f"{_shown_words(dev.shown)} but not {_ROLE_SHORT[dev.roles[0]]}."
            )
        else:
            head = f"The README's development section does not show {_roles_phrase(dev.roles)}."
        if len(dev.commands) > 1:
            tail = (
                f"We add the commands below, run in this order on a clean clone of {rev} and each "
                f"exiting 0{', with the install steps they need first' if dev.setup else ''}."
            )
        else:
            command = f"`{_clip(dev.commands[0].value)}`"
            steps = ""
            if dev.setup:
                listed = len(dev.setup) <= 2
                steps = ", preceded by " + (
                    _join([f"`{_clip(s)}`" for s in dev.setup])
                    if listed
                    else "the steps it needs first"
                )
            ran = f" ({dev.platform})" if dev.platform else ""
            tail = (
                f"We add {command}{' after it' if dev.after else ''}{steps}. It exited 0 on a "
                f"clean clone of {rev}{ran}{'' if dev.setup else '; it needs no steps first'}."
            )
        said.append(f"{head} {tail}")
    elif dev.block:
        said.append(
            "The README's development section does not show how to build and test the project. "
            "We add the commands below."
        )
    if dev.ci or dev.release:
        said.append(
            f"The README does not say {_dev_sentence_words(dev.ci, dev.release)}. We add a "
            "sentence that links the workflow file stating it."
        )
    return " ".join(said)


def _has_item(edits: list[dict[str, Any]], heading: str) -> bool:
    """Whether the contents list gains an item for ``heading`` (a ``- [Heading](#...)`` line)."""
    return any(e["kind"] == "MISSING_INFO" and f"[{heading}]" in e["replacement"] for e in edits)


def _sections_lead(edits: list[dict[str, Any]]) -> str:
    names = _headings(edits)
    links = _links_section(edits)
    docs_links = bool(links) and _DOCS_HEADING in names
    whole = [n for n in names if not (docs_links and n == _DOCS_HEADING)]
    said: list[str] = []
    if whole:
        what = " and ".join(f"`{n}`" for n in whole)
        many = len(whole) > 1
        item = all(_has_item(edits, n) for n in whole)
        said.append(
            f"The README has no {what} section{'s' if many else ''}. "
            + ("We added them; each" if many else "We added one that")
            + " states what the repository's own files declare (cited below)"
            + (
                f", with an item for {'each' if many else 'it'} in the contents list."
                if item
                else "."
            )
        )
    if docs_links:
        targets = _either([f"`{target}`" for _label, target in links])
        both = "it" if len(links) == 1 else "both" if len(links) == 2 else "all"
        said.append(
            f"The README does not link {targets}, which the repository holds. We add a short "
            f"`{_DOCS_HEADING}` section that links {both}."
            + (
                " We also add an item for it to the contents list."
                if _has_item(edits, _DOCS_HEADING)
                else ""
            )
        )
    if not said:
        said.append(
            "We extended the contents list so a section the README holds can be reached from it."
        )
    return " ".join(said)


def _lead(
    groups: dict[str, list[dict[str, Any]]], facts: dict[str, Fact], revision: str, dev: _Dev
) -> list[str]:
    paragraphs: list[str] = []
    mixed = "structure" in groups and any(n not in {"structure", "diagram"} for n in groups)
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
            paragraphs.append(_overview(groups, dev) if mixed else _structure_lead(edits))
        elif name == "sections":
            paragraphs.append(_sections_lead(edits))
        elif name == "dev":
            paragraphs.append(_dev_lead(dev, revision))
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
                f"{_parts(name, edits, dev)[0].capitalize()}, against the repository at revision "
                f"`{revision[:12]}` (evidence cited below)."
            )
    return paragraphs


# ------------------------------------------------------------------------------------- checks
_LENGTH = re.compile(r"(\d+) visible lines of \d+ exceed the visible budget (\d+)")


#: The checks whose findings are about a maintainer's own README: commands, examples, links, and
#: version and edition claims. The others judge the layout and wording this tool gives the READMEs
#: it writes; a live README is not held to them, so what they find in it is never said to be wrong
#: with it, only reported when the correction itself changes it.
_ABOUT_YOURS = frozenset({"BC-02", "BC-03", "BC-06", "BC-12", "BC-14"})


def _tally(delta: dict[str, Any], only: frozenset[str] | None = None) -> tuple[int, int, int, int]:
    """``(before, after, removed, added)``: the failures the checks report on the README and on the
    corrected one, and how many of them the correction takes away and brings, check by check.
    ``only`` limits the count to those checks (a check's length variant counts with it)."""
    live = delta.get("live_failures", {})
    after = delta.get("corrected_failures", {})
    names = {n for n in set(live) | set(after) if only is None or n.split("/")[0] in only}
    removed = sum(max(live.get(n, 0) - after.get(n, 0), 0) for n in names)
    added = sum(max(after.get(n, 0) - live.get(n, 0), 0) for n in names)
    return (
        sum(live.get(n, 0) for n in names),
        sum(after.get(n, 0) for n in names),
        removed,
        added,
    )


def _span_line(original: str, span: str, start: int) -> int | None:
    """The line of the README that holds the code span ``span``, from ``start`` on."""
    needle = f"`{span}`"
    lines = original.splitlines()
    first = max(int(start), 1)
    for number in [*range(first, len(lines) + 1), *range(1, first)]:
        if needle in lines[number - 1]:
            return int(number)
    return None


def _revealed_line(
    revealed: list[dict[str, Any]], edits: list[dict[str, Any]], original: str
) -> tuple[int, str]:
    """``(count, bullet)``: the issues the checks newly find in text that was already there, and
    the change that lets them read it. The cause is the one the record names: a fix that changes a
    heading level changes how the README is split into sections, a closed block makes text
    visible; the two are never swapped."""
    count = sum(i["extra"] for i in revealed)
    spans = [
        m.group(1)
        for item in revealed
        for detail in item["details"]
        if (m := re.search(r"code span '([^']+)'", detail))
    ]
    causes = sorted({c for i in revealed for c in i.get("caused_by", [])})
    if not causes:
        causes = sorted({e["detector"] for e in edits if e["kind"] == "STRUCTURE_FIX"})
    if causes == ["second_h1"]:
        heading = next(e for e in edits if e["detector"] == "second_h1")
        number = _span_line(original, spans[0], heading["line"]) if spans else None
        at = f", line {number}" if number else ""
        if count == 1 and len(spans) == 1:
            result = f"they now judge a code span (`{spans[0]}`{at}) that they skipped before."
        else:
            example = f" (for example the code span `{spans[0]}`{at})" if spans else ""
            result = f"they now report {count} issue(s) in text they skipped before{example}."
        return count, (
            "- Changing the heading level changes how our checks split the README into "
            f"sections, so {result} That text is yours and is unchanged."
        )
    about = f" (for example the code span `{spans[0]}`)" if spans else ""
    if causes == ["unclosed_details"]:
        return count, (
            "- Closing the broken markup makes text visible that the checks could not read "
            f"before; they now report {count} issue(s) there{about}. That text is yours and this "
            "change does not alter it."
        )
    return count, (
        "- Fixing the markup problems changes how the checks read the README, so they now report "
        f"{count} issue(s) in text they could not read before{about}. That text is yours and this "
        "change does not alter it."
    )


def _delta_lines(
    delta: dict[str, Any], edits: list[dict[str, Any]], original: str = ""
) -> list[str]:
    """What the README checks found, computed from the record and nothing else: the totals before
    and after, what the correction removes and what it adds. It never says "fewer" unless it adds
    nothing, and every failure it adds is explained in a line of its own."""
    if not delta:
        return []
    before, after, removed, added = _tally(delta, _ABOUT_YOURS)
    shape = _tally(delta)[3] - added
    text = (
        "- We ran repository-presenter's README checks (install commands, examples, links, "
        "version and edition claims) on your README and on the corrected one. They report "
        f"{before} failure(s) on yours and {after} on the corrected one: "
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
    if shape:
        lines.append(
            "- Separately, our other checks (section layout, line length and wording rules for "
            f"the READMEs this tool writes, which yours is not held to) find {shape} new item(s) "
            "after the change; each is explained below."
        )
    explained = 0
    revealed = delta.get("revealed", [])
    if revealed:
        count, bullet = _revealed_line(revealed, edits, original)
        explained += count
        lines.append(bullet)
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
    if added + shape > explained:
        lines.append(
            f"- {added + shape - explained} of the failure(s) it adds are new problems this change "
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
    original_file = bundle / ORIGINAL_NAME
    original = original_file.read_text(encoding="utf-8") if original_file.is_file() else ""
    dev = _dev_state(edits, facts, original, document)
    stability = document.get("stability", {})
    render = document.get("render_check")
    checks = [
        "- Only `README.md` changes, and only at the places listed: with the edits removed, the "
        "corrected README and yours are identical.",
        *_delta_lines(delta, edits, original),
        "- Running the correction again on the corrected README makes no further edit "
        f"(idempotent: {'yes' if stability.get('idempotent') else 'NO'}); the same inputs give the "
        f"same bytes (deterministic: {'yes' if stability.get('deterministic') else 'NO'}). No "
        f"model wrote any of this text (model calls: {stability.get('provider_calls', 0)}).",
        *_render_lines(document),
    ]
    changes: list[str] = []
    for edit in sorted(edits, key=lambda e: (e["kind"] == "DIAGRAM_FIX", e["start"])):
        changes += _bullet(edit, facts, render, dev)  # the content changes first, the diagram last
    above = "\n".join(
        [
            *[p + "\n" for p in _lead(groups, facts, source_revision, dev)],
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
    return PullRequestContent(title=title_of(edits, dev), body=above + "\n\n" + footer)
