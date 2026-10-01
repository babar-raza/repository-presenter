"""The real :class:`~repository_presenter.core.state.cas.StateBackend`: one git ref per
repository, on this project's own remote - never a target repository (the registry allow-list
governs what this project may *operate on*, not where its own operational state lives).

Ported from legacy ``readme_agent.state.git_backend`` (``migration/reuse-manifest.yaml``): the
per-ref compare-and-swap mechanism itself - plumbing commands only, never a working-tree checkout,
non-fast-forward detection that also structurally re-checks a ref that moved even when git's
stderr wording does not match a known marker, and a per-attempt nonce in the commit message so two
racing writers proposing byte-identical target state never collapse into git's silent "Everything
up-to-date" no-op - is the exact durable primitive this project needs, already proven in the legacy
system's own production use. Retained unchanged in spirit; adapted to this project's own
``run_git``/``github_https_auth_env`` (``core/git_safety/git.py``), to one CAS ref per repository
holding the whole :class:`~repository_presenter.core.state.schema.RepositoryRecord` (including its
embedded lease) rather than legacy's three separate lock-ref families plus a fourth state ref, and
to ``update-index --cacheinfo``/``write-tree`` rather than legacy's stdin-fed
``hash-object``/``mktree`` - this project's own ``run_git`` deliberately closes the child's stdin
(see ``_write_commit``'s own docstring for why).

Not ported: legacy's ``filelock``-based cross-process workspace lock. Each ``GitStateBackend``
instance owns its own disposable, process-local temporary bare repository (a fresh
``tempfile.TemporaryDirectory`` per instance, exactly as legacy did), so no second process ever
shares that directory - only concurrent *calls on one Python instance* need serializing, which a
plain ``threading.Lock`` already does without adding a new dependency this project does not
otherwise need.
"""

from __future__ import annotations

import subprocess
import tempfile
import threading
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from repository_presenter.core.errors import StateBackendError
from repository_presenter.core.git_safety.git import github_https_auth_env, run_git
from repository_presenter.core.retry import RetryableOperationError, run_with_retry
from repository_presenter.core.state.cas import SaveResult
from repository_presenter.core.state.schema import RepositoryRecord

STATE_REF_PREFIX = "refs/repository-presenter-state/records"
RECORD_BLOB_PATH = "record.json"

_STATE_FETCH_ARGS = ["fetch", "--no-write-fetch-head", "--no-tags", "--depth=1"]

_TRANSIENT_GIT_READ_ERRORS = (
    "could not resolve host",
    "connection reset",
    "empty reply from server",
    "failed to connect",
    "http/2 stream",
    "operation timed out",
    "remote end hung up unexpectedly",
    "rpc failed",
    "ssl",
    "tls",
)

# Pinned rather than relying on ambient git config - a GitHub Actions runner has no user identity
# configured by default, and this must not depend on one (core/git_safety/git.py's own
# DETERMINISM_FLAGS reasoning).
_COMMIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "repository-presenter",
    "GIT_AUTHOR_EMAIL": "repository-presenter@noreply.local",
    "GIT_COMMITTER_NAME": "repository-presenter",
    "GIT_COMMITTER_EMAIL": "repository-presenter@noreply.local",
}


def _ref_key(repository: str) -> str:
    """``org/name`` -> ``org__name``: exactly one slash, matching ``RepositoryRecord``'s own
    pattern, so this can never collide with a ref-unsafe path."""
    return repository.replace("/", "__", 1)


def _is_non_fast_forward(stderr: str) -> bool:
    lowered = stderr.lower()
    known_marker = any(
        marker in lowered
        for marker in ("non-fast-forward", "fetch first", "stale info", "already exists")
    )
    # GitHub can reject a stale ref update with "cannot lock ref ... is at <new> but expected
    # <old>" instead of the usual non-fast-forward wording. It is the same CAS outcome - another
    # writer won after our read - so the caller must reload and retry.
    stale_expected_value = (
        "cannot lock ref" in lowered and " is at " in lowered and " but expected " in lowered
    )
    return known_marker or stale_expected_value


def resolve_state_remote(remote: str) -> str:
    """Resolve a checkout-local remote name before entering isolated plumbing."""
    if "://" in remote or Path(remote).is_absolute():
        return remote
    resolved = run_git(["remote", "get-url", remote])
    if resolved.returncode != 0:
        return remote
    target = resolved.stdout.strip()
    if not target:
        raise StateBackendError(f"state remote {remote!r} resolved to an empty URL")
    local_target = Path(target)
    if "://" not in target and local_target.exists():
        return str(local_target.resolve())
    return target


