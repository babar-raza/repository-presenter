"""The ratchet: the best value of M1 to M5, M6d and M9, which may only improve (card C1, step 5).

``data/lane_r_corpus/ratchet.json`` holds the best value of each metric. CI computes the metrics
from the pinned reader and fails when any is worse than the file's value, and fails when the file
itself is worse than the one on ``origin/main`` (read with ``git show``, so a branch cannot lower
its own baseline). A waiver is a recorded owner decision: the metric, the old and the new value, the
dates it was granted and expires (at most 14 days apart), and the owner item; it excuses exactly
that move until it expires.

Two tiers: ``ledger_values`` (M1 to M5, M9: seconds) and ``gate_values`` (M6d: the corpus run of
BC-04 and BC-14 over the test half, a few minutes). Directions: M1, M6d and M9 improve upward; M2 to
M5 improve downward.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from . import corpus, corpus_report, detectors, measure
from .pinned import REPO_ROOT

RATCHET_PATH = REPO_ROOT / "data" / "lane_r_corpus" / "ratchet.json"
RATCHET_REL = "data/lane_r_corpus/ratchet.json"
HIGHER = frozenset({"M1", "M9"})
LOWER = frozenset({"M2", "M3", "M4", "M5"})
MAX_WAIVER_DAYS = 14
# defects found in sealed bundles, not written from a template: the unbiased rows
REAL_ORIGINS = ("traced", "hand_found")


def ledger_values() -> dict[str, float | int]:
    measured = measure.measure()
    return {
        "M1": measured["M1"],
        "M2": measured["M2"],
        "M3": measured["M3"],
        "M4": measured["M4"],
        "M5": measured["M5"],
        "M9": measured["M9"]["authorizable"],
    }


def gate_values() -> dict[str, Any]:
    """M6d: BC-04/BC-14 catch per class on the test half, and on the real (non-template) defects."""
    cases = corpus.load_cases()
    gates = corpus_report.gate_results(cases)
    per_class: dict[str, dict[str, int]] = {}
    real = {"caught": 0, "cases": 0}
    for case in cases:
        if not case.positive or case.level == "ledger":
            continue
        caught = any(gates.get(case.id, {}).values())
        if case.origin in REAL_ORIGINS:
            real["cases"] += 1
            real["caught"] += caught
        if case.split == "test" and case.cls in detectors.FLOORS:
            row = per_class.setdefault(case.cls, {"caught": 0, "cases": 0})
            row["cases"] += 1
            row["caught"] += caught
    return {"per_class_test": dict(sorted(per_class.items())), "real_defects": real}


def current_values() -> dict[str, Any]:
    values: dict[str, Any] = dict(ledger_values())
    values["M6d"] = gate_values()
    return values


def _rate(row: Mapping[str, int]) -> float:
    return row["caught"] / row["cases"] if row["cases"] else 0.0


def flatten(values: Mapping[str, Any]) -> dict[str, float]:
    """One number per metric key; M6d keys are ``M6d.<class>`` and ``M6d.real``."""
    flat: dict[str, float] = {}
    for key, value in values.items():
        if key == "M6d":
            rows = {**value["per_class_test"], "real": value["real_defects"]}
            for name, row in rows.items():
                # the rate, and the counts under it: a cell that shrinks (fewer cases) or catches
                # fewer cannot hide behind an unchanged or rising rate
                flat[f"M6d.{name}"] = _rate(row)
                flat[f"M6d.{name}.caught"] = float(row["caught"])
                flat[f"M6d.{name}.cases"] = float(row["cases"])
        else:
            flat[key] = float(value)
    return flat


def _higher(key: str) -> bool:
    return key in HIGHER or key.startswith("M6d")


def worse(key: str, candidate: float, best: float) -> bool:
    return candidate < best - 1e-9 if _higher(key) else candidate > best + 1e-9


def parse_waivers(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    waivers = list(document.get("waivers", []))
    for waiver in waivers:
        for field in ("metric", "old", "new", "owner_item", "granted", "expires"):
            if field not in waiver:
                raise ValueError(f"waiver is missing {field!r}")
        granted = date.fromisoformat(waiver["granted"])
        expires = date.fromisoformat(waiver["expires"])
        if (expires - granted).days > MAX_WAIVER_DAYS or expires < granted:
            raise ValueError(
                f"waiver for {waiver['metric']}: expiry must be 0 to {MAX_WAIVER_DAYS} days "
                f"after the grant"
            )
    return waivers


def live_waivers(document: Mapping[str, Any], today: date) -> list[dict[str, Any]]:
    return [w for w in parse_waivers(document) if date.fromisoformat(w["expires"]) >= today]


def regressions(
    best: Mapping[str, float],
    now: Mapping[str, float],
    waivers: list[dict[str, Any]] | None = None,
    today: date | None = None,
) -> list[str]:
    """Every metric of ``now`` worse than ``best`` that no live waiver excuses."""
    today = today or date.today()
    excused = {
        w["metric"]: float(w["new"])
        for w in (waivers or [])
        if date.fromisoformat(w["expires"]) >= today
    }
    problems: list[str] = []
    for key, value in sorted(now.items()):
        if key not in best or not worse(key, value, best[key]):
            continue
        if key in excused and not worse(key, value, excused[key]):
            continue
        problems.append(f"{key}: {value} is worse than the ratchet's {best[key]}")
    return problems


def load(path: Path = RATCHET_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def document(
    values: Mapping[str, Any], waivers: list[dict[str, Any]], control: str
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "control_revision": control,
        "corpus_seed": 20261019,
        "metrics": dict(values),
        "waivers": waivers,
    }
