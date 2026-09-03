"""Fact records: stable IDs, mandatory evidence, deterministic JSON, and the schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.core.facts import (
    Evidence,
    Fact,
    FactsDocument,
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
