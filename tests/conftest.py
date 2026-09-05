"""Shared fixtures and the offline isolation every test runs under."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.core.llm import transport
from support import REPO_ROOT, write_cursor

AMBIENT_CREDENTIALS = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GPT_OSS_ENDPOINT",
    "GPT_OSS_API_KEY",
    "GPT_OSS_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
)


@pytest.fixture(scope="session", autouse=True)
def isolate_ambient_credentials_for_the_whole_session() -> Iterator[None]:
    """No fixture at any scope sees a real credential, so no test can reach a live gateway.

    A session-scoped fixture is built before every function-scoped one, so the per-test cleaning
    below came too late for a fixture like ``sealed_canary``: with GPT_OSS_ENDPOINT and
    GPT_OSS_API_KEY in the process environment the suite could compose against the real gateway
    at fixture setup, and a rejected reply failed a different test on each run - six runs of one
    tree gave 503 passed, 501+2 errors, 500+3 errors+1 failed, 500+2 errors, while the same tree
    with both variables unset passed 503 of 503 (lane B, docs/RESEARCH_LANE_B.md, 2026-09-06).
    Hosted CI sets neither, which is why it stayed green throughout.
    """
    with pytest.MonkeyPatch.context() as patch:
        for name in AMBIENT_CREDENTIALS:
            patch.delenv(name, raising=False)
        yield


@pytest.fixture(autouse=True)
def isolate_ambient_credentials_and_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never inherit a developer's or runner's credentials or git configuration."""
    for name in AMBIENT_CREDENTIALS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("GCM_INTERACTIVE", "never")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)


@pytest.fixture(autouse=True)
def no_package_registry_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test reaches the real package registry; a test that needs it injects its own fetch."""

    def refuse(url: str, transport: object = None) -> object:
        raise RuntimeError(f"network is disabled in tests: {url}")

    monkeypatch.setattr(python_registry, "fetch_project_json", refuse)
    monkeypatch.setattr(links, "fetch_status", refuse)

    def refuse_client(config: object) -> object:
        raise RuntimeError("the LLM gateway is unreachable in tests; use support.mock_gateway")

    monkeypatch.setattr(transport, "build_client", refuse_client)


@pytest.fixture
def repo_root() -> Path:
    """This repository's root, whose real cursor the CLI must report."""
    return REPO_ROOT


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A synthetic project root with a default cursor and no bundles."""
    write_cursor(tmp_path)
    return tmp_path
