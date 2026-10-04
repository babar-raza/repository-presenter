"""Model fallback chains: one decision per route per run, recorded, never switched mid-run.

Every probe and every content call goes through the mock gateway (tests/support.py), so these
tests exercise the real SDK client, retry-free transport, and run_job path without the network.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, GatewayError, JobError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.fallback import (
    FALLBACK_CHAINS,
    ModelChainExhaustedError,
    ModelSelection,
    chain_for,
    describe,
    select_models,
)
from repository_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    _Attempts,
    render_messages,
    request_hash,
    request_payload,
    run_job,
)
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.llm.transport import AvailabilityProbe
from repository_presenter.core.preflight import run_gateway_preflight, write_catalog
from support import REPO_ROOT, mock_gateway, model_listing

PRIMARY = "qwen3-next"
CHAIN = ("qwen3-next", "gpt-oss", "recommended", "Qwen2.5-VL-7B")
# The catalog as observed: two chat models that answer, one that answers HTTP 500, and two that
# are not chat routes at all (an image and an embedding model).
ALL_MODELS = (*CHAIN, "stable-diffusion-3.5-large", "qwen3-embedding-8b", "experimental")

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
CONTEXT = JobContext("org/repo", "a" * 40)
FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "org/repo", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
        Fact("example:001", "example", "print(1)", (Evidence("README.md"),)),
    ),
)
MANIFEST = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
PACKET: dict[str, Any] = {
    "repository": "org/repo",
    "ecosystem": "python",
    "fact_dossier": [{"id": "identity:repository", "kind": "identity", "value": "org/repo"}],
    "inherited_units": [],
}


def _investigation() -> dict[str, Any]:
    statement = {"text": "It does things.", "fact_ids": ["identity:repository"]}
    capabilities = [
        {"title": f"Do {i}", "text": "One sentence.", "fact_ids": [fact_id]}
        for i, fact_id in enumerate(("identity:repository", "package:name", "example:001"))
    ]
    return {
        "product_summary": statement,
        "audience": statement,
        "problems_solved": [statement],
        "workflows": [],
        "capabilities": capabilities,
        "limitations": [],
        "uncertainties": [],
    }


def _completion(content: dict[str, Any], model: str) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": model,
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


class FakeGateway:
    """Answers each model as ``up`` says; a model not in ``up`` answers HTTP 500, as observed.

    Probes (one tiny ``ping`` request) and content calls are recorded apart, so a test can prove
    how many of each a run made and which model each one named.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch, up: set[str]) -> None:
        self.up = set(up)
        self.probes: list[str] = []
        self.content: list[str] = []
        self.listed: tuple[str, ...] = ALL_MODELS
        mock_gateway(monkeypatch, self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return model_listing(*((model, "org") for model in self.listed))
        body = json.loads(request.content)
        model = body["model"]
        # A probe is the one liveness token; every other request is a content call.
        if body["messages"][-1]["content"] == "ping":
            self.probes.append(model)
        else:
            self.content.append(model)
        if model not in self.up:
            return httpx.Response(500, json={"error": {"message": "upstream exhausted"}})
        return _completion(_investigation(), model=model)


def _run(
    tmp_path: Path, selection: ModelSelection | None, *, checks: Any = None, name: str = "calls"
) -> tuple[Any, Ledger, CallStore]:
    ledger = Ledger(tmp_path / f"{name}.jsonl")
    store = CallStore(tmp_path / name)
    result = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=store,
        context=replace(CONTEXT, models=selection),
        checks=checks,
    )
    return result, ledger, store


# --- the chain itself ------------------------------------------------------------------------


def test_the_chain_is_the_route_then_its_configured_fallbacks() -> None:
    assert chain_for(PRIMARY) == CHAIN
    assert FALLBACK_CHAINS[PRIMARY] == ("gpt-oss", "recommended", "Qwen2.5-VL-7B")
    # A route with no configured fallbacks has a chain of its own name alone: no silent fallback.
    assert chain_for("unlisted-model") == ("unlisted-model",)


def test_a_chain_that_repeats_a_model_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(FALLBACK_CHAINS, "looping", ("gpt-oss", "gpt-oss"))
    with pytest.raises(ConfigError, match="repeats a model"):
        chain_for("looping")


# --- chain selection at run start --------------------------------------------------------------


