"""Build and check the labeled corpus (G3-W12 card C1, step 4).

``python -m tools.lane_r_audit corpus build`` writes ``data/lane_r_corpus/cases/*.json`` and
``split.json``; ``corpus check`` rebuilds them in memory and fails on any difference, so a committed
case is always a function of the pinned bundles, the seed and the hand specs below. Nothing here
calls a model or the network: the two registry readings (NuGet, Maven Central, read by hand on
2026-10-19) are stored in the specs as fixtures.

Origins (``corpus.ORIGINS``):

* ``traced``: the cases T1 to T10 of ``evidence/lane-r-dependability/Q_claims.md`` that can be
  re-derived from the pinned bundles. T7 is reproduced for Slides-Cpp only (its live README
  documents a NuGet package, so 'not published on any registry' contradicts it); the PDF-Cpp half
  has no such text in its live README and is listed in ``NOT_REPRODUCED`` rather than guessed.
  T8's test count is renderer-owned README text with no counted fact to check it against, so only
  its symbol-prose half is a case.
* ``hand_found``: defects found by reading the sealed READMEs of the 30 bundles (the lint hits whose
  text is visibly junk: a lead-in colon before the License heading, scraped ``Defined as `: number```
  rows, a ``The  contains`` fragment, a malformed badge). Each carries the sealed text and a
  hand-repaired twin.
* ``ledger``: real rows of the pinned ledgers that M1 to M3 count as not accounted.
* ``mutant``: a seeded defect injected into a clean unit (``mutator.py``).
* ``clean_negative``: a sentence constructed from the values of the facts it cites, so it is true
  by construction (it restates a fact verbatim); a detector that fires on one is a false positive.

Every hand case is audited at build time: the injected text must differ from its twin, the defect
span must be in the injected text and not in the twin, and a case that claims a capability absent
from the evidence must show the span in neither the live README nor any cited fact. A failed audit
raises; nothing is silently dropped.
"""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import corpus, detectors, ledger, mutator
from .corpus import Case, case_to_json
from .detectors import Subject
from .pinned import PinnedBundle, load_pins, read_bundles

SEED = 20261019
MUTANTS_PER_CLASS = 10
MUTANTS_BY_CLASS = {"wrong_identifier": 6}  # a class with no floor needs only enough to measure
NEGATIVES = 22
LEDGER_CASES = {"OMIT_UNSUPPORTED": 8, "SUPERSEDE_REDUNDANT": 6, "KEPT": 6}
READING_DATE = "2026-10-19"

NOT_REPRODUCED: dict[str, str] = {
    "T7 (PDF-Cpp half)": "its live README documents no registry package to contradict the claim",
    "T8 count": "'48 test files' is renderer-owned text with no counted fact in the bundle",
}

_WEAK = frozenset({"identity", "package", "public_symbol", "link_target"})


@dataclass(frozen=True)
class Spec:
    id: str
    origin: str
    cls: str
    name: str  # the repository's short name, e.g. "Aspose.Words-FOSS-for-.NET"
    note: str
    section: str = ""
    slot: str = ""
    old: str = ""  # a span of the unit (or snippet) that is the defect ...
    new: str = ""  # ... and its repair; "" removes it
    clean_text: str | None = None  # the whole repaired text when it is not old -> new
    inherited: tuple[str, ...] = ()  # inherited unit ids whose live text the case carries
    readme_snippet: str = ""  # a README-level case: the defective lines as sealed
    registry: Mapping[str, Any] = field(default_factory=dict)
    absent_from_live: tuple[str, ...] = ()  # spans that must not occur in the live README


