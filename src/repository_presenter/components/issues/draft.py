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

Defect classes (G6-W07, TC-ISS-03): the repository defects no validation check names - a license
missing from the root, a license that contradicts the manifest, placeholder manifest metadata, a
missing or placeholder README - are found by the pure detectors registered in ``classes.py`` over
an ``Observation`` the facts stage already has the inputs for, so ``draft_class_handoffs`` /
``record_class_handoffs_if_new`` produce their handoffs from a facts-only extraction, with no
provider call and no network. They go through the same quality gate and the same dedup ledger.

This module never authorizes a GitHub write and never calls ``gh``: it writes only the same
``evidence/upstream-defects/<owner>__<name>/<fingerprint>.json`` artifact a human could otherwise
draft by hand (`model.py::write_handoff`), always at `status: HANDOFF_PENDING` - a human (or a
later redetection pass) still reviews before anything is ever filed. It respects the dedup
ledger's own `{repository, defect_fingerprint}` key (`ledger.py::lookup`) so redrawing the same
defect on a later run never creates a duplicate artifact.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from repository_presenter.components.issues.classes import (
    REGISTRY,
    DefectFinding,
    Observation,
    detect_all,
    fingerprint,
)
from repository_presenter.components.issues.ledger import load_ledger, lookup
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    TriggeringCheck,
    write_handoff,
)
from repository_presenter.components.issues.quality import (
    HandoffQualityError,
    require_issue_quality,
)
from repository_presenter.core.facts import Fact, FactKind, FactsDocument

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
    return fingerprint(repository, check_id, signature)


def _fence(text: str) -> str:
    """``text`` as a fenced block whose fence cannot be closed by the text itself."""
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}\n{text.rstrip()}\n{fence}"


def _issue_text(
    *,
    repository: str,
    source_revision: str,
    fact: Fact,
    evidence: tuple[EvidenceEntry, ...],
    last_detail: str,
    fingerprint: str,
) -> tuple[str, str]:
    """The title and body a maintainer reads: one install route, how to reproduce it, what was
    expected and what happened, in the maintainers' words rather than this system's (the
    quality gate rejects the latter). A ``CONTRADICTED`` fact is a failure; any other polarity is
    only ever reported as unverified, never as a failure nobody observed."""
    route = fact.id.split(":", 1)[-1]
    product = repository.split("/", 1)[-1].replace("-", " ")
    outcome = "fails verification" if fact.polarity == "CONTRADICTED" else "could not be verified"
    commands = [fact.value]
    commands.extend(
        f"curl -s -o /dev/null -w '%{{http_code}}' {e.path}"
        for e in evidence
        if e.path.startswith("https://")
    )
    lines = [
        "## Summary",
        "",
        f"At revision `{source_revision}`, the documented `{route}` install route for "
        f"`{repository}` {outcome}: {last_detail}.",
        "",
        "## Environment",
        "",
        f"- Repository: {repository}",
        f"- Revision: `{source_revision}` (the upstream revision this report was verified against)",
        "",
        "## Steps to reproduce",
        "",
        _fence("\n".join(commands)),
        "",
        "## Expected",
        "",
        "The command above completes without error.",
        "",
        "## Actual",
        "",
        *(f"- `{e.path}`: {e.detail}" for e in evidence),
        "",
        f"<!-- repository-presenter-defect: {fingerprint} -->",
    ]
    return f"{product}: the documented {route} install route {outcome}", "\n".join(lines) + "\n"


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
    resolution").

    Raises ``HandoffQualityError`` (typed findings) when the drafted issue text fails
    ``quality.issue_quality_findings`` - a handoff that fails the gate is never produced."""
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
    title, body = _issue_text(
        repository=repository,
        source_revision=source_revision,
        fact=fact,
        evidence=evidence,
        last_detail=last_detail,
        fingerprint=fingerprint,
    )
    handoff = Handoff(
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
        suggested_issue_body=body,
        status="HANDOFF_PENDING",
        issue_ref=None,
        close_reason=None,
    )
    # The quality gate (quality.py) is the last step: text a maintainer could not act on is never
    # drafted, so it can never reach an approval. The typed refusal carries every finding.
    require_issue_quality(handoff)
    return handoff


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

    Returns the path written, or `None` when nothing qualified (`draft_handoff` above), its text
    failed the quality gate, or the defect is already on record - dedup by
    `{repository, defect_fingerprint}`
    (`ledger.py::lookup`), the same key a manual filer would check by hand, so redrawing an
    identical defect on a later re-seal attempt never creates a duplicate artifact regardless of
    the handoff's current `status`.
    """
    try:
        handoff = draft_handoff(
            repository=repository, source_revision=source_revision, check=check, facts=facts
        )
    except HandoffQualityError:
        # present must never fail on this: text that fails the gate is simply not recorded. The
        # defect is still a defect; it is drafted again on a later run once its evidence reads
        # cleanly, or written by hand and held to the same gate before approval.
        return None
    if handoff is None:
        return None
    ledger = load_ledger(upstream_defects_root)
    if lookup(ledger, handoff.repository, handoff.defect_fingerprint) is not None:
        return None
    path = handoff_path(upstream_defects_root, handoff)
    write_handoff(handoff, path)
    return path


