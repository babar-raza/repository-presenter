"""M1, M2, M3 and the v1 reproduction: what the ledger of each sealed bundle accounts for.

Everything is read from the pinned bundle files. The judge's clause readers are cited by name and
used read-only (``_Bundle``, ``_kept_text_present``, ``read_doc``, ``heading_key``, ``KEPT``,
``_MARKDOWN``); the decisions below (what counts as computed evidence, what counts as a coverage
proof) are this module's own, so the harness does not grade the pipeline with the pipeline's own
rules. No import of validation, reconciliation or composition.

Definitions (frozen in ``ledger_baseline_v2.json``):

* a live unit is an ``inherited_unit`` fact of the bundle; a unit whose disposition is
  ``NON_CONTENT`` is set aside; a unit with no disposition counts as not accounted;
* ACCOUNTED = the unit's text is byte-identical in the candidate README (whitespace runs aside, a
  heading by its words in any level and case: the judge's ``_kept_text_present``), or it is removed
  with computed evidence: an ``OMIT_UNSUPPORTED``, ``CORRECT_WITH_EVIDENCE`` or ``VERIFIED_REWRITE``
  disposition citing a fact whose polarity is CONTRADICTED (a failed execution receipt or a link
  the probe found missing), or a ``SUPERSEDE_REDUNDANT`` with an M3 coverage proof;
* ``DEFER_UNRESOLVED`` and a kept unit whose text is not printed count as not accounted;
* M1 = accounted / all non-NON_CONTENT live units;
* M2 = ``OMIT_UNSUPPORTED`` rows with no CONTRADICTED evidence;
* M3 = ``SUPERSEDE_REDUNDANT`` rows with no coverage proof: the destination section of the
  candidate carries at least ``M3_THRESHOLD`` of the unit's identifier and word tokens.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from repository_presenter.components.readme.acceptance import judge

from .pinned import PinnedBundle

M3_THRESHOLD = 0.8
TOKENISER = "m3-tokens-v1"
NON_CONTENT = "NON_CONTENT"
SUPERSEDE = "SUPERSEDE_REDUNDANT"
OMIT = "OMIT_UNSUPPORTED"
DEFER = "DEFER_UNRESOLVED"
EVIDENCE_REMOVALS = frozenset({OMIT, "CORRECT_WITH_EVIDENCE", "VERIFIED_REWRITE"})

# plan/disposition section ids that do not map to a heading by name (README standard element ids
# differ from the plan's section ids for two sections).
SECTION_HEADINGS: dict[str, str] = {
    "navigation": "Navigation",
    "at_a_glance": "At a Glance",
    "key_capabilities": "Key Capabilities",
    "installation": "Installation",
    "dependencies": "Dependencies",
    "quick_start": "Quick Start",
    "additional_examples": "Additional Examples",
    "api_reference": "API Reference",
    "documentation_resources": "Documentation & Resources",
    "scope_limitations": "Scope and Limitations",
    "development_testing": "Development and Testing",
    "third_party_notices": "Third-Party Notices",
    "license": "License",
}
# Sections that have no H2 of their own: the lead (H1, badges, banner, opening) ...
LEAD_SECTIONS = frozenset({"identity", "badges", "banner", "opening"})
# ... and one unheaded paragraph that may sit in any section: measured over the whole document.
WHOLE_DOCUMENT_SECTIONS = frozenset({"enterprise_relationship"})

_WORD = re.compile(r"[a-z0-9]{2,}")
_IDENTIFIER = re.compile(
    r"[A-Za-z0-9_]+(?:[.\-/][A-Za-z0-9_]+)+|[A-Za-z][a-z0-9]*[A-Z][A-Za-z0-9]*|[A-Za-z0-9]+_[A-Za-z0-9_]+"
)


def tokens(text: str) -> frozenset[str]:
    """Identifier tokens (dotted, hyphenated, camel-case, snake-case; whole) and word tokens
    (lower case, two characters or more), as one set."""
    found = {match.group(0).lower() for match in _IDENTIFIER.finditer(text)}
    found.update(_WORD.findall(text.lower()))
    return frozenset(found)


def unit_kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1] if "." in unit_id else "unknown"


def section_texts(readme: str) -> dict[str, str]:
    """H2 heading key -> the text under it until the next H2 (nested headings included), plus
    ``''`` -> the lead before the first H2. Read with the judge's markdown reader."""
    lines = readme.splitlines()
    tokens_ = judge._MARKDOWN.parse(readme)
    starts: list[tuple[int, str]] = []
    for index, token in enumerate(tokens_):
        if token.type == "heading_open" and token.tag == "h2" and token.map:
            starts.append((token.map[0], judge.heading_key(judge._inline_text(tokens_[index + 1]))))
    sections: dict[str, str] = {}
    first = starts[0][0] if starts else len(lines)
    sections[""] = "\n".join(lines[:first])
    for position, (begin, key) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        sections[key] = sections.get(key, "") + "\n".join(lines[begin:end]) + "\n"
    return sections


