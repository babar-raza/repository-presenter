"""Draft a new upstream-defect handoff automatically, the moment the main pipeline itself proves
one - closing the gap `docs/investigations/12-supervisor-and-production-reassessment.md` section 6
names: `components/issues/` already builds the full handoff lifecycle (`model.py`, `ledger.py`,
`redetect.py`), but until now nothing in `present`'s own validation/invalidation path ever called
into it, so a defect like `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`'s `BC-02` trigraph finding
(`docs/DECISION_LOG.md` 2026-09-23 10:31 UTC) invalidated the sealed bundle and produced nothing a
human could act on, even though the exact confirmed-defect shape this component exists for had just
been found.

Scope, deliberately narrow (`docs/investigations/03-issue-tracking.md` section 3 and section 8's
own open question, which this closes only for the `BC-02` shape; the task's own conservative
instruction - "false positives here would create bogus handoffs"): a check is auto-draft-eligible
only when

1. its `causal_stage` is `EXTRACTING` - the one mechanical signal this codebase already has for
   "about the target repository, not repository-presenter's own composition"
   (`repair/targeted.py`'s `STATE_STAGES` maps only `INVESTIGATING`/`RECONCILING`/`PLANNING`/
   `COMPOSING` to a revisable stage; `EXTRACTING` is structurally unrepairable by revising prose,
   the same rationale `schemas/upstream-defect-handoff.schema.json` already pins `causal_stage`
   to), **and**
2. its `id` is one `redetect.py` already knows how to re-evaluate later (`BC-02` here -
   `NOT_PROCESSABLE` is redetectable too but is a repository-level disposition with no
   `candidates/` bundle and no `invalidate_bundle` call site to hook; wiring it needs its own call
   site, out of this task's scope), **and**
3. the current run's own facts genuinely back it: an `install_command` fact whose `polarity` is
   not `SUPPORTED`, the same fact `BC-02` itself judges (`validation/registry.py::_check_install`).

`causal_stage EXTRACTING` alone is not enough - `BC-01` also raises it for reasons that are about
this codebase's own snapshot/extraction integrity (an unpinned revision, a fact with no evidence),
never about the target repository's content (investigation section 2's own boundary case: "the
sprint's AUD-001-AUD-005 findings are all bugs in repository-presenter's own ... state, never in a
target repository"). Requiring both the stage and a real, non-`SUPPORTED` fact of the exact kind
`BC-02` judges keeps this hook from ever drafting off a check failure that turns out to be
internal, an environment gap, or a toolchain problem here rather than in the target repository.

This module never authorizes a GitHub write and never calls ``gh``: it writes only the same
``evidence/upstream-defects/<owner>__<name>/<fingerprint>.json`` artifact a human could otherwise
draft by hand (`model.py::write_handoff`), always at `status: HANDOFF_PENDING` - a human (or a
later redetection pass) still reviews before anything is ever filed. It respects the dedup
ledger's own `{repository, defect_fingerprint}` key (`ledger.py::lookup`) so redrawing the same
defect on a later run never creates a duplicate artifact.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from repository_presenter.components.issues.ledger import load_ledger, lookup
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    TriggeringCheck,
    write_handoff,
)
from repository_presenter.core.facts import FactKind, FactsDocument

# The only triggering_check.id this hook drafts automatically. Matches redetect.py's own
# registered, bundle-scoped shape exactly - a defect this hook creates is always one a later
# redetection pass can also close. Widening this set needs its own reasoned addition here, in
# module docstring above, plus a matching redetector - never guessed.
_AUTO_DRAFT_CHECK_IDS = frozenset({"BC-02"})
_FACT_KIND_FOR_CHECK: dict[str, FactKind] = {"BC-02": "install_command"}


def eligible_for_handoff(check: Mapping[str, Any]) -> bool:
    """The conservative gate on ``check`` alone (a `validation.json` check record, e.g. the
    ``first`` failing check `cli.py::run_present` already has in hand when it calls
    `bundle/seal.py::invalidate_bundle`): `causal_stage EXTRACTING` and an `id` this hook and
    `redetect.py` both already know how to handle. Does not look at facts - `draft_handoff` below
    additionally requires a genuine, non-`SUPPORTED` fact backing it before ever drafting."""
    return check.get("causal_stage") == "EXTRACTING" and check.get("id") in _AUTO_DRAFT_CHECK_IDS


def _fingerprint(repository: str, check_id: str, signature: str) -> str:
    """sha256 of `{repository, triggering_check.id, a primary-evidence signature}`
    (`schemas/upstream-defect-handoff.schema.json`'s own `defect_fingerprint` description;
    investigation section 4 point 1) - the stable dedup key, independent of wording, so an
    unrelated prose edit to a fact's evidence detail never mints a spurious second handoff for the
    same underlying defect."""
    digest = hashlib.sha256(f"{repository}\n{check_id}\n{signature}".encode()).hexdigest()
    return f"sha256:{digest}"


def draft_handoff(
    *,
    repository: str,
    source_revision: str,
    check: Mapping[str, Any],
    facts: FactsDocument,
) -> Handoff | None:
    """Build one `Handoff` for a check that is auto-draft-eligible and genuinely backed by the
    current run's own facts, or `None` when either bar is not met - fails closed, never guessed
    (`AGENTS.md`: "Preserve uncertainty when evidence cannot resolve it; never invent a
    resolution")."""
    if not eligible_for_handoff(check):
        return None
    kind = _FACT_KIND_FOR_CHECK.get(str(check.get("id")))
    if kind is None:
        return None
    # Deterministic among ties: the lowest fact ID, so two equivalent runs draft the same
    # handoff. `by_kind` returns facts in extraction order, not a stable id order.
    offending = sorted(
        (fact for fact in facts.by_kind(kind) if fact.polarity != "SUPPORTED"),
        key=lambda fact: fact.id,
    )
    if not offending:
        # The check failed for a reason this hook's own fact-kind mapping cannot find backing
        # for in the current run's facts (e.g. a synthetic/unrelated detail, or the check version
        # changed what it judges) - report nothing rather than draft off an assumption.
        return None
    fact = offending[0]
    if not fact.evidence:
        return None
    evidence = tuple(EvidenceEntry(path=e.path, detail=e.detail) for e in fact.evidence)
    signature = f"{fact.id}:{fact.polarity}:{fact.value}"
    fingerprint = _fingerprint(repository, str(check["id"]), signature)
    last_detail = fact.evidence[-1].detail or fact.value
    claim = (
        f"At revision {source_revision}, {repository}'s own {fact.id} is {fact.polarity} "
        f"({last_detail})."
    )
    title = f"{fact.id} is {fact.polarity} at {source_revision[:12]}"
    body_lines = [
        f"repository-presenter's validation pipeline ({check['id']}) found `{fact.id}` "
        f"{fact.polarity} while re-verifying `{repository}` at revision `{source_revision}`.",
        "",
        "## Evidence",
        "",
        *(f"- `{e.path}`: {e.detail}" for e in evidence),
        "",
        f"<!-- repository-presenter-defect: {fingerprint} -->",
    ]
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision=source_revision,
        defect_fingerprint=fingerprint,
        triggering_check=TriggeringCheck(
            id=str(check["id"]), version=str(check.get("version", "1")), causal_stage="EXTRACTING"
        ),
        evidence=evidence,
        claim=claim,
        suggested_issue_title=title,
        suggested_issue_body="\n".join(body_lines) + "\n",
        status="HANDOFF_PENDING",
        issue_ref=None,
    )


