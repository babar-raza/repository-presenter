"""Gateway configuration comes from the process environment and fails closed by owner item."""

from __future__ import annotations

import pytest

from repository_presenter.core.config import RESUME_PREDICATE, load_gateway_config
from repository_presenter.core.errors import ConfigError


def test_both_variables_yield_a_config_that_never_reprs_the_key() -> None:
    config = load_gateway_config(
        {
            "GPT_OSS_ENDPOINT": "https://gw.example/v1/",
            "GPT_OSS_API_KEY": "sk-secret-value-0123456789",
            "GPT_OSS_MODEL": " qwen3-next ",
        }
    )
    assert config.base_url == "https://gw.example/v1"
    assert config.host == "gw.example"
    assert config.api_key == "sk-secret-value-0123456789"
    assert config.model_override == "qwen3-next"
    assert config.timeout_seconds == 360.0
    assert "sk-secret" not in repr(config)
    assert "sk-secret" not in str(config)
    minimal = load_gateway_config(
        {"GPT_OSS_ENDPOINT": "http://localhost:8000", "GPT_OSS_API_KEY": "k"}
    )
    assert (minimal.base_url, minimal.model_override) == ("http://localhost:8000", None)


@pytest.mark.parametrize(
    ("environment", "missing"),
    [
        ({}, "GPT_OSS_ENDPOINT and GPT_OSS_API_KEY"),
        ({"GPT_OSS_ENDPOINT": "https://gw.example/v1"}, "GPT_OSS_API_KEY"),
        ({"GPT_OSS_ENDPOINT": "   ", "GPT_OSS_API_KEY": "k"}, "GPT_OSS_ENDPOINT"),
        (
            {"LLM_BASE_URL": "https://gw.example/v1", "LLM_API_KEY": "k"},
            "GPT_OSS_ENDPOINT and GPT_OSS_API_KEY",
        ),
    ],
)
def test_missing_variables_name_the_owner_item_and_its_resume_predicate(
    environment: dict[str, str], missing: str
) -> None:
    with pytest.raises(ConfigError) as info:
        load_gateway_config(environment)
    assert str(info.value) == (
        f"OWNER-02: {missing} not set in the process environment; resume when {RESUME_PREDICATE}"
    )
    assert info.value.exit_code == 2


@pytest.mark.parametrize("endpoint", ["gw.example/v1", "ftp://gw.example", "https://", "/v1"])
def test_the_endpoint_must_be_an_absolute_http_url_and_is_never_echoed(endpoint: str) -> None:
    with pytest.raises(ConfigError) as info:
        load_gateway_config({"GPT_OSS_ENDPOINT": endpoint, "GPT_OSS_API_KEY": "k"})
    assert str(info.value) == "GPT_OSS_ENDPOINT is not an absolute http(s) URL"
