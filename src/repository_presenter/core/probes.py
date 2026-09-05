"""What a live probe observed, kept beside the facts it informed rather than inside them.

A fact's evidence is hashed into `dependencies.json`, so anything volatile written there reopens
a stage whenever the world moves under an unchanged repository: PyPI publishing a new release
rewrote `install_command:pip`'s evidence and reopened EXTRACTING for a candidate whose bytes
could not change (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC7). The observation still
matters to a reader, so it is recorded here - the target, what the probe got, the HTTP status,
how long it took, and the volatile reading itself - and sealed in the bundle as `probes.json`.
Nothing in this file is hashed, and nothing a fact needs is only here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PROBES_FILENAME = "probes.json"


@dataclass(frozen=True)
class ProbeRecord:
    """One live read of one target, with the timing and status the fact does not carry."""

    kind: str
    target: str
    outcome: str
    status: int | None = None
    elapsed_ms: int | None = None
    # The reading that changes without the repository changing - a registry's latest version -
    # kept here so the fact it informed stays stable.
    observation: str | None = None


def write_probes(records: list[ProbeRecord], path: Path) -> None:
    """Write the probe records as one deterministic JSON document, ordered by target."""
    payload = [asdict(record) for record in sorted(records, key=lambda r: (r.kind, r.target))]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"))
