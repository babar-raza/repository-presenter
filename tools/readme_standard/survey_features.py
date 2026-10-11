"""Measure one README into the flat feature record that docs/README_STANDARD.md counts.

A pure function of the README text (plus, optionally, the repository tree for relative-link
checks). No network, no clock, no model. It is the one definition of every figure the standard
quotes: ``data/readme_standard/survey.json`` holds its output for the 36 registry repositories,
``tools/readme_standard/check_profiles.py`` recomputes the standard's frequencies from that file,
and the same functions are the deterministic detectors the standard's defect table names.

Owner/reviewer tooling (tools/README.md): never imported by src/, never read by a product stage.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any
from urllib.parse import unquote

# Moves when a measure's definition changes; survey.json records the version it was built with.
FEATURES_VERSION = 1

# The standard's twelve H2 names, in the order the generated portfolio READMEs use them.
STANDARD_H2 = (
    "Navigation",
    "At a Glance",
    "Key Capabilities",
    "Installation",
    "Dependencies",
    "Quick Start",
    "Additional Examples",
    "API Reference",
    "Documentation & Resources",
    "Scope and Limitations",
    "Development and Testing",
    "License",
)
# The ten sections the owner's standard template names (plans/idea.md; Navigation and Additional
# Examples are the two structural additions every generated README also carries).
TEN_SECTIONS = (
    "At a Glance",
    "Key Capabilities",
    "Installation",
    "Dependencies",
    "Quick Start",
    "API Reference",
    "Documentation & Resources",
    "Scope and Limitations",
    "Development and Testing",
    "License",
)

_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_IMAGE_LINK = re.compile(r"\[!\[([^\]]*)\]\(([^)\s]+)[^)]*\)\]\(([^)\s]+)[^)]*\)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿⭐⭕]")
_BANNED_EDITION = re.compile(
    r"commercial edition|on-?premises? edition|paid version|full version", re.IGNORECASE
)
_PIP_UNQUOTED = re.compile(r"pip3?\s+install\s+(?:-\S+\s+)*[^\s\"'`|]*[<>]=")
_BOILERPLATE_ROW = re.compile(
    r"^(?:Class|Struct|Interface|Enum|Trait|Enumeration)\s+(?:with\s+\d+\s+\w+|in the .+ API|"
    r"extending\s+\w+)|^Represents the \S+ component\.?$|^Created by .+ on \d",
    re.IGNORECASE,
)
_MARKETING = re.compile(
    r"\b(?:unparalleled|blazing|seamless(?:ly)?|cutting-edge|revolutionary|world-class|"
    r"state-of-the-art|industry-leading|game-chang\w+|effortless(?:ly)?|best-in-class)\b",
    re.IGNORECASE,
)
_COMMERCIAL_SUBSTITUTE = re.compile(
    r"\bcommercial (?:Aspose[.\w]*|product|package|edition|version|library|source|codebase)\b",
    re.IGNORECASE,
)
_BADGE_RANK = {"package": 0, "runtime": 1, "ci": 2, "license": 3, "contributors": 4}
_AUDIENCE = re.compile(
    r"\bfor (?:developers|teams)\b|\bideal for\b|\bdevelopers (?:use|who|coming)\b|"
    r"\bdesigned for\b|\bfor migrants\b|\bmigrants\b|\bused by\b",
    re.IGNORECASE,
)
_FIRST_PERSON = re.compile(r"\b(?:we|We|our|Our|ours)\b|\bI\b(?![/'])|\b(?:my|My)\b")
_SECOND_PERSON = re.compile(r"\byou(?:r|rs|rself)?\b", re.IGNORECASE)
_TYPE_COUNT = re.compile(r"(\d[\d,]*)\s+(?:public\s+)?(?:types|classes and enumerations)\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\[(\"'])")
_ASPOSE_HOST = re.compile(r"^(?:[\w-]+\.)*aspose\.(org|com)$", re.IGNORECASE)
_REGISTRY_COMMANDS = (
    (
        "pip",
        re.compile(r"\bpip3?[ \t]+install[ \t]+(?!-e\b|-r\b|\.|git\+)[\"']?[A-Za-z][\w.\-\[\]]*"),
    ),
    ("dotnet-add-package", re.compile(r"\bdotnet\s+add\s+package\b")),
    ("nuget-cli", re.compile(r"\bInstall-Package\b|\bnuget\s+install\b")),
    ("maven-dependency", re.compile(r"<dependency>")),
    ("gradle", re.compile(r"\bimplementation\s*[(\"']")),
    ("go-get", re.compile(r"\bgo\s+get\b")),
    ("npm", re.compile(r"\bnpm[ \t]+(?:install|i)[ \t]+(?!--)(?!run\b)[@A-Za-z][\w@/.\-]*")),
    ("cargo-add", re.compile(r"\bcargo\s+add\b")),
)
_NATIVE_BUILD_TOKENS = re.compile(r"add_subdirectory|FetchContent|find_package|cmake\s+-")
_SOURCE_TOKENS = re.compile(
    r"\bgit\s+clone\b|pip\s+install\s+-e|\bnpm\s+install\b|ProjectReference"
)


class Line:
    """One physical line with the context the measures need."""

    __slots__ = ("code", "details", "number", "opener", "text")

    def __init__(self, number: int, text: str, code: bool, details: int, opener: bool) -> None:
        self.number = number
        self.text = text
        self.code = code
        self.details = details
        self.opener = opener


def scan(text: str) -> list[Line]:
    """Every line with fence state and ``<details>`` nesting depth at that line."""
    lines: list[Line] = []
    fence: tuple[str, int] | None = None
    depth = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        match = _FENCE.match(raw)
        if fence is None:
            if match:
                fence = (match.group(1)[0], len(match.group(1)))
                lines.append(Line(number, raw, True, depth, True))
                continue
            scrubbed = _CODE_SPAN.sub("", raw)
            opens = len(re.findall(r"<details\b", scrubbed, re.IGNORECASE))
            closes = len(re.findall(r"</details>", scrubbed, re.IGNORECASE))
            inside = depth + (1 if opens else 0)
            lines.append(Line(number, raw, False, inside, False))
            depth = max(0, depth + opens - closes)
        else:
            closing = (
                match is not None
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and not match.group(2).strip()
            )
            lines.append(Line(number, raw, True, depth, False))
            if closing:
                fence = None
    return lines


def _visible_lines(text: str) -> int:
    """Lines outside ``<details>`` blocks, blank lines included and the tag lines themselves
    excluded - the count composition/renderer.py ``line_counts`` budgets."""
    visible = 0
    depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<details"):
            depth += 1
        elif stripped.startswith("</details"):
            depth = max(0, depth - 1)
        elif depth == 0:
            visible += 1
    return visible


def _headings(lines: Sequence[Line]) -> list[tuple[int, int, str, bool]]:
    found = []
    for line in lines:
        if line.code:
            continue
        match = _HEADING.match(line.text)
        if match:
            found.append(
                (line.number, len(match.group(1)), match.group(2).strip(), line.details > 0)
            )
    return found


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower-case, punctuation dropped, spaces to hyphens."""
    lowered = re.sub(r"[`*_]", "", heading.strip().lower())
    lowered = re.sub(r"[^\w\- ]", "", lowered)
    return lowered.replace(" ", "-")


