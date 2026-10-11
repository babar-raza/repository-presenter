"""A finding that denies a name any fact is refuted by the fact it denies (BC-10, wave 4 cause 5).

The payloads are the reviewer's own, copied from the wave-4 transactions (cut 8c48f4d2, 2026-10-11):
Aspose.Cells-FOSS-for-Go raised twelve findings that its API reference's types and members have
"no verified public_symbol facts", each citing the SUPPORTED public_symbol facts whose values were
those names; Aspose.HTML-FOSS-for-Python denied ``aspose_html.dom.html``, a SUPPORTED symbol;
Aspose.Cells-FOSS-for-TypeScript denied the package name ``excel-cells``, the value of SUPPORTED
``package:name``. The negative controls are the same reviewers' findings that look alike and are
not name denials - a claim about the names, a name that is no fact, a name excluded by polarity.

The reviewer states the names it denies in the finding's typed ``unsupported_names``, as it
states an absence in ``absent``; the rule never reads the finding's ``text``
(tests/test_routing_fields.py). Each finding below carries the names its sealed text denied.
"""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.readme.review.independent import review as review_module
from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    DETERMINISTIC_RULES,
    NAME_DENIAL_RULE,
    SYMBOL_INDEX_CHARS,
    TRIGGER_REJECTION_REFUTED,
    name_denial_defect,
    refutation,
    review_document,
    review_packet,
    scope_rulings,
    second_read_decision,
    symbol_index,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

MANIFESTS = load_manifests(REPO_ROOT / "prompts")
REVIEWER = MANIFESTS["independent_review"]
AUTHORING = MANIFESTS["section_authoring"]

