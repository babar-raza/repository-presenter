"""Verified information the live README lacks, added to a section it already has.

Every addition is a pure insertion at the end of an existing section (never a replacement, never
a heading), is rendered by the project's own deterministic renderer or taken verbatim from a
fact or from the pinned tree, and is made only when the README does not already say it:

* ``add_dev_commands``  the clone's build and test commands, the CI matrix, the suite size and the
  release workflow (TC-COV-02 facts) in Development and Testing;
* ``add_install_forms``  the verified install command and, for Java, the Maven and Gradle
  declarations, in Installation;
* ``add_doc_links``      links to the changelog, contributing guide, security policy, code of
  conduct and ``docs/`` the pinned tree holds, in Documentation and Resources;
* ``add_version_badge``  the registry's published-version badge, on the badge row.

Presence is judged on the README as a whole, by the command, path or coordinate itself, never by
the heading it sits under, so an equivalent the maintainers wrote differently is left alone.
"""

from __future__ import annotations

import posixpath
import re

from repository_presenter.components.readme.composition.renderer import (
    RenderContext,
    badge_slots,
    render_readme,
)
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
from repository_presenter.components.readme_correction.commands import (
    covered,
    missing_precondition,
    readme_commands,
    states_install,
)
from repository_presenter.components.readme_correction.detectors import detector
from repository_presenter.components.readme_correction.detectors._layout import (
    addition_text,
    append_point,
    eol,
    fence_lines,
    find_section,
)
from repository_presenter.components.readme_correction.model import (
    MISSING_INFO,
    Context,
    DetectorResult,
    Edit,
    Finding,
    ReadmeLine,
)
from repository_presenter.components.readme_correction.text_gate import clean
from repository_presenter.core.ecosystems import EcosystemSpec, spec_for
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID

DEV_HEADING = re.compile(r"develop|testing|\btests?\b|building|\bbuild\b", re.IGNORECASE)
INSTALL_HEADING = re.compile(r"install|set-?up|getting started", re.IGNORECASE)
DOCS_HEADING = re.compile(r"documentation|resources|links", re.IGNORECASE)
_SHELL = frozenset({"bash", "sh", "shell", "console", "text", "powershell", "ps1", "cmd", ""})
_GRADLE = frozenset({"groovy", "kotlin", "gradle", "kts"})


def _squash(text: str) -> str:
    return " ".join(text.split())


def _render_section(ctx: Context, section_id: str, facts: tuple[Fact, ...]) -> str:
    """The deterministic renderer's section for ``section_id`` over ``facts``, heading removed."""
    plugin_for(ctx.entry.ecosystem)
    document = FactsDocument(ctx.facts.repository, ctx.facts.source_revision, facts)
    plan = {"sections": [{"section_id": section_id, "include": True}]}
    text = render_readme(ctx.entry, document, plan, {"units": []}, {"dispositions": []})
    lines = text.splitlines()
    body = clean(chr(10).join(lines[1:]).strip(chr(10))) if lines else ""
    return augment_dependencies(ctx, body) if section_id == "dependencies" else body


# ----------------------------------------------------------------------- Development and Testing
#: Independent review of the correction bundles (2026-10-11): every failing content hunk was an
#: add_dev_commands edit - a duplicate of a command the section already shows, commands stitched
#: from unrelated CI steps (a release Debug build with a package-test ctest, a sanitizer job without
#: its configure step), a command that fails on a clean clone. A fact being SUPPORTED shows it
#: exists, not that the sequence runs. So the detector only reports until a command can be shown
#: to run.
DEV_RE_ENABLE = (
    "the commands come from ONE CI job's contiguous steps (configure, build and test of the same "
    "job, the primary non-sanitizer non-release job) and a build receipt verifies the sequence on "
    "a clean clone: the fact carries attributes ci_job_contiguous=true and a build_receipt"
)


def _dev_conditions_unmet(ctx: Context, cited: tuple[str, ...]) -> str:
    """Why the cited build/test facts may not yet be edited in, or '' when they may. Today no
    extractor records the job chain or a receipt, so the answer is always the reason."""
    commands = [ctx.fact(i) for i in cited if i in (BUILD_COMMAND_FACT_ID, TEST_COMMAND_FACT_ID)]
    for fact in commands:
        attributes = (fact.attributes or {}) if fact is not None else {}
        if attributes.get("ci_job_contiguous") != "true" or not attributes.get("build_receipt"):
            return "the commands are not one CI job's contiguous steps verified by a build receipt"
    if not commands:
        return "no verified build or test command is cited, only CI or suite information"
    return ""