def test_a_downed_primary_is_replaced_by_the_first_fallback_that_answers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={"gpt-oss", "recommended", "Qwen2.5-VL-7B"})
    selection = select_models(CONFIG, [PRIMARY])
    decision = selection.decisions[PRIMARY]
    assert decision.model == "gpt-oss"
    assert decision.reason == "primary qwen3-next unavailable"
    # Each chain model is probed exactly once, in chain order - never once per job or per call.
    assert gateway.probes == list(CHAIN)
    assert gateway.content == []

    result, ledger, _ = _run(tmp_path, selection)
    assert gateway.content == ["gpt-oss"]
    assert result.model_served == "gpt-oss"
    record = ledger.records()[0]
    assert record.effective_model == "gpt-oss" and record.model_route == PRIMARY


def test_a_run_whose_primary_answers_names_the_primary_and_probes_each_model_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(CHAIN))
    selection = select_models(CONFIG, [PRIMARY])
    assert selection.decisions[PRIMARY].model == PRIMARY
    assert selection.decisions[PRIMARY].reason == "primary"
    assert gateway.probes == list(CHAIN)

    _, ledger, _ = _run(tmp_path, selection)
    assert gateway.content == [PRIMARY]
    assert ledger.records()[0].effective_model == PRIMARY


def test_an_exhausted_chain_fails_closed_with_a_typed_error_before_any_content_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up=set())
    with pytest.raises(ModelChainExhaustedError) as raised:
        select_models(CONFIG, [PRIMARY])
    assert isinstance(raised.value, GatewayError)
    message = str(raised.value)
    assert "no model in its chain answered" in message
    assert "qwen3-next HTTP 500" in message and "Qwen2.5-VL-7B HTTP 500" in message
    assert gateway.probes == list(CHAIN) and gateway.content == []


def test_a_fallback_the_recorded_catalog_does_not_list_is_never_probed_into_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(CHAIN))
    selection = select_models(CONFIG, [PRIMARY], listed=(PRIMARY, "recommended"))
    assert selection.decisions[PRIMARY].model == PRIMARY
    assert "gpt-oss" not in gateway.probes  # refused from the catalog, no request made
    unlisted = next(probe for probe in selection.probes if probe.model == "gpt-oss")
    assert unlisted == AvailabilityProbe("gpt-oss", False, "not in the recorded catalog")


# --- one decision per run; never a mid-run switch ----------------------------------------------


def test_a_mid_run_recovery_of_the_primary_does_not_switch_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={"gpt-oss", "recommended", "Qwen2.5-VL-7B"})
    selection = select_models(CONFIG, [PRIMARY])
    probes_at_start = len(gateway.probes)
    gateway.up.add(PRIMARY)  # the primary comes back while the run is in progress

    _run(tmp_path, selection)
    assert gateway.content == ["gpt-oss"]  # every call of the run, no switch to the primary
    assert len(gateway.probes) == probes_at_start  # no re-probe mid-run


def test_a_call_naming_any_other_model_is_refused_before_it_reaches_the_gateway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(CHAIN))
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "gpt-oss"})
    assert selection.model_for(PRIMARY) == "gpt-oss"
    attempts = _Attempts(
        MANIFEST, replace(CONTEXT, models=selection), Ledger(tmp_path / "x.jsonl"), "logical"
    )
    other = request_payload(MANIFEST, render_messages(MANIFEST, PACKET), model=PRIMARY)
    with pytest.raises(ConfigError, match="never switches models mid-run"):
        attempts.call(CONFIG, other)
    assert gateway.content == [] and attempts.count == 0


def test_a_route_outside_the_run_selection_is_refused_rather_than_defaulted() -> None:
    selection = ModelSelection(probes=())
    with pytest.raises(ConfigError, match="no model was selected for route"):
        selection.model_for(PRIMARY)


# --- the effective model is part of the request, the record, and the cache key -----------------


def test_the_request_hash_changes_with_the_effective_model_and_not_for_the_primary() -> None:
    primary_hash = request_hash(MANIFEST, PACKET)
    assert request_hash(MANIFEST, PACKET, model=PRIMARY) == primary_hash
    fallback_hash = request_hash(MANIFEST, PACKET, model="gpt-oss")
    assert fallback_hash != primary_hash
    assert request_hash(MANIFEST, PACKET, model="recommended") != fallback_hash
    payload = request_payload(MANIFEST, render_messages(MANIFEST, PACKET), model="gpt-oss")
    assert payload["model"] == "gpt-oss"