# Aspose.Cells-FOSS-for-Go, first read (c82bd1308010): id, section, quote, text, the public_symbol
# VALUES of the fact_ids the finding cited. F01/F03/F14/F15 were already folded as the renderer's
# own sentences and are left out.
GO_FIRST: list[tuple[str, str, str, str, list[str]]] = [
    (
        "F02",
        "api_reference",
        "| Class | Description |",
        "The candidate's API reference table includes Chart, ChartAnchor, ChartSeries, ChartType, "
        "PivotDataField, PivotTable, VBAProject, SheetNotFoundError, CellNotFoundError, "
        "InvalidRefError, FormulaError, and ConditionalFormatting, none of which are supported by "
        "public_symbol facts.",
        [
            "Chart",
            "ChartAnchor",
            "ChartSeries",
            "ChartType",
            "PivotDataField",
            "PivotTable",
            "VBAProject",
            "SheetNotFoundError",
            "CellNotFoundError",
            "InvalidRefError",
            "FormulaError",
            "ConditionalFormatting",
        ],
    ),
    (
        "F04",
        "api_reference",
        "### Workbook",
        "The candidate's detailed member reference section includes members for Workbook such as "
        "SourceXML, StylesXML, Modified, FilePath, and methods like Load, LoadWithPassword, "
        "SaveWorkbook, SetVBAProject, GetVBAProject, HasVBAProject, ClearVBAProject, "
        "CheckPassword, and VerifyPassword, none of which have verified public_symbol facts.",
        [
            "Workbook.SourceXML",
            "Workbook.StylesXML",
            "Workbook.Modified",
            "Workbook.FilePath",
            "Load",
            "LoadWithPassword",
            "SaveWorkbook",
            "Workbook.SetVBAProject",
            "Workbook.GetVBAProject",
            "Workbook.HasVBAProject",
            "Workbook.ClearVBAProject",
            "Workbook.CheckPassword",
            "Workbook.VerifyPassword",
        ],
    ),
    (
        "F05",
        "api_reference",
        "### Worksheet",
        "The candidate's detailed member reference section includes members for Worksheet such as "
        "Name, Index, Modified, DataValidations, Tables, Pictures, ConditionalFormattings, Charts, "
        "PivotTables, AddChart, RemoveChart, ToCSV, FromCSV, AddDataValidation, "
        "RemoveDataValidation, AddPicture, AddPivotTable, RemovePivotTable, AddTable, GetTable, "
        "RemoveChart, RemoveConditionalFormatting, RemoveDataValidation, RemovePivotTable, and "
        "RemoveTable, none of which have verified public_symbol facts.",
        [
            "Worksheet.Name",
            "Worksheet.Index",
            "Worksheet.Modified",
            "Worksheet.DataValidations",
            "Worksheet.Tables",
            "Worksheet.Pictures",
            "Worksheet.ConditionalFormattings",
            "Worksheet.Charts",
            "Worksheet.PivotTables",
            "Worksheet.AddChart",
            "Worksheet.RemoveChart",
            "Worksheet.ToCSV",
            "Worksheet.FromCSV",
            "Worksheet.AddDataValidation",
            "Worksheet.RemoveDataValidation",
            "Worksheet.AddPicture",
            "Worksheet.AddPivotTable",
            "Worksheet.RemovePivotTable",
            "Worksheet.AddTable",
            "Worksheet.GetTable",
            "Worksheet.RemoveChart",
            "Worksheet.RemoveConditionalFormatting",
            "Worksheet.RemoveDataValidation",
            "Worksheet.RemovePivotTable",
        ],
    ),
    (
        "F06",
        "api_reference",
        "### StreamingReader",
        "The candidate's detailed member reference section includes members for StreamingReader "
        "such as ProcessRowsWithColumns, ProcessRowsWithFilter, ProcessRowsWithRange, and methods "
        "for StreamOptions, none of which have verified public_symbol facts.",
        [
            "StreamingReader.ProcessRowsWithColumns",
            "StreamingReader.ProcessRowsWithFilter",
            "StreamingReader.ProcessRowsWithRange",
            "StreamOptions",
        ],
    ),
    (
        "F07",
        "api_reference",
        "### DataValidation",
        "The candidate's detailed member reference section includes members for DataValidation "
        "such as Formula2, none of which have verified public_symbol facts.",
        ["DataValidation.Formula2"],
    ),
    (
        "F08",
        "api_reference",
        "### Table",
        "The candidate's detailed member reference section includes members for Table such as "
        "Name, Range, HasHeaderRow, and StyleName, none of which have verified public_symbol "
        "facts.",
        ["Table.Name", "Table.Range", "Table.HasHeaderRow", "Table.StyleName"],
    ),
    (
        "F09",
        "api_reference",
        "### Style",
        "The candidate's detailed member reference section includes members for Style such as "
        "Font, Fill, Alignment, and Border, none of which have verified public_symbol facts.",
        ["Style.Font", "Style.Fill", "Style.Alignment", "Style.Border"],
    ),
    (
        "F10",
        "api_reference",
        "### Font",
        "The candidate's detailed member reference section includes members for Font such as "
        "Italic, none of which have verified public_symbol facts.",
        ["Font.Italic"],
    ),
    (
        "F11",
        "api_reference",
        "### Fill",
        "The candidate's detailed member reference section includes members for Fill such as Type "
        "and Color, none of which have verified public_symbol facts.",
        ["Fill.Type", "Fill.Color"],
    ),
    (
        "F12",
        "api_reference",
        "### Alignment",
        "The candidate's detailed member reference section includes members for Alignment such as "
        "Horizontal, Vertical, and WrapText, none of which have verified public_symbol facts.",
        ["Alignment.Horizontal", "Alignment.Vertical", "Alignment.WrapText"],
    ),
    (
        "F13",
        "api_reference",
        "### Border",
        "The candidate's detailed member reference section includes members for Border such as "
        "Top, Bottom, Left, Right, and Color, none of which have verified public_symbol facts.",
        ["Border.Top", "Border.Bottom", "Border.Left", "Border.Right", "Border.Color"],
    ),
    (
        "F16",
        "api_reference",
        "### RowCallback",
        "The candidate's detailed member reference section includes members for RowCallback, "
        "StreamOptions, and StreamingReader, none of which have verified public_symbol facts.",
        ["RowCallback", "StreamOptions", "StreamingReader"],
    ),
]

