"""Fact records: stable IDs, mandatory evidence, deterministic JSON, and the schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.core.facts import (
    DECLARED_SYMBOL_KINDS,
    Evidence,
    Fact,
    FactsDocument,
    bounded_records,
    fact_id,
    slug,
    write_facts,
)
from support import REPO_ROOT

REVISION = "a" * 40


def sample_document() -> FactsDocument:
    return FactsDocument(
        repository="example-org/Aspose.Example-FOSS-for-Python",
        source_revision=REVISION,
        facts=(
            Fact(
                fact_id("package", "name"),
                "package",
                "aspose-example",
                (Evidence("setup.py", "name keyword"),),
            ),
            Fact(
                fact_id("install_command", "pip"),
                "install_command",
                "pip install aspose-example",
                (Evidence("setup.py"),),
                polarity="UNRESOLVED",
                confidence=0.5,
            ),
            Fact(fact_id("identity", "revision"), "identity", REVISION, (Evidence("source/"),)),
        ),
    )


def test_slugs_are_lowercase_identifier_safe_and_stable() -> None:
    assert slug("Aspose.3D FOSS") == "aspose.3d-foss"
    assert slug("aspose.threed") == "aspose.threed"
    # A run of separators keeps its first character: Python names a symbol dict_ or class_
    # to avoid a keyword, and Aspose.Font's aspose_font.cff.dict_.PrivateDictOp crashed
    # fact extraction outright before this (measured 2026-09-06).
    assert slug("aspose_font.cff.dict_.PrivateDictOp") == "aspose_font.cff.dict_privatedictop"
    assert slug("a--b") == "a-b" and slug("x..y") == "x.y"
    # The collapse never merges a keyword-avoiding name with the real one.
    assert slug("Class_.Method") != slug("Class.Method")
    assert fact_id("import_path", "aspose.threed") == "import_path:aspose.threed"
    assert fact_id("build_test_asset", "tests", "ci") == "build_test_asset:tests.ci"
    with pytest.raises(ValueError, match="cannot derive"):
        slug("!!!")
    with pytest.raises(ValueError, match="at least one part"):
        fact_id("package")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"id": "package:name", "kind": "license"}, "must be <kind>:<slug>"),
        ({"id": "package:Name"}, "must be <kind>:<slug>"),
        ({"evidence": ()}, "carries no evidence"),
        ({"value": ""}, "empty value"),
        ({"confidence": 1.5}, "between 0 and 1"),
        ({"polarity": "MAYBE"}, "unknown polarity"),
        ({"kind": "rumor", "id": "rumor:x"}, "unknown fact kind"),
    ],
)
def test_malformed_facts_are_rejected(kwargs: dict[str, object], message: str) -> None:
    base: dict[str, object] = {
        "id": "package:name",
        "kind": "package",
        "value": "x",
        "evidence": (Evidence("setup.py"),),
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=message):
        Fact(**base)  # type: ignore[arg-type]


def test_evidence_needs_a_path() -> None:
    with pytest.raises(ValueError, match="needs a path"):
        Evidence("")


def test_documents_reject_duplicate_ids() -> None:
    fact = Fact("package:name", "package", "x", (Evidence("setup.py"),))
    with pytest.raises(ValueError, match="duplicate fact IDs"):
        FactsDocument("o/Aspose.X-FOSS-for-Go", REVISION, (fact, fact))


def test_json_is_sorted_and_byte_identical_across_orderings(tmp_path: Path) -> None:
    document = sample_document()
    reordered = FactsDocument(document.repository, document.source_revision, document.facts[::-1])
    assert document.to_json() == reordered.to_json()
    payload = json.loads(document.to_json())
    assert [fact["id"] for fact in payload["facts"]] == sorted(
        fact["id"] for fact in payload["facts"]
    )
    digest = write_facts(document, tmp_path / "facts.json")
    assert len(digest) == 64
    assert (tmp_path / "facts.json").read_bytes() == document.to_json().encode("utf-8")
    assert b"\r\n" not in (tmp_path / "facts.json").read_bytes()


def test_document_validates_against_the_schema() -> None:
    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(json.loads(sample_document().to_json()))) == []
    broken = json.loads(sample_document().to_json())
    broken["facts"][0]["evidence"] = []
    assert list(validator.iter_errors(broken))


def test_by_kind_filters() -> None:
    document = sample_document()
    assert [fact.id for fact in document.by_kind("package")] == ["package:name"]
    assert document.by_kind("example") == ()


def test_bounded_records_never_admits_identity_revision() -> None:
    """G5-W02 (27.2 RC4). A job packet is rendered to text and hashed to key the call store, so a
    fact embedded in every packet changes that hash on every new revision even when nothing a job
    would reason about changed. `identity:revision` is excluded from every packet this way; a
    sibling `identity` fact (`identity:repository`) is untouched, proving the exclusion is by
    fact ID, not by kind."""
    document = sample_document()
    records = bounded_records(
        document, ["package", "install_command", "identity"], ("SUPPORTED", "UNRESOLVED")
    )
    assert {record["id"] for record in records} == {"package:name", "install_command:pip"}
    assert "identity:revision" not in {record["id"] for record in records}

    with_repository = FactsDocument(
        document.repository,
        document.source_revision,
        (
            *document.facts,
            Fact(
                fact_id("identity", "repository"), "identity", document.repository, (Evidence("x"),)
            ),
        ),
    )
    records = bounded_records(with_repository, ["identity"])
    assert {record["id"] for record in records} == {"identity:repository"}


def _symbol(path: str, symbol_kind: str) -> Fact:
    return Fact(
        f"public_symbol:{path.lower()}",
        "public_symbol",
        path,
        (Evidence("src/x.py", f"line 1; {symbol_kind}; public by name"),),
        attributes={"symbol_kind": symbol_kind},
    )


SURFACE = FactsDocument(
    "aspose-page-foss/Aspose.Page-FOSS-for-Python",
    REVISION,
    (
        _symbol("aspose.page", "module"),
        _symbol("aspose.page.ps", "module"),
        _symbol("aspose.page.ps.PsDocument", "class"),
        _symbol("aspose.page.ps.PsDocument.save", "method"),
        _symbol("aspose.page.common.RenderModel", "class"),
        Fact(
            "public_symbol:aspose.page.xps.xpsdocument",
            "public_symbol",
            "aspose.page.xps.XpsDocument",
            (Evidence("src/x.py"),),
            attributes={"symbol_kind": "unknown"},
        ),
    ),
)


def test_symbol_kinds_bound_a_packet_by_declaration_not_by_dotted_depth() -> None:
    """G4-W17 arrival item 40. `symbol_max_depth` counts dots in the whole path, so how much of a
    repository's surface a job may cite depends on how many segments its package root happens to
    have. Measured 2026-09-07 over the sealed bundles: Aspose.PDF for Java admitted 3 of its
    24,830 public symbols (`org`, `org.aspose`, `org.aspose.pdf` - not one class) and Aspose.3D
    for Java 3 of 5,366, while Aspose.Slides for Python, root `slides_foss`, admitted 1,702 of
    3,180 including every method. Aspose.Page for Python (root `aspose.page`) reached S4 with
    about seven namespace strings of its 570 symbols, and its reconciliation was rejected twice
    for citing `public_symbol:aspose.page.common` - the only shape of thing it had been shown.
    Bounding by the kind the extractor already recorded is root-shape independent."""
    depth_bound = {record["value"] for record in bounded_records(SURFACE, ["public_symbol"])}
    # The defect, still reproducible through the default: not one class of this root survives.
    assert depth_bound == {"aspose.page", "aspose.page.ps"}

    declared = {
        record["value"]
        for record in bounded_records(
            SURFACE, ["public_symbol"], symbol_kinds=DECLARED_SYMBOL_KINDS
        )
    }
    assert "aspose.page.ps.PsDocument" in declared
    assert "aspose.page.common.RenderModel" in declared
    # A member is still out: the kind bound replaces the depth proxy, it does not lift it.
    assert "aspose.page.ps.PsDocument.save" not in declared
    # A symbol the surface facade's table does not map records "unknown" for a whole ecosystem
    # (G4-W17 arrival item 9, Go and Rust); it keeps the depth bound rather than vanishing.
    assert "aspose.page.xps.XpsDocument" not in declared
    assert {"aspose.page", "aspose.page.ps"} <= declared

    # The cap still bounds the count, whichever rule admitted the symbol.
    capped = bounded_records(
        SURFACE, ["public_symbol"], symbol_kinds=DECLARED_SYMBOL_KINDS, symbol_cap=2
    )
    assert len(capped) == 2


def test_structured_attributes_round_trip_through_json_and_the_schema() -> None:
    import json as _json

    import jsonschema as _jsonschema

    fact = Fact(
        "public_symbol:pkg.widget",
        "public_symbol",
        "pkg.Widget",
        (Evidence("pkg/widget.py", "line 1; class; public by name"),),
        attributes={"symbol_kind": "class", "signature": "class Widget"},
    )
    document = FactsDocument("org/repo", "a" * 40, (fact,))
    payload = _json.loads(document.to_json())
    schema = _json.loads(Path("schemas/facts.schema.json").read_text(encoding="utf-8"))
    _jsonschema.Draft202012Validator(schema).validate(payload)
    assert payload["facts"][0]["attributes"] == {
        "symbol_kind": "class",
        "signature": "class Widget",
    }
    with pytest.raises(ValueError, match="attributes must map"):
        Fact("identity:x", "identity", "x", (Evidence("p"),), attributes={"k": ""})
