"""Typed records of the README correction path.

A correction is a patch to the live upstream README, never a regenerated candidate. It is made of
``Edit`` records, each a literal span of the original text replaced by a replacement the verified
facts dictate (or, for a missing section, a pure insertion the existing deterministic renderer
wrote). The shape forbids the harm the path must never do: an edit that rewrites an unrelated
maintainer sentence cannot be constructed, because a ``FALSE_CLAIM_FIX`` or ``BROKEN_LINK`` span is
one line and short, and a ``MISSING_SECTION`` span is empty (docs/REPOSITORY_LAYOUT.md section 2).

Nothing here consults a model. The path makes zero provider calls by construction.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from repository_presenter.components.readme.review.acceptance.text_checks import scan
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry

FALSE_CLAIM_FIX = "FALSE_CLAIM_FIX"
MISSING_SECTION = "MISSING_SECTION"
BROKEN_LINK = "BROKEN_LINK"
#: Markup the README itself shows broken (a second H1, a ``<details>`` never closed): evidence is
#: the README's own line, not a fact, and the fix is one heading marker or one closing tag.
STRUCTURE_FIX = "STRUCTURE_FIX"
#: Verified information the live README lacks, added to a section it already has (a build and
#: test command, an install form, a link to a file the tree holds, the published-version badge).
#: A pure insertion: no maintainer byte is replaced, no heading is introduced.
MISSING_INFO = "MISSING_INFO"
#: The README's own At a Glance diagram, redrawn: every label, group title and edge unchanged, the
#: body between the fence markers replaced by the drawing ``components/readme_diagram`` writes. The
#: one correction that replaces several lines; evidence is the README's own fence (a locator).
DIAGRAM_FIX = "DIAGRAM_FIX"
#: The closed set of correction kinds; nothing outside it can be applied or proposed.
EDIT_KINDS: frozenset[str] = frozenset(
    {FALSE_CLAIM_FIX, MISSING_SECTION, BROKEN_LINK, STRUCTURE_FIX, MISSING_INFO, DIAGRAM_FIX}
)
#: Why a detector that could have edited reported its candidate instead (typed, closed).
REPORT_ONLY_REASONS: dict[str, str] = {
    "RE_ENABLE_CONDITION_UNMET": "the detector is report-only until its re-enable condition holds",
    "ALREADY_SHOWN": "the README already shows an equivalent of the candidate",
    "CONTRADICTS_README_PUBLICATION_CLAIM": (
        "the README itself says the package is not published; an insertion that asserts "
        "publication would contradict a sentence the maintainers wrote"
    ),
    "NEEDS_INSTALL_FIRST": "the candidate command needs an install the evidence does not name",
    "NOT_IN_VERIFIED_CHAIN": (
        "the command is not a step of the one CI job (or project file) whose steps were verified"
    ),
    "NO_BUILD_RECEIPT": "the commands could not be run on a clean clone with the tools at hand",
    "BUILD_RECEIPT_FAILED": "the commands failed, or did not finish, on a clean clone",
    "DOCS_HOLDS_NO_DOCUMENTATION": "the docs directory holds no documentation files",
    "WOULD_FAIL_VALIDATION": "applying it would make a validation check fail that the live passes",
    "INTERNAL_NARRATION": "the text to insert carries internal-assurance narration",
    "OVERLAPS_ANOTHER_CORRECTION": "it overlaps another correction",
    "DIAGRAM_LABEL_NOT_PORTABLE": "a label holds & < or >, which no Mermaid 11.4-12.1 draws",
    "DIAGRAM_CONTRACT_FAILS": "the redrawn diagram would fail the At a Glance contract anew",
}
#: A diagram body is a few dozen lines, never more than this.
MAX_DIAGRAM = 8000
#: A line that opens or closes a fenced block (an invisible Mermaid link, ``a ~~~ b``, is not one).
_FENCE_LINE = re.compile(r"^[ \t]{0,3}(?:`{3,}|~{3,})", re.MULTILINE)
#: An addition is a few lines, never a rewrite of a section.
MAX_ADDITION = 4000
#: A one-line fix touches a few words, never a sentence the maintainers wrote.
MAX_SPAN = 200
KIND_FIELD = "kind"
KIND_CORRECTION = "correction"
#: A bundle of live-anchored operations (``live_ops.py``): the second, separately typed family.
KIND_LIVE_ANCHORED = "live_anchored"


class InvalidEditError(ValueError):
    """An edit that violates the closed shape of its kind; never constructed, never applied."""


def _opens_heading(text: str) -> bool:
    """Whether ``text`` has an H1 or H2 heading line outside a fenced block: an addition may carry
    a sub-heading (H3 and deeper) of the section it joins, never a section of its own."""
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            inside = not inside
        elif not inside and (line.startswith("# ") or line.startswith("## ")):
            return True
    return False


@dataclass(frozen=True)
class Edit:
    """One literal replacement of ``original`` (``text[start:end]``) by ``replacement``.

    ``fact_ids`` are the facts that dictate the replacement (or, for ``BROKEN_LINK``, that record
    the target missing); their polarities are looked up in the facts document when the bundle is
    written, so the record cannot disagree with the evidence."""

    kind: str
    detector: str
    start: int
    end: int
    original: str
    replacement: str
    fact_ids: tuple[str, ...]
    rationale: str
    order: int = 0  # tie-break between insertions at one offset (shell order)
    #: ``README.md:<line>`` (a STRUCTURE_FIX) or ``tree:<path>`` (a file the pinned tree holds).
    locators: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in EDIT_KINDS:
            raise InvalidEditError(f"unknown correction kind {self.kind!r}")
        if self.kind == STRUCTURE_FIX:
            if not self.locators:
                raise InvalidEditError(f"{self.detector}: a structure fix cites the README line")
        elif self.kind in {MISSING_INFO, MISSING_SECTION}:
            if not (self.fact_ids or self.locators):
                raise InvalidEditError(f"{self.detector}: an addition cites a fact or a tree path")
        elif self.kind == DIAGRAM_FIX:
            if not self.locators:
                raise InvalidEditError(f"{self.detector}: a diagram fix cites the README line")
        elif not self.fact_ids:
            raise InvalidEditError(f"{self.detector}: an edit needs at least one evidence fact")
        if self.replacement == self.original:
            raise InvalidEditError(f"{self.detector}: the replacement equals the original")
        if self.kind == STRUCTURE_FIX and self.start == self.end:
            if self.original or self.replacement.strip() != "</details>":
                raise InvalidEditError(f"{self.detector}: the only insertion is a closing tag")
        elif self.kind == MISSING_INFO:
            if self.start != self.end or self.original or not self.replacement.strip():
                raise InvalidEditError(f"{self.detector}: an addition is inserted, never replaces")
            if len(self.replacement) > MAX_ADDITION or _opens_heading(self.replacement):
                raise InvalidEditError(f"{self.detector}: an addition is short and has no heading")
        elif self.kind == MISSING_SECTION:
            if self.start != self.end or self.original:
                raise InvalidEditError(f"{self.detector}: a section is inserted, never replaces")
            if not self.replacement.lstrip("\n").startswith("## "):
                raise InvalidEditError(f"{self.detector}: an inserted section starts at an H2")
        elif self.kind == DIAGRAM_FIX:
            if not self.original or not self.replacement or self.start == self.end:
                raise InvalidEditError(f"{self.detector}: a diagram fix replaces a diagram body")
            if any(_FENCE_LINE.search(text) for text in (self.original, self.replacement)):
                raise InvalidEditError(f"{self.detector}: a diagram fix stays inside one fence")
            if max(len(self.original), len(self.replacement)) > MAX_DIAGRAM:
                raise InvalidEditError(f"{self.detector}: a diagram body is not this long")
        else:
            if not self.original or "\n" in self.original or len(self.original) > MAX_SPAN:
                raise InvalidEditError(
                    f"{self.detector}: a {self.kind} replaces one short line fragment, "
                    f"not {self.original[:40]!r}"
                )
            if "\n" in self.replacement:
                raise InvalidEditError(f"{self.detector}: a {self.kind} stays on one line")


@dataclass(frozen=True)
class Finding:
    """Something a detector noticed that no deterministic edit can honestly fix.

    A finding is reported to the maintainers and never applied: an unverifiable claim is not
    "corrected", and a broken link with no unique repair is not deleted."""

    detector: str
    line: int
    text: str
    reason: str
    fact_ids: tuple[str, ...] = ()
    #: set when the finding is a skipped *edit*: why a detector that could have edited did not
    #: (one of ``REPORT_ONLY_REASONS``); the bundle lists these under ``report_only``.
    report_only_reason: str = ""
    #: the exact text the skipped edit would have inserted (empty when it was a replacement)
    candidate: str = ""
    #: what must hold before the detector may edit (the re-enable condition)
    re_enable: str = ""
    locators: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.report_only_reason and self.report_only_reason not in REPORT_ONLY_REASONS:
            raise InvalidEditError(
                f"{self.detector}: {self.report_only_reason!r} is not a report-only reason"
            )


@dataclass(frozen=True)
class ReadmeLine:
    number: int  # 1-based
    start: int  # offset of the first character in the README text
    text: str  # without the line ending
    in_fence: bool

    @property
    def end(self) -> int:
        return self.start + len(self.text)


@dataclass(frozen=True)
class Context:
    """Everything a detector reads: the live README, the verified facts, the tracked tree."""

    entry: RegistryEntry
    facts: FactsDocument
    readme: str
    tree_paths: tuple[str, ...]
    readme_path: str = "README.md"
    #: Version 2 of how the Requirements additions read: a ``;``-joined MSBuild
    #: ``TargetFrameworks`` value is stated as the list it is ("Targets `a` and `b`.", not pasted as
    #: a requirement), and a dependency group of one short line joins the section's list instead of
    #: taking an H3 of its own. A bundle written before records no ``rendering`` in
    #: ``corrections.json``, and the gate re-derives it the way it was written, so a sealed bundle
    #: keeps verifying.
    requirements_v2: bool = True

    @functools.cached_property
    def lines(self) -> tuple[ReadmeLine, ...]:
        raw = self.readme.splitlines(keepends=True)
        flags = [line.code for line in scan(self.readme)]
        lines: list[ReadmeLine] = []
        offset = 0
        for index, chunk in enumerate(raw):
            body = chunk.rstrip("\r\n")
            lines.append(ReadmeLine(index + 1, offset, body, flags[index]))
            offset += len(chunk)
        return tuple(lines)

    @functools.cached_property
    def by_id(self) -> dict[str, Fact]:
        return {fact.id: fact for fact in self.facts.facts}

    def fact(self, fact_id: str) -> Fact | None:
        return self.by_id.get(fact_id)

    def supported(self, fact_id: str) -> Fact | None:
        fact = self.by_id.get(fact_id)
        return fact if fact is not None and fact.polarity == "SUPPORTED" else None


@dataclass(frozen=True)
class DetectorResult:
    edits: tuple[Edit, ...] = ()
    findings: tuple[Finding, ...] = ()


Detector = Callable[[Context], DetectorResult]


@dataclass
class CorrectionResult:
    """What ``engine.correct`` returns: the corrected text, every applied edit with the span it
    now occupies, what was left alone, and the proof that nothing else changed."""

    original: str
    corrected: str
    edits: list[Edit] = field(default_factory=list)
    output_spans: list[tuple[int, int]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
