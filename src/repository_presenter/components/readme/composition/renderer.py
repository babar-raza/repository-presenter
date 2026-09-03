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
from urllib.parse import quote

from repository_presenter.components.readme.composition.authoring import (
    allowed_identifiers,
    identifier_allowed,
    identifier_tokens,
    surface_members,
    verified_members,
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
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry

RENDERER_VERSION = "3"  # the template component version dependencies.json records
ADDITIONAL_EXAMPLES_SUMMARY = "View Additional Examples"
README_FILENAME = "README.md"
PATCH_FILENAME = "README.patch"
__all__ = ["renders_verbatim"]  # re-exported for the validator and the tests
_LINK_TEXT = re.compile(r"text '(.*)'$")
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
        self.symbol_names: frozenset[str] = frozenset(
            fact.value.rsplit(".", 1)[-1]
            for fact in facts.by_kind("public_symbol")
            if fact.polarity == "SUPPORTED"
            and fact.evidence
            and any(
                f"; {kind};" in (fact.evidence[0].detail or "") for kind in ("class", "function")
            )
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
        prose capitalizes words, but here the match is exact against the surface.
        """
        tokens = set(identifier_tokens(text))
        tokens.update(word for word in _WORD.findall(text) if word in self.symbol_names)
        # A bare extension that is a format fact value (``.stl``) is an identifier too.
        tokens.update(ext for ext in _EXTENSION.findall(text) if ext in self.allowed)
        rendered = text
        for token in sorted(tokens, key=len, reverse=True):
            if token in self.name_tokens:
                continue
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
        lead = f"Install the published package from PyPI (`{package.value}`"
        lead += f", version {version.value}):" if version is not None else "):"
        lines.append(lead)
        lines.append("")
        lines.extend(_code_block("bash", install.value))
    elif install is not None and package is not None:
        detail = install.evidence[-1].detail or "the registry could not be checked"
        state = (
            "is not yet published on PyPI"
            if install.polarity == "CONTRADICTED"
            else "could not be confirmed on PyPI at this revision"
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


def _link_text(fact: Fact) -> str:
    for evidence in fact.evidence:
        match = _LINK_TEXT.search(evidence.detail or "")
        if match and match.group(1):
            return match.group(1)
    return fact.value


def _at_a_glance(context: RenderContext) -> list[str]:
    glance = context.plan.get("at_a_glance") or {}
    inputs = [context.fact(i) for i in glance.get("input_format_ids", [])]
    outputs = [context.fact(i) for i in glance.get("output_format_ids", [])]
    titles = list(glance.get("capability_titles", []))
    lines = ["```mermaid", "graph LR"]
    for index, fact in enumerate(f for f in inputs if f is not None):
        lines.append(f'  I{index + 1}["{fact.value.lstrip(".").upper()}"] --> P')
    lines.append(f'  P["{context.name}"]')
    lines.append("  P --- C")
    lines.append('  subgraph C["Core capabilities"]')
    for index, title in enumerate(titles):
        lines.append(f'    C{index + 1}["{title}"]')
    # Up to five capabilities form one column; six to eight form two balanced columns, the
    # rows held side by side by invisible links (README_CONTRACT.md section 2.1).
    if len(titles) >= 6:
        left = (len(titles) + 1) // 2
        for row in range(len(titles) - left):
            lines.append(f"    C{row + 1} ~~~ C{left + row + 1}")
    lines.append("  end")
    if any(f is not None for f in outputs):
        lines.append("  C --- O")
        lines.append('  subgraph O["Outputs"]')
        for index, fact in enumerate(f for f in outputs if f is not None):
            lines.append(f'    O{index + 1}["{fact.value.lstrip(".").upper()}"]')
        lines.append("  end")
    lines.append("```")
    return lines


def _section_body(context: RenderContext, section: Section) -> list[str]:
    sid = section.id
    plan = context.plan
    lines: list[str] = []
    if sid == "identity":
        lines.append(f"# {context.name}")
    elif sid == "badges":
        lines.append(" ".join(_badges(context)))
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
        lines.append(context.unit(sid, "lead_in"))
        example = context.fact(plan.get("quick_start_example_id", ""))
        if example is not None:
            lines.append("")
            lines.extend(_code_block(context.entry.ecosystem, example.value))
    elif sid == "additional_examples":
        # README_CONTRACT.md section 2 row 12: one lead-in, then a single details block
        # holding every further verified example under its own task-named heading.
        lines.append(context.unit(sid, "preview"))
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary>{ADDITIONAL_EXAMPLES_SUMMARY}</summary>")
        for example_id in plan.get("additional_example_ids", []):
            example = context.fact(example_id)
            if example is None:
                continue
            task = context.unit(sid, f"workflow:{example_id}").strip().rstrip(".")
            lines.append("")
            lines.append(f"### {task}")
            lines.append("")
            lines.extend(_code_block(context.entry.ecosystem, example.value))
        lines.append("")
        lines.append("</details>")
    elif sid == "api_reference":
        lines.append("<details>")
        lines.append("<summary>Hub APIs</summary>")
        lines.append("")
        for hub in plan.get("api_hubs", []):
            symbol = context.fact(hub.get("symbol_fact_id", ""))
            if symbol is None:
                continue
            slot = f"hub:{hub['symbol_fact_id']}"
            lines.append(f"- `{symbol.value}`: {context.unit(sid, slot)}")
        lines.append("")
        lines.append("</details>")
    elif sid == "documentation_resources":
        lines.append(context.unit(sid, "resources"))
        lines.append("")
        for link in plan.get("links", []):
            if link.get("section_id") != sid:
                continue
            target = context.fact(link.get("link_fact_id", ""))
            if target is not None:
                lines.append(f"- [{_link_text(target)}]({target.value})")
    elif sid == "scope_limitations":
        lines.append(context.unit(sid, "scope"))
        limitations = plan.get("material_limitations", [])
        if limitations:
            lines.append("")
            for index in range(1, len(limitations) + 1):
                lines.append(f"- {context.unit(sid, f'limitation:{index}')}")
    elif sid == "development_testing":
        lines.append(context.unit(sid, "summary"))
        assets = context.supported("build_test_asset")
        if assets:
            lines.append("")
            lines.extend(f"- `{fact.value}`" for fact in assets)
    elif sid == "enterprise_relationship":
        lines.append(context.unit(sid, "context"))
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