# The same candidate's second read (af4eab994023): three findings, the first two of the same
# shape, the third a judgment about a limitation that no name lookup settles.
GO_SECOND: list[tuple[str, str, str, str, list[str]]] = [
    (
        "F03",
        "api_reference",
        "| Chart | Chart represents a chart embedded in a worksheet. |",
        "The candidate includes Chart, PivotTable, VBAProject, and other types in the API "
        "reference table that are not supported by any fact indicating they are public and "
        "supported.",
        [],
    ),
    (
        "F05",
        "quick_start",
        "```go",
        "The candidate's second Quick Start example uses `LoadWorkbook` but the fact example:003 "
        "shows `LoadWorkbook` is not a verified function; the correct function is `Load`.",
        ["example:003", "public_symbol:loadworkbook"],
    ),
    (
        "F06",
        "scope_limitations",
        "- `Cell` references must be A1-style strings, `CalculateFormula` supports only SUM, "
        "AVERAGE, MAX, and MIN, and any other formula returns an error rather than being "
        "evaluated.",
        "The candidate claims 'Cell references must be A1-style strings' but the fact example:004 "
        "and others show A1-style references are used, but the limitation about tuple/array "
        "indices is not directly supported by facts.",
        ["example:004", "public_symbol:calculateformula"],
    ),
]


