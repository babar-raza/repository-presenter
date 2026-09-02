"""Bounded retry: only explicitly retryable failures replay, under a named policy."""

from __future__ import annotations

import pytest

from repository_presenter.core.retry import (
    RETRY_POLICIES,
    RetryableOperationError,
    RetryPolicy,
    run_with_retry,
)


def test_every_declared_operation_class_has_a_bounded_policy() -> None:
    assert set(RETRY_POLICIES) == {"clone", "package_registry", "link_check", "llm_call"}
    assert all(policy.max_attempts <= 5 for policy in RETRY_POLICIES.values())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0, "initial_seconds": 1, "maximum_seconds": 1},
        {"max_attempts": 11, "initial_seconds": 1, "maximum_seconds": 1},
        {"max_attempts": 3, "initial_seconds": -1, "maximum_seconds": 1},
    ],
)
def test_policies_reject_unbounded_or_negative_values(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        RetryPolicy("clone", **kwargs)  # type: ignore[arg-type]


def test_only_explicitly_retryable_failures_are_retried() -> None:
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RetryableOperationError("transient")
        return "ok"

    assert run_with_retry("clone", operation, sleep=lambda _seconds: None) == "ok"
    assert calls == 3


def test_caller_may_tighten_the_attempt_bound() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise RetryableOperationError("still transient")

    with pytest.raises(RetryableOperationError):
        run_with_retry("clone", operation, sleep=lambda _seconds: None, max_attempts=2)
    assert calls == 2


def test_non_retryable_failure_is_not_replayed() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        run_with_retry("clone", operation, sleep=lambda _seconds: None)
    assert calls == 1


def test_server_suggested_delay_wins_within_the_policy_maximum() -> None:
    sleeps: list[float] = []
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RetryableOperationError("slow down", retry_after_seconds=7)
        if calls == 2:
            raise RetryableOperationError("slow down more", retry_after_seconds=10_000)
        return "ok"

    assert run_with_retry("clone", operation, sleep=sleeps.append) == "ok"
    assert sleeps == [7.0, RETRY_POLICIES["clone"].maximum_seconds]
