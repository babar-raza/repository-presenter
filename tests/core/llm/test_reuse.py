"""A stored output is re-judged under the current checks before it is reused."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repository_presenter.core.llm.ledger import Ledger
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
    ),
)
MANIFEST = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
PACKET: dict[str, Any] = {
    "repository": "org/repo",
    "ecosystem": "python",
    "fact_dossier": [{"id": "identity:repository", "kind": "identity", "value": "org/repo"}],
    "inherited_units": [],
}


def _investigation(title: str) -> dict[str, Any]:
    statement = {"text": "It does things.", "fact_ids": ["identity:repository"]}
    return {
        "product_summary": statement,
        "audience": statement,
        "problems_solved": [statement],
        "workflows": [],
        "capabilities": [
            {"title": name, "text": "One sentence.", "fact_ids": [fact_id]}
            for name, fact_id in (
                (title, "package:name"),
                ("Do 2", "identity:repository"),
                ("Do 3", "package:name"),
            )
        ],
        "limitations": [],
        "uncertainties": [],
    }


def _completion(content: Any) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "qwen3-next",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(content)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    return httpx.Response(200, json=body)


class _Gateway:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        mock_gateway(monkeypatch, self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        return self.responses.pop(0)


def _run(store: CallStore, ledger: Ledger, checks: Any = None) -> Any:
    return run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=store,
        context=CONTEXT,
        checks=checks,
    )


def test_a_normalising_check_reshapes_the_stored_output_on_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(monkeypatch, _completion(_investigation("do things")))
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    first = _run(store, ledger)
    assert first.output["capabilities"][0]["title"] == "do things"

    def capitalise(output: dict[str, Any]) -> list[str]:
        for capability in output["capabilities"]:
            capability["title"] = capability["title"].capitalize()
        return []

    again = _run(store, ledger, checks=capitalise)
    assert (again.provider_calls, again.cache_reused) == (0, True)
    assert again.output["capabilities"][0]["title"] == "Do things"
    assert store.get(first.request_sha256) == again.output
    assert store.record(first.request_sha256)["model_served"] == "qwen3-next"
    assert len(gateway.requests) == 1
    assert [r.disposition for r in ledger.records()] == ["provider_call", "cache_reuse"]


def test_a_stored_output_the_rules_reject_is_replaced_by_a_new_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("do things")),
        _completion(_investigation("Do better things")),
    )
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    first = _run(store, ledger)

    def reject_lowercase(output: dict[str, Any]) -> list[str]:
        return [
            f"title {c['title']!r} must start with a capital"
            for c in output["capabilities"]
            if not c["title"][:1].isupper()
        ]

    replaced = _run(store, ledger, checks=reject_lowercase)
    assert (replaced.provider_calls, replaced.cache_reused) == (1, False)
    assert replaced.output["capabilities"][0]["title"] == "Do better things"
    assert replaced.request_sha256 == first.request_sha256
    assert store.get(first.request_sha256) == replaced.output
    assert len(gateway.requests) == 2
    records = ledger.records()
    assert [(r.disposition, r.outcome, r.error_class) for r in records] == [
        ("provider_call", "success", None),
        ("cache_stale", "cache_stale", "OutputRejected"),
        ("provider_call", "success", None),
    ]
    assert ledger.summary().provider_calls == 2 and ledger.summary().cache_reuses == 0
