"""The runner renders, calls once, validates, binds, re-asks once, stores, and reuses."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

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
    assert records[1].request_sha256 == result.request_sha256
    assert ledger.summary().provider_calls == 1 and ledger.summary().cache_reuses == 1


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
