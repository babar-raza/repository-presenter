"""The runner renders, calls once, validates, binds, re-asks once, stores, and reuses."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.components.readme.bundle.seal import seed_call_store
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, JobError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    render_messages,
    request_payload,
    run_job,
)
from repository_presenter.core.llm.ledger import Ledger, canonical_hash
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT, mock_gateway

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
CONTEXT = JobContext("org/repo", "a" * 40)
FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "org/repo", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
        Fact("example:001", "example", "print(1)", (Evidence("README.md"),)),
        Fact("example:002", "example", "boom", (Evidence("README.md"),), polarity="CONTRADICTED"),
    ),
)
MANIFEST = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
PACKET: dict[str, Any] = {
    "repository": "org/repo",
    "ecosystem": "python",
    "fact_dossier": [{"id": "identity:repository", "kind": "identity", "value": "org/repo"}],
    "inherited_units": [],
}


def _investigation(*capability_fact_ids: str) -> dict[str, Any]:
    statement = {"text": "It does things.", "fact_ids": ["identity:repository"]}
    return {
        "product_summary": statement,
        "audience": statement,
        "problems_solved": [statement],
        "workflows": [],
        "capabilities": [
            {"title": f"Do {i}", "text": "One sentence.", "fact_ids": [fact_id]}
            for i, fact_id in enumerate(capability_fact_ids)
        ],
        "limitations": [],
        "uncertainties": [],
    }


def _completion(
    content: Any, model: str = "qwen3-next", finish_reason: str = "stop"
) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(content)},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    return httpx.Response(200, json=body)


class _Gateway:
    """Serves scripted chat completions and records every request body."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        mock_gateway(monkeypatch, self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        self.requests.append(json.loads(request.content))
        return self.responses.pop(0)


def test_messages_render_the_packet_and_the_payload_follows_the_sampling_contract() -> None:
    messages = render_messages(MANIFEST, PACKET)
    system = messages[0]["content"]
    assert messages[0]["role"] == "system" and system.startswith(MANIFEST.manifest.system)
    assert '"required": [\n  "product_summary",' in system
    assert system.endswith("}\n")
    user = messages[1]["content"]
    assert "Repository: org/repo" in user and "Ecosystem: python" in user
    assert '"id": "identity:repository"' in user
    payload = request_payload(MANIFEST, messages)
    assert payload["model"] == "qwen3-next" and payload["temperature"] == 0.0
    assert payload["max_tokens"] == 3000
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "repository_investigation",
            "schema": MANIFEST.manifest.output.schema_,
            "strict": True,
        },
    }
    with pytest.raises(ConfigError, match=r"missing \['inherited_units'\], unexpected \['extra'\]"):
        render_messages(
            MANIFEST, {**{k: v for k, v in PACKET.items() if k != "inherited_units"}, "extra": 1}
        )


def test_an_accepted_output_is_stored_and_reused_without_a_second_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    result = run_job(
        MANIFEST, PACKET, config=CONFIG, facts=FACTS, ledger=ledger, store=store, context=CONTEXT
    )
    assert (result.attempts, result.provider_calls, result.cache_reused) == (1, 1, False)
    assert result.model_served == "qwen3-next" and result.total_tokens == 120
    assert result.output["capabilities"][0]["fact_ids"] == ["package:name"]
    assert len(gateway.requests) == 1
    assert gateway.requests[0]["model"] == "qwen3-next"
    assert gateway.requests[0]["messages"][0]["role"] == "system"
    assert store.get(result.request_sha256) == result.output

    again = run_job(
        MANIFEST, PACKET, config=CONFIG, facts=FACTS, ledger=ledger, store=store, context=CONTEXT
    )
    assert (again.provider_calls, again.cache_reused, again.output) == (0, True, result.output)
    assert len(gateway.requests) == 1
    records = ledger.records()
    assert [(r.disposition, r.outcome, r.attempt) for r in records] == [
        ("provider_call", "success", 1),
        ("cache_reuse", "cache_reuse", 0),
    ]
    assert records[0].prompt_sha256 == MANIFEST.sha256 and records[0].total_tokens == 120
    assert records[0].model_served == "qwen3-next" and records[0].http_status == 200
    # TB-07, external review D7, 2026-09-08: the live ("provider_call") record's own
    # request_sha256 field must be the exact value CallStore is actually keyed by - what
    # run_job() returns as result.request_sha256 - not a different hash that merely shares the
    # field name. Before this fix it was canonical_hash(payload) alone, never matching the real
    # cache key (canonical_hash of {"prompt_sha256", "payload"} together), so seed_call_store
    # (which reads exactly this field from a sealed bundle's ledger to pre-populate a fresh
    # process's store) seeded a key no lookup could ever find.
    assert records[0].request_sha256 == result.request_sha256
    assert records[1].request_sha256 == result.request_sha256
    assert ledger.summary().provider_calls == 1 and ledger.summary().cache_reuses == 1


