"""An audience, benefit, or use case in the opening is stated only when an accepted fact states it.

Every sentence below is verbatim from the wave-3 reseal (f69f75c7) candidates the acceptance review
rejected (3D-Java, 3D-.NET, 3D-TypeScript, Cells-.NET, Cells-Java): the opening named who uses the
library and what for, and the pipeline's own checks (BC-04 identifiers and citations, reviewer
ACCEPT) passed it because the units cited identity and package facts that carry no audience.
"""

from __future__ import annotations

import copy
import re
from typing import Any

import pytest

from repository_presenter.components.readme.composition.audience import (
    AUDIENCE_SECTIONS,
    UNSUPPORTED_AUDIENCE,
    audience_errors,
    sentences,
    strip_audience_claims,
    strip_audience_units,
    support_texts,
    unsupported_audience_sentences,
)
from repository_presenter.components.readme.composition.authoring import (
    _OBJECTIVES,
    SectionTask,
    unit_checks,
)
from repository_presenter.components.readme.composition.coherence import (
    coherence_checks,
    recover_coherence_audience_claims,
    recover_coherence_regressions,
)
from repository_presenter.components.readme.composition.type_fallback import (
    recover_section_authoring_with_type_fallback,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

# --- the verbatim sentences -------------------------------------------------------------------

JAVA_3D_ENABLES = (
    "It enables developers to load, create, modify, and export 3D scenes and models without "
    "requiring a full commercial suite."
)
JAVA_3D_USED_BY = (
    "It is used by Java developers building applications that process 3D data, such as CAD "
    "viewers, simulation tools, and 3D printing workflows."
)
CELLS_NET_ENABLES = (
    "Aspose.Cells FOSS for .NET is a free, open-source library that enables .NET developers to "
    "create, read, and convert Excel files without requiring a commercial license."
)
CELLS_NET_USE = (
    "Developers use it to generate reports, process spreadsheets programmatically, and "
    "integrate Excel-like functionality into their applications."
)
TS_USE = (
    "Developers use it to build 3D content pipelines in TypeScript applications, especially "
    "for converting models, preparing geometry, and inspecting scene hierarchies."
)
CELLS_JAVA_ENABLING = (
    "Aspose.Cells FOSS for Java reads and writes Excel files in XLSX format, enabling developers "
    "to create, modify, and inspect spreadsheet content without requiring a commercial license."
)
CELLS_JAVA_SUITABLE = (
    "It supports Java 17 and has no external dependencies, making it suitable for developers "
    "building lightweight, self-contained applications."
)
CELLS_JAVA_INCLUDE = (
    "Users include Java developers who need to generate reports, process financial data, or "
    "enforce data entry rules in spreadsheets."
)
NET_3D_ENABLES = (
    "It enables developers to read, write, and convert 3D scenes across multiple formats "
    "including GLTF, OBJ, STL, FBX, and Collada."
)

AUDIENCE_SENTENCES = [
    JAVA_3D_ENABLES,
    JAVA_3D_USED_BY,
    CELLS_NET_ENABLES,
    CELLS_NET_USE,
    TS_USE,
    CELLS_JAVA_ENABLING,
    CELLS_JAVA_SUITABLE,
    CELLS_JAVA_INCLUDE,
    NET_3D_ENABLES,
]

# The same openings' sentences that state what the product is and does, from facts: none may be
# refused (the negative control for every pattern above).
JAVA_3D_LEAD = "Aspose.3D FOSS for Java is a Java library for working with 3D files."
JAVA_3D_FORMATS = (
    "The library supports reading and writing STL files, as well as other 3D formats, and "
    "provides programmatic control over geometry, materials, and scene structure."
)
NET_3D_RUNTIMES = (
    "The library supports .NET Core 3.1, .NET 6, .NET 8, and .NET 10, and requires no external "
    "dependencies."
)
TS_LEAD = (
    "Aspose.3D FOSS for TypeScript reads and writes 3D scene formats such as OBJ and GLTF, and "
    "converts between them using Scene.open and Scene.save."
)
TS_MESH = (
    "It supports polygonal mesh processing including triangulation of quad faces via "
    "PolygonModifier.triangulate."
)
CELLS_NET_RUNTIME = (
    "The library targets netstandard2.0 and net8.0, and version 26.9.0.0 is available under the "
    "MIT license."
)
CELLS_NET_FORMATS = (
    "It supports reading and writing XLSX files, as well as exporting to PDF, and provides "
    "capabilities for styling cells, managing tables, applying data validation, adding "
    "hyperlinks, and setting page layout options."
)
CELLS_JAVA_HEAD = "Aspose.Cells FOSS for Java reads and writes Excel files in XLSX format."
RUNTIME_FLOOR = "Built for Java 21 and higher, the library is distributed under the MIT license."
PRIVATE_USE = (
    "Open an existing PDF file, including a password-protected one by passing the user or owner "
    "password."
)
FORMAT_USED_BY = "It reads MSG files, the compound file format used by Outlook."
CLEAN_SENTENCES = [
    JAVA_3D_LEAD,
    JAVA_3D_FORMATS,
    NET_3D_RUNTIMES,
    TS_LEAD,
    TS_MESH,
    CELLS_NET_RUNTIME,
    CELLS_NET_FORMATS,
    CELLS_JAVA_HEAD,
    RUNTIME_FLOOR,
    PRIVATE_USE,
    FORMAT_USED_BY,
]

NAME = "Aspose.3D FOSS for Java"
REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
PRESERVED = "inherited_unit:003.paragraph"
DROPPED = "inherited_unit:009.paragraph"


def _fact(fact_id: str, kind: str, value: str) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),))


