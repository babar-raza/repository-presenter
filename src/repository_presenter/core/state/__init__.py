"""Durable repository state: CAS records, leases, triggers, and recovery (G5-W04).

See ``docs/STATE_MACHINE.md`` sections 13-15 for the authoritative design and
``migration/reuse-manifest.yaml`` for what was ported from the legacy
``foss-readme-optimizer`` system versus written fresh.
"""

from __future__ import annotations
