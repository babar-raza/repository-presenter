"""The eleven blocking checks: a sound candidate passes nine and pends two; each failure names
its causal stage; validation.json is deterministic."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    slot_fact_sets,
)
from repository_presenter.components.readme.composition.components.shell import SEMANTIC_SHELL
from repository_presenter.components.readme.composition.renderer import (
    api_reference_names,
    render_readme,
)
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    Candidate,
    _check_examples,
    _check_install,
    _check_links,
    _check_structure,
    _fences,
    blocking_failures,
    summarize_validation,
    validate_candidate,
    write_validation,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret

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
    }
    assert document["summary"] == {"pass": 9, "fail": 0, "pending": 2}
    assert summarize_validation(document) == "pass 9, fail 0, pending 2"
    assert document["checks"][9]["judged_at"] == "S10"
    assert document["checks"][10]["details"] == ["judged at S12"]
    assert all(check["causal_stage"] is None for check in document["checks"])
    assert document["readme_sha256"] == hashlib.sha256(candidate.readme.encode()).hexdigest()
    assert len(document["protected_content_fingerprint"]) == 64
    assert document["advisory"] == []
    assert document["source_revision"] == REVISION and document["validator_version"] == "3"


def test_the_coverage_ledger_records_each_row_against_the_evidence(tmp_path: Path) -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.2 RC6: a coverage defect used to dead-end as a
    # presentation advisory because nothing recorded what a row needed against what the evidence
    # gave it. The ledger says it per row, with the reason the evidence itself carries.
    document = validate_candidate(_candidate(), tmp_path, ())
    ledger = {row["section_id"]: row for row in document["coverage"]}
    assert [row["section_id"] for row in document["coverage"]] == [s.id for s in SEMANTIC_SHELL]
    # A structural row rests on no fact kind; navigation renders from the sections present.
    assert ledger["navigation"]["kinds"] == [] and ledger["navigation"]["required"] is True
    # A required row names its kinds and how far each resolved.
    quick_start = ledger["quick_start"]
    assert quick_start["required"] is True and quick_start["included"] is True
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
        "### Save a scene\n\n```python\nprint(1)\n```\n\n</details>\n"
    )
    document = validate_candidate(_candidate(_candidate().readme + "\n" + section), tmp_path, ())
    details = _failed(document, "BC-07")["details"]
    assert "example heading 'Example 2' is reused" in details
    assert "example heading 'Example 2' names no task" in details
    assert not any("Save a scene" in detail for detail in details)


def test_the_aspose_ceiling_counts_contextual_links_not_the_mandated_rows() -> None:
    # README_CONTRACT.md row 15 bounds the contextual Aspose links; the banner (row 3) and the
    # Enterprise target (row 18) are mandated rows rendered from verified product facts.
    def fact(name: str, url: str) -> Fact:
        return Fact(f"link_target:{name}", "link_target", url, (Evidence(url, "HTTP 200"),))

    docs = [fact(f"doc{n}", f"https://docs.aspose.org/3d/python/page-{n}/") for n in range(5)]
    banner = fact("product.banner", "https://products.aspose.org/media/3d/python/banner-readme.png")
    homepage = fact("product.homepage", "https://products.aspose.org/3d/python/")
    enterprise = fact("product.enterprise", "https://products.aspose.com/3d/python-net/")
    facts = FactsDocument(
        FACTS.repository, FACTS.source_revision, (*FACTS.facts, *docs, banner, homepage, enterprise)
    )
    base = _candidate().readme
    nl = chr(10)
    mandated = (
        f"[![Aspose.3D FOSS for Python]({banner.value})]({homepage.value})"
        f"{nl}{nl}[Enterprise Edition]({enterprise.value}){nl}"
    )
    four = " ".join(f"[page {n}]({docs[n].value})" for n in range(4))
    within = _candidate(readme=nl.join([base, mandated, four, ""]), facts=facts)
    assert not any("exceed the ceiling" in str(failure) for failure in _check_links(within))
    five = f"{four} [page 4]({docs[4].value})"
    over = _candidate(readme=nl.join([base, mandated, five, ""]), facts=facts)
    assert any("5 Aspose links exceed the ceiling of 4" in str(f) for f in _check_links(over))


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
