"""The labeled corpus: cases, the dev/test split, differential catch and exact lower bounds.

A case is one defect (or one clean negative) in the setting of a pinned bundle:

* ``injected`` is the defective text and ``clean`` its twin: a unit's prose (``level`` "unit"), a
  README fragment ("readme": ``clean`` is a snippet of the sealed README and ``injected`` the text
  that replaces it) or a ledger row ("ledger");
* ``cited`` and ``facts`` carry the fixtures a detector needs (the cited facts' kind and value),
  ``inherited`` the live units a polarity case reads, so the corpus is reviewable without the
  bundles; the registry probe readings the case relies on are stored in ``facts``;
* ``positive`` is False for a clean negative: ``injected`` equals ``clean`` and a detector that
  fires on it is a false positive.

Catch is differential: a detector catches a case when it fires on ``injected`` and not on
``clean``. The split into a dev half and a test half is a fixed hash of the repository name; the
test half is never used to tune a detector.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import detectors
from .detectors import REGISTRY, Detector, Subject
from .pinned import REPO_ROOT

CORPUS_DIR = REPO_ROOT / "data" / "lane_r_corpus"
CASES_DIR = CORPUS_DIR / "cases"
SPLIT_PATH = CORPUS_DIR / "split.json"
SPLIT_SALT = "lane-r-corpus-v1:"
ORIGINS = ("traced", "hand_found", "ledger", "mutant", "clean_negative")
ALPHA = 0.05


def split_of(repository: str) -> str:
    """``dev`` or ``test`` by a fixed hash of the repository name (never by a judgment)."""
    digest = hashlib.sha256((SPLIT_SALT + repository).encode("utf-8")).digest()
    return "test" if digest[0] % 2 else "dev"


@dataclass(frozen=True)
class Case:
    id: str
    origin: str
    cls: str
    repository: str
    bundle: str  # the pinned bundle directory
    level: str
    injected: str
    clean: str
    section: str = ""
    slot: str = ""
    positive: bool = True
    cited: tuple[str, ...] = ()
    facts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    inherited: Mapping[str, str] = field(default_factory=dict)
    ledger: Mapping[str, Any] = field(default_factory=dict)
    readme_edit: tuple[str, str] | None = None
    excerpt: str = ""
    source: str = ""

    @property
    def split(self) -> str:
        return split_of(self.repository)

    def subject(self, variant: str) -> Subject:
        text = self.injected if variant == "injected" else self.clean
        ledger = dict(self.ledger)
        if self.level == "ledger" and variant == "clean":
            ledger = dict(ledger.get("clean", {"printed": True}))
        elif self.level == "ledger":
            ledger.pop("clean", None)
        return Subject(
            text,
            self.level,
            self.section,
            self.slot,
            self.cited,
            self.facts,
            self.inherited,
            ledger,
        )


def case_from_json(row: Mapping[str, Any]) -> Case:
    edit = row.get("readme_edit")
    return Case(
        id=row["id"],
        origin=row["origin"],
        cls=row["class"],
        repository=row["repository"],
        bundle=row["bundle"],
        level=row["level"],
        injected=row["injected"],
        clean=row["clean"],
        section=row.get("section", ""),
        slot=row.get("slot", ""),
        positive=row.get("positive", True),
        cited=tuple(row.get("cited", ())),
        facts=row.get("facts", {}),
        inherited=row.get("inherited", {}),
        ledger=row.get("ledger", {}),
        readme_edit=None if edit is None else (edit[0], edit[1]),
        excerpt=row.get("excerpt", ""),
        source=row.get("source", ""),
    )


def case_to_json(case: Case) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": case.id,
        "origin": case.origin,
        "class": case.cls,
        "repository": case.repository,
        "bundle": case.bundle,
        "level": case.level,
        "injected": case.injected,
        "clean": case.clean,
        "positive": case.positive,
        "excerpt": case.excerpt,
        "source": case.source,
    }
    for key, value in (
        ("section", case.section),
        ("slot", case.slot),
        ("cited", list(case.cited)),
        ("facts", dict(case.facts)),
        ("inherited", dict(case.inherited)),
        ("ledger", dict(case.ledger)),
        ("readme_edit", list(case.readme_edit) if case.readme_edit else None),
    ):
        if value:
            row[key] = value
    return row


def load_cases(directory: Path = CASES_DIR) -> list[Case]:
    cases: list[Case] = []
    for path in sorted(directory.glob("*.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(case_from_json(row) for row in rows)
    return cases


def split_document(cases: Iterable[Case], pins_repositories: Iterable[str]) -> dict[str, Any]:
    """The committed split file: repository -> half, for every pinned repository and case."""
    repositories = sorted({*pins_repositories, *(case.repository for case in cases)})
    return {
        "schema_version": 1,
        "rule": "sha256(salt + repository)[0] % 2 == 1 -> test, else dev",
        "salt": SPLIT_SALT,
        "halves": {repository: split_of(repository) for repository in repositories},
    }


# --- exact binomial bound -----------------------------------------------------------------------


def lower_bound(successes: int, trials: int, alpha: float = ALPHA) -> float:
    """The one-sided exact (Clopper-Pearson) lower confidence bound on a success probability."""
    if trials == 0 or successes == 0:
        return 0.0
    if successes == trials:
        return float(alpha ** (1.0 / trials))

    def upper_tail(p: float) -> float:  # P(X >= successes | p)
        return sum(
            math.comb(trials, k) * p**k * (1.0 - p) ** (trials - k)
            for k in range(successes, trials + 1)
        )

    low, high = 0.0, 1.0
    for _ in range(80):
        mid = (low + high) / 2.0
        if upper_tail(mid) < alpha:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


# --- evaluating detectors on cases --------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    """Per detector: fires on the injected text, fires on the clean twin, the added findings."""

    injected: bool
    clean: bool
    findings: tuple[str, ...] = ()

    @property
    def caught(self) -> bool:
        return self.injected and not self.clean


def evaluate(case: Case, detector_list: Iterable[Detector] | None = None) -> dict[str, Outcome]:
    """Outcome of every deterministic reference detector on one case (gates: ``gate_outcomes``)."""
    chosen = list(detector_list) if detector_list is not None else detectors.reference_detectors()
    outcomes: dict[str, Outcome] = {}
    for detector in chosen:
        found = detector.run(case.subject("injected"))
        twin = detector.run(case.subject("clean"))
        outcomes[detector.id] = Outcome(bool(found), bool(twin), tuple(found[:3]))
    return outcomes


def relevant(case: Case, detector: Detector) -> bool:
    return case.cls in detector.classes


def reference_caught(case: Case, outcomes: Mapping[str, Outcome]) -> bool:
    """A positive case is caught when a reference detector of its class catches it."""
    return any(
        outcome.caught
        for detector_id, outcome in outcomes.items()
        if relevant(case, REGISTRY[detector_id])
    )


def false_positive(case: Case, outcomes: Mapping[str, Outcome]) -> bool:
    """A clean negative is flagged by any reference detector."""
    return any(outcome.injected for outcome in outcomes.values())


@dataclass
class ClassRow:
    cases: int = 0
    caught: int = 0

    def to_json(self) -> dict[str, Any]:
        rate = self.caught / self.cases if self.cases else 0.0
        return {
            "cases": self.cases,
            "caught": self.caught,
            "rate": round(rate, 4),
            "lower_bound_95": round(lower_bound(self.caught, self.cases), 4),
        }


def report(
    cases: Iterable[Case],
    reference: Mapping[str, Mapping[str, Outcome]],
    gate: Mapping[str, Mapping[str, Outcome]] | None = None,
) -> dict[str, Any]:
    """Per class and half: cases, caught by reference detectors, caught by the gates (M6d),
    exact lower bounds; the false-positive count on clean negatives."""
    table: dict[str, dict[str, dict[str, ClassRow]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(ClassRow))
    )
    negatives = {"cases": 0, "flagged": 0, "flagged_ids": []}
    for case in cases:
        outcomes = reference.get(case.id, {})
        if not case.positive:
            negatives["cases"] += 1
            if false_positive(case, outcomes):
                negatives["flagged"] += 1
                negatives["flagged_ids"].append(case.id)  # type: ignore[attr-defined]
            continue
        for half in (case.split, "all"):
            row = table[case.cls][half]["reference"]
            row.cases += 1
            row.caught += reference_caught(case, outcomes)
            if gate is not None:
                grow = table[case.cls][half]["gates"]
                grow.cases += 1
                grow.caught += any(o.caught for o in gate.get(case.id, {}).values())
    return {
        "classes": {
            cls: {
                half: {kind: row.to_json() for kind, row in kinds.items()}
                for half, kinds in sorted(halves.items())
            }
            for cls, halves in sorted(table.items())
        },
        "clean_negatives": negatives,
    }