def _section(
    lines: Sequence[Line], heads: Sequence[tuple[int, int, str, bool]], name: str, level: int = 2
) -> list[Line]:
    """Lines under the first heading of ``level`` named ``name``, up to the next heading of the
    same or a shallower level."""
    for index, (number, lvl, title, _inside) in enumerate(heads):
        if lvl == level and title == name:
            end = len(lines) + 1
            for later in heads[index + 1 :]:
                if later[1] <= level:
                    end = later[0]
                    break
            return [line for line in lines if number < line.number < end]
    return []


def _links(body: Sequence[Line]) -> list[str]:
    """Link destinations (not image sources) in prose lines, code spans removed."""
    found: list[str] = []
    for line in body:
        if line.code:
            continue
        stripped = _CODE_SPAN.sub("", line.text)
        for _alt, _img, target in _IMAGE_LINK.findall(stripped):
            found.append(target)
        stripped = _IMAGE_LINK.sub("", stripped)
        found.extend(match[2] for match in _LINK.finditer(stripped))
        found.extend(_AUTOLINK.findall(stripped))
    return found


def _host(url: str) -> str:
    match = re.match(r"^[a-z][a-z0-9+.\-]*://([^/:?#]+)", url, re.IGNORECASE)
    return match.group(1).lower() if match else ""