@detector("add_dev_commands")
def add_dev_commands(ctx: Context) -> DetectorResult:
    section = find_section(ctx, DEV_HEADING)
    point = None if section is None else append_point(ctx, section)
    if section is None or point is None:
        return DetectorResult()
    readme = _squash(ctx.readme)
    shown = readme_commands(ctx)
    dropped: set[str] = set()
    findings: list[Finding] = []
    for fact in ctx.facts.facts:
        if fact.polarity != "SUPPORTED":
            continue
        if fact.id in (BUILD_COMMAND_FACT_ID, TEST_COMMAND_FACT_ID):
            needs = missing_precondition(fact.value)
            if _squash(fact.value) in readme or covered(ctx, fact.value, shown):
                dropped.add(fact.id)  # the README already shows this command, in some form
                findings.append(
                    Finding(
                        "add_dev_commands",
                        0,
                        fact.value.splitlines()[0][:80],
                        f"the README already shows `{fact.value.splitlines()[0]}` in some form; "
                        "not added",
                        (fact.id,),
                        report_only_reason="ALREADY_SHOWN",
                        candidate=fact.value,
                    )
                )
            elif needs is not None and not states_install(ctx, needs):
                dropped.add(fact.id)
                findings.append(
                    Finding(
                        "add_dev_commands",
                        0,
                        fact.value.splitlines()[0][:80],
                        f"`{fact.value.splitlines()[0]}` needs `{needs}` installed first "
                        f"(`pip install {needs}`), which the evidence of {fact.id} does not "
                        "name; not added",
                        (fact.id,),
                        report_only_reason="NEEDS_INSTALL_FIRST",
                        candidate=fact.value,
                    )
                )
        elif fact.id == CI_MATRIX_FACT_ID:
            if fact.evidence and fact.evidence[0].path in readme:
                dropped.add(fact.id)
        elif fact.id == "build_test_asset:tests":
            # A wrong suite size is corrected (claim_test_files); an absent one is not added.
            dropped.add(fact.id)
        elif fact.id == "build_test_asset:ci":
            workflows = [e.path for e in fact.evidence if e.path.endswith((".yml", ".yaml"))]
            if any(path in readme for path in workflows):
                dropped.add(fact.id)
    dev_ids = {
        "build_test_asset:ci",
        BUILD_COMMAND_FACT_ID,
        TEST_COMMAND_FACT_ID,
        CI_MATRIX_FACT_ID,
    }
    kept = tuple(f for f in ctx.facts.facts if f.id not in dropped)
    body = _render_section(ctx, "development_testing", kept)
    if not body:
        return DetectorResult(findings=tuple(findings))
    cited = tuple(sorted(f.id for f in kept if f.id in dev_ids and f.polarity == "SUPPORTED"))
    # Nothing the README lacks is cited: either every piece was already there, or the section
    # rendered only what the maintainers' own words already cover.
    if not cited:
        return DetectorResult(findings=tuple(findings))
    text = addition_text(ctx, point, body.splitlines(), continue_list=False)
    unmet = _dev_conditions_unmet(ctx, cited)
    if unmet:  # report-only: the candidate is listed with its evidence, never applied
        findings.append(
            Finding(
                "add_dev_commands",
                ctx.readme.count(chr(10), 0, point.offset) + 1,
                section.title,
                f"'{section.title}' could take the clone's build and test information; not "
                f"applied: {unmet}",
                cited,
                report_only_reason="RE_ENABLE_CONDITION_UNMET",
                candidate=text,
                re_enable=DEV_RE_ENABLE,
            )
        )
        return DetectorResult(findings=tuple(findings))
    return DetectorResult(
        edits=(
            Edit(
                kind=MISSING_INFO,
                detector="add_dev_commands",
                start=point.offset,
                end=point.offset,
                original="",
                replacement=text,
                fact_ids=cited,
                rationale=(
                    f"'{section.title}' lacks the clone's verified build and test information "
                    "(commands, CI matrix, suite size, release workflow); the renderer's "
                    "sentences and command block for the cited facts are appended"
                ),
            ),
        ),
        findings=tuple(findings),
    )


