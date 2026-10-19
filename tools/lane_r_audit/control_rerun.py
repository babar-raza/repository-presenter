"""The control re-run (card C1, step 6): today's deterministic checks over the frozen inputs.

Before C2 changes any gate, re-run the S9 blocking checks of the validator that runs today over each
of the 30 pinned bundles, offline and with no provider call, and record the verdicts beside the
validator version each bundle was sealed under (23 of the 30 were judged by version 3, which predates
BC-12 and BC-14). The difference is the baseline: a bundle that passed when sealed and fails now was
accepted by a weaker validator, which is a statement about the gates, not about the bundle.

Imports the validation layer (like ``baseline_gates``) because the re-run IS the gates; the metrics
M1 to M5 never import this module. The result does not depend on the worker count.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from repository_presenter.components.readme.validation import registry as validation

from . import baseline_gates
from .pinned import PinnedBundle, load_pins, read_bundles

WORKERS = max(1, min(8, (os.cpu_count() or 2) - 1))
# the S9 checks that read only the candidate (BC-09 scans a transaction directory; BC-10, BC-11 and
# BC-13 are judged at other stages): id -> the module-level check function
_CHECKS = {
    "BC-01": "_check_source",
    "BC-02": "_check_install",
    "BC-03": "_check_examples",
    "BC-04": "_check_units",
    "BC-05": "_check_dispositions",
    "BC-06": "_check_links",
    "BC-07": "_check_structure",
    "BC-08": "_check_protected",
    "BC-12": "_check_canonical_name",
    "BC-14": "_check_claims",
}


def rerun_one(bundle: PinnedBundle) -> dict[str, Any]:
    candidate = baseline_gates.candidate_for(bundle)
    verdicts: dict[str, Any] = {}
    for check_id, name in _CHECKS.items():
        try:
            failures = getattr(validation, name)(candidate)
        except Exception as exc:  # recorded, never swallowed: an ERROR is a finding about the gate
            verdicts[check_id] = {"verdict": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:160]}
            continue
        verdicts[check_id] = {"verdict": "FAIL" if failures else "PASS", "failures": len(failures)}
    sealed = (bundle.sealed.validation or {}) if bundle.sealed else {}
    sealed_failed = sorted(
        c["id"] for c in sealed.get("checks", []) if c.get("verdict") == "FAIL"
    )
    return {
        "directory": bundle.pin.directory,
        "sealed_validator_version": sealed.get("validator_version"),
        "sealed_failed": sealed_failed,
        "now": verdicts,
        "now_failed": sorted(k for k, v in verdicts.items() if v["verdict"] != "PASS"),
    }


def _worker(directory: str) -> dict[str, Any]:
    bundles = {b.pin.directory: b for b in read_bundles(load_pins())}
    return rerun_one(bundles[directory])


def rerun_all() -> dict[str, Any]:
    pins = load_pins()
    directories = sorted(p.directory for p in pins.bundles)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(_worker, directories))
    versions: dict[str, int] = {}
    for row in rows:
        key = str(row["sealed_validator_version"])
        versions[key] = versions.get(key, 0) + 1
    newly_failing = {
        row["directory"]: sorted(set(row["now_failed"]) - set(row["sealed_failed"]))
        for row in rows
        if set(row["now_failed"]) - set(row["sealed_failed"])
    }
    return {
        "schema_version": 1,
        "control_revision": pins.control_revision,
        "validator_version_now": validation.VALIDATOR_VERSION,
        "bundles": len(rows),
        "sealed_validator_versions": dict(sorted(versions.items())),
        "bundles_failing_now": sum(1 for r in rows if r["now_failed"]),
        "bundles_newly_failing": len(newly_failing),
        "newly_failing": newly_failing,
        "rows": rows,
    }
