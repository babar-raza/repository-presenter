"""The issue funnel and its age alerts (TC-ISS-11): read-only, deterministic, no network.

Where every upstream-defect handoff stands, in one line the status report shows:

    PENDING -> APPROVED -> (ACKNOWLEDGED) -> FILED -> RESOLVED

``PENDING`` is a ``HANDOFF_PENDING`` handoff the owner has not approved; ``APPROVED`` is one with a
valid approval record that no run has filed yet; ``FILED`` and ``RESOLVED`` follow the handoff's
own status. A handoff waiting in the first two stages longer than a limit
(``DEFAULT_MAX_PENDING_DAYS``)
raises a GitHub Actions annotation (``AgeAlert``) in the style ``core/state/health.py`` established
for dead-man alerts: named, specific, visible in the run. It is a warning, not a failure: the next
step is the owner's (read the issue text, approve or reject), so a red job every day would only
teach people to ignore it.

The age of a handoff is the time since git first saw its file (``git_first_seen``): later edits to
the file do not reset the clock, and a file git has never seen has an unknown age that is reported
but never alerted on.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from repository_presenter.components.issues.approval import handoff_id
from repository_presenter.components.issues.ledger import discover_handoff_paths
from repository_presenter.components.issues.model import Handoff, load_handoff
from repository_presenter.core.git_safety.git import run_git

DEFAULT_MAX_PENDING_DAYS = 14
FUNNEL_STAGES: tuple[str, ...] = ("PENDING", "APPROVED", "ACKNOWLEDGED", "FILED", "RESOLVED")
_STAGE_BY_STATUS = {
    "HANDOFF_ACKNOWLEDGED": "ACKNOWLEDGED",
    "FILED": "FILED",
    "RESOLVED_UPSTREAM": "RESOLVED",
}
_WAITING = frozenset({"PENDING", "APPROVED"})


def stage_of(handoff: Handoff, *, approved: bool) -> str:
    """The funnel stage of ``handoff``; ``approved`` only matters while it is still pending."""
    if handoff.status == "HANDOFF_PENDING":
        return "APPROVED" if approved else "PENDING"
    return _STAGE_BY_STATUS[handoff.status]


@dataclass(frozen=True)
class FunnelRow:
    """One handoff's stage and age in whole days (``None`` when git never saw the file)."""

    handoff: Handoff
    stage: str
    age_days: int | None


def funnel_counts(rows: Iterable[FunnelRow]) -> dict[str, int]:
    """Handoffs per stage, every stage present and in funnel order."""
    counts = dict.fromkeys(FUNNEL_STAGES, 0)
    for row in rows:
        counts[row.stage] += 1
    return counts


def render_funnel(counts: dict[str, int]) -> str:
    return "issues: " + ", ".join(f"{stage} {counts[stage]}" for stage in FUNNEL_STAGES)


@dataclass(frozen=True)
class AgeAlert:
    """A handoff that has waited too long (or whose age cannot be told)."""

    repository: str
    handoff_id: str
    stage: str
    age_days: int | None
    max_days: int

    def annotation(self) -> str:
        """A GitHub Actions workflow command: ``::warning`` for a late handoff, ``::notice`` when
        its age is unknown. Single line; carries only names and numbers, never evidence text."""
        where = f"repository={self.repository} handoff={self.handoff_id} stage={self.stage}"
        if self.age_days is None:
            return (
                f"::notice title=Issue handoff age unknown::{where} - age unknown (git has not "
                "recorded when this handoff was added), so it cannot be alerted on"
            )
        return (
            f"::warning title=Issue handoff waiting too long::{where} - waiting {self.age_days} "
            f"days, over the {self.max_days}-day limit; approve it (ops/issue_approvals/), or "
            "reject it by removing the handoff"
        )


def age_alerts(rows: Iterable[FunnelRow], *, max_pending_days: int) -> list[AgeAlert]:
    """Alerts for handoffs still waiting (PENDING or APPROVED) past ``max_pending_days``, oldest
    first, then the ones whose age is unknown. Exactly at the limit is not yet late."""
    late: list[AgeAlert] = []
    unknown: list[AgeAlert] = []
    for row in rows:
        if row.stage not in _WAITING:
            continue
        alert = AgeAlert(
            row.handoff.repository,
            handoff_id(row.handoff),
            row.stage,
            row.age_days,
            max_pending_days,
        )
        if row.age_days is None:
            unknown.append(alert)
        elif row.age_days > max_pending_days:
            late.append(alert)
    late.sort(key=lambda a: (-(a.age_days or 0), a.handoff_id))
    unknown.sort(key=lambda a: a.handoff_id)
    return [*late, *unknown]


def git_first_seen(root: Path) -> Callable[[Path], datetime | None]:
    """A reader of when git first committed a file: the earliest commit that added it, or ``None``
    when git does not know the file (untracked, outside the repository, or git failed)."""

    def first_seen(path: Path) -> datetime | None:
        try:
            relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return None
        done = run_git(
            ["log", "--diff-filter=A", "--format=%cI", "--", relative], cwd=root, timeout=60
        )
        if done.returncode != 0:
            return None
        stamps = [line.strip() for line in done.stdout.splitlines() if line.strip()]
        if not stamps:
            return None
        try:
            moment = datetime.fromisoformat(stamps[-1])  # git log is newest first
        except ValueError:
            return None
        return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)

    return first_seen


def build_funnel(
    upstream_defects_root: Path,
    *,
    is_approved: Callable[[Handoff], bool],
    first_seen: Callable[[Path], datetime | None],
    now: datetime,
) -> list[FunnelRow]:
    """One row per committed handoff, in ledger order. ``is_approved`` is consulted only for a
    pending handoff."""
    rows = []
    for path in discover_handoff_paths(upstream_defects_root):
        handoff = load_handoff(path)
        approved = handoff.status == "HANDOFF_PENDING" and is_approved(handoff)
        added = first_seen(path)
        age = None if added is None else max(0, (now - added).days)
        rows.append(FunnelRow(handoff, stage_of(handoff, approved=approved), age))
    return rows
