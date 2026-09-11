"""The cross-file governance invariants tools/reviewer/reviewer_check.py checked only while a
reviewer session was awake, promoted into CI (PHASE1/F8).

The sprint diagnosis (plans/sprint/PHASE1-SPRINT-PLAN.md section 1, D): enforcement was split,
with cross-file checks living only in mortal tools/. ``repo_checks()`` there reads the cursor,
section 27.9, the ESM, the contract and the budgets and prints ``[FLAG]`` lines - but only when
the reviewer wakes, and it went dark 2026-09-06 to 09-11 with every monitor. What follows is the
deterministic, file-reading subset of those checks, restated as tests over the tree as committed:
no transcript, no git history, no gh, no clock. What stays in tools/ is what needs those (time-box
overrun, growth signals, section 31 flags, PR age). ``reviewer_check.py`` itself is not imported -
it resolves a transcript path at import time - so the rules are ported, each as a pure function a
synthetic red-before test holds to its own meaning.

Already covered elsewhere, deliberately not duplicated: the cursor validates against its schema
(test_schemas.py); a queued purpose equals section 27.9's text and every stated entry is queued,
active or accepted (test_queue_agreement.py); ``audit_second_reader_ledger`` is promoted in
test_bundle_audits.py (91f74be) and holds on every sealed manifest directory today.

Two rules read evidence against the tree rather than text against text. ``test_gate_evidence_
matches_disk``: a gate manifest's cohort row that says ``SEALED`` must resolve, through that
repository's own ``candidates/<owner>__<name>/CURRENT`` pointer, to a bundle in a counted state -
the G4 manifest's 3D-.NET row said ``SEALED`` for five days after f8e3bf0 deleted the bundle
(amended by PHASE1/F3 to ``SEALED_THEN_UNSEALED``), and nothing read the two against each other.
The ceiling rule: the portfolio ceiling is derived from ``data/registry.json`` (PHASE1/F3 replaced
a hardcoded ``31/31`` that stood five days after item 31 re-enabled PDF-TS), so no governance
prose restates it as a literal. Today's residue lives in dated RESEARCH sections whose text is the
owner's; each is strict-xfailed per section so a new restatement in a clean section fails loudly
and a clean-up of a listed one shows as XPASS, exactly as test_bundle_audits.py pins its own.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.candidates import COUNTED_STATES
from repository_presenter.core.registry.loader import enabled_entries, load_registry
from support import REPO_ROOT, write_bundle
from test_queue_agreement import RESEARCH, queue_entries, state

ESM = REPO_ROOT / "docs" / "EXECUTION_STATE_MACHINE.md"
CONTRACT = REPO_ROOT / "docs" / "README_CONTRACT.md"
AGENTS = REPO_ROOT / "AGENTS.md"
REGISTRY = REPO_ROOT / "data" / "registry.json"
EVIDENCE = REPO_ROOT / "evidence" / "build"
CANDIDATES = REPO_ROOT / "candidates"
LANES = REPO_ROOT / "project" / "lanes"
NL = chr(10)

# Loop-prompt section 6 rule 14: blocking checks stay at most fifteen without an owner decision in
# section 27.9. The rule's own constant, cited rather than restated anywhere else.
BLOCKING_CHECK_CAP = 15


# --- queue order and narrative (section 27.9) ---------------------------------------------------


def section_27_9_narrative() -> str:
    """The order narrative section 27.9 states before its one YAML block."""
    section = RESEARCH.read_text("utf-8").split("### 27.9 Queue", 1)[1].split(NL + "### ", 1)[0]
    return section.split("```yaml", 1)[0]


def test_the_queue_keeps_section_27_9s_relative_order() -> None:
    """Loop-prompt section 2: list order is execution order and section 27.9 is its source.

    The reviewer re-derived which entries had been worked from six hundred commit subjects
    before comparing; the deterministic core is that the entries still queued appear in the
    same relative order section 27.9 states them in.
    """
    queued = [item["id"] for item in state()["next_ready_items"]]
    stated = [entry["id"] for entry in queue_entries() if entry["id"] in queued]
    assert queued == stated, f"state.yaml queues {queued}; section 27.9 orders them {stated}"


def test_every_queued_item_is_named_in_section_27_9s_order_narrative() -> None:
    """An entry the YAML block carries but the narrative never places has no stated position."""
    narrative = section_27_9_narrative()
    expanded = {
        f"{gate}-W{number:02d}"
        for gate, low, high in re.findall(r"(G\d)-W(\d+) to G\d-W(\d+)", narrative)
        for number in range(int(low), int(high) + 1)
    }
    unnamed = [
        item["id"]
        for item in state()["next_ready_items"]
        if item["id"] not in narrative and item["id"] not in expanded
    ]
    assert unnamed == [], f"queued but absent from section 27.9's order narrative: {unnamed}"


# --- budgets and caps ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "key"),
    [(AGENTS, "agents_md_max_lines"), (ESM, "execution_state_machine_max_lines")],
    ids=["AGENTS.md", "EXECUTION_STATE_MACHINE.md"],
)
def test_a_governance_document_stays_within_its_line_budget(path: Path, key: str) -> None:
    """Loop-prompt section 0: budgets are hard; the cursor's execution_limits carry the numbers."""
    cap = state()["execution_limits"]["governance_budget"][key]
    lines = len(path.read_text("utf-8").splitlines())
    assert lines <= cap, f"{path.name} is {lines} lines against its budget of {cap}"