def test_a_genuinely_cold_process_reuses_a_seeded_sealed_bundles_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TB-07, external review D7, 2026-09-08: seed_call_store's whole purpose (RC4 - a hosted
    runner's first run of an already-sealed revision, with nothing under the gitignored runs/
    directory to reuse) depends on the ledger's own request_sha256 being the exact key CallStore
    is looked up by. Before this fix it never was, so a genuinely fresh process re-running an
    already-sealed composition would remake every "seedable" call live - the gap this test proves
    closed, with a real run_job() computing the key, never a synthetic one."""
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    sealing_ledger = Ledger(tmp_path / "sealing" / "calls.jsonl")
    sealed = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=sealing_ledger,
        store=CallStore(tmp_path / "sealing" / "calls"),
        context=CONTEXT,
    )
    assert sealed.provider_calls == 1  # the original sealing composition's own live call

    # A sealed bundle carrying just this one job's own ledger and its accepted artifact -
    # everything seed_call_store needs, and nothing a real bundle wouldn't also have.
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "investigation.json").write_text(json.dumps(sealed.output) + "\n", encoding="utf-8")
    (bundle / "calls.jsonl").write_bytes((tmp_path / "sealing" / "calls.jsonl").read_bytes())

    fresh_store = CallStore(tmp_path / "cold" / "calls")
    assert seed_call_store(bundle, fresh_store) == ["repository_investigation"]

    # No further response queued: a live call here would raise IndexError on gateway.responses,
    # failing the test loudly rather than silently falling back to one.
    cold = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "cold" / "calls.jsonl"),
        store=fresh_store,
        context=CONTEXT,
    )
    assert (cold.provider_calls, cold.cache_reused, cold.output) == (0, True, sealed.output)
    assert len(gateway.requests) == 1  # only the original sealing call ever reached the gateway


def test_a_rejected_output_earns_one_re_ask_that_quotes_the_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:002", "nope:1")),
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    ledger = Ledger(tmp_path / "calls.jsonl")
    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
    )
    assert (result.attempts, result.provider_calls) == (2, 2)
    second = gateway.requests[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-1]["role"] == "user"
    assert "fact example:002 is CONTRADICTED, not SUPPORTED" in second[-1]["content"]
    assert "unknown fact ID nope:1" in second[-1]["content"]
    assert [(r.outcome, r.attempt) for r in ledger.records()] == [
        ("success", 1),
        ("response_invalid", 1),
        ("success", 2),
    ]


def test_a_jobs_own_checks_are_quoted_in_the_re_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:001", "identity:repository")),
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    seen: list[int] = []

    def checks(output: dict[str, Any]) -> list[str]:
        seen.append(len(output["capabilities"]))
        return [] if len(seen) > 1 else ["capability titles repeat the keyword Do"]

    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
        checks=checks,
    )
    assert result.attempts == 2 and seen == [3, 3]
    assert (
        "capability titles repeat the keyword Do" in gateway.requests[1]["messages"][-1]["content"]
    )


def test_a_binding_defect_does_not_suppress_a_simultaneous_domain_check_defect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 100 (PGPY-02). Before this fix, ``_parse`` only ran a job's own
    ``checks`` when ``binding_errors`` was already clean, so an attempt carrying both a binding
    defect (an unknown or unsupported cited fact) and a domain defect (whatever ``checks`` judges)
    only ever surfaced the binding one - the model's sole re-ask fixed what it was told, the
    domain defect survived byte-identical, and by the time ``checks`` finally ran the budget was
    spent (measured live on Page-Python, docs/DECISION_LOG.md 2026-09-16 20:20 UTC).

    Attempt 1 here cites both a CONTRADICTED fact and an unknown one (a real binding defect) AND
    trips the domain ``checks`` callable - the fix surfaces both in the one rejection message, so
    a single re-ask can fix both at once, exactly as it does for two binding defects together
    (the sibling test above this one).
    """
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:002", "nope:1")),
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    seen: list[int] = []

    def checks(output: dict[str, Any]) -> list[str]:
        seen.append(len(output["capabilities"]))
        return [] if len(seen) > 1 else ["capability titles repeat the keyword Do"]

    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
        checks=checks,
    )
    assert result.attempts == 2
    # checks ran on attempt 1 despite the binding defect - both classes of defect were judged.
    assert seen == [3, 3]
    rejection = gateway.requests[1]["messages"][-1]["content"]
    assert "fact example:002 is CONTRADICTED, not SUPPORTED" in rejection
    assert "unknown fact ID nope:1" in rejection
    assert "capability titles repeat the keyword Do" in rejection


