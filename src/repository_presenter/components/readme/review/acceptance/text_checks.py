"""Deterministic predicates over a candidate README, used by the acceptance profile's ``text``
evaluators. Each predicate returns PASS, FAIL, or NOT_APPLICABLE; a disqualifier triggers on FAIL.

Every predicate reads the README text only. Fenced code is excluded wherever the rule concerns
prose or structure. The phrase lists and thresholds are PROPOSALS (see ``profile.py``): they
implement the wording of ``plans/idea.md`` at its cited lines and await owner ratification.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class TextResult:
    outcome: Outcome
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Line:
    number: int
    text: str
    code: bool
    opener: bool = False
    info: str = ""


_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)")
_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_BADGE_HINTS = ("shields.io", "badge")
_ASPOSE = re.compile(r"aspose\.(?:com|org)", re.IGNORECASE)
_BANNED_EDITIONS = re.compile(
    r"commercial edition|on-?premises?\s+edition|paid version|full version", re.IGNORECASE
)
_NARRATION = (
    re.compile(r"source[- ]revisions?", re.IGNORECASE),
    re.compile(r"isolated[- ]build", re.IGNORECASE),
    re.compile(r"network polic(?:y|ies)", re.IGNORECASE),
    re.compile(r"registry receipts?", re.IGNORECASE),
    re.compile(r"provider calls?", re.IGNORECASE),
    re.compile(r"evidence collectors?", re.IGNORECASE),
    re.compile(r"validation status", re.IGNORECASE),
)
_ADDITIONAL_COMMENTARY = (
    re.compile(r"syntax[- ]check", re.IGNORECASE),
    re.compile(r"static[- ]api[- ]check", re.IGNORECASE),
    re.compile(r"non[- ]execution", re.IGNORECASE),
    re.compile(r"source[- ]revision", re.IGNORECASE),
    re.compile(r"inventory", re.IGNORECASE),
)
_EXAMPLE_NUMBERED = re.compile(r"^example\s*\d+$", re.IGNORECASE)
_VISIBLE_REQUIRED = frozenset(
    {"installation", "key capabilities", "scope and limitations", "development and testing"}
)
_LICENSE_MIN_PROSE_WORDS = 5


def scan(readme: str) -> list[Line]:
    """Every line with its 1-based number, marked as code when it lies inside a fence."""
    lines: list[Line] = []
    fence: tuple[str, int] | None = None
    for number, text in enumerate(readme.splitlines(), start=1):
        match = _FENCE.match(text)
        if fence is None:
            if match:
                fence = (match.group(1)[0], len(match.group(1)))
                lines.append(Line(number, text, True, opener=True, info=match.group(2).strip()))
            else:
                lines.append(Line(number, text, False))
        else:
            closing = (
                match is not None
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and not match.group(2).strip()
            )
            if closing:
                fence = None
            lines.append(Line(number, text, True))
    return lines


def _prose(lines: Sequence[Line]) -> list[Line]:
    return [line for line in lines if not line.code]


def _headings(lines: Sequence[Line]) -> list[tuple[Line, int, str]]:
    found = []
    for line in _prose(lines):
        match = _HEADING.match(line.text)
        if match:
            found.append((line, len(match.group(1)), match.group(2).strip()))
    return found


def _is_badge_image(url: str) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in _BADGE_HINTS)


def _badge_rows(lines: Sequence[Line]) -> list[list[str]]:
    """Maximal runs of consecutive prose lines that carry at least one badge image. A blank line
    or a fence ends a run, as a Markdown paragraph does. Banners and other images do not count."""
    rows: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        urls = [url for _, url in _IMAGE.findall(line.text)] if not line.code else []
        badges = [url for url in urls if _is_badge_image(url)]
        if badges:
            current.extend(badges)
            continue
        if current:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    return rows


def single_h1(lines: Sequence[Line]) -> TextResult:
    h1 = [line.number for line, level, _ in _headings(lines) if level == 1]
    if len(h1) == 1:
        return TextResult(Outcome.PASS, (f"one H1 at line {h1[0]}",))
    return TextResult(Outcome.FAIL, (f"{len(h1)} H1 headings at lines {h1}",))


def single_badge_row(lines: Sequence[Line]) -> TextResult:
    rows = _badge_rows(lines)
    urls = [url for row in rows for url in row]
    duplicates = sorted({url for url in urls if urls.count(url) > 1})
    if len(rows) > 1 or duplicates:
        return TextResult(
            Outcome.FAIL,
            (f"{len(rows)} badge rows", f"duplicated badges: {duplicates}" if duplicates else ""),
        )
    return TextResult(Outcome.PASS, (f"{len(rows)} badge row(s), no duplicated badge",))


def edition_name(lines: Sequence[Line]) -> TextResult:
    text = "\n".join(line.text for line in _prose(lines))
    banned = sorted({match.group(0).lower() for match in _BANNED_EDITIONS.finditer(text)})
    if banned:
        return TextResult(Outcome.FAIL, (f"non-canonical edition names: {banned}",))
    if _ASPOSE.search(text) or "Enterprise Edition" in text:
        return TextResult(Outcome.PASS, ("Enterprise Edition is the only edition name",))
    return TextResult(Outcome.NOT_APPLICABLE, ("no Aspose.com product is referenced",))


def implementation_label(lines: Sequence[Line]) -> TextResult:
    hits = [
        line.number for line in _prose(lines) if "preserved repository details" in line.text.lower()
    ]
    if hits:
        return TextResult(Outcome.FAIL, (f"implementation label at lines {hits}",))
    return TextResult(Outcome.PASS, ("no implementation label",))


def assurance_narration(lines: Sequence[Line]) -> TextResult:
    found: list[str] = []
    for line in _prose(lines):
        for pattern in _NARRATION:
            if pattern.search(line.text):
                found.append(f"line {line.number}: {pattern.pattern}")
    if found:
        return TextResult(Outcome.FAIL, tuple(found))
    return TextResult(Outcome.PASS, ("no assurance narration in the visitor text",))


def other_platforms_section(lines: Sequence[Line]) -> TextResult:
    hits = [
        line.number
        for line, _, text in _headings(lines)
        if re.match(r"other platforms\b", text, re.IGNORECASE)
    ]
    if hits:
        return TextResult(Outcome.FAIL, (f"'Other platforms' heading at lines {hits}",))
    return TextResult(Outcome.PASS, ("no 'Other platforms' section",))


def promotion_after_product(lines: Sequence[Line]) -> TextResult:
    """The FOSS explanation comes first: no Aspose destination may appear between the H1 and the
    opening paragraph (a banner link counts - a ratification point), nor inside the opening
    paragraph's first sentence. A link later in the opening paragraph follows the explanation."""
    prose = _prose(lines)
    h1_index = next((i for i, line in enumerate(prose) if _is_h1(line.text)), None)
    if h1_index is None:
        return TextResult(Outcome.NOT_APPLICABLE, ("no H1, so no opening paragraph",))
    start = h1_index + 1
    while start < len(prose) and (not prose[start].text.strip() or "[![" in prose[start].text):
        start += 1
    if start >= len(prose) or _HEADING.match(prose[start].text):
        return TextResult(Outcome.NOT_APPLICABLE, ("no opening paragraph before a heading",))
    end = start
    while end < len(prose) and prose[end].text.strip() and not _HEADING.match(prose[end].text):
        end += 1
    opening = " ".join(line.text for line in prose[start:end])
    first_sentence = re.split(r"(?<=[.!?])\s", opening, maxsplit=1)[0]
    hits = [line.number for line in prose[h1_index:start] if _ASPOSE.search(line.text)]
    if _ASPOSE.search(first_sentence):
        hits.append(prose[start].number)
    if hits:
        return TextResult(Outcome.FAIL, (f"Aspose destination before the explanation: {hits}",))
    return TextResult(Outcome.PASS, ("the explanation precedes any Aspose destination",))