def _is_aspose(url: str) -> bool:
    return bool(_ASPOSE_HOST.match(_host(url)))


def _badge_paragraph(lines: Sequence[Line], first_h2: int) -> tuple[list[str], int]:
    """Badge images and the number of badge paragraphs between the H1 and the first H2."""
    rows: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.number >= first_h2:
            break
        if line.code:
            continue
        text = line.text.strip()
        if not text:
            if current:
                rows.append(current)
                current = []
            continue
        images = [m[2] for m in _IMAGE.finditer(text)]
        badge = images and all(
            ("shields.io" in u or "badge" in u.lower() or "pkg.go.dev" in u) for u in images
        )
        if badge and not text.startswith("#"):
            current.extend(images)
        elif current:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    flat = [image for row in rows for image in row]
    return flat, len(rows)


def _badge_kind(url: str) -> str:
    lowered = url.lower()
    if any(k in lowered for k in ("nuget/v", "maven-central", "pypi/v", "crates/v", "npm/v")):
        return "package"
    if "pkg.go.dev" in lowered:
        return "package"
    if "pyversions" in lowered or re.search(
        r"/badge/(?:python|java|\.net|go|node|c\+\+|c%2b|rust|"
        r"cmake|dotnet)",
        lowered,
    ):
        return "runtime"
    if "workflows" in lowered or "build" in lowered or "actions" in lowered:
        return "ci"
    if "contributors" in lowered:
        return "contributors"
    if "issues" in lowered:
        return "issues"
    if "license" in lowered:
        return "license"
    if "status" in lowered:
        return "status"
    return "other"


def _prose_paragraphs(lines: Sequence[Line]) -> list[str]:
    """Visible prose paragraphs: not code, heading, table, HTML tag line, nor inside details."""
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            paragraphs.append(" ".join(current))
            current.clear()

    for line in lines:
        text = line.text.strip()
        if (
            line.code
            or line.details
            or not text
            or text.startswith(("#", "|", "<", "---", "![", "[!["))
        ):
            flush()
            continue
        if re.match(r"^(?:[-*+]|\d+[.)])\s+", text):
            flush()
            text = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", text)
            if text.startswith("["):
                continue
        current.append(text)
    flush()
    return paragraphs


def _plain(text: str) -> str:
    text = _LINK.sub(lambda m: m.group(1), text)
    text = re.sub(r"[*_]{1,3}", "", text)
    return text.replace("`", "")


def sentence_lengths(paragraphs: Sequence[str]) -> list[int]:
    lengths = []
    for paragraph in paragraphs:
        for sentence in _SENTENCE_SPLIT.split(_plain(paragraph)):
            words = sentence.split()
            if len(words) >= 5:
                lengths.append(len(words))
    return lengths


def _percentile(values: Sequence[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))] if ordered else 0


def _relative_targets(links: Sequence[str]) -> list[str]:
    targets = []
    for link in links:
        if not link or link in ("…", "...") or link.startswith(("#", "mailto:")):
            continue  # an ellipsis in a link position is documentation text, not a link
        if re.match(r"^[a-z][a-z0-9+.\-]*:", link, re.I):
            continue
        targets.append(unquote(link.split("#", 1)[0].split("?", 1)[0]))
    return [t for t in targets if t]


