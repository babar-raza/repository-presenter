"""The ledger is append-only JSON lines whose records reconcile provider calls and reuses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.core.llm.ledger import CallRecord, Ledger, canonical_hash, load_records
from support import REPO_ROOT, call_statistics


def _record(call_id: str, disposition: str, outcome: str, tokens: int | None) -> CallRecord:
    return CallRecord(
        call_id=call_id,
        logical_call_id="logical",
        repository="org/repo",
        source_revision="a" * 40,
        stage="S3",
        job="repository_investigation",
        prompt_sha256="b" * 64,
        model_route="qwen3-next",
        model_served="qwen3-next" if disposition == "provider_call" else None,
        attempt=1 if disposition == "provider_call" else 0,
        disposition=disposition,  # type: ignore[arg-type]
        started_at="2026-09-02T12:00:00.000+00:00",
        finished_at="2026-09-02T12:00:01.000+00:00",
        latency_ms=1000,
        outcome=outcome,  # type: ignore[arg-type]
        http_status=200 if disposition == "provider_call" else None,
        request_sha256="c" * 64,
        response_sha256="d" * 64,
        provider_request_id="chatcmpl-1",
        prompt_tokens=None if tokens is None else tokens - 5,
        completion_tokens=None if tokens is None else 5,
        total_tokens=tokens,
        error_class=None,
    )


def test_records_round_trip_and_summarize(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "t" / "calls.jsonl")
    ledger.append(_record("one", "provider_call", "success", 30))
    ledger.append(_record("two", "provider_call", "http_error", None))
    ledger.append(_record("three", "cache_reuse", "cache_reuse", None))
    raw = ledger.path.read_bytes()
    assert raw.count(b"\n") == 3 and b"\r\n" not in raw
    assert raw.startswith(b'{"attempt":1,"call_id":"one"')
    records = ledger.records()
    assert [r.call_id for r in records] == ["one", "two", "three"]
    assert records[0] == _record("one", "provider_call", "success", 30)
    summary = ledger.summary()
    assert (summary.provider_calls, summary.cache_reuses) == (2, 1)
    assert summary.calls_by_job == {"repository_investigation": 2}
    assert summary.total_tokens is None
    assert Ledger(tmp_path / "absent.jsonl").summary().provider_calls == 0


def test_duplicate_or_malformed_lines_are_defects(tmp_path: Path) -> None:
    path = tmp_path / "calls.jsonl"
    line = _record("one", "provider_call", "success", 30).to_line()
    path.write_text(line + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate call ID one"):
        load_records(path)
    path.write_text('{"call_id": "x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="do not match CallRecord"):
        load_records(path)


def test_canonical_hash_ignores_key_order_and_whitespace_only() -> None:
    assert canonical_hash({"b": 1, "a": [1, 2]}) == canonical_hash({"a": [1, 2], "b": 1})
    assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})
    assert len(canonical_hash("text")) == 64


# RESEARCH_AND_GUIDELINES.md section 27.6 control 1. The floors are what the sealed canary
# measures today, so a change that makes the model re-ask more often fails here; G2-W12 raises
# the prose families the gateway will not constrain; section 27.10 records why 95 is not
# reachable. The floor is 85 and not the 91.7 percent one composition measured: a composition
# is about 24 provider calls, so a single extra rejection moves the rate four points, and two
# compositions of the same configuration measured 91.7 and 87.5. A floor tighter than the
# sample supports would fail on noise rather than on a regression.
SEALED_LEDGER = (
    REPO_ROOT
    / "candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    / "65b1f577c0f16d0d9112bb6c1153d3024543ac02/calls.jsonl"
)
FIRST_ATTEMPT_FLOOR = 85.0
REASK_CEILING = 15.0


def test_the_sealed_canarys_first_attempt_acceptance_holds_its_floor() -> None:
    statistics = call_statistics(SEALED_LEDGER)
    total = statistics["TOTAL"]
    assert total.calls >= 20, "too few provider calls for the ratio to mean anything"
    assert total.first_attempt_rate >= FIRST_ATTEMPT_FLOOR
    assert total.reask_share <= REASK_CEILING
    # Every job the composition runs is measured, so a new job cannot slip in unmeasured.
    assert set(statistics) == {
        "TOTAL",
        "independent_review",
        "presentation_planning",
        "repository_investigation",
        "section_authoring",
        "source_reconciliation",
        "targeted_repair",
    }
    assert sum(entry.calls for job, entry in statistics.items() if job != "TOTAL") == total.calls


def test_the_statistics_count_only_provider_calls_and_their_rejections(tmp_path: Path) -> None:
    ledger = tmp_path / "calls.jsonl"
    ledger.write_text(
        "\n".join(
            json.dumps(record)
            for record in (
                {"job": "a", "disposition": "provider_call", "outcome": "success"},
                {"job": "a", "disposition": "provider_call", "outcome": "response_invalid"},
                {"job": "a", "disposition": "cache_reuse", "outcome": "cache_reuse"},
                {"job": "b", "disposition": "provider_call", "outcome": "success"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    statistics = call_statistics(ledger)
    assert statistics["a"].calls == 2 and statistics["a"].invalid == 1
    assert statistics["a"].first_attempt_rate == 50.0 and statistics["a"].reask_share == 50.0
    assert statistics["b"].first_attempt_rate == 100.0
    assert statistics["TOTAL"].calls == 3 and statistics["TOTAL"].invalid == 1


def test_a_ledger_sealed_before_the_rejection_field_still_reads(tmp_path: Path) -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.6 control 1 needs the rejection in the sealed record,
    # and adding a field must not make an already sealed ledger unreadable: a field with a
    # default reads as its default, while an unknown field is still a defect.
    assert load_records(SEALED_LEDGER), "the sealed canary's ledger must still load"

    older = json.loads(_record("older", "provider_call", "response_invalid", 10).to_line())
    del older["rejection"], older["schema_version"]
    path = tmp_path / "calls.jsonl"
    path.write_text(json.dumps(older) + "\n", encoding="utf-8")
    (record,) = load_records(path)
    assert record.rejection == () and record.schema_version == 1

    path.write_text(json.dumps({**older, "unexpected": 1}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="do not match CallRecord"):
        load_records(path)


def test_the_statistics_carry_why_each_job_re_asked(tmp_path: Path) -> None:
    path = tmp_path / "calls.jsonl"
    path.write_text(
        json.dumps(
            {
                "job": "a",
                "disposition": "provider_call",
                "outcome": "response_invalid",
                "rejection": ["fact example:008 is CONTRADICTED, not SUPPORTED"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert call_statistics(path)["a"].rejections == (
        "fact example:008 is CONTRADICTED, not SUPPORTED",
    )