# ------------------------------------------------------------------------------- Dependencies
DEPENDENCIES_HEADING = re.compile(r"dependenc|requirement|prerequisite", re.IGNORECASE)
_BULLET_KEY = re.compile(r"^- `([^`]+)`")
_ZERO = re.compile(
    r"(?i)\b(?:no|zero|without)\s+(?:required\s+|third[- ]party\s+|runtime\s+)*dependenc"
)


_NONE = re.compile(r"(?i)\bnone\b")


def _bullet_token(line: str) -> str | None:
    """What a rendered dependency bullet is about: its package name, or its floor version."""
    match = _BULLET_KEY.match(line)
    if match is not None:
        return re.split(r"[<>=!~ \[]", match.group(1), maxsplit=1)[0].lower()
    floor = re.search(r"(\d+(?:\.\d+)*)", line)
    return floor.group(1) if line.startswith("- Requires") and floor else None


@detector("add_dependency_groups")
def add_dependency_groups(ctx: Context) -> DetectorResult:
    """Dependency groups the README's Dependencies section never mentions, from the dependency
    facts: a group (Required, Optional, Native and System, Development) the README has no heading
    for, with only the entries whose package or floor version the README names nowhere."""
    section = find_section(ctx, DEPENDENCIES_HEADING)
    point = None if section is None else append_point(ctx, section)
    if section is None or point is None:
        return DetectorResult()
    body = _render_section(ctx, "dependencies", ctx.facts.facts)
    if not body:
        return DetectorResult()
    headings = {ln.text.strip("# ").strip().lower() for ln in ctx.lines if ln.text.startswith("#")}
    readme = ctx.readme.lower()
    section_text = chr(10).join(line.text for line in section.lines)
    groups: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        if line.startswith("### "):
            groups.append((line, []))
        elif groups and line.strip():
            groups[-1][1].append(line)
    block: list[str] = []
    for heading, lines in groups:
        if heading[4:].strip().lower() in headings:
            continue
        kept = []
        for line in lines:
            token = _bullet_token(line)
            if not line.startswith("- "):  # the "no required dependencies" statement
                if not (_ZERO.search(ctx.readme) or _NONE.search(section_text)):
                    kept.append(line)
            elif token is not None and token not in readme:
                kept.append(line)
        if kept:
            block += [heading, "", *kept, ""]
    if not block:
        return DetectorResult()
    cited = tuple(
        sorted(
            f.id for f in ctx.facts.facts if f.kind == "dependency" and f.polarity == "SUPPORTED"
        )
    )[:20]
    floor = spec_for_ecosystem(ctx).floor_fact_id
    if floor and ctx.supported(floor) is not None:
        cited += (floor,)
    if ctx.supported(CMAKE_FACT_ID) is not None:
        cited += (CMAKE_FACT_ID,)
    return DetectorResult(
        edits=(
            Edit(
                kind=MISSING_INFO,
                detector="add_dependency_groups",
                start=point.offset,
                end=point.offset,
                original="",
                replacement=addition_text(ctx, point, block[:-1], continue_list=False),
                fact_ids=cited,
                rationale=(
                    f"'{section.title}' names none of the dependency information of the cited "
                    "facts for the groups added"
                ),
            ),
        )
    )


# --------------------------------------------------------------------------------- Installation
def _chunks(body: str) -> list[tuple[str, str, list[str]]]:
    """``(lead, language, fence lines)`` of each fenced block in ``body``, with the paragraph
    immediately before it as the lead."""
    chunks: list[tuple[str, str, list[str]]] = []
    paragraph: list[str] = []
    last = ""
    fence: list[str] | None = None
    language = ""
    for line in body.splitlines():
        if fence is None:
            if line.startswith("```"):
                fence, language = [], line[3:].strip().lower()
            elif line.strip():
                paragraph.append(line)
            elif paragraph:
                last, paragraph = chr(10).join(paragraph), []
        elif line.startswith("```"):
            lead = chr(10).join(paragraph) or last
            chunks.append((lead, language, fence))
            fence, paragraph, last = None, [], ""
        else:
            fence.append(line)
    return chunks


