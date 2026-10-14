"""Controlled defects injected into a conformant README, each expected to be found exactly once (e).

The strongest idempotence test there is (metamorphic, T6 of the second first-principles analysis):
start from a README the lane leaves alone (``x*``, a fixed point of the lane), inject **one**
defect, and require that the lane

* reports exactly the edit that defect calls for, from exactly the detector that owns it;
* changes nothing else (every other non-diagram line of the mutated text is still a line of the
  output), and
* for a defect with a single inverse (a version, a link target, a heading level, a closing tag, a
  diagram body) gives back ``x*`` byte for byte.

A mutation is a registered function ``Subject -> Mutated | None``; ``None`` means this README has no
site for it (no ``<details>`` block to unclose, no relative link to break), which is not a failure
and is counted as not applicable. Adding a mutation is adding a function and its row in the test,
never a branch here (AGENTS.md: registries, not a central if/elif).

Facts. Two mutations change what the README says about a fact, so they carry the facts that make
the defect a defect: a dead link brings the ``CONTRADICTED`` link fact the extractor would have
written, and a false version needs the registry's published version, which sealed bundles recorded
before that fact existed, so ``with_published_version`` adds it from the manifest version (marked
synthetic in its evidence).

Pure given the lane: no network, no model.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from repository_presenter.components.readme.validation import claims as bc14
from repository_presenter.components.readme_correction.detectors import claims as claim_detectors
from repository_presenter.components.readme_correction.model import Context, ReadmeLine
from repository_presenter.components.readme_diagram.rebuild import mermaid_fences
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.package_registry import PUBLISHED_VERSION_FACT_ID
from repository_presenter.core.registry.models import RegistryEntry
from tools.idempotence.lane import Lane, LaneRun, correction_lane
from tools.idempotence.retention import line_retention

_H1 = re.compile(r"^#(?!#)[ \t]+\S")
_H2 = re.compile(r"^##(?!#)[ \t]+\S")
_CODE_SPAN = re.compile(r"`[^`]*`")
#: The sections the correction lane can render from facts alone (``detectors/sections.py``), in the
#: order a dropped one is tried: the shortest and least entangled first.
REFILLABLE = ("license", "installation", "dependencies")
#: The version a false-version mutation writes; any release the registry cannot hold.
WRONG_VERSION = "0.0.1"
NL = "\n"


@dataclass(frozen=True)
class Subject:
    """A conformant README and everything a mutation needs to defect it consistently."""

    entry: RegistryEntry
    text: str  # x*: a fixed point of the lane, so it carries none of the defects below
    original: str  # x: the README the lane started from (the vertical diagram lives here)
    facts: FactsDocument
    tree: tuple[str, ...] = ("README.md",)

    def context(self, text: str | None = None) -> Context:
        return Context(self.entry, self.facts, self.text if text is None else text, self.tree)


@dataclass(frozen=True)
class Mutated:
    kind: str
    detector: str  # the detector that must find it
    text: str
    site: str  # where, for a human
    facts: FactsDocument  # the facts the lane runs with (the subject's, plus any the defect needs)
    tree: tuple[str, ...]
    restores: bool  # the lane's output must equal the subject's text byte for byte
    edits: int = 1  # how many edits of ``detector`` the one defect calls for


Mutator = Callable[[Subject], "Mutated | None"]
MUTATORS: dict[str, Mutator] = {}


def mutator(kind: str) -> Callable[[Mutator], Mutator]:
    def register(function: Mutator) -> Mutator:
        if kind in MUTATORS:
            raise ValueError(f"mutation {kind!r} is registered twice")
        MUTATORS[kind] = function
        return function

    return register


def with_published_version(facts: FactsDocument) -> FactsDocument:
    """``facts`` plus a ``package:published_version`` fact from the manifest version when none
    exists (sealed bundles written before that fact existed lack it)."""
    ids = {fact.id: fact for fact in facts.facts}
    version = ids.get("package:version")
    if PUBLISHED_VERSION_FACT_ID in ids or version is None:
        return facts
    synthetic = Fact(
        PUBLISHED_VERSION_FACT_ID,
        "package",
        version.value,
        (Evidence("synthetic:registry", "the manifest version, standing in for the registry"),),
    )
    return replace(facts, facts=(*facts.facts, synthetic))


# --- the mutations ----------------------------------------------------------------------------


@mutator("second_h1")
def second_h1(subject: Subject) -> Mutated | None:
    """A section heading promoted to a second H1."""
    ctx = subject.context()
    first = next((ln for ln in ctx.lines if not ln.in_fence and _H1.match(ln.text)), None)
    if first is None:
        return None
    # The last H2 is the least entangled: a template section heading earlier on is judged by name.
    heading = next(
        (
            ln
            for ln in reversed(ctx.lines)
            if not ln.in_fence and ln.number > first.number and _H2.match(ln.text)
        ),
        None,
    )
    if heading is None:
        return None
    text = ctx.readme[: heading.start] + ctx.readme[heading.start + 1 :]
    return Mutated(
        "second_h1",
        "second_h1",
        text,
        f"line {heading.number}: {heading.text[:50]!r} loses one #",
        subject.facts,
        subject.tree,
        restores=True,
    )


def _details_blocks(ctx: Context) -> list[tuple[int, int]]:
    """``(open line, close line)`` of each balanced ``<details>`` block outside fences."""
    stack: list[int] = []
    blocks: list[tuple[int, int]] = []
    for line in ctx.lines:
        if line.in_fence:
            continue
        text = _CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line.text)
        events = sorted(
            [(m.start(), True) for m in re.finditer(r"<details\b", text, re.IGNORECASE)]
            + [(m.start(), False) for m in re.finditer(r"</details\s*>", text, re.IGNORECASE)]
        )
        for _position, opening in events:
            if opening:
                stack.append(line.number)
            elif stack:
                blocks.append((stack.pop(), line.number))
    return blocks


@mutator("unclosed_details")
def unclosed_details(subject: Subject) -> Mutated | None:
    """A ``</details>`` removed, in the one layout whose inverse is unambiguous: the closing tag
    alone on its line, a blank line either side, the next heading an H2 and no H2 inside."""
    ctx = subject.context()
    lines = ctx.lines
    for opened, closed in reversed(_details_blocks(ctx)):
        tag = lines[closed - 1]
        if tag.text.strip().lower() != "</details>" or closed < 2 or closed >= len(lines) - 1:
            continue
        before, after, heading = lines[closed - 2], lines[closed], lines[closed + 1]
        if before.text.strip() or after.text.strip() or heading.in_fence:
            continue
        if not _H2.match(heading.text):
            continue
        if any(
            not ln.in_fence and _H2.match(ln.text) for ln in lines[opened : closed - 1]
        ):  # an H2 inside the block would be where the lane closes it
            continue
        cut_from, cut_to = tag.start, heading.start  # "</details>", NL, NL: tag and one blank line
        text = ctx.readme[:cut_from] + ctx.readme[cut_to:]
        return Mutated(
            "unclosed_details",
            "unclosed_details",
            text,
            f"line {closed}: the </details> closing the block opened on line {opened}",
            subject.facts,
            subject.tree,
            restores=True,
        )
    return None


@mutator("vertical_diagram")
def vertical_diagram(subject: Subject) -> Mutated | None:
    """The At a Glance diagram drawn the way the maintainers drew it (stacked, clipping)."""
    now = mermaid_fences(subject.text.splitlines(keepends=True))
    then = mermaid_fences(subject.original.splitlines(keepends=True))
    if not now or len(now) != len(then):
        return None
    lines = subject.text.splitlines(keepends=True)
    for fresh, old in reversed(list(zip(now, then, strict=True))):
        if fresh.body == old.body:
            continue
        text = "".join([*lines[: fresh.first], old.body, *lines[fresh.last :]])
        return Mutated(
            "vertical_diagram",
            "at_a_glance_diagram",
            text,
            f"line {fresh.first + 1}: the diagram body is the live README's own",
            subject.facts,
            subject.tree,
            restores=True,
        )
    return None


@mutator("false_version")
def false_version(subject: Subject) -> Mutated | None:
    """The published version of the package, written wrong where the README attaches it to the
    package name (an install command, a dependency line)."""
    facts = with_published_version(subject.facts)
    ctx = Context(subject.entry, facts, subject.text, subject.tree)
    identity, published = ctx.supported("package:name"), ctx.supported(PUBLISHED_VERSION_FACT_ID)
    if identity is None or published is None:
        return None
    expected = bc14._normal_version(published.value)
    names = bc14._names(identity.value)
    for line in ctx.lines:
        for start, end, shown in claim_detectors._attached(line, names):
            if claim_detectors._same_version(shown, expected):
                text = ctx.readme[:start] + WRONG_VERSION + ctx.readme[end:]
                return Mutated(
                    "false_version",
                    "claim_version",
                    text,
                    f"line {line.number}: {shown} becomes {WRONG_VERSION}",
                    facts,
                    subject.tree,
                    restores=ctx.readme[start:end] == expected,
                )
    return None


_RELATIVE = re.compile(r"^line (\d+); relative; text '(.*)'$")


def _relative_targets(facts: FactsDocument) -> dict[str, Fact]:
    out: dict[str, Fact] = {}
    for fact in facts.by_kind("link_target"):
        first = fact.evidence[0].detail or ""
        if fact.polarity == "SUPPORTED" and _RELATIVE.match(first):
            out[fact.value] = fact
    return out


@mutator("dead_link")
def dead_link(subject: Subject) -> Mutated | None:
    """A relative link whose target the tree does not hold (the case of its file name changed), with
    the ``CONTRADICTED`` link fact the extractor writes for it."""
    targets = _relative_targets(subject.facts)
    if not targets:
        return None
    ctx = Context(subject.entry, subject.facts, subject.text, subject.tree)
    for line in ctx.lines:
        if line.in_fence:
            continue
        for target, fact in targets.items():
            broken = target.swapcase()
            if (
                broken == target
                or not re.fullmatch(r"[\w./-]+", target)
                or target.startswith((".", "/"))
                or line.text.count(f"]({target})") != 1
            ):
                continue
            offset = line.start + line.text.index(f"]({target})") + 2
            text = ctx.readme[:offset] + broken + ctx.readme[offset + len(target) :]
            shown = _RELATIVE.match(fact.evidence[0].detail or "")
            label = shown.group(2) if shown else ""
            contradicted = Fact(
                fact.id,
                "link_target",
                broken,
                (
                    Evidence("README.md", f"line {line.number}; relative; text '{label}'"),
                    Evidence("README.md", f"MISSING: tree does not contain {broken}"),
                ),
                polarity="CONTRADICTED",
            )
            kept = tuple(f for f in subject.facts.facts if f.id != fact.id)
            return Mutated(
                "dead_link",
                "broken_link",
                text,
                f"line {line.number}: ({target}) becomes ({broken})",
                replace(subject.facts, facts=(*kept, contradicted)),
                subject.tree,
                restores=True,
            )
    return None


def _section_range(lines: Sequence[ReadmeLine], title: str) -> tuple[int, int] | None:
    """``(first line index, end index)`` of the H2 section named ``title``, outside fences."""
    for index, line in enumerate(lines):
        if line.in_fence or not _H2.match(line.text):
            continue
        if line.text.lstrip("# \t").strip().lower() != title:
            continue
        end = next(
            (
                j
                for j in range(index + 1, len(lines))
                if not lines[j].in_fence and _H2.match(lines[j].text)
            ),
            len(lines),
        )
        return index, end
    return None


def dropped_section_candidates(subject: Subject) -> list[Mutated]:
    """Each refillable template section removed whole, heading to the next H2. None without facts:
    a section is rendered from facts alone, so with none there is nothing to find it with."""
    ctx = subject.context()
    out: list[Mutated] = []
    if not subject.facts.facts:
        return out
    for title in REFILLABLE:
        found = _section_range(ctx.lines, title)
        if found is None:
            continue
        first, end = found
        cut_from = ctx.lines[first].start
        cut_to = ctx.lines[end].start if end < len(ctx.lines) else len(ctx.readme)
        text = ctx.readme[:cut_from] + ctx.readme[cut_to:]
        out.append(
            Mutated(
                f"dropped_section:{title}",
                "missing_sections",
                text,
                f"lines {first + 1}-{end}: the {title} section",
                subject.facts,
                subject.tree,
                restores=False,
            )
        )
    return out


@mutator("dropped_section")
def dropped_section(subject: Subject) -> Mutated | None:
    """The first refillable template section the subject has (License, Installation, Dependencies);
    ``run_mutation`` tries the others when the facts cannot refill this one."""
    candidates = dropped_section_candidates(subject)
    return replace(candidates[0], kind="dropped_section") if candidates else None


# --- running one ------------------------------------------------------------------------------


@dataclass
class Outcome:
    kind: str
    applicable: bool
    site: str = ""
    expected: str = ""
    found: list[str] = field(default_factory=list)  # detectors of the edits the lane reported
    extra_detectors: list[str] = field(default_factory=list)
    restored: bool | None = None  # None when the mutation has no single inverse
    confined: bool = True
    lost: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def detected(self) -> bool:
        return self.applicable and not self.problems


def _judge(subject: Subject, mutated: Mutated, run: LaneRun) -> Outcome:
    outcome = Outcome(mutated.kind, True, mutated.site, mutated.detector, run.detectors)
    outcome.extra_detectors = [d for d in run.detectors if d != mutated.detector]
    own = [e for e in run.edits if e.detector == mutated.detector]
    if not own:
        outcome.problems.append(f"{mutated.detector} did not find the defect ({mutated.site})")
    elif mutated.restores and len(own) != mutated.edits:
        outcome.problems.append(f"{mutated.detector} made {len(own)} edit(s), not {mutated.edits}")
    if outcome.extra_detectors:
        outcome.problems.append(f"other detectors fired: {', '.join(outcome.extra_detectors)}")
    lines = line_retention(mutated.text, run.text, run.input_spans)
    outcome.lost = len(lines.lost)
    outcome.confined = not lines.lost
    if lines.lost:
        outcome.problems.append(
            f"{len(lines.lost)} untouched line(s) lost, first: {lines.lost[0].text[:60]!r}"
        )
    if mutated.restores:
        outcome.restored = run.text == subject.text
        if not outcome.restored:
            outcome.problems.append("the corrected text is not the conformant text it came from")
    return outcome


def run_mutation(
    subject: Subject,
    kind: str,
    lane: Callable[[Mutated], Lane] | None = None,
) -> Outcome:
    """Apply mutation ``kind`` to ``subject`` and judge what the lane does about it.

    ``lane`` builds the lane to run for a given mutation (its facts and tree differ); the default
    is the correction lane's bare detector pass, which is what "the detectors find exactly those"
    asks about (settling drops an edit only to protect a validation check, which is a different
    question)."""
    build = lane or (lambda m: correction_lane(subject.entry, m.facts, tree=m.tree, settle=False))
    candidates = dropped_section_candidates(subject) if kind == "dropped_section" else None
    if candidates is None:
        single = MUTATORS[kind](subject)
        candidates = [] if single is None else [single]
    if not candidates:
        return Outcome(kind, applicable=False)
    last: Outcome | None = None
    for mutated in candidates:
        mutated = replace(mutated, kind=kind)
        outcome = _judge(subject, mutated, build(mutated)(mutated.text))
        if outcome.detected:
            return outcome
        last = outcome
    assert last is not None
    return last


def run_all(
    subject: Subject,
    kinds: Sequence[str] | None = None,
    lane: Callable[[Mutated], Lane] | None = None,
) -> list[Outcome]:
    return [run_mutation(subject, kind, lane) for kind in (kinds or sorted(MUTATORS))]


@dataclass
class Combined:
    """Several defects injected into one README, and what the lane did about all of them."""

    applied: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    expected: dict[str, int] = field(default_factory=dict)  # detector -> edits it must make
    found: dict[str, int] = field(default_factory=dict)
    restored: bool | None = None  # the output is the conformant text (every defect had an inverse)
    confined: bool = True
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.applied) and not self.problems


def run_combined(
    subject: Subject,
    kinds: Sequence[str] | None = None,
    lane: Callable[[Mutated], Lane] | None = None,
) -> Combined:
    """Inject every mutation in ``kinds`` that still has a site, one on top of another, and require
    the lane's edits to be exactly the ones those defects call for.

    Each mutation is checked as it is added: the lane run on the text so far must report exactly the
    edits of the mutations already accepted plus its own. A defect whose site an earlier one
    destroyed (the section that held the ``<details>`` block was dropped) is skipped and named, so
    what remains is always an exact expectation, never a loosened one."""
    build = lane or (lambda m: correction_lane(subject.entry, m.facts, tree=m.tree, settle=False))
    result = Combined()
    current = subject
    expected: Counter[str] = Counter()
    last: Mutated | None = None
    # A dead link's fact names the line the link is on, so it is injected last: every defect that
    # moves lines has been injected by then and the line is the one in the final text.
    for kind in sorted(kinds or MUTATORS, key=lambda k: (k == "dead_link", k)):
        if kind == "dropped_section":
            options = dropped_section_candidates(current)
        else:
            single = MUTATORS[kind](current)
            options = [] if single is None else [single]
        if not options:
            result.skipped[kind] = "no site"
            continue
        for mutated in options:
            trial = replace(current, text=mutated.text, facts=mutated.facts, tree=mutated.tree)
            found = Counter(build(mutated)(trial.text).detectors)
            want = expected + Counter({mutated.detector: mutated.edits})
            if mutated.restores:
                accepted = found == want
            else:  # a refilled section makes one or two edits (the section and its contents item)
                accepted = set(found) == set(want) and all(
                    found[d] == want[d] for d in want if d != mutated.detector
                )
            if accepted:
                expected = found if not mutated.restores else want
                current, last = trial, mutated
                result.applied.append(kind)
                break
        else:
            result.skipped[kind] = "its site conflicts with an earlier defect or is not found"
    result.expected = dict(expected)
    if last is None:
        return result
    run = build(last)(current.text)
    result.found = dict(Counter(run.detectors))
    if result.found != result.expected:
        result.problems.append(f"expected edits {result.expected}, the lane made {result.found}")
    lines = line_retention(current.text, run.text, run.input_spans)
    result.confined = not lines.lost
    if lines.lost:
        result.problems.append(f"{len(lines.lost)} untouched line(s) lost")
    inverse = all(kind != "dropped_section" for kind in result.applied)
    if inverse:
        result.restored = run.text == subject.text
        if not result.restored:
            result.problems.append("the corrected text is not the conformant text it came from")
    return result


def make_subject(
    entry: RegistryEntry,
    original: str,
    facts: FactsDocument,
    tree: Sequence[str] | None = None,
) -> Subject | None:
    """The conformant ``x*`` of ``original`` under ``facts`` as a mutation subject, or None when the
    lane does not reach a fixed point on it (the fixed-point gate reports that, not this).

    The tree defaults to the README and every relative link target the facts found resolvable, so a
    dead-link mutation has a file to point back at."""
    document = with_published_version(facts)
    paths = tuple(tree) if tree is not None else ("README.md", *sorted(_relative_targets(document)))
    lane = correction_lane(entry, document, tree=paths, settle=False)
    first = lane(original)
    again = lane(first.text)
    if again.edits or again.text != first.text:
        return None
    return Subject(entry, first.text, original, document, paths)
