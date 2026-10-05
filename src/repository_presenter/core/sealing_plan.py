"""Plan one unattended sealing run: which drifted, enabled repositories to seal, in what order, and
under which model. Read-only and deterministic; no provider call and no GitHub call.

Input is the drift monitor's output through its file contract (``DRIFT_CONTRACT_VERSION``), never
the monitor's code: the drift monitor (``monitor.yml``) is a separate producer, so this
module depends only on the JSON shape below. A record is one repository and one status; only
``DRIFTED`` records ever become work. Output is the matrix the scheduled workflow fans out over.

Contract (``schema_version`` 1)::

    {"schema_version": 1,
     "repositories": [{"repository": "owner/name", "status": "DRIFTED" | "CURRENT" | "UNKNOWN"}]}

Selection rules, in order: only ``DRIFTED``; only a repository the registry lists and whose mode is
not ``disabled`` (the registry is the allow-list, a drifted but unlisted repository is never
sealed); sorted by repository name for a deterministic order; at most ``MAX_REPOSITORIES_PER_RUN``
taken, the rest deferred to a later run.

Sealing uses ``SEALING_MODEL`` alone (owner rule: never switch models). ``require_sealing_model``
refuses a run whose prompt manifests route anywhere else or whose ``GPT_OSS_MODEL`` override names
another model; the workflow never sets that override at all.

Pause switch: the repository variable ``REPOSITORY_PRESENTER_SEALING_PAUSED`` exactly equal to
``"1"`` plans nothing (``sealing_paused``). Unset, empty, or any other value leaves sealing
enabled: the owner wants autonomy by default, and the per-run cap bounds the spend. The check
runs in the plan job, before the drift file is read, so no seal or propose leg ever starts while
paused.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.core.config import MODEL_VARIABLE
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.registry.loader import find_entry
from repository_presenter.core.registry.models import Registry

DRIFT_CONTRACT_VERSION = 1
DRIFTED = "DRIFTED"
DRIFT_STATUSES = frozenset({DRIFTED, "CURRENT", "UNKNOWN"})
MAX_REPOSITORIES_PER_RUN = 3
SEALING_MODEL = "qwen3-next"
SEALING_PAUSED_VARIABLE = "REPOSITORY_PRESENTER_SEALING_PAUSED"
SEALING_PAUSED_NOTICE = "sealing paused by owner variable"


@dataclass(frozen=True)
class DriftRecord:
    repository: str
    status: str


@dataclass(frozen=True)
class SealingPlan:
    """The run: ``selected`` in order, everything else drifted that this run will not seal.

    ``publishable`` is the subset of ``selected`` whose registry mode is ``full``: the registry
    documents mode as governing publication readiness, so only those may receive a proposal. A
    ``dry_run`` repository is still sealed (analysis is not publication) but never proposed.
    """

    selected: tuple[str, ...]
    publishable: tuple[str, ...]
    deferred: tuple[str, ...]
    not_admitted: tuple[str, ...]
    disabled: tuple[str, ...]


def parse_drift_contract(raw: Any) -> tuple[DriftRecord, ...]:
    """Validate a decoded drift contract; fail closed on anything not exactly this shape."""
    if not isinstance(raw, dict):
        raise ConfigError("drift contract is not a JSON object")
    if raw.get("schema_version") != DRIFT_CONTRACT_VERSION:
        raise ConfigError(
            f"drift contract schema_version {raw.get('schema_version')!r} is not "
            f"{DRIFT_CONTRACT_VERSION}"
        )
    items = raw.get("repositories")
    if not isinstance(items, list):
        raise ConfigError("drift contract has no repositories list")
    records: list[DriftRecord] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError("drift contract repository entry is not an object")
        repository = item.get("repository")
        status = item.get("status")
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ConfigError(f"drift contract entry has no owner/name repository: {item!r}")
        if status not in DRIFT_STATUSES:
            raise ConfigError(f"drift contract entry {repository} has unknown status {status!r}")
        if repository in seen:
            raise ConfigError(f"drift contract names {repository} more than once")
        seen.add(repository)
        records.append(DriftRecord(repository, status))
    return tuple(records)


def read_drift_contract(path: Path) -> tuple[DriftRecord, ...]:
    """Read the drift monitor's output file; a missing file is a named failure, never zero work."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(
            f"drift monitor output not found at {path}; the scheduled sealing run needs the drift "
            "monitor's contract file and makes no work without it"
        ) from exc
    except ValueError as exc:
        raise ConfigError(f"drift monitor output is not valid JSON: {path}: {exc}") from exc
    return parse_drift_contract(raw)


