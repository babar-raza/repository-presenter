"""Preflight records the live catalog and refuses an override the catalog does not contain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import ConfigError, GatewayError
from repository_presenter.core.llm.prompts import JOB_IDS, load_manifests
from repository_presenter.core.preflight import run_gateway_preflight, write_catalog
from support import REPO_ROOT, mock_gateway, model_listing

PROMPTS = REPO_ROOT / "prompts"


def _serve(monkeypatch: pytest.MonkeyPatch, *ids: str) -> None:
    mock_gateway(monkeypatch, lambda request: model_listing(*((i, "org") for i in ids)))


def test_preflight_records_the_catalog_and_routes_and_accepts_an_override_it_contains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve(monkeypatch, "qwen3-next", "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789", "qwen3-next")
    result = run_gateway_preflight(config, PROMPTS)
    assert result.catalog.ids == ("gpt-oss", "qwen3-next")
    assert result.model_override == "qwen3-next"
    assert tuple(sorted(result.prompts.manifests)) == tuple(sorted(JOB_IDS))

    path = tmp_path / "runs" / "preflight" / "catalog.json"
    digest = write_catalog(result, path)
    raw = path.read_bytes()
    payload = json.loads(raw)
    assert payload["models"] == [
        {"id": "gpt-oss", "owned_by": "org"},
        {"id": "qwen3-next", "owned_by": "org"},
    ]
    assert (payload["schema_version"], payload["model_override"]) == (1, "qwen3-next")
    assert payload["base_url"] == "https://gw.example/v1"
    assert payload["prompts"] == [
        {"prompt_id": job, "model_route": "qwen3-next", "sha256": digest_of}
        for job, digest_of in sorted(load_manifests(PROMPTS).hashes().items())
    ]
    assert b"sk-test" not in raw
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert len(digest) == 64
    assert write_catalog(result, path) == digest


def test_no_override_means_no_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "gpt-oss", "qwen3-next")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
    result = run_gateway_preflight(config, PROMPTS)
    assert (result.catalog.ids, result.model_override) == (("gpt-oss", "qwen3-next"), None)


def test_an_override_absent_from_the_catalog_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "qwen3-next", "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789", "missing-model")
    with pytest.raises(GatewayError) as info:
        run_gateway_preflight(config, PROMPTS)
    assert str(info.value) == (
        "GPT_OSS_MODEL='missing-model' is not in the live model catalog (gpt-oss, qwen3-next)"
    )


def test_a_route_the_catalog_no_longer_lists_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
    with pytest.raises(GatewayError, match="routes to 'qwen3-next', which the gateway catalog"):
        run_gateway_preflight(config, PROMPTS)


def test_manifests_are_checked_before_the_gateway_is_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
    with pytest.raises(ConfigError, match="no prompts/ directory"):
        run_gateway_preflight(config, tmp_path / "prompts")
