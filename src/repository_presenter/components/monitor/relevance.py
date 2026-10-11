"""Relevance-aware change classification (G7-W06, TC-REF-01): did the upstream change touch
anything this sealed README consumed?

A head change alone is not a reason to re-seal. PDF-Java's release commit moves the head every
release and touches nothing the README states; re-sealing on it is a reseal storm (provider spend,
a PR, a review) for no change in the README's truth. ``classify_change`` is the pure decision:

- ``NO_CHANGE``: the head is still the sealed revision (a git revision is immutable), and no
  recorded dependency's blob id differs.
- ``IRRELEVANT_CHANGE``: the head moved, and no *consumed* path changed.
- ``RELEVANT_CHANGE``: a consumed path changed: the README itself (a maintainer edit), a manifest,
  a source file a fact cites, a protected-content file.
- ``UNKNOWN``: the question cannot be decided from what was read (a tree that is unreadable or
  truncated, a bundle whose facts cannot be read). Never guessed, and never work for a sealing run.
- ``UNREACHABLE``: the head itself could not be read.

What "consumed" means, strongest source first:

1. The bundle's recorded ``upstream_blobs`` (README, license, notices and every file a fact cites,
   with their git blob ids at the sealed revision, ``components/readme/bundle/seal.py``), compared
   with the same paths at the head. When the bundle also records ``consumed_fact_ids`` (the facts
   the candidate README actually consumes; ``manifest.json`` or ``dependencies.json``), a recorded
   path that only unconsumed facts cite is not consumed. Without that field every recorded path is.
2. A conservative fallback for a bundle sealed before blob ids were recorded: the tree listing of
   the sealed revision against the head's, compared only over the paths the sealed ``facts.json``
   cites as evidence (a cited directory compares its whole file listing) plus the repository
   root's README, license and notice files. A repository the facts do not describe is not guessed
   about: no readable ``facts.json`` means ``UNKNOWN``.

The classification reads nothing itself: the caller hands it the sealed scope and the trees it
read, so it is testable with no network. Nothing here calls a provider.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from repository_presenter.core.candidates import UPSTREAM_BLOBS_FIELD
from repository_presenter.core.github.read_client import TreeRead

ChangeClass = Literal["NO_CHANGE", "IRRELEVANT_CHANGE", "RELEVANT_CHANGE", "UNKNOWN", "UNREACHABLE"]
CONSUMED_FACT_IDS_FIELD = "consumed_fact_ids"
FACTS_FILENAME = "facts.json"
DEPENDENCIES_FILENAME = "dependencies.json"
_DETAIL_PATHS = 10
# The repository root's own README, license and notice files: always consumed in the fallback.
_STRUCTURAL = re.compile(r"^(readme|licen[sc]e|notice|copying)([._-][^/]*)?$", re.IGNORECASE)


@dataclass(frozen=True)
class SealedScope:
    """What a sealed bundle recorded about the upstream it consumed.

    ``fact_paths`` maps each fact id to the repository paths its evidence cites (``None`` when the
    bundle's ``facts.json`` could not be read); ``consumed_fact_ids`` is ``None`` when the bundle
    does not record which facts the README consumes (every fact then counts as consumed).
    """

    revision: str
    recorded_blobs: Mapping[str, str]
    fact_paths: Mapping[str, frozenset[str]] | None = None
    consumed_fact_ids: frozenset[str] | None = None

    @property
    def has_blobs(self) -> bool:
        return bool(self.recorded_blobs)


@dataclass(frozen=True)
class LiveObservation:
    """What the monitor read: the head (``None`` when unreadable) and the trees it needed."""

    head_revision: str | None
    head_tree: TreeRead | None = None
    sealed_tree: TreeRead | None = None


@dataclass(frozen=True)
class Classification:
    change: ChangeClass
    detail: str | None = None
    changed_paths: tuple[str, ...] = ()


def needs_head_tree(scope: SealedScope, head_revision: str) -> bool:
    """A head tree is needed to compare recorded blob ids, or whenever the head moved."""
    return scope.has_blobs or head_revision != scope.revision


def needs_sealed_tree(scope: SealedScope, head_revision: str) -> bool:
    """The sealed revision's tree is needed only to decide a moved head with no recorded blobs."""
    return head_revision != scope.revision and not scope.has_blobs


def _cited(evidence: Iterable[Any]) -> frozenset[str]:
    paths: set[str] = set()
    for item in evidence:
        path = item.get("path") if isinstance(item, dict) else None
        # A URL (a link or registry page) is not a repository path: nothing to compare in a tree.
        if isinstance(path, str) and path and "://" not in path:
            paths.add(path)
    return frozenset(paths)


def read_sealed_facts(bundle: Path) -> list[dict[str, Any]] | None:
    """The sealed ``facts.json`` fact records, or ``None`` when unreadable or malformed."""
    try:
        document = json.loads((bundle / FACTS_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    facts = document.get("facts") if isinstance(document, dict) else None
    if not isinstance(facts, list) or not all(isinstance(f, dict) for f in facts):
        return None
    return facts


def _consumed_ids(bundle: Path, manifest: Mapping[str, Any]) -> frozenset[str] | None:
    """``consumed_fact_ids`` from the manifest, else ``dependencies.json``; ``None`` when absent
    or malformed (a malformed field is never read as an empty consumption)."""
    raw: Any = manifest.get(CONSUMED_FACT_IDS_FIELD)
    if raw is None:
        try:
            dependencies = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        raw = dependencies.get(CONSUMED_FACT_IDS_FIELD) if isinstance(dependencies, dict) else None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        return None
    return frozenset(raw)


def load_scope(bundle: Path, revision: str, manifest: Mapping[str, Any]) -> SealedScope:
    """The sealed scope of a verified bundle directory (``manifest`` is its verified manifest)."""
    recorded = manifest.get(UPSTREAM_BLOBS_FIELD)
    blobs: dict[str, str] = {}
    if isinstance(recorded, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in recorded.items()
    ):
        blobs = dict(recorded)
    facts = read_sealed_facts(bundle)
    fact_paths: dict[str, frozenset[str]] | None = None
    if facts is not None:
        fact_paths = {
            str(fact["id"]): _cited(fact.get("evidence") or ())
            for fact in facts
            if isinstance(fact.get("id"), str)
        }
    return SealedScope(revision, blobs, fact_paths, _consumed_ids(bundle, manifest))


def _problem(tree: TreeRead | None, role: str) -> str | None:
    if tree is None:
        return f"{role} tree was not read"
    if tree.error is not None:
        return f"{role} tree unreadable: {tree.error}"
    if tree.truncated:
        return f"{role} tree listing is truncated; consumed content cannot be judged"
    if tree.paths and not tree.blob_shas:
        return f"{role} tree carries no blob ids; consumed content cannot be judged"
    return None


def _consumed_blob_paths(scope: SealedScope) -> set[str]:
    recorded = set(scope.recorded_blobs)
    if scope.consumed_fact_ids is None or scope.fact_paths is None:
        return recorded
    every_cited = set().union(*scope.fact_paths.values()) if scope.fact_paths else set()
    consumed: set[str] = set()
    for fact_id in scope.consumed_fact_ids:
        consumed |= scope.fact_paths.get(fact_id, frozenset())
    # What no fact cites (README, license, notices) is structural: always consumed.
    return (recorded - every_cited) | (recorded & consumed)


def _consumed_cited_paths(scope: SealedScope) -> set[str]:
    assert scope.fact_paths is not None
    if scope.consumed_fact_ids is None:
        return set().union(*scope.fact_paths.values()) if scope.fact_paths else set()
    consumed: set[str] = set()
    for fact_id in scope.consumed_fact_ids:
        consumed |= scope.fact_paths.get(fact_id, frozenset())
    return consumed


def _listing(tree: TreeRead, prefix: str) -> dict[str, str]:
    return {path: sha for path, sha in tree.blob_shas.items() if path.startswith(prefix)}


def _summary(changed: list[str], head: str | None, scope: SealedScope) -> str:
    shown = ", ".join(changed[:_DETAIL_PATHS])
    more = f" (+{len(changed) - _DETAIL_PATHS} more)" if len(changed) > _DETAIL_PATHS else ""
    return f"consumed upstream content changed since {scope.revision[:12]}: {shown}{more}"


def classify_change(scope: SealedScope, live: LiveObservation) -> Classification:
    """Classify the change between the sealed bundle and the live repository. Pure."""
    head = live.head_revision
    if head is None:
        return Classification("UNREACHABLE", "the upstream head could not be read")
    moved = head != scope.revision
    if not scope.has_blobs and not moved:
        # The same git revision has the same content: nothing can differ, no tree needed.
        return Classification("NO_CHANGE")
    if scope.has_blobs:
        return _classify_by_blobs(scope, live, moved)
    return _classify_by_trees(scope, live)


def _classify_by_blobs(scope: SealedScope, live: LiveObservation, moved: bool) -> Classification:
    problem = _problem(live.head_tree, "upstream")
    if problem is not None or live.head_tree is None:
        return Classification("UNKNOWN", problem)
    consumed = _consumed_blob_paths(scope)
    shas = live.head_tree.blob_shas
    changed = sorted(p for p in consumed if shas.get(p) != scope.recorded_blobs[p])
    if changed:
        return Classification(
            "RELEVANT_CHANGE", _summary(changed, live.head_revision, scope), tuple(changed)
        )
    if moved:
        return Classification(
            "IRRELEVANT_CHANGE",
            f"head moved {scope.revision[:12]} -> {(live.head_revision or '')[:12]} but "
            f"none of the {len(consumed)} consumed paths changed",
        )
    return Classification("NO_CHANGE")


def _classify_by_trees(scope: SealedScope, live: LiveObservation) -> Classification:
    if scope.fact_paths is None:
        return Classification(
            "UNKNOWN",
            "the sealed bundle records no upstream blob ids and its facts cannot be read; "
            "consumed paths are undecidable",
        )
    for tree, role in ((live.sealed_tree, "sealed-revision"), (live.head_tree, "upstream")):
        problem = _problem(tree, role)
        if problem is not None:
            return Classification("UNKNOWN", problem)
    sealed_tree, head_tree = live.sealed_tree, live.head_tree
    assert sealed_tree is not None and head_tree is not None
    cited = _consumed_cited_paths(scope)
    structural = {
        path
        for tree in (sealed_tree, head_tree)
        for path in tree.blob_shas
        if "/" not in path and _STRUCTURAL.match(path)
    }
    changed: list[str] = []
    for path in sorted(cited | structural):
        if path.endswith("/"):
            if _listing(sealed_tree, path) != _listing(head_tree, path):
                changed.append(path)
        elif sealed_tree.blob_shas.get(path) != head_tree.blob_shas.get(path):
            changed.append(path)
    if changed:
        return Classification(
            "RELEVANT_CHANGE", _summary(changed, live.head_revision, scope), tuple(changed)
        )
    return Classification(
        "IRRELEVANT_CHANGE",
        f"head moved {scope.revision[:12]} -> {(live.head_revision or '')[:12]} but none of the "
        f"{len(cited | structural)} paths the sealed facts cite changed",
    )
