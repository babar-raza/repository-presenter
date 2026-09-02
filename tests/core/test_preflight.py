"""Preflight records the live catalog and refuses an override the catalog does not contain."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import GatewayError
from repository_presenter.core.preflight import run_gateway_preflight, write_catalog
from support import mock_gateway, model_listing


def _serve(monkeypatch: pytest.MonkeyPatch, *ids: str) -> None:
    mock_gateway(monkeypatch, lambda request: model_listing(*((i, "org") for i in ids)))


def test_preflight_records_the_catalog_and_accepts_an_override_it_contains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve(monkeypatch, "qwen3-next", "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789", "qwen3-next")
    result = run_gateway_preflight(config)
    assert result.catalog.ids == ("gpt-oss", "qwen3-next")
    assert result.model_override == "qwen3-next"

    path = tmp_path / "runs" / "preflight" / "catalog.json"
    digest = write_catalog(result, path)
    raw = path.read_bytes()
    assert json.loads(raw) == {
        "schema_version": 1,
        "base_url": "https://gw.example/v1",
        "models": [{"id": "gpt-oss", "owned_by": "org"}, {"id": "qwen3-next", "owned_by": "org"}],
        "model_override": "qwen3-next",
    }
    assert b"sk-test" not in raw
    assert raw.endswith(b"}\n") and b"\r\n" not in raw
    assert len(digest) == 64
    assert write_catalog(result, path) == digest


def test_no_override_means_no_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
    result = run_gateway_preflight(config)
    assert (result.catalog.ids, result.model_override) == (("gpt-oss",), None)


def test_an_override_absent_from_the_catalog_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, "qwen3-next", "gpt-oss")
    config = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789", "missing-model")
    with pytest.raises(GatewayError) as info:
        run_gateway_preflight(config)
    assert str(info.value) == (
        "GPT_OSS_MODEL='missing-model' is not in the live model catalog (gpt-oss, qwen3-next)"
    )