class _StateGitWorkspace:
    """One process-local, disposable bare object/ref database for state git plumbing."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="repository-presenter-state-")
        self.root = Path(self._temporary.name)
        self.git_dir = self.root / "plumbing.git"
        initialized = run_git(["init", "--bare", str(self.git_dir)], cwd=self.root)
        if initialized.returncode != 0:
            self._temporary.cleanup()
            raise StateBackendError(
                f"initializing isolated state git workspace failed: {initialized.stderr}"
            )
        self.lock = threading.Lock()

    def cleanup(self) -> None:
        self._temporary.cleanup()


class GitStateBackend:
    """Production defaults to ``origin`` in the current working directory. A caller may select a
    separate state-only git remote - this is how a disposable-runner proof keeps every state write
    inside an isolated local bare repository without touching the control checkout's own
    ``origin``."""

    def __init__(self, *, remote: str = "origin", token: str | None = None) -> None:
        self._remote = resolve_state_remote(remote)
        self._token = token
        self._workspace = _StateGitWorkspace()
        self._git_cwd = self._workspace.git_dir
        self._lock = self._workspace.lock

    def close(self) -> None:
        """Deterministically remove this backend's disposable plumbing workspace."""
        self._workspace.cleanup()

    def __enter__(self) -> GitStateBackend:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def _run_remote_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        auth_env = github_https_auth_env(self._token)
        return run_git(args, cwd=self._git_cwd, env=auth_env or None)

    def _fetch_remote_sha(self, remote_ref: str) -> str | None:
        """The remote ref's current commit SHA, or ``None`` if it does not exist yet (first write
        for this repository) - distinguished from any other fetch failure (network/auth), which
        raises rather than being silently treated as "no prior state" (fail closed)."""
        local_ref = f"refs/repository-presenter-state-fetch/{uuid4().hex}"

        def fetch_once() -> subprocess.CompletedProcess[str]:
            result = self._run_remote_git(
                [*_STATE_FETCH_ARGS, self._remote, f"+{remote_ref}:{local_ref}"]
            )
            if result.returncode == 0:
                return result
            lowered = result.stderr.lower()
            if "couldn't find remote ref" in lowered:
                return result
            if any(marker in lowered for marker in _TRANSIENT_GIT_READ_ERRORS):
                raise RetryableOperationError(f"fetch of {remote_ref} failed: {result.stderr}")
            raise StateBackendError(f"fetch of {remote_ref} failed: {result.stderr}")

        try:
            result = run_with_retry("github_api", fetch_once)
        except RetryableOperationError as exc:
            raise StateBackendError(str(exc)) from exc
        if result.returncode != 0:
            return None
        try:
            rev = run_git(["rev-parse", "--verify", local_ref], cwd=self._git_cwd)
            if rev.returncode != 0:
                raise StateBackendError(
                    f"rev-parse of isolated fetch ref failed after fetching {remote_ref}: "
                    f"{rev.stderr}"
                )
            return rev.stdout.strip()
        finally:
            cleanup = run_git(["update-ref", "-d", local_ref], cwd=self._git_cwd)
            if cleanup.returncode != 0:
                raise StateBackendError(
                    f"cleanup of isolated fetch ref {local_ref} failed: {cleanup.stderr}"
                )

    def _push_with_retry(
        self, args: list[str], *, remote_ref: str
    ) -> subprocess.CompletedProcess[str]:
        def push_once() -> subprocess.CompletedProcess[str]:
            result = self._run_remote_git(args)
            if result.returncode == 0 or _is_non_fast_forward(result.stderr):
                return result
            if any(marker in result.stderr.lower() for marker in _TRANSIENT_GIT_READ_ERRORS):
                raise RetryableOperationError(f"push of {remote_ref} failed: {result.stderr}")
            return result

        try:
            return run_with_retry("github_api", push_once)
        except RetryableOperationError as exc:
            raise StateBackendError(str(exc)) from exc

    def _read_blob(self, commit_sha: str, path: str) -> str:
        result = run_git(["cat-file", "-p", f"{commit_sha}:{path}"], cwd=self._git_cwd)
        if result.returncode != 0:
            raise StateBackendError(f"reading {path} from {commit_sha} failed: {result.stderr}")
        return result.stdout

    def _write_commit(self, *, payload: str, parent_sha: str | None, message: str) -> str:
        """``hash-object`` -> ``update-index --cacheinfo`` -> ``write-tree`` -> ``commit-tree`` -
        no working tree touched. Returns the new commit SHA.

        This project's own ``run_git`` (``core/git_safety/git.py``) deliberately closes the
        child's stdin (no interactive prompts can ever reach a hook or credential helper), unlike
        legacy's wrapper - so legacy's ``hash-object -w --stdin``/``mktree`` plumbing, which reads
        its payload from stdin, cannot be used unchanged here. ``--cacheinfo`` lets
        ``update-index`` register one blob at one path with no stdin and no working tree at all
        (confirmed live against a disposable bare repository), and since this backend's disposable
        workspace index only ever holds this one ``record.json`` entry, each write simply replaces
        it rather than accumulating path history - ``write-tree`` always yields a tree containing
        exactly the latest payload.
        """
        tmp_path = self._workspace.root / f"record-{uuid4().hex}.json"
        tmp_path.write_text(payload, encoding="utf-8", newline="\n")
        try:
            blob = run_git(["hash-object", "-w", "--", str(tmp_path)], cwd=self._git_cwd)
        finally:
            tmp_path.unlink(missing_ok=True)
        if blob.returncode != 0:
            raise StateBackendError(f"hash-object failed: {blob.stderr}")
        blob_sha = blob.stdout.strip()

        indexed = run_git(
            ["update-index", "--add", "--cacheinfo", f"100644,{blob_sha},{RECORD_BLOB_PATH}"],
            cwd=self._git_cwd,
        )
        if indexed.returncode != 0:
            raise StateBackendError(f"update-index failed: {indexed.stderr}")

        tree = run_git(["write-tree"], cwd=self._git_cwd)
        if tree.returncode != 0:
            raise StateBackendError(f"write-tree failed: {tree.stderr}")
        tree_sha = tree.stdout.strip()

        commit_args = ["commit-tree", tree_sha, "-m", message]
        if parent_sha is not None:
            commit_args += ["-p", parent_sha]
        commit = run_git(commit_args, cwd=self._git_cwd, env=_COMMIT_IDENTITY_ENV)
        if commit.returncode != 0:
            raise StateBackendError(f"commit-tree failed: {commit.stderr}")
        return commit.stdout.strip()

    def _parse_record(self, repository: str, payload: str) -> RepositoryRecord:
        try:
            return RepositoryRecord.model_validate_json(payload)
        except ValidationError as exc:
            raise StateBackendError(
                f"durable state for {repository!r} is corrupt or unparseable: {exc}"
            ) from exc

    def load(self, repository: str) -> RepositoryRecord | None:
        with self._lock:
            remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(repository)}"
            sha = self._fetch_remote_sha(remote_ref)
            if sha is None:
                return None
            return self._parse_record(repository, self._read_blob(sha, RECORD_BLOB_PATH))

    def save(
        self, repository: str, record: RepositoryRecord, expected_version: int | None
    ) -> SaveResult:
        with self._lock:
            remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(repository)}"
            parent_sha = self._fetch_remote_sha(remote_ref)

            if parent_sha is None:
                if expected_version is not None:
                    return SaveResult(outcome="stale", record=None)
                current_version = None
            else:
                current = self._parse_record(
                    repository, self._read_blob(parent_sha, RECORD_BLOB_PATH)
                )
                if expected_version != current.state_version:
                    return SaveResult(outcome="stale", record=current)
                current_version = current.state_version

            new_version = (current_version or 0) + 1
            new_record = record.model_copy(update={"state_version": new_version})
            payload = new_record.model_dump_json(indent=2) + "\n"
            # Two racing writers computing the identical target state (same tree, parent, pinned
            # commit identity) would otherwise build a byte-identical commit; git pushes that as a
            # silent no-op ("Everything up-to-date"), not a rejection - both writers would see
            # returncode == 0 and believe they won the CAS. A per-attempt nonce in the commit
            # message (never the persisted payload) makes every attempt's commit distinct so git's
            # real non-fast-forward check can tell two racing attempts apart.
            commit_sha = self._write_commit(
                payload=payload,
                parent_sha=parent_sha,
                message=f"state: {repository} v{new_version} #{uuid4().hex[:12]}",
            )

            push = self._push_with_retry(
                ["push", self._remote, f"{commit_sha}:{remote_ref}"], remote_ref=remote_ref
            )
            if push.returncode != 0:
                if _is_non_fast_forward(push.stderr):
                    return SaveResult(outcome="stale", record=None)
                # _is_non_fast_forward matches known stderr substrings, which is git-version/
                # locale-dependent and can miss a genuine CAS rejection. Before treating an
                # unmatched push failure as a hard error, re-fetch the ref structurally: if it has
                # genuinely moved past the commit pushed from, that is the same CAS outcome
                # (stale) regardless of what git's stderr said. Only a push failure where the ref
                # did not move (auth, network, permissions) remains a hard StateBackendError.
                current_sha = self._fetch_remote_sha(remote_ref)
                if current_sha is not None and current_sha != parent_sha:
                    current = self._parse_record(
                        repository, self._read_blob(current_sha, RECORD_BLOB_PATH)
                    )
                    return SaveResult(outcome="stale", record=current)
                raise StateBackendError(f"push of {remote_ref} failed: {push.stderr}")

            return SaveResult(outcome="saved", record=new_record)
