"""``correct-readme``: the live README at the registry's head, corrected against verified facts.

Read-only toward the target (a pinned, push-disabled clone), model-free, and effect-free: the only
thing written is the bundle directory the caller names. Facts are either a candidate's or a prior
facts-only run's ``facts.json`` for *the same revision*, or are extracted now through the existing
facts-only path the caller supplies; a revision mismatch is a refusal, never a best effort.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction.bundle import write_bundle
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import CorrectionError, correct
from repository_presenter.components.readme_correction.model import Context
from repository_presenter.core.facts import read_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths

#: The only README path the proposal effect writes (``components/propose/effect.py``).
README_PATH = "README.md"
#: ``extract_facts(revision) -> path`` of a ``facts.json`` for exactly that revision.
FactsExtractor = Callable[[str], Path]


@dataclass(frozen=True)
class CorrectionOutcome:
    repository: str
    revision: str
    out: Path
    edits: int
    summary: dict[str, int]
    unapplied: int
    manifest: dict[str, Any]


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
    if snapshot.readme_path != README_PATH:
        raise CorrectionError(
            f"{entry.repository} has README {snapshot.readme_path!r}; a correction patches "
            f"{README_PATH} only (insufficient evidence for a placeholder, no README to correct)"
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
    facts = read_facts(facts_path)
    if facts.repository != entry.repository or facts.source_revision != clone.revision:
        raise CorrectionError(
            f"facts are for {facts.repository} @ {facts.source_revision}, but the registry head "
            f"is {entry.repository} @ {clone.revision}; extract facts at the head and retry"
        )
    ctx = Context(entry, facts, text, tuple(list_tree_paths(clone.path)), snapshot.readme_path)
    result = correct(ctx)
    delta = validation_delta(ctx, result.corrected, original)
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
        edits=len(result.edits),
        summary=dict(manifest["summary"]),
        unapplied=len(result.findings),
        manifest=manifest,
    )
