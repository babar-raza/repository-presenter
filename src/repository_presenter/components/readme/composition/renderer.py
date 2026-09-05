"""Stage S7: the deterministic renderer - the Markdown document from shell, plan, units, facts.

The LLM never writes Markdown. This module owns every heading, badge, navigation link, command,
code block, details block, diagram, link, and license statement, emits the plan's included
sections in shell order, drops each authored unit into its slot with fact-value identifiers
wrapped in code spans, and places every inherited unit the reconciliation preserved or moved.
The result is a pure function of its inputs, so a rerun on the same inputs is byte-identical.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from repository_presenter.components.readme.composition.authoring import (
    allowed_identifiers,
    canonical_abbreviations,
    identifier_allowed,
    identifier_tokens,
    surface_members,
    verified_members,
)
from repository_presenter.components.readme.composition.components.ecosystems import (
    REGISTRY_NAMES,
    host_names,
    registry_name,
)
from repository_presenter.components.readme.composition.components.identity import (
    product_name,
    product_name_tokens,
)
from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    Section,
)
from repository_presenter.components.readme.composition.placement import (
    placed_texts,
    placements,
    renders_verbatim,
)
from repository_presenter.components.readme.evidence.facts.links import link_text
from repository_presenter.components.readme.evidence.facts.product_pages import (
    banner_target,
    enterprise_target,
)
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry

RENDERER_VERSION = "17"  # the template component version dependencies.json records
ADDITIONAL_EXAMPLES_SUMMARY = "View Additional Examples"
API_SURFACE_SUMMARY = "View the Complete Public API Surface"
README_FILENAME = "README.md"
PATCH_FILENAME = "README.patch"
__all__ = ["renders_verbatim"]  # re-exported for the validator and the tests
_LOWER_WORD = re.compile(r"(?<![.\w])[a-z]{3,}\b")
_WORD = re.compile(r"\b[A-Z][A-Za-z0-9]*\b")
_EXTENSION = re.compile(r"(?<![\w`.])\.[a-z0-9]{2,}\b")
_SLUG_STRIP = re.compile(r"[^\w\- ]")
# README_CONTRACT.md section 2 row 20: the declaration, then for a permissive license one
# sentence of practical permissions and the notice condition, and the absence of warranty.
_MIT_PROSE = (
    "This project is licensed under the [MIT License]({file}). The MIT License permits use, "
    "copying, modification, distribution, sublicensing, and commercial use, provided its "
    "copyright and permission notice are retained. The software is provided without warranty."
)
_GENERIC_PROSE = "This project is licensed under the [{spdx}]({file})."
_IMPORT = r"(?m)^\s*(?:import|from)\s+{module}\b"
_EXTRA = re.compile(r"extra '([^']+)'")
_FLOOR = re.compile(r">=\s*(\d+(?:\.\d+)*)")
_FILE_COUNT = re.compile(r"(\d+) files")


class RenderContext:
    """Everything the renderer reads, indexed once."""

    def __init__(
        self,
        entry: RegistryEntry,
        facts: FactsDocument,
        plan: dict[str, Any],
        units: dict[str, Any],
        dispositions: dict[str, Any],
    ) -> None:
        self.entry = entry
        self.facts = facts
        self.plan = plan
        self.name = product_name(entry)
        self.by_id: dict[str, Fact] = {fact.id: fact for fact in facts.facts}
        self.included: list[Section] = [
            section
            for section in SEMANTIC_SHELL
            if any(
                item.get("section_id") == section.id and item.get("include")
                for item in plan.get("sections", [])
            )
        ]
        self.units: dict[tuple[str, str], str] = {
            (unit["section"], unit["slot"]): unit["text"] for unit in units.get("units", [])
        }
        # Placement follows the three rules of README_CONTRACT.md section 3, decided once in
        # placement.py so the validator judges exactly what the renderer did.
        self.placements = placements(plan, dispositions, facts, entry.ecosystem)
        self.placed: dict[str, list[str]] = placed_texts(self.placements)
        self.allowed = allowed_identifiers(facts, self.name)
        self.members = verified_members(facts)
        self.methods = surface_members(facts)
        self.name_tokens = product_name_tokens(self.name)
        self.hosts = host_names(fact.value for fact in facts.facts if fact.polarity == "SUPPORTED")
        self.abbreviations = canonical_abbreviations(facts)
        self.symbol_names: frozenset[str] = frozenset(
            fact.value.rsplit(".", 1)[-1]
            for fact in facts.by_kind("public_symbol")
            if fact.polarity == "SUPPORTED"
            and fact.evidence
            and any(
                f"; {kind};" in (fact.evidence[0].detail or "")
                for kind in ("class", "enum", "function")
            )
        )

    def canonical(self, text: str) -> str:
        """``text`` with every known abbreviation raised to the spelling the document uses."""
        return _LOWER_WORD.sub(
            lambda match: self.abbreviations.get(match.group(0), match.group(0)), text
        )

    def fact(self, fact_id: str) -> Fact | None:
        return self.by_id.get(fact_id)

    def supported(self, kind: str) -> list[Fact]:
        return [f for f in self.facts.by_kind(kind) if f.polarity == "SUPPORTED"]  # type: ignore[arg-type]

    def unit(self, section: str, slot: str) -> str:
        return self.prose(self.units.get((section, slot), ""))

    def prose(self, text: str) -> str:
        """Authored text with every fact-value identifier wrapped in a code span.

        Besides the tokens the guard checks, a capitalized word that names a recorded class or
        function (``Scene``) is wrapped too; the guard leaves such words alone because ordinary
        prose capitalizes words, but here the match is exact against the surface. A known
        abbreviation written in lower case is raised to its canonical form first: the code owns
        that spelling, so it normalises it rather than re-asking the model and rejecting the
        reply (docs/RESEARCH_AND_GUIDELINES.md section 27.10; BC-07 still judges the result).
        """
        text = self.canonical(text)
        tokens = set(identifier_tokens(text))
        tokens.update(word for word in _WORD.findall(text) if word in self.symbol_names)
        # A bare extension that is a format fact value (``.stl``) is an identifier too.
        tokens.update(ext for ext in _EXTENSION.findall(text) if ext in self.allowed)
        rendered = text
        for token in sorted(tokens, key=len, reverse=True):
            if token in self.name_tokens or token in REGISTRY_NAMES.values() or token in self.hosts:
                continue  # the product's name, package registries and hosting sites are nouns
            if token not in self.symbol_names and not identifier_allowed(
                token, self.allowed, self.members, self.methods
            ):
                continue
            rendered = re.sub(rf"(?<![`\w.]){re.escape(token)}(?![`\w])", f"`{token}`", rendered)
        return rendered


def anchor(heading: str) -> str:
    """GitHub's anchor form of a heading."""
    return _SLUG_STRIP.sub("", heading.strip().lower()).replace(" ", "-")


