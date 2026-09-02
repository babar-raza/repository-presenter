"""Shared fixtures and the offline isolation every test runs under."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.core.llm import transport
from support import REPO_ROOT, write_cursor


@pytest.fixture(autouse=True)
def isolate_ambient_credentials_and_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never inherit a developer's or runner's credentials or git configuration."""
    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GPT_OSS_ENDPOINT",
        "GPT_OSS_API_KEY",
        "GPT_OSS_MODEL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ):
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