def blocking_check_rows() -> list[str]:
    """The numbered rows of README_CONTRACT.md section 5."""
    contract = CONTRACT.read_text("utf-8")
    section = contract.split(NL + "## 5. Blocking checks", 1)[1].split(NL + "## ", 1)[0]
    return re.findall(r"^\| (\d+) \|", section, re.M)


def test_the_contract_carries_at_most_fifteen_blocking_checks() -> None:
    rows = blocking_check_rows()
    assert rows, "section 5 of the contract states no numbered rows; the cap would hold vacuously"
    assert len(rows) <= BLOCKING_CHECK_CAP, (
        f"{len(rows)} blocking checks exceed rule 14's cap of {BLOCKING_CHECK_CAP}: {rows}"
    )


# --- limits versus decisions --------------------------------------------------------------------


def test_lane_work_agrees_with_the_cursors_parallelism_limit() -> None:
    """A lane file under project/lanes/ or a queued purpose that plans lanes is the decision;
    ``execution_limits.parallel_repository_work_allowed`` is the cursor's statement of it. The
    reviewer flagged the two disagreeing; here they must agree on the tree as committed."""
    cursor = state()
    planned = [
        item["id"]
        for item in cursor["next_ready_items"]
        if re.search(r"\blanes?\b", item["purpose"])
    ]
    lanes = sorted(path.name for path in LANES.glob("*.yaml"))
    if planned or lanes:
        assert cursor["execution_limits"]["parallel_repository_work_allowed"] is True, (
            f"parallel_repository_work_allowed is false while lanes exist ({lanes}) or are "
            f"planned by {planned}"
        )


# --- the cursor's gate purpose versus the ESM ---------------------------------------------------

# A quantified predicate as the gate purposes phrase them ("at least 85 percent", "under three
# minutes", "blocking coverage check"); the ESM may spell the same bound with a symbol.
QUANTIFIED = re.compile(
    r"(?:at least|at most|under)\s+\w+\s+(?:percent|minutes)|blocking coverage check"
)


def esm_gate_section(gate_id: str) -> str:
    """The ESM's own section for a gate id such as G3_PYTHON_COHORT (its heading is ``## G3 —``)."""
    label = gate_id.split("_", 1)[0]
    match = re.search(rf"(?ms)^## {label} — .*?(?=^## |\Z)", ESM.read_text("utf-8"))
    assert match, f"the ESM has no `## {label} —` section for {gate_id}"
    return match.group(0)


def dropped_predicates(purpose: str, gate_section: str) -> list[str]:
    """Quantified predicates the purpose states that the gate's ESM section no longer carries."""
    dropped = []
    for phrase in QUANTIFIED.findall(purpose):
        key = re.sub(r"\s+", " ", phrase)
        symbolic = key.replace("at least ", "≥").replace(" percent", "%").replace("at most ", "≤")
        if key not in gate_section and symbolic not in gate_section:
            dropped.append(key)
    return dropped


def test_the_current_gate_has_its_esm_section_with_exit_predicates() -> None:
    """Loop-prompt section 0 names the current gate's ESM section as authority; it must exist."""
    section = esm_gate_section(state()["current_gate"]["id"])
    assert "### Exit predicates" in section


def test_the_cursors_gate_purpose_states_no_predicate_the_esm_dropped() -> None:
    """The purpose is a copy of the ESM's bounds; a copy with no reader drifts (section 1, C)."""
    gate = state()["current_gate"]
    assert dropped_predicates(gate["purpose"], esm_gate_section(gate["id"])) == []


def test_the_gate_purpose_rule_flags_a_dropped_bound_and_admits_a_symbolic_one() -> None:
    purpose = "accepts at least 85 percent first attempt and completes under three minutes"
    assert dropped_predicates(purpose, "... ≥85% first attempt ... under three minutes ...") == []
    assert dropped_predicates(purpose, "... ≥85% first attempt ...") == ["under three minutes"]
    assert dropped_predicates(purpose, "") == ["at least 85 percent", "under three minutes"]