def _badges(context: RenderContext) -> list[str]:
    repo = context.entry.repository
    badges: list[str] = []
    install = context.fact("install_command:pip")
    package = context.fact("package:name")
    if install is not None and install.polarity == "SUPPORTED" and package is not None:
        badges.append(
            f"[![PyPI](https://img.shields.io/pypi/v/{package.value}.svg)]"
            f"(https://pypi.org/project/{package.value}/)"
        )
    requires = context.fact("package:python_requires")
    if requires is not None and requires.polarity == "SUPPORTED":
        label = quote(requires.value.replace(">=", "").strip() + "+", safe="")
        badges.append(f"![Python](https://img.shields.io/badge/python-{label}-blue.svg)")
    spdx = context.fact("license:spdx")
    license_file = context.fact("license:file")
    if spdx is not None and license_file is not None and spdx.polarity == "SUPPORTED":
        badge = quote(spdx.value, safe="")
        badges.append(
            f"[![License: {spdx.value}](https://img.shields.io/badge/License-{badge}-blue.svg)]"
            f"({license_file.value})"
        )
    badges.append(
        f"[![Contributors](https://img.shields.io/github/contributors/{repo})]"
        f"(https://github.com/{repo}/graphs/contributors)"
    )
    return badges


def _navigation(context: RenderContext) -> list[str]:
    return [
        f"- [{section.heading}](#{anchor(section.heading)})"
        for section in context.included
        if section.heading is not None and section.id != "navigation"
    ]


