"""Missing standard-template sections that verified facts alone can fill.

The template's Installation, Dependencies, Development and Testing, Third-party notices and License
sections are rendered by the existing deterministic renderer from facts (``render_readme`` with a
plan that includes just that section and no authored units). A section the live README already has
under any heading that means the same is never touched; a section that needs prose - Key
Capabilities, Scope and Limitations, At a Glance, Quick Start, API Reference, Documentation and
Resources - is reported as a finding, never invented (AGENTS.md: the model proposes, code verifies).

Insertion is purely additive: the block goes in front of the first existing H2 that the template
orders after it, else at the end, so every maintainer byte keeps its place.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from repository_presenter.components.readme.composition.components.shell import SEMANTIC_SHELL
from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.model import (
    MISSING_SECTION,
    Context,
    DetectorResult,
    Edit,
    Finding,
)
from repository_presenter.core.ecosystems import EcosystemSpec, spec_for
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

NL = chr(10)
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
#: A heading that means each template section, in template order. The table is the one place the
#: mapping lives: the "is it already there" test and the "where does it go" test both read it.
_MEANS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (sid, re.compile(pattern, re.IGNORECASE))
    for sid, pattern in (
        ("navigation", r"navigation|table of contents|contents"),
        ("at_a_glance", r"at a glance|overview"),
        ("key_capabilities", r"key capabilities|capabilities|features"),
        ("installation", r"install|set-?up|getting started"),
        ("dependencies", r"dependenc|requirement|prerequisite"),
        ("quick_start", r"quick ?start|usage"),
        ("additional_examples", r"examples?"),
        ("api_reference", r"\bapi\b|reference"),
        ("documentation_resources", r"documentation|resources|links"),
        ("scope_limitations", r"scope|limitations"),
        ("development_testing", r"develop|testing|\btests?\b|contribut|building|\bbuild\b"),
        ("third_party_notices", r"third[- ]party|notices?|attribution|acknowledg|credits"),
        ("license", r"licen[sc]e|copyright|legal"),
    )
)
_ORDER = {sid: index for index, (sid, _pattern) in enumerate(_MEANS)}
_SHELL = {section.id: section for section in SEMANTIC_SHELL}
#: The template sections no fact can fill without prose; reported when absent.
_NEEDS_PROSE = (
    "at_a_glance",
    "key_capabilities",
    "quick_start",
    "api_reference",
    "documentation_resources",
    "scope_limitations",
)


def _spec(ctx: Context) -> EcosystemSpec:
    """The ecosystem's presentation spec; ``plugin_for`` registers it before anything asks."""
    plugin_for(ctx.entry.ecosystem)
    return spec_for(ctx.entry.ecosystem)


def _installation_ids(ctx: Context) -> tuple[str, ...]:
    install = ctx.supported(_spec(ctx).install_fact_id)
    if install is None:
        return ()
    extra = [
        ctx.supported(i) for i in ("package:name", PUBLISHED_VERSION_FACT_ID, "package:version")
    ]
    return (install.id, *(fact.id for fact in extra if fact is not None))


def _dependency_ids(ctx: Context) -> tuple[str, ...]:
    ids = [f.id for f in ctx.facts.by_kind("dependency") if f.polarity == "SUPPORTED"]
    floor = _spec(ctx).floor_fact_id
    if floor and ctx.supported(floor) is not None:
        ids.append(floor)
    return tuple(ids[:20])


def _development_ids(ctx: Context) -> tuple[str, ...]:
    return tuple(
        fact.id
        for fact in (ctx.supported("build_test_asset:tests"), ctx.supported("build_test_asset:ci"))
        if fact is not None
    )


def _license_ids(ctx: Context) -> tuple[str, ...]:
    return tuple(
        fact.id
        for fact in (ctx.supported("license:spdx"), ctx.supported("license:file"))
        if fact is not None
    )


def _notice_ids(ctx: Context) -> tuple[str, ...]:
    return tuple(
        f.id for f in ctx.facts.by_kind("third_party_notices") if f.polarity == "SUPPORTED"
    )


