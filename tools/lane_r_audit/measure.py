"""The harness's measured values: one deterministic document per run, and the v2 baseline file.

``measure`` reads the pinned bundles once and computes every metric the ratchet and the baseline
need. It is a pure function of the pinned bytes and the working tree's ``data/readme_standard``
(for the judge): no clock, no network, no random. Two runs give identical output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import claims_ref, ledger, lint
from .pinned import (
    PINS_PATH,
    REPO_ROOT,
    PinnedBundle,
    Pins,
    check_survey,
    load_pins,
    read_bundles,
)

BASELINE_V2_PATH = REPO_ROOT / "data" / "lane_r_corpus" / "ledger_baseline_v2.json"
V1_PATH = REPO_ROOT / "evidence" / "lane-r-dependability" / "ledger_baseline.json"
# The metrics a ratchet holds; "higher" metrics may only rise, the others only fall.
HIGHER_IS_BETTER = frozenset({"M1", "M6d", "M9"})
RATCHETED = ("M1", "M2", "M3", "M4", "M5", "M6d", "M9")


def measure_ledger(bundles: list[PinnedBundle]) -> dict[str, Any]:
    """M1, M2, M3, M9 and the judge counts, in total and per bundle."""
    verdicts = ledger.judge_verdicts(bundles)
    per_bundle: dict[str, Any] = {}
    all_accounts: list[ledger.UnitAccount] = []
    for bundle in bundles:
        accounts = ledger.unit_accounts(bundle)
        all_accounts.extend(accounts)
        verdict = verdicts[bundle.repository]
        per_bundle[bundle.pin.directory] = {
            "revision": bundle.pin.revision,
            "v1": ledger.v1_bundle(bundle),
            "ledger": ledger.ledger_metrics(accounts).to_json(),
            "judge_failing": list(verdict.failing),
            "authorizable": verdict.authorizable,
        }
    total = ledger.ledger_metrics(all_accounts)
    authorizable = sum(1 for verdict in verdicts.values() if verdict.authorizable)
    return {
        "inputs": len(bundles),
        "M1": round(total.m1, 6),
        "M2": total.m2,
        "M3": total.m3,
        "M9": {"authorizable": authorizable, "inputs": len(bundles)},
        "ledger": total.to_json(),
        "v1": ledger.v1_totals(bundles),
        "judge": {
            "J4_fail": sum(1 for v in verdicts.values() if "J4_DISPOSITIONS" in v.failing),
            "J6_fail": sum(1 for v in verdicts.values() if "J6_NOT_WORSE_THAN_LIVE" in v.failing),
            "authorizable": authorizable,
        },
        "m7_regression": {
            "J5_pass": sum(1 for v in verdicts.values() if v.passes("J5_RERUN")),
            "inputs": len(bundles),
        },
        "bundles": per_bundle,
    }


def measure_claims(bundles: list[PinnedBundle]) -> dict[str, Any]:
    """M4 (claim escapes in LLM-owned prose) and M5 (junk-lint hits in the README), with the
    live READMEs' own lint hits and the strict M4 reading beside them as diagnostics."""
    by_class: dict[str, int] = dict.fromkeys(claims_ref.CLASSES, 0)
    rules: dict[str, int] = dict.fromkeys(lint.RULES, 0)
    units = flagged = strict = live_hits = 0
    per_bundle: dict[str, Any] = {}
    for bundle in bundles:
        content = (bundle.content_units or {}).get("units", [])
        found = claims_ref.bundle_escapes(content, bundle.facts_by_id)
        strict += len(claims_ref.bundle_escapes(content, bundle.facts_by_id, strict=True))
        hits = lint.lint(bundle.readme)
        live_hits += len(lint.lint(bundle.live or ""))
        units += len(content)
        flagged += len({escape.unit for escape in found})
        for escape in found:
            by_class[escape.cls] += 1
        for hit in hits:
            rules[hit.rule] += 1
        per_bundle[bundle.pin.directory] = {"m4": len(found), "m5": len(hits)}
    return {
        "M4": sum(by_class.values()),
        "M5": sum(rules.values()),
        "m4_detail": {
            "by_class": by_class,
            "units": units,
            "units_flagged": flagged,
            "strict_reading": strict,
        },
        "m5_detail": {"by_rule": rules, "live_readme_hits": live_hits},
        "claims_per_bundle": per_bundle,
    }


def measure(pins: Pins | None = None, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Every metric from the pinned bundles. Raises ``PinnedInputError`` on any pin deviation."""
    pins = pins or load_pins()
    check_survey(pins)
    bundles = read_bundles(pins, repo_root)
    result = measure_ledger(bundles)
    result.update(measure_claims(bundles))
    result["control_revision"] = pins.control_revision
    return result


def baseline_v2(measured: dict[str, Any], pins: Pins | None = None) -> dict[str, Any]:
    """The v2 baseline document: the values the C3 to C8 deltas are read against."""
    pins = pins or load_pins()
    totals = measured["ledger"]
    return {
        "schema_version": 2,
        "control_revision": pins.control_revision,
        "pins_file": PINS_PATH.relative_to(REPO_ROOT).as_posix(),
        "survey_sha256": pins.survey_sha256,
        "m3_definition": {
            "threshold": ledger.M3_THRESHOLD,
            "threshold_status": "provisional; frozen here until an owner decision in DECISION_LOG",
            "tokeniser": ledger.TOKENISER,
            "destination": "the destination_section of the disposition, located in the sealed "
            "README (an H2 by name, the lead for identity/badges/banner/opening)",
        },
        "v1_reproduced": measured["v1"],
        "v1_judge": {
            "J4_fail": measured["judge"]["J4_fail"],
            "J6_fail": measured["judge"]["J6_fail"],
        },
        "m1": {
            "value": measured["M1"],
            "accounted": totals["accounted"],
            "over": totals["units"],
            "defer_unresolved_not_accounted": totals["defer_unresolved"],
        },
        "m2": {
            "value": measured["M2"],
            "of_omit_unsupported": totals["omit_unsupported"],
            "of_which_cite_no_fact": totals["omit_unsupported_without_fact"],
        },
        "m3": {
            "value": measured["M3"],
            "of_supersede_redundant": totals["supersede_redundant"],
            "destination_unlocated": totals["supersede_destination_unlocated"],
            "threshold": ledger.M3_THRESHOLD,
            "tokeniser": ledger.TOKENISER,
        },
        "m4": {"value": measured["M4"], **measured["m4_detail"]},
        "m5": {"value": measured["M5"], **measured["m5_detail"]},
        "m7_regression": measured["m7_regression"],
        "m9": measured["M9"],
        "unaccounted_by_disposition": totals["unaccounted_by_disposition"],
        "bundles": measured["bundles"],
    }


def dumps(document: dict[str, Any]) -> str:
    """The canonical JSON form: sorted keys, two spaces, a final newline."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
