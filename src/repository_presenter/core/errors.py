"""Typed failures of the presenter, mapped to CLI exit codes.

Exit codes: 0 success, 1 validation or policy failure, 2 usage or configuration error,
3 safety refusal (allow-list, git safety, secret canary). A class is added here only together
with the stage that raises it.
"""

from __future__ import annotations


class PresenterError(Exception):
    """Base of every typed failure; ``exit_code`` is what the CLI returns for it."""

    exit_code = 1


class ConfigError(PresenterError):
    """A configuration or data file is missing or malformed; the run fails closed."""

    exit_code = 2


class GatewayError(PresenterError):
    """The LLM gateway refused, failed, or answered unusably; no job runs on a guess."""


class JobError(PresenterError):
    """A job's output was rejected after its one bounded re-ask, or the provider failed for good."""


class ProviderCallBudgetError(GatewayError):
    """This process reached its provider-call ceiling (``core/llm/ledger.py``'s
    ``PROVIDER_CALL_BUDGET``); the refused call is never sent, so the run stops with no further
    spend and fails closed."""


class NotAllowlistedError(PresenterError):
    """The repository is not in the registry allow-list, so nothing is touched."""

    exit_code = 3


class GitSafetyError(PresenterError):
    """A clone could not be made, pinned, or proven push-disabled; analysis never starts."""

    exit_code = 3


class RepositorySnapshotError(GitSafetyError):
    """The immutable repository view is absent or drifted while a transaction used it."""


class RepositoryMetadataError(PresenterError):
    """A read-only GitHub repository-metadata call failed, was denied, or answered unusably."""


class StateBackendError(PresenterError):
    """The durable-state backend (``core/state/``) could not load, save, or lease a repository
    record: corrupt or unparseable stored state, an unsupported schema version, or a CAS write
    that failed for a reason other than a plain stale-version rejection (``core/state/cas.py``
    retries those; this is for what is left after retries are exhausted or cannot apply)."""


class IllegalTransitionError(StateBackendError):
    """A durable-state transition was rejected by ``core/state/cas.py``'s own checks: not in the
    transition registry, the record's current state does not match the transition's ``from``, or
    the caller's lease/fencing token is stale (docs/STATE_MACHINE.md section 17)."""
