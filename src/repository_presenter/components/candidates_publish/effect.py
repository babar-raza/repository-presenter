"""The gated effect: commit a just-sealed candidate bundle to THIS control repository's own
committed ``candidates/<slug>/`` tree, on a dedicated branch, and open or update the one pull
request that carries it (G7-W14; ``docs/EXECUTION_STATE_MACHINE.md`` G7 Work item 14).

The gap this closes: a hosted ``present.yml`` run can genuinely re-seal a repository to
``READY_FOR_PROPOSAL``, but exports the result only as a 7-day workflow artifact - the committed
``candidates/<slug>/`` tree ``repository-presenter status`` reads stays stale until a human or
agent session notices and opens a PR by hand. This module is that missing step, run by the
workflow itself, never a human or an agent session.

Simpler than ``components/propose/effect.py`` in exactly the way G7-W14 names: the write target is
THIS control repository, not an external product repository, so there is no candidate-hash/
source-revision binding to a *target's* live state to recheck, and no committed
``ops/proposal-authorizations/`` record to load - the bundle this effect publishes already carries
its own proof (``sealed-ready``'s own ``READY_FOR_PROPOSAL`` check, which only ever holds after a
real independent-review ACCEPT and a fresh-process no-op proof; ``present.yml``'s own export step
never hands this effect anything else). Every other gate ``AGENTS.md`` "Security and Effects"
requires still holds, in the same shape every other write path in this project uses:

1. ``write_authorized(environment)`` - the owner-controlled kill switch
   ``REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED``. Never inferred from a credential.
2. A write-scoped token is supplied (``GH_CANDIDATES_WRITE_TOKEN`` - never ``GH_TOKEN``, and never
   ``REPOSITORY_PRESENTER_STATE_TOKEN``, ``present.yml``'s own distinctly-scoped state-ref
   credential). It is a short-lived Repository Presenter GitHub App installation token minted
   inside the write job and scoped to this control repository alone - deliberately NOT the job's
   own ambient ``secrets.GITHUB_TOKEN``. Two documented GitHub rules make the ambient token unable
   to carry this effect on this repository (``docs/DECISION_LOG.md`` 2026-10-10): (a) the "Allow
   GitHub Actions to create and approve pull requests" setting is off here, so a ``GITHUB_TOKEN``
   cannot open the pull request at all; (b) events a ``GITHUB_TOKEN`` causes do not start
   ``pull_request`` runs (or, on newer GitHub, start them only in an approval-required state),
   so the required ``Python 3.11``/``3.12``/``3.13`` checks would never report on the branch's
   own head commit. An App installation token has neither limit: its pull request is created, and
   its ``pull_request`` checks run, as for any person's. Exposed under this distinct name so the
   gated step is the only place that name exists, exactly like every sibling effect.
3. Token provenance (``core/github/token_provenance.py``): ``verify_installation_token`` must show
   the token is an installation token whose reach is exactly the control repository, before any
   write; and ``verify_pull_request_app`` must attribute the pull request (an existing one before
   anything is pushed, a new one immediately after it is opened) to the Repository Presenter App -
   the one thing a bare installation token cannot prove about itself ahead of time, and the check
   that catches the job's ambient ``GITHUB_TOKEN`` (also a ``ghs_`` installation token, of GitHub's
   own Actions app) ever being wired in by mistake.

Idempotent by construction, never by a separate check bolted on: ``candidates/<slug>/CURRENT`` is
read at the exact commit this effect is about to build on (the branch's own remote tip when one
already exists, or the base branch otherwise) before anything is staged. When that already names
the revision this run would publish, nothing is committed, pushed, or opened - whether that is
because the base branch is already current, or because a prior run already pushed this exact
revision to this same pending branch. A new commit and a new/updated pull request happen only when
that check finds a genuine difference, which is also what keeps an unchanged candidate re-run from
ever opening a duplicate PR or pushing an empty commit.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    PullRequestRef,
)
from repository_presenter.core.github.client import (
    create_pull_request as default_create_pull_request,
)
from repository_presenter.core.github.client import (
    find_pull_requests as default_find_pull_requests,
)
from repository_presenter.core.github.client import (
    update_pull_request as default_update_pull_request,
)
from repository_presenter.core.github.token_provenance import TokenDecision
from repository_presenter.core.github.token_provenance import (
    verify_installation_token as default_verify_installation_token,
)
from repository_presenter.core.github.token_provenance import (
    verify_pull_request_app as default_verify_pull_request_app,
)

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_CANDIDATES_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

#: One stable branch per external target repository this control repository tracks a candidate
#: for - mirrors ``components/propose/effect.py``'s own ``PRESENTER_BRANCH`` reasoning: a fixed,
#: derived name is what lets every run find the same branch rather than inventing a new one.
BRANCH_PREFIX = "repository-presenter/candidates-update/"

_NOT_AUTHORIZED_REASON = (
    f"not authorized: set {AUTHORIZATION_VARIABLE}=1 (owner-controlled) - a token's presence or "
    "scope is never by itself sufficient"
)
_NO_TOKEN_REASON = "no write-scoped token available (GH_CANDIDATES_WRITE_TOKEN, never GH_TOKEN)"

#: The revision this effect's own commit message and pull-request body carry, read back to decide
#: whether an open pull request already carries the exact revision about to be published.
_REVISION_LINE = re.compile(r"revision:\s*([0-9a-f]+)")


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only when the owner has explicitly set ``AUTHORIZATION_VARIABLE`` to a truthy
    value. Absence, an empty string, or any other value is unauthorized - fail closed."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


def branch_name(repository: str) -> str:
    """The canonical candidates-update branch name for ``repository`` (the external target this
    bundle is about, never the control repository itself)."""
    return BRANCH_PREFIX + repository.replace("/", "__")


def _is_same_revision(pr: PullRequestRef, revision: str) -> bool:
    found = _REVISION_LINE.search(pr.body)
    return found is not None and found.group(1) == revision


RemoteBranchShaFn = Callable[[str], "str | None"]
CheckoutFn = Callable[[str, str], None]
ReadCommittedFn = Callable[[str], "str | None"]
OverlayFn = Callable[[], None]
StageAndCommitFn = Callable[["tuple[str, ...]", str], "str | None"]
PushFn = Callable[[str], None]
VerifyTokenFn = Callable[[str, str], TokenDecision]
VerifyPullRequestAppFn = Callable[..., TokenDecision]
FindPullRequestsFn = Callable[..., "tuple[PullRequestRef, ...]"]
CreatePullRequestFn = Callable[..., PullRequestRef]
UpdatePullRequestFn = Callable[..., PullRequestRef]


@dataclass(frozen=True)
class PublishResult:
    """The outcome of one :func:`publish_candidates` call. ``effected`` is ``True`` only when the
    control repository's committed state is confirmed to already carry (or was just made to carry)
    ``revision`` for ``repository`` - whether or not that needed a new commit or PR edit; every
    refusal leaves ``effected`` ``False`` with a typed ``reason_code`` and no write call made."""

    repository: str
    control_repository: str
    authorized: bool
    effected: bool
    branch: str
    revision: str
    pr_number: int | None
    pr_url: str | None
    commit_written: bool
    pr_created: bool
    pr_updated: bool
    reason: str
    reason_code: Refusal | None = None


def publish_candidates(
    *,
    repository: str,
    control_repository: str,
    revision: str,
    base_branch: str,
    token: str | None,
    environment: Mapping[str, str],
    pr_title: str,
    pr_body: str,
    bundle_paths: tuple[str, ...],
    current_path: str,
    remote_branch_sha: RemoteBranchShaFn,
    checkout: CheckoutFn,
    read_committed: ReadCommittedFn,
    overlay: OverlayFn,
    stage_and_commit: StageAndCommitFn,
    push: PushFn,
    branch: str | None = None,
    verify_token: VerifyTokenFn = default_verify_installation_token,
    verify_pull_request_app: VerifyPullRequestAppFn = default_verify_pull_request_app,
    find_pull_requests: FindPullRequestsFn = default_find_pull_requests,
    create_pull_request: CreatePullRequestFn = default_create_pull_request,
    update_pull_request: UpdatePullRequestFn = default_update_pull_request,
) -> PublishResult:
    """Publish ``repository``'s sealed bundle at ``revision`` to the control repository's own
    ``candidates/<slug>/`` tree - but only past every gate in this module's own docstring. Every
    early return before the first write makes no write call, and the gates before the token check
    make no call at all.

    ``bundle_paths`` are the exact working-tree paths this effect stages and commits (the sealed
    revision directory and its ``CURRENT`` pointer). ``current_path`` is ``CURRENT``'s own
    working-tree path, read back *after* :func:`checkout` moves the tree to this run's actual
    starting point (the pending branch's own prior tip, or the base branch) but *before*
    :func:`overlay` replaces it with the new bundle - never assumed from whatever ``base_branch``
    happened to have checked out before this effect ran, and never compared against the new
    bundle's own already-overlaid copy of itself. ``overlay`` applies the sealed bundle onto the
    working tree only after that comparison has decided there is a genuine difference to
    publish - exactly like ``propose.yml``'s own "Require a READY_FOR_PROPOSAL bundle" step
    overlays the same artifact, but ordered after the branch checkout here (never before it): a
    checkout with the bundle already overlaid would carry those uncommitted changes onto whatever
    commit the branch happens to already hold, which conflicts whenever that commit's own copy of
    the bundle differs - exactly the case this effect is built to handle idempotently."""
    owner, name = control_repository.split("/", 1)
    branch = branch if branch is not None else branch_name(repository)

    def _refuse(authorized: bool, code: Refusal, reason: str) -> PublishResult:
        return PublishResult(
            repository=repository,
            control_repository=control_repository,
            authorized=authorized,
            effected=False,
            branch=branch,
            revision=revision,
            pr_number=None,
            pr_url=None,
            commit_written=False,
            pr_created=False,
            pr_updated=False,
            reason=reason,
            reason_code=code,
        )

    def _github_error(reason: str) -> PublishResult:
        return _refuse(True, Refusal.GITHUB_ERROR, reason)

    if not write_authorized(environment):
        return _refuse(False, Refusal.WRITE_NOT_ENABLED, _NOT_AUTHORIZED_REASON)

    if not token:
        return _refuse(True, Refusal.NO_WRITE_TOKEN, _NO_TOKEN_REASON)

    token_decision = verify_token(control_repository, token)
    if not token_decision.ok:
        return _refuse(
            True, token_decision.code or Refusal.TOKEN_UNVERIFIABLE, token_decision.reason
        )

    # past every gate that needs nothing but the token itself -------------------------------

    try:
        branch_exists = remote_branch_sha(branch) is not None
    except RepositoryMetadataError as exc:
        return _github_error(f"could not read {branch!r}: {exc}")
    # The ref to fetch and build on: the pending branch's own name when it already exists
    # (continuing it - never rebased, never force-reset), or the base branch for a fresh one.
    # Never a bare sha: a fresh hosted checkout has no history for a branch it has not fetched.
    start_point = branch if branch_exists else base_branch

    try:
        checkout(branch, start_point)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not check out {branch!r} from {start_point!r}: {exc}")

    try:
        previous_current = read_committed(current_path)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not read {current_path!r}: {exc}")
    previous_revision = previous_current.strip() if previous_current is not None else None

    if previous_revision == revision:
        # Already current at this exact revision on this exact branch - nothing new to publish.
        # Report any already-open PR for it rather than silently doing nothing unexplained.
        try:
            prs = find_pull_requests(owner, name, head_branch=branch, token=token)
        except RepositoryMetadataError as exc:
            return _github_error(f"could not list pull requests for {branch!r}: {exc}")
        existing_pr = next((pr for pr in prs if pr.state == "open"), None)
        return PublishResult(
            repository=repository,
            control_repository=control_repository,
            authorized=True,
            effected=True,
            branch=branch,
            revision=revision,
            pr_number=existing_pr.number if existing_pr is not None else None,
            pr_url=existing_pr.url if existing_pr is not None else None,
            commit_written=False,
            pr_created=False,
            pr_updated=False,
            reason="candidates/ is already current at this revision; nothing to publish",
        )

    # Read the pull-request state before any write, exactly like
    # ``components/propose/effect.py``'s own ordering - a read that fails costs nothing to undo,
    # and the same read decides both whether to create or update after the push below.
    try:
        prs = find_pull_requests(owner, name, head_branch=branch, token=token)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not list pull requests for {branch!r}: {exc}")
    existing_pr = next((pr for pr in prs if pr.state == "open"), None)
    if existing_pr is not None:
        # Before anything is staged or pushed: never add a commit to a pull request this App did
        # not open (a foreign or hand-made PR on the reserved branch name is a stop, not a merge).
        attribution = verify_pull_request_app(owner, name, existing_pr.number, token=token)
        if not attribution.ok:
            return _refuse(True, attribution.code or Refusal.TOKEN_UNVERIFIABLE, attribution.reason)

    try:
        overlay()
    except RepositoryMetadataError as exc:
        return _github_error(f"could not overlay the sealed bundle: {exc}")

    message = (
        f"Update candidates/ for {repository} via repository-presenter\n\nrevision: {revision}\n"
    )
    try:
        commit_sha = stage_and_commit(bundle_paths, message)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not commit {bundle_paths!r}: {exc}")
    if commit_sha is None:
        # Defensive: the previous_revision check above should already have caught a no-op
        # candidate. Reaching here with nothing actually staged is a dependency-identity defect,
        # never papered over as a silent success.
        return _github_error(
            "the candidate revision changed but staging produced no diff - refusing to push or "
            "open a pull request for an empty commit"
        )

    try:
        push(branch)
    except RepositoryMetadataError as exc:
        return _github_error(f"could not push {branch!r}: {exc}")

    pr_created = False
    pr_updated = False
    if existing_pr is None:
        try:
            pr_ref = create_pull_request(
                owner,
                name,
                title=pr_title,
                body=pr_body,
                head=branch,
                base=base_branch,
                token=token,
            )
        except RepositoryMetadataError as exc:
            return _github_error(f"could not open the candidates-update pull request: {exc}")
        pr_created = True
        attribution = verify_pull_request_app(owner, name, pr_ref.number, token=token)
        if not attribution.ok:
            return PublishResult(
                repository=repository,
                control_repository=control_repository,
                authorized=True,
                effected=False,
                branch=branch,
                revision=revision,
                pr_number=pr_ref.number,
                pr_url=pr_ref.url,
                commit_written=True,
                pr_created=True,
                pr_updated=False,
                reason=f"{attribution.reason} - review and close {pr_ref.url} if it is not ours",
                reason_code=attribution.code or Refusal.TOKEN_UNVERIFIABLE,
            )
    else:
        pr_ref = existing_pr
        if existing_pr.title != pr_title or not _is_same_revision(existing_pr, revision):
            try:
                pr_ref = update_pull_request(
                    owner, name, existing_pr.number, title=pr_title, body=pr_body, token=token
                )
                pr_updated = True
            except RepositoryMetadataError as exc:
                return _github_error(f"could not update the candidates-update pull request: {exc}")

    return PublishResult(
        repository=repository,
        control_repository=control_repository,
        authorized=True,
        effected=True,
        branch=branch,
        revision=revision,
        pr_number=pr_ref.number,
        pr_url=pr_ref.url,
        commit_written=True,
        pr_created=pr_created,
        pr_updated=pr_updated,
        reason="published",
    )
