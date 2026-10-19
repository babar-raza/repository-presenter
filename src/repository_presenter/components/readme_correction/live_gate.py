"""The propose gate for a live-anchored bundle: everything recomputed from the bundle's own bytes.

``gate.correction_refusal`` proves a correction by re-running the detectors; here the equivalent is
re-applying the operations. Nothing is read back as a claim:

* ``operations.json`` is parsed strictly (a kind outside the closed four is refused);
* ``live_ops.check_ops`` runs again over ``README.original.md``, ``facts.json`` and ``tree.txt``
  (anchors, per-kind rules, evidence resolved against the facts the bundle carries);
* applying the operations to ``README.original.md`` must give ``README.md`` byte for byte, and the
  confinement proof must hold over the stored texts;
* ``corrections.json`` must say exactly what the recomputation says, ``validation_delta.json`` must
  equal the recomputed delta (the correction path's own judge), and ``introduced`` must be empty.

Each refusal carries a typed code (``live_ops`` codes plus the ones below) so a person can see
which rule stopped it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.live_bundle import (
    OPERATIONS_NAME,
    diagram_notes,
    operation_records,
)
from repository_presenter.components.readme_correction.live_ops import (
    STALE_REVISION,
    LiveOpError,
    apply_placed,
    check_ops,
    confinement_proof,
    ops_from_json,
    place,
)
from repository_presenter.components.readme_correction.model import (
    KIND_FIELD,
    KIND_LIVE_ANCHORED,
    Context,
    CorrectionResult,
)
from repository_presenter.core.facts import FACTS_FILENAME, read_facts
from repository_presenter.core.registry.models import RegistryEntry

BUNDLE_UNREADABLE = "BUNDLE_UNREADABLE"
HASH_MISMATCH = "HASH_MISMATCH"
README_NOT_REPRODUCED = "README_NOT_REPRODUCED"
CONFINEMENT_FAILED = "CONFINEMENT_FAILED"
RECORD_MISMATCH = "RECORD_MISMATCH"
DELTA_MISMATCH = "DELTA_MISMATCH"
DELTA_INTRODUCES = "DELTA_INTRODUCES"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def live_anchored_refusal(
    bundle: Path, manifest: dict[str, Any], entry: RegistryEntry
) -> str | None:
    """Why ``bundle`` is not a proven live-anchored correction, or None. Pure: reads the bundle."""
    if manifest.get(KIND_FIELD) != KIND_LIVE_ANCHORED or manifest.get("state") != files.STATE:
        return f"the manifest is not a {KIND_LIVE_ANCHORED} bundle in state {files.STATE}"
    try:
        original = (bundle / files.ORIGINAL_NAME).read_bytes()
        stored = (bundle / files.README_NAME).read_bytes()
        facts = read_facts(bundle / FACTS_FILENAME)
        tree = tuple(
            line
            for line in (bundle / files.TREE_NAME).read_text(encoding="utf-8").splitlines()
            if line
        )
        document = _json(bundle / files.CORRECTIONS_NAME)
        stored_delta = _json(bundle / files.DELTA_NAME)
        raw_ops = _json(bundle / OPERATIONS_NAME)
        original_text = original.decode("utf-8")
        stored_text = stored.decode("utf-8")
    except (OSError, ValueError) as exc:
        return f"{BUNDLE_UNREADABLE}: the bundle cannot be read back: {exc}"
    if manifest.get("original_sha256") != files.sha256(original):
        return f"{HASH_MISMATCH}: the manifest's original_sha256 is not the stored original README"
    if manifest.get("corrected_sha256") != files.sha256(stored):
        return (
            f"{HASH_MISMATCH}: the manifest's corrected_sha256 is not the stored corrected README"
        )
    revision = manifest.get("revision")
    if (
        facts.source_revision != revision
        or facts.repository != manifest.get("repository")
        or not isinstance(document, dict)
        or document.get("source_revision") != revision
    ):
        return (
            f"{STALE_REVISION}: facts.json or corrections.json is for another repository or "
            "revision than the manifest"
        )
    try:
        ops = ops_from_json(raw_ops)
    except LiveOpError as exc:
        return f"{exc.code}: {exc}"
    ctx = Context(entry, facts, original_text, tree, str(manifest.get("readme_path", "README.md")))
    refusals = check_ops(ctx, ops)
    if refusals:
        return str(refusals[0]) + (f" (and {len(refusals) - 1} more)" if len(refusals) > 1 else "")
    try:
        placed = place(original_text, ops)
    except LiveOpError as exc:  # check_ops placed them already; kept for a total function
        return f"{exc.code}: {exc}"
    again, _spans = apply_placed(original_text, placed)
    if again != stored_text:
        return (
            f"{README_NOT_REPRODUCED}: re-applying the operations does not reproduce README.md "
            "byte for byte"
        )
    if not confinement_proof(original_text, stored_text, ops):
        return f"{CONFINEMENT_FAILED}: text outside the operations' spans differs from the original"
    if (
        document.get("operations") != operation_records(ctx, placed)
        or document.get("diagram_notes") != diagram_notes(placed)
        or document.get(KIND_FIELD) != KIND_LIVE_ANCHORED
    ):
        return f"{RECORD_MISMATCH}: corrections.json does not list exactly the operations applied"
    delta = validation_delta(
        ctx, CorrectionResult(original=original_text, corrected=again), original
    )
    if json.loads(json.dumps(delta)) != stored_delta:
        return f"{DELTA_MISMATCH}: validation_delta.json is not what the judge finds now"
    if delta["introduced"]:
        introduced = ", ".join(item["check"] for item in delta["introduced"])
        return (
            f"{DELTA_INTRODUCES}: the operations introduce failing checks the live README did "
            f"not have: {introduced}"
        )
    return None
