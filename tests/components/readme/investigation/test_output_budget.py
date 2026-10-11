"""S3 output budget: a reply the schema admits must fit the manifest's max_output_tokens.

The defect (Aspose.Font-FOSS-for-Python, 2026-10-10, call ba605653fa64): a repository_investigation
reply reached finish_reason length at 3,000 tokens while still inside ``limitations``. Nothing in
the manifest bounded a string or the uncertainties list, so the longest admissible reply was
infinite, and the largest sealed reply (2,563 tokens) left no room for a repository with a wider
API surface. Now every string and list is bounded, and the budget is derived from the longest reply
that bound admits (``dossier.output_chars_bound``), not guessed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.components.readme.investigation import dossier
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

LOADED = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
BUDGET = LOADED.manifest.sampling.max_output_tokens
# The longest fact ID any sealed investigation cites (64 characters in 37 sealed investigations).
CITED_ID_CHARS = 64


def _facts(count: int = 400) -> FactsDocument:
    prefix = "public_symbol:"
    return FactsDocument(
        "org/Aspose.Widget-FOSS-for-Python",
        "a" * 40,
        tuple(
            Fact(
                f"{prefix}{'m' * (CITED_ID_CHARS - len(prefix) - 5)}{index:05}",
                "public_symbol",
                "v",
                (Evidence("x"),),
            )
            for index in range(count)
        ),
    )


def _truncated_font_reply() -> str:
    path = Path(__file__).parent / "fixtures" / "ba605653fa64.rejected-1.json"
    return str(json.loads(path.read_text(encoding="utf-8"))["content"])


def test_the_manifest_alone_admits_an_unbounded_reply() -> None:
    """RED, the defect as it stood: strings and the uncertainties list carried no bound."""
    assert dossier.output_chars_bound(LOADED.manifest.output.schema_) is None


def test_the_longest_reply_the_call_schema_admits_fits_the_budget() -> None:
    schema = dossier.investigation_schema(LOADED, _facts())
    chars = dossier.output_chars_bound(schema)
    assert chars is not None  # no field the schema leaves open makes the bound infinite
    assert chars / dossier.OUTPUT_CHARS_PER_TOKEN <= BUDGET


def test_the_budget_holds_the_reply_font_python_needed() -> None:
    """The truncated reply was 13,074 characters and still inside ``limitations``; at the measured
    rate it needed more than 3,000 tokens, and the new budget holds it and the rest of the reply."""
    truncated = _truncated_font_reply()
    assert len(truncated) / dossier.OUTPUT_CHARS_PER_TOKEN > 3000
    assert len(truncated) / dossier.OUTPUT_CHARS_PER_TOKEN < BUDGET


def test_what_font_python_wrote_before_the_cut_is_within_the_new_bounds() -> None:
    """The bounds must not reject legitimate content: every complete field of the truncated reply
    validates under the new manifest schema."""
    text = _truncated_font_reply()
    complete = json.loads(text[: text.index('"limitations"')].rstrip().rstrip(",") + "}")
    schema = copy.deepcopy(LOADED.manifest.output.schema_)
    schema["required"] = sorted(complete)
    assert Draft202012Validator(schema).is_valid(complete)


def _valid_reply(fact_id: str = "identity:repository") -> dict[str, Any]:
    statement = {"text": "A sentence.", "fact_ids": [fact_id]}
    return {
        "product_summary": statement,
        "audience": statement,
        "problems_solved": [statement],
        "workflows": [{"name": "n", **statement}],
        "capabilities": [{"title": "t", **statement}] * 3,
        "limitations": [],
        "uncertainties": ["A question."],
    }


def test_a_reply_past_the_text_or_uncertainty_bounds_is_rejected() -> None:
    """Negative control: the bound is real. An unbounded reply is still refused."""
    validator = Draft202012Validator(LOADED.manifest.output.schema_)
    assert validator.is_valid(_valid_reply())
    for mutate in (
        lambda r: r["product_summary"].update(text="x" * 401),
        lambda r: r["workflows"][0].update(name="x" * 101),
        lambda r: r["capabilities"][0].update(title="x" * 101),
        lambda r: r["capabilities"][0].update(text="x" * 401),
        lambda r: r.update(uncertainties=["q"] * 9),
        lambda r: r.update(uncertainties=["x" * 301]),
    ):
        reply = copy.deepcopy(_valid_reply())
        mutate(reply)
        assert not validator.is_valid(reply)


def test_a_repeating_citation_list_stays_capped() -> None:
    """The font reply's audience repeated install_command:pip fourteen times; the cap that bounds
    it (and the 171 repeats of example:005 that ran S3 out on PDF-TypeScript) is unchanged."""
    facts = _facts(30)
    schema = dossier.investigation_schema(LOADED, facts)
    ids = sorted(fact.id for fact in facts.facts)
    reply = _valid_reply(ids[0])
    reply["audience"] = {"text": "A sentence.", "fact_ids": [ids[0]] * 15}
    assert not Draft202012Validator(schema).is_valid(reply)
    reply["audience"] = {"text": "A sentence.", "fact_ids": [ids[0]] * 14}
    assert Draft202012Validator(schema).is_valid(reply)


def test_the_prompt_states_the_limits_the_reply_is_decoded_under() -> None:
    system = LOADED.manifest.system
    assert "at most 14 fact IDs" in system and "at most 11" in system
    assert "at most 400 characters" in system
    assert "at most eight items of at most 300 characters" in system
