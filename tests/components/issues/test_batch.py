"""TC-ISS-09/11: a batch of approved filings is bounded per repository (a daily cap, an open-issue
cap) and paced. Every count comes from the target repository itself, through an injected scan, so
a fresh checkout or a second run the same day cannot exceed a cap; a count that cannot be read
refuses the filing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from repository_presenter.components.issues.batch import (
    DEFAULT_DAILY_CAP,
    DEFAULT_OPEN_CAP,
    DEFAULT_PACE_SECONDS,
    FilingGovernor,
    FilingPolicy,
)
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import MarkerIssue

NOW = datetime(2026, 10, 11, 9, 30, tzinfo=UTC)


def _issue(number: int, state: str, created: str) -> MarkerIssue:
    return MarkerIssue(number, f"https://github.com/o/n/issues/{number}", state, created)


class _Scan:
    """A fake issue tracker: the marked issues the repository already holds."""

    def __init__(self, *issues: MarkerIssue, fail: bool = False) -> None:
        self.issues = list(issues)
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *, state: str, since: str | None) -> tuple[MarkerIssue, ...]:
        self.calls.append({"state": state, "since": since})
        if self.fail:
            raise RepositoryMetadataError("o/n: GET returned HTTP 403")
        return tuple(i for i in self.issues if state == "all" or i.state == state)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _governor(
    scan: _Scan, *, policy: FilingPolicy | None = None, clock: _Clock | None = None
) -> tuple[FilingGovernor, _Clock]:
    clock = clock or _Clock()
    governor = FilingGovernor(
        policy or FilingPolicy(daily_cap=2, open_cap=4, pace_seconds=30.0),
        scan=scan,
        now=lambda: NOW,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return governor, clock


def test_the_defaults_are_small_bounded_numbers() -> None:
    policy = FilingPolicy()
    assert (policy.daily_cap, policy.open_cap, policy.pace_seconds) == (
        DEFAULT_DAILY_CAP,
        DEFAULT_OPEN_CAP,
        DEFAULT_PACE_SECONDS,
    )
    assert 1 <= DEFAULT_DAILY_CAP <= DEFAULT_OPEN_CAP and DEFAULT_PACE_SECONDS > 0


def test_an_empty_repository_admits_up_to_the_daily_cap_and_no_more() -> None:
    governor, _ = _governor(_Scan())
    assert governor.check() is None
    governor.record_filed()
    assert governor.check() is None
    governor.record_filed()
    refusal = governor.check()
    assert refusal is not None and "daily cap" in refusal and "2" in refusal


def test_issues_filed_earlier_today_count_against_the_cap_across_runs() -> None:
    scan = _Scan(
        _issue(1, "open", "2026-10-11T00:00:01Z"),
        _issue(2, "closed", "2026-10-11T03:00:00Z"),
        _issue(3, "closed", "2026-10-10T23:59:59Z"),  # yesterday: not counted
    )
    governor, _ = _governor(scan)
    refusal = governor.check()
    assert refusal is not None and "daily cap" in refusal


def test_yesterdays_filings_do_not_count_against_todays_cap() -> None:
    scan = _Scan(
        _issue(1, "closed", "2026-10-10T23:59:59Z"), _issue(2, "closed", "2026-10-09T01:00:00Z")
    )
    governor, _ = _governor(scan)
    assert governor.check() is None


def test_the_open_issue_cap_refuses_even_when_the_daily_cap_has_room() -> None:
    scan = _Scan(*(_issue(n, "open", f"2026-10-0{n}T01:00:00Z") for n in range(1, 5)))
    governor, _ = _governor(scan, policy=FilingPolicy(daily_cap=9, open_cap=4, pace_seconds=0))
    refusal = governor.check()
    assert refusal is not None and "open" in refusal and "4" in refusal


def test_closed_issues_do_not_count_toward_the_open_cap() -> None:
    scan = _Scan(*(_issue(n, "closed", f"2026-09-0{n}T01:00:00Z") for n in range(1, 8)))
    governor, _ = _governor(scan, policy=FilingPolicy(daily_cap=9, open_cap=2, pace_seconds=0))
    assert governor.check() is None


def test_a_filing_in_this_run_counts_toward_the_open_cap() -> None:
    scan = _Scan(_issue(1, "open", "2026-10-01T01:00:00Z"))
    governor, _ = _governor(scan, policy=FilingPolicy(daily_cap=9, open_cap=2, pace_seconds=0))
    assert governor.check() is None
    governor.record_filed()
    assert governor.check() is not None


def test_a_count_that_cannot_be_read_refuses_instead_of_assuming_zero() -> None:
    governor, _ = _governor(_Scan(fail=True))
    refusal = governor.check()
    assert refusal is not None and "cannot count" in refusal


def test_the_scan_is_asked_for_todays_issues_and_the_open_ones_once() -> None:
    scan = _Scan()
    governor, _ = _governor(scan)
    governor.check()
    governor.record_filed()
    governor.check()
    assert {"state": "all", "since": "2026-10-11T00:00:00Z"} in scan.calls
    assert {"state": "open", "since": None} in scan.calls
    assert len(scan.calls) == 2  # memoized: the second check reads nothing


def test_the_first_write_is_not_paced_and_the_next_waits_out_the_interval() -> None:
    governor, clock = _governor(
        _Scan(), policy=FilingPolicy(daily_cap=5, open_cap=9, pace_seconds=30)
    )
    assert governor.before_write() is None
    assert clock.slept == []  # nothing to wait for before the first write
    clock.now += 12
    assert governor.before_write() is None
    assert clock.slept == [pytest.approx(18.0)]  # 30 - 12 already elapsed


def test_no_wait_when_the_interval_has_already_passed() -> None:
    governor, clock = _governor(
        _Scan(), policy=FilingPolicy(daily_cap=5, open_cap=9, pace_seconds=30)
    )
    governor.before_write()
    clock.now += 31
    governor.before_write()
    assert clock.slept == []


def test_a_refused_write_is_not_paced() -> None:
    governor, clock = _governor(_Scan(fail=True))
    assert governor.before_write() is not None
    assert clock.slept == []


@pytest.mark.parametrize("kwargs", [{"daily_cap": -1}, {"open_cap": -1}, {"pace_seconds": -0.5}])
def test_a_negative_policy_value_is_a_configuration_error(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        FilingPolicy(**kwargs)


def test_a_zero_daily_cap_pauses_filing() -> None:
    governor, _ = _governor(_Scan(), policy=FilingPolicy(daily_cap=0))
    assert governor.check() is not None
