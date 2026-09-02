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


class NotAllowlistedError(PresenterError):
    """The repository is not in the registry allow-list, so nothing is touched."""

    exit_code = 3


class GitSafetyError(PresenterError):
    """A clone could not be made, pinned, or proven push-disabled; analysis never starts."""

    exit_code = 3


class RepositorySnapshotError(GitSafetyError):
    """The immutable repository view is absent or drifted while a transaction used it."""