def _fact(fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


def _symbol(value: str, polarity: str = "SUPPORTED") -> Fact:
    return _fact(f"public_symbol:{value.lower()}", "public_symbol", value, polarity)


def _finding(
    label: str,
    section: str,
    quote: str,
    text: str,
    fact_ids: list[str],
    criterion: str = "factuality",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": label,
        "section_id": section,
        "causal_stage": "S6",
        "criterion": criterion,
        "text": text,
        "quote": quote,
        "fact_ids": fact_ids,
        "absent": [],
        "unsupported_names": [],
        "omission": None,
        "repair": "Remove the unsupported symbols.",
        **extra,
    }


def _go_ids(values: list[str]) -> list[str]:
    return [value if ":" in value else f"public_symbol:{value.lower()}" for value in values]


def _first_names(label: str, values: list[str]) -> list[str]:
    """What the reviewer lists in ``unsupported_names`` for a first-read finding: the names its
    text denies, a member by its bare name. Go F05 also listed ``RemoveTable``, which no fact or
    row carries."""
    names = dict.fromkeys(value.rsplit(".", 1)[-1] for value in values)
    return [*names, *(["RemoveTable"] if label == "F05" else [])]


# The second read's denials: F03 lists the three types its text names, F05 the one function it
# calls "not a verified function", and F06 - a judgment about a limitation - denies no name.
GO_SECOND_NAMES: dict[str, list[str]] = {
    "F03": ["Chart", "PivotTable", "VBAProject"],
    "F05": ["LoadWorkbook"],
    "F06": [],
}


def _go_findings(rows: list[tuple[str, str, str, str, list[str]]]) -> list[dict[str, Any]]:
    second = rows is GO_SECOND
    return [
        _finding(
            i,
            s,
            q,
            t,
            _go_ids(ids),
            unsupported_names=GO_SECOND_NAMES[i] if second else _first_names(i, ids),
        )
        for i, s, q, t, ids in rows
    ]


def _go_facts() -> FactsDocument:
    values: dict[str, None] = {}
    for _, _, _, _, ids in GO_FIRST:
        values.update(dict.fromkeys(ids))
    # The second read's findings name these; the reviewer cited them in the first read too.
    values.update(
        dict.fromkeys(["LoadWorkbook", "CalculateFormula", "Chart", "PivotTable", "VBAProject"])
    )
    return FactsDocument(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Go",
        "a" * 40,
        (
            *(_symbol(value) for value in values),
            _fact("example:003", "example", "wb, _ := cells_foss.LoadWorkbook(path)"),
            _fact("example:004", "example", "ws.Cells().Set(cell, value)"),
        ),
    )


# The candidate's API reference prints every one of those names - and not RemoveTable, which only
# the reviewer's F05 text lists.
def _go_candidate(facts: FactsDocument) -> str:
    rows = "\n".join(
        f"| {fact.value} | The {fact.value} symbol. |"
        for fact in facts.facts
        if fact.kind == "public_symbol"
    )
    return (
        "# Aspose.Cells FOSS for Go\n\n## API Reference\n\n| Class | Description |\n"
        f"| --- | --- |\n{rows}\n\n## License\n\nMIT.\n"
    )


def _review(
    findings: list[dict[str, Any]],
    facts: FactsDocument,
    candidate: str,
    second: dict[str, Any] | None = None,
    verdict: str = "REJECT_FACTUAL",
    original: str = "The original README.\n",
) -> dict[str, Any]:
    return review_document(
        {"verdict": verdict, "findings": findings, "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=candidate,
        facts=facts,
        original_readme=original,
        second=second,
        units={"units": []},
        dispositions=None,
    )


def _rules(finding: dict[str, Any], facts: FactsDocument, candidate: str) -> set[str]:
    by_id = {fact.id: fact for fact in facts.facts}
    return {ruling.rule for ruling in scope_rulings(finding, candidate, by_id)}


# --- the real payloads -------------------------------------------------------------------------


@pytest.mark.parametrize("row", GO_FIRST, ids=[row[0] for row in GO_FIRST])
def test_each_wave4_cells_go_denial_is_refuted_by_the_facts_it_cites(
    row: tuple[str, str, str, str, list[str]],
) -> None:
    """The finding says the names have no public_symbol fact; the facts it cites ARE those names."""
    facts = _go_facts()
    (finding,) = _go_findings([row])
    by_id = {fact.id: fact for fact in facts.facts}
    ruling = refutation(scope_rulings(finding, _go_candidate(facts), by_id))
    assert ruling is not None and ruling.rule == NAME_DENIAL_RULE and ruling.deterministic
    record = ruling.refuted_by()
    assert record["rule"] == NAME_DENIAL_RULE
    assert record["evidence"]["kinds"] == ["public_symbol"]
    assert record["evidence"]["count"] >= 1
    # Every name it denied is mapped to a SUPPORTED fact id that exists.
    for name, fact_id in record["evidence"]["names"].items():
        assert by_id[fact_id].polarity == "SUPPORTED", name
    assert set(record["evidence"]["facts"]) <= set(by_id)


def test_the_wave4_cells_go_first_read_replays_to_a_deterministic_accept() -> None:
    """The sealed review rejected on all twelve; each is now advisory with its recorded refutation,
    the returned verdict is kept, and the accept needs the second read (REJECTION_REFUTED)."""
    facts = _go_facts()
    document = _review(_go_findings(GO_FIRST), facts, _go_candidate(facts))
    assert document["findings"] == []
    assert document["verdict"] == ACCEPT
    assert document["verdict_as_returned"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == "rejection_refuted_deterministically"
    assert [f["id"] for f in document["advisory"]] == [row[0] for row in GO_FIRST]
    for record in document["advisory"]:
        assert record["refuted_by"]["rule"] == NAME_DENIAL_RULE
        assert record["causal_state"] is None and "reviewer_scope_defect" in record
    decision = second_read_decision(document, [])
    assert decision.triggered and TRIGGER_REJECTION_REFUTED in decision.reasons


def test_the_wave4_cells_go_second_read_keeps_only_the_finding_no_lookup_settles() -> None:
    """The second read repeats the denial twice (a relative clause, and a function the finding
    itself cites as SUPPORTED) and adds a judgment about a limitation. The two denials fold; the
    judgment stands and the rejection with it - a real finding is not folded to get an ACCEPT."""
    facts = _go_facts()
    candidate = _go_candidate(facts)
    first = _review(_go_findings(GO_FIRST), facts, candidate)
    assert first["verdict"] == ACCEPT
    second = {
        "verdict": "REJECT_FACTUAL",
        "findings": _go_findings(GO_SECOND),
        "preserve": [],
    }
    document = _review(_go_findings(GO_FIRST), facts, candidate, second=second)
    assert [(f["id"], f["reader"]) for f in document["findings"]] == [("F06", 2)]
    assert document["verdict"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == "extra_read_verdict"
    folded = {
        (f["id"], f["reader"]): f["refuted_by"]["rule"]
        for f in document["advisory"]
        if f.get("reader") == 2
    }
    assert folded == {("F03", 2): NAME_DENIAL_RULE, ("F05", 2): NAME_DENIAL_RULE}


def test_the_refutation_depends_on_the_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation: with the rule inert the wave-4 payloads block exactly as the sealed review did."""
    facts = _go_facts()
    monkeypatch.setattr(review_module, "name_denial_defect", lambda *a, **k: None)
    document = _review(_go_findings(GO_FIRST), facts, _go_candidate(facts))
    assert document["verdict"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == "rejection_stands"
    assert [f["id"] for f in document["findings"]] == [row[0] for row in GO_FIRST]


def test_a_denied_name_is_looked_up_by_its_text_when_the_finding_cites_nothing() -> None:
    """Aspose.HTML-FOSS-for-Python F05 (wave 4): no fact_ids at all, and
    ``aspose_html.dom.html`` is a SUPPORTED public_symbol; wave 3 raised it seven times."""
    facts = FactsDocument(
        "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
        "a" * 40,
        (
            _symbol("aspose_html.dom"),
            _symbol("aspose_html.dom.html"),
            _symbol("aspose_html.dom.html.HTMLAddressElement"),
        ),
    )
    candidate = (
        "# HTML\n\n## API Reference\n\n| `aspose_html.dom.html` | HTML element subclasses. |\n"
    )
    for text in (
        "The candidate lists 'aspose_html.dom.html' as a public symbol, but no fact supports "
        "this exact symbol.",
        "The candidate lists 'aspose_html.dom.html' as a public symbol, but the facts show it is "
        "not supported.",
    ):
        finding = _finding(
            "F05",
            "api_reference",
            "aspose_html.dom.html",
            text,
            [],
            unsupported_names=["aspose_html.dom.html"],
        )
        document = _review([finding], facts, candidate)
        assert document["findings"] == [] and document["verdict"] == ACCEPT
        (record,) = document["advisory"]
        assert record["refuted_by"]["evidence"]["names"] == {
            "aspose_html.dom.html": "public_symbol:aspose_html.dom.html"
        }


def test_a_denied_package_name_is_refuted_by_package_name() -> None:
    """Aspose.Cells-FOSS-for-TypeScript F01 and F02 (wave 4): `excel-cells` is SUPPORTED
    ``package:name``. The third finding of that read is real and stays."""
    facts = FactsDocument(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
        "a" * 40,
        (
            _fact("package:name", "package", "excel-cells"),
            _fact(
                "identity:repository",
                "identity",
                "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
            ),
        ),
    )
    candidate = (
        "# Aspose.Cells FOSS for TypeScript\n\n## Installation\n\n"
        "`excel-cells` is not yet published on npm; build it from a source checkout instead:\n\n"
        "## Scope and Limitations\n\nIt reads Excel files in the excel-cells format at version "
        "1.0.0.\n"
    )
    f01 = _finding(
        "F01",
        "identity",
        "Aspose.Cells FOSS for TypeScript reads and writes Excel files in XLSX format.",
        "The candidate incorrectly states the package name as 'excel-cells' in the opening "
        "paragraph and installation section, while the repository name and all facts confirm "
        "the product is 'Aspose.Cells FOSS for TypeScript'.",
        ["identity:repository"],
        unsupported_names=["excel-cells"],
    )
    f02 = _finding(
        "F02",
        "installation",
        "`excel-cells` is not yet published on npm; build it from a source checkout instead:",
        "The candidate incorrectly claims the package name is 'excel-cells' in the installation "
        "section, while the facts confirm the repository name is "
        "'Aspose.Cells-FOSS-for-TypeScript' and no npm package name fact supports 'excel-cells'.",
        ["package:name"],
        unsupported_names=["excel-cells"],
    )
    f03 = _finding(
        "F03",
        "scope_limitations",
        "It reads Excel files in the excel-cells format at version 1.0.0.",
        "The candidate claims the library reads and writes Excel files in the 'excel-cells "
        "format at version 1.0.0', but no fact supports the existence of an 'excel-cells format' "
        "or its version.",
        [],
    )
    document = _review([f01, f02, f03], facts, candidate)
    assert [f["id"] for f in document["findings"]] == ["F03"]
    assert document["verdict"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == "rejection_stands"
    folded = {f["id"]: f["refuted_by"] for f in document["advisory"]}
    assert set(folded) == {"F01", "F02"}
    for record in folded.values():
        assert record["rule"] == NAME_DENIAL_RULE
        assert record["evidence"]["names"] == {"excel-cells": "package:name"}
        assert record["evidence"]["kinds"] == ["package_name"]


# --- negative controls -------------------------------------------------------------------------


def _go_one(
    index: int, facts: FactsDocument | None = None, **changes: Any
) -> tuple[dict[str, Any], FactsDocument, str]:
    facts = facts or _go_facts()
    finding = {**_go_findings([GO_FIRST[index]])[0], **changes}
    return finding, facts, _go_candidate(facts)


def test_a_name_that_is_no_fact_leaves_the_finding_standing() -> None:
    """The reviewer's denial is true of `Frobnicate`: the candidate prints it and no fact carries
    it. One unresolved name keeps the whole finding blocking, however many others resolve."""
    finding, facts, candidate = _go_one(1)
    finding["unsupported_names"] = [*finding["unsupported_names"], "Frobnicate"]
    candidate = candidate.replace("\n## License", "\n| Frobnicate | Not a fact. |\n\n## License")
    assert "| Frobnicate |" in candidate
    assert NAME_DENIAL_RULE not in _rules(finding, facts, candidate)
    document = _review([finding], facts, candidate)
    assert [f["id"] for f in document["findings"]] == ["F04"]
    assert (
        document["verdict"] == "REJECT_FACTUAL" and document["verdict_basis"] == "rejection_stands"
    )
    assert "refuted_by" not in document["findings"][0]
    # The same name unquoted or absent from the section: the unprinted one is the reviewer's slip.
    unprinted = candidate.replace("| Frobnicate | Not a fact. |\n", "")
    assert NAME_DENIAL_RULE in _rules(finding, facts, unprinted)


def test_a_qualified_name_is_resolved_only_exactly() -> None:
    """`Tables` is a member of Worksheet; the finding says Workbook.Tables has no fact, which is
    true, so the bare member name's looseness does not reach a qualified one."""
    finding, facts, candidate = _go_one(1)
    candidate = candidate.replace("\n## License", "\n| Workbook.Tables | Printed. |\n\n## License")
    wrong_type = {**finding, "unsupported_names": ["Workbook.Tables"]}
    assert name_denial_defect(wrong_type, {f.id: f for f in facts.facts}, candidate) is None
    # And a qualified name that is a fact resolves.
    right_type = {**wrong_type, "unsupported_names": ["Worksheet.Tables"]}
    assert name_denial_defect(right_type, {f.id: f for f in facts.facts}, candidate) is not None


def test_a_denied_name_the_section_never_prints_does_not_save_the_finding_alone() -> None:
    """Wave-4 Go F05 listed `RemoveTable`, in no fact and nowhere in the candidate: the listing is
    the reviewer's slip and does not keep the finding standing beside 23 names that resolve. A
    finding whose every name is like that is not refuted by any fact, so it stands."""
    finding, facts, candidate = _go_one(2)
    assert "RemoveTable" not in candidate
    ruling = name_denial_defect(finding, {fact.id: fact for fact in facts.facts}, candidate)
    assert ruling is not None and ruling.evidence["not_in_section"] == ["RemoveTable"]
    lone = {**finding, "unsupported_names": ["RemoveTable"]}
    assert name_denial_defect(lone, {fact.id: fact for fact in facts.facts}, candidate) is None


def test_a_name_only_a_contradicted_symbol_carries_is_not_supported() -> None:
    """The name appears in the facts, but only as CONTRADICTED: no SUPPORTED fact carries it."""
    base = _go_facts()
    facts = FactsDocument(
        base.repository,
        base.source_revision,
        (*base.facts, _symbol("LegacyExport", "CONTRADICTED")),
    )
    finding, _, candidate = _go_one(1, facts)
    finding["unsupported_names"] = [*finding["unsupported_names"], "LegacyExport"]
    candidate = candidate.replace("\n## License", "\n| LegacyExport | Old. |\n\n## License")
    assert name_denial_defect(finding, {f.id: f for f in facts.facts}, candidate) is None
    # And a finding that cites the CONTRADICTED fact itself points at excluded evidence.
    cited = {**finding, "fact_ids": [*finding["fact_ids"], "public_symbol:legacyexport"]}
    assert name_denial_defect(cited, {f.id: f for f in facts.facts}, candidate) is None


def test_a_denial_of_a_claim_about_names_is_not_a_denial_of_the_names() -> None:
    """Wave-3 Aspose.Cells-FOSS-for-TypeScript: every name in these sentences is a SUPPORTED fact,
    and the finding does not deny them - it denies what the candidate says OF them (a mutability
    limitation, the signatures and fields printed beside them), so it lists no name in
    ``unsupported_names``. They keep blocking."""
    types = (
        "Workbook",
        "Worksheet",
        "Cell",
        "Style",
        "ConditionalFormat",
        "AutoFilter",
        "DataValidation",
        "Hyperlink",
        "Comment",
        "Cells",
        "WorksheetCollection",
    )
    facts = FactsDocument(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript",
        "a" * 40,
        tuple(
            _symbol(v)
            for v in (
                *types,
                "Workbook.charts",
                "Worksheet.charts",
                "Workbook.images",
                "Worksheet.images",
            )
        ),
    )
    candidate = "# T\n\n## Scope and Limitations\n\n- Workbook.charts provide read-only access.\n"
    by_id = {fact.id: fact for fact in facts.facts}
    for section, quote, text, cited in (
        (
            "scope_limitations",
            "Workbook.charts, Worksheet.charts, Workbook.images, and Worksheet.images provide "
            "read-only access to charts and images",
            "The candidate states 'Workbook.charts, Worksheet.charts, Workbook.images, and "
            "Worksheet.images provide read-only access to charts and images but do not support "
            "modification or creation of new chart or image objects', but no fact supports this "
            "claim about charts and images being read-only.",
            ["public_symbol:workbook.charts"],
        ),
        (
            "scope_limitations",
            "Workbook.charts, Worksheet.charts, Workbook.images, and Worksheet.images provide "
            "read-only access to charts and images",
            "The candidate claims 'Workbook.charts, Worksheet.charts, Workbook.images, and "
            "Worksheet.images provide read-only access to charts and images but do not support "
            "modification or creation of new chart or image objects', but the facts do not "
            "verify this limitation; they only list the symbols without specifying mutability.",
            ["public_symbol:workbook.charts"],
        ),
        (
            "api_reference",
            "### Workbook",
            "The candidate's detailed member reference for Workbook, Worksheet, Cell, Style, "
            "ConditionalFormat, AutoFilter, DataValidation, Hyperlink, Comment, Cells, and "
            "WorksheetCollection includes method signatures and fields that are not supported by "
            "the public_symbol facts and introduce unsupported details.",
            ["public_symbol:workbook", "public_symbol:cell"],
        ),
    ):
        finding = _finding("F01", section, quote, text, cited)
        assert name_denial_defect(finding, by_id, candidate) is None, text


def test_the_finding_text_is_never_read_for_the_names() -> None:
    """The wave-4 denial sentences, with the typed field empty: nothing is looked up, the finding
    stands. Rewording the prose changes nothing either way (RESEARCH_AND_GUIDELINES.md 27.2 RC8)."""
    facts = _go_facts()
    by_id = {fact.id: fact for fact in facts.facts}
    candidate = _go_candidate(facts)
    for row in GO_FIRST:
        (finding,) = _go_findings([row])
        assert name_denial_defect(finding, by_id, candidate) is not None, row[0]
        assert name_denial_defect({**finding, "unsupported_names": []}, by_id, candidate) is None
        absent_key = {k: v for k, v in finding.items() if k != "unsupported_names"}
        assert name_denial_defect(absent_key, by_id, candidate) is None, row[0]
        reworded = {**finding, "text": "A different sentence entirely."}
        assert name_denial_defect(reworded, by_id, candidate) is not None, row[0]
    stands = _review(
        [{**_go_findings([GO_FIRST[0]])[0], "unsupported_names": []}], facts, candidate
    )
    assert [f["id"] for f in stands["findings"]] == ["F02"]
    assert stands["verdict"] == "REJECT_FACTUAL" and stands["advisory"] == []


def test_a_listed_name_is_read_as_a_name_however_it_is_quoted() -> None:
    facts = _go_facts()
    by_id = {fact.id: fact for fact in facts.facts}
    candidate = _go_candidate(facts)
    finding = _finding("F01", "api_reference", "| Chart |", "x", [], unsupported_names=["`Chart`"])
    for spelled in ("`Chart`", "'Chart'", '"Chart"', "Chart()", " Chart ", "Chart", "Chart"):
        ruling = name_denial_defect({**finding, "unsupported_names": [spelled]}, by_id, candidate)
        assert ruling is not None and list(ruling.evidence["names"]) == ["Chart"], spelled


def test_a_multi_word_entry_is_a_claim_not_a_name() -> None:
    facts = _go_facts()
    by_id = {fact.id: fact for fact in facts.facts}
    candidate = _go_candidate(facts)
    for names in (["Chart represents a chart"], ["Chart", "the Chart type"]):
        finding = _finding(
            "F01",
            "api_reference",
            "| Chart |",
            "The candidate lists 'Chart represents a chart' as a public symbol, but no fact "
            "supports this exact symbol.",
            ["public_symbol:chart"],
            unsupported_names=names,
        )
        assert name_denial_defect(finding, by_id, candidate) is None, names


def test_a_name_denial_that_also_claims_an_omission_keeps_the_omission() -> None:
    """The names having facts refutes the denial, not the claim that the section lacks something."""
    facts = _go_facts()
    candidate = _go_candidate(facts)
    finding, _, _ = _go_one(0, absent=["ChartAnchor2"])
    original = "The original README documents `ChartAnchor2`.\n"
    document = _review([finding], facts, candidate, original=original)
    assert [f["id"] for f in document["findings"]] == ["F02"]
    assert document["verdict_basis"] == "rejection_stands"


def test_only_a_factuality_finding_is_refuted_by_a_name_denial() -> None:
    facts = _go_facts()
    finding, _, candidate = _go_one(0, criterion="presentation")
    assert NAME_DENIAL_RULE not in _rules(finding, facts, candidate)


def test_the_rule_is_a_registered_deterministic_one_and_records_plain_data() -> None:
    assert NAME_DENIAL_RULE in DETERMINISTIC_RULES
    facts = _go_facts()
    finding, _, candidate = _go_one(0)
    document = _review([finding], facts, candidate)
    import json

    json.dumps(document, sort_keys=True)  # review.json writes it as is


# --- the packet --------------------------------------------------------------------------------

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
        "family": "html",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def test_the_packet_lists_the_symbols_its_facts_bounds_left_out() -> None:
    """Wave 4: Aspose.HTML-FOSS-for-Python's `facts` carried 257 of 338 symbols and the JMAP .NET
    one 44 of 265; the rendered API reference printed all of them, so the reviewer judged rows it
    could not see. Anything past the dotted-depth bound now travels as a bare value."""
    deep = "aspose_html.dom.html.HTMLDocument.getElementById"  # four dots: past SYMBOL_MAX_DEPTH
    facts = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        (
            _symbol("aspose_html.URL"),
            _symbol(deep),
            _symbol("aspose_html.dom.html.HTMLDocument.cookie"),
            _symbol("aspose_html.dom.html.HTMLDocument.body", "CONTRADICTED"),
        ),
    )
    packet = review_packet(ENTRY, facts, "# Old\n", "# New\n", {}, {}, {"checks": []})
    listed = {record["value"] for record in packet["facts"] if record["kind"] == "public_symbol"}
    assert listed == {"aspose_html.URL"}
    # The index is values only, SUPPORTED only, and never repeats what `facts` already carries.
    assert packet["symbol_index"] == f"{deep}, aspose_html.dom.html.HTMLDocument.cookie"
    assert set(packet) == REVIEWER.manifest.packet.names


def test_the_symbol_index_says_so_when_nothing_is_left_out_and_is_capped_when_a_lot_is() -> None:
    facts = FactsDocument(ENTRY.repository, "a" * 40, (_symbol("aspose_html.URL"),))
    assert symbol_index(facts, {"public_symbol:aspose_html.url"}).startswith("none:")
    many = FactsDocument(
        ENTRY.repository,
        "a" * 40,
        tuple(_symbol(f"pkg.mod.Type{i}.member{i}") for i in range(2000)),
    )
    index = symbol_index(many, set())
    assert len(index) <= SYMBOL_INDEX_CHARS + 60
    assert index.endswith("more not listed") and index.startswith("pkg.mod.Type0.member0, ")
    shown = index.count("pkg.mod.")
    assert f"and {2000 - shown} more not listed" in index