def require_sealing_model(routes: Mapping[str, str], environment: Mapping[str, str]) -> None:
    """Refuse any run that would seal with a model other than ``SEALING_MODEL``."""
    elsewhere = sorted(
        {f"{job}={route}" for job, route in routes.items() if route != SEALING_MODEL}
    )
    if elsewhere:
        raise ConfigError(
            f"sealing runs only on {SEALING_MODEL}; prompt manifests route elsewhere: "
            f"{', '.join(elsewhere)}"
        )
    override = (environment.get(MODEL_VARIABLE) or "").strip()
    if override and override != SEALING_MODEL:
        raise ConfigError(
            f"{MODEL_VARIABLE}={override!r} would switch the sealing model; sealing runs only on "
            f"{SEALING_MODEL}"
        )


def plan_sealing_run(
    records: Iterable[DriftRecord],
    registry: Registry,
    *,
    cap: int = MAX_REPOSITORIES_PER_RUN,
) -> SealingPlan:
    """Select at most ``cap`` drifted, admitted, enabled repositories, in sorted order."""
    if cap < 1:
        raise ConfigError(f"a sealing run needs a cap of at least 1, not {cap}")
    drifted = sorted(
        (record.repository for record in records if record.status == DRIFTED),
    )
    eligible: list[tuple[str, str]] = []
    not_admitted: list[str] = []
    disabled: list[str] = []
    for repository in drifted:
        entry = find_entry(registry, repository)
        if entry is None:
            not_admitted.append(repository)
        elif entry.mode == "disabled":
            disabled.append(repository)
        else:
            eligible.append((entry.repository, entry.mode))
    taken = eligible[:cap]
    return SealingPlan(
        selected=tuple(repository for repository, _ in taken),
        publishable=tuple(repository for repository, mode in taken if mode == "full"),
        deferred=tuple(repository for repository, _ in eligible[cap:]),
        not_admitted=tuple(not_admitted),
        disabled=tuple(disabled),
    )


def sealing_paused(environment: Mapping[str, str]) -> bool:
    """True only when the owner pause variable is exactly ``"1"`` (never inferred from presence,
    truthiness or case: ``"true"``, ``"0"``, ``" 1"`` and the empty string all leave sealing on)."""
    return environment.get(SEALING_PAUSED_VARIABLE) == "1"


def _matrix(repositories: Iterable[str]) -> str:
    targets = [
        {"repository": repository, "slug": repository.replace("/", "__")}
        for repository in repositories
    ]
    return json.dumps(targets, separators=(",", ":"), sort_keys=True)


def empty_plan() -> SealingPlan:
    """The plan of a paused run: nothing selected, nothing publishable, nothing deferred."""
    return SealingPlan(selected=(), publishable=(), deferred=(), not_admitted=(), disabled=())


def github_output_lines(plan: SealingPlan) -> list[str]:
    """The step outputs the scheduled workflow reads, one ``name=value`` line each: the sealing
    matrix, whether there is any work, the proposal matrix (publishable only), and whether any
    repository is publishable this run."""
    return [
        f"repositories={_matrix(plan.selected)}",
        f"has_work={'true' if plan.selected else 'false'}",
        f"publishable={_matrix(plan.publishable)}",
        f"has_publishable={'true' if plan.publishable else 'false'}",
    ]
