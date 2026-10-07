"""Plan one unattended sealing run: which drifted, enabled repositories to seal, in what order, and
under which model. Read-only and deterministic; no provider call and no GitHub call.

Input is the drift monitor's output through its file contract (``DRIFT_CONTRACT_VERSION``), never
the monitor's code: the drift monitor (``monitor.yml``) is a separate producer, so this
module depends only on the JSON shape below. A record is one repository and one status; only
``DRIFTED`` records ever become work. Output is the matrix the scheduled workflow fans out over.

Contract (``schema_version`` 1)::

    {"schema_version": 1,
     "repositories": [{"repository": "owner/name", "status": "DRIFTED" | "CURRENT" | "UNKNOWN",
                        "source_revision": "<40-hex>" | null}]}

``source_revision`` is additive and optional (omitted or ``null`` on older evidence): the upstream
head the status was observed against, when the monitor's own evidence carried one. It is read for
exactly one purpose below: telling a fresh commit apart from the same stuck drift a failed seal
already saw.

Selection rules, in order: only ``DRIFTED``; only a repository the registry lists and whose mode is
not ``disabled`` (the registry is the allow-list, a drifted but unlisted repository is never
sealed); a repository the sealing history's own record shows FAILED within the cooldown, with no
new commit since, is skipped (``SEALING_FAILURE_COOLDOWN``, below) rather than retried every run
for nothing; sorted by repository name for a deterministic order; at most
``MAX_REPOSITORIES_PER_RUN`` taken, the rest deferred to a later run.

Failure memory (G7-W06 follow-up, #1009): the plan job has no failure memory on its own - every
run re-reads the drift file fresh, so a repository stuck on the same unfixed blocking defect (a
BC-05 UNCLASSIFIED deferral, a repeated S6 authoring refusal, anything that is not a transient
provider hiccup) is re-selected and re-spends its full provider-call budget every single run,
forever, with zero progress. ``plan_sealing_run`` now also takes the sealing history (optional;
``read_sealing_history_contract``/``SealingAttempt``, assembled by the workflow from past
``sealing-scheduled.yml`` runs - see that file's header). A repository whose most recent recorded
attempt is ``FAILED`` is skipped while ``now - observed_at < SEALING_FAILURE_COOLDOWN``, UNLESS
the drift record's own ``source_revision`` differs from the one the failure was recorded against
(a new commit landed, so the old failure may no longer apply - never skip on stale evidence). Each
skip is a typed, logged ``SkippedRepository`` (never silent); once the cooldown elapses the
repository is eligible again automatically, with no separate unlock step, so a repository that
keeps failing is retried roughly once per cooldown window forever, never abandoned (the required
negative control: starvation would mean the fix just moved the stuck-forever defect from "re-tried
and burning budget" to "silently parked", which is not an improvement).

Cooldown ``SEALING_FAILURE_COOLDOWN = timedelta(hours=24)``: the scheduled workflow runs once a
day (``cron: "37 5 * * *"``); 24 hours is exactly one scheduled cycle, so a stuck repository loses
at most one automatic attempt to the skip (a manual ``workflow_dispatch`` inside the window is
still correctly skipped - nothing changed, so there is nothing new to spend a call re-discovering)
while still being retried on the very next cycle once the window passes, with no dependency on
however many cycles happened to run in between.

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
from datetime import UTC, datetime, timedelta
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

SEALING_HISTORY_CONTRACT_VERSION = 1
OUTCOME_SEALED = "SEALED"
OUTCOME_FAILED = "FAILED"
SEALING_OUTCOMES = frozenset({OUTCOME_SEALED, OUTCOME_FAILED})
# See the module docstring's "Cooldown" paragraph for why 24h (one scheduled cycle).
SEALING_FAILURE_COOLDOWN = timedelta(hours=24)


@dataclass(frozen=True)
class DriftRecord:
    repository: str
    status: str
    source_revision: str | None = None


@dataclass(frozen=True)
class SealingAttempt:
    """One repository's most recently recorded sealing outcome, read from sealing history."""

    repository: str
    outcome: str
    observed_at: datetime
    source_revision: str | None = None


@dataclass(frozen=True)
class SkippedRepository:
    """A drifted, admitted, enabled repository this run still did not select, and why - the typed
    reason ``plan_sealing_run`` always records rather than silently dropping the repository."""

    repository: str
    reason: str


