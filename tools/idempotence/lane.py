"""The lanes under test, and the fixed-point measure (metric d).

A *lane* is any function from a README text to a ``LaneRun``: the text it produced and the edits it
reports having made (each a character span of its input). The live-first correction lane
(``components/readme_correction``) is one; a regeneration lane that reports no edits is another,
and the same measures judge both. Nothing here calls a model: the correction lane is model-free, and
a lane that needs the gateway must be wrapped by the caller. The regeneration lane's own
``P(P(x))`` therefore stays a production-shaped proof; offline it is judged through ``report.py``
(what a sealed candidate keeps of the live README) and the floor in tests/test_idempotence_gate.py.

Fixed point. ``P`` is idempotent on ``x`` when

* ``P(P(x)) = P(x)`` and the second run reports no edit (I3, self-application);
* two cold runs on ``x`` give the same bytes (I1, reproducibility);
* every changed line of ``P(x)`` against ``x`` belongs to a reported edit (no unexplained hunk), and
  every non-diagram line of ``x`` that no edit covers is still a line of ``P(x)``, in order (I2/T4,
  no loss);
* every reported edit cites its evidence (a fact id, or the README line or tree path it rests on).

Pure given the lane: no network, no clock.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.model import Context, CorrectionResult
from repository_presenter.components.readme_correction.settle import correct_settled
from repository_presenter.core.facts import FactsDocument, read_facts
from repository_presenter.core.registry.loader import load_registry, require_listed
from repository_presenter.core.registry.models import RegistryEntry
from tools.idempotence import corpus
from tools.idempotence.editscript import EditScript, edit_script
from tools.idempotence.retention import LineRetention, covered_lines, line_retention

NO_REVISION = "0" * 40


@dataclass(frozen=True)
class EditRecord:
    """One enumerated edit: a character span of the lane's input and what replaced it."""

    kind: str
    detector: str
    start: int
    end: int
    original: str
    replacement: str
    #: the facts and the README lines or tree paths that dictate the edit (a verified edit cites one)
    fact_ids: tuple[str, ...] = ()
    locators: tuple[str, ...] = ()

    @property
    def evidenced(self) -> bool:
        return bool(self.fact_ids or self.locators)

    @property
    def signature(self) -> tuple[str, str, str, str]:
        """Position-free identity of the edit, to compare two runs over differently placed text."""
        return (self.detector, self.kind, self.original, self.replacement)


@dataclass(frozen=True)
class LaneRun:
    text: str
    edits: tuple[EditRecord, ...] = ()
    #: where each edit's replacement sits in ``text`` (empty for a lane that cannot say)
    output_spans: tuple[tuple[int, int], ...] = ()
    #: edits a detector found and refused to apply (reported, never applied)
    unapplied: int = 0

    @property
    def input_spans(self) -> list[tuple[int, int]]:
        return [(edit.start, edit.end) for edit in self.edits]

    @property
    def detectors(self) -> list[str]:
        return sorted(edit.detector for edit in self.edits)


Lane = Callable[[str], LaneRun]


def _record(result: CorrectionResult) -> LaneRun:
    edits = tuple(
        EditRecord(
            e.kind, e.detector, e.start, e.end, e.original, e.replacement, e.fact_ids, e.locators
        )
        for e in result.edits
    )
    return LaneRun(result.corrected, edits, tuple(result.output_spans), len(result.findings))


def correction_lane(
    entry: RegistryEntry,
    facts: FactsDocument | None = None,
    *,
    tree: Sequence[str] = ("README.md",),
    settle: bool = True,
) -> Lane:
    """The live-first correction lane over ``entry`` with ``facts`` (none: the facts-free path).

    ``settle=True`` is the lane as ``correct-readme`` runs it: edits that would tip a blocking
    check the live README passes are dropped and reported. ``settle=False`` is the bare detector
    pass, for a measure that wants to see every proposed edit.
    """
    document = facts or FactsDocument(entry.repository, NO_REVISION, ())

    def run(text: str) -> LaneRun:
        ctx = Context(entry, document, text, tuple(tree))
        if settle:
            return _record(correct_settled(ctx, text.encode("utf-8"))[0])
        return _record(correct(ctx))

    return run


def registry_entry(repository: str, registry: Path | None = None) -> RegistryEntry:
    return require_listed(load_registry(registry or corpus.DEFAULT_REGISTRY), repository)