def destination_text(destination: str | None, sections: dict[str, str], readme: str) -> str | None:
    """The README text the destination section names, or None when it cannot be located."""
    if destination is None:
        return None
    if destination in LEAD_SECTIONS:
        return sections.get("", "")
    if destination in WHOLE_DOCUMENT_SECTIONS:
        return readme
    heading = SECTION_HEADINGS.get(destination)
    if heading is None:
        return None
    return sections.get(judge.heading_key(heading))


def coverage(unit_text: str, destination: str | None) -> float:
    """Share of the unit's tokens found in the destination text (0.0 when it is not located)."""
    wanted = tokens(unit_text)
    if destination is None or not wanted:
        return 0.0 if destination is None else 1.0
    return len(wanted & tokens(destination)) / len(wanted)


@dataclass(frozen=True)
class UnitAccount:
    unit_id: str
    kind: str
    disposition: str | None
    destination: str | None
    present: bool
    contradicted: tuple[str, ...]  # cited fact ids with polarity CONTRADICTED
    cited: int
    coverage: float | None  # SUPERSEDE only
    located: bool

    @property
    def accounted(self) -> bool:
        if self.disposition is None or self.disposition == DEFER:
            return False
        if self.present:
            return True
        if self.disposition in EVIDENCE_REMOVALS:
            return bool(self.contradicted)
        if self.disposition == SUPERSEDE:
            return self.coverage is not None and self.coverage >= M3_THRESHOLD
        return False


def unit_accounts(bundle: PinnedBundle) -> list[UnitAccount]:
    sealed = bundle.sealed
    units = sealed.inherited_units() or {}
    rows: dict[str, list[dict[str, Any]]] = {}
    for row in sealed.disposition_rows() or []:
        rows.setdefault(str(row.get("unit_id", "")), []).append(row)
    doc = judge.read_doc(bundle.readme)
    sections = section_texts(bundle.readme)
    accounts: list[UnitAccount] = []
    for unit_id, text in units.items():
        found = rows.get(unit_id, [])
        row = found[0] if len(found) == 1 else None
        disposition = None if row is None else str(row.get("disposition"))
        if disposition == NON_CONTENT:
            continue
        fact_ids = [str(i) for i in (row or {}).get("fact_ids") or []]
        contradicted = tuple(
            i for i in fact_ids if bundle.facts_by_id.get(i, {}).get("polarity") == "CONTRADICTED"
        )
        destination = None if row is None else row.get("destination_section")
        score: float | None = None
        located = True
        if disposition == SUPERSEDE:
            where = destination_text(destination, sections, bundle.readme)
            located = where is not None
            score = coverage(text, where)
        accounts.append(
            UnitAccount(
                unit_id,
                unit_kind(unit_id),
                disposition,
                destination if isinstance(destination, str) else None,
                judge._kept_text_present(unit_id, text, bundle.readme, doc),
                contradicted,
                len(fact_ids),
                score,
                located,
            )
        )
    return accounts


