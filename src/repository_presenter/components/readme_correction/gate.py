"""The propose gate for a correction: an explicit, typed alternative to a regenerated candidate's.

A regenerated candidate is proposable once an honest independent review, a measured zero-call
no-op proof and a ratified acceptance score all hold (``core/candidates.py::proposal_gate_refusal``,
untouched). A correction has no model to review and no prose to score; the honest equivalents,
each *recomputed here from the bundle's own bytes* rather than read back from a claim, are:

* review  -> the diff touches only enumerated, evidenced edits: re-running the engine on the
  bundle's original README, facts and tree reproduces ``README.md`` and every edit exactly, and the
  engine's confinement proof (nothing outside an edit changed) holds;
* no-op   -> that re-run is byte-identical, a run over the corrected text finds nothing more to
  correct, and no provider is on the path at all;
* acceptance -> the shared judges (``validate_candidate``) fail no check more often on the
  corrected text than on the live one.

``load_proposable_correction`` returns the same ``ProposableCandidate`` the regenerated loader does,
so everything after it (source-revision recheck, authorization record, the PR effect) is shared.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import CorrectionError, correct
from repository_presenter.components.readme_correction.model import (
    EDIT_KINDS,
    KIND_CORRECTION,
    KIND_FIELD,
    Context,
)
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.candidates import BundleError, ProposableCandidate, verify_bundle
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.facts import FACTS_FILENAME, read_facts
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.loader import load_registry, require_listed
from repository_presenter.core.registry.models import RegistryEntry

_REGISTRY_RELATIVE_PATH = Path("data") / "registry.json"
#: The polarity the facts behind each kind must have: a fix is dictated by a SUPPORTED fact, a
#: broken link by the CONTRADICTED link fact that records the target missing.
_EVIDENCE_POLARITY = {
    "FALSE_CLAIM_FIX": "SUPPORTED",
    "MISSING_SECTION": "SUPPORTED",
    "BROKEN_LINK": "CONTRADICTED",
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def correction_refusal(bundle: Path, manifest: dict[str, Any], entry: RegistryEntry) -> str | None:
    """Why ``bundle`` is not a proven correction, or None. Pure: reads only the bundle."""
    if manifest.get(KIND_FIELD) != KIND_CORRECTION or manifest.get("state") != files.STATE:
        return f"the manifest is not a {KIND_CORRECTION} bundle in state {files.STATE}"
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
        original_text = original.decode("utf-8")
    except (OSError, ValueError) as exc:
        return f"the bundle cannot be read back: {exc}"
    if manifest.get("original_sha256") != files.sha256(original):
        return "the manifest's original_sha256 is not the stored original README"
    if manifest.get("corrected_sha256") != files.sha256(stored):
        return "the manifest's corrected_sha256 is not the stored corrected README"
    if facts.source_revision != manifest.get("revision") or facts.repository != manifest.get(
        "repository"
    ):
        return "facts.json is for another repository or revision than the manifest"
    ctx = Context(entry, facts, original_text, tree, str(manifest.get("readme_path", "README.md")))
    try:
        again = correct(ctx)
    except (CorrectionError, ValueError) as exc:
        return f"re-running the correction fails: {exc}"
    if again.corrected.encode("utf-8") != stored:
        return "re-running the correction does not reproduce README.md byte for byte"
    stored_edits = [
        (e["kind"], e["detector"], e["start"], e["end"], e["original"], e["replacement"])
        for e in document.get("edits", [])
    ]
    derived_edits = [
        (e.kind, e.detector, e.start, e.end, e.original, e.replacement) for e in again.edits
    ]
    if stored_edits != derived_edits:
        return "corrections.json does not list exactly the edits the correction makes"
    for edit in again.edits:
        if edit.kind not in EDIT_KINDS:
            return f"edit kind {edit.kind!r} is outside the closed set"
        wanted = _EVIDENCE_POLARITY[edit.kind]
        for fact_id in edit.fact_ids:
            fact = ctx.fact(fact_id)
            if fact is None or fact.polarity != wanted:
                return f"{edit.detector} cites {fact_id} which is not a {wanted} fact"
    if correct(Context(entry, facts, again.corrected, tree, ctx.readme_path)).edits:
        return "a run over the corrected README finds further corrections: the result is not final"
    if not again.edits:
        return "the bundle makes no correction; there is nothing to propose"
    delta = validation_delta(ctx, again.corrected, original)
    if delta["introduced"]:
        introduced = ", ".join(item["check"] for item in delta["introduced"])
        return (
            f"the correction introduces failing checks the live README did not have: {introduced}"
        )
    return None


def load_proposable_correction(bundle: Path, repository: str, *, root: Path) -> ProposableCandidate:
    """The corrected README of ``bundle`` as the one thing a proposal may carry, or a typed refusal.

    ``bundle`` is the directory ``correct-readme --out`` wrote; ``root`` is the control repository
    (its registry names the entry the renderer's ecosystem vocabulary comes from)."""
    try:
        manifest = verify_bundle(bundle)
    except BundleError as exc:
        raise WriteRefusedError(Refusal.BUNDLE_INCONSISTENT, str(exc)) from exc
    if manifest is None:
        raise WriteRefusedError(Refusal.BUNDLE_MISSING, f"{bundle} holds no sealed bundle")
    if manifest.get("repository") != repository:
        raise WriteRefusedError(
            Refusal.BUNDLE_INCONSISTENT,
            f"the bundle is for {manifest.get('repository')!r}, not {repository}",
        )
    try:
        entry = require_listed(load_registry(root / _REGISTRY_RELATIVE_PATH), repository)
    except PresenterError as exc:
        raise WriteRefusedError(Refusal.REGISTRY_NOT_LISTED, str(exc)) from exc
    reason = correction_refusal(bundle, manifest, entry)
    if reason is not None:
        raise WriteRefusedError(Refusal.CORRECTION_NOT_PROVEN, f"{repository}: {reason}")
    text = (bundle / files.README_NAME).read_bytes().decode("utf-8")
    return ProposableCandidate(
        repository=repository,
        revision=str(manifest["revision"]),
        readme_text=text,
        candidate_hash=sha256_text(text),
        bundle=bundle,
    )
