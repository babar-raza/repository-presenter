"""The Lane R ratchet (G3-W12 card C1, step 5): the metrics may only improve.

Two tiers, both computed from the pinned reader, never from a stored number:

* the ledger tier (M1 to M5, M9) takes seconds;
* the gate tier (M6d: BC-04 and BC-14 over the corpus's test half) takes a few minutes in worker
  processes.

``data/lane_r_corpus/ratchet.json`` is read from the branch, and again from ``origin/main`` with
``git show``: a branch that lowers its own file fails here, because the file on main is the bar. A
checkout without ``origin/main`` FAILS (never skips): a skipped ratchet is a false green, which is
the failure this card exists to end. A waiver is a recorded owner decision with an expiry at most
14 days after its grant; these tests parse it.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from tools.lane_r_audit import ratchet

from repository_presenter.core.git_safety.git import run_git
from support import REPO_ROOT


def _on_main(path: str) -> str | None:
    probe = run_git(["rev-parse", "--verify", "--quiet", "origin/main^{commit}"], cwd=REPO_ROOT)
    if probe.returncode != 0:
        pytest.fail(
            "origin/main is not fetched: the ratchet never skips (git fetch origin main; hosted CI "
            "needs fetch-depth 0 or an explicit fetch)"
        )
    shown = run_git(["show", f"origin/main:{path}"], cwd=REPO_ROOT)
    return shown.stdout if shown.returncode == 0 else None


def _main_ratchet() -> dict[str, Any] | None:
    text = _on_main(ratchet.RATCHET_REL)
    return json.loads(text) if text is not None else None


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    return ratchet.load()


# --- the file on the branch, and against main ----------------------------------------------------


def test_the_committed_ratchet_is_well_formed(committed: dict[str, Any]) -> None:
    assert committed["schema_version"] == 1
    metrics = committed["metrics"]
    assert {"M1", "M2", "M3", "M4", "M5", "M9", "M6d"} <= set(metrics)
    assert set(metrics["M6d"]["per_class_test"]) == {
        "count",
        "formatting",
        "invented_capability",
        "polarity_contradiction",
        "scraped_text",
        "symbol_prose",
        "version",
    }
    ratchet.parse_waivers(committed)  # raises on a malformed or over-long waiver


def test_the_committed_ratchet_is_no_worse_than_origin_main(committed: dict[str, Any]) -> None:
    on_main = _main_ratchet()
    if on_main is None:  # the commit that introduces the file: nothing to be worse than
        return
    # only a waiver already on main excuses a lowered value: a branch cannot grant itself one
    problems = ratchet.regressions(
        ratchet.flatten(on_main["metrics"]),
        ratchet.flatten(committed["metrics"]),
        ratchet.parse_waivers(on_main),
    )
    assert not problems, "\n".join(problems)


def test_the_pins_are_the_pins_on_origin_main() -> None:
    """A branch that shrinks pins.json lowers M2 to M5 without lowering a ratchet value."""
    on_main = _on_main("data/lane_r_corpus/pins.json")
    if on_main is None:
        return
    here = (REPO_ROOT / "data" / "lane_r_corpus" / "pins.json").read_text(encoding="utf-8")
    assert here == on_main, "pins.json differs from origin/main: re-pinning is an owner decision"


# --- the metrics themselves ----------------------------------------------------------------------


def test_ledger_tier_is_no_worse_than_the_ratchet_and_reproducible(
    committed: dict[str, Any],
) -> None:
    first = ratchet.ledger_values()
    assert first == ratchet.ledger_values()  # two runs give identical M1 to M5 and M9
    best = ratchet.flatten({k: v for k, v in committed["metrics"].items() if k != "M6d"})
    problems = ratchet.regressions(best, ratchet.flatten(first), [])
    assert not problems, "\n".join(problems)


def test_gate_tier_is_no_worse_than_the_ratchet(committed: dict[str, Any]) -> None:
    now = ratchet.gate_values()
    best = ratchet.flatten({"M6d": committed["metrics"]["M6d"]})
    problems = ratchet.regressions(best, ratchet.flatten({"M6d": now}), [])
    assert not problems, "\n".join(problems)


def test_the_baseline_records_that_the_gates_catch_no_real_defect(
    committed: dict[str, Any],
) -> None:
    """The measured fact the plan rests on (F2): BC-04 and BC-14 catch none of the real defects.

    When C2 lands this number rises and the ratchet keeps it; this test then names the new floor
    instead of the old one, in the same commit.
    """
    real = committed["metrics"]["M6d"]["real_defects"]
    assert real["cases"] >= 20
    assert real["caught"] == 0


# --- negative controls: the ratchet fails what it must ------------------------------------------

_BEST = {"M1": 0.5, "M2": 300.0, "M6d.version": 0.5}


def test_a_lowered_higher_metric_fails() -> None:
    assert ratchet.regressions(_BEST, {"M1": 0.4})


def test_a_raised_lower_metric_fails() -> None:
    assert ratchet.regressions(_BEST, {"M2": 301.0})


def test_an_improvement_and_a_tie_pass() -> None:
    assert ratchet.regressions(_BEST, {"M1": 0.6, "M2": 300.0, "M6d.version": 0.5}) == []


def test_a_live_waiver_excuses_exactly_its_move() -> None:
    waiver = {
        "metric": "M1",
        "old": 0.5,
        "new": 0.45,
        "owner_item": "OWNER-X",
        "granted": "2026-10-19",
        "expires": "2026-10-30",
    }
    today = date(2026, 10, 20)
    assert ratchet.regressions(_BEST, {"M1": 0.45}, [waiver], today) == []
    assert ratchet.regressions(_BEST, {"M1": 0.40}, [waiver], today)  # worse than the waiver allows


def test_an_expired_waiver_excuses_nothing() -> None:
    waiver = {
        "metric": "M1",
        "old": 0.5,
        "new": 0.45,
        "owner_item": "OWNER-X",
        "granted": "2026-10-01",
        "expires": "2026-10-10",
    }
    assert ratchet.regressions(_BEST, {"M1": 0.45}, [waiver], date(2026, 10, 20))


def test_a_waiver_longer_than_fourteen_days_is_rejected() -> None:
    waiver = {
        "metric": "M1",
        "old": 0.5,
        "new": 0.4,
        "owner_item": "OWNER-X",
        "granted": "2026-10-01",
        "expires": "2026-10-30",
    }
    with pytest.raises(ValueError, match="14 days"):
        ratchet.parse_waivers({"waivers": [waiver]})


def test_a_waiver_missing_a_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="owner_item"):
        ratchet.parse_waivers(
            {
                "waivers": [
                    {
                        "metric": "M1",
                        "old": 1,
                        "new": 0,
                        "granted": "2026-10-01",
                        "expires": "2026-10-02",
                    }
                ]
            }
        )


def test_a_waiver_written_in_the_branch_file_does_not_excuse_a_lowered_value() -> None:
    main_doc: dict[str, Any] = {"metrics": {"M1": 0.5}, "waivers": []}
    branch_doc: dict[str, Any] = {
        "metrics": {"M1": 0.3},
        "waivers": [
            {
                "metric": "M1",
                "old": 0.5,
                "new": 0.3,
                "owner_item": "OWNER-FAKE",
                "granted": "2026-10-19",
                "expires": "2026-10-30",
            }
        ],
    }
    problems = ratchet.regressions(
        ratchet.flatten(main_doc["metrics"]),
        ratchet.flatten(branch_doc["metrics"]),
        ratchet.parse_waivers(main_doc),  # what the real test reads: main's waivers only
        date(2026, 10, 20),
    )
    assert problems


def _m6d(caught: int, cases: int) -> dict[str, Any]:
    return {
        "M6d": {
            "per_class_test": {"version": {"caught": caught, "cases": cases}},
            "real_defects": {"caught": 0, "cases": 20},
        }
    }


def test_a_shrunk_cell_cannot_hide_behind_a_higher_rate() -> None:
    problems = ratchet.regressions(ratchet.flatten(_m6d(1, 8)), ratchet.flatten(_m6d(1, 1)), [])
    assert any("version.cases" in p for p in problems)