HAND: tuple[Spec, ...] = (
    Spec(
        "traced-T1",
        "traced",
        detectors.POLARITY,
        "Aspose.Words-FOSS-for-.NET",
        "Q_claims T1: DOCX/RTF/HTML listed as supported; the live unit 067.list says DOC, RTF, ODT, "
        "HTML and EPUB are not read or written",
        "key_capabilities",
        "capability:2",
        old=", supporting formats such as DOCX, RTF, HTML, and Markdown",
        inherited=("inherited_unit:067.list",),
    ),
    Spec(
        "traced-T2",
        "traced",
        detectors.INVENTED_CAPABILITY,
        "Aspose.Imaging-FOSS-for-.NET",
        "Q_claims T2: 'image transformation' from one fact that is a class name",
        "api_reference",
        "hub:public_symbol:aspose.imaging.foss",
        old="format detection, metadata extraction, and image transformation through",
        new="format detection and metadata extraction through",
        absent_from_live=("image transformation",),
    ),
    Spec(
        "traced-T3",
        "traced",
        detectors.POLARITY,
        "Aspose.3D-FOSS-for-.NET",
        "Q_claims T3: 30 formats 'not functional'; the live unit 061.list names only PDF and Draco "
        "and its Quick Start uses glTF, OBJ, STL and COLLADA",
        "scope_limitations",
        "limitation:2",
        clean_text="FileFormat.PDF and FileFormat.Draco are not functional in this FOSS build.",
        inherited=("inherited_unit:061.list",),
    ),
    Spec(
        "traced-T4",
        "traced",
        detectors.INVENTED_CAPABILITY,
        "Aspose.Page-FOSS-for-Python",
        "Q_claims T4: 'Model-View-Presenter server', cited facts are five identity facts",
        "scope_limitations",
        "scope",
        old=", as well as a Model-View-Presenter server for remote conversion tasks",
        absent_from_live=("Model-View-Presenter",),
    ),
    Spec(
        "traced-T5",
        "traced",
        detectors.INVENTED_CAPABILITY,
        "Aspose.Cells-FOSS-for-Java",
        "Q_claims T5: the commercial edition 'adds ... DOCX, XLSM, ODS'; cited facts are package facts",
        "enterprise_relationship",
        "context",
        old=" such as comprehensive charting, pivot tables, conditional formatting, and support for "
        "additional file formats including DOCX, XLSM, and ODS",
        new="",
        absent_from_live=("XLSM",),
    ),
    Spec(
        "traced-T6",
        "traced",
        detectors.VERSION,
        "Aspose.Slides-FOSS-for-Java",
        f"Q_claims T6: an install coordinate at 26.8.0; Maven Central lists only 26.7.0 "
        f"(maven-metadata.xml, read {READING_DATE})",
        "scope_limitations",
        "limitation:1",
        old="aspose-slides-foss:26.8.0",
        new="aspose-slides-foss:26.7.0",
        registry={
            "package:published_version": {
                "kind": "package",
                "value": "26.7.0",
                "attributes": {
                    "registry": "maven",
                    "package": "org.aspose:aspose-slides-foss",
                    "read": READING_DATE,
                },
            }
        },
    ),
    Spec(
        "traced-T7",
        "traced",
        detectors.IDENTIFIER,
        "Aspose.Slides-FOSS-for-Cpp",
        "Q_claims T7: 'not yet published on any package registry'; the live README documents the "
        "NuGet package Aspose.Slides.Cpp.FOSS (Install From NuGet on Windows, Install-Package)",
        readme_snippet="`AsposeSlidesFoss` is not yet published on any package registry; build it from "
        "a source checkout instead, verified against this revision:",
        clean_text="`AsposeSlidesFoss` is available as the Windows NuGet package "
        "`Aspose.Slides.Cpp.FOSS`; elsewhere build it from a source checkout instead, verified "
        "against this revision:",
    ),
    Spec(
        "traced-T8",
        "traced",
        detectors.SYMBOL_PROSE,
        "Aspose.BarCode-FOSS-for-Python",
        "Q_claims T8: prose assembled from enum member names",
        "development_testing",
        "summary",
        old=" The examples/ directory provides runnable samples that demonstrate member AUTO, member "
        "H, member data, member render, member to_png, and member to_svg usage.",
        new=" The examples/ directory provides runnable samples.",
    ),
    Spec(
        "traced-T9",
        "traced",
        detectors.VERSION,
        "Aspose.Email-FOSS-for-.Net",
        f"Q_claims T9: version 0.1.0 of Aspose.Email.Foss; NuGet lists only 26.7.0 "
        f"(flat container, read {READING_DATE})",
        "documentation_resources",
        "link:link_target:020",
        old="Aspose.Email.Foss 0.1.0 targeting net8.0",
        new="Aspose.Email.Foss 26.7.0 targeting net8.0",
        registry={
            "package:published_version": {
                "kind": "package",
                "value": "26.7.0",
                "attributes": {
                    "registry": "nuget",
                    "package": "Aspose.Email.Foss",
                    "read": READING_DATE,
                },
            }
        },
    ),
    Spec(
        "traced-T10",
        "traced",
        detectors.FORMATTING,
        "Aspose.HTML-FOSS-for-Python",
        "Q_claims T10: the requirement skia-python>=87.0,<145 printed as two bullets",
        readme_snippet="- `<145`\n- `skia-python>=87.0`",
        clean_text="- `skia-python>=87.0,<145`",
    ),
    Spec(
        "hand-colon-cells-java",
        "hand_found",
        detectors.FORMATTING,
        "Aspose.Cells-FOSS-for-Java",
        "a lead-in ending in a colon directly before the License heading (line 432)",
        readme_snippet="Requires JDK 17+ and Maven as the build tool. Run the test suite:",
        clean_text="Requires JDK 17+ and Maven as the build tool.",
    ),
    Spec(
        "hand-colon-html-py",
        "hand_found",
        detectors.FORMATTING,
        "Aspose.HTML-FOSS-for-Python",
        "a lead-in ending in a colon directly before the License heading (line 591)",
        readme_snippet="Install `quickjs` to also exercise the JavaScript-bridge tests and doctests:",
        clean_text="Install `quickjs` to also exercise the JavaScript-bridge tests and doctests.",
    ),
    Spec(
        "hand-colon-page-py",
        "hand_found",
        detectors.FORMATTING,
        "Aspose.Page-FOSS-for-Python",
        "a lead-in ending in a colon directly before the License heading (line 438)",
        readme_snippet="Sync dependencies and run the test suite with `uv`:",
        clean_text="Sync dependencies and run the test suite with `uv`.",
    ),
    Spec(
        "hand-colon-pdf-py",
        "hand_found",
        detectors.FORMATTING,
        "Aspose-PDF-FOSS-for-Python",
        "a lead-in ending in a colon directly before the License heading (line 800)",
        readme_snippet="checks and tests CI runs:",
        clean_text="checks and tests CI runs.",
    ),
    Spec(
        "hand-badge-words-py",
        "hand_found",
        detectors.FORMATTING,
        "Aspose.Words-FOSS-for-Python",
        "a badge whose URL carries an encoded comma where the version range was cut",
        readme_snippet="![Python](https://img.shields.io/badge/python-3.10%2C%3C3.13%2B-blue.svg)",
        clean_text="![Python](https://img.shields.io/badge/python-3.10--3.13-blue.svg)",
    ),
    Spec(
        "hand-scraped-ts-borderid",
        "hand_found",
        detectors.SCRAPED_TEXT,
        "Aspose.Cells-FOSS-for-TypeScript",
        "a member row whose type residue replaced the description (line 209)",
        readme_snippet="- `borderId`: Defined as `: number`.",
        clean_text="- `borderId`: `number`.",
    ),
    Spec(
        "hand-scraped-ts-cells",
        "hand_found",
        detectors.SCRAPED_TEXT,
        "Aspose.Cells-FOSS-for-TypeScript",
        "a member row whose type residue replaced the description (line 210)",
        readme_snippet="- `cells`: Defined as `: { [key: string]: CellValue }`.",
        clean_text="- `cells`: `{ [key: string]: CellValue }`.",
    ),
    Spec(
        "hand-scraped-ts-code",
        "hand_found",
        detectors.SCRAPED_TEXT,
        "Aspose.Cells-FOSS-for-TypeScript",
        "a member row whose type residue replaced the description (line 212)",
        readme_snippet="- `code`: Defined as `: string`.",
        clean_text="- `code`: `string`.",
    ),
    Spec(
        "hand-scraped-3d-net-bonepose",
        "hand_found",
        detectors.SCRAPED_TEXT,
        "Aspose.3D-FOSS-for-.NET",
        "an API row whose XML-doc cross-reference was dropped, leaving 'The  contains' (line 190)",
        readme_snippet="| `BonePose` | The  contains the transformation matrix for a bone node |",
        clean_text="| `BonePose` | Contains the transformation matrix for a bone node |",
    ),
    Spec(
        "hand-scraped-3d-net-circle",
        "hand_found",
        detectors.SCRAPED_TEXT,
        "Aspose.3D-FOSS-for-.NET",
        "an API row whose XML-doc cross-reference was dropped, leaving 'A  curve' (Circle)",
        readme_snippet="| `Circle` | A  curve consists of a set of points in the edge of the circle shape",
        clean_text="| `Circle` | A curve consists of a set of points in the edge of the circle shape",
    ),
)