def _extra_bullet(fact: Fact) -> str:
    match = _EXTRA.search(fact.evidence[0].detail or "") if fact.evidence else None
    suffix = f" (extra `{match.group(1)}`)" if match else ""
    return f"- `{fact.value}`{suffix}"


def _dependencies(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2 row 9: the dependency snapshot in four subsections.

    Required renders its requirements, or the fixed verified-zero sentence with the manifest
    clause the extractor recorded, so a reader never mistakes zero for a forgotten section.
    Optional, Native and System, and Development omit silently when their bucket is empty.
    """
    facts = context.supported("dependency")
    marker = context.fact("dependency:none")
    required = [
        fact
        for fact in facts
        if fact.id != "dependency:none"
        and not fact.id.startswith(("dependency:optional.", "dependency:development."))
    ]
    optional = [fact for fact in facts if fact.id.startswith("dependency:optional.")]
    development = [fact for fact in facts if fact.id.startswith("dependency:development.")]
    lines: list[str] = []
    if required:
        lines.extend(["### Required Package Dependencies", ""])
        lines.extend(f"- `{fact.value}`" for fact in required)
    elif marker is not None and marker.polarity == "SUPPORTED" and marker.evidence:
        clause = marker.evidence[0].detail or "the manifest declares none"
        lines.extend(["### Required Package Dependencies", ""])
        lines.append(
            "No required third-party package dependencies; in "
            f"`{marker.evidence[0].path}`, {clause}."
        )
    if optional:
        lines.extend(["", "### Optional Dependencies", ""])
        lines.extend(_extra_bullet(fact) for fact in optional)
    requires = context.fact("package:python_requires")
    if requires is not None and requires.polarity == "SUPPORTED" and requires.evidence:
        lines.extend(["", "### Native and System Requirements", ""])
        floor = _FLOOR.fullmatch(requires.value.strip())
        path = requires.evidence[0].path
        if floor:
            lines.append(
                f"- Requires Python {floor.group(1)} or later "
                f'(`python_requires="{requires.value}"` in `{path}`).'
            )
        else:
            lines.append(f"- Requires Python `{requires.value}` (`python_requires` in `{path}`).")
    if development:
        lines.extend(["", "### Development Dependencies", ""])
        lines.extend(_extra_bullet(fact) for fact in development)
    return lines[1:] if lines and lines[0] == "" else lines


def _public_type_count(context: RenderContext) -> int:
    return sum(
        1
        for fact in context.supported("public_symbol")
        if fact.evidence
        and any(f"; {kind};" in (fact.evidence[0].detail or "") for kind in ("class", "enum"))
    )


def _documentation_resources(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2 row 15: one list, each item a bold link, an em dash, and
    the authored sentence; the reference item states the verified public type count and points
    to the in-page API Reference; the issues line closes it; never the same target twice."""
    sid = "documentation_resources"
    repository = context.fact("identity:repository")
    issues = f"https://github.com/{repository.value}/issues" if repository is not None else None
    api_included = any(section.id == "api_reference" for section in context.included)
    lines: list[str] = []
    seen: set[str] = set()
    for link in context.plan.get("links", []):
        if link.get("section_id") != sid:
            continue
        target = context.fact(link.get("link_fact_id", ""))
        if target is None or target.value in seen or target.value == issues:
            continue
        seen.add(target.value)
        sentence = context.unit(sid, f"link:{target.id}")
        host = (urlsplit(target.value).hostname or "").lower()
        if host.startswith("reference.") and api_included:
            count = _public_type_count(context)
            sentence += (
                f" It covers all {count} verified public types; the "
                "[API Reference](#api-reference) section above covers the essentials."
            )
        lines.append(f"- **[{link_text(target)}]({target.value})** — {sentence}")
    if issues is not None:
        lines.append(f"- Found a bug or have a feature request? [Open an issue]({issues}).")
    return lines


def _development_sentences(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2 row 17: the suite-size sentence when a test-file count is
    verified, and the release sentence linking the publish workflow file when one exists;
    representative assets are named in prose, never listed as bare directories."""
    sentences: list[str] = []
    tests = context.fact("build_test_asset:tests")
    if tests is not None and tests.polarity == "SUPPORTED":
        counts = [
            m.group(1)
            for evidence in tests.evidence
            if (m := _FILE_COUNT.match(evidence.detail or "")) is not None
        ]
        if counts:
            sentences.append(f"The suite covers {counts[-1]} test files under `{tests.value}`.")
    ci = context.fact("build_test_asset:ci")
    if ci is not None and ci.polarity == "SUPPORTED":
        prefix = ci.value if ci.value.endswith("/") else ci.value + "/"
        workflows = [e.path for e in ci.evidence if e.path.startswith(prefix) and e.path != prefix]
        release = [w for w in workflows if any(k in w.lower() for k in ("publish", "release"))]
        chosen = release[0] if release else workflows[0] if workflows else None
        if chosen is not None:
            stem = chosen.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            sentences.append(f"Releases run through the [{stem} workflow]({chosen}).")
    return sentences


def renderer_sentences(
    entry: RegistryEntry,
    facts: FactsDocument,
    plan: dict[str, Any],
    units: dict[str, Any],
    dispositions: dict[str, Any],
) -> tuple[str, ...]:
    """Every sentence the renderer writes into a section an LLM otherwise owns.

    A count computed from the facts, the suite size, the release line: the unit beside them did
    not write them and no revision of it can change them, so a finding against one is out of the
    reviewer's scope exactly as one against a deterministic section is
    (docs/README_CONTRACT.md section 6, section 3). Measured on the canary 2026-09-05: the
    reviewer twice preferred the original README's stale counts - 305 public types, 33 test
    files - over the 337 and 34 the renderer computed from facts, and the repair loop could
    only spend an attempt on prose it does not own.
    """
    context = RenderContext(entry, facts, plan, units, dispositions)
    sentences = list(_development_sentences(context))
    if any(section.id == "api_reference" for section in context.included):
        count = _public_type_count(context)
        sentences.append(
            f"It covers all {count} verified public types; the "
            "[API Reference](#api-reference) section above covers the essentials."
        )
    return tuple(sentences)


def _symbol_description(context: RenderContext, fact: Fact) -> str:
    """The docstring first line when the source has one, else the sentence authored from the
    signature in a bounded batch, else the verified signature; never an invented sentence.
    Table-safe: no pipes; a bare signature is rendered as one code span."""
    attributes = fact.attributes or {}
    text = attributes.get("docstring") or ""
    if not text:
        text = context.units.get(("api_reference", f"type:{fact.id}"), "")
    if not text and attributes.get("signature"):
        # A signature is code, not prose: in a code span its parameter names (obj, prop) are
        # never judged as abbreviations or claims by the prose checks.
        signature = attributes["signature"].replace("|", "/").replace("`", "")
        return f"Defined as `{signature}`."
    if not text:
        text = f"Public {attributes.get('symbol_kind', 'symbol')}."
    return text.replace("|", "/").replace("`", "")


def _table_names(values: list[str]) -> dict[str, str]:
    """The name each type takes in the table: its final segment, or the shortest dotted suffix
    that tells it apart when two verified types share that segment (README_CONTRACT.md row 14
    lists the complete verified surface, so both stay, under names a visitor can import)."""
    names: dict[str, str] = {}
    for value in values:
        segments = value.split(".")
        for depth in range(1, len(segments) + 1):
            suffix = ".".join(segments[-depth:])
            rivals = [
                other
                for other in values
                if other != value and ".".join(other.split(".")[-depth:]) == suffix
            ]
            if not rivals:
                break
        names[value] = suffix
    return names


def _api_reference(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2 row 14: a visible intro with the verified public type
    count, then one details block holding the Core API table over every verified public type,
    split by kind, and the Detailed Member Reference grouped by the plan's hub types."""
    sid = "api_reference"
    symbols = context.supported("public_symbol")
    by_kind: dict[str, list[Fact]] = {}
    for fact in symbols:
        by_kind.setdefault((fact.attributes or {}).get("symbol_kind", ""), []).append(fact)
    classes = sorted(by_kind.get("class", []), key=lambda f: f.value)
    enums = sorted(by_kind.get("enum", []), key=lambda f: f.value)
    count = len(classes) + len(enums)
    names = _table_names([f.value for f in (*classes, *enums)])
    lines = [context.unit(sid, "intro"), "", f"The verified public surface has {count} types."]
    lines += ["", "<details>", f"<summary>{API_SURFACE_SUMMARY}</summary>", ""]
    lines += ["### Core API", "", "| Class | Description |", "| --- | --- |"]
    lines += [f"| `{names[f.value]}` | {_symbol_description(context, f)} |" for f in classes]
    if enums:
        lines += ["", "#### Enumerations", "", "| Enumeration | Description |", "| --- | --- |"]
        lines += [f"| `{names[f.value]}` | {_symbol_description(context, f)} |" for f in enums]
    members: dict[str, list[Fact]] = {}
    for fact in by_kind.get("method", []):
        members.setdefault(fact.value.rsplit(".", 1)[0], []).append(fact)
    hubs: list[tuple[dict[str, Any], Fact]] = []
    for hub in context.plan.get("api_hubs", []):
        symbol = context.fact(hub.get("symbol_fact_id", ""))
        if symbol is not None:
            hubs.append((hub, symbol))
    if hubs:
        lines += ["", "#### Detailed Member Reference"]
        for hub, symbol in hubs:
            lines += ["", f"### {names.get(symbol.value, symbol.value.rsplit('.', 1)[-1])}", ""]
            lines.append(context.unit(sid, f"hub:{hub['symbol_fact_id']}"))
            owned = sorted(members.get(symbol.value, []), key=lambda f: f.value)
            if owned:
                lines.append("")
                lines += [
                    f"- `{f.value.rsplit('.', 1)[-1]}`: {_symbol_description(context, f)}"
                    for f in owned
                ]
    lines += ["", "</details>"]
    return lines


def _enterprise_paragraph(context: RenderContext) -> str:
    """README_CONTRACT.md section 2 row 18: the closing paragraph of Scope and Limitations,
    from the live verified Enterprise target; a family-level target names no platform, and
    Enterprise Edition appears exactly once, here."""
    if not any(section.id == "enterprise_relationship" for section in context.included):
        return ""
    target = enterprise_target(context.facts.facts)
    if target is None:
        return ""
    level = (target.attributes or {}).get("level", "platform")
    name = context.name.replace(" FOSS", "")
    if level == "family":
        name = name.split(" for ", 1)[0]
    sentence = (
        f"These limitations don't apply to [{name} \u2014 Enterprise Edition]({target.value})."
    )
    adds = context.unit("enterprise_relationship", "context").strip()
    return f"{sentence} {adds}" if adds else sentence


def _oxford(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _installation(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2 row 8, every command verified at this revision.

    The registry install renders only when the manifest and the package registry agree it is
    published; an unpublished or unchecked package is stated plainly instead. The source install
    is the form the examples stage itself ran (a clone installed with pip) and appears only when
    that install produced an executed example; the verify command imports a module an executed
    example imported; the runtime sentence restates the manifest's own declarations.
    """
    lines: list[str] = []
    install = context.fact("install_command:pip")
    package = context.fact("package:name")
    version = context.fact("package:version")
    if install is not None and install.polarity == "SUPPORTED" and package is not None:
        registry = registry_name(context.entry.ecosystem)
        lead = f"Install the published package from {registry} (`{package.value}`"
        lead += f", version {version.value}):" if version is not None else "):"
        lines.append(lead)
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif install is not None and package is not None:
        detail = install.evidence[-1].detail or "the registry could not be checked"
        registry = registry_name(context.entry.ecosystem)
        state = (
            f"is not yet published on {registry}"
            if install.polarity == "CONTRADICTED"
            else f"could not be confirmed on {registry} at this revision"
        )
        lines.append(f"The package `{package.value}` {state} ({detail}).")
    executed = context.supported("example")
    repository = context.fact("identity:repository")
    if executed and repository is not None:
        name = repository.value.split("/")[-1]
        lines.append("")
        lines.append("To work from a source checkout instead, install the clone with pip:")
        lines.append("")
        lines.extend(
            _code_block(
                "bash",
                f"git clone https://github.com/{repository.value}.git\ncd {name}\npip install .",
            )
        )
    imported = [
        fact.value
        for fact in context.supported("import_path")
        if any(re.search(_IMPORT.format(module=re.escape(fact.value)), e.value) for e in executed)
    ]
    if imported:
        module = max(imported, key=len)
        lines.append("")
        lines.append("Verify the install:")
        lines.append("")
        lines.extend(_code_block("bash", f'python -c "import {module}"'))
    versions = context.fact("package:python_versions")
    requires = context.fact("package:python_requires")
    sentence = ""
    if versions is not None and versions.polarity == "SUPPORTED":
        listed = _oxford([v.strip() for v in versions.value.split(",") if v.strip()])
        sentence = f"The package supports Python {listed}"
        if requires is not None and requires.polarity == "SUPPORTED":
            sentence += f" and declares `python_requires` as `{requires.value}`"
        sentence += "."
    elif requires is not None and requires.polarity == "SUPPORTED":
        sentence = f"The package declares `python_requires` as `{requires.value}`."
    if sentence:
        lines.append("")
        lines.append(sentence)
    return lines[1:] if lines and lines[0] == "" else lines


def _code_block(language: str, code: str) -> list[str]:
    return [f"```{language}", code.rstrip("\n"), "```"]


# Display names for format extensions whose canonical form is not the bare upper case.
FORMAT_NAMES: dict[str, str] = {
    "gltf": "glTF",
    "dae": "COLLADA",
    "wrl": "VRML",
    "drc": "Draco",
    "x": "DirectX X",
}


def format_name(value: str) -> str:
    """The canonical display name of a format fact value such as ``.gltf``."""
    extension = value.lstrip(".").lower()
    return FORMAT_NAMES.get(extension, extension.upper())


def _or_list(items: list[str]) -> str:
    if len(items) <= 2:
        return " or ".join(items)
    return ", ".join(items[:-1]) + f", or {items[-1]}"


def _label(text: str) -> str:
    return text.replace(chr(34), "'")


def _at_a_glance(context: RenderContext) -> list[str]:
    """README_CONTRACT.md section 2.1: one chain, StartingPoints --> PRODUCT --> Capabilities
    --> Outputs, each group a single listing node; Starting Points and Outputs are omitted with
    their hop when nothing is verified; up to five capabilities form one column, six to eight
    two balanced columns; the renderer owns every node, edge, and label."""
    glance = context.plan.get("at_a_glance") or {}
    inputs = [
        format_name(fact.value)
        for fact in (context.fact(i) for i in glance.get("input_format_ids", []))
        if fact is not None
    ]
    outputs = [
        format_name(fact.value)
        for fact in (context.fact(i) for i in glance.get("output_format_ids", []))
        if fact is not None
    ]
    titles = [_label(title) for title in glance.get("capability_titles", [])]
    lines = ["```mermaid", "flowchart TD"]
    chain: list[str] = []
    if inputs:
        lines.append('  subgraph StartingPoints["Starting Points"]')
        lines.append("    direction LR")
        lines.append(f'    i1["An existing {_or_list(inputs)} file"]')
        lines.append("  end")
        chain.append("StartingPoints")
    lines.append(f'  PRODUCT["{_label(context.name)}"]')
    chain.append("PRODUCT")
    lines.append('  subgraph Capabilities["Core Capabilities"]')
    if len(titles) >= 6:
        lines.append("    direction LR")
        left = (len(titles) + 1) // 2
        for name, first, column in (("capl", 1, titles[:left]), ("capr", left + 1, titles[left:])):
            lines.append(f'    subgraph {name}[" "]')
            lines.append("      direction TB")
            for offset, title in enumerate(column):
                lines.append(f'      c{first + offset}["{title}"]')
            lines.append("    end")
    else:
        lines.append("    direction TB")
        for index, title in enumerate(titles, start=1):
            lines.append(f'    c{index}["{title}"]')
    lines.append("  end")
    chain.append("Capabilities")
    if outputs:
        lines.append('  subgraph Outputs["Outputs"]')
        lines.append("    direction TB")
        lines.append(f'    o1["{_or_list(outputs)} file"]')
        lines.append("  end")
        chain.append("Outputs")
    lines.append("  " + " --> ".join(chain))
    lines.append("```")
    return lines


def _example_entry(context: RenderContext, sid: str, example_id: str) -> list[str]:
    """One further example: its authored task heading, then the verified code verbatim."""
    example = context.fact(example_id)
    assert example is not None
    task = context.unit(sid, f"workflow:{example_id}").strip().rstrip(".")
    return ["", f"### {task}", "", *_code_block(context.entry.ecosystem, example.value)]


def _section_body(context: RenderContext, section: Section) -> list[str]:
    sid = section.id
    plan = context.plan
    lines: list[str] = []
    if sid == "identity":
        lines.append(f"# {context.name}")
    elif sid == "badges":
        lines.append(" ".join(_badges(context)))
    elif sid == "banner":
        # README_CONTRACT.md row 3: both URLs come from verified facts and the alt text names
        # the product; when either fact is unresolved the row is omitted entirely.
        pair = banner_target(context.facts.facts)
        if pair is not None:
            image, homepage = pair
            lines.append(f"[![{context.name}]({image.value})]({homepage.value})")
    elif sid == "opening":
        lines.append(context.unit(sid, "opening"))
    elif sid == "navigation":
        lines.extend(_navigation(context))
    elif sid == "at_a_glance":
        lines.extend(_at_a_glance(context))
    elif sid == "key_capabilities":
        for index, item in enumerate(plan.get("core_capabilities", []), start=1):
            lines.append(f"- **{item['title']}.** {context.unit(sid, f'capability:{index}')}")
    elif sid == "installation":
        lines.extend(_installation(context))
    elif sid == "dependencies":
        lines.extend(_dependencies(context))
    elif sid == "quick_start":
        # README_CONTRACT.md section 2 row 10: one or two minimal examples, each introduced by
        # one lead-in sentence.
        lines.append(context.unit(sid, "lead_in"))
        example = context.fact(plan.get("quick_start_example_id", ""))
        if example is not None:
            lines.append("")
            lines.extend(_code_block(context.entry.ecosystem, example.value))
        second = context.fact(plan.get("second_quick_start_example_id") or "")
        if second is not None:
            lines.append("")
            lines.append(context.unit(sid, "lead_in:2"))
            lines.append("")
            lines.extend(_code_block(context.entry.ecosystem, second.value))
    elif sid == "additional_examples":
        # README_CONTRACT.md section 2 row 12: one lead-in; one flagship example visible under
        # its own task-named heading when the plan selects one; then a single details block
        # holding every further verified example under its own task-named heading.
        lines.append(context.unit(sid, "preview"))
        additional = [
            example_id
            for example_id in plan.get("additional_example_ids", [])
            if context.fact(example_id) is not None
        ]
        flagship = plan.get("flagship_example_id")
        if isinstance(flagship, str) and flagship in additional:
            lines.extend(_example_entry(context, sid, flagship))
            additional.remove(flagship)
        if additional:
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>{ADDITIONAL_EXAMPLES_SUMMARY}</summary>")
            for example_id in additional:
                lines.extend(_example_entry(context, sid, example_id))
            lines.append("")
            lines.append("</details>")
    elif sid == "api_reference":
        lines.extend(_api_reference(context))
    elif sid == "documentation_resources":
        lines.extend(_documentation_resources(context))
    elif sid == "scope_limitations":
        lines.append(context.unit(sid, "scope"))
        # Every authored limitation is its own bullet, in slot order (row 16).
        slots = sorted(
            (int(slot.split(":", 1)[1]), slot)
            for (section, slot) in context.units
            if section == sid and slot.startswith("limitation:") and slot[11:].isdigit()
        )
        if slots:
            lines.append("")
            lines.extend(f"- {context.unit(sid, slot)}" for _, slot in slots)
    elif sid == "development_testing":
        lines.append(context.unit(sid, "summary"))
        facts_sentences = _development_sentences(context)
        if facts_sentences:
            lines.append("")
            lines.append(" ".join(facts_sentences))
    elif sid == "enterprise_relationship":
        pass  # rendered as the closing paragraph of Scope and Limitations (row 18)
    elif sid == "third_party_notices":
        notices = context.supported("third_party_notices")
        for fact in notices:
            lines.append(f"See [Third-party notices]({fact.value}).")
    elif sid == "license":
        spdx = context.fact("license:spdx")
        license_file = context.fact("license:file")
        if spdx is not None and license_file is not None:
            template = _MIT_PROSE if spdx.value == "MIT" else _GENERIC_PROSE
            lines.append(
                template.format(name=context.name, spdx=spdx.value, file=license_file.value)
            )
    placed = context.placed.get(sid, [])
    if placed and section.visibility == "collapsible" and lines and lines[-1] == "</details>":
        # A placed unit inherits its section's visibility: inside the details block, after the
        # composed content, never appended outside it.
        closing = lines.pop()
        for verbatim in placed:
            lines.append("")
            lines.append(verbatim.rstrip("\n"))
        lines.append("")
        lines.append(closing)
    else:
        for verbatim in placed:
            lines.append("")
            lines.append(verbatim.rstrip("\n"))
    if sid == "scope_limitations":
        # Row 18: the Enterprise paragraph is the section's closing paragraph, after every
        # bullet and every placed unit, separated by a blank line and never inside a bullet.
        closing = _enterprise_paragraph(context)
        if closing:
            lines.append("")
            lines.append(closing)
    return [line for line in lines if line is not None]


def render_readme(
    entry: RegistryEntry,
    facts: FactsDocument,
    plan: dict[str, Any],
    units: dict[str, Any],
    dispositions: dict[str, Any],
) -> str:
    """The complete README as one string with LF endings and a single trailing newline."""
    context = RenderContext(entry, facts, plan, units, dispositions)
    blocks: list[str] = []
    for section in context.included:
        body = _section_body(context, section)
        if not any(line.strip() for line in body):
            continue
        heading = [f"## {section.heading}", ""] if section.heading else []
        blocks.append("\n".join(heading + body).rstrip("\n"))
    return "\n\n".join(blocks) + "\n"


def render_patch(original: str, rendered: str) -> str:
    """A unified diff from the existing README to the candidate, LF endings, empty when equal."""
    lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile="a/README.md",
        tofile="b/README.md",
    )
    text = "".join(line if line.endswith("\n") else line + "\n" for line in lines)
    return text


def line_counts(readme: str) -> tuple[int, int]:
    """(visible lines outside details blocks, total lines) for the length budget."""
    visible = 0
    total = 0
    depth = 0
    for line in readme.splitlines():
        total += 1
        stripped = line.strip()
        if stripped.startswith("<details"):
            depth += 1
            continue
        if stripped.startswith("</details"):
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            visible += 1
    return visible, total


def write_text(text: str, path: Path) -> str:
    data = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