def _shows(ctx: Context, language: str, token: str) -> bool:
    """Whether the README already has a snippet of this family naming ``token``."""
    family = _GRADLE if language in _GRADLE else {language} if language == "xml" else _SHELL
    return any(lang in family and token in text.lower() for lang, text in fence_lines(ctx))


def _named_in_code(ctx: Context, token: str) -> bool:
    """Whether the package ``token`` appears in any code of the README: a fenced line or an inline
    code span, in whatever language (a Maven XML snippet already carries ``mvn dependency:get``'s
    coordinates)."""
    if any(token in text.lower() for _language, text in fence_lines(ctx)):
        return True
    return any(
        token in span.lower()
        for line in ctx.lines
        if not line.in_fence
        for span in re.findall(r"`([^`\n]+)`", line.text)
    )


@detector("add_install_forms")
def add_install_forms(ctx: Context) -> DetectorResult:
    section = find_section(ctx, INSTALL_HEADING)
    point = None if section is None else append_point(ctx, section)
    install = ctx.supported(spec_for_ecosystem(ctx).install_fact_id)
    package = ctx.supported("package:name")
    if section is None or point is None or install is None or package is None:
        return DetectorResult()
    if (install.attributes or {}).get("install_kind") in {"source", "source_checkout"}:
        return DetectorResult()
    version = ctx.supported(PUBLISHED_VERSION_FACT_ID) or ctx.supported("package:version")
    spec = spec_for_ecosystem(ctx)
    token = package.value.split(":")[-1].lower()
    first = _squash(install.value.splitlines()[0]) if install.value else ""
    wanted: list[tuple[str, str, list[str]]] = []
    body = _render_section(ctx, "installation", ctx.facts.facts)
    alternatives = {
        body_text.strip()
        for _lead, _fence, body_text in spec.install_alternative_blocks(
            package.value, version.value if version is not None else ""
        )
    }
    for lead, language, lines in _chunks(body):
        text = chr(10).join(lines).strip()
        primary = bool(first) and _squash(lines[0]) == first if lines else False
        if not (primary or text in alternatives):
            continue  # only the install command and the declared alternatives are additions
        if (primary and first in _squash(ctx.readme)) or _shows(ctx, language, token):
            continue
        if primary and _named_in_code(ctx, token):
            continue  # the coordinates are already shown in a snippet (XML, Gradle, inline code)
        wanted.append((lead, language, lines))
    if not wanted:
        return DetectorResult()
    block: list[str] = []
    for lead, language, lines in wanted:
        block += ([lead, ""] if lead else []) + [f"```{language}", *lines, "```", ""]
    text = addition_text(ctx, point, block[:-1], continue_list=False)
    cited = tuple(
        f.id for f in (install, package, ctx.supported(PUBLISHED_VERSION_FACT_ID)) if f is not None
    )
    return DetectorResult(
        edits=(
            Edit(
                kind=MISSING_INFO,
                detector="add_install_forms",
                start=point.offset,
                end=point.offset,
                original="",
                replacement=text,
                fact_ids=cited,
                rationale=(
                    f"'{section.title}' shows no snippet naming {token!r} in "
                    f"{', '.join(sorted({language or 'shell' for _l, language, _f in wanted}))}; "
                    "the verified install form(s) are appended"
                ),
            ),
        )
    )


def spec_for_ecosystem(ctx: Context) -> EcosystemSpec:
    plugin_for(ctx.entry.ecosystem)
    return spec_for(ctx.entry.ecosystem)


# ------------------------------------------------------------------- Documentation and Resources
_DOC_FILES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "Changelog",
        "release history.",
        re.compile(r"(?i)^(changelog|changes|history)(\.md|\.rst|\.txt)?$"),
    ),
    (
        "Contributing guide",
        "how to contribute.",
        re.compile(r"(?i)^contributing(\.md|\.rst|\.txt)?$"),
    ),
    (
        "Security policy",
        "how to report a vulnerability.",
        re.compile(r"(?i)^security(\.md|\.rst|\.txt)?$"),
    ),
    (
        "Code of conduct",
        "community standards.",
        re.compile(r"(?i)^code[_-]of[_-]conduct(\.md|\.rst|\.txt)?$"),
    ),
)


