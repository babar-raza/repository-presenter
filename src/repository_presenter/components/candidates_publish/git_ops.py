"""Real local git plumbing for :mod:`effect`'s commit-and-push half (G7-W14).

Unlike ``components/propose/effect.py`` (which never clones the external target it proposes to,
and writes through the GitHub Contents/Refs REST API one file at a time), this effect's target is
THIS control repository's own already-checked-out working tree - the same checkout every hosted
job already has via ``actions/checkout``. A sealed bundle is many files
(``docs/REPOSITORY_LAYOUT.md``: ``README.md``, ``manifest.json``, ``facts.json``, ... - about a
dozen per candidate), so committing it through the Contents API would mean one REST call per file,
non-atomic and far more code than the problem needs. Plain ``git`` on the working tree the job
already has - exactly ``core/git_safety/git.py``'s own ``run_git``/``github_https_auth_env``,
already used for this project's state-ref pushes (``core/state/git_backend.py``) - commits every
changed file in one step (AGENTS.md "prefer a battle-tested... facility before writing a custom
mechanism").

Every function here raises :class:`RepositoryMetadataError` on failure (the same type
``core/github/client.py``'s write calls raise, so :mod:`effect` catches one exception type across
both its local-git and its GitHub-REST operations) and makes no retry decision of its own -
``effect.py`` decides what a failure means.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.git_safety.git import github_https_auth_env, run_git

#: Pinned rather than relying on ambient git config, exactly like
#: ``core/state/git_backend.py``'s own ``_COMMIT_IDENTITY_ENV`` - a hosted runner has no user
#: identity configured by default, and a local rehearsal must not depend on the operator's own.
_COMMIT_IDENTITY_ENV = {
    "GIT_AUTHOR_NAME": "repository-presenter",
    "GIT_AUTHOR_EMAIL": "repository-presenter@noreply.local",
    "GIT_COMMITTER_NAME": "repository-presenter",
    "GIT_COMMITTER_EMAIL": "repository-presenter@noreply.local",
}

#: ``git ls-remote --exit-code`` exits 2 for "no matching refs" specifically (not "git itself
#: failed") - the one case this module treats as an ordinary "branch does not exist yet" answer.
_LS_REMOTE_NO_MATCH_EXIT_CODE = 2


def remote_branch_sha(
    root: Path, branch: str, *, token: str | None, remote: str = "origin"
) -> str | None:
    """``branch``'s current tip commit sha on ``remote``, or ``None`` if it does not exist yet."""
    result = run_git(
        ["ls-remote", "--exit-code", remote, f"refs/heads/{branch}"],
        cwd=root,
        env=github_https_auth_env(token) or None,
    )
    if result.returncode == _LS_REMOTE_NO_MATCH_EXIT_CODE:
        return None
    if result.returncode != 0:
        raise RepositoryMetadataError(f"ls-remote of {branch!r} failed: {result.stderr}")
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    sha = line.split()[0] if line else ""
    if not sha:
        raise RepositoryMetadataError(f"ls-remote of {branch!r} returned no usable commit sha")
    return sha


def checkout_branch(
    root: Path, branch: str, start_point: str, *, token: str | None, remote: str = "origin"
) -> None:
    """Fetch ``start_point`` (a ref *name* - ``branch`` itself, continuing a pending update, or
    the base branch, for a fresh one) from ``remote`` and check it out as the local ``branch``,
    creating or resetting it to exactly that fetched tip.

    Always fetches first, never trusts a local copy of either ref: a fresh hosted checkout
    (``actions/checkout`` fetches only the one ref it was triggered on) has no history at all for
    the control-update branch the first time this effect reads it, and even the base branch's own
    local copy can be behind the remote by the time this job's own checkout ran. Never rebased,
    never force-reset past ``start_point`` itself - ``branch`` always ends up exactly at the
    commit ``start_point`` names on ``remote``, right now. ``--depth=1``: building one new commit
    on top needs only that one parent, never the ref's full history - the same bound
    ``core/state/git_backend.py``'s own ``_STATE_FETCH_ARGS`` already applies to this project's
    other control-repository ref reads."""
    fetched = run_git(
        ["fetch", "--depth=1", remote, start_point],
        cwd=root,
        env=github_https_auth_env(token) or None,
    )
    if fetched.returncode != 0:
        raise RepositoryMetadataError(f"fetch of {start_point!r} failed: {fetched.stderr}")
    result = run_git(["checkout", "-B", branch, "FETCH_HEAD"], cwd=root)
    if result.returncode != 0:
        raise RepositoryMetadataError(
            f"checkout of {branch!r} from {start_point!r} failed: {result.stderr}"
        )


