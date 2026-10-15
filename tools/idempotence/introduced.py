"""What a candidate says that neither the live README nor the facts said (metric c).

Every prose atom of the candidate (sentence or list item) is traced to a source, in this order:

1. ``live``  - it is a live atom, or reworded from one (the same thresholds as ``retention``);
2. ``facts`` - at least ``FACT_THRESHOLD`` of its content words are in the vocabulary of the
   verified facts (their values and attributes; ``inherited_unit`` facts are the live README's own
   text and do not count as a second source);
3. otherwise it is **introduced**: text a model or a template wrote that no source supports.

An introduced atom is flagged ``llm`` when it is a sentence of an authored content unit
(``content_units.json`` in a sealed bundle), so a review can tell model prose from template prose.
Without the units the flag is unknown (``None``), never guessed.

Pure function of its inputs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from tools.idempotence.atoms import Atom, Atoms, atomise, sentences, toks
from tools.idempotence.retention import REWORD_THRESHOLD, SCATTER_THRESHOLD

FACT_THRESHOLD = 0.85
LLM_THRESHOLD = 0.8


@dataclass(frozen=True)
class IntroducedAtom:
    atom: Atom
    llm: bool | None  # True: a sentence of an authored unit; False: not; None: units not given


@dataclass
class IntroducedReport:
    total: int = 0  # candidate prose atoms
    from_live: int = 0
    from_facts: int = 0
    introduced: list[IntroducedAtom] = field(default_factory=list)
    units_known: bool = False

    @property
    def share(self) -> float:
        return len(self.introduced) / self.total if self.total else 0.0

    @property
    def llm(self) -> int:
        return sum(1 for item in self.introduced if item.llm)

    @property
    def llm_share(self) -> float | None:
        return self.llm / self.total if self.units_known and self.total else None


def fact_texts(facts: Iterable[dict[str, object]]) -> list[str]:
    """The text of each fact worth tracing a sentence to (everything but the live README's own)."""
    out: list[str] = []
    for fact in facts:
        if fact.get("kind") == "inherited_unit":
            continue
        parts = [str(fact.get("value", ""))]
        attributes = fact.get("attributes")
        if isinstance(attributes, dict):
            parts.extend(str(value) for value in attributes.values())
        out.append(" ".join(parts))
    return out


def _index(atoms: Sequence[Atom]) -> tuple[dict[str, list[int]], set[str]]:
    sets = [toks(atom.text) for atom in atoms]
    index: dict[str, list[int]] = defaultdict(list)
    for position, tokens in enumerate(sets):
        for token in tokens:
            index[token].append(position)
    vocabulary: set[str] = set().union(*sets) if sets else set()
    return index, vocabulary


def _sourced_in_live(
    atom: Atom, keys: set[str], index: dict[str, list[int]], vocabulary: set[str]
) -> bool:
    if atom.key in keys:
        return True
    tokens = toks(atom.text)
    if len(tokens) < 2:
        return False
    hits: Counter[int] = Counter()
    for token in tokens:
        hits.update(index.get(token, ()))
    if hits and hits.most_common(1)[0][1] / len(tokens) >= REWORD_THRESHOLD:
        return True
    return len(tokens & vocabulary) / len(tokens) >= SCATTER_THRESHOLD


def introduced_text(
    live: str | Atoms,
    candidate: str | Atoms,
    facts: Sequence[str] = (),
    authored: Sequence[str] | None = None,
) -> IntroducedReport:
    """Trace every prose atom of ``candidate``; ``facts`` are texts from :func:`fact_texts` and
    ``authored`` the texts of the authored content units (None when unknown)."""
    live_atoms = atomise(live) if isinstance(live, str) else live
    cand_atoms = atomise(candidate) if isinstance(candidate, str) else candidate
    live_prose = live_atoms.prose()
    live_index, live_vocabulary = _index(live_prose)
    live_keys = {atom.key for atom in live_prose}
    fact_vocabulary: set[str] = set()
    for text in facts:
        fact_vocabulary |= toks(text)
    unit_sets: list[frozenset[str]] = []
    for text in authored or ():
        unit_sets.extend(toks(part) for part in sentences(text))
    unit_index: dict[str, list[int]] = defaultdict(list)
    for position, tokens in enumerate(unit_sets):
        for token in tokens:
            unit_index[token].append(position)

    report = IntroducedReport(units_known=authored is not None)
    for atom in cand_atoms.prose():
        report.total += 1
        if _sourced_in_live(atom, live_keys, live_index, live_vocabulary):
            report.from_live += 1
            continue
        tokens = toks(atom.text)
        if tokens and len(tokens & fact_vocabulary) / len(tokens) >= FACT_THRESHOLD:
            report.from_facts += 1
            continue
        flag: bool | None = None
        if authored is not None:
            hits: Counter[int] = Counter()
            for token in tokens:
                hits.update(unit_index.get(token, ()))
            flag = bool(
                tokens and hits and hits.most_common(1)[0][1] / len(tokens) >= LLM_THRESHOLD
            )
        report.introduced.append(IntroducedAtom(atom, flag))
    return report