#: The same review found add_doc_links treating any docs/ directory as documentation (Slides-.NET
#: and Slides-Cpp: docs/ holds a banner, a NuGet icon and a NuGet README), and a bullet landing
#: after the section's closing rule. The detector reports its candidate until the fact below exists.
DOCS_FACT_ID = "build_test_asset:documentation"
DOCS_RE_ENABLE = (
    f"a SUPPORTED fact {DOCS_FACT_ID} records a tracked docs directory holding documentation files "
    "(at least one .md or .rst with prose, not images or package assets), and the bullet is placed "
    "inside the section's existing list"
)
_ASSET_DIRS = frozenset(
    {"media", "assets", "images", "img", "nuget", "static", "public", "icons", "banner", "logo"}
)


def docs_hold_documentation(ctx: Context) -> bool:
    """Whether ``docs/`` of the pinned tree holds at least one markdown or reST file outside the
    asset directories (a banner, an icon and a package README are not documentation)."""
    for path in ctx.tree_paths:
        parts = path.lower().split("/")
        is_text = parts[-1].endswith((".md", ".rst"))
        if parts[0] == "docs" and len(parts) > 1 and is_text and not _ASSET_DIRS & set(parts[1:-1]):
            return True
    return False


def docs_conditions_unmet(ctx: Context) -> str:
    """Why documentation links may not yet be edited in, or '' when they may."""
    if ctx.supported(DOCS_FACT_ID) is None:
        return "no fact records a tracked docs directory holding documentation files"
    return ""


def doc_link_bullets(ctx: Context) -> list[tuple[str, str]]:
    """``(bullet, tree path)`` for each community or documentation file the pinned tree holds that
    the README never names, in a fixed order. Root files win over ``.github/`` ones."""
    readme = ctx.readme.lower()
    found: list[tuple[str, str]] = []
    for label, gloss, pattern in _DOC_FILES:
        candidates = [
            path
            for path in ctx.tree_paths
            if posixpath.dirname(path) in {"", ".github", "docs"}
            and pattern.match(posixpath.basename(path))
        ]
        if not candidates:
            continue
        path = sorted(
            candidates, key=lambda p: (posixpath.dirname(p) != "", posixpath.dirname(p), p)
        )[0]
        if posixpath.basename(path).lower() in readme:
            continue
        found.append((f"- **[{label}]({path})** — {gloss}", path))
    has_docs = any(path.startswith("docs/") for path in ctx.tree_paths)
    if has_docs and "docs/" not in readme and docs_hold_documentation(ctx):
        found.append(
            ("- **[Documentation](docs/)** — documentation kept in this repository.", "docs/")
        )
    return found


@detector("add_doc_links")
def add_doc_links(ctx: Context) -> DetectorResult:
    section = find_section(ctx, DOCS_HEADING)
    point = None if section is None else append_point(ctx, section)
    bullets = doc_link_bullets(ctx)
    findings: list[Finding] = []
    has_docs = any(path.startswith("docs/") for path in ctx.tree_paths)
    if has_docs and "docs/" not in ctx.readme.lower() and not docs_hold_documentation(ctx):
        findings.append(
            Finding(
                "add_doc_links",
                0,
                "docs/",
                "docs/ holds no documentation files (only media or package assets), so the "
                "README is not linked to it as documentation",
                report_only_reason="DOCS_HOLDS_NO_DOCUMENTATION",
                locators=("tree:docs/",),
            )
        )
    if section is None or point is None or not bullets:
        return DetectorResult(findings=tuple(findings))
    text = addition_text(ctx, point, [b for b, _p in bullets], continue_list=True)
    unmet = docs_conditions_unmet(ctx)
    if unmet:  # report-only: the candidate is listed with its evidence, never applied
        findings.append(
            Finding(
                "add_doc_links",
                ctx.readme.count(chr(10), 0, point.offset) + 1,
                section.title,
                f"'{section.title}' could link {', '.join(p for _b, p in bullets)}; not "
                f"applied: {unmet}",
                report_only_reason="RE_ENABLE_CONDITION_UNMET",
                candidate=text,
                re_enable=DOCS_RE_ENABLE,
                locators=tuple(f"tree:{path}" for _b, path in bullets),
            )
        )
        return DetectorResult(findings=tuple(findings))
    return DetectorResult(
        findings=tuple(findings),
        edits=(
            Edit(
                kind=MISSING_INFO,
                detector="add_doc_links",
                start=point.offset,
                end=point.offset,
                original="",
                replacement=text,
                fact_ids=(),
                locators=tuple(f"tree:{path}" for _b, path in bullets),
                rationale=(
                    f"'{section.title}' does not name {', '.join(p for _b, p in bullets)}, which "
                    "the pinned tree holds"
                ),
            ),
        ),
    )


