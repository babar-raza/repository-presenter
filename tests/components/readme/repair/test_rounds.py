"""A failed second-reader job must never be mistaken for a completed, corroborating one."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from repository_presenter.components.readme.repair.rounds import _second_opinion
from repository_presenter.core.errors import JobError
from repository_presenter.core.llm.jobs import JobResult
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT

MANIFESTS = load_manifests(REPO_ROOT / "prompts")
LOADED = MANIFESTS["independent_review"]
PACKET: dict[str, Any] = {}
COMMON: dict[str, Any] = {}


def test_a_failed_second_reader_job_returns_none_not_an_empty_dict() -> None:
    """TB-04, external review D4: review_document reads `second={}` as a *completed* reading
    that corroborated nothing, silently demoting a real blocking finding to advisory and
    flipping REJECT_PRESENTATION to ACCEPT. `_second_opinion` must return None on JobError -
    the caller (rounds.py's run_round) then leaves the first reader's review untouched, exactly
    as if no second reading had ever been attempted."""
    with patch(
        "repository_presenter.components.readme.repair.rounds.run_job",
        side_effect=JobError("gateway unavailable"),
    ):
        assert _second_opinion(LOADED, PACKET, None, COMMON) is None


def test_a_successful_second_reader_job_returns_its_output() -> None:
    result = JobResult(
        job="independent_review",
        output={"findings": [], "verdict": "ACCEPT", "preserve": []},
        request_sha256="a" * 64,
        attempts=1,
        provider_calls=1,
        cache_reused=False,
        model_served="qwen3-next",
        total_tokens=100,
    )
    with patch("repository_presenter.components.readme.repair.rounds.run_job", return_value=result):
        assert _second_opinion(LOADED, PACKET, None, COMMON) == result.output