def features(text: str, tree: Path | None = None) -> dict[str, Any]:
    """The flat feature record of one README. ``tree`` is the repository checkout, used only to
    test relative links; without it ``dead_relative_links`` is ``None``."""
    text = text.replace("\r\n", "\n")
    lines = scan(text)
    heads = _headings(lines)
    h1s = [h for h in heads if h[1] == 1]
    h2s = [h for h in heads if h[1] == 2]
    h2_names = [h[2] for h in h2s]
    first_h2 = h2s[0][0] if h2s else len(lines) + 1
    out: dict[str, Any] = {
        "lines": len(lines),
        "visible_lines": _visible_lines(text),
        "h1_count": len(h1s),
        "h1_text": h1s[0][2] if h1s else None,
        "h1_canonical": bool(
            h1s
            and re.match(
                r"^Aspose\.[A-Za-z0-9]+ FOSS for (?:\.NET|Node\.js|[A-Za-z0-9+#]+)$", h1s[0][2]
            )
        ),
        "h2": h2_names,
    }
    present = {name: name in h2_names for name in STANDARD_H2}
    out["standard_h2_present"] = present
    out["ten_sections_present"] = sum(1 for name in TEN_SECTIONS if present[name])
    order = [name for name in STANDARD_H2 if present[name]]
    positions = [h2_names.index(name) for name in order]
    out["standard_order_inversions"] = sum(
        1
        for i in range(len(positions))
        for j in range(i + 1, len(positions))
        if positions[i] > positions[j]
    )
    out["extra_h2"] = [name for name in h2_names if name not in STANDARD_H2]

    # Navigation
    nav = _section(lines, heads, "Navigation")
    nav_targets = [t for t in _links(nav) if t.startswith("#")]
    out["navigation"] = bool(nav) or present["Navigation"]
    out["navigation_entries"] = len(nav_targets)
    covered = {t[1:] for t in nav_targets}
    wanted = {slug(h[2]) for h in h2s if h[2] != "Navigation"}
    out["navigation_missing_h2"] = sorted(wanted - covered) if out["navigation"] else None
    if present["Navigation"] and present["At a Glance"]:
        out["navigation_before_glance"] = h2_names.index("Navigation") < h2_names.index(
            "At a Glance"
        )
    else:
        out["navigation_before_glance"] = None

    # Badges and banner (between H1 and first H2)
    head_lines = [ln for ln in lines if ln.number < first_h2]
    badges, badge_paragraphs = _badge_paragraph(head_lines, first_h2)
    out["badge_count"] = len(badges)
    out["badge_paragraphs"] = badge_paragraphs
    out["badge_kinds"] = [_badge_kind(b) for b in badges]
    ranks = [_BADGE_RANK.get(kind, 5) for kind in out["badge_kinds"]]
    out["badge_order_ok"] = ranks == sorted(ranks)
    banner_image = None
    banner_target = None
    for line in head_lines:
        if line.code:
            continue
        for _alt, image, target in _IMAGE_LINK.findall(line.text):
            if "banner" in image.lower():
                banner_image, banner_target = image, target
    out["banner"] = banner_image is not None
    out["banner_target_host"] = _host(banner_target) if banner_target else None
    out["banner_image_host"] = _host(banner_image) if banner_image else None
    out["banner_links_to_aspose"] = bool(banner_target and _is_aspose(banner_target))
    openers = _prose_paragraphs(head_lines[1:])
    opening = openers[0] if openers else ""
    out["opening_words"] = len(opening.split())
    out["opening_sentences"] = len(_SENTENCE_SPLIT.split(_plain(opening))) if opening else 0
    out["opening_starts_with_product"] = bool(h1s and opening.lower().startswith(h1s[0][2].lower()))
    out["opening_audience_phrase"] = bool(_AUDIENCE.search(opening))
    out["opening_names_license"] = bool(re.search(r"\b(?:MIT|licensed|licence|license)\b", opening))

    # At a Glance
    glance = _section(lines, heads, "At a Glance")
    glance_text = "\n".join(ln.text for ln in glance)
    if "```mermaid" in glance_text:
        form = "mermaid"
    elif _IMAGE.search(glance_text):
        form = "image"
    else:
        form = "none"
    out["glance_form"] = form if present["At a Glance"] else None
    out["glance_groups"] = (
        [g for g in ("Starting Points", "Core Capabilities", "Outputs") if g in glance_text]
        if form == "mermaid"
        else []
    )

    # Key Capabilities
    caps = [ln for ln in _section(lines, heads, "Key Capabilities") if not ln.code]
    bullets = [ln for ln in caps if re.match(r"^\s*[-*+]\s+\S", ln.text) and not ln.details]
    out["capability_bullets_visible"] = len(bullets)

    # Installation
    install = _section(lines, heads, "Installation")
    install_text = "\n".join(ln.text for ln in install)
    commands = [name for name, rx in _REGISTRY_COMMANDS if rx.search(install_text)]
    out["install_registry_commands"] = commands
    out["install_native_build"] = bool(_NATIVE_BUILD_TOKENS.search(install_text))
    out["install_source_clone"] = bool(_SOURCE_TOKENS.search(install_text))
    out["install_says_unpublished"] = bool(
        re.search(
            r"not (?:yet )?(?:been )?published|no published package|no PyPI package|"
            r"not on (?:PyPI|NuGet)|has not been published|"
            r"no (?:package|artifact|version|crate)\b[^.]{0,60}\bpublished|no versioned tag",
            install_text,
            re.IGNORECASE,
        )
    )

    # Dependencies
    out["dependencies_h3"] = [h[2] for h in heads if h[1] == 3 and _under(h, heads, "Dependencies")]
    dependency_text = "\n".join(ln.text for ln in _section(lines, heads, "Dependencies"))
    out["dependencies_zero_sentence"] = (
        "No required third-party package dependencies" in dependency_text
    )
    out["details_summaries"] = [
        re.sub(r"\s+", " ", m).strip()
        for m in re.findall(
            r"<summary>(.*?)</summary>",
            "\n".join(ln.text for ln in lines if not ln.code),
            re.DOTALL,
        )
    ]

    # Quick Start, Additional Examples
    quick = _section(lines, heads, "Quick Start")
    out["quick_start_fences"] = sum(1 for ln in quick if ln.opener)
    examples = _section(lines, heads, "Additional Examples")
    out["additional_examples_in_details"] = any(ln.details for ln in examples)
    example_h3 = [h for h in heads if h[1] == 3 and _under(h, heads, "Additional Examples")]
    out["additional_examples_h3"] = len(example_h3)
    names = [h[2].lower() for h in example_h3]
    out["numbered_example_headings"] = any(re.match(r"^example\s*\d+$", n) for n in names)
    out["duplicate_example_headings"] = len(names) - len(set(names))

    # API Reference
    api = _section(lines, heads, "API Reference")
    api_text = "\n".join(ln.text for ln in api)
    rows = [ln for ln in api if ln.text.lstrip().startswith("|") and not ln.code]
    data_rows = [
        r
        for r in rows
        if not re.match(r"^\s*\|\s*[-:| ]+\|\s*$", r.text)
        and not re.match(
            r"^\s*\|\s*(?:Class|Interface|Struct|Enumeration|Enum|Trait|Member|Type)\s*\|", r.text
        )
    ]
    out["api_in_details"] = any(ln.details for ln in api)
    api_summary = re.search(r"<summary>(.*?)</summary>", api_text, re.DOTALL)
    out["api_summary"] = re.sub(r"\s+", " ", api_summary.group(1)).strip() if api_summary else None
    out["api_rows"] = len(data_rows)
    out["api_class_description_tables"] = len(
        re.findall(r"^\s*\|\s*Class\s*\|\s*Description\s*\|", api_text, re.MULTILINE)
    )
    out["api_detailed_member_reference"] = "Detailed Member Reference" in api_text
    out["api_top_level_bullets"] = sum(
        1 for ln in api if not ln.code and re.match(r"^[-*+]\s+\S", ln.text)
    )
    boiler = 0
    for row in data_rows:
        cells = [c.strip() for c in row.text.strip().strip("|").split("|")]
        if len(cells) >= 2 and _BOILERPLATE_ROW.search(cells[1]):
            boiler += 1
    out["api_boilerplate_rows"] = boiler
    claimed = _TYPE_COUNT.findall(
        "\n".join(ln.text for ln in api if not ln.details)
        + "\n".join(ln.text for ln in _section(lines, heads, "Documentation & Resources"))
    )
    claimed_counts = sorted({int(c.replace(",", "")) for c in claimed})
    out["api_claimed_type_counts"] = claimed_counts
    out["api_count_mismatch"] = bool(
        claimed_counts and data_rows and max(claimed_counts) != len(data_rows)
    )

    # Documentation & Resources
    docs = _section(lines, heads, "Documentation & Resources")
    doc_links = _links(docs)
    hosts = {_host(u) for u in doc_links}
    out["docs_site"] = any(h.startswith("docs.aspose.") for h in hosts)
    out["kb_site"] = any(h.startswith("kb.aspose.") for h in hosts)
    out["reference_site"] = any(h.startswith("reference.aspose.") for h in hosts)
    out["issues_link"] = any(u.rstrip("/").endswith("/issues") for u in _links(lines)) or any(
        "issues" in u and u.startswith("../") for u in doc_links
    )
    out["docs_repo_relative"] = len(_relative_targets(doc_links))
    out["docs_link_texts"] = [
        m[1].strip()
        for ln in docs
        if not ln.code
        for m in _LINK.finditer(_CODE_SPAN.sub("", ln.text))
    ]

    # Scope and Enterprise Edition
    scope = _section(lines, heads, "Scope and Limitations")
    scope_text = "\n".join(ln.text for ln in scope if not ln.code)
    out["scope_bullets"] = sum(
        1 for ln in scope if re.match(r"^\s*[-*+]\s+\S", ln.text) and not ln.code
    )
    prose_text = "\n".join(ln.text for ln in lines if not ln.code)
    editions = re.findall(r"Enterprise Edition", prose_text)
    out["enterprise_mentions"] = len(editions)
    out["enterprise_in_scope"] = "Enterprise Edition" in scope_text
    enterprise_link = re.search(r"\[([^\]]*Enterprise Edition[^\]]*)\]\(([^)\s]+)\)", prose_text)
    out["enterprise_anchor"] = enterprise_link.group(1) if enterprise_link else None
    out["enterprise_url"] = enterprise_link.group(2) if enterprise_link else None
    flat = re.sub(r"\s+", " ", scope_text)
    if re.search(r"(?:don't|does not|do not) apply to \[", flat):
        out["enterprise_shape"] = "dont_apply"
    elif re.search(r"apply only to .{0,80}(?:don't|do not) carry over to \[", flat):
        out["enterprise_shape"] = "apply_only"
    elif re.search(r"\bsee \[[^\]]*Enterprise Edition", flat):
        out["enterprise_shape"] = "see_for"
    elif enterprise_link:
        out["enterprise_shape"] = "other"
    else:
        out["enterprise_shape"] = None
    scope_prose = [ln.text.strip() for ln in scope if ln.text.strip() and not ln.code]
    last_paragraph: list[str] = []
    for ln in reversed(scope):
        if ln.code:
            break
        if ln.text.strip():
            last_paragraph.append(ln.text)
        elif last_paragraph:
            break
    out["enterprise_closes_scope"] = bool(
        scope_prose and "Enterprise Edition" in "\n".join(last_paragraph)
    )
    out["enterprise_anchor_full_featured"] = bool(
        enterprise_link and enterprise_link.group(1).lower().startswith("full-featured")
    )
    out["banned_edition_names"] = len(_BANNED_EDITION.findall(prose_text))
    out["commercial_substitute_mentions"] = len(_COMMERCIAL_SUBSTITUTE.findall(prose_text))
    out["opening_free_open_source"] = bool(
        re.search(r"\bfree,? open[- ]source\b|\bopen[- ]source\b", opening, re.IGNORECASE)
    )

    # Aspose links
    all_links = [u for u in _links(lines) if _is_aspose(u)]
    out["aspose_links_total"] = len(all_links)
    out["aspose_links_distinct"] = len(set(all_links))
    out["aspose_domains"] = sorted(
        {_host(u).split(".", 1)[-1] if _host(u).count(".") > 1 else _host(u) for u in all_links}
    )
    out["aspose_links_by_kind"] = {
        kind: sum(1 for u in all_links if _host(u).startswith(prefix))
        for kind, prefix in (
            ("products", "products."),
            ("docs", "docs."),
            ("kb", "kb."),
            ("reference", "reference."),
            ("forum", "forum."),
        )
    }
    out["forum_links"] = sum(1 for u in _links(lines) if _host(u).startswith("forum.aspose"))
    out["aspose_before_first_h2"] = sum(
        1 for ln in head_lines for _a, _i, t in _IMAGE_LINK.findall(ln.text) if _is_aspose(t)
    ) + sum(
        1
        for ln in head_lines
        if not ln.code
        for t in _LINK.findall(_IMAGE_LINK.sub("", ln.text))
        if _is_aspose(t[1])
    )

    # Other standard sections
    out["third_party_h2"] = "Third-Party Notices" in h2_names
    out["project_structure_h2"] = "Project Structure" in h2_names
    out["feature_showcase_h2"] = "Feature Showcase" in h2_names
    license_body = [ln for ln in _section(lines, heads, "License") if not ln.code]
    license_text = " ".join(ln.text.strip() for ln in license_body if ln.text.strip())
    out["license_section"] = present["License"]
    out["license_prose"] = bool(re.search(r"licensed under (?:the )?(?:\[)?[A-Z]", license_text))
    out["license_permissions_sentence"] = "permits use" in license_text.lower()
    out["license_bare_link"] = bool(
        license_text and re.fullmatch(r"\[[^\]]*\]\([^)]*\)\.?", license_text.strip())
    )
    out["license_copyright_line"] = bool(
        re.search(r"copyright\s*(?:\(c\)|©|\d{4})", license_text, re.IGNORECASE)
    )

    # Tone
    visible_paragraphs = _prose_paragraphs(lines)
    lengths = sentence_lengths(visible_paragraphs)
    out["sentences_measured"] = len(lengths)
    out["sentence_mean"] = round(statistics.mean(lengths), 1) if lengths else None
    out["sentence_median"] = statistics.median(lengths) if lengths else None
    out["sentence_p90"] = _percentile(lengths, 0.9) if lengths else None
    out["sentence_max"] = max(lengths) if lengths else None
    prose = "\n".join(
        _CODE_SPAN.sub("", ln.text)
        for ln in lines
        if not ln.code and not ln.details and not ln.text.lstrip().startswith("|")
    )
    out["emoji"] = len(_EMOJI.findall("\n".join(ln.text for ln in lines if not ln.code)))
    out["first_person_words"] = len(_FIRST_PERSON.findall(prose))
    out["second_person_words"] = len(_SECOND_PERSON.findall(prose))
    out["marketing_words"] = len(_MARKETING.findall(prose))
    out["em_dashes"] = prose.count("—")

    # Defect detectors
    out["second_h1"] = len(h1s) > 1
    scrubbed_lines = [_CODE_SPAN.sub("", ln.text) for ln in lines if not ln.code]
    opens = sum(len(re.findall(r"<details\b", t, re.IGNORECASE)) for t in scrubbed_lines)
    closes = sum(len(re.findall(r"</details>", t, re.IGNORECASE)) for t in scrubbed_lines)
    out["details_opened"] = opens
    out["details_closed"] = closes
    out["unclosed_details"] = opens != closes
    out["fences_without_language"] = sum(
        1 for ln in lines if ln.opener and not ln.text.strip().strip("`~").strip()
    )
    out["unquoted_pip_specifier"] = bool(
        _PIP_UNQUOTED.search("\n".join(ln.text for ln in lines if ln.code))
    )
    out["heading_level_jumps"] = sum(1 for prev, cur in pairwise(heads) if cur[1] - prev[1] > 1)
    empty = 0
    for earlier, later in pairwise(heads):
        between = [
            ln.text.strip()
            for ln in lines
            if earlier[0] < ln.number < later[0] and ln.text.strip() not in ("", "---")
        ]
        if not between and later[1] <= earlier[1]:
            empty += 1
    out["empty_headings"] = empty
    titles = [(h[1], h[2].lower()) for h in heads if h[1] > 1]
    out["duplicate_headings"] = len(titles) - len(set(titles))
    every_link = _links(lines)
    out["absolute_self_blob_links"] = sum(
        1
        for u in every_link
        if re.match(r"^https://github\.com/[^/]+/[^/]+/blob/(?:main|master)/", u)
    )
    relative = _relative_targets(every_link)
    out["relative_links"] = len(relative)
    out["agent_file_links"] = sum(
        1 for t in relative if re.search(r"(?:^|/)(?:agents|claude)\.md$", t, re.IGNORECASE)
    )
    if tree is not None:
        out["dead_relative_links"] = sorted(
            {
                t
                for t in relative
                if not (tree / t).exists() and not (tree / t.lstrip("./")).exists()
            }
        )
    else:
        out["dead_relative_links"] = None
    out["placeholder_ellipsis_links"] = sum(1 for u in every_link if u in ("…", "..."))
    return out


def _under(
    head: tuple[int, int, str, bool], heads: Sequence[tuple[int, int, str, bool]], parent: str
) -> bool:
    """True when ``head`` falls under the H2 named ``parent``."""
    owner = None
    for candidate in heads:
        if candidate[0] > head[0]:
            break
        if candidate[1] == 2:
            owner = candidate[2]
    return owner == parent