def read_committed_file(root: Path, path: str) -> str | None:
    """``path``'s text content at the currently checked-out commit, or ``None`` if it does not
    exist there - a plain filesystem read, since ``checkout_branch`` already moved the working
    tree to the commit this needs to read."""
    candidate = root / path
    if not candidate.is_file():
        return None
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError as exc:
        raise RepositoryMetadataError(f"reading {path!r} failed: {exc}") from exc


def overlay_bundle(root: Path, slug: str, import_dir: Path) -> None:
    """Replace ``candidates/<slug>`` in the working tree wholesale with ``import_dir``'s own
    content - the exact same "replaces candidates/<slug> on each job's checkout wholesale"
    operation ``propose.yml``'s own "Require a READY_FOR_PROPOSAL bundle" step already performs
    (there, in bash, against ``base_branch``'s own checkout; here, against this branch's, after
    :func:`checkout_branch` - see ``effect.py``'s own docstring for why the ordering matters)."""
    if not import_dir.is_dir():
        raise RepositoryMetadataError(
            f"sealed bundle import directory does not exist: {import_dir}"
        )
    target = root / "candidates" / slug
    try:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(import_dir, target)
    except OSError as exc:
        raise RepositoryMetadataError(
            f"overlaying the sealed bundle onto {target} failed: {exc}"
        ) from exc


def stage_and_commit(root: Path, paths: tuple[str, ...], message: str) -> str | None:
    """Stage exactly ``paths`` and commit; returns the new commit sha, or ``None`` when staging
    produced no change (git's own "nothing to commit", never treated as a failure)."""
    added = run_git(["add", "--", *paths], cwd=root)
    if added.returncode != 0:
        raise RepositoryMetadataError(f"staging {paths!r} failed: {added.stderr}")
    status = run_git(["status", "--porcelain", "--", *paths], cwd=root)
    if status.returncode != 0:
        raise RepositoryMetadataError(
            f"checking staged status of {paths!r} failed: {status.stderr}"
        )
    if not status.stdout.strip():
        return None
    commit = run_git(["commit", "-m", message], cwd=root, env=_COMMIT_IDENTITY_ENV)
    if commit.returncode != 0:
        raise RepositoryMetadataError(f"commit of {paths!r} failed: {commit.stderr}")
    revision = run_git(["rev-parse", "HEAD"], cwd=root)
    if revision.returncode != 0:
        raise RepositoryMetadataError(f"reading the new commit's sha failed: {revision.stderr}")
    return revision.stdout.strip()


def push_branch(root: Path, branch: str, *, token: str | None, remote: str = "origin") -> None:
    """Push the local ``branch``'s current ``HEAD`` to ``remote`` at ``refs/heads/{branch}`` - a
    plain push, never ``--force``: the caller only ever builds ``HEAD`` as one new commit on top
    of ``branch``'s own prior tip (or the base branch, for a first publish), so this is always a
    fast-forward."""
    result = run_git(
        ["push", remote, f"HEAD:refs/heads/{branch}"],
        cwd=root,
        env=github_https_auth_env(token) or None,
    )
    if result.returncode != 0:
        raise RepositoryMetadataError(f"push of {branch!r} failed: {result.stderr}")