def _is_h1(text: str) -> bool:
    match = _HEADING.match(text)
    return bool(match and len(match.group(1)) == 1)


def license_prose(lines: Sequence[Line]) -> TextResult:
    headings = _headings(lines)
    index = next((i for i, (_, _, text) in enumerate(headings) if text.lower() == "license"), None)
    if index is None:
        return TextResult(Outcome.FAIL, ("no License heading",))
    body = _section_body(lines, headings[index][0].number)
    prose = _LINK.sub(" ", "\n".join(body))
    words = re.findall(r"[A-Za-z]+", prose)
    if len(words) >= _LICENSE_MIN_PROSE_WORDS:
        return TextResult(Outcome.PASS, (f"{len(words)} prose words outside links",))
    return TextResult(Outcome.FAIL, (f"only {len(words)} prose words outside links",))


def third_party_notices(lines: Sequence[Line]) -> TextResult:
    headings = _headings(lines)
    match = next(
        (
            line
            for line, _, text in headings
            if re.sub(r"[\s-]+", " ", text.lower()) in ("third party notices", "third party notice")
        ),
        None,
    )
    if match is None:
        return TextResult(Outcome.NOT_APPLICABLE, ("no third-party notices heading",))
    body = _section_body(lines, match.number)
    for text in body:
        for label, target in _LINK.findall(text):
            if label and not label.startswith("`") and not target.lower().startswith(("http", "/")):
                return TextResult(Outcome.PASS, (f"relative link with normal text: {target}",))
    return TextResult(Outcome.FAIL, ("no repository-relative link with normal link text",))