@dataclass(frozen=True)
class Derivable:
    section_id: str
    evidence: Callable[[Context], tuple[str, ...]]
    already_says: Callable[[Context], bool]
    required: bool = True  # a required section with no fact behind it is reported


def _spells_install_command(ctx: Context) -> bool:
    install = ctx.supported(_spec(ctx).install_fact_id)
    first = install.value.splitlines()[0].strip() if install is not None else ""
    return bool(first) and first in ctx.readme


def _never(_ctx: Context) -> bool:
    return False


DERIVABLE: tuple[Derivable, ...] = (
    Derivable("installation", _installation_ids, _spells_install_command),
    Derivable("dependencies", _dependency_ids, _never),
    Derivable("development_testing", _development_ids, _never, required=False),
    Derivable("third_party_notices", _notice_ids, _never, required=False),
    Derivable("license", _license_ids, _never),
)


def _present(ctx: Context, section_id: str) -> bool:
    pattern = dict(_MEANS)[section_id]
    return any(
        (match := _HEADING.match(line.text)) is not None and pattern.search(match.group(2))
        for line in ctx.lines
        if not line.in_fence
    )


def _h2_order(ctx: Context) -> list[tuple[int, int]]:
    """``(offset, template index)`` of every H2 heading that means a template section."""
    found: list[tuple[int, int]] = []
    for line in ctx.lines:
        match = None if line.in_fence else _HEADING.match(line.text)
        if match is None or len(match.group(1)) != 2:
            continue
        for sid, pattern in _MEANS:
            if pattern.search(match.group(2)):
                found.append((line.start, _ORDER[sid]))
                break
    return found


def _rendered(ctx: Context, section_id: str) -> str:
    _spec(ctx)
    plan = {"sections": [{"section_id": section_id, "include": True}]}
    text = render_readme(ctx.entry, ctx.facts, plan, {"units": []}, {"dispositions": []})
    return text.strip("\n")


@detector("missing_sections")
def missing_sections(ctx: Context) -> DetectorResult:
    h2 = _h2_order(ctx)
    structured = sum(1 for line in ctx.lines if not line.in_fence and line.text.startswith("## "))
    edits: list[Edit] = []
    findings: list[Finding] = []
    if structured < 2:
        reason = "the README has fewer than two H2 sections; no section is inserted into it"
        return DetectorResult(findings=(Finding("missing_sections", 1, "", reason),))
    used_offsets: set[int] = set()
    for item in DERIVABLE:
        sid = item.section_id
        if _present(ctx, sid) or item.already_says(ctx):
            continue
        evidence = item.evidence(ctx)
        block = _rendered(ctx, sid) if evidence else ""
        if not block:
            if item.required:
                findings.append(
                    Finding(
                        "missing_sections", 0, "", f"{sid} is absent and no verified fact fills it"
                    )
                )
            continue
        later = [offset for offset, index in h2 if index > _ORDER[sid]]
        position = min(later) if later else len(ctx.readme)
        at_end = position == len(ctx.readme)
        if position in used_offsets:
            lead = NL if at_end else ""  # the block before it already ended the paragraph
        elif at_end:
            lead = (
                "" if ctx.readme.endswith(NL * 2) else (NL if ctx.readme.endswith(NL) else NL * 2)
            )
        else:
            blank_before = position == 0 or ctx.readme[:position].endswith(NL * 2)
            lead = "" if blank_before else NL
        tail = NL if at_end else NL * 2
        used_offsets.add(position)
        edits.append(
            Edit(
                kind=MISSING_SECTION,
                detector="missing_sections",
                start=position,
                end=position,
                original="",
                replacement=f"{lead}{block}{tail}",
                fact_ids=evidence,
                rationale=(
                    f"the README has no {_SHELL[sid].heading} section; the template's is rendered "
                    "from the cited facts alone"
                ),
                order=_ORDER[sid],
            )
        )
    for sid in _NEEDS_PROSE:
        if not _present(ctx, sid):
            findings.append(
                Finding(
                    "missing_sections",
                    0,
                    "",
                    f"{_SHELL[sid].heading} is absent and needs authored prose; "
                    "not derivable deterministically",
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
