"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from support import REPO_ROOT, write_cursor


@pytest.fixture
def repo_root() -> Path:
    """This repository's root, whose real cursor the CLI must report."""
    return REPO_ROOT


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A synthetic project root with a default cursor and no bundles."""
    write_cursor(tmp_path)
    return tmp_path
