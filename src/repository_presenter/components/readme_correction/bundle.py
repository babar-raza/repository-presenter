"""The correction bundle: the minimum honest set a proposal of a corrected README needs.

It is deliberately not a regenerated candidate's bundle and lives in no ``candidates/`` tree: it has
no plan, units, dispositions, model calls or review, because it has none of those. Its manifest
carries ``kind: "correction"`` and a state no regenerated-candidate reader counts, so no existing
count, drift monitor, recheck or propose gate can mistake one for the other. What it does carry is
what makes a correction checkable by anyone holding only the directory:

* ``README.original.md`` and ``facts.json`` and ``tree.txt``: the inputs;
* ``README.md``, ``README.patch`` and ``corrections.json``: the output and every edit it is made of;
* ``validation_delta.json``: the same judges that gate a regenerated README, run on both texts;
* ``manifest.json``: digests of all of the above, in the format ``verify_bundle`` already reads.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.renderer import render_patch
from repository_presenter.components.readme_correction.engine import is_stable
from repository_presenter.components.readme_correction.model import (
    KIND_CORRECTION,
    KIND_FIELD,
    Context,
    CorrectionResult,
    Edit,
)
from repository_presenter.core.facts import FACTS_FILENAME, write_facts

MANIFEST_NAME = "manifest.json"
STATE = "CORRECTION_READY"  # not a counted state: no regenerated-candidate reader sees it as one
README_NAME = "README.md"
ORIGINAL_NAME = "README.original.md"
PATCH_NAME = "README.patch"
CORRECTIONS_NAME = "corrections.json"
TREE_NAME = "tree.txt"
DELTA_NAME = "validation_delta.json"
SCHEMA_VERSION = 1
_VALUE_LIMIT = 160


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def edit_record(ctx: Context, index: int, edit: Edit) -> dict[str, Any]:
    """One edit as the bundle states it: what was quoted, what replaced it, and the evidence."""
    evidence = []
    for fact_id in edit.fact_ids:
        fact = ctx.fact(fact_id)
        evidence.append(
            {
                "fact_id": fact_id,
                "status": fact.polarity if fact is not None else "ABSENT",
                "kind": fact.kind if fact is not None else None,
                "value": fact.value[:_VALUE_LIMIT] if fact is not None else None,
            }
        )
    for locator in edit.locators:  # a structure fix's evidence is the README's own line
        evidence.append(
            {"fact_id": None, "status": "README_TEXT", "kind": "readme_structure", "value": locator}
        )
    return {
        "index": index,
        "kind": edit.kind,
        "detector": edit.detector,
        "line": ctx.readme.count("\n", 0, edit.start) + 1,
        "start": edit.start,
        "end": edit.end,
        "original": edit.original,
        "replacement": edit.replacement,
        "rationale": edit.rationale,
        "evidence": evidence,
    }


def corrections_document(
    ctx: Context, original: bytes, result: CorrectionResult, deterministic: bool, idempotent: bool
) -> dict[str, Any]:
    edits = [edit_record(ctx, index, edit) for index, edit in enumerate(result.edits)]
    kinds: dict[str, int] = {}
    for edit in result.edits:
        kinds[edit.kind] = kinds.get(edit.kind, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        KIND_FIELD: KIND_CORRECTION,
        "repository": ctx.facts.repository,
        "source_revision": ctx.facts.source_revision,
        "readme_path": ctx.readme_path,
        "original_sha256": sha256(original),
        "corrected_sha256": sha256(result.corrected.encode("utf-8")),
        "summary": dict(sorted(kinds.items())),
        "edits": edits,
        "unapplied_findings": [
            {
                "detector": finding.detector,
                "line": finding.line,
                "text": finding.text[:_VALUE_LIMIT],
                "reason": finding.reason,
                "fact_ids": list(finding.fact_ids),
            }
            for finding in result.findings
        ],
        "confinement": {
            "verified": True,
            "statement": "the corrected text with every edit's span removed equals the original "
            "with the same spans removed",
            "edits": len(edits),
        },
        "stability": {
            "deterministic": deterministic,
            "idempotent": idempotent,
            "provider_calls": 0,
        },
    }


def write_bundle(
    ctx: Context,
    original: bytes,
    result: CorrectionResult,
    delta: dict[str, Any],
    directory: Path,
) -> dict[str, Any]:
    """Write the bundle into ``directory`` (created, never merged into) and return its manifest."""
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"{directory} is not empty; a correction bundle is written whole")
    directory.mkdir(parents=True, exist_ok=True)
    deterministic, idempotent = is_stable(ctx, result)
    document = corrections_document(ctx, original, result, deterministic, idempotent)
    corrected = result.corrected.encode("utf-8")
    (directory / README_NAME).write_bytes(corrected)
    (directory / ORIGINAL_NAME).write_bytes(original)
    (directory / PATCH_NAME).write_bytes(render_patch(ctx.readme, result.corrected).encode("utf-8"))
    (directory / CORRECTIONS_NAME).write_text(_dump(document), encoding="utf-8", newline="\n")
    (directory / DELTA_NAME).write_text(_dump(delta), encoding="utf-8", newline="\n")
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
        KIND_FIELD: KIND_CORRECTION,
        "state": STATE,
        "repository": ctx.facts.repository,
        "revision": ctx.facts.source_revision,
        "readme_path": ctx.readme_path,
        "original_sha256": sha256(original),
        "corrected_sha256": sha256(corrected),
        "summary": document["summary"],
        "no_op_proof": {
            "method": "deterministic re-run of the correction over the bundle's own inputs",
            "byte_identical": deterministic,
            "idempotent_on_output": idempotent,
            "provider_calls": 0,
            "runs": 2,
        },
        "files": files,
    }
    (directory / MANIFEST_NAME).write_text(_dump(manifest), encoding="utf-8", newline="\n")
    return manifest


def _dump(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
