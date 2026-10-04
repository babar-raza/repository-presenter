"""Model availability at run start: a route's own model must prove it can do the work, or stop.

No substitute model is ever selected: a sealed result must come from the route's own model. Every
probe and every content call goes through the mock gateway (tests/support.py), so these tests
exercise the real SDK client, retry-free transport, and run_job path without the network. A probe
is the same strict json_schema shape a content call sends, and the route's model is available only
after PROBE_CONSECUTIVE_PASSES probes in a row pass: HTTP 200 with content that satisfies the probe
schema. Each test's gateway script says what each probe answers, so the negative controls
(plain-text 200, a schema-violating 200, one pass then a failure) are exercised directly.
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
from repository_presenter.core.llm import fallback
from repository_presenter.core.llm.fallback import (
    FALLBACK_CHAINS,
    PROBE_CONSECUTIVE_PASSES,
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
# Models that answer in the catalog but are never a substitute for the route's own model.
OTHERS = ("gpt-oss", "recommended", "Qwen2.5-VL-7B")
# The catalog as observed: two chat models that answer, one that answers HTTP 500, and two that
# are not chat routes at all (an image and an embedding model).
ALL_MODELS = (PRIMARY, *OTHERS, "stable-diffusion-3.5-large", "qwen3-embedding-8b", "experimental")

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


def _reply(content: str, model: str) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    return httpx.Response(200, json=body)


def _completion(content: dict[str, Any], model: str) -> httpx.Response:
    return _reply(json.dumps(content), model)


def _each(models: tuple[str, ...] | list[str], times: int = PROBE_CONSECUTIVE_PASSES) -> list[str]:
    """What a run's probe log holds when every model is probed ``times`` in a row, in order."""
    return [model for model in models for _ in range(times)]


# What a scripted probe can answer. "ok" is the only reply that satisfies the probe schema.
PROBE_OK = "ok"
PROBE_500 = "500"
PROBE_PLAIN_TEXT = "text"  # HTTP 200, the plain-text reply a chat-only check would accept
PROBE_WRONG_VALUE = "wrong"  # HTTP 200, valid JSON, but the enum rejects its value
PROBE_EXTRA_FIELD = "extra"  # HTTP 200, valid JSON, but additionalProperties is false
_PROBE_REPLIES = {
    PROBE_OK: json.dumps({"status": "ok"}),
    PROBE_PLAIN_TEXT: "I am here and ready to help.",
    PROBE_WRONG_VALUE: json.dumps({"status": "nope"}),
    PROBE_EXTRA_FIELD: json.dumps({"status": "ok", "extra": 1}),
}