# --- gate evidence versus disk ------------------------------------------------------------------


def sealed_rows(node: Any, path: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Every cohort row anywhere in a gate manifest whose outcome is exactly ``SEALED``.

    Walked rather than addressed by key: G3 keeps its rows under ``cohort.sealed_candidates``,
    G4 under ``cohort``, and a later gate may nest them again. A reversed row reads
    ``SEALED_THEN_UNSEALED`` (the F3 amendment) and is a record of something that no longer
    holds, so it is not a claim against the disk.
    """
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(node, dict):
        if node.get("outcome") == "SEALED" and isinstance(node.get("repository"), str):
            found.append((path, node))
        for key, value in node.items():
            found.extend(sealed_rows(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(sealed_rows(value, f"{path}[{index}]"))
    return found


def current_state(candidates: Path, repository: str) -> str | None:
    """The manifest state of the bundle ``CURRENT`` names for ``repository``; None when no live
    pointer resolves to a sealed bundle (seal.py's ``candidates/<owner>__<name>``, inverted)."""
    current = candidates / repository.replace("/", "__") / "CURRENT"
    if not current.is_file():
        return None
    manifest = current.parent / current.read_text("utf-8").strip() / "manifest.json"
    if not manifest.is_file():
        return None
    return str(json.loads(manifest.read_text("utf-8")).get("state"))


def unbacked_sealed_rows(manifest: dict[str, Any], candidates: Path) -> list[str]:
    """The repositories a manifest records as SEALED whose CURRENT bundle is not in a counted
    state - a gate's evidence claiming a candidate the disk no longer carries."""
    return [
        f"{path}: {row['repository']}"
        for path, row in sealed_rows(manifest)
        if current_state(candidates, row["repository"]) not in COUNTED_STATES
    ]


def gate_manifests() -> list[Path]:
    return sorted(EVIDENCE.glob("*/manifest.json"))


def test_there_is_at_least_one_sealed_row_to_hold_to_the_disk() -> None:
    rows = [
        row
        for manifest in gate_manifests()
        for row in sealed_rows(json.loads(manifest.read_text("utf-8")))
    ]
    assert rows, "no gate manifest records a SEALED row; the disk check would pass vacuously"


@pytest.mark.parametrize("manifest", gate_manifests(), ids=lambda path: path.parent.name)
def test_gate_evidence_matches_disk(manifest: Path) -> None:
    record = json.loads(manifest.read_text("utf-8"))
    assert unbacked_sealed_rows(record, CANDIDATES) == []


def test_a_sealed_row_whose_pointer_is_gone_or_unproven_is_reported(tmp_path: Path) -> None:
    """Red-before on the F3 shape: a SEALED row with no CURRENT (the deleted 3D-.NET bundle), and
    one whose pointer names a bundle sealed but not yet counted; the reversed spelling and a live
    counted bundle are clean."""
    manifest = {
        "cohort": [
            {"repository": "owner/live", "outcome": "SEALED"},
            {"repository": "owner/gone", "outcome": "SEALED"},
            {"repository": "owner/unproven", "outcome": "SEALED"},
            {"repository": "owner/reversed", "outcome": "SEALED_THEN_UNSEALED"},
        ],
        "second_pass": {"report": [{"repository": "owner/nested", "outcome": "SEALED"}]},
    }
    write_bundle(tmp_path, "owner__live", "a" * 40, "READY_FOR_PROPOSAL")
    write_bundle(tmp_path, "owner__unproven", "b" * 40, "ACCEPTED")
    write_bundle(tmp_path, "owner__nested", "c" * 40, "READY_FOR_PROPOSAL")
    assert unbacked_sealed_rows(manifest, tmp_path / "candidates") == [
        ".cohort[1]: owner/gone",
        ".cohort[2]: owner/unproven",
    ]


# --- the portfolio ceiling is derived, never restated ------------------------------------------


def portfolio_ceiling() -> tuple[int, int]:
    """``(ceiling, denominator)`` as the registry derives them: enabled entries, all entries."""
    registry = load_registry(REGISTRY)
    return len(enabled_entries(registry)), len(registry.entries)


def ceiling_restatements(text: str, ceiling: int, denominator: int) -> list[str]:
    """Every phrase that states the portfolio ceiling as a literal number.

    Two shapes, both taken from what PHASE1/F3 removed from the ESM: the all-of-them fraction
    (``31/31 local``, ``31/31 READMEs``) for any number but the frozen denominator - a ``34/34``
    counts dispositions, which every entry gets, and ``1/1`` is a single item, never a portfolio;
    and the currently derived ceiling as a counted noun (``32 READMEs``). A stale ceiling in the
    counted-noun form alone is not caught; in the ESM's own history the two forms travelled
    together on adjacent lines, and the fraction form is what the census predicate was written in.
    """
    found = []
    for match in re.finditer(r"\b(\d+)/(\d+)\b", text):
        number = int(match.group(1))
        if number == int(match.group(2)) and number not in (1, denominator):
            found.append(match.group(0))
    counted_noun = re.compile(rf"\b{ceiling} (?:sealed )?(?:READMEs|candidates)\b")
    found.extend(match.group(0) for match in counted_noun.finditer(text))
    return found


def test_the_ceiling_rule_flags_what_f3_removed_and_admits_the_derived_form() -> None:
    """The exact ESM lines c59121e (PHASE1/F3) replaced, before and after."""
    before = (
        "    G4_MultiLanguageCohorts --> G5_RerunDurabilityAndHosted: 31/31 local, census\n"
        "Goal: 31/31 READMEs and 34/34 dispositions on this machine\n"
    )
    after = (
        "    G4_MultiLanguageCohorts --> G5_RerunDurabilityAndHosted: every enabled entry local\n"
        "Goal: a README for every enabled registry entry (`data/registry.json`, derived) and\n"
        "34/34 dispositions\n"
    )
    assert ceiling_restatements(before, 32, 34) == ["31/31", "31/31"]
    assert ceiling_restatements(after, 32, 34) == []
    assert ceiling_restatements("so the reachable ceiling is 32 READMEs, not 31", 32, 34) == [
        "32 READMEs"
    ]
    assert ceiling_restatements("status prints 10/34; 1/1 accepted; 32 dispositions", 32, 34) == []


def sections(path: Path) -> list[str]:
    """A document split at its ``## `` headings; the first chunk is whatever precedes them."""
    return [chunk for chunk in re.split(r"(?m)^(?=## )", path.read_text("utf-8")) if chunk]


def section_id(document: str, chunk: str) -> str:
    match = re.match(r"## (G\d|\d+)", chunk.split(NL, 1)[0])
    return f"{document} {match.group(1) if match else 'preamble'}"


# Today's residue, each in a dated section whose text is the owner's (loop-prompt section 0: a
# measurement paragraph, never a rewrite). Strict: a clean-up must remove its row.
KNOWN_CEILING_RESTATEMENTS = {
    "RESEARCH 24": (
        "'32/32' twice in the 2026-09 live-portfolio shell comparison: the measured share of the "
        "live READMEs carrying a constant, a dated reading of the portfolio as it stood (PHASE1/F8)"
    ),
    "RESEARCH 27": (
        "'31/31' in 27.0's 'Order to 31/31' bullet (the pre-item-31 ceiling, owner text) and "
        "'32 READMEs' in G4-W17's 27.9 entry quoting item (31)'s own reading - the active item's "
        "text is the owner's to edit, loop-prompt section 2 (PHASE1/F8)"
    ),
    "RESEARCH 28": (
        "'31/31' in 28.3 and 28.5, the 2026-09-04/05 delivery plan written when 31 was the "
        "ceiling: dated owner text (PHASE1/F8)"
    ),
    "RESEARCH 29": (
        "'32 READMEs' and '30/30 clean' in 29.12's 2026-09-06 aspose.org reuse audit: readings "
        "of the second reuse source, the latter its own gate count (PHASE1/F8)"
    ),
    "RESEARCH 30": (
        "'31/31' in 30.7's 2026-09-05 rate projection and 30.8's autonomy ruling: dated owner "
        "text at the 31 ceiling (PHASE1/F8)"
    ),
}


def _section_params() -> list[Any]:
    params = []
    for document, path in (("ESM", ESM), ("RESEARCH", RESEARCH)):
        for chunk in sections(path):
            label = section_id(document, chunk)
            reason = KNOWN_CEILING_RESTATEMENTS.get(label)
            marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
            params.append(pytest.param(chunk, marks=marks, id=label))
    return params


def test_every_known_ceiling_residue_names_a_section_that_exists() -> None:
    known = {
        section_id(doc, c) for doc, p in (("ESM", ESM), ("RESEARCH", RESEARCH)) for c in sections(p)
    }
    stray = sorted(set(KNOWN_CEILING_RESTATEMENTS) - known)
    assert stray == [], f"residue rows name no section in either document: {stray}"


@pytest.mark.parametrize("chunk", _section_params())
def test_no_governance_prose_restates_the_portfolio_ceiling(chunk: str) -> None:
    ceiling, denominator = portfolio_ceiling()
    assert ceiling_restatements(chunk, ceiling, denominator) == []
