"""Read and write GitHub API clients (`docs/REPOSITORY_LAYOUT.md`).

Only the read half exists so far: `read_client.py` fetches a file, a recursive tree listing, or
the live default-branch revision of a public repository, each a single bounded GET with no
write scope. It is used to re-observe a target repository's own current state (never
repository-presenter's own state) — first consumer:
`components/readme/upstream_defects/redetect.py` (`docs/investigations/03-issue-tracking.md`
section 6). No module under this package ever performs a `POST`/`PATCH`/`DELETE` call; adding one
needs its own separately authorized write-scope work item, per `AGENTS.md`'s Security and Effects
section.
"""

from __future__ import annotations
