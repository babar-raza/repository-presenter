"""Gateway configuration comes from the process environment and fails closed by owner item."""

from __future__ import annotations

import pytest

from repository_presenter.core.config import (
    DEFAULT_TIMEOUT_SECONDS,
    RESUME_PREDICATE,
    load_gateway_config,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

# Measured 2026-09-06 from this session's own ledger records - the 783 successful provider calls
# in candidates/*/calls.jsonl and runs/transactions/*/*/calls.jsonl - not estimated (G4-W17
# arrival item 35). A least-squares fit gives
# latency_ms = 0.0898 * prompt_tokens + 18.67 * completion_tokens + 689.
MEASURED_MS_PER_COMPLETION_TOKEN = 18.67
MEASURED_MS_PER_PROMPT_TOKEN = 0.0898
MEASURED_CALL_OVERHEAD_MS = 689.0
# The longest call that succeeded: aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET's
# source_reconciliation, 67,468 prompt and 15,828 completion tokens.
LONGEST_SUCCESSFUL_CALL_SECONDS = 355.4
# The largest packet any job has been measured reading, across every job and repository.
LARGEST_MEASURED_PROMPT_TOKENS = 81_792


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
    assert config.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
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


def test_the_timeout_clears_the_longest_call_this_portfolio_has_measured() -> None:
    """G4-W17 arrival item 35. The old 360 s ceiling stood 4.6 s above the longest call that
    ever succeeded, and nine calls - every one ``source_reconciliation`` - died on it across
    three repositories on 2026-09-06. A ceiling that close to the observed maximum is not a
    ceiling, it is a coin toss, so it carries the same headroom rule ``SYMBOL_CAP`` and
    ``UNIT_CAP`` already use (RESEARCH_AND_GUIDELINES.md section 27.10 follow-up 3)."""
    assert DEFAULT_TIMEOUT_SECONDS > LONGEST_SUCCESSFUL_CALL_SECONDS * 2


def test_the_timeout_admits_every_output_budget_the_prompt_manifests_declare() -> None:
    """The defect the old ceiling actually hid: 360 s could not deliver
    ``source_reconciliation``'s own declared 32,000-token output budget, which needs 597 s of
    generation at the measured rate - the job was truncated by the clock, not by its manifest.
    Raising any manifest's ``max_output_tokens`` past what the timeout can deliver now fails
    here in milliseconds instead of after a quarter of an hour of production calls."""
    manifests = load_manifests(REPO_ROOT / "prompts").manifests
    assert manifests, "the prompt manifests are the source of every declared output budget"
    for name in sorted(manifests):
        budget = manifests[name].manifest.sampling.max_output_tokens
        projected_ms = (
            MEASURED_MS_PER_PROMPT_TOKEN * LARGEST_MEASURED_PROMPT_TOKENS
            + MEASURED_MS_PER_COMPLETION_TOKEN * budget
            + MEASURED_CALL_OVERHEAD_MS
        )
        assert projected_ms / 1000 < DEFAULT_TIMEOUT_SECONDS, (
            f"{name} declares max_output_tokens={budget}, which needs "
            f"{projected_ms / 1000:.0f}s at the measured rate against the largest packet "
            f"measured; DEFAULT_TIMEOUT_SECONDS is {DEFAULT_TIMEOUT_SECONDS}"
        )