def _facts(preserved: str = "", dropped: str = "") -> FactsDocument:
    found = [
        _fact("identity:repository", "identity", REPOSITORY),
        _fact("identity:platform", "identity", "java"),
        _fact("package:name", "package", "org.aspose:aspose-3d-foss"),
    ]
    if preserved:
        found.append(_fact(PRESERVED, "inherited_unit", preserved))
    if dropped:
        found.append(_fact(DROPPED, "inherited_unit", dropped))
    return FactsDocument(REPOSITORY, "a" * 40, tuple(found))


def _task(section: str = "opening", *, with_preserved: bool = False) -> SectionTask:
    ids = {"identity:repository", "identity:platform", "package:name"}
    if with_preserved:
        ids.add(PRESERVED)
    return SectionTask(section, {}, frozenset(ids), ("opening",) if section == "opening" else ())


def _output(text: str, section: str = "opening") -> dict[str, Any]:
    return {
        "units": [
            {
                "section": section,
                "slot": "opening",
                "text": text,
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }


def _opening(*parts: str) -> str:
    return " ".join(parts)


WAVE3_JAVA_3D_OPENING = _opening(JAVA_3D_LEAD, JAVA_3D_ENABLES, JAVA_3D_FORMATS, JAVA_3D_USED_BY)


# --- the rule ---------------------------------------------------------------------------------


@pytest.mark.parametrize("sentence", AUDIENCE_SENTENCES)
def test_each_audience_sentence_the_review_found_is_refused_without_a_supporting_fact(
    sentence: str,
) -> None:
    assert unsupported_audience_sentences(sentence, []) == [sentence]
    # Identity and package facts do not carry an audience: the platform is not one.
    support = support_texts(_task().accepted_ids, _facts())
    assert unsupported_audience_sentences(sentence, support) == [sentence]


@pytest.mark.parametrize("sentence", CLEAN_SENTENCES)
def test_a_sentence_that_states_what_the_product_is_and_does_is_not_refused(
    sentence: str,
) -> None:
    assert unsupported_audience_sentences(sentence, []) == []


def test_a_claim_a_preserved_unit_states_passes_in_its_own_words_and_in_a_paraphrase() -> None:
    """The negative control: an audience sentence copied from the live README through a unit
    reconciliation kept in the opening is a fact-backed claim, so it is not refused."""
    support = [JAVA_3D_USED_BY]
    assert unsupported_audience_sentences(JAVA_3D_USED_BY, support) == []
    paraphrase = "It is used by Java developers building applications that process 3D data."
    assert unsupported_audience_sentences(paraphrase, support) == []


def test_a_preserved_sentence_extended_with_an_invented_use_case_is_refused() -> None:
    extended = JAVA_3D_USED_BY[:-1] + ", and medical imaging."
    assert unsupported_audience_sentences(extended, [JAVA_3D_USED_BY]) == [extended]


def test_a_supporting_text_in_one_sentence_cannot_be_assembled_from_unrelated_facts() -> None:
    """The claim's words must sit in one sentence (or two adjacent ones) of one text: the words
    "developers", "reports" and "spreadsheets" scattered over unrelated facts support nothing."""
    scattered = [
        "Developers guide.",
        "Reports are written to disk.",
        "Spreadsheets open in Excel.",
        "Applications link the jar.",
    ]
    assert unsupported_audience_sentences(CELLS_NET_USE, scattered) == [CELLS_NET_USE]


def test_the_refusal_names_the_sentence_and_the_way_out() -> None:
    errors = audience_errors(_output(WAVE3_JAVA_3D_OPENING)["units"], [], "opening")
    assert len(errors) == 2
    assert all(UNSUPPORTED_AUDIENCE in error for error in errors)
    assert JAVA_3D_ENABLES in errors[0] and JAVA_3D_USED_BY in errors[1]
    assert "delete" in errors[0]
    assert all(error.startswith("unit opening: ") for error in errors)


def test_only_the_opening_is_judged() -> None:
    assert set(AUDIENCE_SECTIONS) == {"opening"}
    units = _output(CELLS_NET_USE, "key_capabilities")["units"]
    assert audience_errors(units, [], "key_capabilities") == []
    assert len(audience_errors(units, [], "opening")) == 1


def test_sentences_split_on_a_sentence_end_and_not_inside_a_name_or_version() -> None:
    assert sentences("Reads Node.js files. Version 26.9.0.0 is out. It targets .NET 8.") == [
        "Reads Node.js files.",
        "Version 26.9.0.0 is out.",
        "It targets .NET 8.",
    ]


# --- unit_checks (the authoring guard, S8 coherence and BC-04 all call it) --------------------


def test_unit_checks_refuses_the_real_java_3d_opening_with_one_repairable_error_per_sentence() -> (
    None
):
    errors = unit_checks(_output(WAVE3_JAVA_3D_OPENING), _task(), _facts(), NAME)
    assert len(errors) == 2
    assert all(UNSUPPORTED_AUDIENCE in error for error in errors)
    assert "without requiring a full commercial suite" in errors[0]
    assert "CAD viewers" in errors[1]


def test_unit_checks_accepts_the_opening_once_it_states_only_what_the_product_is_and_does() -> None:
    clean = _opening(JAVA_3D_LEAD, JAVA_3D_FORMATS)
    assert unit_checks(_output(clean), _task(), _facts(), NAME) == []


def test_unit_checks_accepts_an_audience_the_opening_was_handed_as_a_preserved_unit() -> None:
    facts = _facts(preserved=JAVA_3D_USED_BY)
    opening = _opening(JAVA_3D_LEAD, JAVA_3D_USED_BY)
    assert unit_checks(_output(opening), _task(with_preserved=True), facts, NAME) == []


def test_unit_checks_refuses_the_same_sentence_when_its_unit_was_not_handed_to_the_opening() -> (
    None
):
    """A README unit reconciliation dropped or sent elsewhere is not a fact of this section."""
    facts = _facts(dropped=JAVA_3D_USED_BY)
    opening = _opening(JAVA_3D_LEAD, JAVA_3D_USED_BY)
    errors = unit_checks(_output(opening), _task(), facts, NAME)
    assert len(errors) == 1 and UNSUPPORTED_AUDIENCE in errors[0]


def test_unit_checks_leaves_another_section_to_its_own_rules() -> None:
    task = _task("scope_limitations")
    assert [
        error
        for error in unit_checks(_output(CELLS_NET_USE, "scope_limitations"), task, _facts(), NAME)
        if UNSUPPORTED_AUDIENCE in error
    ] == []


# --- the last resort: delete, never rewrite ---------------------------------------------------


def test_stripping_deletes_the_audience_sentences_and_keeps_the_facts() -> None:
    stripped = strip_audience_claims(WAVE3_JAVA_3D_OPENING, [])
    assert stripped == _opening(JAVA_3D_LEAD, JAVA_3D_FORMATS)


@pytest.mark.parametrize(
    ("sentence", "kept"),
    [
        (CELLS_JAVA_ENABLING, CELLS_JAVA_HEAD),
        (CELLS_JAVA_SUITABLE, "It supports Java 17 and has no external dependencies."),
        (
            CELLS_NET_ENABLES,
            "Aspose.Cells FOSS for .NET is a free, open-source library.",
        ),
    ],
)
def test_a_trailing_audience_clause_is_cut_back_to_the_sentence_that_stands_alone(
    sentence: str, kept: str
) -> None:
    assert strip_audience_claims(sentence, []) == kept


def test_stripping_never_adds_a_word() -> None:
    opening = _opening(CELLS_JAVA_ENABLING, CELLS_JAVA_SUITABLE, CELLS_JAVA_INCLUDE)
    stripped = strip_audience_claims(opening, [])
    assert stripped is not None
    assert set(re.findall(r"\w+", stripped.lower())) <= set(re.findall(r"\w+", opening.lower()))


def test_a_unit_that_would_be_left_empty_is_not_touched() -> None:
    output = _output(_opening(CELLS_JAVA_INCLUDE, CELLS_NET_USE))
    before = copy.deepcopy(output)
    assert strip_audience_claims(output["units"][0]["text"], []) is None
    assert strip_audience_units(output, [], "opening") is None
    assert output == before


def test_stripping_a_fragment_head_drops_the_whole_sentence() -> None:
    """ "Aspose.Note FOSS for Python version 26.3.2" lost its verb to the audience clause; a head
    with no predicate is not kept as a sentence."""
    sentence = (
        "Aspose.Note FOSS for Python version 26.3.2 enables Python developers to read and convert "
        "Microsoft OneNote files to PDF."
    )
    assert strip_audience_claims(_opening(sentence, JAVA_3D_FORMATS), []) == JAVA_3D_FORMATS


def test_strip_audience_units_only_touches_the_opening() -> None:
    other = _output(CELLS_NET_USE, "key_capabilities")
    assert strip_audience_units(other, [], "key_capabilities") is None
    opening = _output(_opening(JAVA_3D_LEAD, CELLS_NET_USE))
    assert strip_audience_units(opening, [], "opening") is opening
    assert opening["units"][0]["text"] == JAVA_3D_LEAD


def test_the_stripped_opening_passes_the_guard_that_refused_it() -> None:
    output = _output(WAVE3_JAVA_3D_OPENING)
    assert unit_checks(copy.deepcopy(output), _task(), _facts(), NAME)
    recovered = recover_section_authoring_with_type_fallback(
        output, slot_titles={}, task=_task(), facts=_facts(), name=NAME
    )
    assert recovered is not None
    assert unit_checks(recovered, _task(), _facts(), NAME) == []
    assert recovered["units"][0]["text"] == _opening(JAVA_3D_LEAD, JAVA_3D_FORMATS)


def test_the_last_resort_keeps_an_audience_the_opening_was_handed() -> None:
    facts = _facts(preserved=JAVA_3D_USED_BY)
    output = _output(_opening(JAVA_3D_LEAD, JAVA_3D_USED_BY))
    recovered = recover_section_authoring_with_type_fallback(
        output, slot_titles={}, task=_task(with_preserved=True), facts=facts, name=NAME
    )
    assert recovered is None
    assert output["units"][0]["text"] == _opening(JAVA_3D_LEAD, JAVA_3D_USED_BY)


# --- S8 coherence -----------------------------------------------------------------------------


def _coherence(opening_text: str) -> dict[str, Any]:
    return _output(opening_text)


def test_coherence_refuses_a_rewrite_that_introduces_an_audience() -> None:
    errors = coherence_checks(
        _coherence(_opening(JAVA_3D_LEAD, CELLS_NET_USE)), [_task()], _facts(), NAME
    )
    assert any(UNSUPPORTED_AUDIENCE in error for error in errors)


def test_coherence_recovery_restores_the_accepted_opening_a_rewrite_replaced() -> None:
    accepted = _opening(JAVA_3D_LEAD, JAVA_3D_FORMATS)
    revised = _coherence(_opening(JAVA_3D_LEAD, JAVA_3D_FORMATS, CELLS_NET_USE))
    existing = _output(accepted)["units"]
    fixed = recover_coherence_audience_claims(
        revised, existing_units=existing, tasks=[_task()], facts=_facts()
    )
    assert fixed is revised
    assert revised["units"][0]["text"] == accepted
    # The composed recovery the S8 call site passes reaches it too.
    again = _coherence(_opening(JAVA_3D_LEAD, CELLS_NET_USE))
    composed = recover_coherence_regressions(
        again, existing_units=existing, facts=_facts(), tasks=[_task()]
    )
    assert composed is not None and again["units"][0]["text"] == accepted


def test_coherence_recovery_deletes_the_claim_when_the_accepted_opening_had_it_too() -> None:
    both = _opening(JAVA_3D_LEAD, CELLS_NET_USE)
    revised = _coherence(both)
    fixed = recover_coherence_audience_claims(
        revised, existing_units=_output(both)["units"], tasks=[_task()], facts=_facts()
    )
    assert fixed is revised and revised["units"][0]["text"] == JAVA_3D_LEAD


def test_coherence_recovery_leaves_a_clean_opening_alone() -> None:
    clean = _coherence(_opening(JAVA_3D_LEAD, JAVA_3D_FORMATS))
    assert (
        recover_coherence_audience_claims(
            clean, existing_units=clean["units"], tasks=[_task()], facts=_facts()
        )
        is None
    )


# --- the request: objective, prompt, contract -------------------------------------------------


def test_the_opening_objective_no_longer_asks_who_uses_it() -> None:
    objective, _budget = _OBJECTIVES["opening"]
    assert "who uses it" not in objective.replace("not who uses it", "")
    assert "State no audience, use case or benefit" in objective
    assert "unless an accepted fact" in objective


def test_the_section_authoring_prompt_forbids_an_invented_audience() -> None:
    system = " ".join(
        load_manifests(REPO_ROOT / "prompts")["section_authoring"].manifest.system.split()
    )
    assert "never says who uses the product" in system
    assert "Developers use it to" in system
    assert "not an audience" in system


def test_the_contract_no_longer_asks_the_opening_for_who_uses_it() -> None:
    contract = (REPO_ROOT / "docs" / "README_CONTRACT.md").read_text(encoding="utf-8")
    row = next(line for line in contract.splitlines() if line.startswith("| 4 | `opening`"))
    assert "who uses it" not in row
    assert "composition/audience.py" in row
