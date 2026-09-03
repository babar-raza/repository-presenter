"""Stage S9: the versioned registry of exactly the eleven blocking checks.

docs/README_CONTRACT.md section 5 names the checks that block acceptance at G1; everything else is
advisory until contract v1 freezes. Each check here carries a versioned ID, the sections it
judges, and - when it fails - the causal stage the repair loop reopens (docs/STATE_MACHINE.md
section 8), so a failure is routed to its cause and never masked at validation. The checks run
over the candidate's README, facts, plan, units, and dispositions and nothing else; two of them
are judged by later stages - the independent review (S10) and the fresh-process rerun (S12) - and
stay PENDING in validation.json until those stages write their verdict. The advisory notes the
document records are context for the reviewer, never a verdict.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    allowed_identifiers,
    identifier_allowed,
    surface_members,
    unit_checks,
    verified_members,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    SUBSECTION_HEADINGS,
)
from repository_presenter.components.readme.composition.placement import (
    Placement,
    placements,
)
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
)
from repository_presenter.components.readme.composition.renderer import line_counts
from repository_presenter.components.readme.evidence.facts.links import (
    check_anchor,
    check_relative,
    extract_links,
    heading_slugs,
)
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret, scan_for_secrets

VALIDATION_FILENAME = "validation.json"
VALIDATOR_VERSION = "1"
Verdict = Literal["PASS", "FAIL", "PENDING"]
CausalStage = Literal["EXTRACTING", "INVESTIGATING", "RECONCILING", "PLANNING", "COMPOSING"]
STAGE_ORDER: tuple[CausalStage, ...] = (
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
)


@dataclass(frozen=True)
class Check:
    """One blocking check of the contract, versioned so a change re-checks accepted candidates."""

    id: str
    version: str
    name: str
    sections: tuple[str, ...]
    judged_at: str


BLOCKING_CHECKS: tuple[Check, ...] = (
    Check(
        "BC-01",
        "1",
        "Source revision pinned; original README bytes exact; every fact carries evidence",
        ("all",),
        "S9",
    ),
    Check(
        "BC-02",
        "1",
        "Install command verified against the manifest and the package-registry observation",
        ("installation",),
        "S9",
    ),
    Check(
        "BC-03",
        "1",
        "Every rendered example was executed or compiled in isolation at this revision",
        ("quick_start", "additional_examples"),
        "S9",
    ),
    Check(
        "BC-04",
        "1",
        "Every content unit cites existing SUPPORTED facts; every identifier in prose is a fact "
        "value in a code span",
        (
            "opening",
            "key_capabilities",
            "scope_limitations",
            "api_reference",
            "documentation_resources",
            "enterprise_relationship",
        ),
        "S9",
    ),
    Check(
        "BC-05",
        "1",
        "Every material inherited unit has exactly one disposition; placed units appear in their "
        "destination",
        ("all",),
        "S9",
    ),
    Check(
        "BC-06",
        "1",
        "Every link resolves; Aspose links are within the ceiling; Enterprise Edition is the "
        "only edition name",
        ("documentation_resources", "enterprise_relationship", "badges"),
        "S9",
    ),
    Check(
        "BC-07",
        "1",
        "Exactly one factual H1; one badge row; title-case headings; canonical abbreviations; "
        "At a Glance topology and column rules; no internal narration; within the length budget",
        ("structure",),
        "S9",
    ),
    Check("BC-08", "1", "Protected content preserved", ("all",), "S9"),
    Check("BC-09", "1", "No configured secret in the bundle", ("bundle",), "S9"),
    Check(
        "BC-10",
        "1",
        "Independent review returns ACCEPT under a reviewer identity separate from authoring",
        ("review",),
        "S10",
    ),
    Check(
        "BC-11",
        "1",
        "Fresh-process rerun is byte-identical with zero provider calls",
        ("bundle",),
        "S12",
    ),
)


@dataclass(frozen=True)
class Failure:
    stage: CausalStage | None
    detail: str


@dataclass(frozen=True)
class Candidate:
    """Everything S9 reads: the artifacts, the snapshot facts they must agree with, the tasks."""

    entry: RegistryEntry
    facts: FactsDocument
    plan: dict[str, Any]
    units: dict[str, Any]
    dispositions: dict[str, Any]
    readme: str
    original_readme: bytes | None
    source_revision: str
    readme_sha256: str | None
    tree_paths: Sequence[str]
    tasks: Sequence[SectionTask]
    policy: PlanningPolicy = DEFAULT_POLICY


_PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
_EXECUTION_MARKERS = (": EXECUTED", ": COMPILED")
# (level, is a shell heading, is a prescribed subheading) combinations a heading may take
_HEADING_OK = frozenset({(2, True, False), (3, False, True)})
_SPAN = re.compile(r"`([^`]+)`")
_BADGE_TOKEN = r"(?:\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\))"
_BADGE_ROW = re.compile(rf"{_BADGE_TOKEN}(?: {_BADGE_TOKEN})*")
_EDITION = re.compile(r"\b([A-Z][A-Za-z]+) Edition\b")
# A word after a dot is an extension spelling (.dae), not an abbreviation.
_LOWER_WORD = re.compile(r"(?<![.\w])[a-z]{3,}\b")
_LINK_DESTINATION = re.compile(r"\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip3?|python3?(?:\s+-m)?|npm|npx|yarn|pnpm|dotnet|mvn|gradle|go|"
    r"cargo|cmake|make|git)\b",
    re.IGNORECASE,
)
_CAPABILITY_NODE = re.compile(r"^\s*C(\d+)\[", re.MULTILINE)
_CAPABILITY_EDGE = re.compile(r"^\s*C\d+\s*(?:-->|---)", re.MULTILINE)
_ABBREVIATIONS = frozenset(
    {
        "PDF",
        "XLSX",
        "HTML",
        "EPS",
        "XPS",
        "API",
        "JSON",
        "XML",
        "CSV",
        "SVG",
        "URL",
        "HTTP",
        "SDK",
        "CLI",
    }
)
# Format extensions that are also ordinary words are never judged as abbreviations.
_WORD_EXTENSIONS = frozenset({"max", "ply", "dat", "raw", "bin", "log", "map", "mat", "tag", "ini"})
_NARRATION = (
    "preserved repository details",
    "other platforms",
    "provider call",
    "source revision",
    "validator",
    "isolated build",
    "fact id",
    "generated by",
    "this readme was",
)
_RENDERER_HOSTS = frozenset({"img.shields.io"})
_ASPOSE_SUFFIXES = (".aspose.com", ".aspose.org", ".aspose.app", ".aspose.cloud")
_ASPOSE_HOSTS = frozenset({"aspose.com", "aspose.org", "aspose.app", "aspose.cloud"})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def _fences(readme: str) -> list[tuple[str, str]]:
    """(language, body) of every fenced block, in document order."""
    found: list[tuple[str, str]] = []
    language: str | None = None
    body: list[str] = []
    for line in readme.splitlines():
        stripped = line.strip()
        if language is None and stripped.startswith("```"):
            language = stripped[3:].strip()
            body = []
        elif language is not None and stripped == "```":
            found.append((language, "\n".join(body)))
            language = None
        elif language is not None:
            body.append(line)
    return found


def _outside_fences(readme: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        elif not inside:
            lines.append(line)
    return lines


def _prose(lines: Sequence[str]) -> str:
    """Prose outside code spans, link destinations, URLs, and headings."""
    kept = [line for line in lines if not line.startswith("#")]
    text = "\n".join(kept)
    text = _SPAN.sub(" ", text)
    text = _LINK_DESTINATION.sub("]", text)
    return _URL.sub(" ", text)


def _section_texts(readme: str) -> dict[str, str]:
    """The text under each headed shell section, keyed by section id."""
    by_heading = {section.heading: section.id for section in SEMANTIC_SHELL if section.heading}
    texts: dict[str, list[str]] = {}
    current: str | None = None
    inside = False
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") and not inside:
            inside = True
        elif stripped == "```" and inside:
            inside = False
        if not inside and line.startswith("## "):
            current = by_heading.get(line[3:].strip())
            continue
        if current is not None:
            texts.setdefault(current, []).append(line)
    return {section: "\n".join(lines) for section, lines in texts.items()}


def _unit_type(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _fence_body(value: str) -> tuple[str, str]:
    """(language, body) of an inherited code block's source text."""
    lines = value.splitlines()
    if lines and lines[0].strip().startswith("```"):
        language = lines[0].strip()[3:].strip()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return language, "\n".join(lines)
    return "", value