def visible_core_sections(lines: Sequence[Line]) -> TextResult:
    collapsed: list[str] = []
    inside = False
    for line in _prose(lines):
        lowered = line.text.lower()
        if "<details" in lowered:
            inside = True
        if inside:
            match = _HEADING.match(line.text)
            if match and match.group(2).strip().lower() in _VISIBLE_REQUIRED:
                collapsed.append(f"{match.group(2).strip()} at line {line.number}")
        if "</details>" in lowered:
            inside = False
    if collapsed:
        return TextResult(Outcome.FAIL, tuple(collapsed))
    return TextResult(Outcome.PASS, ("no required core section is collapsed",))


def example_headings(lines: Sequence[Line]) -> TextResult:
    """Inside the Additional Examples section: no 'Example N' heading, no reused heading, and no
    internal verification commentary. Numbered headings are checked document-wide."""
    headings = _headings(lines)
    problems: list[str] = []
    section = next(
        (
            line.number
            for line, level, text in headings
            if level <= 2 and text.lower() == "additional examples"
        ),
        None,
    )
    if section is None:
        numbered = [line.number for line, _, text in headings if _EXAMPLE_NUMBERED.match(text)]
        if not numbered:
            return TextResult(Outcome.NOT_APPLICABLE, ("no additional examples",))
        return TextResult(Outcome.FAIL, (f"numbered example headings at lines {numbered}",))
    end = _section_end(lines, section)
    seen: dict[str, int] = {}
    for line, _, text in headings:
        if line.number <= section or (end is not None and line.number >= end):
            continue
        if _EXAMPLE_NUMBERED.match(text):
            problems.append(f"numbered example heading at line {line.number}: {text}")
        key = text.lower()
        if key in seen:
            problems.append(f"heading reused at line {line.number}: {text}")
        seen.setdefault(key, line.number)
    for line in _section_lines(lines, section):
        for pattern in _ADDITIONAL_COMMENTARY:
            if pattern.search(line.text):
                problems.append(f"verification commentary at line {line.number}")
    if problems:
        return TextResult(Outcome.FAIL, tuple(problems))
    return TextResult(Outcome.PASS, ("task-named examples, no verification commentary",))


def _section_end(lines: Sequence[Line], heading_number: int) -> int | None:
    for line in _prose(lines):
        if line.number <= heading_number:
            continue
        match = _HEADING.match(line.text)
        if match and len(match.group(1)) <= 2:
            return line.number
    return None


def fences_and_spacing(lines: Sequence[Line]) -> TextResult:
    problems: list[str] = []
    blank_run = 0
    for line in lines:
        if line.opener and not line.info:
            problems.append(f"fence without a language at line {line.number}")
        if not line.code and not line.text.strip():
            blank_run += 1
            if blank_run == 2:
                problems.append(f"repeated empty-line run ending at line {line.number}")
        else:
            blank_run = 0
    if problems:
        return TextResult(Outcome.FAIL, tuple(problems))
    return TextResult(Outcome.PASS, ("every fence has a language; no repeated empty-line run",))


def _section_body(lines: Sequence[Line], heading_number: int) -> list[str]:
    body: list[str] = []
    for line in _prose(lines):
        if line.number <= heading_number:
            continue
        if _HEADING.match(line.text):
            break
        body.append(line.text)
    return body


def _section_lines(lines: Sequence[Line], heading_number: int) -> list[Line]:
    body: list[Line] = []
    for line in _prose(lines):
        if line.number <= heading_number:
            continue
        match = _HEADING.match(line.text)
        if match and len(match.group(1)) <= 2:
            break
        body.append(line)
    return body


TEXT_PREDICATES: dict[str, Callable[[Sequence[Line]], TextResult]] = {
    "single_h1": single_h1,
    "single_badge_row": single_badge_row,
    "edition_name": edition_name,
    "implementation_label": implementation_label,
    "assurance_narration": assurance_narration,
    "other_platforms_section": other_platforms_section,
    "promotion_after_product": promotion_after_product,
    "license_prose": license_prose,
    "third_party_notices": third_party_notices,
    "visible_core_sections": visible_core_sections,
    "example_headings": example_headings,
    "fences_and_spacing": fences_and_spacing,
}
