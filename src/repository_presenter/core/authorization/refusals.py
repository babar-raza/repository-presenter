"""The typed reasons any README-proposal (or other write) effect refuses, in one place.

Every write path reports a refusal as one of these codes plus a human sentence, so a workflow, a
test, and the decision log all name the same thing. ``WriteRefusedError`` is the exception form: it
is a safety refusal (exit status 3, like an allow-list miss), never a validation failure.
"""

from __future__ import annotations

from enum import StrEnum

from repository_presenter.core.errors import PresenterError


class Refusal(StrEnum):
    # Registry write gate (core/registry/write_gate.py).
    REGISTRY_NOT_LISTED = "registry_not_listed"
    REGISTRY_DISABLED = "registry_disabled"
    REGISTRY_DRY_RUN = "registry_dry_run"
    REGISTRY_INACTIVE = "registry_inactive"
    # Candidate bundle (core/candidates.py::load_proposable_candidate).
    BUNDLE_MISSING = "bundle_missing"
    BUNDLE_NOT_READY = "bundle_not_ready"
    BUNDLE_INCONSISTENT = "bundle_inconsistent"
    SOURCE_MOVED = "source_moved"
    LOCAL_TEST_CANNOT_WRITE = "local_test_cannot_write"
    # Owner switch and credential presence (components/propose/effect.py).
    WRITE_NOT_ENABLED = "write_not_enabled"
    NO_WRITE_TOKEN = "no_write_token"
    # Authorization record (core/authorization/proposal.py, record_provenance.py).
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_UNREADABLE = "authorization_unreadable"
    AUTHORIZATION_NOT_COMMITTED = "authorization_not_committed"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_MISMATCH = "authorization_mismatch"
    # Write-token provenance (core/github/token_provenance.py).
    TOKEN_NOT_INSTALLATION = "token_not_installation"
    TOKEN_WRONG_SCOPE = "token_wrong_scope"
    TOKEN_UNVERIFIABLE = "token_unverifiable"
    TOKEN_APP_MISMATCH = "token_app_mismatch"
    # Remote state (components/propose/effect.py).
    PR_ALREADY_MERGED = "pr_already_merged"
    PR_ALREADY_CLOSED = "pr_already_closed"
    GITHUB_ERROR = "github_error"


class WriteRefusedError(PresenterError):
    """A write was refused before any remote effect; ``code`` is the typed reason."""

    exit_code = 3

    def __init__(self, code: Refusal, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
