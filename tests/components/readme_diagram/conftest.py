"""The live At a Glance diagrams the diagram package is measured against.

``fixtures/live/*.mmd`` are the Mermaid fences of the 32 live upstream READMEs that carried one
(35 were surveyed on 2026-10-11; three have no Mermaid diagram), each exactly as the maintainers'
repository held it; ``index.json`` names the repository, revision and README line of each. They are
test inputs, never expected output: every property asserted here is stated about the diagram, not
copied from a rendering.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from repository_presenter.components.readme_diagram import render_check

LIVE_DIR = Path(__file__).parent / "fixtures" / "live"


@pytest.fixture(scope="session")
def live() -> dict[str, str]:
    """Fixture name to the live diagram's source, in name order."""
    return {path.stem: path.read_text(encoding="utf-8") for path in sorted(LIVE_DIR.glob("*.mmd"))}


@pytest.fixture(scope="session")
def live_index() -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = json.loads(
        (LIVE_DIR / "index.json").read_text(encoding="utf-8")
    )
    return index


@pytest.fixture(scope="session")
def renderer() -> render_check.Renderer:
    """The installed browser renderer, or a skip: the tests that draw need Node, Chrome or Edge and
    the packages of ``render/package.json`` (``RP_MERMAID_TOOLS``), none of which CI is assumed to
    have. Nothing they do reaches the network."""
    found = render_check.find_renderer(os.environ)
    if found is None:
        pytest.skip("no Mermaid renderer installed (set RP_MERMAID_TOOLS; see render_check.py)")
    return found
