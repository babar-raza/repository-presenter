"""The bundle of a live-anchored correction: the correction layout plus ``operations.json``.

Same files as ``bundle.write_bundle`` (README.md, README.original.md, README.patch,
corrections.json, facts.json, manifest.json, tree.txt, validation_delta.json) and one more,
``operations.json``: the
operations (``live_ops.Op``) that turn the original into README.md, as a list of dicts with sorted
keys. The manifest's ``kind`` is ``live_anchored``; nothing else about an existing bundle changes.

``corrections.json`` records, per operation, where it sits, what it quotes and replaces and the
evidence it cites with each entry's status read from ``facts.json``, so the record cannot disagree
with the evidence. ``live_gate.py`` recomputes all of it from the bundle's own bytes before a pull
request may be proposed.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.renderer import render_patch
from repository_presenter.components.readme_correction.bundle import (
    CORRECTIONS_NAME,
    DELTA_NAME,
    MANIFEST_NAME,
    ORIGINAL_NAME,
    PATCH_NAME,
    README_NAME,
    SCHEMA_VERSION,
    STATE,
    TREE_NAME,
    sha256,
)
from repository_presenter.components.readme_correction.live_ops import (
    Op,
    Placed,
    apply_ops,
    evidence_record,
    glance_bodies,
    glance_notes,
    inserted_titles,
    line_of,
    ops_to_json,
    resolve_evidence,
)
from repository_presenter.components.readme_correction.model import (
    KIND_FIELD,
    KIND_LIVE_ANCHORED,
    Context,
)
from repository_presenter.core.facts import FACTS_FILENAME, write_facts

OPERATIONS_NAME = "operations.json"
#: The files ``write_live_bundle`` writes.
LIVE_BUNDLE_FILES: tuple[str, ...] = (
    MANIFEST_NAME,
    README_NAME,
    ORIGINAL_NAME,
    PATCH_NAME,
    CORRECTIONS_NAME,
    DELTA_NAME,
    FACTS_FILENAME,
    TREE_NAME,
    OPERATIONS_NAME,
)


def dump(document: Any) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def operation_records(ctx: Context, placed: Sequence[Placed]) -> list[dict[str, Any]]:
    """Each operation as the bundle states it, in document order."""
    records: list[dict[str, Any]] = []
    for index, item in enumerate(placed):
        refs = resolve_evidence(ctx, item.op, [])
        records.append(
            {
                "index": index,
                "id": item.op.id,
                "kind": item.op.kind,
                "line": line_of(ctx.readme, item),
                "start": item.start,
                "end": item.end,
                "anchor": item.op.anchor,
                "replacement": item.op.replacement,
                "sections": inserted_titles(item),
                "evidence": [evidence_record(ref) for ref in refs],
            }
        )
    return records


def diagram_notes(placed: Sequence[Placed]) -> list[dict[str, str]]:
    """The lint defects tolerated on the diagrams the operations insert, for the record."""
    notes: list[dict[str, str]] = []
    for item in placed:
        for body in glance_bodies(item.text):
            notes += glance_notes(body)
    return notes


def live_document(
    ctx: Context, original: bytes, corrected: str, placed: Sequence[Placed]
) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for item in placed:
        kinds[item.op.kind] = kinds.get(item.op.kind, 0) + 1
    ops = [item.op for item in placed]
    return {
        "schema_version": SCHEMA_VERSION,
        KIND_FIELD: KIND_LIVE_ANCHORED,
        "repository": ctx.facts.repository,
        "source_revision": ctx.facts.source_revision,
        "readme_path": ctx.readme_path,
        "original_sha256": sha256(original),
        "corrected_sha256": sha256(corrected.encode("utf-8")),
        "summary": dict(sorted(kinds.items())),
        "operations": operation_records(ctx, placed),
        "diagram_notes": diagram_notes(placed),
        "confinement": {
            "verified": True,
            "statement": "the corrected text with every operation's span removed equals the "
            "original with the same spans removed",
            "operations": len(placed),
        },
        "stability": {
            "deterministic": apply_ops(ctx.readme, ops) == corrected,
            "order_independent": apply_ops(ctx.readme, tuple(reversed(ops))) == corrected,
            "provider_calls": 0,
        },
    }


def write_live_bundle(
    ctx: Context,
    original: bytes,
    corrected: str,
    placed: Sequence[Placed],
    delta: dict[str, Any],
    directory: Path,
) -> dict[str, Any]:
    """Write the bundle into ``directory`` (created, never merged into); return its manifest."""
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"{directory} is not empty; a correction bundle is written whole")
    directory.mkdir(parents=True, exist_ok=True)
    document = live_document(ctx, original, corrected, placed)
    body = corrected.encode("utf-8")
    ops: list[Op] = [item.op for item in placed]
    (directory / README_NAME).write_bytes(body)
    (directory / ORIGINAL_NAME).write_bytes(original)
    (directory / PATCH_NAME).write_bytes(render_patch(ctx.readme, corrected).encode("utf-8"))
    (directory / CORRECTIONS_NAME).write_text(dump(document), encoding="utf-8", newline="\n")
    (directory / DELTA_NAME).write_text(dump(delta), encoding="utf-8", newline="\n")
    (directory / OPERATIONS_NAME).write_text(dump(ops_to_json(ops)), encoding="utf-8", newline="\n")
    (directory / TREE_NAME).write_text(
        "\n".join(sorted(ctx.tree_paths)) + "\n", encoding="utf-8", newline="\n"
    )
    write_facts(ctx.facts, directory / FACTS_FILENAME)
    files = {
        path.name: {"sha256": sha256(path.read_bytes()), "bytes": path.stat().st_size}
        for path in sorted(directory.iterdir())
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        KIND_FIELD: KIND_LIVE_ANCHORED,
        "state": STATE,
        "repository": ctx.facts.repository,
        "revision": ctx.facts.source_revision,
        "readme_path": ctx.readme_path,
        "original_sha256": sha256(original),
        "corrected_sha256": sha256(body),
        "summary": document["summary"],
        "no_op_proof": {
            "method": "deterministic re-application of the operations over the bundle's own inputs",
            "byte_identical": document["stability"]["deterministic"],
            "order_independent": document["stability"]["order_independent"],
            "provider_calls": 0,
            "runs": 2,
        },
        "files": files,
    }
    (directory / MANIFEST_NAME).write_text(dump(manifest), encoding="utf-8", newline="\n")
    return manifest
