"""Every sealed candidate still renders to the bytes it was sealed with.

A candidate's README is a pure function of its facts, plan, units and dispositions, so any change
to the renderer can be held to the documents already on disk without a clone, a provider call, or
a toolchain. This is the regression control a refactor of shared composition code answers to:
G4-W10 moved every ecosystem-specific spelling into `EcosystemSpec`, and the proof that it moved
nothing else is that the sealed bytes did not move (`RESEARCH_AND_GUIDELINES.md` §29.6 E4).

It is deliberately stronger than re-running the canary: it covers every sealed candidate, and it
cannot be satisfied by a stored reply, because nothing here calls a provider.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT

CANDIDATES = REPO_ROOT / "candidates"
REGISTRY = REPO_ROOT / "data" / "registry.json"


def sealed_bundles() -> list[Path]:
    """Every bundle directory a CURRENT file points at."""
    bundles = []
    for current in sorted(CANDIDATES.glob("*/CURRENT")):
        revision = current.read_text("utf-8").strip()
        bundle = current.parent / revision
        if (bundle / "README.md").is_file():
            bundles.append(bundle)
    return bundles


def load_facts(path: Path) -> FactsDocument:
    """facts.json as the document the renderer takes; the seal wrote it, so it round-trips."""
    payload = json.loads(path.read_text("utf-8"))
    facts = []
    for row in payload["facts"]:
        row = dict(row)
        row["evidence"] = tuple(Evidence(**entry) for entry in row.get("evidence", ()))
        row["attributes"] = dict(row.get("attributes") or {})
        facts.append(Fact(**row))
    return FactsDocument(
        repository=payload["repository"],
        source_revision=payload["source_revision"],
        facts=tuple(facts),
    )


def entry_for(repository: str) -> RegistryEntry:
    entries = json.loads(REGISTRY.read_text("utf-8"))["entries"]
    row = next(item for item in entries if item["repository"] == repository)
    return RegistryEntry.model_validate(row)


def read(bundle: Path, name: str) -> dict[str, Any]:
    loaded = json.loads((bundle / name).read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_there_is_at_least_one_sealed_bundle_to_hold_the_renderer_to() -> None:
    assert sealed_bundles(), "no sealed candidate on disk; the control would pass vacuously"


@pytest.mark.parametrize("bundle", sealed_bundles(), ids=lambda b: b.parent.name)
def test_a_sealed_candidate_renders_to_its_own_bytes(bundle: Path) -> None:
    facts = load_facts(bundle / "facts.json")
    rendered = render_readme(
        entry_for(facts.repository),
        facts,
        read(bundle, "plan.json"),
        read(bundle, "content_units.json"),
        read(bundle, "dispositions.json"),
    )
    stored = (bundle / "README.md").read_text("utf-8")
    assert rendered == stored, f"{bundle.parent.name} no longer renders the bytes it sealed with"
