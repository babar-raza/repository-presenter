"""The dedup ledger: `{repository, defect_fingerprint} -> {issue_ref, filed_at_revision,
last_observed_state}`.

`docs/investigations/03-issue-tracking.md` section 4 point 3: "A durable local ledger of which
issues this system filed ... independent of GitHub, mapping `{repository, defect fingerprint} ->
{issue number/URL, filed_at revision, last-observed state}` - the natural analog of the per-item
receipts this codebase already keeps at `evidence/build/lanes/<lane>/<ITEM>.json`."

Modeled on that same convention, but without inventing a second on-disk format: the 2026-09-17
15:40 UTC decision-log ruling that unblocked this work item recorded that the handoff schema
(`schemas/upstream-defect-handoff.schema.json`) "already carries the full lifecycle this requires"
- `source_revision` is the filed-at revision, `status` is the last-observed state, `issue_ref` is
`issue_ref`. So the ledger here is a read layer over the handoff artifacts already committed at
`evidence/upstream-defects/<owner>__<name>/<fingerprint>.json`, one row per artifact, rather than a
second, independently-maintained file a future edit could drift out of sync with the artifacts
themselves. This is the dedup primitive investigation section 4 point 2 calls for: before ever
drafting a new handoff for a `{repository, defect_fingerprint}` pair, look it up here first.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repository_presenter.components.readme.upstream_defects.model import (
    Handoff,
    IssueRef,
    load_handoff,
)

UPSTREAM_DEFECTS_DIRNAME = "upstream-defects"
LedgerKey = tuple[str, str]


class LedgerError(ValueError):
    """The on-disk handoff artifacts cannot be reduced to a well-formed ledger."""


@dataclass(frozen=True)
class LedgerEntry:
    """One row: what this system currently knows about one `{repository, defect_fingerprint}`."""

    repository: str
    defect_fingerprint: str
    path: Path
    filed_at_revision: str
    last_observed_state: str
    triggering_check_id: str
    issue_ref: IssueRef | None

    @property
    def key(self) -> LedgerKey:
        return (self.repository, self.defect_fingerprint)

    @classmethod
    def from_handoff(cls, handoff: Handoff, path: Path) -> LedgerEntry:
        return cls(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            path=path,
            filed_at_revision=handoff.source_revision,
            last_observed_state=handoff.status,
            triggering_check_id=handoff.triggering_check.id,
            issue_ref=handoff.issue_ref,
        )


def discover_handoff_paths(upstream_defects_root: Path) -> tuple[Path, ...]:
    """Every committed handoff artifact under `evidence/upstream-defects/`, sorted for
    determinism."""
    if not upstream_defects_root.is_dir():
        return ()
    return tuple(sorted(upstream_defects_root.glob("*/*.json")))


def load_ledger(upstream_defects_root: Path) -> dict[LedgerKey, LedgerEntry]:
    """Build the dedup ledger by reading every handoff artifact on disk.

    Fails closed (`LedgerError`) if two artifacts claim the same `{repository,
    defect_fingerprint}` key - that would make dedup lookups silently non-deterministic, the same
    discipline `core/registry/models.py::validate_stable_identities` already applies to duplicate
    registry entries.
    """
    ledger: dict[LedgerKey, LedgerEntry] = {}
    for path in discover_handoff_paths(upstream_defects_root):
        handoff = load_handoff(path)
        entry = LedgerEntry.from_handoff(handoff, path)
        existing = ledger.get(entry.key)
        if existing is not None:
            raise LedgerError(f"duplicate handoff for {entry.key}: {existing.path} and {path}")
        ledger[entry.key] = entry
    return ledger


def lookup(
    ledger: dict[LedgerKey, LedgerEntry], repository: str, defect_fingerprint: str
) -> LedgerEntry | None:
    """The dedup check: has this exact defect already been recorded for this repository?

    A non-`None` result means a filer must not draft a second handoff for this
    `{repository, defect_fingerprint}` pair, regardless of its current `status` - the fingerprint,
    not the status, is what dedup keys on (investigation section 4 point 1).
    """
    return ledger.get((repository, defect_fingerprint))
