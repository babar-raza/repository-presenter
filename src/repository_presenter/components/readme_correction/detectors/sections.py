"""Missing standard-template sections that verified facts alone can fill.

The template's Installation, Dependencies, Development and Testing and License sections (the four
of the ten that need no prose; an extra conditional section such as Third-party notices is not one
of the ten and is never added) are rendered by the existing deterministic renderer from facts
(``render_readme`` with a plan that includes just that section and no authored units). A section
the live README already has under any heading that means the same is never touched; a section
that needs prose - Key
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
from repository_presenter.components.readme.evidence.facts.commands import (
    BUILD_COMMAND_FACT_ID,
    CI_MATRIX_FACT_ID,
    TEST_COMMAND_FACT_ID,
)
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme_correction.augment import (
    CMAKE_FACT_ID,
    augment_dependencies,
)
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.detectors._layout import (
    fence_lines,
    navigation_plan,
)
from repository_presenter.components.readme_correction.detectors.additions import (
    _bullet_token,
    doc_link_bullets,
)
from repository_presenter.components.readme_correction.detectors.stale import (
    registry_says_unpublished,
    unpublished_commands,
)
from repository_presenter.components.readme_correction.model import (
    MISSING_INFO,
    MISSING_SECTION,
    Context,
    DetectorResult,
    Edit,
    Finding,
)
from repository_presenter.components.readme_correction.text_gate import clean
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


#: What would fill each prose section for the regeneration lane: the fact kinds it composes from.
_FILLED_BY: dict[str, tuple[str, ...]] = {
    "at_a_glance": ("capability", "format"),
    "key_capabilities": ("capability", "public_symbol"),
    "quick_start": ("example", "import_path"),
    "api_reference": ("public_symbol",),
    "documentation_resources": ("link_target",),
    "scope_limitations": ("inherited_unit", "format"),
}


def _filled_by(ctx: Context, section_id: str) -> str:
    parts = []
    for kind in _FILLED_BY[section_id]:
        count = sum(1 for f in ctx.facts.facts if f.kind == kind and f.polarity == "SUPPORTED")
        parts.append(f"{count} SUPPORTED {kind} fact(s)" if count else f"no SUPPORTED {kind} fact")
    return "would be filled from " + ", ".join(parts)


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
    if ctx.supported(CMAKE_FACT_ID) is not None:
        ids.append(CMAKE_FACT_ID)
    return tuple(ids[:20])


def _development_ids(ctx: Context) -> tuple[str, ...]:
    return tuple(
        fact.id
        for fact in (
            ctx.supported(fact_id)
            for fact_id in (
                "build_test_asset:tests",
                "build_test_asset:ci",
                BUILD_COMMAND_FACT_ID,
                TEST_COMMAND_FACT_ID,
                CI_MATRIX_FACT_ID,
            )
        )
        if fact is not None
    )


def _docs_locators(ctx: Context) -> tuple[str, ...]:
    return tuple(f"tree:{path}" for _bullet, path in doc_link_bullets(ctx))


def _docs_block(ctx: Context) -> str:
    bullets = [bullet for bullet, _path in doc_link_bullets(ctx)]
    return NL.join(["## Documentation & Resources", "", *bullets]) if bullets else ""


def _license_ids(ctx: Context) -> tuple[str, ...]:
    return tuple(
        fact.id
        for fact in (ctx.supported("license:spdx"), ctx.supported("license:file"))
        if fact is not None
    )


@dataclass(frozen=True)
class Derivable:
    section_id: str
    evidence: Callable[[Context], tuple[str, ...]]
    already_says: Callable[[Context], bool]
    required: bool = True  # a required section with no fact behind it is reported
    render: Callable[[Context], str] | None = None  # not the renderer: built from the tree
    locators: Callable[[Context], tuple[str, ...]] | None = None  # ``tree:`` evidence


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
    Derivable("license", _license_ids, _never),
    Derivable(
        "documentation_resources",
        lambda _ctx: (),
        _never,
        required=False,
        render=_docs_block,
        locators=_docs_locators,
    ),
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
    body = clean(text.strip(NL))
    return augment_dependencies(ctx, body) if section_id == "dependencies" else body


def _covered_elsewhere(ctx: Context, sid: str, block: str) -> str | None:
    """Why inserting this section would only repeat what the README already says, or None.

    Dependencies: a package the block lists is already named somewhere in the README. Installation:
    an install snippet naming the package is already shown."""
    readme = ctx.readme.lower()
    if sid == "dependencies":
        named = [
            token
            for line in block.splitlines()
            if line.startswith("- ")
            and (token := _bullet_token(line)) is not None
            and not line.startswith("- Requires")
        ]
        hit = next((token for token in named if token in readme), None)
        if hit is not None:
            return f"the README already names {hit!r} elsewhere"
    if sid == "installation":
        package = ctx.supported("package:name")
        if package is not None:
            token = package.value.split(":")[-1].lower()
            if any(token in text.lower() for _lang, text in fence_lines(ctx)):
                return f"the README already shows a snippet naming {token!r}"
    return None


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
    inserted: set[str] = set()
    for item in DERIVABLE:
        sid = item.section_id
        if _present(ctx, sid) or item.already_says(ctx):
            continue
        evidence = item.evidence(ctx)
        locators = item.locators(ctx) if item.locators else ()
        block = ""
        if evidence or locators:
            block = item.render(ctx) if item.render else _rendered(ctx, sid)
        if not block:
            if item.required:
                findings.append(
                    Finding(
                        "missing_sections", 0, "", f"{sid} is absent and no verified fact fills it"
                    )
                )
            continue
        skip = _covered_elsewhere(ctx, sid, block)
        if sid == "installation" and registry_says_unpublished(ctx) and unpublished_commands(ctx):
            skip = "the README installs the package from a registry that does not list it"
        if skip is not None:
            findings.append(
                Finding(
                    "missing_sections",
                    0,
                    "",
                    f"{_SHELL[sid].heading} is absent but not inserted: {skip}",
                )
            )
            continue
        later = [offset for offset, index in h2 if index > _ORDER[sid]]
        position = min(later) if later else len(ctx.readme)
        heading = _SHELL[sid].heading or sid
        navigation = navigation_plan(ctx, heading, min(later) if later else None)
        if navigation.status == "unsafe":
            findings.append(
                Finding(
                    "missing_sections",
                    0,
                    "",
                    f"{heading} is absent but not inserted: the README's contents list cannot be "
                    "extended safely",
                )
            )
            continue
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
                locators=locators,
                rationale=(
                    f"the README has no {_SHELL[sid].heading} section; the template's is rendered "
                    "from the cited facts alone"
                ),
                order=_ORDER[sid],
            )
        )
        if navigation.status == "ok":
            edits.append(
                Edit(
                    kind=MISSING_INFO,
                    detector="missing_sections",
                    start=navigation.offset,
                    end=navigation.offset,
                    original="",
                    replacement=navigation.text,
                    fact_ids=evidence,
                    locators=(f"{ctx.readme_path}:{navigation.line}", *locators),
                    rationale=(
                        f"the README's contents list gains the {heading} item beside "
                        f"line {navigation.line}, so the inserted section is reachable from it"
                    ),
                    order=_ORDER[sid],
                )
            )
        inserted.add(sid)
    for sid in _NEEDS_PROSE:
        if sid not in inserted and not _present(ctx, sid):
            findings.append(
                Finding(
                    "missing_sections",
                    0,
                    "",
                    f"{_SHELL[sid].heading} is absent and needs authored prose; "
                    f"not derivable deterministically; {_filled_by(ctx, sid)}",
                )
            )
    return DetectorResult(edits=tuple(edits), findings=tuple(findings))