@dataclass(frozen=True)
class SealingPlan:
    """The run: ``selected`` in order, everything else drifted that this run will not seal.

    ``publishable`` is the subset of ``selected`` whose registry mode is ``full``: the registry
    documents mode as governing publication readiness, so only those may receive a proposal. A
    ``dry_run`` repository is still sealed (analysis is not publication) but never proposed.

    ``skipped`` is drifted, admitted, enabled repositories withheld by failure memory alone (a
    recent recorded failure, cooldown not yet elapsed, no new commit) - disjoint from
    ``deferred`` (withheld only by the per-run cap) and from ``not_admitted``/``disabled``.
    """

    selected: tuple[str, ...]
    publishable: tuple[str, ...]
    deferred: tuple[str, ...]
    not_admitted: tuple[str, ...]
    disabled: tuple[str, ...]
    skipped: tuple[SkippedRepository, ...] = ()


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
        revision = item.get("source_revision")
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ConfigError(f"drift contract entry has no owner/name repository: {item!r}")
        if status not in DRIFT_STATUSES:
            raise ConfigError(f"drift contract entry {repository} has unknown status {status!r}")
        if revision is not None and not isinstance(revision, str):
            raise ConfigError(
                f"drift contract entry {repository} has a non-string source_revision {revision!r}"
            )
        if repository in seen:
            raise ConfigError(f"drift contract names {repository} more than once")
        seen.add(repository)
        records.append(DriftRecord(repository, status, revision))
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


def parse_sealing_history_contract(raw: Any) -> tuple[SealingAttempt, ...]:
    """Validate a decoded sealing history contract; fail closed on anything not exactly this
    shape (the same discipline ``parse_drift_contract`` applies to its own file).

    Contract (``schema_version`` 1)::

        {"schema_version": 1,
         "repositories": [{"repository": "owner/name", "outcome": "SEALED" | "FAILED",
                            "observed_at": "<ISO 8601, timezone-aware>",
                            "source_revision": "<40-hex>" | null}]}

    One row per repository is expected (the assembler's own job is to reduce to the most recent
    attempt), but a caller that hands over several is not refused: ``plan_sealing_run`` reduces to
    the latest ``observed_at`` per repository itself, so assembly never has to be exactly right for
    planning to stay correct.
    """
    if not isinstance(raw, dict):
        raise ConfigError("sealing history contract is not a JSON object")
    if raw.get("schema_version") != SEALING_HISTORY_CONTRACT_VERSION:
        raise ConfigError(
            f"sealing history contract schema_version {raw.get('schema_version')!r} is not "
            f"{SEALING_HISTORY_CONTRACT_VERSION}"
        )
    items = raw.get("repositories")
    if not isinstance(items, list):
        raise ConfigError("sealing history contract has no repositories list")
    attempts: list[SealingAttempt] = []
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError("sealing history contract repository entry is not an object")
        repository = item.get("repository")
        outcome = item.get("outcome")
        revision = item.get("source_revision")
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ConfigError(f"sealing history entry has no owner/name repository: {item!r}")
        if outcome not in SEALING_OUTCOMES:
            raise ConfigError(f"sealing history entry {repository} has unknown outcome {outcome!r}")
        if revision is not None and not isinstance(revision, str):
            raise ConfigError(
                f"sealing history entry {repository} has a non-string source_revision {revision!r}"
            )
        try:
            observed_at = datetime.fromisoformat(str(item.get("observed_at")))
        except ValueError as exc:
            raise ConfigError(
                f"sealing history entry {repository} has no valid observed_at: {exc}"
            ) from exc
        if observed_at.tzinfo is None:
            raise ConfigError(f"sealing history entry {repository} observed_at has no timezone")
        attempts.append(SealingAttempt(repository, outcome, observed_at, revision))
    return tuple(attempts)