# --- plumbing ------------------------------------------------------------------------------------


def _short(bundle: PinnedBundle) -> str:
    return bundle.pin.directory.split("__", 1)[1]


def _unit(bundle: PinnedBundle, section: str, slot: str) -> dict[str, Any]:
    for unit in (bundle.content_units or {}).get("units", []):
        if unit.get("section") == section and unit.get("slot") == slot:
            return unit
    raise LookupError(f"{bundle.pin.directory} has no unit {section}/{slot}")


def _facts(bundle: PinnedBundle, ids: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fact_id in ids:
        fact = bundle.facts_by_id.get(fact_id)
        if fact is None:
            continue
        row: dict[str, Any] = {"kind": fact["kind"], "value": fact.get("value")}
        if fact.get("attributes"):
            row["attributes"] = fact["attributes"]
        out[fact_id] = row
    return out


def _inherited(bundle: PinnedBundle, ids: list[str]) -> dict[str, str]:
    live = bundle.sealed.inherited_units() or {}
    return {i: live[i] for i in ids if i in live}


def _source(bundle: PinnedBundle, where: str) -> str:
    return f"{bundle.pin.directory}@{bundle.pin.revision[:8]}: {where}"


def _supported(facts: Mapping[str, Mapping[str, Any]], cited: list[str]) -> set[str]:
    from . import claims_ref

    return claims_ref.support(facts, cited)


def _audit(spec: Spec, case: Case, bundle: PinnedBundle) -> None:
    if case.injected == case.clean:
        raise ValueError(f"{spec.id}: the injected text equals its twin")
    live = bundle.live or ""
    for span in spec.absent_from_live:
        if span.casefold() in live.casefold():
            raise ValueError(f"{spec.id}: {span!r} is in the live README, so it is not invented")
        if span.casefold() not in case.injected.casefold():
            raise ValueError(f"{spec.id}: {span!r} is not in the injected text")
        if span.casefold() in case.clean.casefold():
            raise ValueError(f"{spec.id}: {span!r} is still in the clean twin")
        blob = json.dumps(case.facts, default=str).casefold()
        if span.casefold() in blob:
            raise ValueError(f"{spec.id}: {span!r} is in a cited fact, so it is supported")
    if spec.readme_snippet and spec.readme_snippet not in bundle.readme:
        raise ValueError(f"{spec.id}: the sealed README does not contain the snippet")


def hand_case(spec: Spec, bundle: PinnedBundle) -> Case:
    if spec.readme_snippet:
        injected = spec.readme_snippet
        clean = spec.clean_text if spec.clean_text is not None else ""
        case = Case(
            id=spec.id,
            origin=spec.origin,
            cls=spec.cls,
            repository=bundle.repository,
            bundle=bundle.pin.directory,
            level="readme",
            injected=injected,
            clean=clean,
            readme_edit=(clean, injected),
            excerpt=spec.note,
            source=_source(bundle, "README.md (sealed text)"),
        )
    else:
        unit = _unit(bundle, spec.section, spec.slot)
        text = str(unit["text"])
        if spec.clean_text is not None:
            clean = spec.clean_text
        else:
            if spec.old not in text:
                raise ValueError(f"{spec.id}: {spec.old!r} is not in the unit text")
            clean = text.replace(spec.old, spec.new, 1)
        cited = [str(i) for i in unit["fact_ids"]]
        inherited_ids = sorted({*(i for i in cited if i.startswith("inherited_unit")), *spec.inherited})
        facts = _facts(bundle, [i for i in cited if not i.startswith("inherited_unit")])
        facts.update(spec.registry)
        case = Case(
            id=spec.id,
            origin=spec.origin,
            cls=spec.cls,
            repository=bundle.repository,
            bundle=bundle.pin.directory,
            level="unit",
            injected=text,
            clean=clean,
            section=spec.section,
            slot=spec.slot,
            cited=tuple(cited),
            facts=facts,
            inherited=_inherited(bundle, inherited_ids),
            excerpt=spec.note,
            source=_source(bundle, f"content_units {spec.section}/{spec.slot}"),
        )
    _audit(spec, case, bundle)
    return case


# --- mutants -------------------------------------------------------------------------------------


def _all_units(bundles: list[PinnedBundle]) -> list[tuple[PinnedBundle, dict[str, Any]]]:
    return [(b, u) for b in bundles for u in (b.content_units or {}).get("units", [])]


def _silent_on_twin(cls: str, subject: Subject) -> bool:
    return all(
        not d.run(subject) for d in detectors.reference_detectors() if cls in d.classes
    )


def _negated_tokens(bundle: PinnedBundle) -> tuple[dict[str, str], list[str]]:
    """The live units of a bundle that say 'not supported', and the identifiers they name."""
    negative: dict[str, str] = {}
    tokens: set[str] = set()
    for uid, text in (bundle.sealed.inherited_units() or {}).items():
        if detectors._NEGATIVE.search(text):
            named = {m.group(0) for m in detectors._NAMED.finditer(text)}
            if named:
                negative[uid] = text
                tokens |= named
    return negative, sorted(tokens)


def mutants(bundles: list[PinnedBundle], seed: int = SEED) -> list[Case]:
    pool = _all_units(bundles)
    cases: list[Case] = []
    classes = [*mutator.MUTATIONS, detectors.POLARITY]
    for cls in classes:
        order = list(pool)
        random.Random(f"{seed}:{cls}").shuffle(order)
        used: set[str] = set()
        made = 0
        quota = MUTANTS_BY_CLASS.get(cls, MUTANTS_PER_CLASS)
        for bundle, unit in order:
            if made >= quota:
                break
            if bundle.pin.directory in used:
                continue
            section, slot = str(unit["section"]), str(unit["slot"])
            text = str(unit["text"])
            cited = [str(i) for i in unit["fact_ids"]]
            plain = [i for i in cited if not i.startswith("inherited_unit")]
            facts = _facts(bundle, plain)
            kinds = {str(facts.get(i, {}).get("kind", "?")) for i in plain}
            if cls == detectors.INVENTED_CAPABILITY and kinds - _WEAK:
                continue
            if cls == detectors.SYMBOL_PROSE and section == "api_reference":
                continue
            if cls in (detectors.SYMBOL_PROSE, detectors.INVENTED_CAPABILITY) and len(text) < 40:
                continue
            inherited: dict[str, str] = {}
            case_rng = random.Random(f"{seed}:{cls}:{bundle.pin.directory}:{section}/{slot}")
            if cls == detectors.POLARITY:
                inherited, negated = _negated_tokens(bundle)
                if section != "key_capabilities":
                    continue
                injected = mutator.polarity(text, case_rng, negated)
            else:
                supported = _supported(facts, plain)
                injected = mutator.MUTATIONS[cls](text, case_rng, supported)
            if injected is None or injected == text:
                continue
            twin = Subject(text, "unit", section, slot, tuple(cited), facts, inherited, {})
            if not _silent_on_twin(cls, twin):
                continue
            cases.append(
                Case(
                    id=f"mutant-{cls}-{made + 1:02d}",
                    origin="mutant",
                    cls=cls,
                    repository=bundle.repository,
                    bundle=bundle.pin.directory,
                    level="unit",
                    injected=injected,
                    clean=text,
                    section=section,
                    slot=slot,
                    cited=tuple(cited),
                    facts=facts,
                    inherited=inherited,
                    excerpt=f"seeded mutation ({cls}) of a clean unit",
                    source=_source(bundle, f"content_units {section}/{slot}"),
                )
            )
            used.add(bundle.pin.directory)
            made += 1
        if made < quota:
            raise RuntimeError(f"only {made} mutants for {cls}; the pool cannot carry the corpus")
    return cases


# --- clean negatives -----------------------------------------------------------------------------

_NEGATIVE_TEMPLATES: dict[str, tuple[str, str]] = {
    "package:version": ("package", "The current release is version {value}."),
    "package:name": ("package", "The package is published as `{value}`."),
    "package:python_requires": ("package", "The package requires Python {value}."),
    "license:spdx": ("license", "The library is released under the {value} license."),
}


def negatives(bundles: list[PinnedBundle], seed: int = SEED) -> list[Case]:
    """Sentences that restate one fact verbatim, one per bundle, so they are true by construction."""
    cases: list[Case] = []
    order = list(bundles)
    random.Random(f"{seed}:negatives").shuffle(order)
    for bundle in order:
        if len(cases) >= NEGATIVES:
            break
        picks = [
            (fid, template)
            for fid, (kind, template) in _NEGATIVE_TEMPLATES.items()
            if fid in bundle.facts_by_id and bundle.facts_by_id[fid].get("kind") == kind
        ]
        install = [
            f
            for f in bundle.facts_by_id.values()
            if f["kind"] == "install_command" and isinstance(f.get("value"), str)
        ]
        if install:
            picks.append((str(install[0]["id"]), "Install it with `{value}`."))
        if not picks:
            continue
        pick_rng = random.Random(f"{seed}:neg:{bundle.pin.directory}")
        fact_id, template = pick_rng.choice(sorted(picks))
        value = bundle.facts_by_id[fact_id]["value"]
        if not isinstance(value, str) or not value.strip() or "\n" in value:
            continue
        text = template.format(value=value.strip())
        cases.append(
            Case(
                id=f"negative-{len(cases) + 1:02d}",
                origin="clean_negative",
                cls="clean",
                repository=bundle.repository,
                bundle=bundle.pin.directory,
                level="unit",
                injected=text,
                clean=text,
                section="key_capabilities",
                slot="constructed",
                positive=False,
                cited=(fact_id,),
                facts=_facts(bundle, [fact_id]),
                excerpt=f"restates {fact_id} verbatim",
                source=_source(bundle, f"constructed from {fact_id}"),
            )
        )
    if len(cases) < NEGATIVES:
        raise RuntimeError(f"only {len(cases)} clean negatives could be constructed")
    return cases


# --- ledger cases --------------------------------------------------------------------------------


def ledger_cases(bundles: list[PinnedBundle], seed: int = SEED) -> list[Case]:
    """Real not-accounted rows of the pinned ledgers (M2, M3, and kept units that are not printed)."""
    buckets: dict[str, list[tuple[PinnedBundle, ledger.UnitAccount, str]]] = {
        "OMIT_UNSUPPORTED": [],
        "SUPERSEDE_REDUNDANT": [],
        "KEPT": [],
    }
    for bundle in bundles:
        live = bundle.sealed.inherited_units() or {}
        for account in ledger.unit_accounts(bundle):
            text = live.get(account.unit_id, "")
            if not text.strip() or account.accounted:
                continue
            if account.disposition == ledger.OMIT and not account.contradicted:
                buckets["OMIT_UNSUPPORTED"].append((bundle, account, text))
            elif account.disposition == ledger.SUPERSEDE and (account.coverage or 0.0) < 0.8:
                buckets["SUPERSEDE_REDUNDANT"].append((bundle, account, text))
            elif account.disposition in ("VERIFIED_PRESERVE", "VERIFIED_MOVE"):
                buckets["KEPT"].append((bundle, account, text))
    cases: list[Case] = []
    for name, want in LEDGER_CASES.items():
        rows = sorted(buckets[name], key=lambda r: (r[0].pin.directory, r[1].unit_id))
        random.Random(f"{seed}:ledger:{name}").shuffle(rows)
        used: set[str] = set()
        for bundle, account, text in rows:
            if want == 0:
                break
            if bundle.pin.directory in used:
                continue
            used.add(bundle.pin.directory)
            row: dict[str, Any] = {
                "unit_id": account.unit_id,
                "disposition": account.disposition,
                "printed": False,
                "contradicted": bool(account.contradicted),
                "coverage": round(account.coverage or 0.0, 4),
                "clean": {"printed": True},
            }
            cases.append(
                Case(
                    id=f"ledger-{name.lower()}-{len(cases) + 1:02d}",
                    origin="ledger",
                    cls=detectors.DROPPED_CONTENT,
                    repository=bundle.repository,
                    bundle=bundle.pin.directory,
                    level="ledger",
                    injected=text,
                    clean=text,
                    ledger=row,
                    excerpt=f"{account.unit_id}: {account.disposition}, not accounted",
                    source=_source(bundle, f"dispositions.json {account.unit_id}"),
                )
            )
            want -= 1
        if want:
            raise RuntimeError(f"ledger bucket {name} is {want} case(s) short")
    return cases


# --- the whole corpus ----------------------------------------------------------------------------


def build_all(bundles: list[PinnedBundle] | None = None) -> dict[str, list[Case]]:
    bundles = bundles if bundles is not None else read_bundles(load_pins())
    by_name = {_short(b): b for b in bundles}
    traced: list[Case] = []
    found: list[Case] = []
    for spec in HAND:
        case = hand_case(spec, by_name[spec.name])
        (traced if spec.origin == "traced" else found).append(case)
    return {
        "traced": traced,
        "hand_found": found,
        "ledger": ledger_cases(bundles),
        "mutants": mutants(bundles),
        "negatives": negatives(bundles),
    }


def documents(groups: Mapping[str, list[Case]]) -> dict[str, str]:
    """File name -> exact text of every corpus file (cases, and the split)."""
    files = {
        f"cases/{name}.json": json.dumps(
            [case_to_json(c) for c in cases], indent=1, sort_keys=True, ensure_ascii=False
        )
        + "\n"
        for name, cases in groups.items()
    }
    every = [c for cases in groups.values() for c in cases]
    pins = load_pins()
    split = corpus.split_document(every, (p.repository for p in pins.bundles))
    files["split.json"] = json.dumps(split, indent=1, sort_keys=True) + "\n"
    return files


def write(root: Path, files: Mapping[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def differences(root: Path, files: Mapping[str, str]) -> list[str]:
    out: list[str] = []
    for name, text in files.items():
        path = root / name
        if not path.exists():
            out.append(f"{name}: missing")
        elif path.read_text(encoding="utf-8") != text:
            out.append(f"{name}: differs from the builder's output")
    return out


def count_by(cases: list[Case], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        value = getattr(case, key if key != "class" else "cls")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))

