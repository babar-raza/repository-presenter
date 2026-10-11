"""Where a correction sits in the owner's sending order, and why one is held or has nothing to send.

Recorded in each bundle's ``corrections.json`` under ``send`` so the owner table and whoever opens
the pull requests read one source:

* ``pr_order`` - 1 for a correction with a content edit (a version, a section, markup: a factual fix
  that should not wait behind a presentation change), 2 for a diagram-only correction (sent as a
  small pilot, not thirty-odd at once), ``None`` when there is nothing to send;
* ``hold_reason`` - a typed, evidence-bearing reason an owner has recorded in
  ``data/correction_holds.json`` for not opening the pull request yet (an upstream defect to file
  first); a hold never changes the bundle, only whether it is sent now;
* ``no_push_reason`` - the typed reason an entry with no edit has none (closed set below).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction.model import DIAGRAM_FIX, Finding

HOLDS_PATH = Path(__file__).resolve().parents[4] / "data" / "correction_holds.json"

#: Why an entry has nothing to push (typed, closed).
NO_PUSH_REASONS: dict[str, str] = {
    "NO_LIVE_README": "the repository has no README the proposal effect can patch",
    "INSUFFICIENT_EVIDENCE": "the facts-only run found the repository not processable",
    "ONLY_CHANGE_UNPORTABLE_DIAGRAM": (
        "the only correction found is redrawing a diagram whose label no Mermaid release draws "
        "portably, so the live drawing stays"
    ),
    "NO_DETECTOR_FIRED": (
        "the closed detector set found nothing to correct; this is not a finding that the "
        "README is accurate or complete"
    ),
}


def load_holds(path: Path = HOLDS_PATH) -> dict[str, dict[str, Any]]:
    """The recorded holds by repository. Strict: an entry without a typed code, a reason and a
    pairing is a defect in the data, never a hold that quietly means nothing."""
    if not path.is_file():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    holds: dict[str, dict[str, Any]] = {}
    for entry in document["holds"]:
        for key in ("repository", "reason_code", "reason", "pair_with", "recorded"):
            if not entry.get(key):
                raise ValueError(f"{path.name}: a hold lacks {key!r}: {entry}")
        if entry["repository"] in holds:
            raise ValueError(f"{path.name}: {entry['repository']} is held twice")
        holds[entry["repository"]] = entry
    return holds


def send_plan(
    repository: str,
    kinds: set[str],
    findings: list[Finding],
    *,
    holds: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    held = load_holds() if holds is None else holds
    hold = held.get(repository)
    plan: dict[str, Any] = {
        "pr_order": None,
        "hold_reason": (
            {k: hold[k] for k in ("reason_code", "reason", "pair_with", "recorded")}
            if hold
            else None
        ),
        "no_push_reason": None,
    }
    if kinds:
        plan["pr_order"] = 2 if kinds == {DIAGRAM_FIX} else 1
    elif any(f.report_only_reason == "DIAGRAM_LABEL_NOT_PORTABLE" for f in findings):
        plan["no_push_reason"] = "ONLY_CHANGE_UNPORTABLE_DIAGRAM"
    else:
        plan["no_push_reason"] = "NO_DETECTOR_FIRED"
    return plan