def _example_for_unit(facts: FactsDocument, unit_id: str) -> Fact | None:
    marker = f"unit {unit_id}"
    for fact in facts.by_kind("example"):
        if any(marker in (evidence.detail or "") for evidence in fact.evidence):
            return fact
    return None


def _placements(candidate: Candidate) -> list[Placement]:
    return placements(
        candidate.plan, candidate.dispositions, candidate.facts, candidate.entry.ecosystem
    )


def _placed_texts(candidate: Candidate) -> list[str]:
    return [p.text for p in _placements(candidate) if p.outcome == "placed"]


def _check_source(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    facts = candidate.facts
    if facts.source_revision != candidate.source_revision:
        failures.append(
            Failure(
                "EXTRACTING",
                f"facts.json records revision {facts.source_revision}; the snapshot pinned "
                f"{candidate.source_revision}",
            )
        )
    revision = next((f for f in facts.facts if f.id == "identity:revision"), None)
    if revision is not None and revision.value != candidate.source_revision:
        failures.append(
            Failure("EXTRACTING", f"identity:revision is {revision.value}, not the pinned revision")
        )
    if candidate.original_readme is not None and (
        _sha256(candidate.original_readme) != candidate.readme_sha256
    ):
        failures.append(
            Failure("EXTRACTING", "the original README bytes differ from the snapshot digest")
        )
    for fact in facts.facts:
        if not fact.evidence:
            failures.append(Failure("EXTRACTING", f"{fact.id} carries no evidence"))
    return failures


def _check_install(candidate: Candidate) -> list[Failure]:
    installs = candidate.facts.by_kind("install_command")
    if not installs:
        return [
            Failure(
                "EXTRACTING",
                "no install command fact; the source install is not verified at this revision",
            )
        ]
    failures: list[Failure] = []
    for fact in installs:
        details = " ".join(evidence.detail or "" for evidence in fact.evidence)
        if fact.polarity != "SUPPORTED":
            last = fact.evidence[-1].detail or "" if fact.evidence else ""
            failures.append(Failure("EXTRACTING", f"{fact.id} is {fact.polarity}: {last}"))
        elif "manifest" not in details or "package registry" not in details:
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact.id} lacks manifest or package-registry evidence: {details}",
                )
            )
        elif f"```bash\n{fact.value}\n```" not in candidate.readme:
            failures.append(
                Failure("COMPOSING", f"the Installation section does not render {fact.value!r}")
            )
    return failures