class FakeGateway:
    """Answers each model as ``up`` says; a model not in ``up`` answers HTTP 500, as observed.

    ``probe_script`` overrides what a model's probes answer, one entry per probe in order, and
    once the script is spent the model answers by ``up`` again. Probes (the ``ping`` liveness
    token) and content calls are recorded apart, so a test can prove how many of each a run made,
    which model each named, and the exact request shape each probe sent.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        up: set[str],
        probe_script: dict[str, list[str]] | None = None,
    ) -> None:
        self.up = set(up)
        self.script = {model: list(replies) for model, replies in (probe_script or {}).items()}
        self.probes: list[str] = []
        self.probe_bodies: list[dict[str, Any]] = []
        self.content: list[str] = []
        self.content_bodies: list[dict[str, Any]] = []
        self.listed: tuple[str, ...] = ALL_MODELS
        # A content call to a model not in ``up``. 500 is transient and retried with backoff, so a
        # test that needs no waiting sets a non-transient status such as 400.
        self.content_down_status = 500
        mock_gateway(monkeypatch, self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return model_listing(*((model, "org") for model in self.listed))
        body = json.loads(request.content)
        model = body["model"]
        # A probe is the one liveness token; every other request is a content call.
        if body["messages"][-1]["content"] == "ping":
            self.probes.append(model)
            self.probe_bodies.append(body)
            return self._probe_reply(model)
        self.content.append(model)
        self.content_bodies.append(body)
        if model not in self.up:
            return httpx.Response(self.content_down_status, json={"error": {"message": "down"}})
        return _completion(_investigation(), model=model)

    def _probe_reply(self, model: str) -> httpx.Response:
        scripted = self.script.get(model)
        outcome = scripted.pop(0) if scripted else (PROBE_OK if model in self.up else PROBE_500)
        if outcome == PROBE_500:
            return httpx.Response(500, json={"error": {"message": "upstream exhausted"}})
        return _reply(_PROBE_REPLIES[outcome], model)


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


# --- the route's own model is the only model -----------------------------------------------------


def test_the_chain_for_a_route_is_the_route_alone() -> None:
    # No substitute is configured: the table is empty, so every route's chain is itself.
    assert FALLBACK_CHAINS == {}
    assert chain_for(PRIMARY) == (PRIMARY,)
    assert chain_for("unlisted-model") == ("unlisted-model",)


def test_a_configured_substitute_that_repeats_a_model_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(FALLBACK_CHAINS, "looping", ("gpt-oss", "gpt-oss"))
    with pytest.raises(ConfigError, match="repeats a model"):
        chain_for("looping")


def test_a_route_whose_model_passes_is_selected_probed_in_a_row_and_used_for_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY, *OTHERS})
    selection = select_models(CONFIG, [PRIMARY])
    assert selection.decisions[PRIMARY].model == PRIMARY
    assert selection.decisions[PRIMARY].reason == "primary"
    assert gateway.probes == _each((PRIMARY,))
    assert gateway.content == []

    result, ledger, _ = _run(tmp_path, selection)
    assert gateway.content == [PRIMARY]
    assert result.model_served == PRIMARY
    assert ledger.records()[0].effective_model == PRIMARY


def test_a_route_whose_model_is_down_fails_closed_and_no_other_model_is_probed_or_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Every other model answers, and none of them is used: the route's own model must.
    gateway = FakeGateway(monkeypatch, up=set(OTHERS))
    with pytest.raises(ModelChainExhaustedError) as raised:
        select_models(CONFIG, [PRIMARY])
    assert isinstance(raised.value, GatewayError)
    assert "qwen3-next HTTP 500" in str(raised.value)
    assert gateway.probes == [PRIMARY]
    assert gateway.content == []


def test_a_route_model_the_recorded_catalog_does_not_list_fails_closed_without_a_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(ALL_MODELS))
    with pytest.raises(ModelChainExhaustedError, match="not in the recorded catalog"):
        select_models(CONFIG, [PRIMARY], listed=OTHERS)
    assert PRIMARY not in gateway.probes


def test_a_route_model_that_fails_mid_run_is_not_replaced_and_no_probe_is_repeated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY, *OTHERS})
    selection = select_models(CONFIG, [PRIMARY])
    probes_at_start = len(gateway.probes)
    gateway.up.discard(PRIMARY)  # the chosen model goes down while the run is in progress
    gateway.content_down_status = 400  # refused, not transient: no backoff, no retry
    with pytest.raises(JobError, match="HTTP 400"):
        _run(tmp_path, selection)
    # Every call named the route's own model; no call fell through to another, nothing re-probed.
    assert gateway.content == [PRIMARY]
    assert len(gateway.probes) == probes_at_start


def test_a_call_naming_any_other_model_is_refused_before_it_reaches_the_gateway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY, *OTHERS})
    selection = select_models(CONFIG, [PRIMARY])
    attempts = _Attempts(
        MANIFEST, replace(CONTEXT, models=selection), Ledger(tmp_path / "x.jsonl"), "logical"
    )
    other = request_payload(MANIFEST, render_messages(MANIFEST, PACKET), model=OTHERS[0])
    with pytest.raises(ConfigError, match="never switches models mid-run"):
        attempts.call(CONFIG, other)
    assert gateway.content == [] and attempts.count == 0


def test_a_route_outside_the_run_selection_is_refused_rather_than_defaulted() -> None:
    selection = ModelSelection(probes=())
    with pytest.raises(ConfigError, match="no model was selected for route"):
        selection.model_for(PRIMARY)


# --- the effective model is part of the request, the record, and the cache key -----------------


def test_the_request_hash_changes_with_the_model_named_and_not_for_the_route() -> None:
    primary_hash = request_hash(MANIFEST, PACKET)
    assert request_hash(MANIFEST, PACKET, model=PRIMARY) == primary_hash
    assert request_hash(MANIFEST, PACKET, model="other-model") != primary_hash
    payload = request_payload(MANIFEST, render_messages(MANIFEST, PACKET), model="other-model")
    assert payload["model"] == "other-model"


def test_the_route_payload_is_unchanged_and_names_the_route() -> None:
    messages = render_messages(MANIFEST, PACKET)
    sampling = MANIFEST.manifest.sampling
    assert sampling.max_output_tokens == 3000
    expected = {
        "model": PRIMARY,
        "messages": messages,
        "temperature": sampling.temperature,
        "max_tokens": sampling.max_output_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": MANIFEST.manifest.prompt_id,
                "schema": MANIFEST.manifest.output.schema_,
                "strict": True,
            },
        },
        "seed": sampling.seed,
    }
    assert json.dumps(request_payload(MANIFEST, messages)) == json.dumps(expected)
    assert json.dumps(request_payload(MANIFEST, messages, model=PRIMARY)) == json.dumps(expected)


def test_a_route_run_sends_and_records_the_manifest_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY})
    _, ledger, _ = _run(tmp_path, select_models(CONFIG, [PRIMARY]))
    assert gateway.content_bodies[0]["max_tokens"] == 3000
    assert ledger.records()[0].max_tokens == 3000
    assert ledger.records()[0].effective_model == PRIMARY


def test_a_route_output_that_fails_a_check_is_neither_stored_nor_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY})
    selection = select_models(CONFIG, [PRIMARY])

    def refuse(output: dict[str, Any]) -> list[str]:
        """The same quality gate every call answers to, whichever model produced the reply."""
        return ["quality gate: refused"]

    with pytest.raises(JobError, match="rejected twice"):
        _run(tmp_path, selection, checks=refuse)
    assert gateway.content == [PRIMARY, PRIMARY]  # the one re-ask, still the same model
    store = CallStore(tmp_path / "calls")
    assert store.get(request_hash(MANIFEST, PACKET, model=PRIMARY)) is None
    ledger = Ledger(tmp_path / "calls.jsonl")
    rejected = [r for r in ledger.records() if r.outcome == "response_invalid"]
    assert rejected and all(r.effective_model == PRIMARY for r in rejected)


# --- reproducibility: a recorded model is honoured only when it is the route's own ---------------


def test_a_rerun_reuses_its_recorded_model_while_that_model_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up={PRIMARY})
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: PRIMARY})
    decision = selection.decisions[PRIMARY]
    assert decision.model == PRIMARY and decision.reason == "recorded model still available"
    assert selection.models_used() == {PRIMARY: PRIMARY}


def test_a_recorded_route_model_that_no_longer_answers_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up=set(OTHERS))
    with pytest.raises(ModelChainExhaustedError, match="qwen3-next HTTP 500"):
        select_models(CONFIG, [PRIMARY], recorded={PRIMARY: PRIMARY})
    assert gateway.probes == [PRIMARY] and gateway.content == []


def test_a_recorded_substitute_from_an_earlier_bundle_is_never_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY, *OTHERS})
    selection = select_models(CONFIG, [PRIMARY], recorded={PRIMARY: "gpt-oss"})
    decision = selection.decisions[PRIMARY]
    assert decision.model == PRIMARY
    assert decision.reason == "recorded model gpt-oss is not in the chain"
    assert "gpt-oss" not in gateway.probes


# --- operator-facing output ---------------------------------------------------------------------


def test_the_description_names_the_route_and_its_probe_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up={PRIMARY})
    lines = describe(select_models(CONFIG, [PRIMARY]))
    assert lines[0] == (
        "chain qwen3-next: qwen3-next HTTP 200, schema-valid, 2 of 2 consecutive passes (available)"
    )
    assert lines[1] == "route qwen3-next: will use qwen3-next (primary)"


def test_preflight_records_the_route_decision_in_the_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeGateway(monkeypatch, up={PRIMARY, *OTHERS})
    result = run_gateway_preflight(CONFIG, REPO_ROOT / "prompts")
    assert result.selection is not None
    assert result.selection.models_used() == {PRIMARY: PRIMARY}
    write_catalog(result, tmp_path / "catalog.json")
    recorded = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert recorded["fallback"]["decisions"][0]["model"] == PRIMARY
    assert [probe["model"] for probe in recorded["fallback"]["probes"]] == [PRIMARY]


def test_preflight_refuses_a_route_whose_own_model_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up=set(OTHERS))
    with pytest.raises(ModelChainExhaustedError):
        run_gateway_preflight(CONFIG, REPO_ROOT / "prompts")


# --- availability: a probe must answer the way a content call must -------------------------------


@pytest.mark.parametrize("reply", [PROBE_PLAIN_TEXT, PROBE_WRONG_VALUE, PROBE_EXTRA_FIELD])
def test_a_plain_200_probe_whose_content_breaks_the_schema_is_rejected(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    # The route's model answers HTTP 200 to its probe, but never with schema-valid content.
    gateway = FakeGateway(monkeypatch, up={PRIMARY, *OTHERS}, probe_script={PRIMARY: [reply]})
    with pytest.raises(ModelChainExhaustedError) as raised:
        select_models(CONFIG, [PRIMARY])
    assert "qwen3-next HTTP 200, content not schema-valid" in str(raised.value)
    assert gateway.probes == [PRIMARY]  # rejected at once; no later pass can rescue it
    assert gateway.content == []


def test_two_consecutive_passes_select_the_route_model(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY})
    selection = select_models(CONFIG, [PRIMARY])
    assert selection.decisions[PRIMARY].model == PRIMARY
    assert gateway.probes == [PRIMARY, PRIMARY]
    assert selection.probes[0] == AvailabilityProbe(
        PRIMARY, True, "HTTP 200, schema-valid, 2 of 2 consecutive passes"
    )


def test_a_probe_sends_the_strict_json_schema_shape_a_content_call_sends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(monkeypatch, up={PRIMARY})
    select_models(CONFIG, [PRIMARY])
    probe_body = gateway.probe_bodies[0]
    content_body = request_payload(MANIFEST, render_messages(MANIFEST, PACKET))
    assert set(probe_body) == {"model", "messages", "max_tokens", "temperature", "response_format"}
    assert set(probe_body["response_format"]) == set(content_body["response_format"])
    json_schema = probe_body["response_format"]["json_schema"]
    assert set(json_schema) == set(content_body["response_format"]["json_schema"])
    assert json_schema["strict"] is True
    assert json_schema["schema"] == {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["ok"]}},
        "required": ["status"],
        "additionalProperties": False,
    }


def test_one_pass_then_a_failure_fails_closed_and_the_model_is_not_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(
        monkeypatch, up={PRIMARY, *OTHERS}, probe_script={PRIMARY: [PROBE_OK, PROBE_500]}
    )
    with pytest.raises(ModelChainExhaustedError) as raised:
        select_models(CONFIG, [PRIMARY])
    assert "qwen3-next HTTP 500 after 1 of 2 consecutive passes" in str(raised.value)
    assert gateway.probes == [PRIMARY, PRIMARY]
    assert gateway.content == []


def test_a_pass_a_failure_then_a_pass_is_not_two_consecutive_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Were the third probe counted, the model would have passed "twice" in total; it must not.
    gateway = FakeGateway(
        monkeypatch, up={PRIMARY}, probe_script={PRIMARY: [PROBE_OK, PROBE_500, PROBE_OK]}
    )
    with pytest.raises(ModelChainExhaustedError):
        select_models(CONFIG, [PRIMARY])
    assert gateway.probes == [PRIMARY, PRIMARY]


def test_a_failed_probe_is_never_retried_so_a_later_pass_cannot_hide_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(
        monkeypatch, up={PRIMARY}, probe_script={PRIMARY: [PROBE_500, PROBE_OK, PROBE_OK]}
    )
    with pytest.raises(ModelChainExhaustedError):
        select_models(CONFIG, [PRIMARY])
    assert gateway.probes == [PRIMARY]


def test_the_route_failing_raises_the_typed_error_naming_it_and_its_probe_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = FakeGateway(
        monkeypatch,
        up=set(OTHERS),
        probe_script={PRIMARY: [PROBE_OK, PROBE_PLAIN_TEXT]},
    )
    with pytest.raises(ModelChainExhaustedError) as raised:
        select_models(CONFIG, [PRIMARY])
    assert isinstance(raised.value, GatewayError)
    message = str(raised.value)
    assert (
        "qwen3-next HTTP 200, content not schema-valid after 1 of 2 consecutive passes" in message
    )
    assert "no substitute model is used" in message
    assert gateway.probes == [PRIMARY, PRIMARY] and gateway.content == []


def test_the_consecutive_pass_requirement_is_one_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    assert PROBE_CONSECUTIVE_PASSES == 2
    gateway = FakeGateway(monkeypatch, up={PRIMARY})
    monkeypatch.setattr(fallback, "PROBE_CONSECUTIVE_PASSES", 3)
    select_models(CONFIG, [PRIMARY])
    assert gateway.probes == _each((PRIMARY,), 3)


def test_a_consecutive_pass_requirement_below_one_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeGateway(monkeypatch, up={PRIMARY})
    monkeypatch.setattr(fallback, "PROBE_CONSECUTIVE_PASSES", 0)
    with pytest.raises(ConfigError, match="at least 1"):
        select_models(CONFIG, [PRIMARY])