def test_the_call_store_never_reuses_an_output_produced_by_a_different_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(CHAIN))
    store = CallStore(tmp_path / "calls")
    ledger = Ledger(tmp_path / "calls.jsonl")
    primary = run_job(
        MANIFEST, PACKET, config=CONFIG, facts=FACTS, ledger=ledger, store=store, context=CONTEXT
    )
    assert primary.provider_calls == 1

    fallen_back = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "gpt-oss"})
    again = run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=store,
        context=replace(CONTEXT, models=fallen_back),
    )
    # A different key, so a real call under the other model - never the primary's stored output.
    assert again.request_sha256 != primary.request_sha256
    assert again.provider_calls == 1 and not again.cache_reused
    assert gateway.content == [PRIMARY, "gpt-oss"]


def test_a_fallback_output_that_fails_a_check_is_neither_stored_nor_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={"gpt-oss"})
    selection = select_models(CONFIG, [PRIMARY])

    def refuse(output: dict[str, Any]) -> list[str]:
        """The same quality gate every model answers to, whichever model produced the reply."""
        return ["quality gate: refused"]

    with pytest.raises(JobError, match="rejected twice"):
        _run(tmp_path, selection, checks=refuse)
    assert gateway.content == ["gpt-oss", "gpt-oss"]  # the one re-ask, still the same model
    store = CallStore(tmp_path / "calls")
    key = request_hash(MANIFEST, PACKET, model="gpt-oss")
    assert store.get(key) is None
    ledger = Ledger(tmp_path / "calls.jsonl")
    rejected = [r for r in ledger.records() if r.outcome == "response_invalid"]
    assert rejected and all(r.effective_model == "gpt-oss" for r in rejected)


# --- reproducibility: the recorded model is preferred while it answers --------------------------


def test_a_rerun_reuses_its_recorded_model_while_that_model_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up=set(CHAIN))
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "gpt-oss"})
    decision = selection.decisions[PRIMARY]
    assert decision.model == "gpt-oss" and decision.reason == "recorded model still available"
    assert selection.models_used() == {PRIMARY: "gpt-oss"}


def test_a_recorded_model_that_no_longer_answers_is_replaced_and_the_change_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up={PRIMARY, "recommended"})
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "gpt-oss"})
    decision = selection.decisions[PRIMARY]
    assert decision.model == PRIMARY
    assert decision.reason == "recorded model gpt-oss unavailable"
    assert decision.recorded == "gpt-oss"


def test_a_recorded_model_outside_the_chain_is_not_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeGateway(monkeypatch, up=set(CHAIN))
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "retired-model"})
    decision = selection.decisions[PRIMARY]
    assert decision.model == PRIMARY
    assert decision.reason == "recorded model retired-model is not in the chain"


# --- operator-facing output ---------------------------------------------------------------------


def test_the_description_names_every_chain_member_and_the_model_each_route_will_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up={"gpt-oss", "recommended", "Qwen2.5-VL-7B"})
    lines = describe(select_models(CONFIG, [PRIMARY]))
    assert lines[0] == (
        "chain qwen3-next: qwen3-next HTTP 500 (unavailable) -> gpt-oss HTTP 200 (available)"
        " -> recommended HTTP 200 (available) -> Qwen2.5-VL-7B HTTP 200 (available)"
    )
    assert lines[1] == "route qwen3-next: will use gpt-oss (primary qwen3-next unavailable)"


def test_preflight_decides_the_chain_and_records_it_in_the_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeGateway(monkeypatch, up={"gpt-oss", "recommended", "Qwen2.5-VL-7B"})
    result = run_gateway_preflight(CONFIG, REPO_ROOT / "prompts")
    assert result.selection is not None
    assert result.selection.models_used() == {PRIMARY: "gpt-oss"}
    write_catalog(result, tmp_path / "catalog.json")
    recorded = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert recorded["fallback"]["decisions"][0]["model"] == "gpt-oss"
    assert [probe["model"] for probe in recorded["fallback"]["probes"]] == list(CHAIN)


def test_preflight_refuses_a_route_whose_whole_chain_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up=set())
    with pytest.raises(ModelChainExhaustedError):
        run_gateway_preflight(CONFIG, REPO_ROOT / "prompts")