def read_sealing_history_contract(path: Path) -> tuple[SealingAttempt, ...]:
    """Read the sealing history file. Unlike the drift contract, a missing or malformed file is
    never a failure here: no history is the ordinary state of the very first run (and of a run
    whose history-assembly step itself failed), and failing closed on it would trade "a stuck
    repository burns its budget every run" for the strictly worse "sealing stops running
    entirely" - this feature is memory, never a gate. The caller (``run_sealing_plan``) is the one
    that decides whether to say so out loud; this function just returns what it can.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    try:
        return parse_sealing_history_contract(raw)
    except ConfigError:
        return ()


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


def _latest_attempts(history: Iterable[SealingAttempt]) -> dict[str, SealingAttempt]:
    """Each repository's own most recent attempt by ``observed_at``; a caller's own history file
    is expected to already hold exactly one row per repository, but this reduces safely even when
    it holds more (several past runs concatenated), so the assembler never has to deduplicate."""
    latest: dict[str, SealingAttempt] = {}
    for attempt in history:
        current = latest.get(attempt.repository)
        if current is None or attempt.observed_at > current.observed_at:
            latest[attempt.repository] = attempt
    return latest


def _cooldown_skip(
    repository: str,
    revision: str | None,
    attempt: SealingAttempt | None,
    *,
    now: datetime,
    cooldown: timedelta,
) -> SkippedRepository | None:
    """``None`` when ``repository`` may be planned; a typed, logged reason when failure memory
    withholds it this run. Never raises: a missing or incomparable ``now`` (naive) is the only
    caller error possible here, and ``plan_sealing_run`` always passes a timezone-aware clock."""
    if attempt is None or attempt.outcome != OUTCOME_FAILED:
        return None
    if (
        revision is not None
        and attempt.source_revision is not None
        and revision != attempt.source_revision
    ):
        # A new commit landed since the recorded failure: the old failure was against a different
        # revision and may no longer apply, so the cooldown never applies to stale evidence.
        return None
    elapsed = now - attempt.observed_at
    if elapsed >= cooldown:
        return None
    resume = attempt.observed_at + cooldown
    return SkippedRepository(
        repository,
        f"cooldown: failed {elapsed} ago"
        f"{f' at {attempt.source_revision}' if attempt.source_revision else ''}; "
        f"eligible again at {resume.isoformat(timespec='seconds')} unless a new commit lands first",
    )


def plan_sealing_run(
    records: Iterable[DriftRecord],
    registry: Registry,
    history: Iterable[SealingAttempt] = (),
    *,
    cap: int = MAX_REPOSITORIES_PER_RUN,
    now: datetime | None = None,
    cooldown: timedelta = SEALING_FAILURE_COOLDOWN,
) -> SealingPlan:
    """Select at most ``cap`` drifted, admitted, enabled repositories, in sorted order.

    ``history`` is this plan's failure memory (see the module docstring): a repository whose most
    recent recorded attempt FAILED is withheld into ``skipped`` while still within ``cooldown`` of
    that failure, unless the drift record's own ``source_revision`` shows a new commit since. Pass
    ``now`` (always timezone-aware) in tests for a deterministic clock; production code leaves it
    to default to the real time.
    """
    if cap < 1:
        raise ConfigError(f"a sealing run needs a cap of at least 1, not {cap}")
    clock = now if now is not None else datetime.now(UTC)
    latest = _latest_attempts(history)
    revisions = {record.repository: record.source_revision for record in records}
    drifted = sorted(
        (record.repository for record in records if record.status == DRIFTED),
    )
    eligible: list[tuple[str, str]] = []
    not_admitted: list[str] = []
    disabled: list[str] = []
    skipped: list[SkippedRepository] = []
    for repository in drifted:
        entry = find_entry(registry, repository)
        if entry is None:
            not_admitted.append(repository)
            continue
        if entry.mode == "disabled":
            disabled.append(repository)
            continue
        skip = _cooldown_skip(
            entry.repository,
            revisions.get(repository),
            latest.get(entry.repository),
            now=clock,
            cooldown=cooldown,
        )
        if skip is not None:
            skipped.append(skip)
            continue
        eligible.append((entry.repository, entry.mode))
    taken = eligible[:cap]
    return SealingPlan(
        selected=tuple(repository for repository, _ in taken),
        publishable=tuple(repository for repository, mode in taken if mode == "full"),
        deferred=tuple(repository for repository, _ in eligible[cap:]),
        not_admitted=tuple(not_admitted),
        disabled=tuple(disabled),
        skipped=tuple(skipped),
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
    return SealingPlan(
        selected=(), publishable=(), deferred=(), not_admitted=(), disabled=(), skipped=()
    )


def _skipped_json(skipped: Iterable[SkippedRepository]) -> str:
    rows = [{"repository": item.repository, "reason": item.reason} for item in skipped]
    return json.dumps(rows, separators=(",", ":"), sort_keys=True)


def github_output_lines(plan: SealingPlan) -> list[str]:
    """The step outputs the scheduled workflow reads, one ``name=value`` line each: the sealing
    matrix, whether there is any work, the proposal matrix (publishable only), whether any
    repository is publishable this run, and every repository failure memory withheld this run
    with its typed reason (never silent - the workflow's own log is the second place, besides
    ``run_sealing_plan``'s stdout, this shows up)."""
    return [
        f"repositories={_matrix(plan.selected)}",
        f"has_work={'true' if plan.selected else 'false'}",
        f"publishable={_matrix(plan.publishable)}",
        f"has_publishable={'true' if plan.publishable else 'false'}",
        f"skipped={_skipped_json(plan.skipped)}",
    ]