@dataclass(frozen=True)
class LedgerMetrics:
    units: int  # non-NON_CONTENT live units
    accounted: int
    m1: float
    m2: int  # OMIT_UNSUPPORTED with no CONTRADICTED evidence
    omit_unsupported: int
    omit_without_fact: int
    m3: int  # SUPERSEDE_REDUNDANT with no coverage proof
    supersede: int
    supersede_unlocated: int
    defer: int
    unaccounted_by_disposition: dict[str, int]

    def to_json(self) -> dict[str, Any]:
        return {
            "units": self.units,
            "accounted": self.accounted,
            "m1": round(self.m1, 6),
            "m2": self.m2,
            "omit_unsupported": self.omit_unsupported,
            "omit_unsupported_without_fact": self.omit_without_fact,
            "m3": self.m3,
            "supersede_redundant": self.supersede,
            "supersede_destination_unlocated": self.supersede_unlocated,
            "defer_unresolved": self.defer,
            "unaccounted_by_disposition": dict(sorted(self.unaccounted_by_disposition.items())),
        }


def ledger_metrics(accounts: Iterable[UnitAccount]) -> LedgerMetrics:
    rows = list(accounts)
    accounted = sum(1 for row in rows if row.accounted)
    omit = [row for row in rows if row.disposition == OMIT]
    supersede = [row for row in rows if row.disposition == SUPERSEDE]
    missing = Counter(str(row.disposition) for row in rows if not row.accounted)
    return LedgerMetrics(
        units=len(rows),
        accounted=accounted,
        m1=accounted / len(rows) if rows else 1.0,
        m2=sum(1 for row in omit if not row.contradicted),
        omit_unsupported=len(omit),
        omit_without_fact=sum(1 for row in omit if row.cited == 0),
        m3=sum(1 for row in supersede if (row.coverage or 0.0) < M3_THRESHOLD),
        supersede=len(supersede),
        supersede_unlocated=sum(1 for row in supersede if not row.located),
        defer=sum(1 for row in rows if row.disposition == DEFER),
        unaccounted_by_disposition=dict(missing),
    )


# --- the v1 totals (ledger_baseline.json), reproduced ------------------------------------------


def v1_bundle(bundle: PinnedBundle) -> dict[str, Any]:
    """The per-bundle numbers of ``evidence/lane-r-dependability/ledger_baseline.json``, derived
    the way its ``method`` says: kept = VERIFIED_PRESERVE | VERIFIED_MOVE, printed =
    ``_kept_text_present``."""
    sealed = bundle.sealed
    units = sealed.inherited_units() or {}
    rows = sealed.disposition_rows() or []
    doc = judge.read_doc(bundle.readme)
    kept = [row for row in rows if row.get("disposition") in judge.KEPT]
    not_printed = [
        row
        for row in kept
        if str(row.get("unit_id")) in units
        and not judge._kept_text_present(
            str(row["unit_id"]), units[str(row["unit_id"])], bundle.readme, doc
        )
    ]
    omit = [row for row in rows if row.get("disposition") == OMIT]
    return {
        "units": len(units),
        "kept": len(kept),
        "kept_not_printed": len(not_printed),
        "omit_unsupported": len(omit),
        "omit_unsupported_without_fact": sum(1 for row in omit if not row.get("fact_ids")),
        "supersede_redundant": sum(1 for row in rows if row.get("disposition") == SUPERSEDE),
    }


V1_KEYS = (
    "units",
    "kept",
    "kept_not_printed",
    "omit_unsupported",
    "omit_unsupported_without_fact",
    "supersede_redundant",
)


def v1_totals(bundles: Iterable[PinnedBundle]) -> dict[str, int]:
    total = dict.fromkeys(V1_KEYS, 0)
    for bundle in bundles:
        for key, value in v1_bundle(bundle).items():
            total[key] += value
    return total


def judge_verdicts(bundles: Iterable[PinnedBundle]) -> dict[str, judge.JudgeVerdict]:
    """The judge's verdict on each pinned bundle (repository -> verdict), with the live-README
    applicability the survey records. Reads ``data/readme_standard`` from the working tree."""
    verdicts: dict[str, judge.JudgeVerdict] = {}
    for bundle in bundles:
        inputs = judge._Inputs(
            bundle.sealed, judge.live_is_standard_for(bundle.repository), judge.DATA_DIR
        )
        clauses = tuple(run(inputs) for _, run in judge.CLAUSES)
        failing = tuple(c.id for c in clauses if c.status in judge.NOT_PASSING)
        verdicts[bundle.repository] = judge.JudgeVerdict(not failing, clauses, failing)
    return verdicts
