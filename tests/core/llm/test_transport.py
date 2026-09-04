"""The transport builds one SDK client per config and reports failures by status only."""

from __future__ import annotations

import json

import httpx
import pytest

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import GatewayError
from repository_presenter.core.llm import transport
from repository_presenter.core.llm.transport import (
    ModelEntry,
    SeedProbe,
    list_models,
    probe_seed,
)
from support import mock_gateway, model_listing

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")


def test_models_are_listed_in_id_order_and_the_key_travels_only_as_a_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url), request.headers.get("authorization")))
        return model_listing(("qwen3-next", "org"), ("gpt-oss", "org"), ("recommended", "alias"))

    mock_gateway(monkeypatch, handler)
    catalog = list_models(CONFIG)
    assert seen == [("GET", "https://gw.example/v1/models", f"Bearer {CONFIG.api_key}")]
    assert catalog.base_url == "https://gw.example/v1"
    assert catalog.models == (
        ModelEntry("gpt-oss", "org"),
        ModelEntry("qwen3-next", "org"),
        ModelEntry("recommended", "alias"),
    )
    assert catalog.ids == ("gpt-oss", "qwen3-next", "recommended")


def test_a_refusal_reports_only_the_status_never_the_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"bad key {CONFIG.api_key}"}})

    mock_gateway(monkeypatch, handler)
    with pytest.raises(GatewayError) as info:
        list_models(CONFIG)
    assert str(info.value) == "GET https://gw.example/v1/models answered HTTP 401"
    assert info.value.exit_code == 1


def test_an_unreachable_gateway_reports_the_failure_class(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    mock_gateway(monkeypatch, handler)
    with pytest.raises(GatewayError, match=r"^gateway gw.example unreachable: APIConnectionError$"):
        list_models(CONFIG)


def test_an_empty_catalog_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_gateway(monkeypatch, lambda request: model_listing())
    with pytest.raises(GatewayError, match="listed no models"):
        list_models(CONFIG)


def test_tests_never_reach_a_real_gateway() -> None:
    with pytest.raises(RuntimeError, match="unreachable in tests"):
        transport.build_client(CONFIG)


def _completion(content: str) -> dict[str, object]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "qwen3-next",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def test_the_seed_probe_compares_two_identical_bounded_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # RESEARCH_AND_GUIDELINES.md section 27.10 follow-up 3 defines honoured: the same bounded
    # completion twice with the same seed, compared byte for byte. Two calls, one answer.
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=_completion("same"))

    mock_gateway(monkeypatch, handler)
    assert probe_seed(CONFIG, "qwen3-next") == SeedProbe("qwen3-next", True, True, "honoured")
    assert len(seen) == 2, "two calls, and only two"
    assert seen[0] == seen[1], "the two requests must be identical for the answer to mean anything"
    assert seen[0]["seed"] == 1 and seen[0]["temperature"] == 0


def test_a_model_that_answers_differently_is_accepted_but_not_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replies = iter(("first", "second"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion(next(replies)))

    mock_gateway(monkeypatch, handler)
    assert probe_seed(CONFIG, "qwen3-next") == SeedProbe(
        "qwen3-next", True, False, "accepted, non-deterministic"
    )


def test_a_gateway_that_refuses_seed_is_recorded_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A refusal settles the question; it is a finding, not a failure, so preflight still records
    # the catalog and the loop learns the answer.
    mock_gateway(monkeypatch, lambda request: httpx.Response(400, json={"error": "no seed"}))
    assert probe_seed(CONFIG, "qwen3-next") == SeedProbe("qwen3-next", False, None, "HTTP 400")
