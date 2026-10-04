"""Per-owner GitHub App installation state for the scheduled drift observation (G7-W06).

`.github/workflows/monitor.yml` mints one read-only installation token per owner. When an owner has
no installation of the App covering its enabled repositories, the mint fails. That is a fact to
report, not an observation error: the owner is simply not observable until the App is installed.
This module records that fact per owner (``record_state``) and summarizes all owners after the
observation (``summarize``).

The run stays red only when no owner at all can be observed. Every owner failing to mint points at
the App credentials (``GH_APP_ID`` / ``GH_APP_PRIVATE_KEY``), not at a per-owner installation gap,
and that must not read as a successful run. A real observation error for an owner whose token was
minted is still a failure of that owner's own leg (see ``monitor.yml``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

APP_SLUG = "repository-presenter"
APP_ID = 5092474
SCHEMA_VERSION = 1
INSTALLED = "INSTALLED"
NOT_INSTALLED = "NOT_INSTALLED"
MINT_OUTCOMES: tuple[str, ...] = ("success", "failure")
RECORD_GLOB = "install-*.json"


class InstallStateError(ValueError):
    """A mint outcome this module does not recognize: an internal defect, never a notice."""


@dataclass(frozen=True)
class InstallationState:
    owner: str
    state: str
    repositories: str
    detail: str | None


def record_state(owner: str, outcome: str, repositories: str) -> InstallationState:
    """Classify one owner's mint outcome. ``success`` means the App is installed for these repos."""
    if outcome not in MINT_OUTCOMES:
        raise InstallStateError(f"unrecognized token mint outcome {outcome!r} for {owner}")
    if outcome == "success":
        return InstallationState(owner, INSTALLED, repositories, None)
    detail = (
        f"GitHub App '{APP_SLUG}' (id {APP_ID}) has no installation on '{owner}' covering the "
        f"enabled repositories ({repositories}), so no read-only token could be minted for them. "
        f"Install the App on '{owner}' with these repositories selected. Until then this owner "
        "is not observed; this is a notice, not a failure."
    )
    return InstallationState(owner, NOT_INSTALLED, repositories, detail)


def write_state(state: InstallationState, path: Path) -> Path:
    """Write one owner's state as deterministic JSON. No token is ever an input to this file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": SCHEMA_VERSION, **asdict(state)}
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


@dataclass(frozen=True)
class Summary:
    exit_code: int
    notices: tuple[str, ...]
    markdown: str
    problem: str | None


def summarize_installs(directory: Path) -> Summary:
    """Read every owner's state under ``directory``. Exit 1 only when no owner was observable."""
    records: list[dict[str, str | None]] = []
    for path in sorted(directory.rglob(RECORD_GLOB)):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        return Summary(
            1,
            (),
            "",
            "no installation records were found: the observation did not run for any owner",
        )
    installed = [r for r in records if r.get("state") == INSTALLED]
    missing = [r for r in records if r.get("state") == NOT_INSTALLED]
    rows = ["| Owner | Installation | Enabled repositories |", "| --- | --- | --- |"]
    rows += [f"| {r['owner']} | {r['state']} | {r['repositories']} |" for r in records]
    markdown = "\n".join(["## Monitor installation coverage", "", *rows, ""])
    notices = tuple(
        f"::notice title=GitHub App not installed on {r['owner']}::{r['detail']}" for r in missing
    )
    if not installed:
        return Summary(
            1,
            notices,
            markdown,
            "no owner's token could be minted, so the App credentials are the likely cause, "
            "not a per-owner installation gap; check GH_APP_ID and GH_APP_PRIVATE_KEY",
        )
    return Summary(0, notices, markdown, None)