def test_a_schema_defect_still_suppresses_domain_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The narrower half of item 100's fix: gating ``checks`` on the schema alone, not on
    ``binding_errors`` too, is safe only because a schema-valid output is exactly the shape a
    domain check is written against - a schema-invalid one is not, and must never reach it. This
    proves ``checks`` is never even called when attempt 1 fails schema validation (here, an object
    with none of the required keys) - a domain check written to assume a valid shape (as this one
    does, indexing ``output["capabilities"]`` with no ``.get`` fallback) would raise if it were.
    """
    _Gateway(
        monkeypatch,
        _completion({"not": "the schema"}),
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    calls = 0

    def checks(output: dict[str, Any]) -> list[str]:
        nonlocal calls
        calls += 1
        len(output["capabilities"])  # would raise KeyError on the malformed reply
        return []

    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
        checks=checks,
    )
    assert result.attempts == 2
    assert calls == 1  # only the schema-valid second attempt ever reached checks


def test_a_truncated_reply_fails_fast_naming_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(monkeypatch, _completion('{"product_summary": {', finish_reason="length"))
    ledger = Ledger(tmp_path / "calls.jsonl")
    with pytest.raises(JobError, match=r"truncated at the manifest's max_output_tokens \(3000\)"):
        run_job(
            MANIFEST,
            PACKET,
            config=CONFIG,
            facts=FACTS,
            ledger=ledger,
            store=CallStore(tmp_path / "calls"),
            context=CONTEXT,
        )
    assert len(gateway.requests) == 1
    assert [(r.outcome, r.error_class) for r in ledger.records()] == [
        ("success", None),
        ("response_invalid", "TruncatedOutput"),
    ]


def test_a_second_rejection_fails_the_job_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _Gateway(monkeypatch, _completion({"not": "the schema"}), _completion("not an object"))
    store = CallStore(tmp_path / "calls")
    with pytest.raises(
        JobError, match="output rejected twice; last rejection: output is not a JSON object"
    ):
        run_job(
            MANIFEST,
            PACKET,
            config=CONFIG,
            facts=FACTS,
            ledger=Ledger(tmp_path / "calls.jsonl"),
            store=store,
            context=CONTEXT,
        )
    kept = sorted(path.name for path in store.directory.iterdir())
    assert [name.rsplit(".", 2)[1] for name in kept] == ["rejected-1", "rejected-2"]
    assert all("rejected" in name for name in kept)  # no accepted output was stored


def test_recover_is_never_consulted_while_a_re_ask_can_still_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 111 (PGPY-04): ``recover`` is a genuine last resort - a job that
    reaches a valid second attempt never even shows ``recover`` its output, so the model's own
    re-ask is always given the first (and, here, only needed) chance."""
    _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:002", "nope:1")),  # rejected
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    seen: list[dict[str, Any]] = []
    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
        recover=seen.append,  # type: ignore[arg-type]
    )
    assert result.attempts == 2
    assert seen == []


