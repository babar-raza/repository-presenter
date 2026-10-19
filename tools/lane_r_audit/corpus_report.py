"""Corpus catch rates: M6d (the deterministic gates), the reference detectors, false positives.

Reads the committed cases, runs every deterministic detector over each (the reference detectors on
the text, BC-04 and BC-14 on the pinned bundle), and reports per class and half the cases, the
catches and the exact lower bound. The reviewer (M6r) is never run here.

BC-04 costs about a second a case, so the gate half runs in worker processes, one bundle at a time
(each worker reads the pinned bundles once). The result does not depend on the worker count.
"""

from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from . import baseline_gates, corpus
from .pinned import load_pins, read_bundles

WORKERS = max(1, min(8, (os.cpu_count() or 2) - 1))


def _gate_chunk(directory_and_ids: tuple[str, list[str]]) -> dict[str, dict[str, bool]]:
    directory, ids = directory_and_ids
    bundles = {b.pin.directory: b for b in read_bundles(load_pins())}
    wanted = set(ids)
    out: dict[str, dict[str, bool]] = {}
    for case in corpus.load_cases():
        if case.id in wanted:
            outcomes = baseline_gates.gate_outcomes(case, bundles[directory])
            out[case.id] = {gate: o.caught for gate, o in outcomes.items()}
    return out


def gate_results(cases: list[corpus.Case]) -> dict[str, dict[str, bool]]:
    chunks: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        if case.positive and case.level != "ledger":
            chunks[case.bundle].append(case.id)
    results: dict[str, dict[str, bool]] = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for part in pool.map(_gate_chunk, sorted(chunks.items())):
            results.update(part)
    return results


def report_all() -> dict[str, Any]:
    cases = corpus.load_cases()
    reference = {case.id: corpus.evaluate(case) for case in cases}
    gates = gate_results(cases)
    gate = {
        case_id: {g: corpus.Outcome(caught, False) for g, caught in row.items()}
        for case_id, row in gates.items()
    }
    document = corpus.report(cases, reference, gate)
    document["cases"] = len(cases)
    document["by_origin"] = _counts(cases, "origin")
    document["by_class"] = _counts([c for c in cases if c.positive], "cls")
    document["by_half"] = _counts(cases, "split")
    document["caught_by_origin"] = _caught_by_origin(cases, reference, gate)
    return document


def _caught_by_origin(
    cases: list[corpus.Case],
    reference: dict[str, dict[str, corpus.Outcome]],
    gate: dict[str, dict[str, corpus.Outcome]],
) -> dict[str, dict[str, int]]:
    """Per origin: positive cases, caught by a reference detector, caught by a gate.

    The mutants are written from templates the reference detectors were also written against, so
    their reference rate is not independent evidence; the traced and hand-found origins are the
    unbiased rows (real sealed defects, found before the detectors existed).
    """
    table: dict[str, dict[str, int]] = defaultdict(lambda: {"cases": 0, "reference": 0, "gates": 0})
    for case in cases:
        if not case.positive or case.level == "ledger":
            continue
        row = table[case.origin]
        row["cases"] += 1
        row["reference"] += corpus.reference_caught(case, reference.get(case.id, {}))
        row["gates"] += any(o.caught for o in gate.get(case.id, {}).values())
    return dict(sorted(table.items()))


def _counts(cases: list[corpus.Case], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        value = getattr(case, key)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
