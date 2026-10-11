"""The corrected README must not fail a blocking check the live README did not already fail.

``validate_candidate`` (BC-01..BC-14) is the project's one judge of a README against its facts. A
live README written by hand fails several of its checks before any correction (a non-canonical
edition name, a badge the facts do not support); a correction is not responsible for those and
must not be blocked by them. It is responsible for not adding to them, so both texts are judged by
the same judges and the corrected one may not fail any check more often than the live one.

The judges that need a regeneration's plan, units or dispositions run with none, so those checks
fail identically for both texts and cancel; the ones that read only the README and the facts
(install, claims, links, structure, canonical name) are the comparison that matters.
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.validation.registry import (
    Candidate,
    validate_candidate,
)
from repository_presenter.components.readme_correction.apply import apply_edits
from repository_presenter.components.readme_correction.model import (
    DIAGRAM_FIX,
    STRUCTURE_FIX,
    Context,
    CorrectionResult,
)


def _failures(ctx: Context, readme: str, original: bytes, revision: str) -> dict[str, list[str]]:
    plugin_for(ctx.entry.ecosystem)  # registers the ecosystem spec the judges read
    candidate = Candidate(
        entry=ctx.entry,
        facts=ctx.facts,
        plan={"sections": []},
        units={"units": []},
        dispositions={"dispositions": []},
        readme=readme,
        original_readme=original,
        source_revision=revision,
        readme_sha256=hashlib.sha256(original).hexdigest(),
        tree_paths=ctx.tree_paths,
        tasks=[],
    )
    with tempfile.TemporaryDirectory() as scratch:
        document = validate_candidate(candidate, Path(scratch), [])
    return {
        check["id"]: list(check["details"])
        for check in document["checks"]
        if check["verdict"] == "FAIL"
    }


#: Structure fixes add no prose, but they change what the judges see: closing a ``<details>``
#: exposes the maintainers' own sections to the prose checks, and promoting a second H1 to H2
#: starts a new section in the judges' segmentation (measured on Aspose.Cells for Go, where it
#: moved a line out of the deterministic Installation section and BC-04 began to judge a `v26`
#: code span the maintainers had always written). A failure the judges find in text that was
#: merely re-classified is *revealed*, not introduced, and is recorded as such.


@dataclass(frozen=True)
class Allowance:
    """A failure one kind of edit may bring without counting as introduced, with its ruling.

    Typed and closed: the allowance names the edit kind, the check and the wording of the failure
    it covers, and every use is written into ``validation_delta.json`` under ``allowed`` with the
    ruling, so a reader sees exactly what the rule let through."""

    edit_kind: str
    check: str
    detail_prefix: str
    ruling: str
    reason: str


ALLOWANCES: tuple[Allowance, ...] = (
    Allowance(
        DIAGRAM_FIX,
        "BC-07",
        "At a Glance",
        "R7",
        "BC-07's topology rule still describes the vertical `flowchart TD` drawing and is being "
        "migrated to components/readme_diagram/contract.py (owner ruling R7); a diagram rebuild "
        "is judged by that contract (the detector asks it before editing), so the old rule's "
        "At a Glance failures on the rebuilt drawing do not count",
    ),
)


def _fresh(before: dict[str, list[str]], check_id: str, after: dict[str, list[str]]) -> list[str]:
    known = before.get(check_id, [])
    return [detail for detail in after.get(check_id, []) if detail not in known]


def _split_allowed(
    before: dict[str, list[str]], after: dict[str, list[str]], kinds: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(introduced, allowed)`` for the failures ``after`` has more of than ``before``."""
    introduced: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for check_id in sorted(after):
        extra = len(after[check_id]) - len(before.get(check_id, []))
        if extra <= 0:
            continue
        fresh = _fresh(before, check_id, after) or after[check_id]
        for allowance in ALLOWANCES:
            if allowance.edit_kind not in kinds or allowance.check != check_id:
                continue
            covered = [d for d in fresh if d.startswith(allowance.detail_prefix)][:extra]
            if covered:
                allowed.append(
                    {
                        "check": check_id,
                        "extra": len(covered),
                        "details": covered,
                        "ruling": allowance.ruling,
                        "reason": allowance.reason,
                    }
                )
                extra -= len(covered)
                fresh = [d for d in fresh if d not in covered]
        if extra > 0:
            introduced.append({"check": check_id, "extra": extra, "details": fresh[:extra]})
    return introduced, allowed


def validation_delta(ctx: Context, result: CorrectionResult, original: bytes) -> dict[str, Any]:
    """Judge the live and the corrected README and report what the correction did to each check.

    ``introduced`` is empty exactly when no check fails more often after the correction than
    before it. The comparison is against the live README with only its structure fixes applied
    (newly visible maintainer text is reported under ``revealed`` instead) and then with its
    diagram rebuild too: what a typed ``ALLOWANCES`` entry covers is reported under ``allowed``
    with its ruling, anything else the rebuild brings is introduced."""
    revision = ctx.facts.source_revision
    live = _failures(ctx, ctx.readme, original, revision)
    structure = [e for e in result.edits if e.kind == STRUCTURE_FIX]
    diagram = [e for e in result.edits if e.kind == DIAGRAM_FIX]
    if structure:
        exposed, _spans = apply_edits(ctx.readme, structure)
        base = _failures(ctx, exposed, original, revision)
    else:
        base = live
    if diagram:
        drawn, _spans = apply_edits(ctx.readme, sorted(structure + diagram, key=lambda e: e.start))
        redrawn = _failures(ctx, drawn, original, revision)
    else:
        redrawn = base
    after = (
        live
        if result.corrected == ctx.readme
        else _failures(ctx, result.corrected, original, revision)
    )
    kinds = {e.kind for e in result.edits}
    introduced, allowed = _split_allowed(base, redrawn, kinds)
    introduced += _increases(redrawn, after)
    return {
        "schema_version": 1,
        "judge": "validate_candidate",
        "live_failures": {key: len(value) for key, value in sorted(live.items())},
        "corrected_failures": {key: len(value) for key, value in sorted(after.items())},
        "introduced": introduced,
        "allowed": allowed,
        "revealed": _increases(live, base),
        "resolved": [
            {"check": check_id, "fewer": len(live[check_id]) - len(after.get(check_id, []))}
            for check_id in sorted(live)
            if len(live[check_id]) > len(after.get(check_id, []))
        ],
    }


def _increases(before: dict[str, list[str]], after: dict[str, list[str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for check_id in sorted(after):
        known = before.get(check_id, [])
        extra = len(after[check_id]) - len(known)
        if extra > 0:
            fresh = [detail for detail in after[check_id] if detail not in known]
            out.append(
                {"check": check_id, "extra": extra, "details": (fresh or after[check_id])[:extra]}
            )
    return out
