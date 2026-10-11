"""Bound and pace a batch of approved filings (TC-ISS-09 and TC-ISS-11).

An owner may approve many handoffs at once. The scheduled workflow must still never flood a
maintainer: per target repository, at most ``daily_cap`` issues are filed per UTC day, no more
than ``open_cap`` of this system's issues are open at once, and successive writes in one run are
``pace_seconds`` apart (GitHub asks integrations to pause between content-creating requests).

The counts come from the target repository itself - the issues carrying this system's fingerprint
marker (``core/github/client.py::scan_marker_issues``) - never from a local file, because a
scheduled run starts from a fresh checkout and a second run the same day must see the first run's
filings. A count that cannot be read refuses the filing (fail closed): a cap decided on a guess
could be exceeded.

``FilingGovernor.before_write`` is the hook ``file.py::file_handoff`` calls once, after every other
gate has passed and just before the first POST, so a cap is spent only by a filing that would
really be made (not by a handoff that is unapproved, already filed upstream, or stale). It is
read-only toward GitHub and holds no credential of its own: the scan is injected.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import MarkerIssue

# Deliberately small: a handful of fresh issues a day is what a maintainer can triage. The owner
# raises them with the CLI flags the workflow passes, in a reviewed workflow change.
DEFAULT_DAILY_CAP = 3
DEFAULT_OPEN_CAP = 5
DEFAULT_PACE_SECONDS = 10.0

# (state, since) -> this system's marked issues of that state; see ``scan_marker_issues``.
ScanFn = Callable[..., tuple[MarkerIssue, ...]]


@dataclass(frozen=True)
class FilingPolicy:
    """The per-repository limits of one run. A cap of ``0`` pauses filing for that repository."""

    daily_cap: int = DEFAULT_DAILY_CAP
    open_cap: int = DEFAULT_OPEN_CAP
    pace_seconds: float = DEFAULT_PACE_SECONDS

    def __post_init__(self) -> None:
        if self.daily_cap < 0 or self.open_cap < 0 or self.pace_seconds < 0:
            raise ValueError("filing policy values must not be negative")


def _instant(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class FilingGovernor:
    """The caps and pacing for one target repository in one run."""

    def __init__(
        self,
        policy: FilingPolicy,
        *,
        scan: ScanFn,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.policy = policy
        self._scan = scan
        self._now = now
        self._sleep = sleep
        self._monotonic = monotonic
        self._counts: tuple[int, int] | None = None  # (filed today, open now) before this run
        self._filed_this_run = 0
        self._last_write: float | None = None

    def _read_counts(self) -> tuple[int, int]:
        if self._counts is None:
            moment = self._now().astimezone(UTC)
            day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
            since = day_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            today = 0
            for issue in self._scan(state="all", since=since):
                created = _instant(issue.created_at)
                if created is not None and created >= day_start:
                    today += 1
            opened = len(self._scan(state="open", since=None))
            self._counts = (today, opened)
        return self._counts

    def check(self) -> str | None:
        """The reason one more filing is refused now, or ``None``. Reads the counts once."""
        try:
            today, opened = self._read_counts()
        except RepositoryMetadataError as exc:
            return f"cannot count this repository's filed issues ({exc}) - refusing to file"
        filed = today + self._filed_this_run
        if filed >= self.policy.daily_cap:
            return (
                f"daily cap reached: {filed} issue(s) filed in this repository today (UTC), "
                f"cap {self.policy.daily_cap}"
            )
        open_now = opened + self._filed_this_run
        if open_now >= self.policy.open_cap:
            return (
                f"open-issue cap reached: {open_now} of this system's issues are open in this "
                f"repository, cap {self.policy.open_cap}"
            )
        return None

    def before_write(self) -> str | None:
        """``check``, then - for an admitted write - wait out the pacing interval since the
        previous write of this run. The first write waits for nothing."""
        refusal = self.check()
        if refusal is not None:
            return refusal
        if self._last_write is not None:
            wait = self.policy.pace_seconds - (self._monotonic() - self._last_write)
            if wait > 0:
                self._sleep(wait)
        self._last_write = self._monotonic()
        return None

    def record_filed(self) -> None:
        """One issue now exists because of this run (filed, or found after a lost response)."""
        self._filed_this_run += 1
