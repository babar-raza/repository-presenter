"""Read and write GitHub API clients (`docs/REPOSITORY_LAYOUT.md`).

Only the read half exists so far, in two modules landed independently for two different
workstreams:

- `client.py` (workstream 2, `docs/investigations/02-repo-metadata-community-files.md` section
  2.1): `GET /repos/{owner}/{repo}` for a repository's own description/homepage/topics, at the
  same repository-scoped `GH_TOKEN` read access Gate A/B already use for cloning.
- `read_client.py` (workstream 3, `docs/investigations/03-issue-tracking.md` section 6): fetches a
  file, a recursive tree listing, or the live default-branch revision of a public repository, each
  a single bounded GET, to re-observe a target repository's own current state for upstream-defect
  redetection.

No module under this package ever performs a `POST`/`PATCH`/`PUT`/`DELETE` call; adding one needs
its own separately authorized write-scope work item (`OWNER-04`/G5's `Administration`/`Issues`
write scopes, neither granted), per `AGENTS.md`'s Security and Effects section.
"""

from __future__ import annotations