# --- defect classes (G6-W07) ---------------------------------------------------------------------


def eligible_defect_classes(observation: Observation) -> tuple[str, ...]:
    """The class ids whose registered detector reports at least one defect for ``observation``:
    the eligibility gate for the class path, decided from the observation alone."""
    return tuple(dict.fromkeys(finding.defect_class for finding in detect_all(observation)))


def render_class_issue(
    finding: DefectFinding, *, repository: str, source_revision: str, defect_fingerprint: str
) -> tuple[str, str]:
    """The title and body for ``finding``: its class's template filled with the finding's
    fields, in the maintainers' words, ending in the dedup marker."""
    template = REGISTRY[finding.defect_class].template
    if template is None:  # a mapped class has no detector, so never reaches here
        raise ValueError(f"defect class {finding.defect_class} has no issue template")
    product = repository.split("/", 1)[-1].replace("-", " ")
    context = {
        **finding.fields,
        "repository": repository,
        "revision": source_revision,
        "product": product,
    }
    lines = [
        "## Summary",
        "",
        template.summary.format_map(context),
        "",
        "## Environment",
        "",
        f"- Repository: {repository}",
        f"- Revision: `{source_revision}` (the upstream revision this report was verified against)",
        "",
        "## Steps to reproduce",
        "",
        _fence(template.steps.format_map(context)),
        "",
        "## Expected",
        "",
        template.expected.format_map(context),
        "",
        "## Actual",
        "",
        template.actual.format_map(context),
        "",
        f"<!-- repository-presenter-defect: {defect_fingerprint} -->",
    ]
    return f"{product}: {finding.statement}", "\n".join(lines) + "\n"


def draft_class_handoff(finding: DefectFinding, *, observation: Observation) -> Handoff:
    """One ``HANDOFF_PENDING`` handoff for a detector's ``finding``.

    Raises ``HandoffQualityError`` (typed findings) when the rendered text fails the quality gate:
    a handoff that fails the gate is never produced."""
    check_id = finding.defect_class
    defect_fingerprint = fingerprint(observation.repository, check_id, finding.signature)
    title, body = render_class_issue(
        finding,
        repository=observation.repository,
        source_revision=observation.source_revision,
        defect_fingerprint=defect_fingerprint,
    )
    handoff = Handoff(
        schema_version=1,
        repository=observation.repository,
        source_revision=observation.source_revision,
        defect_fingerprint=defect_fingerprint,
        triggering_check=TriggeringCheck(id=check_id, version="1", causal_stage="EXTRACTING"),
        evidence=finding.evidence,
        claim=finding.claim,
        suggested_issue_title=title,
        suggested_issue_body=body,
        status="HANDOFF_PENDING",
        issue_ref=None,
        close_reason=None,
        defect_class=check_id,
    )
    require_issue_quality(handoff)
    return handoff


def draft_class_handoffs(observation: Observation) -> list[Handoff]:
    """Every handoff the registered detectors support for ``observation``, in detection order. A
    finding whose text fails the quality gate is left out, never weakened to pass."""
    handoffs = []
    for finding in detect_all(observation):
        try:
            handoffs.append(draft_class_handoff(finding, observation=observation))
        except HandoffQualityError:
            continue
    return handoffs


def record_class_handoffs_if_new(
    upstream_defects_root: Path, *, observation: Observation
) -> list[Path]:
    """The class path of ``record_handoff_if_new``: draft, dedup against the ledger by
    ``{repository, defect_fingerprint}``, and write only what is new. Returns the paths written."""
    handoffs = draft_class_handoffs(observation)
    if not handoffs:
        return []
    ledger = load_ledger(upstream_defects_root)
    written = []
    for handoff in handoffs:
        if lookup(ledger, handoff.repository, handoff.defect_fingerprint) is not None:
            continue
        path = handoff_path(upstream_defects_root, handoff)
        write_handoff(handoff, path)
        written.append(path)
    return written
