"""The idempotence gate over the committed corpus: what CI runs and what an operator can re-run.

For every README of ``data/idempotence/corpus.json`` the live-first correction lane is run on the
README and on its own output, and three things must hold (``lane.fixed_point``):

* the second run is a no-op (``P(P(x)) = P(x)``, no edit reported);
* no non-diagram live line is lost unless a reported edit covers it (retention 100% of the rest);
* every changed line of the output belongs to a reported edit (no unexplained hunk).

Facts. The lane needs facts to correct a claim or fill a section. The corpus holds only the READMEs,
so each is run **facts-free** (the structural detectors: a second H1, an unclosed ``<details>``, the
At a Glance diagram) and, where a sealed candidate recorded facts for exactly the corpus head
revision (``candidates/<slug>/<head>/facts.json``), **with those facts** as well, which exercises
the fact-driven detectors on a real README. A README with no such facts is gated facts-free only,
and the report says which.

Pure given the committed data: no network, no model, no clock.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from repository_presenter.core.facts import FactsDocument
from tools.idempotence import corpus, lane, mutations
from tools.idempotence.corpus import Entry


@dataclass
class GateRow:
    repository: str
    head: str
    with_facts: bool
    report: lane.FixedPointReport

    @property
    def ok(self) -> bool:
        return self.report.ok


def facts_for(entry: Entry, candidates: Path | None = None) -> FactsDocument | None:
    """The sealed facts for exactly this README's revision, or None."""
    return lane.sealed_facts(entry.repository, entry.head, candidates)


def gate_entry(entry: Entry, candidates: Path | None = None, cold: bool = False) -> GateRow:
    facts = facts_for(entry, candidates)
    registered = lane.registry_entry(entry.repository)
    settled = lane.correction_lane(registered, facts)
    bare = lane.correction_lane(registered, facts, settle=False)
    report = lane.fixed_point(settled, entry.text, entry.repository, quick=bare, cold=cold)
    return GateRow(entry.repository, entry.head, facts is not None, report)


def gate(
    entries: Iterable[Entry] | None = None,
    candidates: Path | None = None,
    cold: bool = False,
    progress: Callable[[GateRow], None] | None = None,
) -> list[GateRow]:
    rows: list[GateRow] = []
    for entry in sorted(entries or corpus.load().values(), key=lambda e: e.repository):
        row = gate_entry(entry, candidates, cold)
        if progress is not None:
            progress(row)
        rows.append(row)
    return rows


@dataclass
class MutationRow:
    repository: str
    with_facts: bool
    fixed_point: bool  # the subject (x*) could be built: the lane reaches a fixed point on it
    outcomes: list[mutations.Outcome] = field(default_factory=list)
    combined: mutations.Combined | None = None  # every defect at once

    @property
    def ok(self) -> bool:
        return (
            self.fixed_point
            and all(o.detected for o in self.outcomes if o.applicable)
            and (self.combined is None or self.combined.ok or not self.combined.applied)
        )


def mutation_sweep(
    entries: Iterable[Entry], candidates: Path | None = None, kinds: Sequence[str] | None = None
) -> list[MutationRow]:
    rows: list[MutationRow] = []
    for entry in sorted(entries, key=lambda e: e.repository):
        facts = facts_for(entry, candidates)
        registered = lane.registry_entry(entry.repository)
        document = facts or FactsDocument(entry.repository, entry.head, ())
        subject = mutations.make_subject(registered, entry.text, document)
        if subject is None:
            rows.append(MutationRow(entry.repository, facts is not None, False))
            continue
        rows.append(
            MutationRow(
                entry.repository,
                facts is not None,
                True,
                mutations.run_all(subject, kinds),
                mutations.run_combined(subject, kinds),
            )
        )
    return rows


def render_gate(rows: Sequence[GateRow]) -> str:
    lines = [
        "| repository | facts | edits | hunks | +/- lines | lines kept | second run | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        r = row.report
        verdict = "ok" if row.ok else "FAIL: " + "; ".join(r.problems())[:200]
        lines.append(
            f"| {row.repository} | {'real' if row.with_facts else 'none'} "
            f"| {len(r.first.edits)} | {r.script.hunks} | +{r.script.added}/-{r.script.removed} "
            f"| {r.lines.kept}/{r.lines.eligible} "
            f"| {'no-op' if r.idempotent else 'CHANGES'} | {verdict} |"
        )
    return "\n".join(lines) + "\n"


def render_mutations(rows: Sequence[MutationRow]) -> str:
    kinds = sorted({o.kind for row in rows for o in row.outcomes})
    lines = [
        "| repository | facts | " + " | ".join(kinds) + " | all at once |",
        "|---|---|" + "---|" * (len(kinds) + 1),
    ]
    for row in rows:
        cells = []
        by_kind = {o.kind: o for o in row.outcomes}
        for kind in kinds:
            outcome = by_kind.get(kind)
            if outcome is None or not outcome.applicable:
                cells.append("n/a")
            else:
                cells.append("found" if outcome.detected else "MISSED")
        state = "real" if row.with_facts else "none"
        label = row.repository if row.fixed_point else row.repository + " (no fixed point)"
        together = row.combined
        if together is None or not together.applied:
            cells.append("n/a")
        else:
            cells.append(f"{len(together.applied)} found" if together.ok else "MISSED")
        lines.append(f"| {label} | {state} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