def test_a_last_resort_recover_saves_a_final_rejection_it_can_actually_fix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 111 (PGPY-04). Measured on Page-Python (docs/DECISION_LOG.md
    2026-09-17 03:27 UTC): composition/planning.py's own supporting_fact_ids hint (item 95)
    already named real candidate facts in the rejection message, but the model's sole re-ask
    sometimes retitles rather than cites one, exhausting core/llm/jobs.py's one universal re-ask
    per job without curing the defect. Here, both live attempts reject identically (an unknown and
    a CONTRADICTED citation); ``recover`` deterministically substitutes real SUPPORTED facts - the
    same shape composition/planning.py's own ``recover_uncited_capability_titles`` performs - and
    the corrected output is accepted with no third provider call."""
    _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:002", "nope:1")),
        _completion(_investigation("package:name", "example:002", "nope:1")),
    )

    def recover(output: dict[str, Any]) -> dict[str, Any]:
        for item in output["capabilities"]:
            if item["fact_ids"] == ["example:002"]:
                item["fact_ids"] = ["example:001"]
            elif item["fact_ids"] == ["nope:1"]:
                item["fact_ids"] = ["identity:repository"]
        return output

    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
        recover=recover,
    )
    assert (result.attempts, result.provider_calls) == (2, 2)
    fixed_ids = sorted(
        fact_id for item in result.output["capabilities"] for fact_id in item["fact_ids"]
    )
    assert fixed_ids == sorted(["package:name", "example:001", "identity:repository"])


def test_recover_that_cannot_fully_fix_the_output_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial or wrong ``recover`` correction is re-validated from scratch, exactly like any
    other candidate output - it never passes on its own say-so, so the job fails closed identically
    to a job with no ``recover`` at all."""
    _Gateway(
        monkeypatch,
        _completion(_investigation("package:name", "example:002", "nope:1")),
        _completion(_investigation("package:name", "example:002", "nope:1")),
    )

    def half_fix(output: dict[str, Any]) -> dict[str, Any]:
        for item in output["capabilities"]:
            if item["fact_ids"] == ["example:002"]:
                item["fact_ids"] = ["example:001"]
            # "nope:1" is deliberately left unfixed - still an unknown fact ID.
        return output

    with pytest.raises(JobError, match="output rejected twice"):
        run_job(
            MANIFEST,
            PACKET,
            config=CONFIG,
            facts=FACTS,
            ledger=Ledger(tmp_path / "calls.jsonl"),
            store=CallStore(tmp_path / "calls"),
            context=CONTEXT,
            recover=half_fix,
        )


def test_transient_failures_are_retried_and_accounted_and_refusals_are_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("repository_presenter.core.retry.time.sleep", lambda seconds: None)
    _Gateway(
        monkeypatch,
        httpx.Response(503, json={"error": "busy"}),
        _completion(_investigation("package:name", "example:001", "identity:repository")),
    )
    ledger = Ledger(tmp_path / "calls.jsonl")
    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=CallStore(tmp_path / "calls"),
        context=CONTEXT,
    )
    assert (result.attempts, result.provider_calls) == (2, 2)
    assert [(r.outcome, r.http_status, r.error_class) for r in ledger.records()] == [
        ("http_error", 503, "InternalServerError"),
        ("success", 200, None),
    ]

    _Gateway(monkeypatch, httpx.Response(401, json={"error": "no"}))
    with pytest.raises(JobError, match="gateway answered HTTP 401"):
        run_job(
            MANIFEST,
            PACKET,
            config=CONFIG,
            facts=FACTS,
            ledger=Ledger(tmp_path / "other.jsonl"),
            store=CallStore(tmp_path / "other"),
            context=CONTEXT,
        )


def test_the_seed_travels_with_every_request_and_two_identical_requests_agree() -> None:
    # RESEARCH_AND_GUIDELINES.md sections 18.4 and 27.5 D4: the gateway accepts seed for the
    # routed model, probed in G2-W19, so the manifests declare it and every request carries it.
    # Two identical requests must be identical byte for byte, which is what lets the call store
    # answer the second one without asking the gateway again.
    assert MANIFEST.manifest.sampling.seed == 1
    messages = render_messages(MANIFEST, PACKET)
    payload = request_payload(MANIFEST, messages)
    assert payload["seed"] == 1
    again = request_payload(MANIFEST, render_messages(MANIFEST, PACKET))
    assert canonical_hash(payload) == canonical_hash(again)
    assert payload == again

    # A manifest that declares no seed sends none, so the field never appears by default.
    seedless = replace(
        MANIFEST,
        manifest=MANIFEST.manifest.model_copy(
            update={"sampling": MANIFEST.manifest.sampling.model_copy(update={"seed": None})}
        ),
    )
    assert "seed" not in request_payload(seedless, messages)
