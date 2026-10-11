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
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.validation.registry import (
    Candidate,
    validate_candidate,
)
from repository_presenter.components.readme_correction.model import Context


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


def validation_delta(ctx: Context, corrected: str, original: bytes) -> dict[str, Any]:
    """Judge ``ctx.readme`` and ``corrected`` and report what the correction introduced/resolved.

    ``introduced`` is empty exactly when no check fails more often after the correction than
    before it; a detail that merely quotes a line the correction edited is not new when the check
    already failed as many times before."""
    revision = ctx.facts.source_revision
    live = _failures(ctx, ctx.readme, original, revision)
    after = _failures(ctx, corrected, original, revision)
    introduced: list[dict[str, Any]] = []
    for check_id in sorted(after):
        before = live.get(check_id, [])
        extra = len(after[check_id]) - len(before)
        if extra > 0:
            fresh = [detail for detail in after[check_id] if detail not in before]
            introduced.append(
                {"check": check_id, "extra": extra, "details": (fresh or after[check_id])[:extra]}
            )
    resolved = [
        {"check": check_id, "fewer": len(live[check_id]) - len(after.get(check_id, []))}
        for check_id in sorted(live)
        if len(live[check_id]) > len(after.get(check_id, []))
    ]
    return {
        "schema_version": 1,
        "judge": "validate_candidate",
        "live_failures": {key: len(value) for key, value in sorted(live.items())},
        "corrected_failures": {key: len(value) for key, value in sorted(after.items())},
        "introduced": introduced,
        "resolved": resolved,
    }