def _check_examples(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    by_id = {fact.id: fact for fact in candidate.facts.facts}
    plan = candidate.plan
    planned = [
        fact_id
        for fact_id in [plan.get("quick_start_example_id"), *plan.get("additional_example_ids", [])]
        if fact_id
    ]
    for fact_id in planned:
        fact = by_id.get(fact_id)
        if fact is None or fact.kind != "example":
            failures.append(Failure("PLANNING", f"{fact_id} is not an example fact"))
            continue
        executed = any(
            marker in (evidence.detail or "")
            for evidence in fact.evidence
            for marker in _EXECUTION_MARKERS
        )
        if fact.polarity != "SUPPORTED" or not executed:
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"{fact_id} was not executed or compiled at this revision ({fact.polarity})",
                )
            )
    values = {by_id[fact_id].value.rstrip("\n") for fact_id in planned if fact_id in by_id}
    for language, body in _fences(candidate.readme):
        if language == candidate.entry.ecosystem and body.rstrip("\n") not in values:
            first = body.strip().splitlines()[0] if body.strip() else ""
            failures.append(
                Failure(
                    "COMPOSING",
                    f"a {language} code block is not a planned verified example: {first[:60]!r}",
                )
            )
    return failures


def _check_units(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    facts = candidate.facts
    name = product_name(candidate.entry)
    by_id = {fact.id: fact for fact in facts.facts}
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in candidate.units.get("units", []):
        by_section.setdefault(str(unit.get("section", "")), []).append(unit)
        label = f"{unit.get('section')}/{unit.get('slot')}"
        for fact_id in unit.get("fact_ids", []):
            fact = by_id.get(fact_id)
            if fact is None:
                failures.append(Failure("COMPOSING", f"{label} cites unknown fact {fact_id}"))
            elif fact.polarity != "SUPPORTED":
                failures.append(
                    Failure("COMPOSING", f"{label} cites {fact_id}, which is {fact.polarity}")
                )
    for task in candidate.tasks:
        partial = {"units": by_section.get(task.section_id, []), "omitted": []}
        failures.extend(
            Failure("COMPOSING", f"{task.section_id}: {error}")
            for error in unit_checks(partial, task, facts, name)
        )
    allowed = allowed_identifiers(facts, name)
    members = verified_members(facts)
    methods = surface_members(facts)
    values = {fact.value for fact in facts.facts if fact.polarity == "SUPPORTED"}
    symbols = {
        fact.value.rsplit(".", 1)[-1]
        for fact in facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
    }
    placed_lines = {line for text in _placed_texts(candidate) for line in text.splitlines()}
    # A deterministic section's spans come from facts and their evidence (a manifest path, a
    # declaration key), so the identifier rule judges authored prose only.
    owners = {section.id: section.owner for section in SEMANTIC_SHELL}
    renderer_lines = {
        line
        for section_id, text in _section_texts(candidate.readme).items()
        if owners.get(section_id) == "D"
        for line in text.splitlines()
    }
    seen: set[str] = set()
    for line in _outside_fences(candidate.readme):
        if line in placed_lines or line in renderer_lines:
            continue
        for span in _SPAN.findall(line):
            if span in seen:
                continue
            seen.add(span)
            if (
                span not in values
                and span not in symbols
                and not identifier_allowed(span, allowed, members, methods)
            ):
                failures.append(Failure("COMPOSING", f"code span {span!r} is not a fact value"))
    return failures


def _check_dispositions(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    inherited = {fact.id: fact for fact in candidate.facts.by_kind("inherited_unit")}
    entries = candidate.dispositions.get("dispositions", [])
    counts = Counter(str(entry.get("unit_id", "")) for entry in entries)
    for unit_id in inherited:
        if counts.get(unit_id, 0) != 1:
            failures.append(
                Failure(
                    "RECONCILING",
                    f"{unit_id} has {counts.get(unit_id, 0)} dispositions; exactly one is required",
                )
            )
    for unit_id in counts:
        if unit_id not in inherited:
            failures.append(
                Failure("RECONCILING", f"{unit_id} is not an inherited unit of this README")
            )
    headed = {section.id for section in SEMANTIC_SHELL if section.heading}
    texts = _section_texts(candidate.readme)
    for placement in _placements(candidate):
        destination = placement.destination
        if placement.outcome == "excluded":
            failures.append(
                Failure(
                    "PLANNING",
                    f"{placement.unit_id} was placed in {destination}, which the plan omits",
                )
            )
            continue
        if placement.outcome != "placed":
            continue  # owned by the plan or the renderer, or dropped for fact-ID overlap
        haystack = texts.get(destination, "") if destination in headed else candidate.readme
        if _normalized(placement.text) not in _normalized(haystack):
            failures.append(
                Failure(
                    "COMPOSING",
                    f"{placement.unit_id} was placed in {destination} but the candidate does "
                    "not render it there",
                )
            )
    return failures


def _is_aspose(host: str) -> bool:
    return host in _ASPOSE_HOSTS or host.endswith(_ASPOSE_SUFFIXES)


def _renderer_owned(candidate: Candidate, href: str) -> bool:
    """A target the renderer derives from verified facts rather than from the README's links."""
    parts = urlsplit(href)
    host = (parts.hostname or "").lower()
    if host in _RENDERER_HOSTS:
        return True
    package = next(
        (f.value for f in candidate.facts.by_kind("package") if f.id == "package:name"), None
    )
    if host == "pypi.org" and package is not None:
        return parts.path.rstrip("/") == f"/project/{package}"
    if host == "github.com":
        return parts.path.startswith(f"/{candidate.entry.repository}/")
    return False


def _check_links(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    slugs = heading_slugs(candidate.readme)
    by_value = {fact.value: fact for fact in candidate.facts.by_kind("link_target")}
    aspose = 0
    for target in extract_links(candidate.readme):
        if target.kind == "anchor":
            result = check_anchor(target.href, slugs)
            if result.outcome != "RESOLVED":
                failures.append(Failure("COMPOSING", f"{target.href}: {result.detail}"))
        elif target.kind == "relative":
            result = check_relative(target.href, candidate.tree_paths)
            if result.outcome != "RESOLVED":
                failures.append(Failure("EXTRACTING", f"{target.href}: {result.detail}"))
        elif target.kind == "external":
            host = (urlsplit(target.href).hostname or "").lower()
            if _is_aspose(host):
                aspose += 1
            fact = by_value.get(target.href)
            if fact is not None:
                if fact.polarity != "SUPPORTED":
                    last = fact.evidence[-1].detail or "" if fact.evidence else ""
                    failures.append(
                        Failure("EXTRACTING", f"{target.href} is {fact.polarity}: {last}")
                    )
            elif not _renderer_owned(candidate, target.href):
                failures.append(Failure("PLANNING", f"{target.href} is not a verified link target"))
        else:
            failures.append(
                Failure("COMPOSING", f"{target.href}: {target.kind} links are never rendered")
            )
    ceiling = candidate.policy.aspose_links_max
    if aspose > ceiling:
        failures.append(
            Failure("PLANNING", f"{aspose} Aspose links exceed the ceiling of {ceiling}")
        )
    for match in _EDITION.finditer(_prose(_outside_fences(candidate.readme))):
        if match.group(1) != "Enterprise":
            failures.append(Failure("COMPOSING", f"non-canonical edition name {match.group(0)!r}"))
    return failures


def _topology_failures(body: str) -> list[Failure]:
    failures: list[Failure] = []
    lines = [line.strip() for line in body.splitlines()]
    if lines.count("P --- C") != 1:
        failures.append(
            Failure(
                "COMPOSING",
                "At a Glance needs exactly one relationship from the product to Core capabilities",
            )
        )
    if lines.count("C --- O") > 1:
        failures.append(
            Failure("COMPOSING", "At a Glance needs at most one relationship to Outputs")
        )
    if _CAPABILITY_EDGE.search(body):
        failures.append(Failure("COMPOSING", "At a Glance: a capability fans out"))
    count = len(_CAPABILITY_NODE.findall(body))
    invisible = sum(1 for line in lines if "~~~" in line)
    if count > 8:
        failures.append(Failure("PLANNING", f"At a Glance shows {count} capabilities; at most 8"))
    elif count <= 5 and invisible:
        failures.append(
            Failure("COMPOSING", f"At a Glance: {count} capabilities form one column, not two")
        )
    elif count >= 6 and invisible != count // 2:
        failures.append(
            Failure(
                "COMPOSING",
                f"At a Glance: {count} capabilities form two balanced columns; "
                f"found {invisible} row links, expected {count // 2}",
            )
        )
    return failures


def _check_structure(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    name = product_name(candidate.entry)
    outside = _outside_fences(candidate.readme)
    h1 = [line for line in outside if line.startswith("# ")]
    if h1 != [f"# {name}"]:
        failures.append(
            Failure("COMPOSING", f"expected exactly one H1 {'# ' + name!r}; found {len(h1)}")
        )
    badge_rows = [line for line in outside if _BADGE_ROW.fullmatch(line.strip())]
    if len(badge_rows) != 1:
        failures.append(Failure("COMPOSING", f"expected one badge row; found {len(badge_rows)}"))
    headings = {section.heading for section in SEMANTIC_SHELL if section.heading}
    for line in outside:
        if line.startswith("#") and not line.startswith("# "):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            if (level, text in headings, text in SUBSECTION_HEADINGS) not in _HEADING_OK:
                failures.append(
                    Failure("COMPOSING", f"heading {line!r} is not a shell heading in title case")
                )
    prose = _prose(outside)
    lower_forms = {abbreviation.lower() for abbreviation in _ABBREVIATIONS}
    for fact in candidate.facts.by_kind("format"):
        extension = fact.value.lstrip(".").lower()
        if len(extension) >= 3 and extension.isalpha() and extension not in _WORD_EXTENSIONS:
            lower_forms.add(extension)
    for word in sorted(set(_LOWER_WORD.findall(prose))):
        if word in lower_forms:
            failures.append(
                Failure(
                    "COMPOSING",
                    f"abbreviation {word!r} is not in its canonical form {word.upper()}",
                )
            )
    graphs = [body for language, body in _fences(candidate.readme) if language == "mermaid"]
    if len(graphs) > 1:
        failures.append(Failure("COMPOSING", "more than one At a Glance graph"))
    for body in graphs:
        failures.extend(_topology_failures(body))
    lowered = prose.lower()
    for phrase in _NARRATION:
        if phrase in lowered:
            failures.append(Failure("COMPOSING", f"internal narration {phrase!r}"))
    visible, total = line_counts(candidate.readme)
    policy = candidate.policy
    if visible > policy.visible_lines_budget or total > policy.total_lines_budget:
        failures.append(
            Failure(
                "PLANNING",
                f"{visible} visible lines of {total} exceed the budget "
                f"{policy.visible_lines_budget}/{policy.total_lines_budget}",
            )
        )
    return failures


def protected_fragments(candidate: Candidate) -> list[tuple[str, str, str]]:
    """(category, text, unit_id) for every command, ecosystem example, and verbatim-placed
    prose unit of the existing README - the content whose loss the check judges."""
    fragments: list[tuple[str, str, str]] = []
    placed = {p.unit_id for p in _placements(candidate) if p.outcome == "placed"}
    for fact in candidate.facts.by_kind("inherited_unit"):
        unit_type = _unit_type(fact.id)
        if unit_type == "code_block":
            language, body = _fence_body(fact.value)
            if language == candidate.entry.ecosystem and body.strip():
                fragments.append(("example", body, fact.id))
            fragments.extend(
                ("command", line.strip(), fact.id)
                for line in body.splitlines()
                if _COMMAND.match(line)
            )
        else:
            fragments.extend(
                ("command", span, fact.id)
                for span in _SPAN.findall(fact.value)
                if _COMMAND.match(span)
            )
            if fact.id in placed:
                fragments.append(("unit", fact.value, fact.id))
    return fragments


def protected_fingerprint(fragments: Sequence[tuple[str, str, str]]) -> str:
    digests = sorted(
        f"{category}:{_sha256(_normalized(text).encode('utf-8'))}"
        for category, text, _unit in fragments
    )
    return _sha256("\n".join(digests).encode("utf-8"))


def _check_protected(candidate: Candidate) -> list[Failure]:
    failures: list[Failure] = []
    by_unit = {
        str(entry.get("unit_id", "")): entry
        for entry in candidate.dispositions.get("dispositions", [])
    }
    normalized_readme = _normalized(candidate.readme)
    for category, text, unit_id in protected_fragments(candidate):
        disposition = by_unit.get(unit_id, {}).get("disposition")
        if disposition not in _PLACING or category == "unit":
            continue
        if _normalized(text) in normalized_readme:
            continue
        if category == "example":
            example = _example_for_unit(candidate.facts, unit_id)
            if example is None or example.polarity != "SUPPORTED":
                failures.append(
                    Failure(
                        "RECONCILING",
                        f"{unit_id}: {disposition} keeps an example that was never verified "
                        f"({'no example fact' if example is None else example.polarity}); "
                        "it cannot be rendered",
                    )
                )
            else:
                failures.append(
                    Failure(
                        "COMPOSING",
                        f"{unit_id}: {disposition} keeps {example.id} but the candidate does "
                        "not render it",
                    )
                )
        else:
            failures.append(
                Failure(
                    "COMPOSING",
                    f"{unit_id}: {disposition} keeps the command {text!r} but the candidate "
                    "does not render it",
                )
            )
    return failures


def advisory_notes(candidate: Candidate) -> list[str]:
    """Context for the reviewer that cannot block: technical terms a rewrite left out."""
    by_id = {fact.id: fact for fact in candidate.facts.by_kind("inherited_unit")}
    notes: list[str] = []
    for entry in candidate.dispositions.get("dispositions", []):
        unit_id = str(entry.get("unit_id", ""))
        if entry.get("disposition") != "VERIFIED_REWRITE" or unit_id not in by_id:
            continue
        dropped = sorted(
            {
                span
                for span in _SPAN.findall(by_id[unit_id].value)
                if f"`{span}`" not in candidate.readme and not _COMMAND.match(span)
            }
        )
        if dropped:
            notes.append(f"{unit_id}: the rewrite no longer names {', '.join(dropped)}")
    return notes


def _earliest(failures: Sequence[Failure]) -> CausalStage | None:
    stages = [failure.stage for failure in failures if failure.stage is not None]
    if not stages:
        return None
    return min(stages, key=STAGE_ORDER.index)


def validate_candidate(
    candidate: Candidate, transaction: Path, secrets: Sequence[ConfiguredSecret]
) -> dict[str, Any]:
    """validation.json: every blocking check with its verdict, causal stage, and details."""

    def check_secrets(_candidate: Candidate) -> list[Failure]:
        return [
            Failure(None, f"value of {leak.variable} found in {leak.path.name}")
            for leak in scan_for_secrets(transaction, secrets)
        ]

    judges: dict[str, Callable[[Candidate], list[Failure]]] = {
        "BC-01": _check_source,
        "BC-02": _check_install,
        "BC-03": _check_examples,
        "BC-04": _check_units,
        "BC-05": _check_dispositions,
        "BC-06": _check_links,
        "BC-07": _check_structure,
        "BC-08": _check_protected,
        "BC-09": check_secrets,
    }
    checks: list[dict[str, Any]] = []
    for check in BLOCKING_CHECKS:
        record: dict[str, Any] = {
            "id": check.id,
            "version": check.version,
            "name": check.name,
            "sections": list(check.sections),
            "judged_at": check.judged_at,
            "causal_stage": None,
            "details": [],
        }
        if check.judged_at != "S9":
            record["verdict"] = "PENDING"
            record["details"] = [f"judged at {check.judged_at}"]
        else:
            failures = judges[check.id](candidate)
            record["verdict"] = "FAIL" if failures else "PASS"
            record["causal_stage"] = _earliest(failures)
            record["details"] = [failure.detail for failure in failures]
        checks.append(record)
    verdicts = Counter(record["verdict"] for record in checks)
    return {
        "schema_version": 1,
        "validator_version": VALIDATOR_VERSION,
        "repository": candidate.entry.repository,
        "source_revision": candidate.source_revision,
        "readme_sha256": _sha256(candidate.readme.encode("utf-8")),
        "protected_content_fingerprint": protected_fingerprint(protected_fragments(candidate)),
        "checks": checks,
        "advisory": advisory_notes(candidate),
        "summary": {
            "pass": verdicts.get("PASS", 0),
            "fail": verdicts.get("FAIL", 0),
            "pending": verdicts.get("PENDING", 0),
        },
    }


def record_review_verdict(document: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """validation.json with check 10 judged from review.json: PASS on ACCEPT under a separate
    reviewer identity; otherwise FAIL, routed to the earliest causal state the findings name."""
    findings = list(review.get("findings", []))
    states = [f.get("causal_state") for f in findings if f.get("causal_state") in STAGE_ORDER]
    accepted = review.get("verdict") == "ACCEPT" and bool(review.get("identity_separate"))
    if accepted:
        verdict, stage, details = "PASS", None, []
    else:
        verdict = "FAIL"
        stage = min(states, key=STAGE_ORDER.index) if states else None
        if not review.get("identity_separate"):
            details = ["the reviewer identity is not separate from authoring"]
        else:
            details = [f"{review.get('verdict')}"] + [
                f"{f.get('id')} {f.get('section_id')} ({f.get('causal_state')}): {f.get('text')}"
                for f in findings
            ]
    checks = [
        {**check, "verdict": verdict, "causal_stage": stage, "details": details}
        if check.get("id") == "BC-10"
        else check
        for check in document.get("checks", [])
    ]
    verdicts = Counter(check["verdict"] for check in checks)
    return {
        **document,
        "checks": checks,
        "summary": {
            "pass": verdicts.get("PASS", 0),
            "fail": verdicts.get("FAIL", 0),
            "pending": verdicts.get("PENDING", 0),
        },
    }


def record_replay_verdict(document: dict[str, Any]) -> dict[str, Any]:
    """validation.json with check 11 judged PASS by the fresh-process no-op proof."""
    checks = [
        {
            **check,
            "verdict": "PASS",
            "causal_stage": None,
            "details": [
                "judged by the fresh-process replay: every artifact byte-identical, zero "
                "provider calls"
            ],
        }
        if check.get("id") == "BC-11"
        else check
        for check in document.get("checks", [])
    ]
    verdicts = Counter(check["verdict"] for check in checks)
    return {
        **document,
        "checks": checks,
        "summary": {
            "pass": verdicts.get("PASS", 0),
            "fail": verdicts.get("FAIL", 0),
            "pending": verdicts.get("PENDING", 0),
        },
    }


def blocking_failures(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [check for check in document.get("checks", []) if check.get("verdict") == "FAIL"]


def summarize_validation(document: dict[str, Any]) -> str:
    summary = document.get("summary", {})
    return (
        f"pass {summary.get('pass', 0)}, fail {summary.get('fail', 0)}, "
        f"pending {summary.get('pending', 0)}"
    )


def write_validation(document: dict[str, Any], path: Path) -> str:
    """Write validation.json as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
