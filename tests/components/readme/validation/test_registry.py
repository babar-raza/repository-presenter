"""The eleven blocking checks: a sound candidate passes nine and pends two; each failure names
its causal stage; validation.json is deterministic."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import SectionTask
from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    Candidate,
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
        _unit("api_reference", "hub:public_symbol:aspose.threed.scene", "Scene holds the graph."),
        _unit("documentation_resources", "resources", "The docs explain the API."),
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
    SectionTask("key_capabilities", {}, ACCEPTED, tuple(f"capability:{i}" for i in range(1, 7))),
    SectionTask("quick_start", {}, ACCEPTED, ("lead_in",)),
    SectionTask("api_reference", {}, ACCEPTED, ("hub:public_symbol:aspose.threed.scene",)),
    SectionTask("documentation_resources", {}, ACCEPTED, ("resources",)),
    SectionTask("scope_limitations", {}, ACCEPTED, ("scope",)),
]


def _candidate(
    readme: str | None = None,
    facts: FactsDocument = FACTS,
    dispositions: dict[str, Any] = DISPOSITIONS,
    plan: dict[str, Any] = PLAN,
) -> Candidate:
    rendered = (
        readme if readme is not None else render_readme(ENTRY, facts, plan, UNITS, dispositions)
    )
    return Candidate(
        ENTRY,
        facts,
        plan,
        UNITS,
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
    assert candidate.readme.count(" ~~~ ") == 3  # six capabilities: two columns of three
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
    assert document["source_revision"] == REVISION and document["validator_version"] == "1"


def test_every_failure_names_its_causal_stage(tmp_path: Path) -> None:
    readme = _candidate().readme

    second_h1 = validate_candidate(_candidate(readme + "\n# Second\n"), tmp_path, ())
    structure = _failed(second_h1, "BC-07")
    assert structure["causal_stage"] == "COMPOSING"
    assert structure["details"] == [
        "expected exactly one H1 '# Aspose.3D FOSS for Python'; found 2"
    ]

    one_column = validate_candidate(
        _candidate("\n".join(line for line in readme.splitlines() if " ~~~ " not in line) + "\n"),
        tmp_path,
        (),
    )
    assert _failed(one_column, "BC-07")["details"] == [
        "At a Glance: 6 capabilities form two balanced columns; found 0 row links, expected 3"
    ]

    lowercase = validate_candidate(
        _candidate(readme + "\nIt writes pdf and glb files.\n"), tmp_path, ()
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

    (tmp_path / "calls.jsonl").write_text('{"key": "sk-live-secret-value"}\n', encoding="utf-8")
    secret = ConfiguredSecret("GPT_OSS_API_KEY", b"sk-live-secret-value")
    leaked = validate_candidate(_candidate(), tmp_path, (secret,))
    bundle = _failed(leaked, "BC-09")
    assert bundle["causal_stage"] is None
    assert bundle["details"] == ["value of GPT_OSS_API_KEY found in calls.jsonl"]


def test_validation_json_is_deterministic_and_sorted(tmp_path: Path) -> None:
    document = validate_candidate(_candidate(), tmp_path, ())
    first = write_validation(document, tmp_path / "validation.json")
    second = write_validation(document, tmp_path / "validation.json")
    data = (tmp_path / "validation.json").read_bytes()
    assert first == second == hashlib.sha256(data).hexdigest()
    assert data.endswith(b"}\n") and b"\r" not in data
    assert list(json.loads(data)) == sorted(json.loads(data))