def sealed_facts(repository: str, revision: str, root: Path | None = None) -> FactsDocument | None:
    """The facts a sealed candidate recorded for exactly ``revision``, or None when none did."""
    base = (root or corpus.REPO_ROOT / "candidates") / repository.replace("/", "__") / revision
    path = base / "facts.json"
    return read_facts(path) if path.is_file() else None


@dataclass
class FixedPointReport:
    repository: str
    first: LaneRun
    second: LaneRun
    cold: LaneRun | None  # an independent run on the same input, when reproducibility was asked
    lines: LineRetention
    script: EditScript
    unexplained: list[str] = field(default_factory=list)  # changed runs no reported edit covers

    @property
    def reproducible(self) -> bool:
        return self.cold is None or (
            self.cold.text == self.first.text and self.cold.edits == self.first.edits
        )

    @property
    def idempotent(self) -> bool:
        """``P(P(x)) = P(x)`` and the second pass reports nothing to do."""
        return self.second.text == self.first.text and not self.second.edits

    @property
    def lossless(self) -> bool:
        return not self.lines.lost

    @property
    def unevidenced(self) -> list[EditRecord]:
        """Reported edits that cite neither a fact nor a README line or tree path."""
        return [edit for edit in self.first.edits if not edit.evidenced]

    @property
    def ok(self) -> bool:
        return (
            self.reproducible
            and self.idempotent
            and self.lossless
            and not self.unexplained
            and not self.unevidenced
        )

    def problems(self) -> list[str]:
        out: list[str] = []
        if not self.reproducible:
            out.append("two cold runs on the same input differ")
        if not self.idempotent:
            out.append(
                f"the second run is not a no-op ({len(self.second.edits)} edit(s): "
                f"{', '.join(self.second.detectors) or 'text changed without a reported edit'})"
            )
        out.extend(
            f"live line {lost.number} is lost with no edit covering it: {lost.text[:80]!r}"
            for lost in self.lines.lost
        )
        out.extend(self.unexplained)
        out.extend(
            f"edit by {edit.detector} cites no fact and no README line or tree path"
            for edit in self.unevidenced
        )
        return out


def _unexplained(live: str, run: LaneRun, script: EditScript) -> list[str]:
    """The changed runs of ``script`` that no reported edit accounts for.

    A run is explained when every non-blank live line it removes is covered by an edit span in the
    input and every non-blank candidate line it adds sits inside an edit's replacement in the
    output. Blank lines are interchangeable to a line diff (an insertion that begins or ends with a
    blank line can be drawn one line up or down), so they never decide it. A lane that does not
    report where its edits landed (no ``output_spans``) explains nothing it adds."""
    removed_ok = covered_lines(live, run.input_spans)
    added_ok = covered_lines(run.text, list(run.output_spans))
    live_lines = live.splitlines()
    new_lines = run.text.splitlines()
    out: list[str] = []
    for change in script.changes:
        gone = [
            n for n in range(change.live_first, change.live_last + 1) if live_lines[n - 1].strip()
        ]
        new = [
            n
            for n in range(change.candidate_first, change.candidate_last + 1)
            if new_lines[n - 1].strip()
        ]
        if all(n in removed_ok for n in gone) and all(n in added_ok for n in new):
            continue
        out.append(
            f"unexplained change: live lines {change.live_first}-{change.live_last} became "
            f"candidate lines {change.candidate_first}-{change.candidate_last}"
        )
    return out


def fixed_point(
    lane: Lane,
    text: str,
    repository: str = "",
    *,
    quick: Lane | None = None,
    cold: bool = False,
) -> FixedPointReport:
    """Run ``lane`` on ``text`` and on its own output, and measure what changed.

    ``quick`` is a cheaper lane that can only find *more* than ``lane`` does (the correction
    lane's bare detector pass finds a superset of its settled one): when it finds nothing on the
    output, ``lane`` would find nothing either, so the second pass is settled without running
    ``lane`` again. ``cold`` adds a second independent run on ``text`` to prove reproducibility."""
    first = lane(text)
    second = quick(first.text) if quick is not None else None
    if second is None or second.edits or second.text != first.text:
        second = lane(first.text)
    again = lane(text) if cold else None
    lines = line_retention(text, first.text, first.input_spans)
    script = edit_script(text, first.text)
    return FixedPointReport(
        repository, first, second, again, lines, script, _unexplained(text, first, script)
    )