# ----------------------------------------------------------------------------------------- badge
_BADGE_OPEN = re.compile(r"\[?!\[")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
_BADGE_URL = re.compile(r"!\[[^\]]*\]\(https?://([^/\s)]+)/([^/\s)]+)")


def _badge_family(badge: str) -> str:
    """Where a registry's badge comes from, to the segment that names the registry (shields.io's
    maven-central, pypi, nuget; pkg.go.dev's badge): a README showing that family has a badge."""
    match = _BADGE_URL.search(badge)
    if match is None:
        return ""
    host, first = match.group(1), match.group(2)
    if host == "img.shields.io":
        second = re.search(r"img\.shields\.io/[^/]+/([^/\s)]+)", badge)
        return f"{host}/{first}/" + (second.group(1) if second and first != "badge" else "")
    return f"{host}/{first}/"


@detector("add_version_badge")
def add_version_badge(ctx: Context) -> DetectorResult:
    """The registry's published-version badge, when the package is published and the README shows
    no version badge of that registry. Added at the end of the badge row (the last preamble line
    carrying a badge), else on its own line under the title."""
    if ctx.supported(PUBLISHED_VERSION_FACT_ID) is None:
        return DetectorResult()
    plugin_for(ctx.entry.ecosystem)
    context = RenderContext(
        ctx.entry, ctx.facts.canonical(), {"sections": []}, {"units": []}, {"dispositions": []}
    )
    slots = dict(badge_slots(context))
    badge = slots.get("package")
    if not badge:
        return DetectorResult()
    family = _badge_family(badge)
    if family and re.search(re.escape(family), ctx.readme, re.IGNORECASE):
        return DetectorResult()
    preamble: list[ReadmeLine] = []
    for line in ctx.lines:
        if not line.in_fence and line.text.startswith("## "):
            break
        preamble.append(line)
    row = [line for line in preamble if _IMAGE.search(line.text) and "shields.io" in line.text]
    cited = tuple(
        f.id
        for f in (
            ctx.supported("package:name"),
            ctx.supported(PUBLISHED_VERSION_FACT_ID),
            ctx.supported(spec_for_ecosystem(ctx).install_fact_id),
        )
        if f is not None
    )
    if row:
        first = row[0]
        opener = _BADGE_OPEN.search(first.text)
        at = opener.start() if opener else -1
        if at < 0 or first.text[:at].strip():
            return DetectorResult()  # the row opens with text: no safe place in the stable order
        edit = Edit(
            kind=MISSING_INFO,
            detector="add_version_badge",
            start=first.start + at,
            end=first.start + at,
            original="",
            replacement=badge + " ",
            fact_ids=cited,
            rationale="the README shows no published-version badge; the registry's leads its "
            "badge row (the package badge is first in the stable order)",
        )
        return DetectorResult(edits=(edit,))
    title = next((line for line in preamble if line.text.startswith("# ")), None)
    if title is None:
        return DetectorResult()
    newline = eol(ctx)
    terminator = ctx.readme[title.end : title.end + 2]
    step = 2 if terminator.startswith("\r\n") else 1 if terminator.startswith(chr(10)) else 0
    prefix = "" if step else newline
    after = title.end + step
    following = ctx.readme[after : after + 1]
    suffix = newline if following and following not in {chr(10), chr(13)} else ""
    edit = Edit(
        kind=MISSING_INFO,
        detector="add_version_badge",
        start=title.end + step,
        end=title.end + step,
        original="",
        replacement=f"{prefix}{newline}{badge}{newline}{suffix}",
        fact_ids=cited,
        rationale="the README shows no published-version badge; the registry's is added under "
        "the title",
    )
    return DetectorResult(edits=(edit,))