def handoff_path(upstream_defects_root: Path, handoff: Handoff) -> Path:
    """`evidence/upstream-defects/<owner>__<name>/<fingerprint>.json` for ``handoff``, the same
    layout `redetect.py`/`ledger.py` already read (`REPOSITORY_LAYOUT.md`)."""
    owner, name = handoff.repository.split("/", 1)
    digest = handoff.defect_fingerprint.split(":", 1)[1]
    return upstream_defects_root / f"{owner}__{name}" / f"{digest}.json"


def record_handoff_if_new(
    upstream_defects_root: Path,
    *,
    repository: str,
    source_revision: str,
    check: Mapping[str, Any],
    facts: FactsDocument,
) -> Path | None:
    """The full automatic path: draft, then dedup against the ledger before ever writing.

    Returns the path written, or `None` when nothing qualified (`draft_handoff` above) or the
    defect is already on record - dedup by `{repository, defect_fingerprint}`
    (`ledger.py::lookup`), the same key a manual filer would check by hand, so redrawing an
    identical defect on a later re-seal attempt never creates a duplicate artifact regardless of
    the handoff's current `status`.
    """
    handoff = draft_handoff(
        repository=repository, source_revision=source_revision, check=check, facts=facts
    )
    if handoff is None:
        return None
    ledger = load_ledger(upstream_defects_root)
    if lookup(ledger, handoff.repository, handoff.defect_fingerprint) is not None:
        return None
    path = handoff_path(upstream_defects_root, handoff)
    write_handoff(handoff, path)
    return path
