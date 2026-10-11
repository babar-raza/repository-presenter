"""``correct-readme``: the live README at the registry's head, corrected against verified facts.

Read-only toward the target (a pinned, push-disabled clone), model-free, and effect-free: the only
thing written is the directory the caller names. Facts are either a candidate's or a prior
facts-only run's ``facts.json`` for *the same revision*, or are extracted now through the existing
facts-only path the caller supplies; a revision mismatch is a refusal, never a best effort.

A repository with nothing to correct is a result, not an error: ``no_live_readme`` (no README, or
one the proposal effect cannot patch), ``insufficient_evidence`` (the facts-only run found it not
processable) or ``no_detector_fired`` (the closed detector set found nothing to change: a statement
about the detectors, never a finding that the README is accurate or complete). Only the
``corrected`` and ``no_detector_fired`` results write a bundle; the others write a ``status.json``
that says why, and the regeneration lane handles the first two.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction.bundle import write_bundle
from repository_presenter.components.readme_correction.engine import CorrectionError
from repository_presenter.components.readme_correction.model import Context
from repository_presenter.components.readme_correction.settle import correct_settled
from repository_presenter.core.facts import read_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths

#: The only README path the proposal effect writes (``components/propose/effect.py``).
README_PATH = "README.md"
STATUS_NAME = "status.json"
CORRECTED = "corrected"
NO_CORRECTIONS = "no_detector_fired"
NO_LIVE_README = "no_live_readme"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
#: ``extract_facts(revision)`` -> a ``facts.json`` for exactly that revision, or None when the
#: facts-only run found the repository not processable (a placeholder: insufficient evidence).
FactsExtractor = Callable[[str], Path | None]


@dataclass(frozen=True)
class CorrectionOutcome:
    repository: str
    revision: str
    out: Path
    status: str
    reason: str = ""
    edits: int = 0
    summary: dict[str, int] = field(default_factory=dict)
    unapplied: int = 0
    manifest: dict[str, Any] = field(default_factory=dict)


def _record(
    entry: RegistryEntry, revision: str, out: Path, status: str, reason: str
) -> CorrectionOutcome:
    """A result that proposes nothing: written down, so the portfolio table can show why."""
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} is not empty; a correction result is written whole")
    out.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": 1,
        "kind": "correction",
        "status": status,
        "repository": entry.repository,
        "revision": revision,
        "reason": reason,
    }
    (out / STATUS_NAME).write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return CorrectionOutcome(entry.repository, revision, out, status, reason)


def produce_correction(
    entry: RegistryEntry,
    *,
    clone_directory: Path,
    out_directory: Path,
    facts_path: Path | None = None,
    extract_facts: FactsExtractor | None = None,
    token: str | None = None,
) -> CorrectionOutcome:
    clone = pinned_read_only_clone(entry.clone_url, clone_directory, token=token)
    snapshot = capture_snapshot(entry.repository, clone)
    if snapshot.readme_path is None:
        return _record(
            entry, clone.revision, out_directory, NO_LIVE_README, "the repository has no README"
        )
    if snapshot.readme_path != README_PATH:
        return _record(
            entry,
            clone.revision,
            out_directory,
            NO_LIVE_README,
            f"the README is {snapshot.readme_path!r}; a correction patches {README_PATH} only",
        )
    original = (clone.path / snapshot.readme_path).read_bytes()
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorrectionError(f"{entry.repository}'s README is not UTF-8: {exc}") from exc
    if facts_path is None:
        if extract_facts is None:
            raise CorrectionError("no --facts given and no facts-only extraction available")
        facts_path = extract_facts(clone.revision)
        if facts_path is None:
            return _record(
                entry,
                clone.revision,
                out_directory,
                INSUFFICIENT_EVIDENCE,
                "the facts-only run found the repository not processable (a placeholder)",
            )
    facts = read_facts(facts_path)
    if facts.repository != entry.repository or facts.source_revision != clone.revision:
        raise CorrectionError(
            f"facts are for {facts.repository} @ {facts.source_revision}, but the registry head "
            f"is {entry.repository} @ {clone.revision}; extract facts at the head and retry"
        )
    ctx = Context(entry, facts, text, tuple(list_tree_paths(clone.path)), snapshot.readme_path)
    result, delta = correct_settled(ctx, original)
    if delta["introduced"]:
        raise CorrectionError(
            "the correction introduces failing checks the live README did not have: "
            + ", ".join(item["check"] for item in delta["introduced"])
        )
    manifest = write_bundle(ctx, original, result, delta, out_directory)
    return CorrectionOutcome(
        repository=entry.repository,
        revision=clone.revision,
        out=out_directory,
        status=CORRECTED if result.edits else NO_CORRECTIONS,
        edits=len(result.edits),
        summary=dict(manifest["summary"]),
        unapplied=len(result.findings),
        manifest=manifest,
    )
