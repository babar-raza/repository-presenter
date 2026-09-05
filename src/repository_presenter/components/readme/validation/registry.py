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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    allowed_identifiers,
    canonical_abbreviations,
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
from repository_presenter.components.readme.evidence.facts.product_pages import banner_target
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret, scan_for_secrets

VALIDATION_FILENAME = "validation.json"
VALIDATOR_VERSION = "3"
# The shell rows README_CONTRACT.md section 2 marks Required: the sections every candidate has,
# and so the ones that admit no deferred work before READY_FOR_PROPOSAL (section 6).
REQUIRED_SECTIONS = frozenset(section.id for section in SEMANTIC_SHELL if section.required)
# The fact kinds each shell row's content rests on, read from README_CONTRACT.md section 2's own
# Content column. A row whose kinds resolve to nothing renders thin rather than absent, and
# nothing today says so: the coverage ledger reports the resolution per row so a gap in the
# evidence is visible as a gap (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC6, 27.5 D6).
# Structural rows - navigation renders from the sections present - rest on no fact kind.
ROW_FACT_KINDS: dict[str, tuple[str, ...]] = {
    "identity": ("identity",),
    "badges": ("license", "package", "link_target"),
    "banner": ("link_target",),
    "opening": ("identity", "package", "format", "public_symbol"),
    "navigation": (),
    "at_a_glance": ("format", "public_symbol"),
    "key_capabilities": ("public_symbol", "example", "format", "import_path"),
    "installation": ("install_command", "package"),
    "dependencies": ("dependency",),
    "quick_start": ("example",),
    "additional_examples": ("example",),
    "api_reference": ("public_symbol",),
    "documentation_resources": ("link_target",),
    "scope_limitations": ("inherited_unit", "example", "public_symbol"),
    "development_testing": ("build_test_asset",),
    "enterprise_relationship": ("link_target",),
    "third_party_notices": ("third_party_notices",),
    "license": ("license",),
}
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
        "2",
        "Exactly one factual H1; one badge row; title-case headings; canonical abbreviations; "
        "At a Glance topology and column rules; no internal narration; within the length budget",
        ("structure",),
        "S9",
    ),
    Check("BC-08", "1", "Protected content preserved", ("all",), "S9"),
    Check("BC-09", "1", "No configured secret in the bundle", ("bundle",), "S9"),
    Check(
        "BC-10",
        "2",
        "Independent review returns ACCEPT under a reviewer identity separate from authoring, "
        "with no advisory left on a required row",
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
    """One reason a blocking check failed, with the two fields that route it.

    ``section`` is the shell section the failure is about, set by the judge that knows it. It is
    a field rather than a prefix parsed back out of ``detail`` because routing a defect to its
    causal stage must not depend on prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC8,
    27.5 D5).
    """

    stage: CausalStage | None
    detail: str
    section: str | None = None


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
_HEADING_OK = frozenset({(2, True, False), (3, False, True), (4, False, True)})
_EXAMPLE_N = re.compile(r"(?i)example\s*\d+")
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
_CAPABILITY_NODE = re.compile(r"^\s*c(\d+)\[", re.MULTILINE)
_GLANCE_LABEL = re.compile(r"\[\"([^\"]*)\"\]")
_GLANCE_DIRECTIVE = re.compile(r"^(?:style|classDef|linkStyle|click)\b")
_GLANCE_FENCE = re.compile(r"```mermaid\n.*?\n```", re.DOTALL)
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
        for fact_id in [
            plan.get("quick_start_example_id"),
            plan.get("second_quick_start_example_id"),  # row 10: up to two quick starts
            *plan.get("additional_example_ids", []),
        ]
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
            section = str(unit.get("section", "")) or None
            if fact is None:
                failures.append(
                    Failure("COMPOSING", f"{label} cites unknown fact {fact_id}", section)
                )
            elif fact.polarity != "SUPPORTED":
                failures.append(
                    Failure(
                        "COMPOSING",
                        f"{label} cites {fact_id}, which is {fact.polarity}",
                        section,
                    )
                )
    for task in candidate.tasks:
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        partial = {"units": owned, "omitted": []}
        failures.extend(
            Failure("COMPOSING", f"{task.section_id}: {error}", task.section_id)
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
    section_texts = _section_texts(candidate.readme)
    renderer_lines = {
        line
        for section_id, text in section_texts.items()
        if owners.get(section_id) == "D"
        for line in text.splitlines()
    }
    # The API Reference table rows and member bullets are rendered from the symbol facts.
    renderer_lines.update(
        line
        for line in section_texts.get("api_reference", "").splitlines()
        if line.startswith(("| ", "- `"))
    )
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
    # The ceiling (README_CONTRACT.md row 15) bounds the contextual Aspose links the plan
    # assigns; the rows the contract itself mandates, the banner (row 3) and the Enterprise
    # target (row 18), are shell-rendered from the verified product facts and stand outside it.
    mandated = {
        fact.value
        for fact in candidate.facts.by_kind("link_target")
        if fact.id.startswith("link_target:product.") and fact.polarity == "SUPPORTED"
    }
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
            if _is_aspose(host) and target.href not in mandated:
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


def _column_size(lines: list[str], name: str) -> int | None:
    """How many capability nodes the named column subgraph holds; None when it is absent."""
    try:
        index = lines.index(f'subgraph {name}[" "]')
    except ValueError:
        return None
    size = 0
    for line in lines[index + 1 :]:
        if line == "end":
            break
        if _CAPABILITY_NODE.match(line):
            size += 1
    return size


def _topology_failures(body: str, has_inputs: bool) -> list[Failure]:
    """README_CONTRACT.md section 2.1: one chain with one edge per hop, groups as single
    listing nodes, Starting Points only with a verified input format, one column up to five
    capabilities and two balanced columns from six, geometry-safe labels, no styling."""
    failures: list[Failure] = []
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or lines[0] != "flowchart TD":
        failures.append(Failure("COMPOSING", "At a Glance is a flowchart TD"))
    starting = any(line.startswith("subgraph StartingPoints[") for line in lines)
    outputs = any(line.startswith("subgraph Outputs[") for line in lines)
    chain = " --> ".join(
        group
        for group, present in (
            ("StartingPoints", starting),
            ("PRODUCT", True),
            ("Capabilities", True),
            ("Outputs", outputs),
        )
        if present
    )
    edges = [line for line in lines if "-->" in line or "---" in line or "~~~" in line]
    if edges != [chain]:
        failures.append(
            Failure("COMPOSING", f"At a Glance is the one chain {chain!r}; found {edges}")
        )
    if starting and not has_inputs:
        failures.append(
            Failure("PLANNING", "At a Glance shows Starting Points without a verified input format")
        )
    if any(_GLANCE_DIRECTIVE.match(line) for line in lines):
        failures.append(Failure("COMPOSING", "At a Glance carries a styling directive"))
    count = len(_CAPABILITY_NODE.findall(body))
    columns = {name: _column_size(lines, name) for name in ("capl", "capr")}
    present = [name for name, size in columns.items() if size is not None]
    if count > 8:
        failures.append(Failure("PLANNING", f"At a Glance shows {count} capabilities; at most 8"))
    elif count < 3:
        failures.append(Failure("PLANNING", f"At a Glance shows {count} capabilities; at least 3"))
    elif count <= 5 and present:
        failures.append(
            Failure("COMPOSING", f"At a Glance: {count} capabilities form one column, not two")
        )
    elif count >= 6 and len(present) != 2:
        failures.append(
            Failure(
                "COMPOSING",
                f"At a Glance: {count} capabilities form two balanced columns; "
                f"found {len(present)} column(s)",
            )
        )
    elif count >= 6 and abs((columns["capl"] or 0) - (columns["capr"] or 0)) > 1:
        failures.append(
            Failure(
                "COMPOSING",
                f"At a Glance: {count} capabilities form two balanced columns; "
                f"found {columns['capl']} and {columns['capr']}",
            )
        )
    for label in _GLANCE_LABEL.findall(body):
        for token in label.split():
            if len(token) > 28:
                failures.append(
                    Failure("COMPOSING", f"At a Glance label token over 28 characters: {token!r}")
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
    # README_CONTRACT.md row 3: the banner is one linked image from the verified illustration
    # and homepage facts, immediately below the badge row; it is not a second badge row.
    banner = ""
    pair = banner_target(candidate.facts.facts)
    if pair is not None:
        banner = f"[![{name}]({pair[0].value})]({pair[1].value})"
    badge_rows = [
        line for line in outside if _BADGE_ROW.fullmatch(line.strip()) and line.strip() != banner
    ]
    if len(badge_rows) != 1:
        failures.append(Failure("COMPOSING", f"expected one badge row; found {len(badge_rows)}"))
    # README_CONTRACT.md row 14: every verified public type exactly once, keyed by its canonical
    # defining location, and the Core API table lists those types and nothing else.
    types = [
        fact
        for fact in candidate.facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
        and (fact.attributes or {}).get("symbol_kind") in {"class", "enum"}
    ]
    locations = Counter((fact.attributes or {}).get("defined_at") or fact.value for fact in types)
    for location, count in sorted(locations.items()):
        if count > 1:
            failures.append(
                Failure(
                    "EXTRACTING",
                    f"verified public type {location} is recorded {count} times; one fact per "
                    "canonical defining location",
                )
            )
    rows = re.findall(
        r"^\| `([^`]+)` \|", _section_texts(candidate.readme).get("api_reference", ""), re.M
    )
    if rows and len(rows) != len(types):
        failures.append(
            Failure(
                "COMPOSING",
                f"the Core API table lists {len(rows)} rows for {len(types)} verified public types",
            )
        )
    headings = {section.heading for section in SEMANTIC_SHELL if section.heading}
    # Additional Examples holds every further example under its own real, unique, task-named
    # level-three heading (README_CONTRACT.md section 2 row 12): never "Example N", never reused.
    tasks = [
        line[4:].strip()
        for line in _section_texts(candidate.readme).get("additional_examples", "").splitlines()
        if line.startswith("### ")
    ]
    for task, count in Counter(tasks).items():
        if count > 1:
            failures.append(Failure("COMPOSING", f"example heading {task!r} is reused"))
        if _EXAMPLE_N.fullmatch(task):
            failures.append(Failure("COMPOSING", f"example heading {task!r} names no task"))
    # The Detailed Member Reference groups members under the hub types' own names (row 14).
    topics = {
        fact.value.rsplit(".", 1)[-1]
        for fact in candidate.facts.by_kind("public_symbol")
        if fact.polarity == "SUPPORTED"
    }
    api_lines = set(_section_texts(candidate.readme).get("api_reference", "").splitlines())
    for line in outside:
        if line.startswith("#") and not line.startswith("# "):
            level = len(line) - len(line.lstrip("#"))
            text = line.lstrip("#").strip()
            if level == 3 and text in tasks:
                continue
            if level == 3 and line in api_lines and text in topics:
                continue
            if (level, text in headings, text in SUBSECTION_HEADINGS) not in _HEADING_OK:
                failures.append(
                    Failure("COMPOSING", f"heading {line!r} is not a shell heading in title case")
                )
    prose = _prose(outside)
    lower_forms = canonical_abbreviations(candidate.facts)
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
    glance_text = _section_texts(candidate.readme).get("at_a_glance", "")
    if glance_text.strip() and _GLANCE_FENCE.sub("", glance_text, count=1).strip():
        # README_CONTRACT.md row 6: exactly one Mermaid fence and nothing else.
        failures.append(
            Failure("COMPOSING", "At a Glance holds exactly one Mermaid fence and nothing else")
        )
    has_inputs = any(
        fact.id.startswith("format:input.") and fact.polarity == "SUPPORTED"
        for fact in candidate.facts.by_kind("format")
    )
    for body in graphs:
        failures.extend(_topology_failures(body, has_inputs))
    lowered = prose.lower()
    for phrase in _NARRATION:
        if phrase in lowered:
            failures.append(Failure("COMPOSING", f"internal narration {phrase!r}"))
    visible, total = line_counts(candidate.readme)
    policy = candidate.policy
    # Check 7 judges the visible-length budget; collapsed content is unbounded (contract row 14).
    if visible > policy.visible_lines_budget:
        failures.append(
            Failure(
                "PLANNING",
                f"{visible} visible lines of {total} exceed the visible budget "
                f"{policy.visible_lines_budget}",
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


def coverage_ledger(candidate: Candidate) -> list[dict[str, Any]]:
    """Every shell row with the fact kinds it rests on and how far they resolved.

    RC6: a coverage defect used to dead-end as a presentation advisory, because nothing recorded
    what a row needed against what the evidence gave it. Each entry says whether the row is
    required, whether the plan included it, and for every kind the row rests on: how many facts of
    that kind are SUPPORTED, how many were extracted, and - when some are not - the reason the
    evidence itself gives, never one invented here.
    """
    by_kind: dict[str, list[Fact]] = {}
    for fact in candidate.facts.facts:
        by_kind.setdefault(fact.kind, []).append(fact)
    included = {
        str(entry.get("section_id"))
        for entry in candidate.plan.get("sections", [])
        if entry.get("include")
    }
    ledger: list[dict[str, Any]] = []
    for section in SEMANTIC_SHELL:
        kinds: list[dict[str, Any]] = []
        for kind in ROW_FACT_KINDS.get(section.id, ()):
            facts = by_kind.get(kind, [])
            supported = [fact for fact in facts if fact.polarity == "SUPPORTED"]
            unresolved = [fact for fact in facts if fact.polarity != "SUPPORTED"]
            record: dict[str, Any] = {
                "kind": kind,
                "supported": len(supported),
                "extracted": len(facts),
            }
            if unresolved:
                record["reasons"] = sorted(
                    {
                        f"{fact.polarity}: {_evidence_detail(fact)}"
                        for fact in unresolved[:_LEDGER_REASONS]
                    }
                )
            kinds.append(record)
        ledger.append(
            {
                "section_id": section.id,
                "required": section.required,
                "included": section.id in included,
                "kinds": kinds,
            }
        )
    return ledger


def _evidence_detail(fact: Fact) -> str:
    """The reason the evidence gives for a fact that did not resolve, as the extractor wrote it."""
    detail = fact.evidence[-1].detail if fact.evidence else None
    return str(detail or "no reason recorded")


# A row's reasons are a sample, not an inventory: enough to see why a kind did not resolve
# without the ledger growing with the corpus.
_LEDGER_REASONS = 3


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
            # The same failures as records, so a reader of validation.json routes by field and
            # never by parsing detail prose (section 27.5 D5). details stays the human-readable
            # list the repair packet and the reports show.
            record["failures"] = [
                {
                    "section_id": failure.section,
                    "causal_stage": failure.stage,
                    "detail": failure.detail,
                }
                for failure in failures
            ]
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
        "coverage": coverage_ledger(candidate),
        "advisory": advisory_notes(candidate),
        "summary": {
            "pass": verdicts.get("PASS", 0),
            "fail": verdicts.get("FAIL", 0),
            "pending": verdicts.get("PENDING", 0),
        },
    }


def deferred_on_required_rows(review: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Advisory findings against a section the contract marks Required.

    An advisory is deferred repair work, not accepted work (project/loop-prompt.md section 6
    rule 5), so a required row carries none before READY_FOR_PROPOSAL (docs/README_CONTRACT.md
    section 6, docs/RESEARCH_AND_GUIDELINES.md section 27.5 D5). The advisories that reach this
    point are the ones a deterministic check contradicted; that a required row keeps attracting
    them is itself the signal, and it is reported rather than shipped.
    """
    return [
        dict(finding)
        for finding in review.get("advisory", [])
        if str(finding.get("section_id", "")) in REQUIRED_SECTIONS
    ]


def record_review_verdict(document: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """validation.json with check 10 judged from review.json: PASS on ACCEPT under a separate
    reviewer identity and no advisory left on a required row; otherwise FAIL, routed to the
    earliest causal state the findings name."""
    findings = list(review.get("findings", []))
    deferred = deferred_on_required_rows(review)
    states = [f.get("causal_state") for f in findings if f.get("causal_state") in STAGE_ORDER]
    accepted = (
        review.get("verdict") == "ACCEPT" and bool(review.get("identity_separate")) and not deferred
    )
    if accepted:
        verdict, stage, details = "PASS", None, []
        deferred = []
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
        details.extend(
            f"{f.get('id')} {f.get('section_id')}: a required row admits no advisory "
            f"({f.get('reviewer_scope_defect') or 'recorded advisory'})"
            for f in deferred
        )
    # A deferred advisory names the row it sits on; the rest of check 10's details are about the
    # review as a whole, so they name no section (section 27.5 D5: routing reads fields).
    sections = [None] * (len(details) - len(deferred)) + [
        str(f.get("section_id")) for f in deferred
    ]
    checks = [
        {
            **check,
            "verdict": verdict,
            "causal_stage": stage,
            "details": details,
            # The verdict as a field: whether a review failure invalidates an accepted candidate
            # is decided by this, never by reading details[0] (section 27.2 RC8).
            "review_verdict": str(review.get("verdict", "")),
            "failures": [
                {"section_id": section, "causal_stage": stage, "detail": detail}
                for section, detail in zip(sections, details, strict=True)
            ],
        }
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
