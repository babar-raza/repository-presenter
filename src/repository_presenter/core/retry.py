"""Bounded retry policies for external-operation boundaries, built on tenacity.

Only a failure raised as :class:`RetryableOperationError` is replayed, under the named policy;
anything else propagates on the first attempt. A policy is added here only together with the
boundary that consumes it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from tenacity import RetryCallState, Retrying, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_random_exponential

OperationClass = Literal["clone"]
T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Attempt and backoff bounds for one class of external operation."""

    operation_class: OperationClass
    max_attempts: int
    initial_seconds: float
    maximum_seconds: float

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if self.initial_seconds < 0 or self.maximum_seconds < 0:
            raise ValueError("backoff bounds must not be negative")


RETRY_POLICIES: dict[OperationClass, RetryPolicy] = {
    "clone": RetryPolicy("clone", max_attempts=3, initial_seconds=2, maximum_seconds=30),
}


class RetryableOperationError(Exception):
    """An explicitly retryable boundary failure, optionally carrying a server-suggested delay."""

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class _WaitPolicy:
    def __init__(self, policy: RetryPolicy) -> None:
        self._fallback = wait_random_exponential(
            multiplier=policy.initial_seconds,
            max=policy.maximum_seconds,
        )
        self._maximum = policy.maximum_seconds

    def __call__(self, retry_state: RetryCallState) -> float:
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        retry_after = getattr(exception, "retry_after_seconds", None)
        if retry_after is not None:
            return min(max(float(retry_after), 0.0), self._maximum)
        return float(self._fallback(retry_state))


def run_with_retry(
    operation_class: OperationClass,
    operation: Callable[[], T],
    *,
    sleep: Callable[[float], None] = time.sleep,
    max_attempts: int | None = None,
) -> T:
    """Run ``operation``, replaying only retryable failures under the named bounded policy."""
    policy = RETRY_POLICIES[operation_class]
    retrying = Retrying(
        stop=stop_after_attempt(max_attempts or policy.max_attempts),
        wait=_WaitPolicy(policy),
        retry=retry_if_exception_type(RetryableOperationError),
        reraise=True,
        sleep=sleep,
    )
    return retrying(operation)
