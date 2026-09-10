"""Whether a sealed candidate's README still matches what the code running right now would render
for it, promoted from `tests/test_sealed_bytes.py`'s own render-and-compare logic (PHASE0/PA-03).

Lives here, not in `core/candidates.py` where the taskcard's own one-line text names it: `core/`
may not import an extractor or a composition module (`docs/REPOSITORY_LAYOUT.md` section 2.1,
`core/ecosystems.py`'s own docstring - a one-directional dependency rule, not mechanically
enforced by a test today but real and already respected by every other `core/` module). This file
sits at the same layer `seal.py` and `evaluation.py` already do - above `core/candidates.py`,
below `composition/renderer.py` - importing both without inverting that boundary, exactly the way
`seal.py` already imports `RENDERER_VERSION` from the renderer it does not itself live in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems
from repository_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CANDIDATES_DIRNAME,
    COUNTED_STATES,
    CURRENT_FILENAME,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.loader import find_entry, load_registry

REGISTRY_RELATIVE_PATH = Path("data") / "registry.json"


def _load_facts(path: Path) -> FactsDocument:
    """facts.json as the document the renderer takes; the seal wrote it, so it round-trips."""
    payload = json.loads(path.read_text(encoding="utf-8"))
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


def _read(bundle: Path, name: str) -> dict[str, Any]:
    loaded = json.loads((bundle / name).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{bundle / name} is not a JSON object")
    return loaded


def reproducible_candidates(root: Path) -> int:
    """How many `CURRENT`, counted-state candidates render byte-identical to their sealed
    `README.md` under the code running right now.

    A pure read: renders in memory, compares bytes, writes nothing. A bundle this cannot render
    at all (a missing artifact, an unlisted repository, a malformed document) does not count as
    reproducible - it is silently excluded here, not an error; `verify_bundle` already owns the
    integrity half of PA-03's four counts, and a candidate failing that check would fail this one
    too for the same underlying reason. A project with no registry at all (a minimal fixture, or
    a checkout that has never configured one) can reproduce nothing - zero, not a crash; every
    other count in `run_status` degrades the same way rather than failing the whole command over
    a signal that is informational, never blocking.
    """
    known_ecosystems()
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return 0
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
    except ConfigError:
        return 0
    reproducible = 0
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        bundle = repository_dir / revision
        manifest_path = bundle / BUNDLE_MANIFEST_NAME
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(manifest, dict) or manifest.get("state") not in COUNTED_STATES:
            continue
        readme_path = bundle / "README.md"
        if not readme_path.is_file():
            continue
        try:
            facts = _load_facts(bundle / "facts.json")
            entry = find_entry(registry, facts.repository)
            if entry is None:
                continue
            rendered = render_readme(
                entry,
                facts,
                _read(bundle, "plan.json"),
                _read(bundle, "content_units.json"),
                _read(bundle, "dispositions.json"),
            )
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if rendered == readme_path.read_text(encoding="utf-8"):
            reproducible += 1
    return reproducible
